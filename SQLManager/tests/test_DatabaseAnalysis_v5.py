import os
import sys
import types
import unittest

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager import DatabaseAnalysisController


class _FakeAnalysisDB:
    def __init__(self):
        self.db_type = 'sqlserver'
        self.commands = []

    def doQuery(self, query, params=(), ret_cols=False):
        if '/*sqlmanager:analysis_tables*/' in query:
            rows = [
                ('SALESLINE', 500000, 1, 0),
                ('CUSTOMER', 12000, 0, 0),
            ]
            columns = ['table_name', 'row_count', 'has_primary_key', 'has_clustered_index']
        elif '/*sqlmanager:analysis_indexes*/' in query:
            rows = [
                ('SALESLINE', 'PK_SALESLINE', 1, 1, 'NONCLUSTERED', 0, 'RECID', ''),
                ('SALESLINE', 'IX_SALESLINE_COMPANY_STATUS', 0, 0, 'NONCLUSTERED', 0, 'COMPANYID,STATUS', 'AMOUNT'),
                ('SALESLINE', 'IX_SALESLINE_COMPANY_STATUS_DUP', 0, 0, 'NONCLUSTERED', 0, 'COMPANYID,STATUS', 'AMOUNT'),
            ]
            columns = ['table_name', 'index_name', 'is_unique', 'is_primary_key', 'index_type', 'is_clustered', 'key_columns', 'included_columns']
        elif '/*sqlmanager:analysis_columns*/' in query:
            rows = [
                ('SALESLINE', 'RECID', 'bigint', 0, 8),
                ('SALESLINE', 'COMPANYID', 'int', 0, 4),
                ('SALESLINE', 'STATUS', 'varchar', 0, 20),
                ('SALESLINE', 'CREATEDDATE', 'datetime', 0, 8),
                ('SALESLINE', 'CUSTOMERID', 'bigint', 0, 8),
                ('SALESLINE', 'AMOUNT', 'decimal', 0, 8),
                ('CUSTOMER', 'RECID', 'bigint', 0, 8),
                ('CUSTOMER', 'NAME', 'varchar', 1, 120),
            ]
            columns = ['table_name', 'column_name', 'data_type', 'is_nullable', 'max_length']
        elif '/*sqlmanager:analysis_foreign_keys*/' in query:
            rows = [
                ('SALESLINE', 'CUSTOMERID', 'FK_SALESLINE_CUSTOMER', 'CUSTOMER', 'RECID'),
            ]
            columns = ['table_name', 'column_name', 'foreign_key_name', 'referenced_table', 'referenced_column']
        elif '/*sqlmanager:analysis_constraints*/' in query:
            rows = [
                ('SALESLINE', 'PK_SALESLINE', 'PRIMARY_KEY_CONSTRAINT'),
                ('SALESLINE', 'FK_SALESLINE_CUSTOMER', 'FOREIGN_KEY_CONSTRAINT'),
            ]
            columns = ['table_name', 'constraint_name', 'constraint_type']
        else:
            rows = []
            columns = []
        return (rows, columns) if ret_cols else rows

    def executeCommand(self, command, params=()):
        self.commands.append((command, params))
        return 1


class DatabaseAnalysisTests(unittest.TestCase):
    def test_analyze_returns_grid_and_recommendations(self):
        analyzer = DatabaseAnalysisController(_FakeAnalysisDB())
        report = analyzer.analyze_database(query_patterns=[{
            'table': 'SALESLINE',
            'filters_eq': ['COMPANYID', 'STATUS'],
            'range_filters': ['CREATEDDATE'],
            'include': ['AMOUNT'],
            'frequency': 12,
            'workload': 'transaction',
        }])

        self.assertEqual(report['status'], 200)
        self.assertEqual(report['summary']['tables'], 2)
        self.assertEqual(report['summary']['duplicate_indexes'], 1)
        self.assertLess(report['summary']['transaction_score'], 100)
        self.assertEqual(report['grid_columns'][0], 'table')
        self.assertGreaterEqual(len(report['columns']), 1)
        self.assertGreaterEqual(len(report['indexes']), 1)
        self.assertTrue(any(row['kind'] == 'existing' for row in report['grid']))
        self.assertTrue(any(row['category'] == 'workload-index' for row in report['recommendations']))
        self.assertTrue(any(row['category'] == 'foreign-key-index' for row in report['recommendations']))
        self.assertTrue(any('CREATE' in str(row.get('ddl') or '') or 'DROP' in str(row.get('ddl') or '') for row in report['recommendations']))

    def test_apply_recommendations_supports_dry_run(self):
        db = _FakeAnalysisDB()
        analyzer = DatabaseAnalysisController(db)
        report = analyzer.analyze()
        dry_run = analyzer.apply_recommendations(report['recommendations'], dry_run=True)
        executed = analyzer.apply_recommendations(report['recommendations'][:1], dry_run=False)

        self.assertGreaterEqual(len(dry_run), 1)
        self.assertEqual(len(db.commands), 1)
        self.assertTrue(executed[0]['applied'])


if __name__ == '__main__':
    unittest.main()