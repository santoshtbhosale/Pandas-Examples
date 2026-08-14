"""Regression tests for Project Home dashboard and project workflow."""

from __future__ import annotations

import inspect
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL
from services.database import delete_project, get_dashboard_projects, get_project_workflow_row, init_db, log_audit_event
from services.project_service import (
    create_new_project_state,
    list_dashboard_projects,
    mark_project_completed,
    mark_project_opened,
    persist_project_state,
    remove_project,
)
from services.project_workflow import (
    STATUS_COMPLETED,
    STATUS_DELAYED,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
    STATUS_PENDING,
    active_elapsed_seconds,
    compute_engineer_performance,
    compute_statistics,
    effective_status,
    filter_rows,
    format_duration,
    performance_indicator,
    rows_for_stats,
)


class TestProjectWorkflowLogic(unittest.TestCase):
    def test_format_duration(self) -> None:
        self.assertEqual(format_duration(5040), "01h 24m")
        self.assertEqual(format_duration(900), "15m")
        self.assertEqual(format_duration(None), "—")

    def test_effective_status_new_and_in_progress(self) -> None:
        self.assertEqual(effective_status({"workflow_status": "new"}), STATUS_NEW)
        row = {"workflow_status": "in_progress", "project_opened_at": datetime.now().isoformat()}
        self.assertEqual(effective_status(row), STATUS_IN_PROGRESS)

    def test_completed_status(self) -> None:
        row = {
            "workflow_status": "completed",
            "completed_at": datetime.now().isoformat(),
            "total_time_taken_seconds": 3600,
        }
        self.assertEqual(effective_status(row), STATUS_COMPLETED)

    def test_delayed_active_project(self) -> None:
        now = datetime.now()
        row = {
            "workflow_status": "in_progress",
            "project_opened_at": (now - timedelta(hours=3)).isoformat(),
            "expected_completion_at": (now - timedelta(minutes=30)).isoformat(),
        }
        self.assertEqual(effective_status(row, now=now), STATUS_DELAYED)

    def test_paused_project_time_does_not_increase(self) -> None:
        now = datetime.now()
        opened = (now - timedelta(hours=2)).isoformat()
        row = {
            "is_paused": 1,
            "project_opened_at": opened,
            "total_time_taken_seconds": 1800,
        }
        self.assertEqual(active_elapsed_seconds(row, now=now), 1800)

    def test_performance_completed_on_time(self) -> None:
        row = {
            "workflow_status": "completed",
            "completed_at": datetime.now().isoformat(),
            "total_time_taken_seconds": 3600,
            "completion_outcome": "on_time",
            "delay_seconds": 0,
        }
        title, detail = performance_indicator(row)
        self.assertIn("On Time", title + detail)

    def test_filter_by_engineer_and_status(self) -> None:
        rows = [
            {"project_id": "1", "engineer_name": "Akash", "workflow_status": "completed"},
            {"project_id": "2", "engineer_name": "Sachin", "workflow_status": "in_progress", "project_opened_at": datetime.now().isoformat()},
        ]
        filtered = filter_rows(rows, engineer="Akash", status_label="Completed")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["project_id"], "1")

    def test_search_filters_locally(self) -> None:
        rows = [
            {"project_id": "WD-1", "project_name": "Tower A", "client_name": "ABC", "engineer_name": "Akash", "workflow_status": "new"},
            {"project_id": "WD-2", "project_name": "Mall B", "client_name": "XYZ", "engineer_name": "Sachin", "workflow_status": "new"},
        ]
        filtered = filter_rows(rows, search="mall")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["project_id"], "WD-2")

    def test_statistics_counts(self) -> None:
        now = datetime.now()
        yesterday = (now - timedelta(days=1)).isoformat()
        rows = [
            {"workflow_status": "completed", "completed_at": now.isoformat(), "created_at": yesterday},
            {"workflow_status": "in_progress", "project_opened_at": now.isoformat(), "created_at": yesterday},
            {"workflow_status": "pending", "is_paused": 1, "created_at": yesterday},
            {
                "workflow_status": "in_progress",
                "project_opened_at": (now - timedelta(days=1)).isoformat(),
                "expected_completion_at": (now - timedelta(minutes=10)).isoformat(),
                "created_at": yesterday,
            },
            {"workflow_status": "new", "created_at": now.isoformat()},
        ]
        stats = compute_statistics(rows, now=now)
        self.assertEqual(stats["total"], 5)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["in_progress"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["delayed"], 1)
        self.assertEqual(stats["today"], 2)

    def test_engineer_performance_summary(self) -> None:
        now = datetime.now()
        rows = [
            {
                "engineer_name": "Akash",
                "workflow_status": "completed",
                "completed_at": now.isoformat(),
                "total_time_taken_seconds": 3600,
            },
            {
                "engineer_name": "Akash",
                "workflow_status": "in_progress",
                "project_opened_at": now.isoformat(),
            },
        ]
        summary = compute_engineer_performance(rows, now=now)
        self.assertEqual(summary[0]["engineer"], "Akash")
        self.assertEqual(summary[0]["projects"], 2)
        self.assertEqual(summary[0]["completed"], 1)
        self.assertEqual(summary[0]["in_progress"], 1)


class TestProjectHomeDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _save(self, name: str, engineer: str = "Akash"):
        state = create_new_project_state(self.db_path)
        state.project.project_name = name
        state.project.engineer_name = engineer
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        persist_project_state(state, self.db_path)
        return state.project.project_id

    def test_dashboard_projects_include_workflow_fields(self) -> None:
        pid = self._save("Alpha Tower")
        rows = get_dashboard_projects(db_path=self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["project_id"], pid)
        self.assertEqual(rows[0]["workflow_status"], "new")

    def test_mark_project_opened_sets_in_progress(self) -> None:
        pid = self._save("Beta Tower")
        mark_project_opened(pid, self.db_path)
        row = get_project_workflow_row(pid, self.db_path)
        self.assertEqual(row["workflow_status"], STATUS_IN_PROGRESS)
        self.assertTrue(row["project_opened_at"])

    def test_mark_project_completed_sets_timing(self) -> None:
        pid = self._save("Gamma Tower")
        mark_project_opened(pid, self.db_path)
        mark_project_completed(pid, self.db_path)
        row = get_project_workflow_row(pid, self.db_path)
        self.assertEqual(row["workflow_status"], STATUS_COMPLETED)
        self.assertTrue(row["completed_at"])
        self.assertIsNotNone(row["total_time_taken_seconds"])

    def test_delete_only_selected_project(self) -> None:
        pid1 = self._save("One")
        pid2 = self._save("Two")
        self.assertTrue(remove_project(pid1, db_path=self.db_path))
        rows = list_dashboard_projects(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["project_id"], pid2)

    def test_delete_logs_audit_event(self) -> None:
        pid = self._save("Audit Me", engineer="Sachin")
        remove_project(pid, username="admin", db_path=self.db_path)
        conn_rows = []
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT event_type, project_id, project_name FROM audit_log")
        conn_rows = cur.fetchall()
        conn.close()
        self.assertEqual(conn_rows[0][0], "project_deleted")
        self.assertEqual(conn_rows[0][1], pid)

    def test_engineer_filter_updates_statistics(self) -> None:
        self._save("Akash Project", engineer="Akash")
        self._save("Sachin Project", engineer="Sachin")
        rows = list_dashboard_projects(self.db_path)
        stats = compute_statistics(rows_for_stats(rows, engineer="Akash"))
        self.assertEqual(stats["total"], 1)


class TestProjectHomeUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            from ui.dashboard import MainDashboard

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.MainDashboard = MainDashboard
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_dashboard_builds_without_quick_start(self) -> None:
        source = inspect.getsource(self.MainDashboard._build)
        self.assertNotIn("Quick Start", source)
        self.assertIn("+ New Project", source)
        self.assertIn("PROJECT OVERVIEW", source)

    def test_dashboard_has_six_stat_cards_in_one_row(self) -> None:
        page = self.MainDashboard(self.root, on_new_project=lambda: None, on_open_project=lambda _id: None, on_exit=lambda: None)
        page.update_idletasks()
        self.assertEqual(len(page._stat_labels), 6)
        self.assertIn("total", page._stat_labels)
        self.assertIn("delayed", page._stat_labels)
        self.assertIn("today", page._stat_labels)

    def test_dashboard_has_no_page_level_scroll(self) -> None:
        source = inspect.getsource(self.MainDashboard._build)
        self.assertNotIn("CTkScrollableFrame", source)

    def test_project_hub_has_filters_and_compact_table(self) -> None:
        page = self.MainDashboard(self.root, on_new_project=lambda: None, on_open_project=lambda _id: None, on_exit=lambda: None)
        page.update_idletasks()
        hub = page.project_hub
        self.assertIsNotNone(hub)
        self.assertTrue(hasattr(hub, "engineer_combo"))
        self.assertTrue(hasattr(hub, "status_combo"))
        self.assertTrue(hasattr(hub, "search_entry"))
        self.assertTrue(hasattr(hub, "_show_performance_dialog"))
        self.assertEqual(len(hub._header_columns), 9)
        column_names = [name for name, _width in hub._header_columns]
        self.assertIn("Client", column_names)
        self.assertIn("Project ID", column_names)
        self.assertFalse(hasattr(hub, "performance_frame"))


class TestProjectTypeSwitchingStillWorks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from app_launcher import Application

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.Application = Application
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def _find_widget(self, parent, widget_type):
        if isinstance(parent, widget_type):
            return parent
        for child in parent.winfo_children():
            found = self._find_widget(child, widget_type)
            if found is not None:
                return found
        return None

    def test_new_project_still_opens_type_selector(self) -> None:
        app = self.Application()
        app.withdraw()
        app._show_dashboard()
        app.update_idletasks()
        app._start_new_project()
        app.update_idletasks()
        self.assertIsNotNone(app._type_selector)
        from ui.components.type_selector import ProjectTypeSelector

        selector = self._find_widget(app._type_selector, ProjectTypeSelector)
        self.assertIsNotNone(selector)


if __name__ == "__main__":
    unittest.main()
