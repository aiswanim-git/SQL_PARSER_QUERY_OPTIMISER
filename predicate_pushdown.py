import json

class LogicalPlanNode:
    def __init__(self, node_type, children=None, predicate=None, table=None, alias=None, columns=None):
        self.node_type = node_type
        self.children = children or []
        self.predicate = predicate
        self.table = table
        self.alias = alias
        self.columns = columns or []

    def __str__(self, level=0):
        indent = '  ' * level
        parts = [f'{indent}{self.node_type}']
        if self.table:
            table_part = self.table if not self.alias or self.alias == self.table else f'{self.table} AS {self.alias}'
            parts[-1] += f'({table_part})'
        if self.predicate:
            parts[-1] += f' [{self.predicate}]'
        if self.columns:
            parts[-1] += f' -> {self.columns}'
        text = '\n'.join(parts) + '\n'
        for child in self.children:
            text += child.__str__(level + 1)
        return text


def format_operand(operand):
    if isinstance(operand, dict):
        if operand.get('type') == 'column' or ('table' in operand and 'attr' in operand):
            table = operand.get('table', '')
            attr = operand.get('attr', '')
            return f'{table}.{attr}' if table else attr
        if operand.get('type') in ('int', 'float'):
            return str(operand.get('value'))
        if operand.get('type') == 'string':
            return repr(operand.get('value', ''))
    if isinstance(operand, str):
        return repr(operand) if ' ' in operand else operand
    return str(operand)


def format_condition_from_json(condition):
    if not isinstance(condition, dict) or 'type' not in condition:
        return str(condition)

    op_map = {
        'EQ': '=', 'LT': '<', 'GT': '>', 'LE': '<=', 'GE': '>=', 'NE': '<>',
        'AND': 'AND', 'OR': 'OR', 'NOT': 'NOT'
    }
    ctype = condition['type']

    if ctype in ('AND', 'OR'):
        left = format_condition_from_json(condition['left'])
        right = format_condition_from_json(condition['right'])
        return f'({left}) {op_map[ctype]} ({right})'
    if ctype == 'NOT':
        inner = format_condition_from_json(condition.get('cond', {}))
        return f'NOT ({inner})'
    if ctype in op_map:
        left = format_operand(condition['left'])
        right = format_operand(condition['right'])
        return f'{left} {op_map[ctype]} {right}'
    return str(condition)


def format_columns_from_json(columns):
    out = []
    for col in columns or []:
        table = col.get('table', '')
        attr = col.get('attr', '')
        out.append(f'{table}.{attr}' if table else attr)
    return out


def build_logical_plan_from_json(obj):
    ntype = obj['type']
    if ntype == 'select':
        child = build_logical_plan_from_json(obj['input'])
        return LogicalPlanNode('FILTER', [child], predicate=format_condition_from_json(obj['condition']))
    if ntype == 'project':
        child = build_logical_plan_from_json(obj['input'])
        return LogicalPlanNode('PROJECT', [child], columns=format_columns_from_json(obj['columns']))
    if ntype == 'join':
        left = build_logical_plan_from_json(obj['left'])
        right = build_logical_plan_from_json(obj['right'])
        return LogicalPlanNode('JOIN', [left, right], predicate=format_condition_from_json(obj.get('condition')))
    if ntype == 'base_relation':
        table_obj = obj['tables'][0]
        return LogicalPlanNode('SCAN', table=table_obj['name'], alias=table_obj.get('alias'))
    if ntype == 'subquery':
        child = build_logical_plan_from_json(obj['query'])
        return LogicalPlanNode('SUBQUERY', [child], table=obj.get('alias'), alias=obj.get('alias'))
    raise ValueError(f'Unsupported node type: {ntype}')


def extract_table_references(predicate):
    refs = set()
    cleaned = predicate.replace('(', ' ').replace(')', ' ').replace(',', ' ')
    for token in cleaned.split():
        if '.' in token and not token.startswith("'"):
            refs.add(token.split('.', 1)[0])
    return refs


def split_top_level_and(predicate):
    parts = []
    cur = []
    level = 0
    i = 0
    while i < len(predicate):
        ch = predicate[i]
        if ch == '(':
            level += 1
        elif ch == ')':
            level -= 1
        if level == 0 and predicate[i:i+5] == ' AND ':
            parts.append(''.join(cur).strip())
            cur = []
            i += 5
            continue
        cur.append(ch)
        i += 1
    tail = ''.join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def find_table_in_subtree(node, table_name):
    if node.node_type == 'SCAN':
        return node.table == table_name or node.alias == table_name
    return any(find_table_in_subtree(child, table_name) for child in node.children)


