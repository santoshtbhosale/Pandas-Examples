"""Regression tests for Project Details section visibility rules."""

from __future__ import annotations

import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config.nbc_2026 import (
    PROJECT_TYPE_COLLEGE,
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_HOSPITAL,
    PROJECT_TYPE_HOTEL,
    PROJECT_TYPE_INDUSTRIAL,
    PROJECT_TYPE_IT_PARK,
    PROJECT_TYPE_MALL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
    PROJECT_TYPE_SCHOOL,
    PROJECT_TYPE_TOWNSHIP,
    PROJECT_TYPE_WAREHOUSE,
)
from ui.app_state import AppState
from ui.pages.project_page import (
    ProjectPage,
    show_project_engineering_configuration,
    show_report_signoff,
)


ALL_PROJECT_TYPES = (
    PROJECT_TYPE_RESIDENTIAL,
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_TOWNSHIP,
    PROJECT_TYPE_HOSPITAL,
    PROJECT_TYPE_HOTEL,
    PROJECT_TYPE_SCHOOL,
    PROJECT_TYPE_COLLEGE,
    PROJECT_TYPE_MALL,
    PROJECT_TYPE_IT_PARK,
    PROJECT_TYPE_INDUSTRIAL,
    PROJECT_TYPE_WAREHOUSE,
)

ENGINEERING_CONFIG_TYPES = {
    PROJECT_TYPE_RESIDENTIAL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_TOWNSHIP,
}


class TestProjectDetailsSectionVisibility(unittest.TestCase):
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

    def _build_page(self, project_type: str) -> ProjectPage:
        state = AppState()
        state.project.project_type = project_type
        page = ProjectPage(self.root, state, on_next=lambda: None)
        page._show_details()
        page.update_idletasks()
        return page

    def test_report_signoff_helper_always_true(self) -> None:
        for project_type in ALL_PROJECT_TYPES:
            with self.subTest(project_type=project_type):
                self.assertTrue(show_report_signoff(project_type))

    def test_engineering_config_helper_matches_criteria(self) -> None:
        for project_type in ALL_PROJECT_TYPES:
            with self.subTest(project_type=project_type):
                expected = project_type in ENGINEERING_CONFIG_TYPES
                self.assertEqual(show_project_engineering_configuration(project_type), expected)

    def test_report_signoff_visible_for_all_project_types(self) -> None:
        for project_type in ALL_PROJECT_TYPES:
            with self.subTest(project_type=project_type):
                page = self._build_page(project_type)
                self.assertTrue(
                    page.section_rows_visible(page._signoff_start_row, page._signoff_end_row),
                    f"Report Sign-off must be visible for {project_type}",
                )
                self.assertTrue(hasattr(page, "engineer_var"))
                self.assertTrue(hasattr(page, "prepared_var"))
                self.assertTrue(hasattr(page, "checked_var"))
                self.assertTrue(hasattr(page, "approved_var"))

    def test_engineering_configuration_visibility_by_type(self) -> None:
        for project_type in ALL_PROJECT_TYPES:
            with self.subTest(project_type=project_type):
                page = self._build_page(project_type)
                expected = project_type in ENGINEERING_CONFIG_TYPES
                actual = page.section_rows_visible(
                    page._engineering_start_row,
                    page._engineering_end_row,
                )
                self.assertEqual(
                    actual,
                    expected,
                    f"Engineering Configuration visibility mismatch for {project_type}",
                )

    def test_engineering_rows_do_not_include_signoff_rows(self) -> None:
        page = self._build_page(PROJECT_TYPE_COMMERCIAL)
        self.assertLess(page._engineering_end_row, page._signoff_start_row)

    def test_refresh_reapplies_visibility_after_type_change(self) -> None:
        page = self._build_page(PROJECT_TYPE_RESIDENTIAL)
        self.assertTrue(
            page.section_rows_visible(page._engineering_start_row, page._engineering_end_row)
        )
        page.state.project.project_type = PROJECT_TYPE_COMMERCIAL
        page.refresh()
        page.update_idletasks()
        self.assertFalse(
            page.section_rows_visible(page._engineering_start_row, page._engineering_end_row)
        )
        self.assertTrue(
            page.section_rows_visible(page._signoff_start_row, page._signoff_end_row)
        )

    def test_commercial_signoff_visible_engineering_hidden(self) -> None:
        page = self._build_page(PROJECT_TYPE_COMMERCIAL)
        self.assertFalse(
            page.section_rows_visible(page._engineering_start_row, page._engineering_end_row)
        )
        self.assertTrue(
            page.section_rows_visible(page._signoff_start_row, page._signoff_end_row)
        )


class TestProjectDetailsNavigationWithSections(unittest.TestCase):
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
        from ui.components.type_selector import ProjectTypeSelector

        selector = self._find_widget(app._type_selector, ProjectTypeSelector)
        self.assertIsNotNone(selector)
        selector.select_type(label)
        app.update_idletasks()

    def test_residential_to_commercial_preserves_signoff_visibility(self) -> None:
        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            self._select_type_and_continue(app, "Residential")
            app._workspace._project_details_back()
            app.update_idletasks()
            self._select_type_and_continue(app, "Commercial")
            page = app._workspace.pages["Project"]
            page._show_details()
            page.update_idletasks()
            self.assertFalse(
                page.section_rows_visible(page._engineering_start_row, page._engineering_end_row)
            )
            self.assertTrue(
                page.section_rows_visible(page._signoff_start_row, page._signoff_end_row)
            )
            app._workspace._wizard_show_next("Project")
            app.update_idletasks()
            self.assertEqual(app._workspace._current_page, "Commercial")
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
