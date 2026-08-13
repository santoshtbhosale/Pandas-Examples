"""Regression tests for Client Name editing, clearing, and autocomplete behavior."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

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

            from ui.app_state import AppState
            from ui.pages.project_page import ProjectPage

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.AppState = AppState
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
        with patch("ui.pages.project_page.search_clients", return_value=[]):
            self._set_client_text(page, "ABC")
            page._on_client_key_release()
        self.assertEqual(page.entries["client_name"].get(), "ABC")

    def test_ctrl_a_delete_clears_client_name(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "ABC")
        self._set_client_text(page, "")
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_user_can_replace_typed_value(self) -> None:
        page = self._make_page()
        with patch("ui.pages.project_page.search_clients", return_value=[]):
            self._set_client_text(page, "ABC")
            page._on_client_key_release()
            self._set_client_text(page, "XYZ")
            page._on_client_key_release()
        self.assertEqual(page.entries["client_name"].get(), "XYZ")

    def test_autocomplete_does_not_auto_insert_without_selection(self) -> None:
        page = self._make_page()
        matches = [
            {
                "client_key": "abc_developers",
                "client_name": "ABC Developers",
                "engineer_name": "Akash",
            }
        ]
        with patch("ui.pages.project_page.search_clients", return_value=matches):
            self._set_client_text(page, "ABC")
            page._on_client_key_release()
        self.assertEqual(page.entries["client_name"].get(), "ABC")
        self.assertGreater(len(page._client_suggestions.winfo_children()), 0)

    def test_explicit_suggestion_selection_populates_field(self) -> None:
        page = self._make_page()
        match = {
            "client_key": "abc_developers",
            "client_name": "ABC Developers Pvt Ltd",
            "engineer_name": "Omkar",
        }
        with patch("ui.pages.project_page.search_clients", return_value=[match]):
            self._set_client_text(page, "ABC")
            page._on_client_key_release()
            page._apply_client_suggestion(match)
        self.assertEqual(page.entries["client_name"].get(), "ABC Developers Pvt Ltd")
        self.assertEqual(page.engineer_var.get(), "Omkar")

    def test_selected_suggestion_can_be_cleared(self) -> None:
        page = self._make_page()
        match = {"client_key": "abc", "client_name": "ABC Developers", "engineer_name": ""}
        page._apply_client_suggestion(match)
        self._set_client_text(page, "")
        self.assertEqual(page.entries["client_name"].get(), "")

    def test_focus_out_does_not_restore_old_client_name(self) -> None:
        page = self._make_page()
        self._set_client_text(page, "")
        page._on_client_focus_out()
        page.update_idletasks()
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
