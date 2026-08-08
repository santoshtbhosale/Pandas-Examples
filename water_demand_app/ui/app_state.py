from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.nbc_2026 import (
    PROJECT_TYPE_UNSET,
    hvac_applicable,
    is_project_type_set,
    show_commercial_section,
    show_residential_section,
    show_swimming_section,
)
from models.calculations import CalculationResults
from models.commercial import CommercialUnit
from models.environmental import EnvironmentalResults
from models.other_details import OtherDetails, OHTDetail
from models.project import ProjectData
from models.residential import ResidentialWing
from services.calculator import WaterDemandCalculator
from services.environmental_calculator import calculate_environmental


@dataclass
class AppState:
    project: ProjectData = field(default_factory=ProjectData)
    residential: List[ResidentialWing] = field(default_factory=list)
    commercial: List[CommercialUnit] = field(default_factory=list)
    other: OtherDetails = field(default_factory=OtherDetails)
    results: Optional[CalculationResults] = None
    environmental: Optional[EnvironmentalResults] = None
    calculated_legacy: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def residential_legacy(self) -> List[dict]:
        return [w.legacy_dict() for w in self.residential]

    def commercial_legacy(self) -> List[dict]:
        return [c.legacy_dict() for c in self.commercial]

    def other_legacy(self) -> dict:
        legacy = self.other.legacy_dict()
        for plot in ("Plot-A", "Plot-B"):
            legacy[f"Fire Tank {plot}"] = self.other.fire_tank.get(plot, 0)
        return legacy

    def project_legacy(self) -> Dict[str, str]:
        return self.project.legacy_dict()

    def run_calculations(self) -> None:
        calc = WaterDemandCalculator(
            self.residential, self.commercial, self.other, self.project
        )
        self.results = calc.calculate()
        self.calculated_legacy = self.results.legacy_dict()
        self.environmental = calculate_environmental(self.results, self.project)

    def auto_calculate(self) -> None:
        """Recalculate whenever inputs change (no manual Calculate button)."""
        try:
            from services.automation import prepare_live_calculation
            prepare_live_calculation(self)
            self.run_calculations()
        except Exception:
            self.results = None
            self.environmental = None

    def apply_project_type(self, new_type: str) -> None:
        """Clear data for sections hidden by the new project type."""
        old_type = self.project.project_type
        self.project.project_type = new_type
        if not is_project_type_set(new_type) or not is_project_type_set(old_type):
            self.auto_calculate()
            return
        if not show_residential_section(new_type):
            self.residential = []
        if not show_commercial_section(new_type):
            self.commercial = []
        if not show_swimming_section(new_type):
            for plot in list(self.other.swimming_pool.keys()):
                self.other.swimming_pool[plot] = 0.0
                self.other.swimming_pool_status[plot] = "not_applicable"
                self.other.swimming_pool_na[plot] = True
        if not hvac_applicable(new_type):
            for plot in list(self.other.hvac_water.keys()):
                self.other.hvac_water[plot] = 0.0
        self.auto_calculate()

    def sync_building_defaults(self) -> None:
        """Apply project-level building settings to residential wings when empty."""
        p = self.project
        if not p.building_config:
            return
        for wing in self.residential:
            if not wing.building_config or wing.building_config == "G+7":
                wing.building_config = p.building_config
            if wing.building_height_m <= 0 and p.building_height_m > 0:
                wing.building_height_m = p.building_height_m
            if wing.num_wings <= 0 and p.num_wings > 0:
                wing.num_wings = p.num_wings
            if not wing.building_type:
                wing.building_type = p.building_type

    def load_defaults(self) -> None:
        if not self.residential:
            self.residential = [
                ResidentialWing(plot="Plot-A", wing="WING - A", flats=146, pop_per_flat=5, sort_order=0),
                ResidentialWing(plot="Plot-A", wing="WING - B", flats=146, pop_per_flat=5, sort_order=1),
                ResidentialWing(plot="Plot-B", wing="WING - C", flats=56, pop_per_flat=5, sort_order=2),
                ResidentialWing(plot="Plot-B", wing="WING - D", flats=56, pop_per_flat=5, sort_order=3),
            ]
        if not self.commercial:
            self.commercial = [
                CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Shop - Ground Floor", floor_label="Ground Floor (Shop)", area_sqm=437, sort_order=0),
                CommercialUnit(plot="Plot-A", block="COMM-A", comm_type="Shop - Upper Floor", floor_label="1st Floor (Shop)", area_sqm=437, sort_order=1),
                CommercialUnit(plot="Plot-B", block="COMM-C", comm_type="Shop - Ground Floor", floor_label="Ground & Mezz", area_sqm=339, sort_order=2),
            ]
