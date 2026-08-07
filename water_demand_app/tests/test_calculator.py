"""Unit tests for NBC-2026 water demand calculations."""

import math
import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

from config.nbc_2026 import (
    bhk_population,
    commercial_population,
    fire_tank_capacity_liters,
    kitchen_water_lpd,
    landscape_demand,
    residential_demand,
    say_stp_capacity_kld,
    treated_water_lpd,
    COMMERCIAL_TYPES,
    PLOT_MODE_SINGLE,
    PROJECT_TYPE_IT_PARK,
    PROJECT_TYPE_RESIDENTIAL,
)
from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing
from services.calculator import WaterDemandCalculator


class TestNBCFormulas(unittest.TestCase):
    def test_residential_wing_a(self):
        dom, flu, tot = residential_demand(730)
        self.assertEqual(dom, 76650)
        self.assertEqual(flu, 21900)
        self.assertEqual(tot, 98550)

    def test_shop_ground_floor_population(self):
        spec = COMMERCIAL_TYPES["Shop - Ground Floor"]
        self.assertEqual(commercial_population(437, spec), 146)

    def test_shop_upper_floor_population(self):
        spec = COMMERCIAL_TYPES["Shop - Upper Floor"]
        self.assertEqual(commercial_population(437, spec), 73)

    def test_office_population(self):
        spec = COMMERCIAL_TYPES["Office"]
        self.assertEqual(commercial_population(2185, spec), 218)

    def test_restaurant_population(self):
        spec = COMMERCIAL_TYPES["Restaurant"]
        self.assertEqual(commercial_population(437, spec), 313)

    def test_landscape(self):
        self.assertEqual(landscape_demand(765), 4590)
        self.assertEqual(landscape_demand(762), 4572)

    def test_stp_say_capacity(self):
        self.assertEqual(say_stp_capacity_kld(178605), 180)
        self.assertEqual(say_stp_capacity_kld(46085), 50)
        self.assertEqual(say_stp_capacity_kld(140657), 150)

    def test_treated_water(self):
        self.assertEqual(treated_water_lpd(180), 158760)


class TestPunavaleProject(unittest.TestCase):
    def _build_calculator(self) -> WaterDemandCalculator:
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
        return WaterDemandCalculator(residential, commercial, other)

    def test_plot_a_residential(self):
        calc = self._build_calculator()
        results = calc.calculate()
        pa = results.plots["Plot-A"]
        self.assertEqual(pa.res_population, 1470)
        self.assertEqual(pa.res_total_lpd, 198450)
        self.assertEqual(pa.res_domestic_lpd, 154350)
        self.assertEqual(pa.res_flushing_lpd, 44100)

    def test_plot_a_landscape(self):
        calc = self._build_calculator()
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-A"].landscape_dry_lpd, 4590)

    def test_plot_b_residential(self):
        calc = self._build_calculator()
        results = calc.calculate()
        pb = results.plots["Plot-B"]
        self.assertEqual(pb.res_population, 1120)
        self.assertEqual(pb.res_total_lpd, 151200)


class TestNewFeatures(unittest.TestCase):
    def test_kitchen_water_bhk_mix(self):
        self.assertEqual(kitchen_water_lpd(10, 20, 5, 2, 1), 10 * 25 + 20 * 35 + 5 * 45 + 2 * 50 + 1 * 55)

    def test_bhk_population_4bhk(self):
        self.assertEqual(bhk_population(0, 0, 0, 10, 0), 60)

    def test_fire_tank_by_height(self):
        self.assertEqual(fire_tank_capacity_liters(20), 100_000)
        self.assertEqual(fire_tank_capacity_liters(50), 400_000)

    def test_fire_tank_commercial_building(self):
        self.assertEqual(fire_tank_capacity_liters(20, "Commercial"), 100_000)
        self.assertEqual(fire_tank_capacity_liters(50, "Hotel"), 250_000)

    def test_swimming_pool_na(self):
        other = OtherDetails(
            swimming_pool={"Plot-A": 5000},
            swimming_pool_status={"Plot-A": "not_applicable"},
            swimming_pool_na={"Plot-A": True},
        )
        calc = WaterDemandCalculator(
            [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=5)],
            [],
            other,
        )
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-A"].swimming_pool_lpd, 0)

    def test_hvac_hidden_for_residential(self):
        other = OtherDetails(hvac_water={"Plot-A": 10000})
        project = ProjectData(project_type=PROJECT_TYPE_RESIDENTIAL)
        calc = WaterDemandCalculator(
            [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=5)],
            [],
            other,
            project,
        )
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-A"].hvac_lpd, 0)

    def test_hvac_applicable_for_it_park(self):
        other = OtherDetails(hvac_water={"Plot-A": 5000})
        project = ProjectData(project_type=PROJECT_TYPE_IT_PARK)
        calc = WaterDemandCalculator(
            [],
            [CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="IT Office", area_sqm=1000)],
            other,
            project,
        )
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-A"].hvac_lpd, 5000)

    def test_single_plot_mode(self):
        project = ProjectData(plot_mode=PLOT_MODE_SINGLE)
        calc = WaterDemandCalculator(
            [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=5)],
            [],
            OtherDetails(),
            project,
        )
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-B"].total_population, 0)
        self.assertEqual(results.total["Total Population"], 20)

    def test_plot_label_maps_to_plot_a(self):
        project = ProjectData(plot_mode=PLOT_MODE_SINGLE)
        calc = WaterDemandCalculator(
            [ResidentialWing(plot="Plot", wing="A", flats_2bhk=10)],
            [CommercialUnit(plot="Plot", block="COMM-A", comm_type="Office", area_sqm=100)],
            OtherDetails(),
            project,
        )
        results = calc.calculate()
        self.assertEqual(results.plots["Plot-A"].res_population, 40)
        self.assertGreater(results.plots["Plot-A"].com_population, 0)
        self.assertEqual(results.plots["Plot-B"].total_population, 0)

if __name__ == "__main__":
    unittest.main()
