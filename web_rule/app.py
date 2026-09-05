from flask import Flask, Response, jsonify, render_template, request
import base64
import copy
import json
import os
import subprocess
import tempfile

from elim_unwanted import QueryTreeOptimizer
from predicate_pushdown import optimize_query_plan

app = Flask(__name__, static_folder='static', template_folder='templates')
APP_STATE = {}


DB_PARAMS = {
    'dbname': os.environ.get('PGDATABASE', ''),
    'user': os.environ.get('PGUSER', ''),
    'password': os.environ.get('PGPASSWORD', ''),
    'host': os.environ.get('PGHOST', 'localhost'),
    'port': os.environ.get('PGPORT', '5432'),
}


def _request_json_payload() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _find_parser_binary() -> str | None:
    env_bin = os.environ.get('SQL_TO_RA_BIN')
    candidates = [
        env_bin,
        os.path.join(os.path.dirname(__file__), '..', 'parser', 'sql_parser'),
        os.path.join(os.path.dirname(__file__), '..', 'parser', 'sql_to_ra'),
        os.path.join(os.path.dirname(__file__), '..', 'final_parser', 'sql_to_ra'),
        os.path.join(os.path.dirname(__file__), 'sql_to_ra'),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
    return None


def _load_json_output(raw: str):
    raw = raw.strip()
    return json.loads(raw)


def _parse_sql_to_json(sql_query: str):
    parser_bin = _find_parser_binary()
    if not parser_bin:
        return None, {
            'success': False,
            'error': 'Parser binary not found. Compile sql_parser/sql_to_ra first or set SQL_TO_RA_BIN.',
        }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
        temp_file.write(sql_query)
        temp_path = temp_file.name

    try:
        result = subprocess.run(
            [parser_bin, temp_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return _load_json_output(result.stdout), None
    except subprocess.TimeoutExpired:
        return None, {
            'success': False,
            'error': 'Parser execution timed out',
        }
    except subprocess.CalledProcessError as exc:
        return None, {
            'success': False,
            'error': 'Parser execution failed',
            'stderr': exc.stderr,
        }
    except json.JSONDecodeError:
        return None, {
            'success': False,
            'error': 'Parser output was not valid JSON',
            'raw_output': result.stdout,
        }
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _count_filters(node):
    if not isinstance(node, dict):
        return 0
    total = 1 if node.get('type') == 'select' else 0
    for key in ('input', 'left', 'right', 'query'):
        child = node.get(key)
        if isinstance(child, dict):
            total += _count_filters(child)
    return total


def _collect_join_arms(node, arms):
    """Collect the full subtrees that are children of join nodes."""
    if not isinstance(node, dict):
        return
    if node.get('type') == 'join':
        left = node.get('left')
        right = node.get('right')
        if isinstance(left, dict) and left.get('type') == 'join':
            _collect_join_arms(left, arms)
        else:
            arms.append(copy.deepcopy(left))
        if isinstance(right, dict) and right.get('type') == 'join':
            _collect_join_arms(right, arms)
        else:
            arms.append(copy.deepcopy(right))
        return


def _find_join_root(node):
    """Walk past wrapper nodes and return the first join/base_relation."""
    wrappers = []
    cur = node
    while isinstance(cur, dict) and cur.get('type') not in ('join', 'base_relation', None):
        wrappers.append(cur)
        cur = cur.get('input')
    return cur, wrappers


def _rewrap(inner, wrappers):
    """Reattach wrapper nodes around a reordered join subtree."""
    result = inner
    for wrapper in reversed(wrappers):
        wrapper_copy = copy.deepcopy(wrapper)
        wrapper_copy['input'] = result
        result = wrapper_copy
    return result


def _collect_join_conditions(node, conds):
    if not isinstance(node, dict):
        return
    if node.get('type') == 'join':
        condition = node.get('condition')
        if condition:
            conds.append(condition)
        _collect_join_conditions(node.get('left'), conds)
        _collect_join_conditions(node.get('right'), conds)


def _build_left_deep_join(arms, original_join_conditions=None):
    if not arms:
        return None
    cur = copy.deepcopy(arms[0])
    original_join_conditions = original_join_conditions or {}
    for index, nxt in enumerate(arms[1:]):
        cur = {
            'type': 'join',
            'condition': original_join_conditions.get(index),
            'left': cur,
            'right': copy.deepcopy(nxt),
        }
    return cur


def _simple_join_optimize(plan):
    """Heuristic join reorder that preserves pushed-down wrappers."""
    if not isinstance(plan, dict):
        return plan, {'note': 'invalid plan'}

    join_root, outer_wrappers = _find_join_root(plan)
    if not isinstance(join_root, dict) or join_root.get('type') != 'join':
        return copy.deepcopy(plan), {'note': 'no join tree found'}

    arms = []
    _collect_join_arms(join_root, arms)
    if len(arms) < 2:
        return copy.deepcopy(plan), {'note': 'no join tree found'}

    scored = []
    for arm in arms:
        score = _count_filters(arm)
        scored.append((score, arm))
    scored.sort(key=lambda item: (-item[0], json.dumps(item[1], sort_keys=True)))

    ordered = [arm for _, arm in scored]

    original_conds = []
    _collect_join_conditions(join_root, original_conds)
    cond_map = {idx: cond for idx, cond in enumerate(original_conds)}

    optimized = _build_left_deep_join(ordered, cond_map)
    optimized = _rewrap(optimized, outer_wrappers)

    return optimized, {
        'original_leaf_count': len(arms),
        'heuristic': 'relations with more pushed filters are joined earlier',
    }


def _canonical(node):
    if isinstance(node, dict):
        return tuple(sorted((k, _canonical(v)) for k, v in node.items() if k != 'cost'))
    if isinstance(node, list):
        return tuple(_canonical(x) for x in node)
    return node


def _find_common_subexpressions(node, freq):
    if not isinstance(node, dict):
        return
    sig = _canonical(node)
    freq[sig] = freq.get(sig, 0) + 1
    for key in ('input', 'left', 'right', 'query'):
        child = node.get(key)
        if isinstance(child, dict):
            _find_common_subexpressions(child, freq)


def _collect_duplicate_nodes(node, freq, out, seen):
    if not isinstance(node, dict):
        return
    sig = _canonical(node)
    if freq.get(sig, 0) > 1 and sig not in seen:
        out.append(copy.deepcopy(node))
        seen.add(sig)
    for key in ('input', 'left', 'right', 'query'):
        child = node.get(key)
        if isinstance(child, dict):
            _collect_duplicate_nodes(child, freq, out, seen)


def _run_cse(plan):
    if not isinstance(plan, dict):
        return None
    optimizer = QueryTreeOptimizer()
    return optimizer.opt(plan)


def _cse_duplicate_meta(cse_plan):
    common_expr_count = len(cse_plan.get('common_expressions', {}))
    pred_duplicate_count = int(cse_plan.get('metadata', {}).get('predicate_duplicate_count', 0))
    return {
        'duplicate_count': common_expr_count + pred_duplicate_count,
        'subtree_duplicates': common_expr_count,
        'predicate_duplicates': pred_duplicate_count,
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/parse', methods=['POST'])
def parse_sql():
    sql_query = request.form.get('sql_query', '').strip()
    if not sql_query:
        return jsonify({'success': False, 'error': 'Empty SQL query'})

    output_json, parse_error = _parse_sql_to_json(sql_query)
    if parse_error:
        return jsonify(parse_error)

    APP_STATE.clear()
    APP_STATE['original_plan_json'] = output_json
    return jsonify({'success': True, 'result': output_json})


@app.route('/analyze', methods=['POST'])
def analyze_sql_pipeline():
    sql_query = request.form.get('sql_query', '').strip()
    if not sql_query and request.is_json:
        sql_query = (request.json or {}).get('sql_query', '').strip()

    if not sql_query:
        return jsonify({'success': False, 'error': 'Empty SQL query'})

    parsed_plan, parse_error = _parse_sql_to_json(sql_query)
    if parse_error:
        return jsonify({
            'success': False,
            'error': parse_error.get('error', 'Parsing failed'),
            'details': parse_error,
            'stages': {
                'parse': {'status': 'error', 'error': parse_error.get('error')},
                'predicate_pushdown': {'status': 'skipped'},
                'join_optimization': {'status': 'skipped'},
                'cse': {'status': 'skipped'},
            },
        })

    APP_STATE.clear()
    APP_STATE['original_plan_json'] = parsed_plan

    stages = {
        'parse': {
            'status': 'success',
            'plan': parsed_plan,
        },
    }

    pred_plan = parsed_plan
    pred_result = optimize_query_plan(json.dumps(parsed_plan))
    if pred_result:
        pred_plan = pred_result['optimized_plan_json']
        APP_STATE['pred_plan_json'] = pred_plan
        stages['predicate_pushdown'] = {
            'status': 'success',
            'original_plan': pred_result['original_plan_json'],
            'optimized_plan': pred_plan,
            'original_plan_str': pred_result['original_plan_str'],
            'optimized_plan_str': pred_result['optimized_plan_str'],
        }
    else:
        stages['predicate_pushdown'] = {
            'status': 'error',
            'error': 'Predicate pushdown failed',
        }

    joined_plan, join_meta = _simple_join_optimize(pred_plan)
    APP_STATE['join_plan_json'] = joined_plan
    stages['join_optimization'] = {
        'status': 'success',
        'original_plan': pred_plan,
        'optimized_plan': joined_plan,
        'meta': join_meta,
    }

    cse_before_plan = copy.deepcopy(joined_plan)
    cse_plan = _run_cse(cse_before_plan)
    if cse_plan is None:
        stages['cse'] = {
            'status': 'error',
            'error': 'Common subexpression elimination failed',
        }
    else:
        APP_STATE['cse_plan_json'] = cse_plan
        stages['cse'] = {
            'status': 'success',
            'original_plan': cse_before_plan,
            'optimized_plan': cse_plan,
            'meta': _cse_duplicate_meta(cse_plan),
        }

    APP_STATE['analyze_result'] = stages
    return jsonify({'success': True, 'stages': stages})


@app.route('/optimize/pred_push/', methods=['POST'])
def optimize_pred_push():
    relational_algebra = _request_json_payload().get('relational_algebra', {})
    result = optimize_query_plan(json.dumps(relational_algebra))
    if not result:
        return jsonify({'success': False, 'error': 'Predicate pushdown failed'})

    APP_STATE['pred_plan_json'] = result['optimized_plan_json']
    return jsonify({
        'success': True,
        'original_plan_json': result['original_plan_json'],
        'optimized_plan_json': result['optimized_plan_json'],
        'original_plan_str': result['original_plan_str'],
        'optimized_plan_str': result['optimized_plan_str'],
    })


@app.route('/optimize/join/', methods=['POST'])
def optimize_join():
    relational_algebra = _request_json_payload().get('relational_algebra', {})
    optimized_plan, meta = _simple_join_optimize(relational_algebra)
    APP_STATE['join_plan_json'] = optimized_plan
    return jsonify({
        'success': True,
        'original_plan_json': relational_algebra,
        'optimized_plan_json': optimized_plan,
        'meta': meta,
    })


@app.route('/optimize/join/cost', methods=['POST'])
def optimize_join_cost():
    relational_algebra = _request_json_payload().get('relational_algebra', {})
    if not relational_algebra:
        return jsonify({'success': False, 'error': 'No relational algebra plan provided'})

    try:
        from join_optimization import QueryOptimizer
        relational_algebra = APP_STATE.get('pred_plan_json', relational_algebra)
        optimizer = QueryOptimizer({'use_mock': True})
        optimizer.connect_database()
        result = optimizer.costs_plans(relational_algebra)

        if not result:
            return jsonify({'success': False, 'error': 'Cost optimizer returned no result'})
        if isinstance(result, dict) and 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500

        APP_STATE['cost_join_plan_json'] = result.get('best_plan')
        return jsonify({
            'success': True,
            'original_plan_json': result.get('naive_plan'),
            'optimized_plan_json': result.get('best_plan'),
            'naive_cost': result.get('naive_cost'),
            'best_cost': result.get('best_cost'),
            'cost_scale': result.get('scale'),
            'estimator_naive_cost': result.get('estimator_naive_cost'),
            'estimator_best_cost': result.get('estimator_best_cost'),
            'selected_method': result.get('selected_method'),
            'selected_order': result.get('selected_order'),
            'selected_strategies': result.get('selected_strategies'),
            'method_actual_costs': result.get('method_actual_costs', {}),
            'naive_breakdown': result.get('naive_breakdown', {}),
            'best_breakdown': result.get('best_breakdown', {}),
            'assumptions': result.get('assumptions', {}),
            'algorithm_results': result.get('algorithm_results', {}),
            'most_efficient_algorithm': result.get('most_efficient_algorithm'),
            'most_efficient_estimated_cost': result.get('most_efficient_estimated_cost'),
            'table_rows': result.get('table_rows', {}),
            'mode': 'mock',
        })
    except ImportError as exc:
        return jsonify({
            'success': False,
            'error': f'Missing dependency: {exc}. Try: pip install psycopg2-binary',
        }), 500
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Cost optimizer error: {str(exc)}'}), 500


@app.route('/optimize/common_subexpr/', methods=['POST'])
def optimize_common_subexpr():
    relational_algebra = _request_json_payload().get('relational_algebra', {})
    original_plan = copy.deepcopy(relational_algebra)
    optimized = _run_cse(original_plan)
    if optimized is None:
        return jsonify({'success': False, 'error': 'Common subexpression elimination failed'})

    return jsonify({
        'success': True,
        'original_plan_json': original_plan,
        'optimized_plan_json': optimized,
        'meta': _cse_duplicate_meta(optimized),
    })


@app.route('/generate_tree', methods=['POST'])
def generate_tree():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 400

    payload = request.get_json(silent=True) or {}
    tree_json = payload.get('query', payload)
    output_format = str(payload.get('format', 'svg')).lower()

    if output_format not in {'svg', 'png'}:
        return jsonify({'success': False, 'error': 'format must be svg or png'}), 400
    if not isinstance(tree_json, dict):
        return jsonify({'success': False, 'error': 'query payload must be a JSON object'}), 400

    try:
        from query_tree_viz import generate_query_tree
        graph_bytes = generate_query_tree(tree_json, output_format=output_format)
    except ModuleNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Missing dependency: graphviz. Install with pip install -r requirements.txt',
        }), 500
    except Exception as exc:
        return jsonify({'success': False, 'error': f'Failed to generate tree: {exc}'}), 500

    if output_format == 'svg':
        return Response(graph_bytes.decode('utf-8'), mimetype='image/svg+xml')

    # PNG is returned as base64 for direct frontend embedding.
    return jsonify({
        'success': True,
        'format': 'png',
        'image_base64': base64.b64encode(graph_bytes).decode('utf-8'),
    })


if __name__ == '__main__':
    app.run(debug=True, port=8000)
