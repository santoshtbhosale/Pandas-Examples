"""Tests for date filtering on Project Home."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from services.project_workflow import filter_rows, parse_filter_date


class TestDateFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "project_id": "WD-001",
                "project_name": "Alpha",
                "client_name": "Client A",
                "engineer_name": "Akash",
                "project_type": "residential",
                "workflow_status": "completed",
                "created_at": "2026-08-10T10:00:00",
            },
            {
                "project_id": "WD-002",
                "project_name": "Beta",
                "client_name": "Client B",
                "engineer_name": "Vaibhav",
                "project_type": "commercial",
                "workflow_status": "in_progress",
                "created_at": "2026-08-15T10:00:00",
            },
        ]

    def test_parse_filter_date(self) -> None:
        dt = parse_filter_date("10-08-2026")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.day, 10)

    def test_from_date_filter(self) -> None:
        filtered = filter_rows(self.rows, from_date=datetime(2026, 8, 12))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["project_id"], "WD-002")

    def test_to_date_filter(self) -> None:
        filtered = filter_rows(self.rows, to_date=datetime(2026, 8, 12))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["project_id"], "WD-001")

    def test_date_range_filter(self) -> None:
        filtered = filter_rows(
            self.rows,
            from_date=datetime(2026, 8, 10),
            to_date=datetime(2026, 8, 12),
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["project_id"], "WD-001")


if __name__ == "__main__":
    unittest.main()
