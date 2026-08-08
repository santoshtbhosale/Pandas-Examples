"""Rain Water Harvesting module constants and surface coefficients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# Reuse app brand colors (duplicated lightly so RWH stays self-contained)
RWH_BRAND_NAVY = "#001F3F"
RWH_BRAND_ORANGE = "#F37021"
RWH_HEADER_TEAL = "#1ABC9C"

# Collection efficiency after first-flush / filter losses (0-1)
DEFAULT_COLLECTION_EFFICIENCY = 0.90

# Default climate assumptions (user-editable in GUI)
DEFAULT_ANNUAL_RAINFALL_MM = 750.0
DEFAULT_RAINY_DAYS = 60
DEFAULT_MAX_DAILY_RAINFALL_MM = 50.0


@dataclass(frozen=True)
class CatchmentSurfaceSpec:
    label: str
    runoff_coefficient: float


CATCHMENT_SURFACES: Dict[str, CatchmentSurfaceSpec] = {
    "RCC Roof": CatchmentSurfaceSpec("RCC Roof", 0.85),
    "Metal Roof": CatchmentSurfaceSpec("Metal Roof", 0.90),
    "Tiled Roof": CatchmentSurfaceSpec("Tiled Roof", 0.75),
    "Paved Area": CatchmentSurfaceSpec("Paved Area", 0.70),
    "Unpaved / Garden": CatchmentSurfaceSpec("Unpaved / Garden", 0.20),
    "Custom": CatchmentSurfaceSpec("Custom", 0.80),
}


def harvestable_liters(
    area_sqm: float,
    rainfall_mm: float,
    runoff_coefficient: float,
    collection_efficiency: float = DEFAULT_COLLECTION_EFFICIENCY,
) -> float:
    """Annual harvestable volume in litres: A × R × K × η."""
    if area_sqm <= 0 or rainfall_mm <= 0 or runoff_coefficient <= 0:
        return 0.0
    eff = max(0.0, min(1.0, collection_efficiency))
    coeff = max(0.0, min(1.0, runoff_coefficient))
    return area_sqm * rainfall_mm * coeff * eff


def recommended_tank_liters(annual_harvest_l: float, rainy_days: int) -> float:
    """Simple tank sizing: annual harvest / rainy days."""
    if annual_harvest_l <= 0 or rainy_days <= 0:
        return 0.0
    return annual_harvest_l / float(rainy_days)


def peak_day_harvest_liters(
    area_sqm: float,
    max_daily_rainfall_mm: float,
    runoff_coefficient: float,
    collection_efficiency: float = DEFAULT_COLLECTION_EFFICIENCY,
) -> float:
    """Peak single-day harvest potential in litres."""
    return harvestable_liters(area_sqm, max_daily_rainfall_mm, runoff_coefficient, collection_efficiency)
