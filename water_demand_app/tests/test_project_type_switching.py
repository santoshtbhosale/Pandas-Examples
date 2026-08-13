"""Regression tests for project-type switching and wizard navigation."""

from __future__ import annotations

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import (
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
    project_type_key,
    project_type_label,
)
from services.project_service import create_new_project_state


class TestProjectTypeSwitching(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from app_launcher import Application
            from _app_sidebar import ProjectWorkspace
            from ui.app_state import AppState

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.AppState = AppState
            cls.ProjectWorkspace = ProjectWorkspace
            cls.Application = Application
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def _make_workspace(self):
        ws = self.ProjectWorkspace(self.root, initial_state=self.AppState())
        ws.update_idletasks()
        return ws

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
        self.assertIsNotNone(combo, "Project type combo not found")
        combo.set(label)
        continue_btn = self._find_button_with_text(app._type_selector, "Continue")
        self.assertIsNotNone(continue_btn, "Continue button not found on type selector")
        continue_btn.invoke()
        app.update_idletasks()

    def _open_new_project_to_details(self, app, project_type_label_text: str) -> None:
        app._start_new_project()
        app.update_idletasks()
        self.assertIsNotNone(app._type_selector)
        self._select_type_and_continue(app, project_type_label_text)
        app.update_idletasks()
        self.assertIsNone(app._type_selector)
        self.assertEqual(app._workspace._current_page, "Project")

    def _back_to_type_selector(self, app) -> None:
        app._workspace._project_details_back()
        app.update_idletasks()
        self.assertIsNotNone(app._type_selector)

    def _continue_from_type_selector(self, app, project_type_label_text: str) -> None:
        self._select_type_and_continue(app, project_type_label_text)
        app.update_idletasks()
        self.assertIsNone(app._type_selector)

    def _wizard_next_from_project(self, ws) -> None:
        ws._wizard_show_next("Project")
        ws.update_idletasks()

    def test_1_residential_to_commercial_after_back(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project_to_details(app, "Residential")
            self._back_to_type_selector(app)
            self._continue_from_type_selector(app, "Commercial")
            self.assertEqual(app._workspace.app_state.project.project_type, PROJECT_TYPE_COMMERCIAL)
            self._wizard_next_from_project(app._workspace)
            self.assertEqual(app._workspace._current_page, "Commercial")
        finally:
            app.destroy()

    def test_2_commercial_to_residential_after_back(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project_to_details(app, "Commercial")
            self._back_to_type_selector(app)
            self._continue_from_type_selector(app, "Residential")
            self.assertEqual(app._workspace.app_state.project.project_type, PROJECT_TYPE_RESIDENTIAL)
            self._wizard_next_from_project(app._workspace)
            self.assertEqual(app._workspace._current_page, "Residential")
        finally:
            app.destroy()

    def test_3_empty_details_switch_to_commercial(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project_to_details(app, "Residential")
            self._back_to_type_selector(app)
            self._continue_from_type_selector(app, "Commercial")
            self._wizard_next_from_project(app._workspace)
            self.assertEqual(app._workspace._current_page, "Commercial")
        finally:
            app.destroy()

    def test_4_partial_details_switch_to_commercial(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            self._open_new_project_to_details(app, "Residential")
            project_page = app._workspace.pages["Project"]
            project_page.entries["project_name"].delete(0, "end")
            project_page.entries["project_name"].insert(0, "PARTIAL TEST PROJECT")
            self._back_to_type_selector(app)
            self._continue_from_type_selector(app, "Commercial")
            self._wizard_next_from_project(app._workspace)
            self.assertEqual(app._workspace._current_page, "Commercial")
        finally:
            app.destroy()

    def test_5_multiple_type_switches(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            sequence = ["Residential", "Commercial", "Mixed Use", "Residential", "Commercial"]
            app._start_new_project()
            app.update_idletasks()
            for label in sequence:
                self._select_type_and_continue(app, label)
                app.update_idletasks()
                self.assertIsNone(app._type_selector)
                expected_key = project_type_key(label)
                self.assertEqual(app._workspace.app_state.project.project_type, expected_key)
                self._wizard_next_from_project(app._workspace)
                expected_next = "Residential" if label in ("Residential", "Mixed Use") else "Commercial"
                self.assertEqual(app._workspace._current_page, expected_next)
                self._back_to_type_selector(app)
        finally:
            app.destroy()

    def test_type_selector_destroyed_on_continue(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            state = create_new_project_state()
            app._show_project_type_selector(state)
            app.update_idletasks()
            selector = app._type_selector
            self.assertIsNotNone(selector)
            self._select_type_and_continue(app, "Residential")
            app.update_idletasks()
            self.assertIsNone(app._type_selector)
            self.assertFalse(selector.winfo_exists())
        finally:
            app.destroy()

    def test_apply_project_type_clears_residential_for_commercial(self) -> None:
        ws = self._make_workspace()
        try:
            state = ws.app_state
            state.project.project_type = PROJECT_TYPE_RESIDENTIAL
            state.load_defaults()
            self.assertTrue(state.residential)
            state.apply_project_type(PROJECT_TYPE_COMMERCIAL)
            self.assertEqual(state.project.project_type, PROJECT_TYPE_COMMERCIAL)
            self.assertEqual(state.residential, [])
        finally:
            ws.destroy()

    def test_workspace_back_callback_wired(self) -> None:
        called = []

        def on_back():
            called.append(True)

        ws = self.ProjectWorkspace(self.root, on_back_to_type_selector=on_back)
        ws.update_idletasks()
        try:
            ws.ensure_pages_built()
            ws._project_details_back()
            self.assertEqual(called, [True])
        finally:
            ws.destroy()


if __name__ == "__main__":
    unittest.main()
