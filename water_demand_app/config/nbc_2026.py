"""NBC-2026 water demand constants and calculation parameters."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Brand colors
BRAND_NAVY = "#001F3F"
BRAND_ORANGE = "#F37021"
BRAND_DARK_GRAY = "#34495E"
BRAND_HEADER_GRAY = "#7F8C8D"
BRAND_DEMAND_ORANGE = "#E67E22"
BRAND_UGT_TEAL = "#16A085"
BRAND_STP_PURPLE = "#8E44AD"

# Residential LPCD — NBC Part 9
RES_DOMESTIC_LPCD = 105
RES_FLUSHING_LPCD = 30
RES_TOTAL_LPCD = 135

# Kitchen water (L/day per flat)
KITCHEN_LPD_PER_FLAT: Dict[str, int] = {
    "1BHK": 25,
    "2BHK": 35,
    "3BHK": 45,
    "4BHK": 50,
    "PH": 55,
}

# Residential occupancy per flat type (NBC reference screenshots)
BHK_POPULATION: Dict[str, int] = {
    "1BHK": 2,
    "2BHK": 4,
    "3BHK": 5,
    "4BHK": 6,
    "PH": 5,
}

BUILDING_CONFIG_EXAMPLES: Tuple[str, ...] = (
    "G+7",
    "G+12",
    "2B+G+21",
    "3B+G+30",
    "G+4",
    "G+20",
    "Custom",
)

BUILDING_TYPES: Tuple[str, ...] = (
    "Residential Apartment",
    "High Rise Tower",
    "Mid Rise Tower",
    "Low Rise",
    "Bungalow",
    "Row House",
    "Villa",
    "Hotel",
    "Hospital",
    "Commercial",
    "Industrial",
)

# Staff dropdowns — per Comments.docx
STAFF_NAMES: Tuple[str, ...] = ("Akash", "Vaibhav", "Sachin", "Omkar")
STAFF_ENGINEERS: Tuple[str, ...] = STAFF_NAMES
STAFF_APPROVAL: Tuple[str, ...] = STAFF_NAMES

# Plot configuration
PLOT_MODE_DUAL = "dual"
PLOT_MODE_SINGLE = "single"
PLOT_MODE_LABELS: Dict[str, str] = {
    "Plot A + B": PLOT_MODE_DUAL,
    "Single Plot": PLOT_MODE_SINGLE,
}
PLOTS = ("Plot-A", "Plot-B")
PLOT_SIMPLE = "Plot"

# Project types
PROJECT_TYPE_RESIDENTIAL = "residential"
PROJECT_TYPE_COMMERCIAL = "commercial"
PROJECT_TYPE_MIXED = "mixed_use"
PROJECT_TYPE_INDUSTRIAL = "industrial"
PROJECT_TYPE_HOSPITAL = "hospital"
PROJECT_TYPE_HOTEL = "hotel"
PROJECT_TYPE_SCHOOL = "school"
PROJECT_TYPE_MALL = "mall"
PROJECT_TYPE_IT_PARK = "it_park"

PROJECT_TYPE_LABELS: Dict[str, str] = {
    "Residential": PROJECT_TYPE_RESIDENTIAL,
    "Commercial": PROJECT_TYPE_COMMERCIAL,
    "Mixed Use": PROJECT_TYPE_MIXED,
    "Industrial": PROJECT_TYPE_INDUSTRIAL,
    "Hospital": PROJECT_TYPE_HOSPITAL,
    "Hotel": PROJECT_TYPE_HOTEL,
    "School": PROJECT_TYPE_SCHOOL,
    "Mall": PROJECT_TYPE_MALL,
    "IT Park": PROJECT_TYPE_IT_PARK,
}

# Swimming pool
POOL_APPLICABLE = "applicable"
POOL_NOT_APPLICABLE = "not_applicable"
POOL_STATUS_LABELS: Dict[str, str] = {
    "Applicable": POOL_APPLICABLE,
    "Not Applicable": POOL_NOT_APPLICABLE,
}

# Landscape
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

# NBC Part 4 / Table 7 — static fire water storage (litres) by height (m) — residential
FIRE_TANK_RESIDENTIAL_BY_HEIGHT: Tuple[Tuple[float, int], ...] = (
    (15.0, 50_000),
    (24.0, 100_000),
    (30.0, 200_000),
    (45.0, 300_000),
    (60.0, 400_000),
    (9999.0, 500_000),
)

# Commercial / institutional fire tank by height (NBC Table 7 business buildings)
FIRE_TANK_COMMERCIAL_BY_HEIGHT: Tuple[Tuple[float, int], ...] = (
    (10.0, 10_000),
    (15.0, 50_000),
    (24.0, 100_000),
    (30.0, 150_000),
    (45.0, 200_000),
    (60.0, 250_000),
    (9999.0, 300_000),
)

FLOOR_HEIGHT_M = 3.0

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


def plot_dropdown_choices(plot_mode: str = PLOT_MODE_DUAL) -> List[str]:
    """Plot labels shown in residential/commercial row dropdowns."""
    if plot_mode == PLOT_MODE_SINGLE:
        return [PLOT_SIMPLE]
    return [PLOT_SIMPLE, *PLOTS]


def normalize_plot_for_calc(plot: str) -> str:
    """Map UI label 'Plot' to internal Plot-A for calculations and exports."""
    if plot == PLOT_SIMPLE:
        return "Plot-A"
    return plot


def ui_plot_label(stored_plot: str, plot_mode: str = PLOT_MODE_DUAL) -> str:
    """Convert stored plot key to the label shown in dropdowns."""
    choices = plot_dropdown_choices(plot_mode)
    if plot_mode == PLOT_MODE_SINGLE and stored_plot in (PLOT_SIMPLE, "Plot-A"):
        return PLOT_SIMPLE
    if stored_plot in choices:
        return stored_plot
    return choices[0]


def project_type_key(label: str) -> str:
    return PROJECT_TYPE_LABELS.get(label, PROJECT_TYPE_MIXED)


def show_residential_section(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_RESIDENTIAL,
        PROJECT_TYPE_MIXED,
    )


def show_commercial_section(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_COMMERCIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_INDUSTRIAL,
        PROJECT_TYPE_HOSPITAL,
        PROJECT_TYPE_HOTEL,
        PROJECT_TYPE_SCHOOL,
        PROJECT_TYPE_MALL,
        PROJECT_TYPE_IT_PARK,
    )


def hvac_applicable(project_type: str) -> bool:
    """HVAC only for Commercial and IT Park projects."""
    return project_type in (PROJECT_TYPE_COMMERCIAL, PROJECT_TYPE_IT_PARK)


def parse_building_config(config: str) -> Tuple[int, float]:
    """Parse G+7 / 2B+G+21 style config -> (floors_above_ground, estimated_height_m)."""
    text = (config or "").strip().upper().replace(" ", "")
    if not text or text == "CUSTOM":
        return 0, 0.0
    basements = 0
    above = 0
    m = re.match(r"^((\d+)B\+)?G\+(\d+)$", text)
    if m:
        basements = int(m.group(2) or 0)
        above = int(m.group(3))
    elif re.match(r"^G\+(\d+)$", text):
        above = int(re.match(r"^G\+(\d+)$", text).group(1))
    total_floors = basements + 1 + above
    height = total_floors * FLOOR_HEIGHT_M
    return above, height


def fire_tank_capacity_liters(building_height_m: float, building_type: str = "") -> int:
    height = max(0.0, float(building_height_m or 0))
    btype = (building_type or "").lower()
    table = FIRE_TANK_RESIDENTIAL_BY_HEIGHT
    if any(k in btype for k in ("commercial", "office", "mall", "hotel", "hospital", "industrial", "it")):
        table = FIRE_TANK_COMMERCIAL_BY_HEIGHT
    for limit, capacity in table:
        if height <= limit:
            return capacity
    return table[-1][1]


def kitchen_water_lpd(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_4bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return (
        flats_1bhk * KITCHEN_LPD_PER_FLAT["1BHK"]
        + flats_2bhk * KITCHEN_LPD_PER_FLAT["2BHK"]
        + flats_3bhk * KITCHEN_LPD_PER_FLAT["3BHK"]
        + flats_4bhk * KITCHEN_LPD_PER_FLAT["4BHK"]
        + flats_penthouse * KITCHEN_LPD_PER_FLAT["PH"]
    )


def bhk_population(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_4bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return (
        flats_1bhk * BHK_POPULATION["1BHK"]
        + flats_2bhk * BHK_POPULATION["2BHK"]
        + flats_3bhk * BHK_POPULATION["3BHK"]
        + flats_4bhk * BHK_POPULATION["4BHK"]
        + flats_penthouse * BHK_POPULATION["PH"]
    )


def bhk_flat_count(
    flats_1bhk: int = 0,
    flats_2bhk: int = 0,
    flats_3bhk: int = 0,
    flats_4bhk: int = 0,
    flats_penthouse: int = 0,
) -> int:
    return flats_1bhk + flats_2bhk + flats_3bhk + flats_4bhk + flats_penthouse


@dataclass(frozen=True)
class CommercialTypeSpec:
    label: str
    density_divisor: float
    domestic_lpcd: int
    flushing_lpcd: int
    use_ceil: bool = False
    nbc_reference: str = ""

    @property
    def total_lpcd(self) -> int:
        return self.domestic_lpcd + self.flushing_lpcd


# Commercial Occupancy Types — NBC Part 9 Table 7 occupant load
COMMERCIAL_OCCUPANCY_TYPES: Tuple[str, ...] = (
    "Office",
    "Retail Shop",
    "Restaurant",
    "Hospital",
    "School",
    "College",
    "Cinema",
    "Mall",
    "Hotel",
    "Warehouse",
    "IT Office",
    "Showroom",
)

COMMERCIAL_TYPES: Dict[str, CommercialTypeSpec] = {
    "Office": CommercialTypeSpec("Office", 10.0, 25, 20, nbc_reference="Business"),
    "IT Office": CommercialTypeSpec("IT Office", 10.0, 25, 20, nbc_reference="Business / IT"),
    "Retail Shop": CommercialTypeSpec("Retail Shop", 3.0, 25, 20, nbc_reference="Mercantile GF"),
    "Showroom": CommercialTypeSpec("Showroom", 5.0, 25, 20, nbc_reference="Mercantile"),
    "Restaurant": CommercialTypeSpec("Restaurant", 1.4, 55, 15, use_ceil=True, nbc_reference="Assembly"),
    "Hospital": CommercialTypeSpec("Hospital", 15.0, 340, 110, nbc_reference="Institutional"),
    "School": CommercialTypeSpec("School", 4.0, 25, 20, nbc_reference="Educational"),
    "College": CommercialTypeSpec("College", 4.0, 25, 20, nbc_reference="Educational"),
    "Cinema": CommercialTypeSpec("Cinema", 1.0, 25, 10, use_ceil=True, nbc_reference="Assembly"),
    "Mall": CommercialTypeSpec("Mall", 5.0, 25, 20, nbc_reference="Mercantile"),
    "Hotel": CommercialTypeSpec("Hotel", 10.0, 55, 20, nbc_reference="Residential-transient"),
    "Warehouse": CommercialTypeSpec("Warehouse", 30.0, 25, 10, nbc_reference="Storage"),
    # Legacy aliases for backward compatibility
    "Shop - Ground Floor": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),
    "Shop - Upper Floor": CommercialTypeSpec("Shop - Upper Floor", 6.0, 25, 20),
    "Shop": CommercialTypeSpec("Retail Shop", 3.0, 25, 20),
    "Food Court": CommercialTypeSpec("Food Court", 1.4, 55, 15, use_ceil=True),
    "Banquet Hall": CommercialTypeSpec("Banquet Hall", 1.4, 55, 15, use_ceil=True),
    "Cinema / Auditorium": CommercialTypeSpec("Cinema", 1.0, 25, 10, use_ceil=True),
    "Clubhouse": CommercialTypeSpec("Clubhouse", 10.0, 25, 20),
    "School / Classroom": CommercialTypeSpec("School", 4.0, 25, 20),
    "Bank": CommercialTypeSpec("Bank", 10.0, 25, 20),
    "Library": CommercialTypeSpec("Library", 4.6, 25, 20),
    "Gymnasium": CommercialTypeSpec("Gymnasium", 1.8, 25, 20, use_ceil=True),
    "Warehouse / Storage": CommercialTypeSpec("Warehouse", 30.0, 25, 10),
    "Parking": CommercialTypeSpec("Parking", 50.0, 25, 10),
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
