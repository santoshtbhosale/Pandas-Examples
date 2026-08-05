"""NBC-2026 water demand constants and calculation parameters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

# Brand colors
BRAND_NAVY = "#001F3F"
BRAND_ORANGE = "#F37021"
BRAND_DARK_GRAY = "#34495E"
BRAND_HEADER_GRAY = "#7F8C8D"
BRAND_DEMAND_ORANGE = "#E67E22"
BRAND_UGT_TEAL = "#16A085"
BRAND_STP_PURPLE = "#8E44AD"

# Residential LPCD (Liters Per Capita Per Day)
RES_DOMESTIC_LPCD = 105
RES_FLUSHING_LPCD = 30
RES_TOTAL_LPCD = 135

# Landscape NBC-2026
LANDSCAPE_L_PER_SQM = 6
WET_SEASON_LANDSCAPE_FACTOR = 1000 / 4590  # derived from reference project

# STP parameters
SEWAGE_GENERATION_FACTOR = 0.90
STP_TREATED_WATER_PER_KLD = 882  # liters per KLD of STP capacity
STP_ROUNDING_KLD = 10

# UGT storage days
UGT_DOMESTIC_DAYS = 2
UGT_FLUSHING_DAYS = 1
UGT_FIRE_DAYS = 1

COMPANY_NAME = "AMERICAN EDGE ENGINEERS PVT. LTD."
COMPANY_FOOTER = (
    "American Edge Engineers Pvt. Ltd. | Austin | New York | Pune | Info@americanedgeee.com"
)
COMPANY_ADDRESS = (
    "S.No.29/21, Office No-101, First Floor, Ganesh Primavera Building, "
    "Above Chetak Showroom, Ambegoan Budruk, Pune-411046"
)
COMPANY_CONTACT = "Info@americanedgeee.com, Mo-No-9623134045/8087009611"

PLOTS = ("Plot-A", "Plot-B")


@dataclass(frozen=True)
class CommercialTypeSpec:
    label: str
    density_divisor: float
    domestic_lpcd: int
    flushing_lpcd: int
    use_ceil: bool = False

    @property
    def total_lpcd(self) -> int:
        return self.domestic_lpcd + self.flushing_lpcd


COMMERCIAL_TYPES: Dict[str, CommercialTypeSpec] = {
    "Shop - Ground Floor": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),
    "Shop - Upper Floor": CommercialTypeSpec("Shop - Upper Floor", 6.0, 25, 20),
    "Office": CommercialTypeSpec("Office", 10.0, 25, 20),
    "Restaurant": CommercialTypeSpec("Restaurant", 1.4, 55, 15, use_ceil=True),
    "Food Court": CommercialTypeSpec("Food Court", 10.0, 25, 10),
    "Clubhouse": CommercialTypeSpec("Clubhouse", 10.0, 25, 20),
    "Shop": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),
    "Hospital": CommercialTypeSpec("Hospital", 15.0, 340, 110),
    "School": CommercialTypeSpec("School", 10.0, 25, 20),
    "Mall": CommercialTypeSpec("Mall", 5.0, 25, 20),
    "Custom": CommercialTypeSpec("Custom", 10.0, 25, 20),
}


def commercial_population(area_sqm: float, spec: CommercialTypeSpec) -> int:
    if area_sqm <= 0:
        return 0
    raw = area_sqm / spec.density_divisor
    if spec.use_ceil:
        return int(math.ceil(raw))
    return int(round(raw))


def say_stp_capacity_kld(sewage_lpd: float) -> float:
    sewage_kld = sewage_lpd / 1000.0
    if sewage_kld <= 0:
        return 0.0
    return math.ceil(sewage_kld / STP_ROUNDING_KLD) * STP_ROUNDING_KLD


def round_storage_liters(value: float) -> int:
    if value <= 0:
        return 0
    return int(math.ceil(value / 1000.0) * 1000)


def residential_demand(population: int) -> Tuple[int, int, int]:
    domestic = population * RES_DOMESTIC_LPCD
    flushing = population * RES_FLUSHING_LPCD
    total = population * RES_TOTAL_LPCD
    return domestic, flushing, total


def commercial_demand(population: int, spec: CommercialTypeSpec) -> Tuple[int, int, int]:
    domestic = population * spec.domestic_lpcd
    flushing = population * spec.flushing_lpcd
    total = population * spec.total_lpcd
    return domestic, flushing, total


def landscape_demand(area_sqm: float) -> int:
    return int(round(area_sqm * LANDSCAPE_L_PER_SQM))


def wet_landscape_demand(dry_landscape_lpd: int) -> int:
    if dry_landscape_lpd <= 0:
        return 0
    return int(round(dry_landscape_lpd * WET_SEASON_LANDSCAPE_FACTOR))


def treated_water_lpd(say_stp_kld: float) -> int:
    return int(say_stp_kld * STP_TREATED_WATER_PER_KLD)
