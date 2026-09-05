# This code takes 2 json objects as input: one original and one joined.
# It pushes down select operators into the joined plan by matching base tables
# from the original plan. Subquery aliases are resolved to their real table names.
import json
import copy


def attach_select_nodes(source_plan_input, join_plan_input):
    """
    Walk the source plan to collect every (base_relation -> subtree) mapping,
    then walk the join plan and replace bare base_relation leaves with the
    corresponding select/base subtree from the source.

    Key fixes vs original:
      1. normalize_relation no longer mutates in-place - returns a clean copy.
      2. collect_relations now traverses into 'subquery' nodes so aliases like
         s1/s2 are properly collected.
      3. relation_to_subtree is keyed by table *name* string (not json.dumps of
         the whole node) so alias->real-table resolution works correctly.
    """

    source_plan = copy.deepcopy(source_plan_input)
    join_plan = copy.deepcopy(join_plan_input)

    # Maps real table name (str) -> subtree to graft (select node or base_relation node)
    relation_to_subtree = {}

    # Maps alias name -> real table name, built while walking the source tree.
    alias_to_real = {}

    def get_table_name(base_relation_node):
        """Return the table name from a base_relation node."""
        tables = base_relation_node.get("tables", [])
        if tables:
            return tables[0].get("name", "")
        return ""

    # ------------------------------------------------------------------ #
    #  Phase 1: walk source plan and collect relation -> subtree mappings #
    # ------------------------------------------------------------------ #
    def collect_relations(node):
        if not isinstance(node, dict) or "type" not in node:
            return

        node_type = node["type"]

        if node_type == "base_relation":
            name = get_table_name(node).lower()
            if name and name not in relation_to_subtree:
                relation_to_subtree[name] = copy.deepcopy(node)

        elif node_type == "select":
            child = node.get("input")
            if child is None:
                return
            if child["type"] == "base_relation":
                # This select wraps a base table - record it (prefer select over bare table)
                name = get_table_name(child).lower()
                if name:
                    relation_to_subtree[name] = copy.deepcopy(node)
            else:
                # select wraps something deeper - keep descending
                collect_relations(child)

        elif node_type == "subquery":
            # Fix: traverse into subquery so aliases like s1/s2 are resolved.
            alias = node.get("alias", "")
            inner = node.get("query")
            if inner:
                collect_relations(inner)
                # Map the alias to the real table name found inside
                real = _find_base_table_name(inner)
                if alias and real:
                    alias_to_real[alias.lower()] = real.lower()

        elif node_type == "join":
            collect_relations(node.get("left", {}))
            collect_relations(node.get("right", {}))

        else:
            child = node.get("input")
            if child:
                collect_relations(child)

    def _find_base_table_name(node):
        """Return the first base table name found under node (DFS)."""
        if not isinstance(node, dict):
            return None
        if node.get("type") == "base_relation":
            return get_table_name(node)
        for value in node.values():
            if isinstance(value, dict):
                result = _find_base_table_name(value)
                if result:
                    return result
        return None

    # ------------------------------------------------------------------ #
    #  Phase 2: walk join plan and graft collected subtrees onto leaves   #
    # ------------------------------------------------------------------ #
    def resolve_name(raw_name):
        """
        Resolve a name to its real table name.
        Tries alias_to_real lookup first, then falls back to the name itself.
        """
        low = raw_name.lower()
        return alias_to_real.get(low, low)

    def insert_selects(node):
        if not isinstance(node, dict) or "type" not in node:
            return

        node_type = node["type"]

        if node_type == "join":
            for side in ("left", "right"):
                child = node.get(side, {})
                if not isinstance(child, dict):
                    continue

                if child.get("type") == "base_relation":
                    raw = get_table_name(child)
                    key = resolve_name(raw)
                    if key in relation_to_subtree:
                        node[side] = copy.deepcopy(relation_to_subtree[key])
                else:
                    insert_selects(child)

        else:
            child = node.get("input")
            if child:
                if isinstance(child, dict) and child.get("type") == "base_relation":
                    raw = get_table_name(child)
                    key = resolve_name(raw)
                    if key in relation_to_subtree:
                        node["input"] = copy.deepcopy(relation_to_subtree[key])
                else:
                    insert_selects(child)

    collect_relations(source_plan)
    insert_selects(join_plan)

    return join_plan


def add_selects(source_plan_input, join_plan_input):
    return attach_select_nodes(source_plan_input, join_plan_input)


if __name__ == "__main__":
    SOURCE_FILE = "optimized_out.json"
    JOIN_PLAN_FILE = "best_plan.json"

    with open(SOURCE_FILE, "r") as f:
        source_plan = json.load(f)

    with open(JOIN_PLAN_FILE, "r") as f:
        join_plan = json.load(f)

    updated_plan = attach_select_nodes(source_plan, join_plan)

    with open("joined.json", "w") as f:
        json.dump(updated_plan, f, indent=4)