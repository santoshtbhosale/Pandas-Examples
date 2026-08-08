"""Version 2.0 QA integration tests — workflow, access control, building parser."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

APP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import (
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_RESIDENTIAL,
    fire_tank_capacity_liters,
    parse_building_config,
)
from config.page_visibility import visible_pages as vp
from models.residential import ResidentialWing
from models.user import ROLE_ENGINEER
from services.auth_db import authenticate, init_users_table
from services.database import init_db
from services.project_service import (
    create_new_project_state,
    find_projects,
    load_project_state,
    persist_project_state,
)
from ui.app_state import AppState


class TestQAAuthFlow(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.db = os.path.join(self._tmpdir, "qa.db")
        init_db(self.db)
        init_users_table(self.db)

    def test_invalid_login_rejected(self) -> None:
        self.assertIsNone(authenticate("akash", "wrong", self.db))

    def test_valid_engineer_login(self) -> None:
        user = authenticate("akash", "Akash@123", self.db)
        self.assertIsNotNone(user)
        self.assertEqual(user.role, ROLE_ENGINEER)

    def test_viewer_cannot_launch(self) -> None:
        user = authenticate("omkar", "Omkar@123", self.db)
        self.assertIsNotNone(user)
        self.assertFalse(user.can_launch_water_demand())


class TestQAProjectWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.db = os.path.join(self._tmpdir, "qa.db")
        init_db(self.db)
        init_users_table(self.db)
        self.akash = authenticate("akash", "Akash@123", self.db)
        self.vaibhav = authenticate("vaibhav", "Vaibhav@123", self.db)
        self.admin = authenticate("admin", "Admin@123", self.db)

    def test_create_save_reload_update_no_duplicate(self) -> None:
        state = create_new_project_state(self.akash, self.db)
        state.project.project_name = "QA Residential"
        state.project.client_name = "Test Client"
        state.project.project_location = "Pune"
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        state.residential = [
            ResidentialWing(plot="Plot-A", wing="WING-A", flats_2bhk=10, flats_3bhk=5),
        ]
        state.auto_calculate()
        pid = state.project.project_id
        self.assertFalse(persist_project_state(state, self.akash, self.db))

        loaded = load_project_state(pid, self.db, user=self.akash)
        self.assertEqual(loaded.project.project_name, "QA Residential")
        self.assertEqual(len(loaded.residential), 1)

        loaded.project.project_name = "QA Residential Updated"
        loaded.residential[0].flats_2bhk = 20
        loaded.auto_calculate()
        self.assertTrue(persist_project_state(loaded, self.akash, self.db))

        again = load_project_state(pid, self.db, user=self.akash)
        self.assertEqual(again.project.project_name, "QA Residential Updated")
        self.assertEqual(again.residential[0].flats_2bhk, 20)
        all_projects = find_projects(user=self.admin, db_path=self.db)
        self.assertEqual(len([p for p in all_projects if p["project_id"] == pid]), 1)

    def test_engineer_cannot_open_other_engineer_project(self) -> None:
        state = create_new_project_state(self.akash, self.db)
        state.project.project_name = "Akash Only"
        state.project.client_name = "Client"
        state.project.project_location = "Pune"
        state.residential = [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=5)]
        state.auto_calculate()
        pid = state.project.project_id
        persist_project_state(state, self.akash, self.db)

        with self.assertRaises(ValueError):
            load_project_state(pid, self.db, user=self.vaibhav)

        vaibhav_list = find_projects(user=self.vaibhav, db_path=self.db)
        self.assertFalse(any(p["project_id"] == pid for p in vaibhav_list))

    def test_admin_sees_all_projects(self) -> None:
        state = create_new_project_state(self.akash, self.db)
        state.project.project_name = "Admin Visible"
        state.project.client_name = "C"
        state.project.project_location = "L"
        persist_project_state(state, self.akash, self.db)
        admin_list = find_projects(user=self.admin, db_path=self.db)
        self.assertTrue(any(p["project_name"] == "Admin Visible" for p in admin_list))


class TestQAProjectTypes(unittest.TestCase):
    def test_residential_hides_commercial(self) -> None:
        pages = vp(PROJECT_TYPE_RESIDENTIAL)
        self.assertIn("Residential", pages)
        self.assertNotIn("Commercial", pages)
        self.assertNotIn("HVAC", pages)

    def test_commercial_shows_hvac_not_residential(self) -> None:
        pages = vp(PROJECT_TYPE_COMMERCIAL)
        self.assertIn("Commercial", pages)
        self.assertIn("HVAC", pages)
        self.assertNotIn("Residential", pages)

    def test_unset_type_only_project_tab(self) -> None:
        from config.nbc_2026 import PROJECT_TYPE_UNSET
        pages = vp(PROJECT_TYPE_UNSET)
        self.assertEqual(pages, frozenset({"Project"}))


class TestQABuildingParser(unittest.TestCase):
    def test_g_plus_7(self) -> None:
        above, height = parse_building_config("G+7")
        self.assertEqual(above, 7)
        self.assertGreater(height, 0)

    def test_two_basements_g_plus_21(self) -> None:
        above, height = parse_building_config("2B+G+21")
        self.assertEqual(above, 21)
        self.assertGreater(height, parse_building_config("G+7")[1])

    def test_three_basements_g_plus_30(self) -> None:
        above, height = parse_building_config("3B+G+30")
        self.assertEqual(above, 30)
        self.assertGreater(height, 0)

    def test_invalid_config_returns_zero(self) -> None:
        above, height = parse_building_config("INVALID")
        self.assertEqual(above, 0)
        self.assertEqual(height, 0.0)


class TestQACalculations(unittest.TestCase):
    def test_live_calc_updates_on_input_change(self) -> None:
        state = AppState()
        state.residential = [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=10)]
        state.auto_calculate()
        first = state.results.plots["Plot-A"].res_total_lpd
        state.residential[0].flats_2bhk = 20
        state.auto_calculate()
        second = state.results.plots["Plot-A"].res_total_lpd
        self.assertGreater(second, first)

    def test_fire_tank_table_values(self) -> None:
        self.assertEqual(fire_tank_capacity_liters(20), 100_000)
        self.assertEqual(fire_tank_capacity_liters(50, "Commercial"), 250_000)


if __name__ == "__main__":
    unittest.main()
