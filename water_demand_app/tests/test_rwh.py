"""Unit tests for Rain Water Harvesting calculator."""

import os
import sys
import tempfile
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

from rwh.calculator import RWHCalculator, default_surfaces
from rwh.config import harvestable_liters, recommended_tank_liters
from rwh.database import init_rwh_db, load_rwh_project, save_rwh_project
from rwh.models import RWHCatchmentSurface, RWHProjectData
from rwh.pdf_exporter import export_rwh_pdf


class TestRWHFormulas(unittest.TestCase):
    def test_harvestable_basic(self):
        # 100 m² × 900 mm × 0.85 × 0.90 = 68,850 L
        val = harvestable_liters(100, 900, 0.85, 0.90)
        self.assertAlmostEqual(val, 68850.0, places=1)

    def test_tank_sizing(self):
        self.assertAlmostEqual(recommended_tank_liters(60000, 60), 1000.0, places=1)


class TestRWHCalculator(unittest.TestCase):
    def test_default_project(self):
        project = RWHProjectData(
            project_name="Test RWH",
            annual_rainfall_mm=750,
            rainy_days=60,
            collection_efficiency=0.9,
            surfaces=default_surfaces(),
        )
        results = RWHCalculator(project).calculate()
        self.assertGreater(results.annual_harvest_liters, 0)
        self.assertGreater(results.design_tank_liters, 0)
        self.assertEqual(len(results.surfaces), 2)

    def test_custom_surface(self):
        project = RWHProjectData(
            project_name="Custom",
            annual_rainfall_mm=1000,
            rainy_days=50,
            collection_efficiency=1.0,
            surfaces=[
                RWHCatchmentSurface(surface_type="Custom", area_sqm=200, runoff_coefficient=0.8, label="Shed"),
            ],
        )
        results = RWHCalculator(project).calculate()
        self.assertAlmostEqual(results.annual_harvest_liters, 160000.0, places=0)


class TestRWHPersistenceAndPDF(unittest.TestCase):
    def test_save_load_and_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "test.db")
            init_rwh_db(db)
            project = RWHProjectData(project_name="Persist Test", surfaces=default_surfaces())
            results = RWHCalculator(project).calculate()
            save_rwh_project(project, results, db)
            snap = load_rwh_project(project.rwh_id, db)
            self.assertEqual(snap["project"]["project_name"], "Persist Test")
            pdf_path = os.path.join(tmp, "rwh.pdf")
            export_rwh_pdf(pdf_path, project, results)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 1000)


if __name__ == "__main__":
    unittest.main()
