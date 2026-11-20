"""Regression checks for the minimal CV-related optimizer repairs.

Run from repository root:
    python -m unittest discover -s web_rule/tests -p 'test_cv_regressions.py'
"""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import _simple_join_optimize
from join_optimization import QueryOptimizer
from predicate_pushdown import optimize_query_plan
from elim_unwanted import QueryTreeOptimizer

import json


def table(name):
    return {'type': 'base_relation', 'tables': [{'name': name, 'alias': name}]}


def eq(a, b):
    return {
        'type': 'EQ',
        'left': {'table': a, 'attr': 'id'},
        'right': {'type': 'column', 'table': b, 'attr': 'id'},
    }


def join(left, right, condition):
    return {'type': 'join', 'condition': condition, 'left': left, 'right': right}


def join_table_sets(node):
    if node['type'] == 'base_relation':
        return {node['tables'][0]['alias']}
    if node['type'] == 'select':
        return join_table_sets(node['input'])
    if node['type'] == 'join':
        left = join_table_sets(node['left'])
        right = join_table_sets(node['right'])
        cond = node['condition']
        parts = [cond] if cond.get('type') != 'AND' else [cond['left'], cond['right']]
        for part in parts:
            refs = {part['left']['table'], part['right']['table']}
            assert refs.issubset(left | right), (refs, left, right)
        return left | right
    raise AssertionError(node['type'])


class OptimizationRegressions(unittest.TestCase):
    def test_join_conditions_follow_reordered_tables(self):
        # Original order: ((A join B) join C); a filter on B moves B first.
        # Incorrect positional condition assignment would attach B=C to B join A.
        filtered_b = {'type': 'select', 'condition': {
            'type': 'GT',
            'left': {'table': 'B', 'attr': 'value'},
            'right': {'type': 'int', 'value': 1},
        }, 'input': table('B')}
        original = join(join(table('A'), filtered_b, eq('A', 'B')),
                        table('C'), eq('B', 'C'))
        result, _ = _simple_join_optimize(copy.deepcopy(original))
        self.assertEqual(join_table_sets(result), {'A', 'B', 'C'})
        self.assertEqual(result['left']['left']['input']['tables'][0]['name'], 'B')

    def test_complex_join_predicate_falls_back(self):
        original = join(table('A'), table('B'), {
            'type': 'OR', 'left': eq('A', 'B'), 'right': eq('A', 'B')
        })
        result, meta = _simple_join_optimize(original)
        self.assertEqual(result, original)
        self.assertIn('preserved', meta['note'])

    def test_groupby_is_preserved_after_pushdown(self):
        plan = {
            'type': 'project', 'columns': [{'table': 'A', 'attr': 'dept'}],
            'input': {
                'type': 'groupby', 'group_cols': [{'table': 'A', 'attr': 'dept'}],
                'having': None,
                'input': {'type': 'select', 'condition': {
                    'type': 'GT',
                    'left': {'table': 'A', 'attr': 'salary'},
                    'right': {'type': 'int', 'value': 10}
                }, 'input': table('A')},
            },
        }
        result = optimize_query_plan(json.dumps(plan))
        self.assertIsNotNone(result)
        self.assertEqual(result['optimized_plan_json']['input']['type'], 'groupby')
        self.assertEqual(result['optimized_plan_json']['input']['input']['type'], 'select')

    def test_unmatched_filter_is_not_lost(self):
        plan = {'type': 'select', 'condition': {
            'type': 'GT', 'left': {'table': 'X', 'attr': 'value'},
            'right': {'type': 'int', 'value': 10}
        }, 'input': table('A')}
        result = optimize_query_plan(json.dumps(plan))
        self.assertEqual(result['optimized_plan_json']['type'], 'select')

    def test_historical_mock_optimizer_restored(self):
        self.assertTrue(callable(getattr(QueryOptimizer, 'costs_plans', None)))
        optimizer = QueryOptimizer({'use_mock': True})
        self.assertTrue(optimizer.use_mock)

    def test_cse_keeps_query_wrapper(self):
        result = QueryTreeOptimizer().opt(table('A'))
        self.assertIn('query', result)
        self.assertIn('common_expressions', result)


if __name__ == '__main__':
    unittest.main()
