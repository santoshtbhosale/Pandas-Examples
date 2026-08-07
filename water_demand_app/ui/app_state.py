from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.calculations import CalculationResults
from models.commercial import CommercialUnit
from models.other_details import OtherDetails, OHTDetail
from models.project import ProjectData
from models.residential import ResidentialWing
from services.calculator import WaterDemandCalculator


@dataclass
class AppState:
    project: ProjectData = field(default_factory=ProjectData)
    residential: List[ResidentialWing] = field(default_factory=list)
    commercial: List[CommercialUnit] = field(default_factory=list)
    other: OtherDetails = field(default_factory=OtherDetails)
    results: Optional[CalculationResults] = None
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