def push_filter_to_scan(node, table_name, predicate):
    if node.node_type == 'SCAN' and (node.table == table_name or node.alias == table_name):
        return LogicalPlanNode('FILTER', [node], predicate=predicate)

    if not node.children:
        return node

    new_children = []
    pushed = False
    for child in node.children:
        if not pushed and find_table_in_subtree(child, table_name):
            new_children.append(push_filter_to_scan(child, table_name, predicate))
            pushed = True
        else:
            new_children.append(child)
    node.children = new_children
    return node


def predicate_pushdown(plan):
    if not plan or not plan.children:
        return plan

    plan.children = [predicate_pushdown(child) for child in plan.children]

    if plan.node_type != 'FILTER':
        return plan

    child = plan.children[0]
    predicate = plan.predicate

    if child.node_type == 'PROJECT':
        child.children[0] = predicate_pushdown(LogicalPlanNode('FILTER', [child.children[0]], predicate=predicate))
        return child

    conditions = split_top_level_and(predicate) if ' AND ' in predicate else [predicate]
    residual = []
    result = child

    for cond in conditions:
        refs = extract_table_references(cond)
        if len(refs) == 1:
            table_name = next(iter(refs))
            result = push_filter_to_scan(result, table_name, cond)
        else:
            residual.append(cond)

    for cond in residual:
        result = LogicalPlanNode('FILTER', [result], predicate=cond)

    return result


def parse_operand_to_json(text):
    text = text.strip()
    if text.startswith("'") and text.endswith("'"):
        return {'type': 'string', 'value': text[1:-1]}
    if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
        return {'type': 'int', 'value': int(text)}
    try:
        val = float(text)
        return {'type': 'float', 'value': val}
    except ValueError:
        pass
    if '.' in text:
        table, attr = text.split('.', 1)
        return {'type': 'column', 'table': table, 'attr': attr}
    return text


def parse_condition_to_json(text):
    text = text.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1].strip()

    if ' AND ' in text:
        left, right = text.split(' AND ', 1)
        return {'type': 'AND', 'left': parse_condition_to_json(left), 'right': parse_condition_to_json(right)}
    if ' OR ' in text:
        left, right = text.split(' OR ', 1)
        return {'type': 'OR', 'left': parse_condition_to_json(left), 'right': parse_condition_to_json(right)}
    if text.startswith('NOT '):
        return {'type': 'NOT', 'cond': parse_condition_to_json(text[4:])}

    for op_text, op_type in [('<=', 'LE'), ('>=', 'GE'), ('<>', 'NE'), ('=', 'EQ'), ('<', 'LT'), ('>', 'GT')]:
        if op_text in text:
            left, right = text.split(op_text, 1)
            return {'type': op_type, 'left': parse_operand_to_json(left), 'right': parse_operand_to_json(right)}
    return text


def parse_columns_to_json(columns):
    out = []
    for col in columns:
        if '.' in col:
            table, attr = col.split('.', 1)
            out.append({'table': table, 'attr': attr})
        else:
            out.append({'attr': col})
    return out


def logical_plan_to_json(plan):
    if plan.node_type == 'PROJECT':
        return {'type': 'project', 'columns': parse_columns_to_json(plan.columns), 'input': logical_plan_to_json(plan.children[0])}
    if plan.node_type == 'FILTER':
        return {'type': 'select', 'condition': parse_condition_to_json(plan.predicate), 'input': logical_plan_to_json(plan.children[0])}
    if plan.node_type == 'JOIN':
        return {
            'type': 'join',
            'condition': parse_condition_to_json(plan.predicate) if plan.predicate not in (None, 'None') else None,
            'left': logical_plan_to_json(plan.children[0]),
            'right': logical_plan_to_json(plan.children[1]),
        }
    if plan.node_type == 'SCAN':
        table = {'name': plan.table}
        if plan.alias and plan.alias != plan.table:
            table['alias'] = plan.alias
        return {'type': 'base_relation', 'tables': [table]}
    if plan.node_type == 'SUBQUERY':
        return {'type': 'subquery', 'alias': plan.alias, 'query': logical_plan_to_json(plan.children[0])}
    raise ValueError(f'Unsupported node type: {plan.node_type}')


def optimize_query_plan(json_str):
    try:
        query_json = json.loads(json_str)
        logical_plan = build_logical_plan_from_json(query_json)
        original_plan_str = logical_plan.__str__()
        optimized_plan = predicate_pushdown(logical_plan)
        return {
            'original_plan_str': original_plan_str,
            'optimized_plan_str': optimized_plan.__str__(),
            'original_plan_json': query_json,
            'optimized_plan_json': logical_plan_to_json(optimized_plan),
        }
    except Exception:
        return None
