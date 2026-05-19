import json
import os
import sys
import types
import unittest
from datetime import date, datetime, time, timezone
from decimal import Decimal

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from SQLManager.controller.API.WebSocketManager import prepare_json_data
from SQLManager.controller.managers.Relation_Manager import RelationManager
from SQLManager.controller.SystemController import SystemController
from SQLManager.controller.model.EDTController import EDTController


class JsonSerializationTests(unittest.TestCase):
    def test_prepare_json_data_converts_special_types_recursively(self):
        payload = {
            "MOTHLYHOURS": Decimal("40.50"),
            "created_at": datetime(2026, 5, 18, 12, 30, 15),
            "updated_at": datetime(2026, 5, 18, 12, 30, 15, tzinfo=timezone.utc),
            "day": date(2026, 5, 18),
            "hour": time(12, 30, 15),
            "blob": b"\x00\x01",
            "items": [{"amount": Decimal("10.25")}],
        }

        result = prepare_json_data(payload)

        json.dumps(result)
        self.assertEqual(result["MOTHLYHOURS"], 40.5)
        self.assertEqual(result["created_at"], "2026-05-18T12:30:15+00:00")
        self.assertEqual(result["updated_at"], "2026-05-18T12:30:15+00:00")
        self.assertEqual(result["day"], "2026-05-18")
        self.assertEqual(result["hour"], "12:30:15")
        self.assertEqual(result["blob"], "AAE=")
        self.assertEqual(result["items"][0]["amount"], 10.25)


class EDTDateTimeValidationTests(unittest.TestCase):
    def test_datetime_string_from_systemcontroller_timenow_is_accepted(self):
        timestamp = str(SystemController.timenow())
        field = EDTController("datetime")

        field.value = timestamp

        self.assertIsInstance(field.value, datetime)
        self.assertEqual(field.value, datetime.fromisoformat(timestamp))


class RelationRecordsTests(unittest.TestCase):
    def test_set_records_removes_empty_left_join_rows_and_duplicates(self):
        class ChildTable:
            def __init__(self, db):
                self.records = []
                self.current = None

            def set_current(self, record):
                self.current = record

            def clear(self):
                self.records = []

        relation = RelationManager(None, object(), ChildTable)

        relation.set_records([
            {"RECID": None, "PLANID": None, "AMOUNT": None},
            {"RECID": 1, "PLANID": "PLN0001", "AMOUNT": Decimal("10.00")},
            {"RECID": 1, "PLANID": "PLN0001", "AMOUNT": Decimal("10.00")},
            {"RECID": 2, "PLANID": "PLN0001", "AMOUNT": Decimal("20.00")},
        ])

        self.assertEqual(len(relation.records), 2)
        self.assertEqual(relation.records[0]["RECID"], 1)
        self.assertEqual(relation.records[1]["RECID"], 2)
        self.assertEqual(relation.get_instance().records, relation.records)
        self.assertEqual(relation.get_instance().current, relation.records[0])


if __name__ == "__main__":
    unittest.main()
