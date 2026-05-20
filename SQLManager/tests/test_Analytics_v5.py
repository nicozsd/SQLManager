import os
import sqlite3
import sys
import types
import unittest

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager import CoreConfig
from SQLManager.analytics import AnalyticsRegistry, AnalyticsRouter, DataSource, Dataset, MaterializationJob, Measure
from SQLManager.analytics.query import DatasetExecutor


class _Condition:
    def __init__(self, sql, values):
        self.sql = sql
        self.values = values

    def __and__(self, other):
        return _Condition(f"({self.sql} AND {other.sql})", self.values + other.values)

    def to_sql(self, marker):
        return self.sql.replace("?", marker), self.values


class _Field:
    def __init__(self, name):
        self.name = name

    def __eq__(self, value):
        return _Condition(f"{self.name} = ?", [value])

    def __gt__(self, value):
        return _Condition(f"{self.name} > ?", [value])

    def __ge__(self, value):
        return _Condition(f"{self.name} >= ?", [value])

    def __lt__(self, value):
        return _Condition(f"{self.name} < ?", [value])

    def __le__(self, value):
        return _Condition(f"{self.name} <= ?", [value])

    def __ne__(self, value):
        return _Condition(f"{self.name} <> ?", [value])

    def like(self, value):
        return _Condition(f"{self.name} LIKE ?", [value])

    def in_(self, values):
        return _Condition(f"{self.name} IN ({', '.join(['?'] * len(values))})", list(values))


class _FakeDB:
    def __init__(self):
        self.queries = []

    def doQuery(self, query, params=(), ret_cols=False):
        self.queries.append((query, params, ret_cols))
        if "COUNT(*) AS TOTAL" in query.upper():
            result = [(7,)]
            columns = ["TOTAL"]
        else:
            result = [("OPEN", 3)]
            columns = ["STATUS", "records"]
        return (result, columns) if ret_cols else result


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


class _FakeSalesModel:
    column_calls = 0

    def __init__(self, db):
        self.db = db
        self.source_name = "SALES"

    def get_table_columns(self):
        type(self).column_calls += 1
        return [
            ["RECID", "int", "NO"],
            ["STATUS", "varchar", "YES"],
            ["AMOUNT", "decimal", "YES"],
        ]

    def field(self, name):
        return _Field(name)

    def get_parameter_marker(self):
        return "?"

    def format_pagination(self, limit, offset):
        return f" LIMIT {limit} OFFSET {offset}"


class _FakeFastAPIApp:
    def __init__(self):
        self.routes = []

    def add_api_route(self, path, handler, methods=None, name=None, tags=None):
        self.routes.append({
            "path": path,
            "handler": handler,
            "methods": methods or [],
            "name": name,
            "tags": tags or [],
        })


class AnalyticsRegistryTests(unittest.TestCase):
    def setUp(self):
        CoreConfig.reset()

    def test_autodiscover_registers_public_classes(self):
        module_name = "fake_sqlmanager_analytics_module"
        fake_module = types.ModuleType(module_name)

        FakeDatasetModel = type("FakeDatasetModel", (), {})
        FakeDatasetModel.__module__ = module_name

        fake_module.FakeDatasetModel = FakeDatasetModel
        fake_module.__all__ = ["FakeDatasetModel"]
        sys.modules[module_name] = fake_module

        try:
            registry = AnalyticsRegistry()
            registry.autodiscover([module_name])
            dataset = registry.get("FakeDatasetModel")
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "FakeDatasetModel")
            self.assertIn("records", dataset.measures)
        finally:
            sys.modules.pop(module_name, None)

    def test_search_and_catalog_summary(self):
        registry = AnalyticsRegistry()
        sales = Dataset(name='Sales', source=DataSource(name='Sales'))
        sales.tags = ['BI', 'AUTO']
        sales.add_measure(Measure(name='records'))
        registry.register(sales)

        tickets = Dataset(name='Tickets', source=DataSource(name='Tickets'))
        tickets.tags = ['SUPPORT']
        tickets.add_measure(Measure(name='records'))
        registry.register(tickets)

        results = registry.search(query='sale', tags=['BI'])
        summary = registry.catalog_summary()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'Sales')
        self.assertEqual(summary['datasets'], 2)
        self.assertEqual(summary['tags']['BI'], 1)


