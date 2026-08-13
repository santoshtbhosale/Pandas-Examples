"""Version 2.0 UI/UX and performance regression tests."""

from __future__ import annotations

import inspect
import os
import sys
import tempfile
import time
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config.nbc_2026 import PROJECT_TYPE_RESIDENTIAL
from config.page_visibility import visible_pages
from models.calculations import CalculationResults, PlotResults
from models.project import ProjectData
from services.pdf_exporter import export_pdf
from services.excel_exporter import export_excel


def _reference_results() -> CalculationResults:
    plot_a = PlotResults(
        plot="Plot-A",
        res_population=2835,
        com_population=0,
        stp_capacity_kld=370.0,
        dry_total_water_lpd=500000,
    )
    plot_b = PlotResults(plot="Plot-B")
    return CalculationResults(
        plots={"Plot-A": plot_a, "Plot-B": plot_b},
        total={"Total Population": 2835, "Total Flats": 0},
    )


class TestUIUXV2(unittest.TestCase):
    def test_rwh_absent_from_nav_and_visibility(self) -> None:
        from _app_sidebar import ProjectWorkspace

        nav_keys = [key for key, _ in ProjectWorkspace.NAV]
        self.assertNotIn("RWH", nav_keys)
        pages = visible_pages(PROJECT_TYPE_RESIDENTIAL)
        self.assertNotIn("RWH", pages)

    def test_result_table_embedded_mode(self) -> None:
        try:
            import customtkinter as ctk
            from ui.components.result_table import ResultTableView
        except Exception as exc:
            raise unittest.SkipTest(str(exc)) from exc

        root = ctk.CTk()
        root.withdraw()
        table = ResultTableView(root, embedded=True)
        table.set_rows("Test", [("Description row", "1.00", "KLD")])
        self.assertFalse(isinstance(table._host, ctk.CTkScrollableFrame))
        root.destroy()

    def test_sidebar_rebuild_does_not_destroy(self) -> None:
        source = inspect.getsource(
            __import__("_app_sidebar", fromlist=["ProjectWorkspace"]).ProjectWorkspace._rebuild_sidebar
        )
        self.assertNotIn("destroy()", source)

    def test_workspace_has_debounced_calc(self) -> None:
        from _app_sidebar import ProjectWorkspace

        self.assertTrue(hasattr(ProjectWorkspace, "_schedule_calc"))

    def test_pdf_still_generates_with_section_headings(self) -> None:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise unittest.SkipTest("pypdf not installed")

        project = ProjectData(project_name="UX TEST", project_type=PROJECT_TYPE_RESIDENTIAL)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            out_path = tmp.name
        try:
            export_pdf(out_path, project, _reference_results())
            text = "".join((p.extract_text() or "") for p in PdfReader(out_path).pages).upper()
            for heading in (
                "SECTION-8",
                "BUILDING / POPULATION DETAILS",
                "DRY SEASON",
                "WET SEASON",
                "SECTION-9",
                "UGT DETAILS",
                "SECTION-10",
                "STP DETAILS",
            ):
                self.assertIn(heading, text)
            self.assertNotIn("SECTION-7", text)
        finally:
            if os.path.isfile(out_path):
                os.unlink(out_path)

    def test_no_planetcode_branding_in_dashboard(self) -> None:
        import inspect
        from ui import dashboard

        source = inspect.getsource(dashboard.MainDashboard._build)
        self.assertNotIn("PLANETCODE", source.upper())
        self.assertNotIn("PlanetCode", source)

    def test_app_title_american_edge(self) -> None:
        from app_launcher import APP_TITLE

        self.assertIn("American Edge Engineers", APP_TITLE)
        self.assertNotIn("PlanetCode", APP_TITLE)

    def test_engineering_config_conditional(self) -> None:
        from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL
        from ui.pages.project_page import show_project_engineering_configuration

        self.assertTrue(show_project_engineering_configuration(PROJECT_TYPE_RESIDENTIAL))
        self.assertFalse(show_project_engineering_configuration(PROJECT_TYPE_COMMERCIAL))

    def test_excel_still_generates(self) -> None:
        project = ProjectData(project_name="UX TEST", project_type=PROJECT_TYPE_RESIDENTIAL)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            out_path = tmp.name
        try:
            export_excel(out_path, project, _reference_results())
            self.assertGreater(os.path.getsize(out_path), 3000)
        finally:
            if os.path.isfile(out_path):
                os.unlink(out_path)


class TestNavigationPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from _app_sidebar import ProjectWorkspace
            from ui.app_state import AppState

            cls.ctk = ctk
            root = ctk.CTk()
            root.withdraw()
            cls.root = root
            cls.workspace = ProjectWorkspace(root, initial_state=AppState())
            cls.workspace.app_state.project.project_type = PROJECT_TYPE_RESIDENTIAL
            cls.workspace.ensure_pages_built()
            cls.workspace.update_idletasks()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_page_navigation_performance(self) -> None:
        self.workspace._calc()
        self.workspace._calc_dirty = False
        thresholds = {
            "Project": 700,
            "Residential": 500,
            "Sewage": 500,
            "OHT": 500,
            "STP": 500,
            "SolidWaste": 500,
            "Preview": 1200,
        }
        for page, limit_ms in thresholds.items():
            start = time.perf_counter()
            self.workspace.show(page)
            self.workspace.update_idletasks()
            elapsed_ms = (time.perf_counter() - start) * 1000
            with self.subTest(page=page):
                self.assertLess(elapsed_ms, limit_ms, f"{page} navigation took {elapsed_ms:.1f}ms")

    def test_apply_state_resets_to_project_page(self) -> None:
        from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL
        from ui.app_state import AppState

        state = AppState()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        self.workspace.apply_state(state)
        self.assertIn("Project", self.workspace.pages)
        self.assertEqual(self.workspace._current_page, "Project")

        state.project.project_type = PROJECT_TYPE_COMMERCIAL
        self.workspace.show("Commercial")
        self.assertIn("Commercial", self.workspace.pages)

        state2 = AppState()
        state2.project.project_type = PROJECT_TYPE_COMMERCIAL
        self.workspace.apply_state(state2)
        self.assertIn("Project", self.workspace.pages)
        self.assertNotIn("Residential", self.workspace.pages)

    def test_project_type_switch_navigation(self) -> None:
        from config.nbc_2026 import PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_RESIDENTIAL
        from ui.app_state import AppState

        state = AppState()
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        self.workspace.apply_state(state)
        self.workspace._wizard_show_next("Project")
        self.workspace.update_idletasks()
        self.assertEqual(self.workspace._current_page, "Residential")

        state.project.project_type = PROJECT_TYPE_COMMERCIAL
        self.workspace.apply_state(state)
        self.workspace._wizard_show_next("Project")
        self.workspace.update_idletasks()
        self.assertEqual(self.workspace._current_page, "Commercial")


if __name__ == "__main__":
    unittest.main()
