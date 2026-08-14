"""Tests for Phase-4 live automation."""

import os
import sys
import unittest

APP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing
from services.automation import (
    apply_building_parser,
    apply_fire_tanks,
    auto_fire_tank_liters,
    commercial_from_ui_rows,
    prepare_live_calculation,
    wings_from_ui_rows,
)
from services.calculator import WaterDemandCalculator
from ui.app_state import AppState


class TestAutomation(unittest.TestCase):
    def test_building_parser_sets_height(self) -> None:
        project = ProjectData(building_config="G+12", building_height_m=0)
        wing = ResidentialWing(plot="Plot-A", wing="A", building_config="G+7")
        apply_building_parser(project, [wing])
        self.assertGreater(project.building_height_m, 0)
        self.assertEqual(wing.building_config, "G+12")
        self.assertGreater(wing.building_height_m, 0)

    def test_fire_tank_from_project_height(self) -> None:
        project = ProjectData(building_height_m=25, building_type="Commercial")
        other = OtherDetails()
        cap = auto_fire_tank_liters("Plot-A", [], project, other)
        self.assertGreater(cap, 0)

    def test_live_calc_includes_kitchen_landscape_ugt_stp(self) -> None:
        state = AppState()
        state.project = ProjectData(building_height_m=30, building_type="Residential Apartment")
        state.residential = [
            ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=10, flats_3bhk=5),
        ]
        state.other.landscape_area["Plot-A"] = 500
        prepare_live_calculation(state)
        calc = WaterDemandCalculator(state.residential, state.commercial, state.other, state.project)
        results = calc.calculate()
        plot = results.plots["Plot-A"]
        self.assertGreater(plot.kitchen_water_lpd, 0)
        self.assertGreater(plot.landscape_dry_lpd, 0)
        self.assertGreater(plot.fire_tank_liters, 0)
        self.assertGreater(plot.ugt_domestic_liters, 0)
        self.assertGreater(len(plot.oht_rows), 0)
        self.assertGreater(plot.stp_capacity_kld, 0)

    def test_commercial_auto_from_area(self) -> None:
        state = AppState()
        state.commercial = [CommercialUnit(plot="Plot-A", block="C1", comm_type="Office", area_sqm=1000)]
        prepare_live_calculation(state)
        calc = WaterDemandCalculator([], state.commercial, state.other, state.project)
        results = calc.calculate()
        self.assertGreater(results.plots["Plot-A"].com_population, 0)
        self.assertGreater(results.plots["Plot-A"].com_total_lpd, 0)


if __name__ == "__main__":
    unittest.main()
