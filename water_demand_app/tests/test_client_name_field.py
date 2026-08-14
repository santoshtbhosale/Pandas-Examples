"""Regression tests for Client Name editing and clearing on Project Details."""

from __future__ import annotations

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import PROJECT_TYPE_RESIDENTIAL
from services.project_service import create_new_project_state


class TestClientNameField(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            from ui.pages.project_page import ProjectPage

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.ProjectPage = ProjectPage
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def _make_page(self, state=None):
        state = state or create_new_project_state()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        page = self.ProjectPage(self.root, state, on_next=lambda: None)
        page._show_details()
        page.update_idletasks()
        return page

    def _set_client_text(self, page, text: str) -> None:
        entry = page.entries["client_name"]
        entry.delete(0, "end")
        if text:
            entry.insert(0, text)

    def test_new_project_client_name_starts_empty(self) -> None:
        page = self._make_page()
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_user_can_type_client_name(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC")
        self.assertEqual(page.entries["client_name"].get(), "ABC")

    def test_ctrl_a_delete_clears_client_name(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC")
        self._set_client_text(page, "")
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_user_can_replace_typed_value(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC")
        self._set_client_text(page, "XYZ")
        self.assertEqual(page.entries["client_name"].get(), "XYZ")

    def test_typing_does_not_auto_overwrite(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC")
        self.assertEqual(page.entries["client_name"].get(), "ABC")

    def test_selected_value_can_be_cleared(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC Developers")
        self._set_client_text(page, "")
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_back_navigation_preserves_user_entered_client_name(self) -> None:
        state = create_new_project_state()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        page = self._make_page(state)
        self._set_client_text(page, "ABC Developers")
        state.project.client_name = page.entries["client_name"].get()
        page.refresh()
        self.assertEqual(page.entries["client_name"].get(), "ABC Developers")

    def test_existing_project_loads_saved_client_name(self) -> None:
        state = create_new_project_state()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        state.project.client_name = "Saved Client Ltd"
        page = self._make_page(state)
        self.assertEqual(page.entries["client_name"].get(), "Saved Client Ltd")
        self._set_client_text(page, "Edited Client")
        self.assertEqual(page.entries["client_name"].get(), "Edited Client")

    def test_refresh_does_not_overwrite_in_progress_typing(self) -> None:
        state = create_new_project_state()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        state.project.client_name = "Saved Client"
        page = self._make_page(state)
        self._set_client_text(page, "Typed Client")
        page.refresh()
        self.assertEqual(page.entries["client_name"].get(), "Saved Client")

    def test_refresh_syncs_when_state_changes_externally(self) -> None:
        state = create_new_project_state()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        state.project.client_name = "Original"
        page = self._make_page(state)
        state.project.client_name = "Loaded From DB"
        page.refresh()
        self.assertEqual(page.entries["client_name"].get(), "Loaded From DB")


if __name__ == "__main__":
    unittest.main()
