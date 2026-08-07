"""Tests for template-based Excel export."""

import os
import sys
import tempfile
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing
from openpyxl import load_workbook
from services.calculator import WaterDemandCalculator
from services.excel_exporter import TEMPLATE_PATH, export_excel


class TestTemplateExcelExport(unittest.TestCase):
    def setUp(self) -> None:
        if not os.path.isfile(TEMPLATE_PATH):
            self.skipTest("WaterDemand_Template.xlsx not found")

    def test_template_export_preserves_sheets(self) -> None:
        residential = [
            ResidentialWing(plot="Plot-A", wing="WING - A", flats_2bhk=73, flats_3bhk=73, building_height_m=24),
        ]
        commercial = [
            CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Retail Shop", area_sqm=437),
        ]
        project = ProjectData(project_name="TEST PROJECT", client_name="CLIENT", engineer_name="Akash")
        calc = WaterDemandCalculator(residential, commercial, OtherDetails(), project)
        results = calc.calculate()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            out_path = tmp.name
        try:
            export_excel(out_path, project, results)
            wb = load_workbook(out_path)
            self.assertEqual(
                wb.sheetnames,
                [
                    "Cover",
                    "Consolidated",
                    "Plot-A Demand",
                    "Plot-B Demand",
                    "Plot-A UGT-OHT",
                    "Plot-B UGT-OHT",
                    "Plot-A STP",
                    "Plot-B STP",
                    "Summary",
                ],
            )
            self.assertEqual(wb["Cover"]["B4"].value, "TEST PROJECT")
            self.assertEqual(wb["Cover"]["B8"].value, "Akash")
            self.assertGreater(wb["Plot-A Demand"]["E5"].value, 0)
            self.assertEqual(wb["Plot-A Demand"]["B16"].value, results.plots["Plot-A"].dry_total_water_lpd)
        finally:
            os.unlink(out_path)

    def test_punavale_export_grand_total_and_commercial_rows(self) -> None:
        residential = [
            ResidentialWing(plot="Plot-A", wing="WING - A", flats=146, pop_per_flat=5),
            ResidentialWing(plot="Plot-A", wing="WING - B", flats=146, pop_per_flat=5),
            ResidentialWing(plot="Plot-A", wing="BUNGLOW-A", flats=1, pop_per_flat=5),
            ResidentialWing(plot="Plot-A", wing="BUNGLOW-B", flats=1, pop_per_flat=5),
            ResidentialWing(plot="Plot-B", wing="WING - C", flats=56, pop_per_flat=5),
            ResidentialWing(plot="Plot-B", wing="WING - D", flats=56, pop_per_flat=5),
            ResidentialWing(plot="Plot-B", wing="WING - E", flats=56, pop_per_flat=5),
            ResidentialWing(plot="Plot-B", wing="WING - F", flats=56, pop_per_flat=5),
        ]
        commercial = [
            CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Shop - Ground Floor", floor_label="Ground Floor (Shop)", area_sqm=437),
            CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Shop - Upper Floor", floor_label="1st Floor (Shop)", area_sqm=437),
            CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Office", floor_label="2nd to 6th (Office)", area_sqm=2185),
            CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Restaurant", floor_label="7th (Restaurant)", area_sqm=437),
            CommercialUnit(plot="Plot-A", block="COMM-B", comm_type="Shop - Ground Floor", floor_label="Gr.+Mezz Floor (Shop)", area_sqm=213),
            CommercialUnit(plot="Plot-A", block="COMM-B", comm_type="Office", floor_label="1st & 2nd (office)", area_sqm=484),
            CommercialUnit(plot="Plot-A", block="COMM-B", comm_type="Office", floor_label="3rd & 4th (office)", area_sqm=924),
            CommercialUnit(plot="Plot-B", block="COMM-C", comm_type="Shop - Ground Floor", floor_label="Ground & Mezz", area_sqm=339),
        ]
        other = OtherDetails(
            landscape_area={"Plot-A": 765.0, "Plot-B": 762.0},
            fire_tank={"Plot-A": 300000.0, "Plot-B": 230000.0},
        )
        project = ProjectData(project_name="PUNAVALE", client_name="CLIENT", engineer_name="Akash")
        calc = WaterDemandCalculator(residential, commercial, other, project)
        results = calc.calculate()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            out_path = tmp.name
        try:
            export_excel(out_path, project, results)
            wb = load_workbook(out_path)
            demand = wb["Plot-A Demand"]
            grand_row = None
            for row in range(1, demand.max_row + 1):
                if demand.cell(row=row, column=1).value == "GRAND TOTAL":
                    grand_row = row
                    break
            self.assertIsNotNone(grand_row)
            self.assertEqual(demand.cell(row=grand_row, column=2).value, results.plots["Plot-A"].dry_total_water_lpd)
            blocks = {
                demand.cell(row=row, column=2).value
                for row in range(1, grand_row)
                if demand.cell(row=row, column=2).value in {"COMM-A", "COMM-B"}
            }
            self.assertEqual(blocks, {"COMM-A", "COMM-B"})
        finally:
            os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
