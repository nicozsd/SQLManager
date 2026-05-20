import os
import sys
import types
import unittest

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager.benchmarks import benchmark_callable


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_callable_reports_percentiles(self):
        counter = {'value': 0}

        def sample():
            counter['value'] += 1
            return counter['value']

        result = benchmark_callable('sample', sample, iterations=5, warmup=2)
        payload = result.to_dict()

        self.assertEqual(result.iterations, 5)
        self.assertEqual(result.warmup, 2)
        self.assertEqual(len(result.samples_ms), 5)
        self.assertGreaterEqual(counter['value'], 7)
        self.assertIn('p95_ms', payload)
        self.assertGreaterEqual(payload['max_ms'], payload['min_ms'])


if __name__ == '__main__':
    unittest.main()