"""Unit tests for project-type page visibility and wizard flow."""

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(WORKSPACE_ROOT, "water_demand_app"))

from config.nbc_2026 import (
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_HOSPITAL,
    PROJECT_TYPE_HOTEL,
    PROJECT_TYPE_MALL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
)
from config.page_visibility import visible_pages, wizard_first_page_after_project, wizard_next_page


class TestPageVisibility(unittest.TestCase):
    def test_residential_hides_commercial(self) -> None:
        pages = visible_pages(PROJECT_TYPE_RESIDENTIAL)
        self.assertIn("Residential", pages)
        self.assertNotIn("Commercial", pages)
        self.assertNotIn("HVAC", pages)

    def test_commercial_shows_hvac(self) -> None:
        pages = visible_pages(PROJECT_TYPE_COMMERCIAL)
        self.assertIn("Commercial", pages)
        self.assertIn("HVAC", pages)
        self.assertNotIn("Residential", pages)

    def test_hospital_shows_hospital_page(self) -> None:
        pages = visible_pages(PROJECT_TYPE_HOSPITAL)
        self.assertIn("Hospital", pages)
        self.assertNotIn("Residential", pages)
        self.assertNotIn("Commercial", pages)

    def test_hotel_shows_swimming(self) -> None:
        pages = visible_pages(PROJECT_TYPE_HOTEL)
        self.assertIn("Hotel", pages)
        self.assertIn("Swimming", pages)

    def test_mall_shows_food_court(self) -> None:
        pages = visible_pages(PROJECT_TYPE_MALL)
        self.assertIn("FoodCourt", pages)
        self.assertIn("HVAC", pages)

    def test_mixed_shows_residential_and_commercial(self) -> None:
        pages = visible_pages(PROJECT_TYPE_MIXED)
        self.assertIn("Residential", pages)
        self.assertIn("Commercial", pages)

    def test_wizard_first_page_residential(self) -> None:
        self.assertEqual(wizard_first_page_after_project(PROJECT_TYPE_RESIDENTIAL), "Residential")

    def test_wizard_first_page_hospital(self) -> None:
        self.assertEqual(wizard_first_page_after_project(PROJECT_TYPE_HOSPITAL), "Hospital")

    def test_wizard_next_from_residential_commercial(self) -> None:
        nxt = wizard_next_page("Residential", PROJECT_TYPE_MIXED)
        self.assertEqual(nxt, "Commercial")

    def test_wizard_next_from_commercial_residential_only(self) -> None:
        nxt = wizard_next_page("Commercial", PROJECT_TYPE_COMMERCIAL)
        self.assertEqual(nxt, "Landscape")

    def test_unset_type_shows_only_project_tab(self) -> None:
        pages = visible_pages("")
        self.assertEqual(pages, frozenset({"Project"}))
        self.assertNotIn("Residential", pages)
        self.assertNotIn("Commercial", pages)

    def test_unset_wizard_first_page_is_project(self) -> None:
        self.assertEqual(wizard_first_page_after_project(""), "Project")


if __name__ == "__main__":
    unittest.main()
