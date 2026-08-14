"""Tests for Phase-3 smart dynamic UI."""

import os
import sys
import unittest

APP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL, is_project_type_set
from config.page_visibility import visible_pages
from services.project_service import create_new_project_state


class TestSmartDynamicUI(unittest.TestCase):
    def test_new_project_starts_without_type(self) -> None:
        state = create_new_project_state()
        self.assertFalse(is_project_type_set(state.project.project_type))
        pages = visible_pages(state.project.project_type)
        self.assertEqual(pages, frozenset({"Project"}))

    def test_residential_unlocks_residential_tab_only(self) -> None:
        pages = visible_pages(PROJECT_TYPE_RESIDENTIAL)
        self.assertIn("Residential", pages)
        self.assertNotIn("Commercial", pages)
        self.assertNotIn("HVAC", pages)

    def test_commercial_unlocks_commercial_and_hvac(self) -> None:
        pages = visible_pages(PROJECT_TYPE_COMMERCIAL)
        self.assertIn("Commercial", pages)
        self.assertIn("HVAC", pages)
        self.assertNotIn("Residential", pages)


if __name__ == "__main__":
    unittest.main()
