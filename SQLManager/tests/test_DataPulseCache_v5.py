import os
import sqlite3
import sys
import types
import unittest

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager.controller.Cache.DataPulseCache import DataPulseCache


class _SQLiteLikeDB:
    db_type = 'mysql'

    def __init__(self):
        self.connection = sqlite3.connect(':memory:')

    def doQuery(self, query, params=(), ret_cols=False):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        cursor.close()
        return (rows, columns) if ret_cols else rows

    def executeCommand(self, query, params=()):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount

    def transaction(self):
        parent = self

        class _Tx:
            def __enter__(self):
                return parent

            def __exit__(self, exc_type, exc_value, traceback):
                if exc_type:
                    parent.connection.rollback()
                else:
                    parent.connection.commit()
                return False

        return _Tx()


class DataPulseCacheV5Tests(unittest.TestCase):
    def test_remember_and_invalidate_dataset(self):
        cache = DataPulseCache(enabled=True, default_ttl=30, max_entries=10)
        key = cache.make_query_key(["SalesTable"], "analytics", {"page": 1}, dataset="Sales")

        first = cache.remember("SalesTable", key, lambda: {"rows": 10}, tags=[cache.dataset_key("Sales")])
        second = cache.get("SalesTable", key)
        cache.invalidate_dataset("Sales")
        third = cache.get("SalesTable", key)

        self.assertEqual(first, {"rows": 10})
        self.assertEqual(second, {"rows": 10})
        self.assertIsNone(third)
        self.assertGreaterEqual(cache.stats()["invalidations"], 1)

    def test_configure_updates_runtime_settings(self):
        cache = DataPulseCache(enabled=True, default_ttl=10, max_entries=3)
        cache.configure(default_ttl=90, max_entries=12, backend="memory", namespace="bi")

        self.assertEqual(cache.default_ttl, 90)
        self.assertEqual(cache.max_entries, 12)
        self.assertEqual(cache.backend_name, "memory")
        self.assertEqual(cache.namespace, "bi")

    def test_database_backend_shares_versions_without_redis(self):
        shared_db = _SQLiteLikeDB()

        cache_a = DataPulseCache(enabled=True, default_ttl=30, backend='database', namespace='shared')
        cache_a.bind_connection(shared_db)
        cache_a.configure(backend='database', namespace='shared')

        cache_b = DataPulseCache(enabled=True, default_ttl=30, backend='database', namespace='shared')
        cache_b.bind_connection(shared_db)
        cache_b.configure(backend='database', namespace='shared')

        first_key = cache_a.make_query_key(['SalesTable'], 'analytics', {'page': 1}, dataset='Sales')
        cache_a.remember('SalesTable', first_key, lambda: {'rows': 10}, tags=[cache_a.dataset_key('Sales')])

        mirrored_key = cache_b.make_query_key(['SalesTable'], 'analytics', {'page': 1}, dataset='Sales')
        self.assertEqual(first_key, mirrored_key)
        self.assertEqual(cache_b.get('SalesTable', mirrored_key), {'rows': 10})

        cache_a.invalidate_dataset('Sales')
        second_key = cache_b.make_query_key(['SalesTable'], 'analytics', {'page': 1}, dataset='Sales')

        self.assertNotEqual(first_key, second_key)
        self.assertIsNone(cache_b.get('SalesTable', second_key))
        self.assertEqual(cache_b.backend_name, 'database')


if __name__ == "__main__":
    unittest.main()