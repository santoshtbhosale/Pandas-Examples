"""Tests for one-click project type selection."""

from __future__ import annotations

import inspect
import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


class TestOneClickTypeSelection(unittest.TestCase):
    def test_type_selector_has_four_column_grid(self) -> None:
        from ui import components

        source = inspect.getsource(components.type_selector.ProjectTypeSelector._build)
        self.assertIn("GRID_COLUMNS", source)
        self.assertEqual(components.type_selector.GRID_COLUMNS, 4)

    def test_type_selector_one_click_callback(self) -> None:
        from ui.components import type_selector

        source = inspect.getsource(type_selector.ProjectTypeSelector)
        self.assertIn("on_project_type_selected", source)
        self.assertIn("select_type", source)

    def test_app_launcher_has_select_project_type(self) -> None:
        from app_launcher import Application

        self.assertTrue(hasattr(Application, "select_project_type"))

    def test_no_continue_button_in_type_selector_ui(self) -> None:
        from app_launcher import Application

        source = inspect.getsource(Application._show_project_type_selector)
        self.assertNotIn("Continue →", source)
        self.assertIn("select_project_type", source)


if __name__ == "__main__":
    unittest.main()
