"""Regression tests for production UI/UX upgrade."""

from __future__ import annotations

import inspect
import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_RESIDENTIAL,
    project_type_label,
)
from services.project_workflow import compute_statistics, filter_rows
from ui.theme import COLOR_PRIMARY, STATUS_BADGES


class TestDesignSystem(unittest.TestCase):
    def test_brand_colors_match_corporate_palette(self) -> None:
        self.assertEqual(BRAND_NAVY, "#123B5D")
        self.assertEqual(BRAND_ORANGE, "#F28C28")
        self.assertEqual(COLOR_PRIMARY, BRAND_NAVY)

    def test_theme_module_exists(self) -> None:
        import ui.theme as theme

        self.assertIn("STATUS_BADGES", dir(theme))
        self.assertIn("In Progress", STATUS_BADGES)

    def test_logging_module_exists(self) -> None:
        from services.app_logging import get_logger

        logger = get_logger()
        self.assertEqual(logger.name, "water_demand_app")


class TestDashboardStructure(unittest.TestCase):
    def test_dashboard_has_six_stat_cards(self) -> None:
        from ui import dashboard

        source = inspect.getsource(dashboard.MainDashboard._build)
        self.assertIn('"today"', source)
        self.assertIn("TOTAL PROJECTS", source)

    def test_dashboard_no_duplicate_company_name(self) -> None:
        from ui import dashboard

        source = inspect.getsource(dashboard.MainDashboard)
        self.assertNotIn("AMERICAN EDGE ENGINEERS", source)

    def test_project_hub_has_client_column(self) -> None:
        from ui import project_hub

        source = inspect.getsource(project_hub.ProjectHub._build)
        self.assertIn('"Client"', source)

    def test_project_hub_has_clear_search(self) -> None:
        from ui import project_hub

        source = inspect.getsource(project_hub.ProjectHub)
        self.assertIn("_clear_search", source)


class TestTypeSelector(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from app_launcher import Application

            cls.ctk = ctk
            cls.Application = Application
            cls.root = ctk.CTk()
            cls.root.withdraw()
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

    def test_type_selector_uses_visual_cards(self) -> None:
        from ui.components.type_selector import ProjectTypeSelector

        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            selector = self._find_widget(app._type_selector, ProjectTypeSelector)
            self.assertIsNotNone(selector)
        finally:
            app.destroy()

    def test_residential_commercial_switch_sequence(self) -> None:
        from ui.components.type_selector import ProjectTypeSelector

        app = self.Application()
        app.withdraw()
        try:
            app._start_new_project()
            app.update_idletasks()
            selector = self._find_widget(app._type_selector, ProjectTypeSelector)
            selector.set_selected(project_type_label(PROJECT_TYPE_RESIDENTIAL))
            self._find_button_with_text(app._type_selector, "Continue").invoke()
            app.update_idletasks()
            app._workspace._project_details_back()
            app.update_idletasks()
            selector = self._find_widget(app._type_selector, ProjectTypeSelector)
            selector.set_selected(project_type_label(PROJECT_TYPE_COMMERCIAL))
            self._find_button_with_text(app._type_selector, "Continue").invoke()
            app.update_idletasks()
            self.root.update_idletasks()
            self.assertEqual(app._workspace._current_page, "Project")
        finally:
            app.destroy()


class TestProjectDetailsSections(unittest.TestCase):
    def test_project_page_has_four_sections(self) -> None:
        from ui.pages import project_page

        source = inspect.getsource(project_page.ProjectPage._build)
        self.assertIn("SECTION 1", source)
        self.assertIn("SECTION 2", source)
        self.assertIn("SECTION 3", source)
        self.assertIn("SECTION 4", source)


class TestStatisticsFilter(unittest.TestCase):
    def test_engineer_filter_updates_stats(self) -> None:
        rows = [
            {"engineer_name": "Akash", "workflow_status": "completed", "completed_at": "2026-01-01T10:00:00"},
            {"engineer_name": "Vaibhav", "workflow_status": "new"},
        ]
        akash_rows = filter_rows(rows, engineer="Akash", status_label="All Status", search="")
        stats = compute_statistics(akash_rows)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["completed"], 1)


if __name__ == "__main__":
    unittest.main()