class DatasetExecutorTests(unittest.TestCase):
    def setUp(self):
        CoreConfig.reset()
        CoreConfig.configure_analytics({"enabled": True, "cache_ttl": 30})
        _FakeSalesModel.column_calls = 0

    def test_execute_grouped_dataset_returns_rows_and_meta(self):
        registry = AnalyticsRegistry()
        dataset = Dataset(
            name="Sales",
            source=DataSource(name="Sales", model=_FakeSalesModel),
            dimensions=["STATUS"],
        )
        dataset.add_measure(Measure(name="records"))
        registry.register(dataset)

        db = _FakeDB()
        executor = DatasetExecutor(db, registry)
        response = executor.execute("Sales", {
            "dimensions": ["STATUS"],
            "filters": {"RECID_gt": 0},
            "include_total": True,
        })

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["data"][0]["STATUS"], "OPEN")
        self.assertEqual(response["data"][0]["records"], 3)
        self.assertEqual(response["meta"]["total"], 7)
        self.assertEqual(len(db.queries), 2)

    def test_execute_reuses_cached_dataset_metadata(self):
        registry = AnalyticsRegistry()
        dataset = Dataset(
            name="Sales",
            source=DataSource(name="Sales", model=_FakeSalesModel),
            dimensions=["STATUS"],
        )
        dataset.add_measure(Measure(name="records"))
        registry.register(dataset)

        db = _FakeDB()
        executor = DatasetExecutor(db, registry)
        executor.execute("Sales", {"dimensions": ["STATUS"], "filters": {"RECID_gt": 0}})
        executor.execute("Sales", {"dimensions": ["STATUS"], "filters": {"RECID_gt": 1}})

        self.assertEqual(_FakeSalesModel.column_calls, 1)


class AnalyticsRouterTests(unittest.TestCase):
    def setUp(self):
        CoreConfig.reset()
        CoreConfig.configure_analytics({
            "enabled": True,
            "url_prefix": "analytics",
            "materializations": [{"name": "Sales", "dataset_name": "Sales", "payload": {"include_total": True}}],
            "auto_start_materialization": False,
        })

    def test_router_registers_routes_for_fastapi_style_app(self):
        app = _FakeFastAPIApp()
        registry = AnalyticsRegistry()
        dataset = Dataset(name='Sales', source=DataSource(name='Sales', model=_FakeSalesModel), dimensions=['STATUS'])
        dataset.add_measure(Measure(name='records'))
        registry.register(dataset)
        router = AnalyticsRouter(_FakeDB(), app=app, registry=registry)
        self.assertEqual(len(router.get_route_definitions()), 7)
        self.assertEqual(len(app.routes), 7)
        self.assertTrue(any(route["path"] == "/analytics/datasets" for route in app.routes))
        self.assertTrue(any(route["path"] == "/analytics/catalog" for route in app.routes))
        self.assertTrue(any(route["path"] == "/analytics/ui" for route in app.routes))
        self.assertEqual(len(router.scheduler.list_jobs()), 1)


class MaterializationSchedulerTests(unittest.TestCase):
    def setUp(self):
        CoreConfig.reset()
        CoreConfig.configure_analytics({"enabled": True})

    def test_manual_materialization_job_runs(self):
        registry = AnalyticsRegistry()
        dataset = Dataset(name='Sales', source=DataSource(name='Sales', model=_FakeSalesModel), dimensions=['STATUS'])
        dataset.add_measure(Measure(name='records'))
        registry.register(dataset)

        router = AnalyticsRouter(_FakeDB(), registry=registry)
        router.scheduler.register_job(MaterializationJob(name='warm_sales', dataset_name='Sales', payload={'dimensions': ['STATUS']}))
        response = router.scheduler.run_job('warm_sales')

        self.assertEqual(response['status'], 200)
        self.assertEqual(response['data']['last_status'], 'success')


if __name__ == "__main__":
    unittest.main()