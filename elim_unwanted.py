import copy
import json


RELATIONAL_NODE_TYPES = {
    "project",
    "select",
    "join",
    "groupby",
    "subquery",
    "rename",
}

CHILD_KEYS = ("input", "left", "right", "query")


class QueryTreeOptimizer:
    def __init__(self):
        self.common_expressions = {}
        self.next_expr_id = 0
        self.predicate_duplicates = {}
        self.next_pred_id = 0
        self.predicate_duplicate_count = 0

    def opt(self, query_tree):
        tree_copy = copy.deepcopy(query_tree)
        self._dedupe_predicates(tree_copy)
        self._dedupe_select_chains(tree_copy)
        common_exprs = self.f(tree_copy)
        optimized_tree = self.g(tree_copy, common_exprs)
        return {
            "metadata": {
                "version": "1.0",
                "optimization_level": "expressions_only",
                "predicate_duplicate_count": self.predicate_duplicate_count,
            },
            "common_expressions": self.common_expressions,
            "common_predicates": self.predicate_duplicates,
            "query": optimized_tree,
        }

    def _dedupe_select_chains(self, node):
        if not isinstance(node, dict):
            return

        for key in ("input", "left", "right", "query", "child"):
            child = node.get(key)
            if isinstance(child, dict):
                self._dedupe_select_chains(child)

        if node.get("type") != "select":
            return

        child = node.get("input")
        while isinstance(child, dict) and child.get("type") == "select":
            parent_sig = json.dumps(node.get("condition"), sort_keys=True)
            child_sig = json.dumps(child.get("condition"), sort_keys=True)

            if parent_sig != child_sig:
                break

            self._record_duplicate_predicate(node.get("condition"), 2)
            node["input"] = child.get("input")
            child = node.get("input")

    def _dedupe_predicates(self, node):
        if not isinstance(node, dict):
            return

        for key, value in list(node.items()):
            if key in {"condition", "having", "having_cond"} and isinstance(value, dict):
                node[key] = self._dedupe_logical_expression(value)
                continue

            if isinstance(value, dict):
                self._dedupe_predicates(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._dedupe_predicates(item)

    def _flatten_logical(self, expr, operator):
        if not isinstance(expr, dict) or expr.get("type") != operator:
            return [expr]
        left = self._flatten_logical(expr.get("left"), operator)
        right = self._flatten_logical(expr.get("right"), operator)
        return left + right

    def _chain_logical(self, terms, operator):
        if not terms:
            return {}
        if len(terms) == 1:
            return terms[0]

        cur = terms[0]
        for term in terms[1:]:
            cur = {"type": operator, "left": cur, "right": term}
        return cur

    def _record_duplicate_predicate(self, predicate_node, occurrences):
        pred_id = f"pred_{self.next_pred_id}"
        self.next_pred_id += 1
        self.predicate_duplicates[pred_id] = {
            "predicate": copy.deepcopy(predicate_node),
            "occurrences": occurrences,
        }
        self.predicate_duplicate_count += occurrences - 1

    def _dedupe_logical_expression(self, expr):
        if not isinstance(expr, dict):
            return expr

        expr_type = expr.get("type")
        if expr_type in {"AND", "OR"}:
            flat_terms = self._flatten_logical(expr, expr_type)
            normalized_terms = [self._dedupe_logical_expression(term) for term in flat_terms]

            unique_terms = []
            counts = {}
            first_term_by_signature = {}

            for term in normalized_terms:
                signature = json.dumps(term, sort_keys=True)
                counts[signature] = counts.get(signature, 0) + 1
                if signature not in first_term_by_signature:
                    first_term_by_signature[signature] = term
                    unique_terms.append(term)

            for signature, occurrences in counts.items():
                if occurrences > 1:
                    self._record_duplicate_predicate(first_term_by_signature[signature], occurrences)

            return self._chain_logical(unique_terms, expr_type)

        for side in ("left", "right", "cond"):
            child = expr.get(side)
            if isinstance(child, dict):
                expr[side] = self._dedupe_logical_expression(child)
        return expr

    def _is_relational_subtree(self, node):
        if not isinstance(node, dict):
            return False
        node_type = node.get("type")
        if node_type not in RELATIONAL_NODE_TYPES:
            return False
        return any(isinstance(node.get(key), dict) for key in CHILD_KEYS)

    def f(self, tree):
        expr_map = {}

        def dfs(node):
            if not isinstance(node, dict):
                return

            for value in node.values():
                if isinstance(value, dict):
                    dfs(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            dfs(item)

            if self._is_relational_subtree(node):
                expr_str = json.dumps(node, sort_keys=True)
                expr_map.setdefault(expr_str, []).append(node)

        dfs(tree)
        return {key: nodes for key, nodes in expr_map.items() if len(nodes) > 1}

    def g(self, tree, common_exprs):
        sorted_exprs = sorted(common_exprs.items(), key=lambda item: -len(item[0]))
        covered_node_ids = set()

        for _, nodes in sorted_exprs:
            available_nodes = [node for node in nodes if id(node) not in covered_node_ids]
            if len(available_nodes) < 2:
                continue

            expr_id = f"expr_{self.next_expr_id}"
            self.next_expr_id += 1
            self.common_expressions[expr_id] = copy.deepcopy(available_nodes[0])

            for node in available_nodes:
                self._mark_descendants(node, covered_node_ids)
                node.clear()
                node["type"] = "expr_ref"
                node["id"] = expr_id

        return tree

    def _mark_descendants(self, node, covered_node_ids):
        if not isinstance(node, dict):
            return
        covered_node_ids.add(id(node))
        for value in node.values():
            if isinstance(value, dict):
                self._mark_descendants(value, covered_node_ids)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._mark_descendants(item, covered_node_ids)
