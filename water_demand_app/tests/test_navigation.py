"""GUI navigation smoke test — verifies every sidebar page can be shown."""

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)


class TestSidebarNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from _app_sidebar import ProjectWorkspace

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.app = ProjectWorkspace(cls.root)
            cls.app.ensure_pages_built()
            cls.app.withdraw()
            cls.app.update_idletasks()
            cls.app.update()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "app"):
            cls.app.destroy()
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_all_nav_pages_registered(self) -> None:
        for key, _label in self.app.NAV:
            if not self.app._nav_visible(key):
                continue
            self.app.show(key)
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

    def test_rwh_not_in_pages(self) -> None:
        self.assertNotIn("RWH", self.app.pages)

    def test_oht_page_exists(self) -> None:
        self.app.show("OHT")
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
