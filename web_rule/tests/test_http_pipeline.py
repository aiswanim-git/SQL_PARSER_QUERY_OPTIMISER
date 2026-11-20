"""End-to-end checks against the compiled SQL parser and Flask test client.

Run after 'make -C parser' with web_rule dependencies installed.
"""
import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


class HTTPPipelineTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def analyze(self, sql):
        response = self.client.post('/analyze', data={'sql_query': sql})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()

    def test_health_parser_present(self):
        data = self.client.get('/health').get_json()
        self.assertTrue(data['parser_binary_found'])

    def test_three_table_pipeline(self):
        data = self.analyze(
            'SELECT A.id, B.id, C.id FROM A '
            'JOIN B ON A.id = B.id '
            'JOIN C ON B.id = C.id '
            'WHERE B.value > 10'
        )
        self.assertTrue(data.get('success'), data)
        for name in ('parse', 'predicate_pushdown', 'join_optimization', 'cse'):
            self.assertEqual(data['stages'][name]['status'], 'success', (name, data))

    def test_groupby_stage_does_not_fail(self):
        data = self.analyze(
            'SELECT A.dept FROM employee A '
            'WHERE A.value > 10 GROUP BY A.dept'
        )
        self.assertTrue(data.get('success'), data)
        self.assertEqual(data['stages']['predicate_pushdown']['status'], 'success', data)

    def test_mock_cost_endpoint(self):
        data = self.analyze(
            'SELECT A.id, B.id FROM employee A '
            'JOIN department B ON A.id = B.id WHERE A.value > 10'
        )
        self.assertTrue(data.get('success'), data)
        plan = data['stages']['predicate_pushdown']['optimized_plan']
        resp = self.client.post('/optimize/join/cost', json={'relational_algebra': plan})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        result = resp.get_json()
        self.assertTrue(result.get('success'), result)
        self.assertEqual(result.get('mode'), 'mock')
        self.assertIsInstance(result.get('naive_cost'), (float, int))
        self.assertIsInstance(result.get('best_cost'), (float, int))

    def test_invalid_sql_returns_failure(self):
        data = self.analyze('SELEC A.id FORM employee A')
        self.assertFalse(data.get('success'), data)


if __name__ == '__main__':
    unittest.main()
