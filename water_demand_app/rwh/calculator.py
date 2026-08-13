"""Rain Water Harvesting calculator."""

from __future__ import annotations

from rwh.config import (
    harvestable_liters,
    peak_day_harvest_liters,
    recommended_tank_liters,
)
from rwh.models import RWHCatchmentSurface, RWHProjectData, RWHResults, RWHSurfaceResult


class RWHCalculator:
    def __init__(self, project: RWHProjectData) -> None:
        self.project = project

    def calculate(self) -> RWHResults:
        surface_results: list[RWHSurfaceResult] = []
        total_area = 0.0
        annual_total = 0.0
        peak_total = 0.0
        eff = self.project.collection_efficiency

        for surf in self.project.surfaces:
            if surf.area_sqm <= 0:
                continue
            coeff = surf.resolved_coefficient()
            annual = harvestable_liters(
                surf.area_sqm,
                self.project.annual_rainfall_mm,
                coeff,
                eff,
            )
            peak = peak_day_harvest_liters(
                surf.area_sqm,
                self.project.max_daily_rainfall_mm,
                coeff,
                eff,
            )
            surface_results.append(
                RWHSurfaceResult(
                    surface_type=surf.surface_type,
                    label=surf.label or surf.surface_type,
                    area_sqm=surf.area_sqm,
                    runoff_coefficient=coeff,
                    annual_harvest_liters=round(annual, 2),
                    peak_day_liters=round(peak, 2),
                )
            )
            total_area += surf.area_sqm
            annual_total += annual
            peak_total += peak

        recommended = recommended_tank_liters(annual_total, self.project.rainy_days)
        design = self.project.proposed_tank_liters if self.project.proposed_tank_liters > 0 else recommended

        return RWHResults(
            surfaces=surface_results,
            total_catchment_sqm=round(total_area, 2),
            annual_harvest_liters=round(annual_total, 2),
            annual_harvest_cum=round(annual_total / 1000.0, 3),
            daily_average_liters=round(annual_total / 365.0, 2) if annual_total else 0.0,
            peak_day_liters=round(peak_total, 2),
            recommended_tank_liters=round(recommended, 2),
            design_tank_liters=round(design, 2),
            collection_efficiency=eff,
        )


def default_surfaces() -> list[RWHCatchmentSurface]:
    return [
        RWHCatchmentSurface(surface_type="RCC Roof", area_sqm=500.0, runoff_coefficient=0.85, label="Main Building Roof", sort_order=0),
        RWHCatchmentSurface(surface_type="Paved Area", area_sqm=200.0, runoff_coefficient=0.70, label="Paved Courtyard", sort_order=1),
    ]
