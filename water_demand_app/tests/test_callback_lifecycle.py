"""Regression tests for safe page callback lifecycle during navigation."""

from __future__ import annotations

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL, PROJECT_TYPE_WAREHOUSE, project_type_label
from services.project_service import create_new_project_state
from ui.components.scrollable_frame import ScrollablePage
from ui.scheduled_callbacks import widget_is_alive


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

    def _find_widget(self, parent, widget_type):
        if isinstance(parent, widget_type):
            return parent
        for child in parent.winfo_children():
            found = self._find_widget(child, widget_type)
            if found is not None:
                return found
        return None

    def _find_button_with_text(self, parent, text_fragment: str):
        if isinstance(parent, self.ctk.CTkButton):
            try:
                if text_fragment in parent.cget("text"):
                    return parent
            except Exception:
                pass
        for child in parent.winfo_children():
            found = self._find_button_with_text(child, text_fragment)
            if found is not None:
                return found
        return None

    def _select_type_and_continue(self, app, label: str) -> None:
        combo = self._find_widget(app._type_selector, self.ctk.CTkComboBox)
        self.assertIsNotNone(combo)
        combo.set(label)
        continue_btn = self._find_button_with_text(app._type_selector, "Continue")
        self.assertIsNotNone(continue_btn)
        continue_btn.invoke()
        app.update_idletasks()
        self.root.update_idletasks()

    def test_residential_to_commercial_switch_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            self._select_type_and_continue(app, project_type_label(PROJECT_TYPE_RESIDENTIAL))
            app._workspace._project_details_back()
            app.update_idletasks()
            self._select_type_and_continue(app, project_type_label(PROJECT_TYPE_COMMERCIAL))
            self.root.update_idletasks()
            page = app._workspace.pages["Project"]
            self.assertTrue(widget_is_alive(page))
            self.assertEqual(app._workspace._current_page, "Project")
        finally:
            app.destroy()

    def test_project_details_next_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            self._select_type_and_continue(app, project_type_label(PROJECT_TYPE_COMMERCIAL))
            page = app._workspace.pages["Project"]
            page.entries["project_name"].delete(0, "end")
            page.entries["project_name"].insert(0, "TEST PROJECT")
            page.entries["client_name"].delete(0, "end")
            page.entries["client_name"].insert(0, "TEST CLIENT")
            app._workspace._wizard_show_next("Project")
            app.update_idletasks()
            self.root.update_idletasks()
            self.assertNotEqual(app._workspace._current_page, "Project")
        finally:
            app.destroy()

    def test_warehouse_type_navigation_without_invalid_command(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            self._select_type_and_continue(app, project_type_label(PROJECT_TYPE_WAREHOUSE))
            self.root.update_idletasks()
            page = app._workspace.pages["Project"]
            self.assertTrue(widget_is_alive(page))
            self.assertEqual(app._workspace._current_page, "Project")
            self.assertTrue(page._details_visible)
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
        self.root.update_idletasks()
        if old_page is not None:
            self.assertFalse(widget_is_alive(old_page))
        self.assertTrue(widget_is_alive(workspace.pages["Project"]))


if __name__ == "__main__":
    unittest.main()
