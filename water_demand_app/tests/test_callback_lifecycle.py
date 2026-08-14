"""Regression tests for safe page callback lifecycle during navigation."""

from __future__ import annotations

import os
import sys
import time
import unittest
from tkinter import messagebox

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import (
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
    PROJECT_TYPE_WAREHOUSE,
    project_type_label,
)
from services.project_service import create_new_project_state
from ui.components.scrollable_frame import ScrollablePage
from ui.scheduled_callbacks import widget_is_alive


class _ErrorCollector:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def install(self, root) -> None:
        def report_callback_exception(_self, _exc, val, _tb) -> None:
            self.errors.append(str(val))

        root.report_callback_exception = report_callback_exception

        self._orig_showerror = messagebox.showerror

        def catch_showerror(title, msg, **kwargs) -> None:
            self.errors.append(f"{title}: {msg}")

        messagebox.showerror = catch_showerror  # type: ignore[assignment]

    def restore(self) -> None:
        messagebox.showerror = self._orig_showerror  # type: ignore[assignment]


class TestScrollablePageLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_destroyed_page_does_not_run_after_idle_resize(self) -> None:
        parent = self.ctk.CTkFrame(self.root)
        parent.pack(fill="both", expand=True)
        page = ScrollablePage(parent)
        page.update_idletasks()
        page.cancel_pending_callbacks()
        page.destroy()
        self.root.update_idletasks()
        self.assertFalse(widget_is_alive(page))

    def test_schedule_auto_calculate_ignored_after_destroy(self) -> None:
        from ui.app_state import AppState

        parent = self.ctk.CTkFrame(self.root)
        page = ScrollablePage(parent)
        state = AppState()
        page.schedule_auto_calculate(state, delay_ms=10)
        page.cancel_pending_callbacks()
        page.destroy()
        self.root.update_idletasks()
        self.assertFalse(widget_is_alive(page))

    def test_prepare_for_destroy_cancels_tracked_after_jobs(self) -> None:
        from ui.app_state import AppState

        parent = self.ctk.CTkFrame(self.root)
        page = ScrollablePage(parent)
        state = AppState()
        fired: list[str] = []

        def on_done() -> None:
            fired.append("done")

        page.schedule_auto_calculate(state, delay_ms=200, callback=on_done)
        page.prepare_for_destroy()
        for _ in range(30):
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(fired, [])
        page.destroy()


class TestProjectTypeNavigationCallbacks(unittest.TestCase):
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

    def setUp(self) -> None:
        self.collector = _ErrorCollector()
        self.collector.install(self.root)

    def tearDown(self) -> None:
        self.collector.restore()

    def _find_widget(self, parent, widget_type):
        if isinstance(parent, widget_type):
            return parent
        for child in parent.winfo_children():
            found = self._find_widget(child, widget_type)
            if found is not None:
                return found
        return None

    def _select_type(self, app, label: str) -> None:
        from ui.components.type_selector import ProjectTypeSelector

        selector = self._find_widget(app._type_selector, ProjectTypeSelector)
        self.assertIsNotNone(selector)
        selector.select_type(label)
        app.update_idletasks()

    def _pump_events(self, app, iterations: int = 120) -> None:
        for _ in range(iterations):
            self.root.update()
            app.update_idletasks()
            time.sleep(0.01)

    def _assert_no_invalid_command_errors(self) -> None:
        for err in self.collector.errors:
            self.assertNotIn("invalid command name", err.lower(), msg=err)

    def _open_new_project(self, app) -> None:
        app._start_new_project()
        app.update_idletasks()
        self.assertIsNotNone(app._type_selector)

    def _back_to_type_selector(self, app) -> None:
        app._workspace._project_details_back()
        app.update_idletasks()
        self.assertIsNotNone(app._type_selector)

    def test_residential_to_commercial_switch_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, project_type_label(PROJECT_TYPE_RESIDENTIAL))
            self._back_to_type_selector(app)
            self._select_type(app, project_type_label(PROJECT_TYPE_COMMERCIAL))
            self._pump_events(app)
            page = app._workspace.pages["Project"]
            self.assertTrue(widget_is_alive(page))
            self.assertEqual(app._workspace._current_page, "Project")
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_project_details_next_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, project_type_label(PROJECT_TYPE_COMMERCIAL))
            page = app._workspace.pages["Project"]
            page.entries["project_name"].delete(0, "end")
            page.entries["project_name"].insert(0, "TEST PROJECT")
            page.entries["client_name"].delete(0, "end")
            page.entries["client_name"].insert(0, "TEST CLIENT")
            app._workspace._wizard_show_next("Project")
            self._pump_events(app)
            self.assertNotEqual(app._workspace._current_page, "Project")
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_warehouse_type_navigation_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, project_type_label(PROJECT_TYPE_WAREHOUSE))
            self._pump_events(app)
            page = app._workspace.pages["Project"]
            self.assertTrue(widget_is_alive(page))
            self.assertEqual(app._workspace._current_page, "Project")
            self.assertTrue(page._details_visible)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_apply_state_cancels_old_page_callbacks(self) -> None:
        from _app_sidebar import ProjectWorkspace
        from ui.app_state import AppState

        workspace = ProjectWorkspace(self.root, initial_state=AppState())
        workspace.update_idletasks()
        workspace.apply_state(create_new_project_state())
        workspace.update_idletasks()
        old_page = workspace.pages.get("Project")
        workspace.apply_state(create_new_project_state())
        self._pump_events(workspace)
        if old_page is not None:
            self.assertFalse(widget_is_alive(old_page))
        self.assertTrue(widget_is_alive(workspace.pages["Project"]))

    def test_sequence_1_residential_back_commercial(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Residential")
            self._back_to_type_selector(app)
            self._select_type(app, "Commercial")
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_sequence_2_commercial_back_residential(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Commercial")
            self._back_to_type_selector(app)
            self._select_type(app, "Residential")
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_sequence_3_residential_back_residential(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Residential")
            self._back_to_type_selector(app)
            self._select_type(app, "Residential")
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_sequence_4_continue_back_reselect_commercial(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Residential")
            page = app._workspace.pages["Project"]
            page.entries["project_name"].delete(0, "end")
            page.entries["project_name"].insert(0, "SEQ4 PROJECT")
            page.entries["client_name"].delete(0, "end")
            page.entries["client_name"].insert(0, "SEQ4 CLIENT")
            app._workspace._wizard_show_next("Project")
            app.update_idletasks()
            app._workspace.show("Project")
            self._back_to_type_selector(app)
            self._select_type(app, "Commercial")
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_sequence_5_residential_back_commercial_back_mixed_use(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Residential")
            self._back_to_type_selector(app)
            self._select_type(app, "Commercial")
            self._back_to_type_selector(app)
            self._select_type(app, "Mixed Use")
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_back_next_alternation_without_orphan_callbacks(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            self._select_type(app, "Residential")
            ws = app._workspace
            for _ in range(4):
                ws._wizard_show_next("Project")
                app.update_idletasks()
                ws.show("Project")
                app.update_idletasks()
            self._pump_events(app)
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()

    def test_reselect_does_not_accumulate_after_jobs(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project(app)
            for label in ("Residential", "Commercial", "Residential"):
                self._select_type(app, label)
                self._back_to_type_selector(app)
            self._select_type(app, "Commercial")
            self._pump_events(app)
            page = app._workspace.pages["Project"]
            self.assertTrue(hasattr(page, "_after_jobs"))
            self.assertEqual(page._after_jobs, [])
            self._assert_no_invalid_command_errors()
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
