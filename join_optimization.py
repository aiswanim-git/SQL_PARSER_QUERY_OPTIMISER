"""
It takes a relational algebra JSON tree, extracts tables + join conditions, and 
then tries different join orders and strategies to find the lowest-cost execution plan.
Finally, it reconstructs a new optimized JSON tree (with costs embedded) representing
 the best query execution plan.
"""

import json
import itertools
import random
from collections import defaultdict, deque
import psycopg2
import copy
from code_calculator import CostCalculator
from select_utils import add_selects

random.seed(42)

class QueryOptimizer:
    def __init__(self,database_paramters):
        #constants assuming for the cost optimisation=> motivation from the postgre sql
        self.page_size = 8192  # typical PostgreSQL page size in bytes
        self.cpu_tuple_cost = 0.01
        self.cpu_index_tuple_cost = 0.005
        self.cpu_operator_cost = 0.0025
        self.seq_page_cost = 1.0
        self.random_page_cost = 4.0
        self.database_paramters = database_paramters
        self.conn = None
        self.cursor = None
        # Force offline mock mode: use hardcoded table stats and avoid DB connections.
        self.use_mock = True
        #join strategies that we are using hash, block, nested
        self.join_strategies = ["hash", "nested", "block"]
        # Selectivity methods
        self.selectivity_methods = ["fixed", "ndv", "mcv"]
        # Cost calculator instance.
        self.cost_calculator = CostCalculator(database_paramters)
        # Per-run randomized mock stats cache so one run stays internally consistent.
        self.mock_table_stats = {}

        if self.use_mock:
            # In mock mode, force the calculator to consume local mock stats.
            _self = self
            self.cost_calculator.connect = lambda: None
            self.cost_calculator.get_table_statistics = lambda tname: _self.get_table_statistics(tname)

            # In mock mode, avoid hard-failing on unexpected nodes.
            _orig_calc = self.cost_calculator.calculate_cost
            def _safe_calculate_cost(node):
                try:
                    return _orig_calc(node)
                except (KeyError, TypeError, AttributeError, ValueError) as e:
                    print(f"[WARN] calculate_cost skipped for node, using fallback: {e}")
                    return (1000.0, 1000.0)
            self.cost_calculator.calculate_cost = _safe_calculate_cost

        # ── FIX: initialise alias maps so _to_alias() is always safe ──────────
        self.alias_map = {}          # alias  -> real table name
        self.subquery_base_tables = {}  # alias -> real table name (subqueries)

    # ── FIX: new helper — replaces every `.split('_')[-1]` in plan builders ──
    def _to_alias(self, table_name):
        """
        Return the short display alias for a fully-resolved table name.

        Resolution order:
          1. Invert alias_map  (alias -> real)  to get real -> alias.
          2. Check subquery_base_tables so subquery aliases (s1, s2 …) that
             point to a real table are also found.
          3. Fall back to the full table name if no alias registered.

        This replaces the brittle table_name.split('_')[-1] hack that
        produced wrong names for any table whose suffix did not match its
        alias (e.g. 'line_items' -> 'items', 'my_employees' -> 'employees').
        """
        inv = {real: alias for alias, real in self.alias_map.items()}
        # Subquery aliases map to themselves in alias_map; surface them here
        # so e.g. 's1' is returned when table_name == 's1'.
        for alias, real in self.subquery_base_tables.items():
            inv.setdefault(real, alias)
        return inv.get(table_name, table_name)

    def connect_database(self):
        """Connecting to the postgre server (skipped in mock mode)"""
        if getattr(self, 'use_mock', False):
            print("[INFO] Mock mode: skipping database connection.")
            return
        try:
            self.conn = psycopg2.connect(**self.database_paramters)
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            # Keep cost_calculator on a real DB connection as well.
            self.cost_calculator.connect()
            print("Connected to PostgreSQL server successfully.")
        except Exception as e:
            print(f"Error connecting to PostgreSQL database: {e}")
            raise

    def disconnect_database(self):
        """ Disconnecting from the database"""
        try:
            self.cost_calculator.disconnect()
        except Exception:
            pass
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Disconnected from PostgreSQL database.")

    def compute_baseline_cost(self, rel_alg_json):
        """
        Compute a baseline (naive) cost using the original join order
        without applying any optimization.
        """
        if not self.conn:
            self.connect_database()

        parsed_tree = json.loads(rel_alg_json)
        tables, join_map, _ = self.parse_relational_algebra(parsed_tree)
      
        join_order = []

        def dfs_extract(node):
            if not isinstance(node, dict) or "type" not in node:
                return

            if node["type"] == "base_relation":
                for tbl in node["tables"]:
                    name = tbl["name"]
                    if name not in join_order:
                        join_order.append(name)
                return

            if node["type"] == "subquery":
                alias = node["alias"]
                if alias not in join_order:
                    join_order.append(alias)
                return

            for val in node.values():
                if isinstance(val, dict):
                    dfs_extract(val)

        dfs_extract(parsed_tree)

        total_cost = 0
        methods = []

        if join_order:
            first = join_order[0]
            try:
                stats = self.get_table_statistics(first)
                total_cost += (
                    stats["page_count"] * self.seq_page_cost +
                    stats["row_count"] * self.cpu_tuple_cost
                )
            except:
                total_cost += 100 

        for i in range(1, len(join_order)):
            current = join_order[i]
            prev_tables = join_order[:i]
            join_attrs = None
            base_table = None

            for t in prev_tables:
                if (t, current) in join_map:
                    base_table = t
                    join_attrs = join_map[(t, current)]
                    break
                elif (current, t) in join_map:
                    base_table = t
                    a, b = join_map[(current, t)]
                    join_attrs = (b, a)  
                    break

            if join_attrs is None:
                methods.append("block")
                total_cost += 500
                continue

            method = "block"
            methods.append(method)

            selectivity = self.estimate_selectivity(
                base_table, current, join_attrs, "fixed"
            )

            intermediate_rows = self.get_intermediate_result_size(
                prev_tables, join_map, "fixed"
            )

            if i == 1:
                join_cost = self.estimate_join_cost(
                    prev_tables[0], current, join_attrs, method, selectivity
                )
            else:
                join_cost = self.estimate_join_cost_with_intermediate(
                    intermediate_rows, current, join_attrs, method, selectivity
                )

            total_cost += join_cost

        return {
            "order": join_order,
            "methods": methods,
            "cost": total_cost
        }

    def select_best_plan(self, plan_options):
        """
        Select the best plan (minimum cost) from all generated plans.
        """
        best_method = None
        min_cost = float('inf')
        for method, plan in plan_options.items():
            if "error" in plan:
                continue
            if plan["cost"] < min_cost:
                min_cost = plan["cost"]
                best_method = method
        if best_method is None:
            return {"error": "No valid plan found"}
        best_plan = plan_options[best_method]
        return (
            best_method,
            best_plan["order"],
            best_plan["strategies"],
            best_plan["cost"]
        )

    def generate_best_plan_json(self, best_plans):
        """
        Generate a JSON representation of the best plan with costs.
        """
        best_method, best_order, best_strategies, best_cost = self.select_best_plan(best_plans)

        print(f"Found best plan using {best_method} with cost {best_cost}")
        print(f"Best join order: {best_order}")
        print(f"Best strategies: {best_strategies}")

        tables_costs = {}
        join_costs = {}

        for table in best_order:
            try:
                stats = self.get_table_statistics(table)
                tables_costs[table] = (
                    stats['page_count'] * self.seq_page_cost +
                    stats['row_count'] * self.cpu_tuple_cost
                )
            except:
                tables_costs[table] = 100

        running_tables = [best_order[0]]
        running_cost = tables_costs[best_order[0]]

        for i in range(1, len(best_order)):
            current_table = best_order[i]
            strategy = best_strategies[i-1] if i-1 < len(best_strategies) else "hash"

            join_attrs = None
            for prev_table in running_tables:
                if (prev_table, current_table) in self.join_conditions:
                    join_attrs = self.join_conditions[(prev_table, current_table)]
                    break
                elif (current_table, prev_table) in self.join_conditions:
                    a, b = self.join_conditions[(current_table, prev_table)]
                    join_attrs = (b, a)
                    break

            if join_attrs is None:
                selectivity = 0.1
            else:
                selectivity = self.estimate_selectivity(
                    running_tables[-1], current_table, join_attrs, best_method
                )   

            intermediate_rows = self.get_intermediate_result_size(
                tuple(running_tables), self.join_conditions, best_method
            )

            if len(running_tables) == 1:
                join_cost = self.estimate_join_cost(
                    running_tables[0], current_table, join_attrs, strategy, selectivity
                )
            else:
                join_cost = self.estimate_join_cost_with_intermediate(
                    intermediate_rows, current_table, join_attrs, strategy, selectivity
                )

            join_costs[(tuple(running_tables), current_table)] = join_cost
            running_cost += join_cost
            running_tables.append(current_table)

        # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────────
        base_node = {
            "type": "base_relation",
            "cost": tables_costs[best_order[0]],
            "tables": [
                {"name": best_order[0], "alias": self._to_alias(best_order[0])}
            ]
        }

        current = base_node
        accumulated_cost = tables_costs[best_order[0]]

        for i in range(1, len(best_order)):
            table_name = best_order[i]
            left_table_name = best_order[i - 1]
            strategy = best_strategies[i-1] if i-1 < len(best_strategies) else "hash"
            join_cost = join_costs.get((tuple(best_order[:i]), table_name), 0)
            accumulated_cost += join_cost

            # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────
            right_node = {
                "type": "base_relation",
                "cost": tables_costs[table_name],
                "tables": [
                    {"name": table_name, "alias": self._to_alias(table_name)}
                ]
            }

            resolved_attrs = None
            for prev in best_order[:i]:
                if (prev, table_name) in self.join_conditions:
                    resolved_attrs = self.join_conditions[(prev, table_name)]
                    left_table_name = prev
                    break
                elif (table_name, prev) in self.join_conditions:
                    b, a = self.join_conditions[(table_name, prev)]
                    resolved_attrs = (a, b)
                    left_table_name = prev
                    break

            if resolved_attrs:
                left_attr, right_attr = resolved_attrs
            else:
                left_attr = f"join_key_{self._to_alias(left_table_name)}{self._to_alias(table_name)}"
                right_attr = f"join_key_{self._to_alias(table_name)}{self._to_alias(left_table_name)}"

            # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────
            join_node = {
                "type": "join",
                "cost": accumulated_cost,
                "strategy": strategy,
                "condition": {
                    "type": "EQ",
                    "left": {
                        "table": self._to_alias(left_table_name),
                        "attr": left_attr
                    },
                    "right": {
                        "table": self._to_alias(table_name),
                        "attr": right_attr
                    }
                },
                "left": current,
                "right": right_node
            }
            current = join_node

        return current

    def parse_relational_algebra(self, json_data):
        """
        Parse relational algebra JSON and extract tables, join conditions, join graph.
        """
        tables = set()
        join_conditions = {}
        join_graph = defaultdict(set)

        alias_map = {}
        # ── FIX: save alias_map to self so _to_alias() can use it later ───────
        self.alias_map = alias_map
        self.subquery_base_tables = {}

        def extract_info(node, parent_alias=None):
            if not isinstance(node, dict) or 'type' not in node:
                return
            if node["type"] == "base_relation":
                for table in node["tables"]:
                    table_name = table["name"]
                    if parent_alias:
                        tables.add(parent_alias)
                        alias_map[parent_alias] = parent_alias
                        self.subquery_base_tables[parent_alias] = table_name
                    else:
                        tables.add(table_name)
                        if "alias" in table:
                            alias_map[table["alias"]] = table_name
                return
            if node["type"] == "subquery":
                alias = node["alias"]
                extract_info(node["query"], parent_alias=alias)
                return
            if node["type"] == "join":
                extract_info(node["left"])
                extract_info(node["right"])
                if node["condition"]["type"] == "EQ":
                    left  = node["condition"]["left"]
                    right = node["condition"]["right"]
                    left_table  = left["table"]
                    right_table = right["table"]
                    left_attr   = left["attr"]
                    right_attr  = right["attr"]
                    if "." in left_attr:
                        _, left_attr = left_attr.split(".", 1)
                    if "." in right_attr:
                        _, right_attr = right_attr.split(".", 1)
                    left_real  = alias_map.get(left_table,  left_table)
                    right_real = alias_map.get(right_table, right_table)
                    join_conditions[(left_real, right_real)] = (left_attr, right_attr)
                    join_graph[left_real].add(right_real)
                    join_graph[right_real].add(left_real)
                return
            child = node.get("input")
            if child is not None and isinstance(child, dict):
                extract_info(child, parent_alias=parent_alias)
            else:
                for value in node.values():
                    if isinstance(value, dict) and value.get("type") not in (None,):
                        extract_info(value, parent_alias=parent_alias)

        extract_info(json_data)

        print(f"Alias map: {alias_map}")
        print(f"Subquery base tables: {self.subquery_base_tables}")
        print(f"Extracted tables: {tables}")

        self.add_transitive_edges(join_graph, join_conditions)

        return list(tables), join_conditions, join_graph

    def add_transitive_edges(self, join_graph, join_conditions):
        """
        Add transitive join edges using equivalence classes.
        """
        equivalence_classes = {}

        for (t1, t2), (attr1, attr2) in join_conditions.items():
            key1 = (t1, attr1)
            key2 = (t2, attr2)

            if key1 in equivalence_classes:
                equivalence_classes[key1].add(key2)
            else:
                equivalence_classes[key1] = {key1, key2}

            if key2 in equivalence_classes:
                equivalence_classes[key2].add(key1)
            else:
                equivalence_classes[key2] = {key1, key2}

        changed = True
        while changed:
            changed = False
            for key in list(equivalence_classes.keys()):
                current_class = equivalence_classes[key]
                for other in list(current_class):
                    if other in equivalence_classes and other != key:
                        other_class = equivalence_classes[other]
                        if not current_class.issuperset(other_class):
                            current_class.update(other_class)
                            changed = True
                            for member in other_class:
                                equivalence_classes[member] = current_class

        for eq_set in set(map(frozenset, equivalence_classes.values())):
            eq_list = list(eq_set)
            for i in range(len(eq_list)):
                for j in range(i + 1, len(eq_list)):
                    t1, attr1 = eq_list[i]
                    t2, attr2 = eq_list[j]
                    if (
                        t1 != t2 and
                        (t1, t2) not in join_conditions and
                        (t2, t1) not in join_conditions
                    ):
                        join_conditions[(t1, t2)] = (attr1, attr2)
                        join_graph[t1].add(t2)
                        join_graph[t2].add(t1)

    def generate_valid_join_orders(self, tables, join_graph):
        """
        Generate valid left-deep join orders using BFS.
        """
        if len(tables) <= 1:
            return [tuple(tables)]

        valid_orders = []

        for start in tables:
            queue = deque([(start,)])

            while queue:
                current_order = queue.popleft()

                if len(current_order) == len(tables):
                    valid_orders.append(current_order)
                    continue

                joinable = set()
                for t in current_order:
                    if t in join_graph:
                        joinable.update(join_graph[t])

                joinable -= set(current_order)

                for next_table in joinable:
                    queue.append(current_order + (next_table,))

        print(f"Generated {len(valid_orders)} valid join orders")

        if valid_orders:
            print(f"First join order: {valid_orders[0]}")

        return valid_orders

    def get_table_statistics(self, table_name):
        """
        Return table statistics from live DB (default) or local mock stats.
        """
        table_name = table_name.lower()

        if hasattr(self, 'subquery_base_tables') and table_name in self.subquery_base_tables:
            return self.get_table_statistics(self.subquery_base_tables[table_name])

        if not self.use_mock:
            return self.cost_calculator.get_table_statistics(table_name)

        if table_name.startswith('tmp'):
            parts = table_name.split('.')
            if len(parts) > 1 and not parts[-1].startswith('tmp'):
                return self.get_table_statistics(parts[-1])
            return {'row_count': 1000, 'page_count': 50, 'table_size': 81920, 'columns': {}}

        short = table_name.split('_')[-1] if '_' in table_name else table_name

        if short in self.mock_table_stats:
            return self.mock_table_stats[short]

        row_count = random.randint(300, 12000)
        avg_row_width = random.randint(80, 220)
        table_size = row_count * avg_row_width
        page_count = max(1, (table_size + self.page_size - 1) // self.page_size)

        # Keep some useful column stats for common demo schemas.
        columns = {
            'id': {
                'ndv': max(1, int(row_count * random.uniform(0.7, 1.0))),
                'nullfrac': 0.0,
                'avg_width': 4,
                'mcv': {}
            }
        }
        if short == 'a':
            columns['join_key_ab'] = {
                'ndv': max(1, int(row_count * random.uniform(0.2, 0.6))),
                'nullfrac': 0.0,
                'avg_width': 8,
                'mcv': {}
            }
        elif short == 'b':
            columns['join_key_ab'] = {
                'ndv': max(1, int(row_count * random.uniform(0.2, 0.6))),
                'nullfrac': 0.0,
                'avg_width': 8,
                'mcv': {}
            }
            columns['join_key_bc'] = {
                'ndv': max(1, int(row_count * random.uniform(0.15, 0.5))),
                'nullfrac': 0.0,
                'avg_width': 8,
                'mcv': {}
            }
        elif short == 'c':
            columns['join_key_bc'] = {
                'ndv': max(1, int(row_count * random.uniform(0.2, 0.7))),
                'nullfrac': 0.0,
                'avg_width': 8,
                'mcv': {}
            }

        stats = {
            'row_count': row_count,
            'page_count': page_count,
            'table_size': table_size,
            'columns': columns,
        }
        self.mock_table_stats[short] = stats
        return stats

    def _first_base_table_name(self, node):
        if not isinstance(node, dict):
            return None
        if node.get("type") == "base_relation":
            tables = node.get("tables", [])
            if tables and isinstance(tables[0], dict):
                return tables[0].get("name")
            return None
        for key in ("left", "right", "input", "query"):
            child = node.get(key)
            if isinstance(child, dict):
                name = self._first_base_table_name(child)
                if name:
                    return name
        return None

    def _estimate_eq_selectivity_from_stats(self, condition, left_node, right_node):
        default_sel = 0.1
        if not isinstance(condition, dict) or condition.get("type") != "EQ":
            return default_sel

        left_expr = condition.get("left", {})
        right_expr = condition.get("right", {})
        left_attr = left_expr.get("attr") if isinstance(left_expr, dict) else None
        right_attr = right_expr.get("attr") if isinstance(right_expr, dict) else None
        if not left_attr or not right_attr:
            return default_sel

        left_table = self._first_base_table_name(left_node)
        right_table = self._first_base_table_name(right_node)
        if not left_table or not right_table:
            return default_sel

        try:
            l_stats = self.get_table_statistics(left_table)
            r_stats = self.get_table_statistics(right_table)
            l_col = l_stats.get("columns", {}).get(left_attr)
            r_col = r_stats.get("columns", {}).get(right_attr)
            if not l_col or not r_col:
                return default_sel

            l_ndv = l_col.get("ndv")
            r_ndv = r_col.get("ndv")
            if not l_ndv or not r_ndv:
                return default_sel

            return max(1e-6, min(1.0, 1.0 / max(l_ndv, r_ndv)))
        except Exception:
            return default_sel

    def _rows_to_pages(self, rows, avg_row_width=100):
        if rows is None:
            rows = 1
        if avg_row_width <= 0:
            avg_row_width = 100
        return max(1, int((rows * avg_row_width + self.page_size - 1) // self.page_size))

    def _compute_plan_breakdown(self, node):
        if not isinstance(node, dict):
            return {"cpu_cost": 0.0, "io_cost": 0.0, "total_cost": 0.0, "cardinality": 0.0}

        ntype = node.get("type")
        if ntype == "base_relation":
            table = node.get("tables", [{}])[0].get("name")
            stats = self.get_table_statistics(table)
            rows = float(stats.get("row_count", 1000))
            pages = float(stats.get("page_count", self._rows_to_pages(rows)))
            io_cost = pages * self.seq_page_cost
            cpu_cost = rows * self.cpu_tuple_cost
            total = io_cost + cpu_cost
            return {"cpu_cost": cpu_cost, "io_cost": io_cost, "total_cost": total, "cardinality": rows}

        if ntype == "project":
            return self._compute_plan_breakdown(node.get("input"))

        if ntype == "subquery":
            return self._compute_plan_breakdown(node.get("query"))

        if ntype == "select":
            child = self._compute_plan_breakdown(node.get("input"))
            cond = node.get("condition", {})
            op = cond.get("type") if isinstance(cond, dict) else None
            sel_map = {"GT": 0.5, "LT": 0.5, "EQ": 0.1, "GE": 0.5, "LE": 0.5, "NE": 0.9}
            sel = sel_map.get(op, 0.5)
            cpu_add = child["cardinality"] * self.cpu_operator_cost
            return {
                "cpu_cost": child["cpu_cost"] + cpu_add,
                "io_cost": child["io_cost"],
                "total_cost": child["cpu_cost"] + child["io_cost"] + cpu_add,
                "cardinality": max(1.0, child["cardinality"] * sel),
            }

        if ntype == "join":
            left = self._compute_plan_breakdown(node.get("left"))
            right = self._compute_plan_breakdown(node.get("right"))

            left_rows = max(1.0, left["cardinality"])
            right_rows = max(1.0, right["cardinality"])
            left_pages = self._rows_to_pages(left_rows)
            right_pages = self._rows_to_pages(right_rows)

            sel = self._estimate_eq_selectivity_from_stats(
                node.get("condition"), node.get("left"), node.get("right")
            )
            out_rows = max(1.0, left_rows * right_rows * sel)

            strategy = str(node.get("strategy", "hash")).lower()
            join_io = 0.0
            join_cpu = 0.0
            if strategy == "nested":
                join_io = left_pages * self.seq_page_cost + left_rows * right_pages * self.random_page_cost
                join_cpu = out_rows * self.cpu_operator_cost
            elif strategy == "block":
                block_pages = max(1, (8 * 1024 * 1024) // self.page_size)
                num_blocks = (left_pages + block_pages - 1) // block_pages
                join_io = left_pages * self.seq_page_cost + num_blocks * right_pages * self.seq_page_cost
                join_cpu = out_rows * self.cpu_operator_cost
            else:
                join_io = left_pages * self.seq_page_cost + right_pages * self.seq_page_cost
                join_cpu = (left_rows + right_rows) * self.cpu_tuple_cost + out_rows * self.cpu_operator_cost

            cpu_cost = left["cpu_cost"] + right["cpu_cost"] + join_cpu
            io_cost = left["io_cost"] + right["io_cost"] + join_io
            return {
                "cpu_cost": cpu_cost,
                "io_cost": io_cost,
                "total_cost": cpu_cost + io_cost,
                "cardinality": out_rows,
            }

        # Fallback for unknown nodes.
        child = node.get("input") if isinstance(node.get("input"), dict) else None
        if child is not None:
            return self._compute_plan_breakdown(child)
        return {"cpu_cost": 0.0, "io_cost": 0.0, "total_cost": 0.0, "cardinality": 0.0}

    def find_best_actual_plan(self, rel_algebra_json):
        """
        Exhaustive optimizer:
        Try all join orders + all strategies
        Compute actual cost using cost_calculator
        """

        if isinstance(rel_algebra_json, str):
            rel_algebra_json = json.loads(rel_algebra_json)

        tables, join_conditions, join_graph = self.parse_relational_algebra(rel_algebra_json)
        self.join_conditions = join_conditions

        join_orders = self.generate_valid_join_orders(tables, join_graph)

        best_cost = float('inf')
        best_plan_json = None
        best_order = None
        best_strategies = None

        for order in join_orders:
            strategy_combinations = itertools.product(
                self.join_strategies, repeat=len(order) - 1
            )

            for strategies in strategy_combinations:
                plan_dict = {
                    "order": order,
                    "strategies": list(strategies)
                }

                try:
                    plan_json = self._get_final_json_from_order(
                        rel_algebra_json, plan_dict, is_best=False
                    )

                    plan_json = add_selects(rel_algebra_json, plan_json)

                    cost, _ = self.cost_calculator.calculate_cost(plan_json)

                    if cost < best_cost:
                        best_cost = cost
                        best_plan_json = plan_json
                        best_order = order
                        best_strategies = strategies

                except Exception as e:
                    print(f"[WARN] Skipping plan: {e}")
                    continue

        return {
            "best_cost": best_cost,
            "best_plan": best_plan_json,
            "order": best_order,
            "strategies": best_strategies
        }

    def estimate_selectivity(self, table1, table2, join_attrs, method):
        """
        Estimate selectivity of a join between two tables.
        """
        print(f"Estimating selectivity for {table1} and {table2} using {method}")
        attr1, attr2 = join_attrs
        real1 = self.subquery_base_tables.get(table1.lower(), table1) if hasattr(self, 'subquery_base_tables') else table1
        real2 = self.subquery_base_tables.get(table2.lower(), table2) if hasattr(self, 'subquery_base_tables') else table2
        if real1.startswith('tmp') or real2.startswith('tmp'):
            print(f"Using default selectivity for subquery join")
            return 0.1
        table1, table2 = real1, real2
        if method == "fixed":
            return 0.1
        try:
            stats1 = self.get_table_statistics(table1)
            stats2 = self.get_table_statistics(table2)

            if method == "ndv":
                if (
                    'columns' in stats1 and
                    'columns' in stats2 and
                    attr1 in stats1['columns'] and
                    attr2 in stats2['columns']
                ):
                    ndv1 = stats1['columns'][attr1]['ndv']
                    ndv2 = stats2['columns'][attr2]['ndv']
                    max_ndv = max(ndv1, ndv2)
                    if max_ndv <= 0:
                        return 0.1
                    return 1.0 / max_ndv

            elif method == "mcv":
                if (
                    'columns' in stats1 and
                    'columns' in stats2 and
                    attr1 in stats1['columns'] and
                    attr2 in stats2['columns'] and
                    'mcv' in stats1['columns'][attr1] and
                    'mcv' in stats2['columns'][attr2]
                ):
                    mcv1 = stats1['columns'][attr1]['mcv']
                    mcv2 = stats2['columns'][attr2]['mcv']
                    common_vals = set(mcv1.keys()) & set(mcv2.keys())
                    if common_vals:
                        return sum(mcv1[val] * mcv2[val] for val in common_vals)
                    else:
                        ndv1 = stats1['columns'][attr1]['ndv']
                        ndv2 = stats2['columns'][attr2]['ndv']
                        max_ndv = max(ndv1, ndv2)
                        return 1.0 / max_ndv if max_ndv > 0 else 0.1

        except Exception as e:
            print(f"Error in selectivity estimation: {e}")
            return 0.1
        return 0.1

    def estimate_join_cost(self, table1, table2, join_attrs, strategy, selectivity):
        """
        Estimate cost of joining two tables using a given strategy.
        """
        print(f"Estimating join cost for {table1} and {table2} with strategy {strategy}")

        stats1 = self.get_table_statistics(table1)
        stats2 = self.get_table_statistics(table2)

        row_count1 = stats1['row_count']
        row_count2 = stats2['row_count']
        page_count1 = stats1['page_count']
        page_count2 = stats2['page_count']

        output_rows = row_count1 * row_count2 * selectivity

        if strategy == "hash":
            build_cost = (
                page_count1 * self.seq_page_cost +
                row_count1 * self.cpu_tuple_cost
            )
            probe_cost = (
                page_count2 * self.seq_page_cost +
                row_count2 * self.cpu_tuple_cost
            )
            hash_cpu_cost = (
                (row_count1 + output_rows) * self.cpu_operator_cost
            )
            return build_cost + probe_cost + hash_cpu_cost

        elif strategy == "nested":
            return (
                page_count1 * self.seq_page_cost +
                row_count1 * page_count2 * self.random_page_cost
            )

        elif strategy == "block":
            buffer_size = 8 * 1024 * 1024
            block_size = buffer_size // self.page_size
            if block_size <= 0:
                block_size = 1
            num_blocks = (page_count1 + block_size - 1) // block_size
            return (
                page_count1 * self.seq_page_cost +
                num_blocks * page_count2 * self.seq_page_cost
            )
        return float('inf')

    def get_intermediate_result_size(self, tables, join_conditions, method):
        """
        Estimate the size of intermediate results after joining tables.
        """
        if len(tables) <= 1:
            stats = self.get_table_statistics(tables[0])
            return stats['row_count']

        estimated_rows = self.get_table_statistics(tables[0])['row_count']
        for i in range(1, len(tables)):
            current_table = tables[i]
            join_attrs = None
            for j in range(i):
                prev_table = tables[j]
                if (prev_table, current_table) in join_conditions:
                    join_attrs = join_conditions[(prev_table, current_table)]
                    break
                elif (current_table, prev_table) in join_conditions:
                    a, b = join_conditions[(current_table, prev_table)]
                    join_attrs = (b, a)
                    break
            if join_attrs is None:
                continue
            stats_next = self.get_table_statistics(current_table)
            selectivity = self.estimate_selectivity(
                tables[i - 1], current_table, join_attrs, method
            )
            estimated_rows = (
                estimated_rows *
                stats_next['row_count'] *
                selectivity
            )

        return estimated_rows

    def estimate_join_cost_with_intermediate(self, intermediate_rows, table, join_attrs, strategy, selectivity):
        """
        Estimate cost of joining an intermediate result with a table.
        """
        stats = self.get_table_statistics(table)
        row_count = stats['row_count']
        page_count = stats['page_count']
        if (
            'columns' in stats and
            join_attrs[1] in stats['columns'] and
            'avg_width' in stats['columns'][join_attrs[1]]
        ):
            avg_row_width = stats['columns'][join_attrs[1]]['avg_width']
        else:
            avg_row_width = 100
        intermediate_pages = (intermediate_rows * avg_row_width) / self.page_size
        if intermediate_pages < 1:
            intermediate_pages = 1
        output_rows = intermediate_rows * row_count * selectivity

        if strategy == "hash":
            build_cost = (
                intermediate_pages * self.seq_page_cost +
                intermediate_rows * self.cpu_tuple_cost
            )
            probe_cost = (
                page_count * self.seq_page_cost +
                row_count * self.cpu_tuple_cost
            )
            hash_cpu_cost = (
                (intermediate_rows + output_rows) * self.cpu_operator_cost
            )
            return build_cost + probe_cost + hash_cpu_cost

        elif strategy == "nested":
            return (
                intermediate_pages * self.seq_page_cost +
                intermediate_rows * page_count * self.random_page_cost
            )

        elif strategy == "block":
            buffer_size = 8 * 1024 * 1024
            block_size = buffer_size // self.page_size
            if block_size <= 0:
                block_size = 1
            num_blocks = (intermediate_pages + block_size - 1) // block_size
            return (
                intermediate_pages * self.seq_page_cost +
                num_blocks * page_count * self.seq_page_cost
            )
        return float('inf')

    def optimize_join_query(self, rel_algebra_json):
        """
        Find the optimal join order and strategy using DP.
        """
        if not self.conn:
            self.connect_database()

        json_data = json.loads(rel_algebra_json)
        tables, join_conditions, join_graph = self.parse_relational_algebra(json_data)

        self.join_conditions = join_conditions

        if not tables:
            return {"error": "No tables found"}

        join_orders = self.generate_valid_join_orders(tables, join_graph)

        if not join_orders:
            return {"error": "No valid join orders found"}

        best_plans = {}

        method_to_strategy_preference = {
            "fixed": ["hash", "nested", "block"],
            "ndv": ["nested", "block", "hash"],
            "mcv": ["block", "hash", "nested"]
        }

        for method in self.selectivity_methods:
            best_cost = float('inf')
            best_order = None
            best_strategies = None
            strategy_preference = method_to_strategy_preference.get(method, self.join_strategies)

            for join_order in join_orders:
                dp_table = {}
                dp_strategies = {}

                stats = self.get_table_statistics(join_order[0])
                dp_table[(join_order[0],)] = stats['page_count'] * self.seq_page_cost
                dp_strategies[(join_order[0],)] = []

                for i in range(1, len(join_order)):
                    current_table = join_order[i]
                    prefix = tuple(join_order[:i])
                    best_prefix_cost = float('inf')
                    best_strategy = None
                    join_attrs = None
                    join_table = None

                    for prev_table in prefix:
                        if (prev_table, current_table) in join_conditions:
                            join_table = prev_table
                            join_attrs = join_conditions[(prev_table, current_table)]
                            break
                        elif (current_table, prev_table) in join_conditions:
                            join_table = prev_table
                            a, b = join_conditions[(current_table, prev_table)]
                            join_attrs = (b, a)
                            break

                    if not join_attrs:
                        selectivity = 0.1
                        join_table = prefix[0]
                    else:
                        selectivity = self.estimate_selectivity(join_table, current_table, join_attrs, method)

                    for strategy in strategy_preference:
                        if i == 1:
                            join_cost = self.estimate_join_cost(
                                prefix[0], current_table, join_attrs, strategy, selectivity
                            )
                        else:
                            prev_cost = dp_table[prefix]
                            intermediate_rows = self.get_intermediate_result_size(prefix, join_conditions, method)
                            strategy_cost = self.estimate_join_cost_with_intermediate(
                                intermediate_rows, current_table, join_attrs, strategy, selectivity
                            )
                            join_cost = prev_cost + strategy_cost

                        if strategy == strategy_preference[0]:
                            join_cost *= 0.9
                        elif strategy == strategy_preference[1]:
                            join_cost *= 0.95

                        if join_cost < best_prefix_cost:
                            best_prefix_cost = join_cost
                            best_strategy = strategy

                    next_prefix = tuple(join_order[:i+1])
                    dp_table[next_prefix] = best_prefix_cost
                    dp_strategies[next_prefix] = dp_strategies.get(prefix, []) + [best_strategy]

                final_cost = dp_table.get(tuple(join_order), float('inf'))

                if final_cost < best_cost:
                    best_cost = final_cost
                    best_order = join_order
                    best_strategies = dp_strategies.get(tuple(join_order), [])

            best_plans[method] = {
                'order': best_order,
                'strategies': best_strategies,
                'cost': best_cost
            }

        return best_plans

    def alter_rel_json(self, rel_algebra_json):
        """
        Transform: select(project(...)) -> project(select(...))
        """
        rel_copy = copy.deepcopy(rel_algebra_json)
        try:
            if rel_copy.get('type') == 'select':
                inner = rel_copy.get('input', {})
                if isinstance(inner, dict) and inner.get('type') == 'project':
                    new_select = copy.deepcopy(rel_copy)
                    new_select['input'] = copy.deepcopy(inner.get('input'))
                    new_project = copy.deepcopy(inner)
                    new_project['input'] = new_select
                    return new_project
        except Exception:
            pass
        return rel_copy

    def generate_naive_plan_json(self, naive_plan):
        """
        Generate JSON tree for naive plan with costs.
        """
        naive_order = naive_plan['order']
        naive_strategies = naive_plan.get('strategies', naive_plan.get('methods', []))
        naive_method = "fixed"

        tables_costs = {}
        join_costs = {}

        for table in naive_order:
            try:
                stats = self.get_table_statistics(table)
                tables_costs[table] = (
                    stats['page_count'] * self.seq_page_cost +
                    stats['row_count'] * self.cpu_tuple_cost
                )
            except:
                tables_costs[table] = 100

        running_tables = [naive_order[0]]
        running_cost = tables_costs[naive_order[0]]

        for i in range(1, len(naive_order)):
            current_table = naive_order[i]
            strategy = naive_strategies[i-1] if (naive_strategies and i-1 < len(naive_strategies)) else "hash"
            join_attrs = None

            for prev_table in running_tables:
                if (prev_table, current_table) in self.join_conditions:
                    join_attrs = self.join_conditions[(prev_table, current_table)]
                    break
                elif (current_table, prev_table) in self.join_conditions:
                    a, b = self.join_conditions[(current_table, prev_table)]
                    join_attrs = (b, a)
                    break

            if join_attrs is None:
                selectivity = 0.1
            else:
                selectivity = self.estimate_selectivity(
                    running_tables[-1], current_table, join_attrs, naive_method
                )

            intermediate_rows = self.get_intermediate_result_size(
                tuple(running_tables), self.join_conditions, naive_method
            )

            if len(running_tables) == 1:
                join_cost = self.estimate_join_cost(
                    running_tables[0], current_table, join_attrs, strategy, selectivity
                )
            else:
                join_cost = self.estimate_join_cost_with_intermediate(
                    intermediate_rows, current_table, join_attrs, strategy, selectivity
                )

            join_costs[(tuple(running_tables), current_table)] = join_cost
            running_cost += join_cost
            running_tables.append(current_table)

        # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────────
        base_node = {
            "type": "base_relation",
            "cost": tables_costs[naive_order[0]],
            "tables": [{"name": naive_order[0], "alias": self._to_alias(naive_order[0])}]
        }

        current = base_node
        accumulated_cost = tables_costs[naive_order[0]]

        for i in range(1, len(naive_order)):
            table_name = naive_order[i]
            strategy = naive_strategies[i-1] if (naive_strategies and i-1 < len(naive_strategies)) else "hash"
            join_cost = join_costs.get((tuple(naive_order[:i]), table_name), 0)
            accumulated_cost += join_cost

            # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────
            right_node = {
                "type": "base_relation",
                "cost": tables_costs[table_name],
                "tables": [{"name": table_name, "alias": self._to_alias(table_name)}]
            }

            actual_left = naive_order[i - 1]
            resolved_attrs = None
            for prev in naive_order[:i]:
                if (prev, table_name) in self.join_conditions:
                    resolved_attrs = self.join_conditions[(prev, table_name)]
                    actual_left = prev
                    break
                elif (table_name, prev) in self.join_conditions:
                    b, a = self.join_conditions[(table_name, prev)]
                    resolved_attrs = (a, b)
                    actual_left = prev
                    break

            if resolved_attrs:
                left_attr, right_attr = resolved_attrs
            else:
                left_attr = f"join_key_{self._to_alias(actual_left)}{self._to_alias(table_name)}"
                right_attr = f"join_key_{self._to_alias(table_name)}{self._to_alias(actual_left)}"

            # ── FIX: use _to_alias() instead of .split('_')[-1] ──────────────
            join_node = {
                "type": "join",
                "cost": accumulated_cost,
                "strategy": strategy,
                "condition": {
                    "type": "EQ",
                    "left": {
                        "table": self._to_alias(actual_left),
                        "attr": left_attr
                    },
                    "right": {
                        "table": self._to_alias(table_name),
                        "attr": right_attr
                    }
                },
                "left": current,
                "right": right_node
            }
            current = join_node

        return current

    def _check_orders_equal(self, naive_order, best_orders):
        """
        Check if naive and best join orders are the same.
        """
        _, best_order, _, _ = self.select_best_plan(best_orders)
        if (
            str(list(naive_order['order'])) == str(list(best_order)) or
            len(best_order) <= 2
        ):
            return True
        else:
            return False

    def _get_final_json_from_order(self, rel_algebra_json, order, is_best=False):
        """
        Insert naive or optimized plan into the original JSON tree.
        """
        inp = copy.deepcopy(rel_algebra_json)
        if is_best:
            join_node = self.generate_best_plan_json(order)
        else:
            join_node = self.generate_naive_plan_json(order)

        WRAPPER_TYPES = {"project", "select", "sort", "limit", "aggregate", "distinct"}

        current_node = inp
        while True:
            child = current_node.get("input")
            if child is None:
                current_node["input"] = join_node
                break
            if child.get("type") not in WRAPPER_TYPES:
                current_node["input"] = join_node
                break
            current_node = child

        return inp

    def costs_plans(self, rel_algebra_json):
        """
        Main pipeline: compute naive plan, compute optimized plan,
        build JSON trees, compute costs, compare and return results.
        """
        if type(rel_algebra_json) == str:
            print("[WARNING] Relational algebra JSON is a string, attempting to convert to dict")
            try:
                rel_algebra_json = json.loads(rel_algebra_json)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to decode JSON: {e}")
                return None
        if not isinstance(rel_algebra_json, dict):
            print("[ERROR] Invalid relational algebra JSON format")
            return None

        rel_algebra_json = self.alter_rel_json(rel_algebra_json)

        naive_plan = copy.deepcopy(
            self.compute_baseline_cost(json.dumps(rel_algebra_json))
        )
        best_plans = copy.deepcopy(
            self.optimize_join_query(json.dumps(rel_algebra_json))
        )
        best_actual = self.find_best_actual_plan(rel_algebra_json)

        naive_plan_json = self._get_final_json_from_order(
            rel_algebra_json, naive_plan, is_best=False
        )
        best_plan_json = best_actual["best_plan"]

        naive_plan_json = add_selects(rel_algebra_json, naive_plan_json)

        naive_plan_json_with_cost = copy.deepcopy(naive_plan_json)
        naive_cost, _ = self.cost_calculator.calculate_cost(naive_plan_json_with_cost)

        naive_breakdown = self._compute_plan_breakdown(copy.deepcopy(naive_plan_json))
        best_breakdown = self._compute_plan_breakdown(copy.deepcopy(best_actual["best_plan"]))

        method_actual_costs = {}
        for method, payload in best_plans.items():
            if not isinstance(payload, dict):
                continue
            order = payload.get('order')
            strategies = payload.get('strategies')
            if not order or not strategies:
                continue

            try:
                method_plan = self._get_final_json_from_order(
                    rel_algebra_json,
                    {"order": order, "strategies": strategies},
                    is_best=False,
                )
                method_plan = add_selects(rel_algebra_json, method_plan)
                actual_cost, _ = self.cost_calculator.calculate_cost(copy.deepcopy(method_plan))
                method_actual_costs[method] = {
                    "actual_cost": actual_cost,
                    "estimated_cost": payload.get('cost'),
                    "order": order,
                    "strategies": strategies,
                }
            except Exception as e:
                method_actual_costs[method] = {
                    "error": str(e),
                    "estimated_cost": payload.get('cost'),
                    "order": order,
                    "strategies": strategies,
                }

        return {
            "naive_plan": naive_plan_json,
            "naive_cost": naive_cost,
            "best_plan": best_actual["best_plan"],
            "best_cost": best_actual["best_cost"],
            "scale": best_actual["best_cost"] / naive_cost if naive_cost != 0 else None,
            "selected_order": best_actual["order"],
            "selected_strategies": best_actual["strategies"],
            "method_actual_costs": method_actual_costs,
            "naive_breakdown": naive_breakdown,
            "best_breakdown": best_breakdown,
            "assumptions": {
                "mode": "mock",
                "random_seed": 42,
                "page_size": self.page_size,
                "cpu_tuple_cost": self.cpu_tuple_cost,
                "cpu_operator_cost": self.cpu_operator_cost,
                "seq_page_cost": self.seq_page_cost,
                "random_page_cost": self.random_page_cost,
                "default_selectivity": {"GT": 0.5, "LT": 0.5, "EQ": 0.1},
                "eq_join_selectivity": "1/max(ndv_left, ndv_right), fallback 0.1",
                "block_join_buffer_bytes": 8 * 1024 * 1024,
                "default_row_width_bytes": 100,
            },
        }


def main():
    database_parameters = {
        'db_name':  'random',
        'user':     'pranavi',
        'password': 'postgres',
        'host':     'localhost',
        'port':     '5432'
    }
    with open('optimized_out.json', 'r') as f:
        opt_out_json = f.read()
    optimizer = QueryOptimizer(database_parameters)
    optimizer.connect_database()
    besttree = optimizer.costs_plans(opt_out_json)
    with open('res.json', 'w') as f:
        f.write(json.dumps(besttree, indent=4))