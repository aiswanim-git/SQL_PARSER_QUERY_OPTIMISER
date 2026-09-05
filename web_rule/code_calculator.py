import json

try:
    import psycopg2
except ImportError:
    psycopg2 = None


DEFAULT_SELECTIVITY = {
    "GT": 0.5,
    "LT": 0.5,
    "EQ": 0.1,
}

TUPLE_IO_COST = 1


class CostCalculator:
    def __init__(self, db_params):
        self.db_params = db_params
        self.conn = None
        self.cursor = None

        # Planning constants
        self.page_size = 8192
        self.cpu_tuple_cost = 0.01
        self.cpu_index_tuple_cost = 0.005
        self.cpu_operator_cost = 0.0025
        self.seq_page_cost = 1.0
        self.random_page_cost = 4.0

        self.join_strategies = ["hash", "nested", "block"]
        self.selectivity_methods = ["fixed", "ndv", "mcv"]

        # Used during common subexpression costing
        self.exprs = {}
        self.expr_occ = {}

    def connect(self):
        #Open PostgreSQL connection
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Install psycopg2-binary to enable DB-backed costing."
            )

        try:
            self.conn = psycopg2.connect(**self.db_params)
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            print("Connected to PostgreSQL database successfully.")
        except Exception as exc:
            print(f"Error connecting to PostgreSQL database: {exc}")
            raise

    def disconnect(self):
        #Close PostgreSQL connection
        try:
            if self.cursor is not None:
                self.cursor.close()
        finally:
            self.cursor = None

        try:
            if self.conn is not None:
                self.conn.close()
                print("Disconnected from PostgreSQL database.")
        finally:
            self.conn = None

    #internal herlpers
    def _default_stats(self):
        return {
            "row_count": 1000,
            "page_count": 10,
            "table_size": 81920,
            "columns": {},
        }

    def _normalize_table_name(self, table_name):
        if not isinstance(table_name, str):
            return str(table_name).lower()
        return table_name.lower()

    def _is_temp_like(self, table_name):
        return table_name.startswith("tmp")

    def _resolve_subquery_alias(self, table_name):
        # Try to map a temp/subquery alias to a real base table if possible.
        name = self._normalize_table_name(table_name)

        if hasattr(self, "subquery_base_tables") and name in self.subquery_base_tables:
            mapped = self.subquery_base_tables[name]
            print(f"Using base table '{mapped}' for subquery '{name}'")
            return mapped

        parts = name.split(".")
        if len(parts) > 1 and not parts[-1].startswith("tmp"):
            guessed = parts[-1]
            print(f"Extracting base table '{guessed}' from subquery reference '{name}'")
            return guessed

        return None

    def _fetch_table_level_stats(self, table_name):
        query = """
        SELECT
            reltuples AS row_count,
            relpages  AS page_count,
            pg_table_size(%s) AS table_size
        FROM pg_class
        WHERE relname = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (table_name, table_name))
            row = cur.fetchone()

        if not row:
            raise ValueError(f"Table {table_name} not found in the database.")

        row_count, page_count, table_size = row
        return row_count, page_count, table_size

    def _fetch_column_level_stats(self, table_name, row_count):
        query = """
        SELECT
            a.attname AS column_name,
            s.n_distinct AS ndv,
            s.null_frac AS nullfrac,
            s.avg_width AS avg_width,
            array_to_string(s.most_common_vals, ',') AS mcv_values,
            array_to_string(s.most_common_freqs, ',') AS mcv_freqs
        FROM pg_stats s
        JOIN pg_attribute a
          ON s.attname = a.attname
         AND a.attrelid = %s::regclass
        WHERE s.schemaname = 'public'
          AND s.tablename = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (table_name, table_name))
            rows = cur.fetchall()

        stats = {}
        for item in rows:
            col_name, ndv, nullfrac, avg_width, mcv_vals, mcv_freqs = item

            mcv_map = {}
            if mcv_vals and mcv_freqs:
                vals = mcv_vals.split(",")
                freqs = [float(x) for x in mcv_freqs.split(",")]
                mcv_map = dict(zip(vals, freqs))

            stats[col_name] = {
                "ndv": ndv if ndv > 0 else abs(ndv) * row_count,
                "nullfrac": nullfrac,
                "avg_width": avg_width,
                "mcv": mcv_map,
            }

        return stats

    def _predicate_selectivity(self, cond):
        if not isinstance(cond, dict):
            return 0.5
        op = cond.get("type")
        return DEFAULT_SELECTIVITY.get(op, 0.5)

    def _rows_to_pages(self, rows, avg_row_width=100):
        if rows is None:
            rows = 1
        if avg_row_width <= 0:
            avg_row_width = 100
        return max(1, int((rows * avg_row_width + self.page_size - 1) // self.page_size))

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

    def _estimate_join_selectivity(self, condition, left_node, right_node):
        # Default fallback when condition/stats are not usable.
        default_sel = 0.1

        if not isinstance(condition, dict):
            return default_sel
        if condition.get("type") != "EQ":
            return self._predicate_selectivity(condition)

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
            left_stats = self.get_table_statistics(left_table)
            right_stats = self.get_table_statistics(right_table)
            left_col = left_stats.get("columns", {}).get(left_attr)
            right_col = right_stats.get("columns", {}).get(right_attr)
            if not left_col or not right_col:
                return default_sel

            left_ndv = left_col.get("ndv")
            right_ndv = right_col.get("ndv")
            if not left_ndv or not right_ndv:
                return default_sel

            max_ndv = max(left_ndv, right_ndv)
            if max_ndv <= 0:
                return default_sel
            sel = 1.0 / max_ndv
            return max(1e-6, min(1.0, sel))
        except Exception:
            return default_sel

    def _store_metrics(self, node, cost, cardinality):
        node["cost"] = cost
        node["cardinality"] = cardinality

    def get_table_statistics(self, table_name):
        #Get PostgreSQL statistics for a base table.
        name = self._normalize_table_name(table_name)
        is_temp = self._is_temp_like(name)

        if is_temp:
            resolved = self._resolve_subquery_alias(name)
            if resolved is not None:
                return self.get_table_statistics(resolved)

        if self.conn is None:
            if is_temp:
                print(f"Using default statistics for subquery {name}")
                return self._default_stats()
            raise RuntimeError("Database connection has not been established.")

        try:
            row_count, page_count, table_size = self._fetch_table_level_stats(name)
        except Exception as exc:
            print(f"Error getting basic statistics for {name}: {exc}")
            if is_temp:
                print(f"Using default statistics for subquery {name}")
                return self._default_stats()
            raise

        try:
            column_stats = self._fetch_column_level_stats(name, row_count)
        except Exception as exc:
            print(f"Error getting column statistics for {name}: {exc}")
            column_stats = {}

        return {
            "row_count": row_count,
            "page_count": page_count,
            "table_size": table_size,
            "columns": column_stats,
        }


    def calculate_cost(self, node):
        #The result is also injected into the node as: node["cost"], node["cardinality"]
        if not isinstance(node, dict):
            raise ValueError("Plan node must be a dictionary.")

        node_type = node.get("type")
        if not node_type:
            raise ValueError("Each plan node must contain a 'type' field.")

        if node_type == "base_relation":
            return self._cost_base_relation(node)

        if node_type == "select":
            return self._cost_select(node)

        if node_type == "project":
            return self._cost_project(node)

        if node_type == "join":
            return self._cost_join(node)

        if node_type == "subquery":
            return self._cost_subquery(node)

        if node_type == "expr_ref":
            return self._cost_expr_ref(node)

        raise ValueError(f"Unsupported node type: {node_type}")

    def _cost_base_relation(self, node):
        table = node["tables"][0]
        table_name = table["name"]

        stats = self.get_table_statistics(table_name)
        row_count = stats["row_count"]
        page_count = stats["page_count"]

        cost = row_count * self.cpu_tuple_cost + page_count * self.seq_page_cost
        self._store_metrics(node, cost, row_count)
        return cost, row_count

    def _cost_select(self, node):
        input_cost, input_card = self.calculate_cost(node["input"])

        cond = node.get("condition", {})
        sel = self._predicate_selectivity(cond)
        output_card = input_card * sel

        node_cost = input_cost + (input_card * self.cpu_operator_cost)
        self._store_metrics(node, node_cost, output_card)

        return node_cost, output_card

    def _cost_project(self, node):
        input_cost, input_card = self.calculate_cost(node["input"])
        self._store_metrics(node, input_cost, input_card)
        return input_cost, input_card

    def _cost_join(self, node):
        left_cost, left_card = self.calculate_cost(node["left"])
        right_cost, right_card = self.calculate_cost(node["right"])

        left_table = self._first_base_table_name(node.get("left"))
        right_table = self._first_base_table_name(node.get("right"))

        left_avg_width = 100
        right_avg_width = 100
        left_pages = self._rows_to_pages(left_card, left_avg_width)
        right_pages = self._rows_to_pages(right_card, right_avg_width)

        try:
            if left_table:
                l_stats = self.get_table_statistics(left_table)
                left_pages = max(1, int(l_stats.get("page_count", left_pages)))
                l_rows = l_stats.get("row_count", left_card)
                if l_rows:
                    left_avg_width = max(1, int(l_stats.get("table_size", l_rows * 100) / l_rows))
            if right_table:
                r_stats = self.get_table_statistics(right_table)
                right_pages = max(1, int(r_stats.get("page_count", right_pages)))
                r_rows = r_stats.get("row_count", right_card)
                if r_rows:
                    right_avg_width = max(1, int(r_stats.get("table_size", r_rows * 100) / r_rows))
        except Exception:
            pass

        # For intermediate results, derive pages from cardinality.
        if node.get("left", {}).get("type") != "base_relation":
            left_pages = self._rows_to_pages(left_card, left_avg_width)
        if node.get("right", {}).get("type") != "base_relation":
            right_pages = self._rows_to_pages(right_card, right_avg_width)

        selectivity = self._estimate_join_selectivity(
            node.get("condition"), node.get("left"), node.get("right")
        )
        output_card = max(1.0, left_card * right_card * selectivity)

        strategy = str(node.get("strategy", "hash")).lower()
        if strategy == "nested":
            join_cost = (
                left_pages * self.seq_page_cost +
                left_card * right_pages * self.random_page_cost +
                output_card * self.cpu_operator_cost
            )
        elif strategy == "block":
            buffer_size = 8 * 1024 * 1024
            block_pages = max(1, buffer_size // self.page_size)
            num_blocks = (left_pages + block_pages - 1) // block_pages
            join_cost = (
                left_pages * self.seq_page_cost +
                num_blocks * right_pages * self.seq_page_cost +
                output_card * self.cpu_operator_cost
            )
        else:  # hash
            join_cost = (
                left_pages * self.seq_page_cost +
                right_pages * self.seq_page_cost +
                (left_card + right_card) * self.cpu_tuple_cost +
                output_card * self.cpu_operator_cost
            )

        total = left_cost + right_cost + join_cost
        self._store_metrics(node, total, output_card)
        return total, output_card

    def _cost_subquery(self, node):
        sub_cost, sub_card = self.calculate_cost(node["query"])
        node["cost"] = sub_cost
        return sub_cost, sub_card

    def _cost_expr_ref(self, node):
        expr_id = node["id"]

        if expr_id not in self.exprs:
            raise ValueError(f"Expression ID {expr_id} not found in common expressions.")

        expr_node = self.exprs[expr_id]
        self.expr_occ[expr_id] = self.expr_occ.get(expr_id, 0) + 1

        try:
            node["cost"] = expr_node["cost"]
        except Exception:
            print(f"Error: Expression {expr_id} not found in common expressions.")

        node["cardinality"] = expr_node["cardinality"]
        return expr_node["cost"], expr_node["cardinality"]

    # Common subexpression costing
    def calc_subseq_cost(self, subseq_json):
        """
        Cost a structure of the form:
        {
            "query": <main_query_tree>,
            "common_expressions": {
                "E1": <tree>,
                ...
            }
        }
        """
        query = subseq_json["query"]
        common_expressions = subseq_json["common_expressions"]

        valid_types = {"select", "project", "join", "base_relation", "subquery"}

        for expr_id in common_expressions:
            expr_node = common_expressions[expr_id]
            if "type" not in expr_node or expr_node["type"] not in valid_types:
                continue

            print("Costing")
            expr_cost, expr_card = self.calculate_cost(expr_node)
            common_expressions[expr_id]["cost"] = expr_cost
            common_expressions[expr_id]["cardinality"] = expr_card

        self.exprs = common_expressions
        self.expr_occ = {}

        print(f"Expressions: {self.exprs}")

        main_cost, main_card = self.calculate_cost(query)

        total_cost = main_cost
        for expr_id, occ in self.expr_occ.items():
            total_cost -= common_expressions[expr_id]["cost"] * (occ - 1)

        print("Net benefit: ", main_cost - total_cost, main_cost, total_cost)
        return total_cost, main_card

    # Scale cost and cardinality annotations across a plan tree.
    def scale_costs(self, node, factor=0.8):
        if not isinstance(node, dict):
            return

        if "cost" in node:
            node["cost"] *= factor
        if "cardinality" in node:
            node["cardinality"] *= factor

        for child_key in ("left", "right", "input", "query"):
            child = node.get(child_key)
            if isinstance(child, dict):
                self.scale_costs(child, factor)


if __name__ == "__main__":
    db_params = {
        "dbname": "temp",
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": "5432",
    }

    with open("optimized_out.json", "r") as f:
        opt_out_json = json.load(f)

    calculator = CostCalculator(db_params)
    calculator.connect()

    cost, cardinality = calculator.calculate_cost(opt_out_json)

    print(json.dumps(opt_out_json, indent=4))

    with open("optimized_out_with_cost.json", "w") as f:
        json.dump(opt_out_json, f, indent=4)

    print(f"Cost: {cost}, Cardinality: {cardinality}")
    print("JSON cost: ", opt_out_json["cost"])

    with open("subseq_plan.json", "r") as f:
        subseq_json = json.load(f)

    subseq_cost, subseq_cardinality = calculator.calc_subseq_cost(subseq_json)
    print(f"Subsequence Cost: {subseq_cost}, Cardinality: {subseq_cardinality}")