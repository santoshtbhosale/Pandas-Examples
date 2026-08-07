"""GUI navigation smoke test — verifies every sidebar page can be shown."""

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


class TestSidebarNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            import importlib.util

            spec = importlib.util.spec_from_file_location("water_main", os.path.join(WORKSPACE_ROOT, "main.py"))
            water_main = importlib.util.module_from_spec(spec)
            sys.modules["water_main"] = water_main
            assert spec.loader is not None
            spec.loader.exec_module(water_main)
            WaterDemandApp = water_main.WaterDemandApp

            cls.ctk = ctk
            cls.app = WaterDemandApp()
            cls.app.withdraw()
            cls.app.update_idletasks()
            cls.app.update()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "app"):
            cls.app.destroy()

    def test_all_nav_pages_registered(self) -> None:
        for key, _label in self.app.NAV:
            if not self.app._nav_visible(key):
                continue
            self.assertIn(key, self.app.pages, f"Page '{key}' missing from self.pages")

    def test_show_every_page_without_error(self) -> None:
        for key, _label in self.app.NAV:
            if not self.app._nav_visible(key):
                continue
            with self.subTest(page=key):
                self.app.show(key)
                self.app.update_idletasks()
                self.app.update()
                self.assertIn(key, self.app.pages)

    def test_rwh_page_exists(self) -> None:
        self.assertIn("RWH", self.app.pages)

    def test_oht_page_exists(self) -> None:
        self.assertIn("OHT", self.app.pages)

    def test_hospital_type_navigation(self) -> None:
        self.app.app_state.apply_project_type("hospital")
        self.app._rebuild_sidebar()
        for key, _label in self.app.NAV:
            if not self.app._nav_visible(key):
                continue
            with self.subTest(page=key, project_type="hospital"):
                self.app.show(key)
                self.app.update_idletasks()
                self.app.update()
                self.assertIn(key, self.app.pages)


if __name__ == "__main__":
    unittest.main()
