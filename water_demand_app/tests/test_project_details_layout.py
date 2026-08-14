"""Regression tests for Project Details page layout."""

from __future__ import annotations

import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL
from services.project_service import create_new_project_state
from ui.app_state import AppState
from ui.pages.project_page import ProjectPage


class TestProjectDetailsLayout(unittest.TestCase):
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

    def _build_page(self, project_type: str = PROJECT_TYPE_RESIDENTIAL) -> ProjectPage:
        state = create_new_project_state()
        state.project.project_type = project_type
        page = ProjectPage(self.root, state, on_next=lambda: None)
        page._show_details()
        page.update_idletasks()
        return page

    def _form_entries(self, page: ProjectPage):
        entries = []
        for child in page.form.winfo_children():
            if isinstance(child, self.ctk.CTkEntry):
                entries.append(child)
        return entries

    def _entry_grid_row(self, entry) -> int:
        return int(entry.grid_info().get("row", -1))

    def test_only_two_labeled_text_entries(self) -> None:
        page = self._build_page()
        self.assertEqual(set(page.entries.keys()), {"project_name", "client_name"})
        self.assertEqual(len(self._form_entries(page)), 4)

    def test_project_name_and_client_name_are_adjacent_sections(self) -> None:
        page = self._build_page()
        project_row = self._entry_grid_row(page.entries["project_name"])
        client_row = self._entry_grid_row(page.entries["client_name"])
        self.assertLess(project_row, client_row)
        self.assertEqual(client_row - project_row, 3)

    def test_no_client_suggestions_wrapper(self) -> None:
        page = self._build_page()
        self.assertFalse(hasattr(page, "_client_suggestions"))

    def test_new_project_client_name_starts_empty(self) -> None:
        page = self._build_page()
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_client_name_can_be_typed_cleared_and_replaced(self) -> None:
        page = self._build_page()
        entry = page.entries["client_name"]
        entry.delete(0, "end")
        entry.insert(0, "ABC Developers")
        self.assertEqual(entry.get(), "ABC Developers")
        entry.delete(0, "end")
        self.assertEqual(entry.get(), "")
        entry.insert(0, "XYZ Constructions")
        self.assertEqual(entry.get(), "XYZ Constructions")

    def test_small_numeric_fields_use_compact_width(self) -> None:
        page = self._build_page()
        self.assertLessEqual(int(page.height_entry.cget("width")), 140)
        self.assertLessEqual(int(page.wings_entry.cget("width")), 140)

    def test_commercial_hides_engineering_without_large_gap_rows(self) -> None:
        page = self._build_page(PROJECT_TYPE_COMMERCIAL)
        self.assertFalse(page.section_rows_visible(page._engineering_start_row, page._engineering_end_row))
        self.assertTrue(page.section_rows_visible(page._signoff_start_row, page._signoff_end_row))
        signoff_header = page._signoff_widgets[0]
        signoff_row = int(signoff_header.grid_info().get("row", 99))
        self.assertLess(signoff_row, 16)

    def test_signoff_visible_for_commercial(self) -> None:
        page = self._build_page(PROJECT_TYPE_COMMERCIAL)
        self.assertTrue(hasattr(page, "engineer_var"))
        self.assertTrue(page.section_rows_visible(page._signoff_start_row, page._signoff_end_row))


if __name__ == "__main__":
    unittest.main()
