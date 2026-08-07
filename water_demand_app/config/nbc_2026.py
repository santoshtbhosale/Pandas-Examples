"""NBC-2026 water demand constants and calculation parameters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Brand colors
BRAND_NAVY = "#001F3F"
BRAND_ORANGE = "#F37021"
BRAND_DARK_GRAY = "#34495E"
BRAND_HEADER_GRAY = "#7F8C8D"
BRAND_DEMAND_ORANGE = "#E67E22"
BRAND_UGT_TEAL = "#16A085"
BRAND_STP_PURPLE = "#8E44AD"

# Residential LPCD (Liters Per Capita Per Day) — NBC 2026
RES_DOMESTIC_LPCD = 105
RES_FLUSHING_LPCD = 30
RES_TOTAL_LPCD = 135

# Kitchen water (litres/day per flat) — NBC fixture-based allowance
KITCHEN_LPD_PER_FLAT: Dict[str, int] = {
    "1BHK": 25,
    "2BHK": 35,
    "3BHK": 45,
    "PH": 55,
}

# Default population per flat type when BHK mix is used
BHK_POPULATION: Dict[str, int] = {
    "1BHK": 2,
    "2BHK": 4,
    "3BHK": 5,
    "PH": 5,
}

BUILDING_TYPES: Tuple[str, ...] = (
    "High Rise Tower",
    "Mid Rise Tower",
    "Low Rise",
    "Bungalow",
    "Row House",
    "Villa",
)

# Staff dropdowns
STAFF_ENGINEERS: Tuple[str, ...] = (
    "AKASH KHADE",
    "SWAPNIL",
    "RAHUL PATIL",
    "PRATHMESH GAIKWAD",
    "OTHER",
)
STAFF_APPROVAL: Tuple[str, ...] = (
    "AKASH",
    "SWAPNIL",
    "PRATHMESH GAIKWAD",
    "OTHER",
)

# Plot configuration
PLOT_MODE_DUAL = "dual"
PLOT_MODE_SINGLE = "single"
PLOT_MODE_LABELS: Dict[str, str] = {
    "Dual (Plot-A & Plot-B)": PLOT_MODE_DUAL,
    "Single Plot": PLOT_MODE_SINGLE,
}
PLOTS = ("Plot-A", "Plot-B")

# Project type — controls HVAC visibility
PROJECT_TYPE_RESIDENTIAL = "residential"
PROJECT_TYPE_MIXED = "residential_commercial"
PROJECT_TYPE_COMMERCIAL = "commercial"
PROJECT_TYPE_LABELS: Dict[str, str] = {
    "Residential": PROJECT_TYPE_RESIDENTIAL,
    "Residential + Commercial": PROJECT_TYPE_MIXED,
    "Commercial": PROJECT_TYPE_COMMERCIAL,
}

# Landscape NBC-2026
LANDSCAPE_L_PER_SQM = 6
WET_SEASON_LANDSCAPE_FACTOR = 1000 / 4590

# STP parameters
SEWAGE_GENERATION_FACTOR = 0.90
STP_TREATED_WATER_PER_KLD = 882
STP_ROUNDING_KLD = 10

# UGT storage days
UGT_DOMESTIC_DAYS = 2
UGT_FLUSHING_DAYS = 1
UGT_FIRE_DAYS = 1

# NBC 2016 Part 4 — residential fire water storage (litres) by building height (m)
FIRE_TANK_RESIDENTIAL_BY_HEIGHT: Tuple[Tuple[float, int], ...] = (
    (15.0, 50_000),
    (24.0, 100_000),
    (30.0, 200_000),
    (45.0, 300_000),
    (60.0, 400_000),
    (9999.0, 500_000),
)

COMPANY_NAME = "AMERICAN EDGE ENGINEERS PVT. LTD."
COMPANY_FOOTER = (
    "American Edge Engineers Pvt. Ltd. | Austin | New York | Pune | Info@americanedgeee.com"
)
COMPANY_ADDRESS = (
    "S.No.29/21, Office No-101, First Floor, Ganesh Primavera Building, "
    "Above Chetak Showroom, Ambegoan Budruk, Pune-411046"
)
COMPANY_CONTACT = "Info@americanedgeee.com, Mo-No-9623134045/8087009611"


def active_plots(plot_mode: str = PLOT_MODE_DUAL) -> Tuple[str, ...]:
    if plot_mode == PLOT_MODE_SINGLE:
        return ("Plot-A",)
    return PLOTS


def plot_choices(plot_mode: str = PLOT_MODE_DUAL) -> List[str]:
    return list(active_plots(plot_mode))


def hvac_applicable(project_type: str) -> bool:
    return project_type in (PROJECT_TYPE_MIXED, PROJECT_TYPE_COMMERCIAL)


def fire_tank_capacity_liters(building_height_m: float) -> int:
    """NBC 2016 Part 4 residential static water storage by height."""
    height = max(0.0, float(building_height_m or 0))
    for limit, capacity in FIRE_TANK_RESIDENTIAL_BY_HEIGHT:
        if height <= limit:
            return capacity
    return FIRE_TANK_RESIDENTIAL_BY_HEIGHT[-1][1]


def kitchen_water_lpd(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return (
        flats_1bhk * KITCHEN_LPD_PER_FLAT["1BHK"]
        + flats_2bhk * KITCHEN_LPD_PER_FLAT["2BHK"]
        + flats_3bhk * KITCHEN_LPD_PER_FLAT["3BHK"]
        + flats_penthouse * KITCHEN_LPD_PER_FLAT["PH"]
    )


def bhk_population(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return (
        flats_1bhk * BHK_POPULATION["1BHK"]
        + flats_2bhk * BHK_POPULATION["2BHK"]
        + flats_3bhk * BHK_POPULATION["3BHK"]
        + flats_penthouse * BHK_POPULATION["PH"]
    )


def bhk_flat_count(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return flats_1bhk + flats_2bhk + flats_3bhk + flats_penthouse


@dataclass(frozen=True)
class CommercialTypeSpec:
    label: str
    density_divisor: float  # sq.m per person (NBC occupant load)
    domestic_lpcd: int
    flushing_lpcd: int
    use_ceil: bool = False
    nbc_reference: str = ""

    @property
    def total_lpcd(self) -> int:
        return self.domestic_lpcd + self.flushing_lpcd


# NBC 2016 / 2026 Part 9 Table 7 — Occupant Load (sq.m per person)
COMMERCIAL_TYPES: Dict[str, CommercialTypeSpec] = {
    "Shop - Ground Floor": CommercialTypeSpec(
        "Shop - Ground Floor", 3.0, 25, 20, nbc_reference="Mercantile — ground floor"
    ),
    "Shop - Upper Floor": CommercialTypeSpec(
        "Shop - Upper Floor", 6.0, 25, 20, nbc_reference="Mercantile — upper floors"
    ),
    "Shop": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),
    "Office": CommercialTypeSpec("Office", 10.0, 25, 20, nbc_reference="Business"),
    "Restaurant": CommercialTypeSpec(
        "Restaurant", 1.4, 55, 15, use_ceil=True, nbc_reference="Assembly — dining"
    ),
    "Food Court": CommercialTypeSpec("Food Court", 1.4, 55, 15, use_ceil=True, nbc_reference="Assembly"),
    "Banquet Hall": CommercialTypeSpec("Banquet Hall", 1.4, 55, 15, use_ceil=True, nbc_reference="Assembly"),
    "Cinema / Auditorium": CommercialTypeSpec(
        "Cinema / Auditorium", 1.0, 25, 10, use_ceil=True, nbc_reference="Assembly"
    ),
    "Clubhouse": CommercialTypeSpec("Clubhouse", 10.0, 25, 20, nbc_reference="Assembly"),
    "Hospital": CommercialTypeSpec("Hospital", 15.0, 340, 110, nbc_reference="Institutional"),
    "School / Classroom": CommercialTypeSpec("School / Classroom", 4.0, 25, 20, nbc_reference="Educational"),
    "School": CommercialTypeSpec("School / Classroom", 4.0, 25, 20),
    "Mall": CommercialTypeSpec("Mall", 5.0, 25, 20, nbc_reference="Mercantile"),
    "Bank": CommercialTypeSpec("Bank", 10.0, 25, 20, nbc_reference="Business"),
    "Library": CommercialTypeSpec("Library", 4.6, 25, 20, nbc_reference="Assembly"),
    "Gymnasium": CommercialTypeSpec("Gymnasium", 1.8, 25, 20, use_ceil=True, nbc_reference="Assembly"),
    "Warehouse / Storage": CommercialTypeSpec(
        "Warehouse / Storage", 30.0, 25, 10, nbc_reference="Storage"
    ),
    "Parking": CommercialTypeSpec("Parking", 50.0, 25, 10, nbc_reference="Parking"),
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
