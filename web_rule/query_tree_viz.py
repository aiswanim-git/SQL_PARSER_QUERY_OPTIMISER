import itertools
import textwrap

from graphviz import Digraph


COLOR_MAP = {
    "PROJECT": {"fillcolor": "#e8f5e9", "color": "#2e7d32"},
    "SELECT": {"fillcolor": "#ffebee", "color": "#c62828"},
    "JOIN": {"fillcolor": "#e8f0fe", "color": "#1a73e8"},
    "TABLE": {"fillcolor": "#fff3e0", "color": "#ef6c00"},
    "SUBQUERY": {"fillcolor": "#f3e5f5", "color": "#6a1b9a"},
    "NODE": {"fillcolor": "#eceff1", "color": "#455a64"},
}

CHILD_KEYS = {"input", "query", "left", "right", "child"}


def _next_node_id():
    if not hasattr(build_query_tree, "_counter"):
        build_query_tree._counter = itertools.count(1)
    return f"n{next(build_query_tree._counter)}"


def _wrap(text: str, width: int = 34) -> str:
    if not text:
        return ""
    return "\n".join(textwrap.fill(line, width=width) for line in str(text).splitlines())


def _format_operand(value):
    if isinstance(value, dict):
        if value.get("type") == "column":
            table = value.get("table")
            attr = value.get("attr", "")
            return f"{table}.{attr}" if table else str(attr)
        if "table" in value and "attr" in value:
            return f"{value['table']}.{value['attr']}"
        if value.get("type") in {"int", "float", "string"}:
            v = value.get("value")
            return f"'{v}'" if value.get("type") == "string" else str(v)
        return _format_condition(value)
    return str(value)


def _format_condition(condition):
    if not isinstance(condition, dict):
        return str(condition or "")

    op = condition.get("type", "")
    if op == "NOT":
        return f"NOT ({_format_condition(condition.get('cond'))})"
    if "left" in condition and "right" in condition:
        left = _format_operand(condition.get("left"))
        right = _format_operand(condition.get("right"))
        op_map = {
            "EQ": "=",
            "NE": "!=",
            "LT": "<",
            "LE": "<=",
            "GT": ">",
            "GE": ">=",
            "AND": "AND",
            "OR": "OR",
        }
        op_text = op_map.get(op, op)
        return f"({left} {op_text} {right})"
    return str(condition)


def _node_type(data):
    t = str((data or {}).get("type", "")).lower()
    if t == "project":
        return "PROJECT"
    if t == "select":
        return "SELECT"
    if t == "join":
        return "JOIN"
    if t == "base_relation":
        return "TABLE"
    if t == "subquery":
        return "SUBQUERY"
    return "NODE"


def _node_detail(data, kind):
    if kind == "PROJECT":
        cols = data.get("columns") or []
        column_text = []
        for col in cols:
            if isinstance(col, dict):
                table = col.get("table")
                attr = col.get("attr", "*")
                column_text.append(f"{table}.{attr}" if table else str(attr))
            else:
                column_text.append(str(col))
        if not column_text:
            return ""
        return ", ".join(column_text[:6]) + (" ..." if len(column_text) > 6 else "")

    if kind in {"SELECT", "JOIN"}:
        condition = data.get("condition")
        return _format_condition(condition) if condition else ""

    if kind == "TABLE":
        tables = data.get("tables") or []
        labels = []
        for table in tables:
            if not isinstance(table, dict):
                labels.append(str(table))
                continue
            name = table.get("name", "")
            alias = table.get("alias")
            labels.append(f"{name} AS {alias}" if alias else name)
        return ", ".join(labels[:4]) + (" ..." if len(labels) > 4 else "")

    if kind == "SUBQUERY":
        return f"alias: {data.get('alias')}" if data.get("alias") else ""

    # Keep generic nodes readable by excluding structural child keys.
    extras = []
    for key, value in data.items():
        if key in {"type", *CHILD_KEYS}:
            continue
        rendered = value
        if isinstance(value, dict):
            rendered = "{...}"
        elif isinstance(value, list):
            rendered = f"[{len(value)}]"
        extras.append(f"{key}: {rendered}")
    return "; ".join(extras[:4]) + (" ..." if len(extras) > 4 else "")


def _node_label(kind, detail):
    if detail:
        return f"{kind}\n{_wrap(detail)}"
    return kind


def build_query_tree(dot, data, parent_id=None):
    if not isinstance(data, dict):
        return None

    node_id = _next_node_id()
    kind = _node_type(data)
    style = COLOR_MAP.get(kind, COLOR_MAP["NODE"])
    label = _node_label(kind, _node_detail(data, kind))

    dot.node(
        node_id,
        label=label,
        shape="box",
        style="filled,rounded",
        fillcolor=style["fillcolor"],
        color=style["color"],
        fontname="Helvetica",
        fontsize="10",
    )

    if parent_id:
        dot.edge(parent_id, node_id)

    # Unary operators and nested subquery branch.
    for key in ("input", "query", "child"):
        child = data.get(key)
        if isinstance(child, dict):
            build_query_tree(dot, child, node_id)

    # Binary join branches.
    for key in ("left", "right"):
        child = data.get(key)
        if isinstance(child, dict):
            build_query_tree(dot, child, node_id)

    return node_id


def generate_query_tree(plan, output_format="svg"):
    build_query_tree._counter = itertools.count(1)
    dot = Digraph("QueryTree", format=output_format)
    dot.attr(rankdir="TB", splines="ortho", nodesep="0.45", ranksep="0.6")
    dot.attr("node", shape="box", style="filled,rounded")

    build_query_tree(dot, plan)
    return dot.pipe(format=output_format)
