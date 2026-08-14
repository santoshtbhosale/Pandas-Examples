#!/usr/bin/env python3
"""
American Edge Engineers - Water Demand Report Generator
Single-file production application with NBC-2026 calculations.
Version 2.0.0
"""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import hashlib
import shutil
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import customtkinter as ctk
from PIL import Image as PILImage
from tkcalendar import DateEntry
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "water_demand.db")
LOGO_PATH = os.path.join(APP_DIR, "logo.png")
JSON_SCHEMA_VERSION = "1.0"


# ==================== config/nbc_2026.py ====================
"""NBC-2026 water demand constants and calculation parameters."""



# Brand colors — American Edge Engineers corporate palette
BRAND_NAVY = "#123B5D"
BRAND_ORANGE = "#F28C28"
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
PROJECT_TYPE_UNSET = ""
PROJECT_TYPE_RESIDENTIAL = "residential"
PROJECT_TYPE_COMMERCIAL = "commercial"
PROJECT_TYPE_MIXED = "mixed_use"
PROJECT_TYPE_INDUSTRIAL = "industrial"
PROJECT_TYPE_HOSPITAL = "hospital"
PROJECT_TYPE_HOTEL = "hotel"
PROJECT_TYPE_SCHOOL = "school"
PROJECT_TYPE_COLLEGE = "college"
PROJECT_TYPE_MALL = "mall"
PROJECT_TYPE_IT_PARK = "it_park"
PROJECT_TYPE_WAREHOUSE = "warehouse"
PROJECT_TYPE_TOWNSHIP = "township"

PROJECT_TYPE_LABELS: Dict[str, str] = {
    "Residential": PROJECT_TYPE_RESIDENTIAL,
    "Commercial": PROJECT_TYPE_COMMERCIAL,
    "Mixed Use": PROJECT_TYPE_MIXED,
    "Industrial": PROJECT_TYPE_INDUSTRIAL,
    "Hospital": PROJECT_TYPE_HOSPITAL,
    "Hotel": PROJECT_TYPE_HOTEL,
    "School": PROJECT_TYPE_SCHOOL,
    "College": PROJECT_TYPE_COLLEGE,
    "Shopping Mall": PROJECT_TYPE_MALL,
    "Mall": PROJECT_TYPE_MALL,
    "IT Park": PROJECT_TYPE_IT_PARK,
    "Warehouse": PROJECT_TYPE_WAREHOUSE,
    "Township": PROJECT_TYPE_TOWNSHIP,
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


PROJECT_TYPE_PLACEHOLDER = "— Select Project Type —"


def is_project_type_set(project_type: str) -> bool:
    return bool(project_type and project_type != PROJECT_TYPE_UNSET)


def project_type_key(label: str) -> str:
    if not label or label == PROJECT_TYPE_PLACEHOLDER:
        return PROJECT_TYPE_UNSET
    return PROJECT_TYPE_LABELS.get(label, PROJECT_TYPE_MIXED)


def project_type_label(project_type: str) -> str:
    if not is_project_type_set(project_type):
        return PROJECT_TYPE_PLACEHOLDER
    for label, key in PROJECT_TYPE_LABELS.items():
        if key == project_type:
            return label
    return "Mixed Use"


def show_residential_section(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_RESIDENTIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_TOWNSHIP,
    )


def show_commercial_section(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_COMMERCIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_INDUSTRIAL,
        PROJECT_TYPE_SCHOOL,
        PROJECT_TYPE_COLLEGE,
        PROJECT_TYPE_MALL,
        PROJECT_TYPE_IT_PARK,
        PROJECT_TYPE_WAREHOUSE,
        PROJECT_TYPE_TOWNSHIP,
    )


def show_hospital_section(project_type: str) -> bool:
    return project_type == PROJECT_TYPE_HOSPITAL


def show_hotel_section(project_type: str) -> bool:
    return project_type == PROJECT_TYPE_HOTEL


def show_food_court_section(project_type: str) -> bool:
    return project_type == PROJECT_TYPE_MALL


def show_swimming_section(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_RESIDENTIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_HOTEL,
        PROJECT_TYPE_TOWNSHIP,
    )


def hvac_applicable(project_type: str) -> bool:
    return project_type in (
        PROJECT_TYPE_COMMERCIAL,
        PROJECT_TYPE_IT_PARK,
        PROJECT_TYPE_MALL,
        PROJECT_TYPE_INDUSTRIAL,
        PROJECT_TYPE_TOWNSHIP,
    )


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
    else:
        return 0, 0.0
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

# ==================== config/environmental.py ====================
"""Solid waste and sewage generation engineering constants."""


# Solid waste — kg per capita per day
RESIDENTIAL_WASTE_KG_PER_CAPITA_DAY = 0.45
COMMERCIAL_WASTE_KG_PER_CAPITA_DAY = 0.25

RESIDENTIAL_WET_WASTE_FRACTION = 0.60
RESIDENTIAL_DRY_WASTE_FRACTION = 0.40
COMMERCIAL_WET_WASTE_FRACTION = 0.40
COMMERCIAL_DRY_WASTE_FRACTION = 0.60

RESIDENTIAL_E_WASTE_KG_PER_CAPITA_YEAR = 1.0
COMMERCIAL_E_WASTE_KG_PER_CAPITA_YEAR = 1.5

GARDEN_WASTE_POP_DIVISOR = 47.25  # Residential Population / 47.25 = Garden Waste (kgs/day)

STP_SLUDGE_KG_PER_KLD_DAY = 0.20  # 370 KLD → 74 Kgs/Day

OWC_AREA_LOW_FACTOR = 70 / 900.0
OWC_AREA_HIGH_FACTOR = 75 / 900.0

# Sewage generation — population based (L/capita/day before 90% factor)
RESIDENTIAL_SEWAGE_LPCD = 135
COMMERCIAL_SEWAGE_LPCD = 45
SEWAGE_GENERATION_PERCENT = 0.90

SEWAGE_STP_AREA_LOW_FACTOR = 140 / 370.0
SEWAGE_STP_AREA_HIGH_FACTOR = 160 / 370.0

# ==================== config/page_visibility.py ====================
"""Navigation and section visibility by project type."""




# Sidebar page keys in wizard order
WIZARD_PAGE_ORDER: Tuple[str, ...] = (
    "Project",
    "Residential",
    "Commercial",
    "Hospital",
    "Hotel",
    "FoodCourt",
    "Landscape",
    "Swimming",
    "HVAC",
    "UGT",
    "Sewage",
    "OHT",
    "STP",
    "SolidWaste",
    "Preview",
    "Report",
    "Settings",
)

_COMMON_TAIL: FrozenSet[str] = frozenset(
    {
        "Landscape",
        "UGT",
        "Sewage",
        "OHT",
        "STP",
        "SolidWaste",
        "Preview",
        "Report",
        "Settings",
    }
)

_PAGES_BY_TYPE: dict[str, FrozenSet[str]] = {
    PROJECT_TYPE_RESIDENTIAL: frozenset({"Project", "Residential", *_COMMON_TAIL}),
    PROJECT_TYPE_COMMERCIAL: frozenset({"Project", "Commercial", "HVAC", *_COMMON_TAIL}),
    PROJECT_TYPE_MIXED: frozenset(
        {"Project", "Residential", "Commercial", "Swimming", "HVAC", *_COMMON_TAIL}
    ),
    PROJECT_TYPE_HOSPITAL: frozenset({"Project", "Hospital", *_COMMON_TAIL}),
    PROJECT_TYPE_HOTEL: frozenset({"Project", "Hotel", "Swimming", *_COMMON_TAIL}),
    PROJECT_TYPE_SCHOOL: frozenset(
        {
            "Project",
            "Commercial",
            "Landscape",
            "UGT",
            "Sewage",
            "OHT",
            "STP",
            "SolidWaste",
            "Preview",
            "Report",
            "Settings",
        }
    ),
    PROJECT_TYPE_COLLEGE: frozenset(
        {
            "Project",
            "Commercial",
            "Landscape",
            "UGT",
            "Sewage",
            "OHT",
            "STP",
            "SolidWaste",
            "Preview",
            "Report",
            "Settings",
        }
    ),
    PROJECT_TYPE_IT_PARK: frozenset({"Project", "Commercial", "HVAC", *_COMMON_TAIL}),
    PROJECT_TYPE_MALL: frozenset({"Project", "Commercial", "HVAC", "FoodCourt", *_COMMON_TAIL}),
    PROJECT_TYPE_INDUSTRIAL: frozenset({"Project", "Commercial", *_COMMON_TAIL}),
    PROJECT_TYPE_WAREHOUSE: frozenset({"Project", "Commercial", *_COMMON_TAIL}),
    PROJECT_TYPE_TOWNSHIP: frozenset(
        {"Project", "Residential", "Commercial", "Swimming", "HVAC", *_COMMON_TAIL}
    ),
}


def visible_pages(project_type: str) -> FrozenSet[str]:
    if not is_project_type_set(project_type):
        return frozenset({"Project"})
    return _PAGES_BY_TYPE.get(project_type, _PAGES_BY_TYPE[PROJECT_TYPE_MIXED])


def visible_nav_labels(project_type: str) -> Tuple[str, ...]:
    """Human-readable summary of which workflow sections apply."""
    if not is_project_type_set(project_type):
        return ("Select project type to begin",)
    pages = visible_pages(project_type)
    labels = []
    for key in WIZARD_PAGE_ORDER:
        if key == "Project" or key not in pages:
            continue
        labels.append(key)
    return tuple(labels) if labels else ("Project",)


def wizard_next_page(current: str, project_type: str) -> str | None:
    pages = visible_pages(project_type)
    found = False
    for key in WIZARD_PAGE_ORDER:
        if key not in pages:
            continue
        if found:
            return key
        if key == current:
            found = True
    return None


def wizard_first_page_after_project(project_type: str) -> str:
    if not is_project_type_set(project_type):
        return "Project"
    for key in WIZARD_PAGE_ORDER:
        if key == "Project":
            continue
        if key in visible_pages(project_type):
            return key
    return "Preview"

# ==================== models/project.py ====================




@dataclass
class RevisionInfo:
    date: str = ""
    revision_no: str = "R0"
    description: str = "ISSUED FOR REFERENCE"
    prepared_by: str = ""
    checked_by: str = ""
    approved_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisionInfo":
        return cls(**{k: data.get(k, getattr(cls, k, "")) for k in cls.__dataclass_fields__})


@dataclass
class ProjectData:
    project_id: str = ""
    project_name: str = "PROPOSED RESIDENTIAL"
    client_name: str = "MR. ABC"
    project_location: str = "PUNE"
    engineer_name: str = "Akash"
    project_no: str = ""
    date: str = ""
    plot_mode: str = PLOT_MODE_DUAL
    project_type: str = PROJECT_TYPE_MIXED
    building_config: str = "G+7"
    building_height_m: float = 0.0
    num_wings: int = 1
    building_type: str = "Residential Apartment"
    client_address: str = ""
    client_contact: str = ""
    client_email: str = ""
    client_gst: str = ""
    city: str = ""
    state: str = ""
    rainfall_zone: str = ""
    climate: str = ""
    revision: RevisionInfo = field(default_factory=RevisionInfo)

    def __post_init__(self) -> None:
        if not self.project_id:
            self.project_id = "WD-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not self.date:
            self.date = datetime.now().strftime("%d-%m-%Y")
        if self.building_height_m <= 0 and self.building_config:
            _, est_height = parse_building_config(self.building_config)
            if est_height > 0:
                self.building_height_m = est_height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "project_location": self.project_location,
            "engineer_name": self.engineer_name,
            "project_no": self.project_no,
            "date": self.date,
            "plot_mode": self.plot_mode,
            "project_type": self.project_type,
            "building_config": self.building_config,
            "building_height_m": self.building_height_m,
            "num_wings": self.num_wings,
            "building_type": self.building_type,
            "client_address": self.client_address,
            "client_contact": self.client_contact,
            "client_email": self.client_email,
            "client_gst": self.client_gst,
            "city": self.city,
            "state": self.state,
            "rainfall_zone": self.rainfall_zone,
            "climate": self.climate,
            "revision": self.revision.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectData":
        revision_data = data.get("revision", {})
        if isinstance(revision_data, dict):
            revision = RevisionInfo.from_dict(revision_data)
        else:
            revision = RevisionInfo()
        return cls(
            project_id=data.get("project_id", ""),
            project_name=data.get("project_name", data.get("Project Name", "PROPOSED RESIDENTIAL")),
            client_name=data.get("client_name", data.get("Client Name", "MR. ABC")),
            project_location=data.get("project_location", data.get("Project Location", "PUNE")),
            engineer_name=data.get("engineer_name", data.get("Engineer Name", "Akash")),
            project_no=data.get("project_no", data.get("Project No.", "")),
            date=data.get("date", data.get("Date", "")),
            plot_mode=data.get("plot_mode", PLOT_MODE_DUAL),
            project_type=data.get("project_type", PROJECT_TYPE_MIXED),
            building_config=data.get("building_config", "G+7"),
            building_height_m=float(data.get("building_height_m", 0) or 0),
            num_wings=int(data.get("num_wings", 1) or 1),
            building_type=data.get("building_type", "Residential Apartment"),
            client_address=data.get("client_address", ""),
            client_contact=data.get("client_contact", ""),
            client_email=data.get("client_email", ""),
            client_gst=data.get("client_gst", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            rainfall_zone=data.get("rainfall_zone", ""),
            climate=data.get("climate", ""),
            revision=revision,
        )

    def legacy_dict(self) -> Dict[str, str]:
        return {
            "Project Name": self.project_name,
            "Client Name": self.client_name,
            "Project Location": self.project_location,
            "Engineer Name": self.engineer_name,
            "Project No.": self.project_no,
            "Date": self.date,
        }

# ==================== models/residential.py ====================




@dataclass
class ResidentialWing:
    plot: str = "Plot-A"
    wing: str = ""
    building_config: str = "G+7"
    building_type: str = "Residential Apartment"
    building_height_m: float = 0.0
    num_wings: int = 1
    flats: int = 0
    flats_1bhk: int = 0
    flats_2bhk: int = 0
    flats_3bhk: int = 0
    flats_4bhk: int = 0
    flats_penthouse: int = 0
    pop_per_flat: int = 5
    sort_order: int = 0

    def __post_init__(self) -> None:
        if self.building_height_m <= 0 and self.building_config:
            _, est_height = parse_building_config(self.building_config)
            if est_height > 0:
                self.building_height_m = est_height

    @property
    def has_bhk_mix(self) -> bool:
        return bhk_flat_count(
            self.flats_1bhk,
            self.flats_2bhk,
            self.flats_3bhk,
            self.flats_4bhk,
            self.flats_penthouse,
        ) > 0

    @property
    def effective_flats(self) -> int:
        bhk_total = bhk_flat_count(
            self.flats_1bhk,
            self.flats_2bhk,
            self.flats_3bhk,
            self.flats_4bhk,
            self.flats_penthouse,
        )
        return bhk_total if bhk_total > 0 else self.flats

    @property
    def population(self) -> int:
        if self.has_bhk_mix:
            return bhk_population(
                self.flats_1bhk,
                self.flats_2bhk,
                self.flats_3bhk,
                self.flats_4bhk,
                self.flats_penthouse,
            )
        return self.flats * self.pop_per_flat

    @property
    def kitchen_water(self) -> int:
        if not self.has_bhk_mix:
            return 0
        return kitchen_water_lpd(
            self.flats_1bhk,
            self.flats_2bhk,
            self.flats_3bhk,
            self.flats_4bhk,
            self.flats_penthouse,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResidentialWing":
        return cls(
            plot=data.get("plot", data.get("Plot", "Plot-A")),
            wing=data.get("wing", data.get("Wing", "")),
            building_config=data.get("building_config", data.get("Building Config", "G+7")),
            building_type=data.get("building_type", "Residential Apartment"),
            building_height_m=float(data.get("building_height_m", 0) or 0),
            num_wings=int(data.get("num_wings", data.get("No. Of Wings", 1)) or 1),
            flats=int(data.get("flats", data.get("No. Of Flats", 0)) or 0),
            flats_1bhk=int(data.get("flats_1bhk", 0) or 0),
            flats_2bhk=int(data.get("flats_2bhk", 0) or 0),
            flats_3bhk=int(data.get("flats_3bhk", 0) or 0),
            flats_4bhk=int(data.get("flats_4bhk", 0) or 0),
            flats_penthouse=int(data.get("flats_penthouse", data.get("flats_ph", 0)) or 0),
            pop_per_flat=int(data.get("pop_per_flat", data.get("Pop/Flat", 5)) or 5),
            sort_order=int(data.get("sort_order", 0)),
        )

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Plot": self.plot,
            "Wing": self.wing,
            "Building Config": self.building_config,
            "No. Of Flats": self.effective_flats,
            "Population": self.population,
        }

# ==================== models/commercial.py ====================




@dataclass
class CommercialUnit:
    plot: str = "Plot-A"
    block: str = "COMM-A"
    comm_type: str = "Shop - Ground Floor"
    floor_label: str = ""
    area_sqm: float = 0.0
    density_override: float = 0.0
    sort_order: int = 0

    def type_spec(self) -> CommercialTypeSpec:
        return COMMERCIAL_TYPES.get(self.comm_type, COMMERCIAL_TYPES["Shop - Ground Floor"])

    @property
    def auto_population(self) -> int:
        spec = self.type_spec()
        if self.density_override > 0:
            raw = self.area_sqm / self.density_override
            if spec.use_ceil:
                return int(math.ceil(raw))
            return int(round(raw))
        return commercial_population(self.area_sqm, spec)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommercialUnit":
        return cls(
            plot=data.get("plot", data.get("Plot", "Plot-A")),
            block=data.get("block", data.get("Block", "COMM-A")),
            comm_type=data.get("comm_type", data.get("Commercial Type", "Shop - Ground Floor")),
            floor_label=data.get("floor_label", data.get("Floor", "")),
            area_sqm=float(data.get("area_sqm", data.get("Area", 0)) or 0),
            density_override=float(data.get("density_override", 0) or 0),
            sort_order=int(data.get("sort_order", 0)),
        )

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Plot": self.plot,
            "Commercial Type": self.comm_type,
            "Area": self.area_sqm,
            "Auto Population": self.auto_population,
        }

# ==================== models/other_details.py ====================



@dataclass
class OHTDetail:
    plot: str = "Plot-A"
    wing: str = ""
    domestic_kld: float = 0.0
    flushing_kld: float = 0.0
    fire_break_kld: float = 0.0
    fire_oht_kld: float = 0.0
    sort_order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHTDetail":
        return cls(
            plot=data.get("plot", "Plot-A"),
            wing=data.get("wing", ""),
            domestic_kld=float(data.get("domestic_kld", 0) or 0),
            flushing_kld=float(data.get("flushing_kld", 0) or 0),
            fire_break_kld=float(data.get("fire_break_kld", 0) or 0),
            fire_oht_kld=float(data.get("fire_oht_kld", 0) or 0),
            sort_order=int(data.get("sort_order", 0)),
        )


@dataclass
class OtherDetails:
    landscape_area: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 765.0, "Plot-B": 762.0})
    swimming_pool: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 0.0, "Plot-B": 0.0})
    swimming_pool_status: Dict[str, str] = field(
        default_factory=lambda: {"Plot-A": "not_applicable", "Plot-B": "not_applicable"}
    )
    swimming_pool_na: Dict[str, bool] = field(default_factory=lambda: {"Plot-A": True, "Plot-B": True})
    hvac_water: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 0.0, "Plot-B": 0.0})
    fire_tank: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 300000.0, "Plot-B": 230000.0})
    fire_tank_commercial: Dict[str, Dict[str, float]] = field(default_factory=dict)
    oht_details: List[OHTDetail] = field(default_factory=list)

    def get_fire_tank(self, plot: str, block: str = "") -> float:
        if block and block in self.fire_tank_commercial.get(plot, {}):
            return self.fire_tank_commercial[plot][block]
        return self.fire_tank.get(plot, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "landscape_area": self.landscape_area,
            "swimming_pool": self.swimming_pool,
            "swimming_pool_status": self.swimming_pool_status,
            "swimming_pool_na": self.swimming_pool_na,
            "hvac_water": self.hvac_water,
            "fire_tank": self.fire_tank,
            "fire_tank_commercial": self.fire_tank_commercial,
            "oht_details": [o.to_dict() for o in self.oht_details],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OtherDetails":
        legacy_fire = {}
        if "Fire Tank Plot-A" in data:
            legacy_fire = {
                "Plot-A": float(data.get("Fire Tank Plot-A", 300000) or 300000),
                "Plot-B": float(data.get("Fire Tank Plot-B", 230000) or 230000),
            }
        oht_list = [OHTDetail.from_dict(o) for o in data.get("oht_details", [])]
        pool_na = data.get("swimming_pool_na", {"Plot-A": True, "Plot-B": True})
        pool_status = data.get("swimming_pool_status", {})
        if not pool_status:
            pool_status = {
                plot: "not_applicable" if pool_na.get(plot, True) else "applicable"
                for plot in ("Plot-A", "Plot-B")
            }
        return cls(
            landscape_area=data.get("landscape_area", {"Plot-A": 765.0, "Plot-B": 762.0}),
            swimming_pool=data.get("swimming_pool", {"Plot-A": 0.0, "Plot-B": 0.0}),
            swimming_pool_status=pool_status,
            swimming_pool_na=pool_na,
            hvac_water=data.get("hvac_water", {"Plot-A": 0.0, "Plot-B": 0.0}),
            fire_tank=data.get("fire_tank", legacy_fire or {"Plot-A": 300000.0, "Plot-B": 230000.0}),
            fire_tank_commercial=data.get("fire_tank_commercial", {}),
            oht_details=oht_list,
        )

    def legacy_dict(self) -> Dict[str, float]:
        return {
            f"Fire Tank {plot}": self.fire_tank.get(plot, 0.0)
            for plot in ("Plot-A", "Plot-B")
        }

# ==================== models/calculations.py ====================



@dataclass
class WingResult:
    wing: str
    flats: int
    pop_per_flat: int
    population: int
    domestic_lpd: int
    flushing_lpd: int
    kitchen_water_lpd: int
    total_lpd: int


@dataclass
class CommercialResult:
    block: str
    comm_type: str
    floor_label: str
    area_sqm: float
    density: float
    population: int
    domestic_lpd: int
    flushing_lpd: int
    total_lpd: int


@dataclass
class UGTResult:
    description: str
    water_requirement_lpd: int
    storage_days: int
    total_storage_liters: int
    total_storage_kld: float


@dataclass
class STPResult:
    scope: str
    total_water_lpd: int
    sewage_lpd: int
    sewage_kld: float
    say_stp_kld: float
    treated_water_lpd: int
    reuse_flushing_lpd: int
    reuse_landscape_lpd: int
    reuse_hvac_lpd: int
    excess_treated_lpd: int


@dataclass
class PlotResults:
    plot: str
    residential_wings: List[WingResult] = field(default_factory=list)
    commercial_units: List[CommercialResult] = field(default_factory=list)
    res_population: int = 0
    com_population: int = 0
    total_population: int = 0
    res_domestic_lpd: int = 0
    res_flushing_lpd: int = 0
    res_total_lpd: int = 0
    com_domestic_lpd: int = 0
    com_flushing_lpd: int = 0
    com_total_lpd: int = 0
    landscape_dry_lpd: int = 0
    landscape_wet_lpd: int = 0
    swimming_pool_lpd: int = 0
    hvac_lpd: int = 0
    kitchen_water_lpd: int = 0
    dry_total_water_lpd: int = 0
    wet_total_water_lpd: int = 0
    dry_treated_water_lpd: int = 0
    wet_treated_water_lpd: int = 0
    dry_excess_treated_lpd: int = 0
    wet_excess_treated_lpd: int = 0
    ugt_sections: List[UGTResult] = field(default_factory=list)
    oht_rows: List[Dict[str, Any]] = field(default_factory=list)
    stp_sections: List[STPResult] = field(default_factory=list)
    num_buildings_res: int = 0
    num_buildings_com: int = 0
    total_flats: int = 0
    fire_tank_liters: int = 0
    ugt_domestic_liters: int = 0
    ugt_flushing_liters: int = 0
    sewage_lpd: int = 0
    stp_capacity_kld: float = 0.0

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Population": self.total_population,
            "Res Pop": self.res_population,
            "Com Pop": self.com_population,
            "Total Water (LPD)": self.dry_total_water_lpd,
            "Sewage Gen (LPD)": self.sewage_lpd,
            "STP Capacity (KLD)": self.stp_capacity_kld,
            "UGT Domestic (Liters)": self.ugt_domestic_liters,
            "UGT Flushing (Liters)": self.ugt_flushing_liters,
            "Fire Tank (Liters)": self.fire_tank_liters,
        }


@dataclass
class CalculationResults:
    plots: Dict[str, PlotResults] = field(default_factory=dict)
    total: Dict[str, Any] = field(default_factory=dict)

    def legacy_dict(self) -> Dict[str, Dict[str, Any]]:
        legacy: Dict[str, Dict[str, Any]] = {}
        for plot_name, plot in self.plots.items():
            legacy[plot_name] = plot.legacy_dict()
        legacy["Total"] = self.total
        return legacy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plots": {
                k: {
                    **v.legacy_dict(),
                    "residential_wings": [asdict(w) for w in v.residential_wings],
                    "commercial_units": [asdict(c) for c in v.commercial_units],
                    "ugt_sections": [asdict(u) for u in v.ugt_sections],
                    "stp_sections": [asdict(s) for s in v.stp_sections],
                    "oht_rows": v.oht_rows,
                    "landscape_dry_lpd": v.landscape_dry_lpd,
                    "landscape_wet_lpd": v.landscape_wet_lpd,
                    "dry_total_water_lpd": v.dry_total_water_lpd,
                    "wet_total_water_lpd": v.wet_total_water_lpd,
                }
                for k, v in self.plots.items()
            },
            "total": self.total,
        }

# ==================== models/environmental.py ====================



@dataclass
class SolidWasteResults:
    res_population: int = 0
    comm_population: int = 0
    res_total_waste_kg_day: float = 0.0
    res_wet_waste_kg_day: float = 0.0
    res_dry_waste_kg_day: float = 0.0
    comm_total_waste_kg_day: float = 0.0
    comm_wet_waste_kg_day: float = 0.0
    comm_dry_waste_kg_day: float = 0.0
    total_waste_kg_day: float = 0.0
    total_wet_waste_kg_day: float = 0.0
    total_dry_waste_kg_day: float = 0.0
    wet_waste_considered_kg_day: float = 0.0
    garden_waste_considered_kg_day: float = 0.0
    stp_sludge_kg_day: float = 0.0
    owc_plant_capacity_kg_day: float = 0.0
    res_e_waste_kg_year: float = 0.0
    comm_e_waste_kg_year: float = 0.0
    total_e_waste_kg_year: float = 0.0
    approx_area_sqm: str = ""


@dataclass
class SewageGenerationResults:
    res_population: int = 0
    comm_population: int = 0
    res_sewage_kld: float = 0.0
    comm_sewage_kld: float = 0.0
    total_sewage_kld: float = 0.0
    proposed_stp_capacity_kld: float = 0.0
    stp_sludge_kg_day: float = 0.0
    approx_area_sqm: str = ""


@dataclass
class EnvironmentalResults:
    solid_waste: SolidWasteResults = field(default_factory=SolidWasteResults)
    sewage: SewageGenerationResults = field(default_factory=SewageGenerationResults)

# ==================== services/calculator.py ====================




class WaterDemandCalculator:
    def __init__(
        self,
        residential: List[ResidentialWing],
        commercial: List[CommercialUnit],
        other: OtherDetails,
        project: Optional[ProjectData] = None,
    ) -> None:
        self.residential = residential
        self.commercial = commercial
        self.other = other
        self.project = project or ProjectData()
        self._plots = active_plots(self.project.plot_mode)

    def calculate(self) -> CalculationResults:
        self._apply_auto_fire_tanks()
        results = CalculationResults()
        for plot in PLOTS:
            if plot in self._plots:
                results.plots[plot] = self._calculate_plot(plot)
            else:
                results.plots[plot] = PlotResults(plot=plot)
        results.total = self._calculate_totals(results.plots)
        return results

    def _on_plot(self, item_plot: str, plot: str) -> bool:
        return normalize_plot_for_calc(item_plot) == plot

    def _apply_auto_fire_tanks(self) -> None:

        for plot in self._plots:
            self.other.fire_tank[plot] = float(
                auto_fire_tank_liters(plot, self.residential, self.project, self.other)
            )

    def _calculate_plot(self, plot: str) -> PlotResults:
        plot_res = PlotResults(plot=plot)
        res_wings = [w for w in self.residential if self._on_plot(w.plot, plot)]
        com_units = [c for c in self.commercial if self._on_plot(c.plot, plot)]

        for wing in sorted(res_wings, key=lambda w: w.sort_order):
            dom, flu, tot = residential_demand(wing.population)
            kitchen = wing.kitchen_water
            wr = WingResult(
                wing=wing.wing,
                flats=wing.effective_flats,
                pop_per_flat=wing.pop_per_flat,
                population=wing.population,
                domestic_lpd=dom,
                flushing_lpd=flu,
                kitchen_water_lpd=kitchen,
                total_lpd=tot,
            )
            plot_res.residential_wings.append(wr)
            plot_res.res_population += wing.population
            plot_res.res_domestic_lpd += dom
            plot_res.res_flushing_lpd += flu
            plot_res.res_total_lpd += tot
            plot_res.kitchen_water_lpd += kitchen
            plot_res.total_flats += wing.effective_flats

        plot_res.num_buildings_res = len(res_wings)

        blocks: Dict[str, List[CommercialUnit]] = defaultdict(list)
        for unit in sorted(com_units, key=lambda c: c.sort_order):
            blocks[unit.block].append(unit)

        for unit in sorted(com_units, key=lambda c: (c.block, c.sort_order)):
            spec = unit.type_spec()
            density = unit.density_override if unit.density_override > 0 else spec.density_divisor
            pop = unit.auto_population
            dom, flu, tot = commercial_demand(pop, spec)
            cr = CommercialResult(
                block=unit.block,
                comm_type=unit.comm_type,
                floor_label=unit.floor_label,
                area_sqm=unit.area_sqm,
                density=density,
                population=pop,
                domestic_lpd=dom,
                flushing_lpd=flu,
                total_lpd=tot,
            )
            plot_res.commercial_units.append(cr)
            plot_res.com_population += pop
            plot_res.com_domestic_lpd += dom
            plot_res.com_flushing_lpd += flu
            plot_res.com_total_lpd += tot

        plot_res.num_buildings_com = len(blocks)
        plot_res.total_population = plot_res.res_population + plot_res.com_population

        landscape_area = self.other.landscape_area.get(plot, 0.0)
        plot_res.landscape_dry_lpd = landscape_demand(landscape_area)
        plot_res.landscape_wet_lpd = wet_landscape_demand(plot_res.landscape_dry_lpd)

        pool_na = (
            self.other.swimming_pool_status.get(plot, "not_applicable") == "not_applicable"
            or self.other.swimming_pool_na.get(plot, False)
        )
        plot_res.swimming_pool_lpd = 0 if pool_na else int(self.other.swimming_pool.get(plot, 0))

        if hvac_applicable(self.project.project_type):
            plot_res.hvac_lpd = int(self.other.hvac_water.get(plot, 0))
        else:
            plot_res.hvac_lpd = 0

        dry_other = (
            plot_res.landscape_dry_lpd
            + plot_res.swimming_pool_lpd
            + plot_res.hvac_lpd
            + plot_res.kitchen_water_lpd
        )
        wet_other = (
            plot_res.landscape_wet_lpd
            + plot_res.swimming_pool_lpd
            + plot_res.hvac_lpd
            + plot_res.kitchen_water_lpd
        )

        plot_res.dry_total_water_lpd = (
            plot_res.res_total_lpd + plot_res.com_total_lpd + dry_other
        )
        plot_res.wet_total_water_lpd = (
            plot_res.res_total_lpd + plot_res.com_total_lpd + wet_other
        )

        plot_res.fire_tank_liters = int(self.other.fire_tank.get(plot, 0))
        plot_res.ugt_domestic_liters = round_storage_liters(
            (plot_res.res_domestic_lpd + plot_res.com_domestic_lpd) * UGT_DOMESTIC_DAYS
        )
        plot_res.ugt_flushing_liters = round_storage_liters(
            (plot_res.res_flushing_lpd + plot_res.com_flushing_lpd) * UGT_FLUSHING_DAYS
        )

        plot_res.ugt_sections = self._build_ugt_sections(plot, plot_res, blocks)
        plot_res.oht_rows = self._build_oht_rows(plot, plot_res)
        plot_res.stp_sections = self._build_stp_sections(plot, plot_res, blocks)

        total_sewage = sum(s.sewage_lpd for s in plot_res.stp_sections)
        plot_res.sewage_lpd = total_sewage
        plot_res.stp_capacity_kld = sum(s.say_stp_kld for s in plot_res.stp_sections)

        plot_res.dry_treated_water_lpd = sum(
            s.treated_water_lpd for s in plot_res.stp_sections
        )
        plot_res.wet_treated_water_lpd = plot_res.dry_treated_water_lpd

        plot_res.dry_excess_treated_lpd = sum(s.excess_treated_lpd for s in plot_res.stp_sections)
        plot_res.wet_excess_treated_lpd = plot_res.dry_excess_treated_lpd

        return plot_res

    def _build_ugt_sections(
        self,
        plot: str,
        plot_res: PlotResults,
        blocks: Dict[str, List[CommercialUnit]],
    ) -> List[UGTResult]:
        sections: List[UGTResult] = []

        res_dom = plot_res.res_domestic_lpd
        res_flu = plot_res.res_flushing_lpd
        res_fire = self._residential_fire_tank(plot)

        sections.append(
            UGTResult(
                description="DOMESTIC WATER TANK",
                water_requirement_lpd=res_dom,
                storage_days=UGT_DOMESTIC_DAYS,
                total_storage_liters=round_storage_liters(res_dom * UGT_DOMESTIC_DAYS),
                total_storage_kld=round_storage_liters(res_dom * UGT_DOMESTIC_DAYS) / 1000.0,
            )
        )
        sections.append(
            UGTResult(
                description="FLUSHING WATER TANK NEAR STP",
                water_requirement_lpd=res_flu,
                storage_days=UGT_FLUSHING_DAYS,
                total_storage_liters=round_storage_liters(res_flu * UGT_FLUSHING_DAYS),
                total_storage_kld=round_storage_liters(res_flu * UGT_FLUSHING_DAYS) / 1000.0,
            )
        )
        sections.append(
            UGTResult(
                description="FIRE WATER TANK",
                water_requirement_lpd=res_fire,
                storage_days=UGT_FIRE_DAYS,
                total_storage_liters=int(res_fire),
                total_storage_kld=res_fire / 1000.0,
            )
        )

        for block_name in sorted(blocks.keys()):
            block_dom = sum(u.domestic_lpd for u in plot_res.commercial_units if u.block == block_name)
            block_flu = sum(u.flushing_lpd for u in plot_res.commercial_units if u.block == block_name)
            block_fire = int(self.other.get_fire_tank(plot, block_name) or 0)
            if block_fire == 0 and block_name in self.other.fire_tank_commercial.get(plot, {}):
                block_fire = int(self.other.fire_tank_commercial[plot][block_name])

            if block_dom > 0 or block_flu > 0 or block_fire > 0:
                sections.append(
                    UGTResult(
                        description=f"DOMESTIC WATER TANK ({block_name})",
                        water_requirement_lpd=block_dom,
                        storage_days=UGT_DOMESTIC_DAYS,
                        total_storage_liters=round_storage_liters(block_dom * UGT_DOMESTIC_DAYS),
                        total_storage_kld=round_storage_liters(block_dom * UGT_DOMESTIC_DAYS) / 1000.0,
                    )
                )
                flushing_label = f"FLUSHING WATER TANK ({block_name})"
                if block_name == "COMM-A":
                    flushing_label = "FLUSHING WATER TANK (A&B)"
                sections.append(
                    UGTResult(
                        description=flushing_label,
                        water_requirement_lpd=block_flu,
                        storage_days=UGT_FLUSHING_DAYS,
                        total_storage_liters=round_storage_liters(block_flu * UGT_FLUSHING_DAYS),
                        total_storage_kld=round_storage_liters(block_flu * UGT_FLUSHING_DAYS) / 1000.0,
                    )
                )
                if block_fire > 0:
                    sections.append(
                        UGTResult(
                            description=f"FIRE WATER TANK ({block_name})",
                            water_requirement_lpd=block_fire,
                            storage_days=UGT_FIRE_DAYS,
                            total_storage_liters=block_fire,
                            total_storage_kld=block_fire / 1000.0,
                        )
                    )

        return sections

    def _residential_fire_tank(self, plot: str) -> int:
        return int(self.other.fire_tank.get(plot, 0))

    def _build_oht_rows(self, plot: str, plot_res: PlotResults) -> List[Dict[str, float]]:
        oht_by_wing: Dict[str, OHTDetail] = {
            o.wing: o for o in self.other.oht_details if o.plot == plot
        }
        rows: List[Dict[str, float]] = []

        for wr in plot_res.residential_wings:
            oht = oht_by_wing.get(wr.wing)
            if oht:
                rows.append(
                    {
                        "wing": wr.wing,
                        "domestic_kld": oht.domestic_kld,
                        "flushing_kld": oht.flushing_kld,
                        "fire_break_kld": oht.fire_break_kld,
                        "fire_oht_kld": oht.fire_oht_kld,
                    }
                )
            else:
                rows.append(
                    {
                        "wing": wr.wing,
                        "domestic_kld": round(wr.domestic_lpd / 1000.0, 2),
                        "flushing_kld": round(wr.flushing_lpd / 1000.0, 2),
                        "fire_break_kld": 0.0,
                        "fire_oht_kld": 0.0,
                    }
                )

        block_totals: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"domestic_kld": 0.0, "flushing_kld": 0.0}
        )
        for cu in plot_res.commercial_units:
            block_totals[cu.block]["domestic_kld"] += cu.domestic_lpd / 1000.0
            block_totals[cu.block]["flushing_kld"] += cu.flushing_lpd / 1000.0

        for block_name in sorted(block_totals.keys()):
            oht = oht_by_wing.get(block_name)
            bt = block_totals[block_name]
            rows.append(
                {
                    "wing": block_name,
                    "domestic_kld": oht.domestic_kld if oht else round(bt["domestic_kld"], 2),
                    "flushing_kld": oht.flushing_kld if oht else round(bt["flushing_kld"], 2),
                    "fire_break_kld": oht.fire_break_kld if oht else 0.0,
                    "fire_oht_kld": oht.fire_oht_kld if oht else 20.0,
                }
            )

        return rows

    def _build_stp_sections(
        self,
        plot: str,
        plot_res: PlotResults,
        blocks: Dict[str, List[CommercialUnit]],
    ) -> List[STPResult]:
        sections: List[STPResult] = []

        res_water = plot_res.res_total_lpd
        if res_water > 0:
            sections.append(
                self._stp_calc(
                    "RESIDENTIAL",
                    res_water,
                    plot_res.res_flushing_lpd,
                    plot_res.landscape_dry_lpd,
                    plot_res.hvac_lpd,
                )
            )

        com_blocks = sorted(blocks.keys())
        if com_blocks:
            if plot == "Plot-A" and len(com_blocks) >= 1:
                comm_a_units = [u for u in plot_res.commercial_units if u.block == "COMM-A"]
                comm_b_units = [u for u in plot_res.commercial_units if u.block == "COMM-B"]
                comm_ab_water = sum(u.total_lpd for u in comm_a_units + comm_b_units)
                comm_ab_flushing = sum(u.flushing_lpd for u in comm_a_units + comm_b_units)
                if comm_ab_water > 0:
                    sections.append(
                        self._stp_calc(
                            "COMMERCIAL A & B",
                            comm_ab_water,
                            comm_ab_flushing,
                            0,
                            0,
                        )
                    )
            else:
                for block_name in com_blocks:
                    block_water = sum(
                        u.total_lpd
                        for u in plot_res.commercial_units
                        if u.block == block_name
                    )
                    block_flushing = sum(
                        u.flushing_lpd
                        for u in plot_res.commercial_units
                        if u.block == block_name
                    )
                    block_landscape = plot_res.landscape_dry_lpd if block_name == com_blocks[-1] else 0
                    if block_water > 0:
                        scope = f"COMMERCIAL {block_name.replace('COMM-', '')}"
                        if plot == "Plot-B":
                            scope = "RESIDENTIAL & COMMERCIAL"
                        sections.append(
                            self._stp_calc(scope, block_water, block_flushing, block_landscape, 0)
                        )

        if not sections and plot_res.dry_total_water_lpd > 0:
            sections.append(
                self._stp_calc(
                    "TOTAL",
                    plot_res.dry_total_water_lpd,
                    plot_res.res_flushing_lpd + plot_res.com_flushing_lpd,
                    plot_res.landscape_dry_lpd,
                    plot_res.hvac_lpd,
                )
            )

        return sections

    def _stp_calc(
        self,
        scope: str,
        water_lpd: int,
        flushing_reuse: int,
        landscape_reuse: int,
        hvac_reuse: int,
    ) -> STPResult:
        sewage = int(water_lpd * 0.90)
        sewage_kld = sewage / 1000.0
        say_kld = say_stp_capacity_kld(sewage)
        treated = treated_water_lpd(say_kld)
        excess = treated - flushing_reuse - landscape_reuse - hvac_reuse
        return STPResult(
            scope=scope,
            total_water_lpd=water_lpd,
            sewage_lpd=sewage,
            sewage_kld=round(sewage_kld, 2),
            say_stp_kld=say_kld,
            treated_water_lpd=treated,
            reuse_flushing_lpd=flushing_reuse,
            reuse_landscape_lpd=landscape_reuse,
            reuse_hvac_lpd=hvac_reuse,
            excess_treated_lpd=max(0, excess),
        )

    def _calculate_totals(self, plots: Dict[str, PlotResults]) -> Dict[str, Any]:
        plot_a = plots.get("Plot-A")
        plot_b = plots.get("Plot-B")
        if not plot_a:
            return {}
        active = [p for p in (plot_a, plot_b) if p and (p.total_population > 0 or p.dry_total_water_lpd > 0)]
        if self.project.plot_mode == PLOT_MODE_SINGLE:
            active = [plot_a]
        total_pop = sum(p.total_population for p in active)
        total_water = sum(p.dry_total_water_lpd for p in active)
        total_stp = sum(p.stp_capacity_kld for p in active)
        total_res_pop = sum(p.res_population for p in active)
        total_com_pop = sum(p.com_population for p in active)
        total_flats = sum(p.total_flats for p in active)
        return {
            "Total Population": total_pop,
            "Total Water (LPD)": total_water,
            "Total STP Capacity (KLD)": total_stp,
            "Total Residential Population": total_res_pop,
            "Total Commercial Population": total_com_pop,
            "Total Flats": total_flats,
            "Plot-A Res Pop": plot_a.res_population,
            "Plot-B Res Pop": plot_b.res_population if plot_b else 0,
            "Plot-A Total Water (LPD)": plot_a.dry_total_water_lpd,
            "Plot-B Total Water (LPD)": plot_b.dry_total_water_lpd if plot_b else 0,
            "Plot-A STP Capacity (KLD)": plot_a.stp_capacity_kld,
            "Plot-B STP Capacity (KLD)": plot_b.stp_capacity_kld if plot_b else 0,
        }


def perform_calculations(
    residential_data: List[dict],
    commercial_data: List[dict],
    other_data: dict,
    project_data: Optional[dict] = None,
) -> tuple:
    residential = [ResidentialWing.from_dict(r) for r in residential_data]
    commercial = [CommercialUnit.from_dict(c) for c in commercial_data]
    other = OtherDetails.from_dict(other_data)
    project = ProjectData.from_dict(project_data or {})
    calc = WaterDemandCalculator(residential, commercial, other, project)
    results = calc.calculate()
    return results, results.legacy_dict()

# ==================== services/database.py ====================




DB_PATH = os.path.join(APP_DIR, "data", "water_demand.db")
JSON_SCHEMA_VERSION = "1.0"

_HISTORY_SQL = """
    SELECT project_id, project_name, client_name, project_location, project_no,
           date, updated_at, total_water_demand, engineer_name, created_by
    FROM projects
"""

_DASHBOARD_SQL = """
    SELECT project_id, project_name, client_name, project_location, project_no,
           date, created_at, updated_at, total_water_demand, engineer_name, created_by,
           workflow_status, project_type, project_opened_at, completed_at,
           expected_completion_at, total_paused_seconds, total_time_taken_seconds,
           delay_seconds, completion_outcome, assigned_duration_minutes, is_paused
    FROM projects
"""


def init_db(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT,
            client_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            project_no TEXT,
            date TEXT,
            revision_no TEXT,
            description TEXT,
            prepared_by TEXT,
            checked_by TEXT,
            approved_by TEXT,
            total_water_demand REAL,
            stp_capacity_a REAL,
            stp_capacity_b REAL,
            json_snapshot TEXT,
            created_at TEXT,
            updated_at TEXT,
            created_by TEXT DEFAULT '',
            updated_by TEXT DEFAULT ''
        )
        """
    )
    _migrate_projects_table(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS residential_wings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            plot TEXT,
            wing_name TEXT,
            flats INTEGER,
            pop_per_flat INTEGER,
            sort_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS commercial_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            plot TEXT,
            block_name TEXT,
            comm_type TEXT,
            floor_label TEXT,
            area_sqm REAL,
            density_override REAL,
            sort_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
        """
    )
    conn.commit()
    conn.close()


def _migrate_projects_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(projects)")
    cols = {row[1] for row in cursor.fetchall()}
    if "created_by" not in cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN created_by TEXT DEFAULT ''")
    if "updated_by" not in cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN updated_by TEXT DEFAULT ''")
    workflow_columns = {
        "workflow_status": "TEXT DEFAULT 'new'",
        "project_type": "TEXT DEFAULT ''",
        "project_opened_at": "TEXT",
        "completed_at": "TEXT",
        "expected_completion_at": "TEXT",
        "total_paused_seconds": "INTEGER DEFAULT 0",
        "total_time_taken_seconds": "INTEGER",
        "delay_seconds": "INTEGER DEFAULT 0",
        "completion_outcome": "TEXT DEFAULT ''",
        "assigned_duration_minutes": "INTEGER",
        "is_paused": "INTEGER DEFAULT 0",
    }
    for name, ddl in workflow_columns.items():
        if name not in cols:
            cursor.execute(f"ALTER TABLE projects ADD COLUMN {name} {ddl}")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            project_id TEXT,
            project_name TEXT,
            engineer_name TEXT,
            username TEXT DEFAULT '',
            details TEXT DEFAULT '',
            created_at TEXT
        )
        """
    )
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_projects_project_id ON projects(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_projects_project_name ON projects(project_name)",
        "CREATE INDEX IF NOT EXISTS idx_projects_client_name ON projects(client_name)",
        "CREATE INDEX IF NOT EXISTS idx_projects_engineer_name ON projects(engineer_name)",
        "CREATE INDEX IF NOT EXISTS idx_projects_project_type ON projects(project_type)",
        "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_projects_workflow_status ON projects(workflow_status)",
    ):
        cursor.execute(index_sql)


def project_exists(project_id: str, db_path: str = DB_PATH) -> bool:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def save_project(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH,
    created_by: str = "",
    updated_by: str = "",
) -> bool:
    init_db(db_path)
    is_update = project_exists(project.project_id, db_path)
    snapshot = build_project_snapshot(project, residential, commercial, other, calculated)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    stp_a = 0.0
    stp_b = 0.0
    total_water = 0.0
    if calculated:
        stp_a = float(calculated.get("plots", {}).get("Plot-A", {}).get("STP Capacity (KLD)", 0))
        stp_b = float(calculated.get("plots", {}).get("Plot-B", {}).get("STP Capacity (KLD)", 0))
        total_water = float(calculated.get("total", {}).get("Total Water (LPD)", 0))

    cursor.execute(
        """
        INSERT OR REPLACE INTO projects (
            project_id, project_name, client_name, project_location, engineer_name,
            project_no, date, revision_no, description, prepared_by, checked_by,
            approved_by, total_water_demand, stp_capacity_a, stp_capacity_b,
            json_snapshot, created_at, updated_at, created_by, updated_by,
            workflow_status, project_type, project_opened_at, completed_at,
            expected_completion_at, total_paused_seconds, total_time_taken_seconds,
            delay_seconds, completion_outcome, assigned_duration_minutes, is_paused
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM projects WHERE project_id = ?), ?
        ), ?, COALESCE(
            (SELECT created_by FROM projects WHERE project_id = ?), ?
        ), ?,
            COALESCE((SELECT workflow_status FROM projects WHERE project_id = ?), 'new'),
            ?,
            (SELECT project_opened_at FROM projects WHERE project_id = ?),
            (SELECT completed_at FROM projects WHERE project_id = ?),
            (SELECT expected_completion_at FROM projects WHERE project_id = ?),
            COALESCE((SELECT total_paused_seconds FROM projects WHERE project_id = ?), 0),
            (SELECT total_time_taken_seconds FROM projects WHERE project_id = ?),
            COALESCE((SELECT delay_seconds FROM projects WHERE project_id = ?), 0),
            COALESCE((SELECT completion_outcome FROM projects WHERE project_id = ?), ''),
            (SELECT assigned_duration_minutes FROM projects WHERE project_id = ?),
            COALESCE((SELECT is_paused FROM projects WHERE project_id = ?), 0)
        )
        """,
        (
            project.project_id,
            project.project_name,
            project.client_name,
            project.project_location,
            project.engineer_name,
            project.project_no,
            project.date,
            project.revision.revision_no,
            project.revision.description,
            project.revision.prepared_by,
            project.revision.checked_by,
            project.revision.approved_by,
            total_water,
            stp_a,
            stp_b,
            json.dumps(snapshot),
            project.project_id,
            now,
            now,
            project.project_id,
            created_by or updated_by,
            updated_by or created_by,
            project.project_id,
            project.project_type or "",
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
            project.project_id,
        ),
    )
    cursor.execute("DELETE FROM residential_wings WHERE project_id = ?", (project.project_id,))
    cursor.execute("DELETE FROM commercial_units WHERE project_id = ?", (project.project_id,))
    for idx, wing in enumerate(residential):
        cursor.execute(
            """
            INSERT INTO residential_wings
            (project_id, plot, wing_name, flats, pop_per_flat, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project.project_id, wing.plot, wing.wing, wing.flats, wing.pop_per_flat, idx),
        )
    for idx, unit in enumerate(commercial):
        cursor.execute(
            """
            INSERT INTO commercial_units
            (project_id, plot, block_name, comm_type, floor_label, area_sqm, density_override, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                unit.plot,
                unit.block,
                unit.comm_type,
                unit.floor_label,
                unit.area_sqm,
                unit.density_override,
                idx,
            ),
        )
    conn.commit()
    conn.close()
    return is_update


def _row_to_summary(row: tuple) -> Dict[str, str]:
    return {
        "project_id": row[0] or "",
        "project_name": row[1] or "",
        "client_name": row[2] or "",
        "project_location": row[3] or "",
        "project_no": row[4] or "",
        "date": row[5] or "",
        "updated_at": row[6] or "",
        "total_water_demand": str(row[7] or 0),
        "engineer_name": row[8] or "" if len(row) > 8 else "",
        "created_by": row[9] or "" if len(row) > 9 else "",
    }


def _row_to_dashboard(row: tuple) -> Dict[str, Any]:
    return {
        "project_id": row[0] or "",
        "project_name": row[1] or "",
        "client_name": row[2] or "",
        "project_location": row[3] or "",
        "project_no": row[4] or "",
        "date": row[5] or "",
        "created_at": row[6] or "",
        "updated_at": row[7] or "",
        "total_water_demand": row[8] or 0,
        "engineer_name": row[9] or "",
        "created_by": row[10] or "",
        "workflow_status": row[11] or "new",
        "project_type": row[12] or "",
        "project_opened_at": row[13] or "",
        "completed_at": row[14] or "",
        "expected_completion_at": row[15] or "",
        "total_paused_seconds": row[16] or 0,
        "total_time_taken_seconds": row[17],
        "delay_seconds": row[18] or 0,
        "completion_outcome": row[19] or "",
        "assigned_duration_minutes": row[20],
        "is_paused": row[21] or 0,
    }


def get_project_history(limit: int = 100, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        _HISTORY_SQL + " ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    rows = [_row_to_summary(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def search_projects(query: str, limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_db(db_path)
    key = f"%{(query or '').strip()}%"
    if key == "%%":
        return get_project_history(limit, db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        _HISTORY_SQL
        + """
        WHERE project_id LIKE ? OR project_name LIKE ? OR client_name LIKE ?
           OR project_location LIKE ? OR project_no LIKE ? OR engineer_name LIKE ?
        ORDER BY updated_at DESC LIMIT ?
        """,
        (key, key, key, key, key, key, limit),
    )
    rows = [_row_to_summary(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_project_summary(project_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(_HISTORY_SQL + " WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_summary(row) if row else None


def list_projects(db_path: str = DB_PATH) -> List[Dict[str, str]]:
    return get_project_history(200, db_path)


def get_dashboard_projects(limit: int = 500, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        _DASHBOARD_SQL + " ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    rows = [_row_to_dashboard(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_project_workflow_row(project_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(_DASHBOARD_SQL + " WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_dashboard(row) if row else None


def update_project_workflow(project_id: str, fields: Dict[str, Any], db_path: str = DB_PATH) -> None:
    if not project_id or not fields:
        return
    allowed = {
        "workflow_status",
        "project_type",
        "project_opened_at",
        "completed_at",
        "expected_completion_at",
        "total_paused_seconds",
        "total_time_taken_seconds",
        "delay_seconds",
        "completion_outcome",
        "assigned_duration_minutes",
        "is_paused",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [datetime.now().isoformat(), project_id]
    cursor.execute(
        f"UPDATE projects SET {assignments}, updated_at = ? WHERE project_id = ?",
        values,
    )
    conn.commit()
    conn.close()


def log_audit_event(
    event_type: str,
    *,
    project_id: str = "",
    project_name: str = "",
    engineer_name: str = "",
    username: str = "",
    details: str = "",
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_log (event_type, project_id, project_name, engineer_name, username, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            project_id,
            project_name,
            engineer_name,
            username,
            details,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def delete_project(project_id: str, *, username: str = "", db_path: str = DB_PATH) -> bool:
    if not project_id:
        return False
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(_DASHBOARD_SQL + " WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    summary = _row_to_dashboard(row)
    cursor.execute("DELETE FROM residential_wings WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM commercial_units WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()
    log_audit_event(
        "project_deleted",
        project_id=project_id,
        project_name=summary.get("project_name", ""),
        engineer_name=summary.get("engineer_name", ""),
        username=username,
        db_path=db_path,
    )
    return True


def update_project_metadata(
    project_id: str,
    project_name: str,
    client_name: str,
    project_location: str,
    engineer_name: str = "",
    updated_by: str = "",
    db_path: str = DB_PATH,
) -> None:
    """Update header fields on an existing project without touching calculation data."""
    init_db(db_path)
    data = load_project_from_db(project_id, db_path)
    project, residential, commercial, other, calculated = parse_project_snapshot(data)
    project.project_name = project_name
    project.client_name = client_name
    project.project_location = project_location
    if engineer_name:
        project.engineer_name = engineer_name
    save_project(
        project,
        residential,
        commercial,
        other,
        calculated,
        db_path=db_path,
        updated_by=updated_by,
    )


def load_project_from_db(project_id: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT json_snapshot FROM projects WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Project not found: {project_id}")
    return json.loads(row[0])


def build_project_snapshot(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "project": project.to_dict(),
        "residential": [r.to_dict() for r in residential],
        "commercial": [c.to_dict() for c in commercial],
        "other": other.to_dict(),
        "calculated": calculated or {},
    }


def parse_project_snapshot(data: Dict[str, Any]) -> tuple:
    project = ProjectData.from_dict(data.get("project", {}))
    residential = [ResidentialWing.from_dict(r) for r in data.get("residential", [])]
    commercial = [CommercialUnit.from_dict(c) for c in data.get("commercial", [])]
    other = OtherDetails.from_dict(data.get("other", {}))
    calculated = data.get("calculated", {})
    return project, residential, commercial, other, calculated

# ==================== services/lookup_db.py ====================
"""Client and location lookup tables for autocomplete."""





def _conn(db_path: str = DB_PATH):
    init_db(db_path)
    return sqlite3.connect(db_path)


def init_lookup_tables(db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            client_key TEXT PRIMARY KEY,
            client_name TEXT,
            address TEXT,
            engineer_name TEXT,
            contact TEXT,
            email TEXT,
            gst TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            location_key TEXT PRIMARY KEY,
            city TEXT,
            state TEXT,
            rainfall_zone TEXT,
            climate TEXT,
            full_label TEXT
        )
        """
    )
    # Seed Pune if empty
    cur.execute("SELECT COUNT(*) FROM locations")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """
            INSERT OR IGNORE INTO locations
            (location_key, city, state, rainfall_zone, climate, full_label)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("pune", "Pune", "Maharashtra", "Moderate", "Tropical Wet-Dry", "Pune, Maharashtra"),
        )
    conn.commit()
    conn.close()


def search_clients(prefix: str, limit: int = 8, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_lookup_tables(db_path)
    key = (prefix or "").strip().lower()
    if not key:
        return []
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT client_key, client_name, address, engineer_name, contact, email, gst
        FROM clients
        WHERE client_key LIKE ? OR client_name LIKE ?
        ORDER BY client_name LIMIT ?
        """,
        (f"%{key}%", f"%{key}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "client_key": r[0],
            "client_name": r[1] or "",
            "address": r[2] or "",
            "engineer_name": r[3] or "",
            "contact": r[4] or "",
            "email": r[5] or "",
            "gst": r[6] or "",
        }
        for r in rows
    ]


def upsert_client(record: Dict[str, str], db_path: str = DB_PATH) -> None:
    init_lookup_tables(db_path)
    name = record.get("client_name", "").strip()
    if not name:
        return
    key = name.lower().replace(" ", "_")[:40]
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO clients
        (client_key, client_name, address, engineer_name, contact, email, gst)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            name,
            record.get("address", ""),
            record.get("engineer_name", ""),
            record.get("contact", ""),
            record.get("email", ""),
            record.get("gst", ""),
        ),
    )
    conn.commit()
    conn.close()


def search_locations(prefix: str, limit: int = 8, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_lookup_tables(db_path)
    key = (prefix or "").strip().lower()
    if not key:
        return []
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT location_key, city, state, rainfall_zone, climate, full_label
        FROM locations
        WHERE location_key LIKE ? OR city LIKE ? OR full_label LIKE ?
        ORDER BY city LIMIT ?
        """,
        (f"%{key}%", f"%{key}%", f"%{key}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "location_key": r[0],
            "city": r[1] or "",
            "state": r[2] or "",
            "rainfall_zone": r[3] or "",
            "climate": r[4] or "",
            "full_label": r[5] or "",
        }
        for r in rows
    ]


def upsert_location(record: Dict[str, str], db_path: str = DB_PATH) -> None:
    init_lookup_tables(db_path)
    city = record.get("city", "").strip()
    if not city:
        return
    key = city.lower().replace(" ", "_")[:40]
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO locations
        (location_key, city, state, rainfall_zone, climate, full_label)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            key,
            city,
            record.get("state", ""),
            record.get("rainfall_zone", ""),
            record.get("climate", ""),
            record.get("full_label", city),
        ),
    )
    conn.commit()
    conn.close()


def next_project_number(db_path: str = DB_PATH) -> str:
    init_db(db_path)

    year = datetime.now().year
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT project_no FROM projects WHERE project_no LIKE ? ORDER BY project_no DESC LIMIT 1",
        (f"AE-{year}-%",),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try:
            seq = int(str(row[0]).split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"AE-{year}-{seq:03d}"

# ==================== services/project_workflow.py ====================
"""Project workflow status, timing, and dashboard aggregation helpers."""




STATUS_NEW = "new"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_PENDING = "pending"
STATUS_DELAYED = "delayed"
STATUS_CANCELLED = "cancelled"

STATUS_LABELS = {
    STATUS_NEW: "New",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED: "Completed",
    STATUS_PENDING: "Pending",
    STATUS_DELAYED: "Delayed",
    STATUS_CANCELLED: "Cancelled",
}

STATUS_FILTER_OPTIONS = ["All Status"] + [STATUS_LABELS[s] for s in (
    STATUS_NEW,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_DELAYED,
    STATUS_CANCELLED,
)]

LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")[:26])
    except ValueError:
        return None


def format_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours:02d}h {minutes:02d}m"
    return f"{minutes:02d}m"


def format_duration_or_dash(seconds: Optional[int]) -> str:
    if seconds is None:
        return "—"
    return format_duration(seconds)


def format_duration_clock(seconds: Optional[int]) -> str:
    """Format seconds as HH:MM:SS for project history display."""
    if seconds is None or seconds < 0:
        return "—"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _now() -> datetime:
    return datetime.now()


def effective_status(row: Dict[str, Any], *, now: Optional[datetime] = None) -> str:
    now = now or _now()
    stored = (row.get("workflow_status") or STATUS_NEW).strip().lower()
    if stored == STATUS_CANCELLED:
        return STATUS_CANCELLED
    if stored == STATUS_COMPLETED or row.get("completed_at"):
        return STATUS_COMPLETED
    if stored == STATUS_PENDING or int(row.get("is_paused") or 0):
        return STATUS_PENDING

    opened = _parse_iso(row.get("project_opened_at"))
    expected = _parse_iso(row.get("expected_completion_at"))
    if expected and now > expected and opened and not row.get("completed_at"):
        return STATUS_DELAYED
    if stored == STATUS_DELAYED:
        return STATUS_DELAYED

    if opened or stored == STATUS_IN_PROGRESS:
        return STATUS_IN_PROGRESS
    return STATUS_NEW


def active_elapsed_seconds(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Optional[int]:
    now = now or _now()
    if int(row.get("is_paused") or 0):
        return max(0, int(row.get("total_time_taken_seconds") or 0))

    if row.get("completed_at"):
        if row.get("total_time_taken_seconds") is not None:
            return max(0, int(row["total_time_taken_seconds"]))
        opened = _parse_iso(row.get("project_opened_at"))
        completed = _parse_iso(row.get("completed_at"))
        if opened and completed:
            paused = int(row.get("total_paused_seconds") or 0)
            return max(0, int((completed - opened).total_seconds()) - paused)
        return None

    opened = _parse_iso(row.get("project_opened_at"))
    if not opened:
        return None
    paused = int(row.get("total_paused_seconds") or 0)
    return max(0, int((now - opened).total_seconds()) - paused)


def expected_seconds(row: Dict[str, Any]) -> Optional[int]:
    minutes = row.get("assigned_duration_minutes")
    if minutes is not None and str(minutes).strip() != "":
        return int(minutes) * 60
    expected = _parse_iso(row.get("expected_completion_at"))
    opened = _parse_iso(row.get("project_opened_at"))
    if expected and opened:
        return max(0, int((expected - opened).total_seconds()))
    return None


def performance_indicator(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Tuple[str, str]:
    now = now or _now()
    status = effective_status(row, now=now)
    elapsed = active_elapsed_seconds(row, now=now)
    expected = expected_seconds(row)

    if status == STATUS_COMPLETED:
        outcome = (row.get("completion_outcome") or "").strip().lower()
        delay = int(row.get("delay_seconds") or 0)
        if outcome == "early" or delay < 0:
            detail = f"{format_duration(abs(delay))} early" if delay else "Completed Early"
            return "✓ Completed Early", detail
        if outcome == "delayed" or delay > 0:
            return "⚠ Delayed", f"{format_duration(delay)} late"
        return "✓ On Time", "On Time"

    if status == STATUS_DELAYED:
        if expected is not None and elapsed is not None:
            overdue = max(0, elapsed - expected)
            return "⚠ Delayed", f"{format_duration(overdue)} overdue"
        return "⚠ Delayed", "Overdue"

    if status in (STATUS_IN_PROGRESS, STATUS_NEW, STATUS_PENDING):
        if expected is not None and elapsed is not None:
            remaining = expected - elapsed
            if remaining >= 0:
                return "● In Progress", f"{format_duration(remaining)} remaining"
            return "⚠ Delayed", f"{format_duration(abs(remaining))} overdue"
        return "● In Progress", STATUS_LABELS.get(status, "In Progress")

    if status == STATUS_CANCELLED:
        return "Cancelled", "Cancelled"
    return STATUS_LABELS.get(status, status.title()), ""


def enrich_dashboard_row(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    status = effective_status(row, now=now)
    elapsed = active_elapsed_seconds(row, now=now)
    expected = expected_seconds(row)
    perf_title, perf_detail = performance_indicator(row, now=now)
    project_type = (row.get("project_type") or "").strip()
    return {
        **row,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status.title()),
        "time_taken_seconds": elapsed,
        "time_taken_display": format_duration_clock(elapsed),
        "expected_seconds": expected,
        "expected_display": format_duration_or_dash(expected),
        "performance_title": perf_title,
        "performance_detail": perf_detail,
        "project_type_label": project_type_label(project_type) if project_type else "—",
        "created_display": _display_date(row.get("created_at") or row.get("date")),
        "updated_display": _display_date(row.get("updated_at")),
    }


def _display_date(value: Optional[str]) -> str:
    dt = _parse_iso(value)
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M")[:16]
    return (value or "—")[:16]


def is_today(value: Optional[str], *, now: Optional[datetime] = None) -> bool:
    now = now or _now()
    dt = _parse_iso(value)
    if not dt:
        return False
    return dt.date() == now.date()


def compute_statistics(rows: List[Dict[str, Any]], *, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or _now()
    stats = {
        "total": 0,
        "active": 0,
        "completed": 0,
        "this_month": 0,
        # legacy keys used by older UI/tests
        "in_progress": 0,
        "pending": 0,
        "delayed": 0,
        "today": 0,
    }
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        stats["total"] += 1
        status = row["status"]
        if status == STATUS_COMPLETED:
            stats["completed"] += 1
        elif status != STATUS_CANCELLED:
            stats["active"] += 1
        if status == STATUS_IN_PROGRESS:
            stats["in_progress"] += 1
        elif status == STATUS_PENDING:
            stats["pending"] += 1
        elif status == STATUS_DELAYED:
            stats["delayed"] += 1
        if is_this_month(raw.get("created_at"), now=now) or is_this_month(raw.get("project_opened_at"), now=now):
            stats["this_month"] += 1
        if is_today(raw.get("created_at"), now=now) or is_today(raw.get("project_opened_at"), now=now):
            stats["today"] += 1
    return stats


def compute_engineer_performance(rows: List[Dict[str, Any]], *, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    now = now or _now()
    buckets: Dict[str, Dict[str, Any]] = {}
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        engineer = (row.get("engineer_name") or "Unassigned").strip() or "Unassigned"
        bucket = buckets.setdefault(
            engineer,
            {
                "engineer": engineer,
                "projects": 0,
                "completed": 0,
                "in_progress": 0,
                "delayed": 0,
                "completed_seconds": [],
            },
        )
        bucket["projects"] += 1
        status = row["status"]
        if status == STATUS_COMPLETED:
            bucket["completed"] += 1
            if row.get("time_taken_seconds") is not None:
                bucket["completed_seconds"].append(int(row["time_taken_seconds"]))
        elif status == STATUS_IN_PROGRESS:
            bucket["in_progress"] += 1
        elif status == STATUS_DELAYED:
            bucket["delayed"] += 1

    result = []
    for engineer in sorted(buckets, key=lambda k: (-buckets[k]["projects"], k.lower())):
        bucket = buckets[engineer]
        seconds = bucket["completed_seconds"]
        avg = int(sum(seconds) / len(seconds)) if seconds else None
        result.append(
            {
                "engineer": engineer,
                "projects": bucket["projects"],
                "completed": bucket["completed"],
                "in_progress": bucket["in_progress"],
                "delayed": bucket["delayed"],
                "avg_time_display": format_duration_or_dash(avg),
            }
        )
    return result


def list_engineer_options(rows: List[Dict[str, Any]]) -> List[str]:
    names = {name for name in STAFF_NAMES}
    for row in rows:
        engineer = (row.get("engineer_name") or "").strip()
        if engineer:
            names.add(engineer)
    return ["All Engineers"] + sorted(names, key=str.lower)


def filter_rows(
    rows: List[Dict[str, Any]],
    *,
    engineer: str = "All Engineers",
    status_label: str = "All Status",
    search: str = "",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    now = now or _now()
    search_key = (search or "").strip().lower()
    status_key = LABEL_TO_STATUS.get(status_label)

    filtered: List[Dict[str, Any]] = []
    for raw in rows:
        row = enrich_dashboard_row(raw, now=now)
        if engineer and engineer != "All Engineers":
            eng = (row.get("engineer_name") or "").strip()
            if eng != engineer:
                continue
        if status_key and row["status"] != status_key:
            continue
        if search_key:
            haystack = " ".join(
                [
                    row.get("project_id", ""),
                    row.get("project_name", ""),
                    row.get("client_name", ""),
                    row.get("engineer_name", ""),
                    row.get("project_type_label", ""),
                    row.get("status_label", ""),
                    row.get("project_type", ""),
                ]
            ).lower()
            if search_key not in haystack:
                continue
        project_dt = _project_date(row)
        if from_date and project_dt and project_dt.date() < from_date.date():
            continue
        if to_date and project_dt and project_dt.date() > to_date.date():
            continue
        filtered.append(row)
    filtered.sort(key=lambda r: _project_date(r) or datetime.min, reverse=True)
    return filtered


def _project_date(row: Dict[str, Any]) -> Optional[datetime]:
    for key in ("created_at", "date", "updated_at", "project_opened_at"):
        dt = _parse_iso(row.get(key))
        if dt:
            return dt
    return None


def parse_filter_date(text: str) -> Optional[datetime]:
    """Parse DD-MM-YYYY filter date."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def is_this_month(value: Optional[str], *, now: Optional[datetime] = None) -> bool:
    now = now or _now()
    dt = _parse_iso(value)
    if not dt:
        return False
    return dt.year == now.year and dt.month == now.month


def rows_for_stats(
    rows: List[Dict[str, Any]],
    *,
    engineer: str = "All Engineers",
    status_label: str = "All Status",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    return filter_rows(rows, engineer=engineer, status_label=status_label, search="", now=now)


def completion_fields_on_finish(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    opened = _parse_iso(row.get("project_opened_at")) or now
    paused = int(row.get("total_paused_seconds") or 0)
    elapsed = max(0, int((now - opened).total_seconds()) - paused)
    expected = expected_seconds(row)
    delay = 0
    outcome = "on_time"
    if expected is not None:
        delay = elapsed - expected
        if delay < 0:
            outcome = "early"
        elif delay > 0:
            outcome = "delayed"
    return {
        "workflow_status": STATUS_COMPLETED,
        "completed_at": now.isoformat(),
        "total_time_taken_seconds": elapsed,
        "delay_seconds": max(0, delay) if delay > 0 else delay,
        "completion_outcome": outcome,
        "is_paused": 0,
    }


def open_fields_on_start(row: Dict[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    updates: Dict[str, Any] = {}
    if not row.get("project_opened_at"):
        updates["project_opened_at"] = now.isoformat()
    status = (row.get("workflow_status") or STATUS_NEW).strip().lower()
    if status in ("", STATUS_NEW, STATUS_PENDING):
        updates["workflow_status"] = STATUS_IN_PROGRESS
        updates["is_paused"] = 0
    return updates

# ==================== services/project_service.py ====================
"""Project lifecycle helpers — new, open, search, auto ID."""





def generate_project_id(db_path: str = DB_PATH) -> str:
    """Auto-generate unique project ID: WD-YYYYMMDD-NNN."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"WD-{today}-"
    seq = 1
    while True:
        candidate = f"{prefix}{seq:03d}"
        if not project_exists(candidate, db_path):
            return candidate
        seq += 1
        if seq > 999:
            return f"WD-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def create_new_project_state(db_path: str = DB_PATH) -> AppState:
    """Fresh project with auto-generated IDs."""
    state = AppState()
    state.project = ProjectData(
        project_id=generate_project_id(db_path),
        project_name="NEW PROJECT",
        client_name="",
        project_location="",
        project_type=PROJECT_TYPE_UNSET,
        engineer_name="",
        project_no=next_project_number(db_path),
        date=datetime.now().strftime("%d-%m-%Y"),
        revision=RevisionInfo(
            date=datetime.now().strftime("%d-%m-%Y"),
            prepared_by="",
        ),
    )
    state.residential = []
    state.commercial = []
    return state


def load_project_state(project_id: str, db_path: str = DB_PATH) -> AppState:
    """Load an existing project into AppState."""
    summary = get_project_summary(project_id, db_path)
    if not summary:
        raise ValueError(f"Project not found: {project_id}")
    data = load_project_from_db(project_id, db_path)
    project, residential, commercial, other, calculated = parse_project_snapshot(data)
    state = AppState()
    state.project = project
    state.residential = residential
    state.commercial = commercial
    state.other = other
    if calculated:
        state.run_calculations()
    else:
        state.auto_calculate()
    return state


def persist_project_state(state: AppState, db_path: str = DB_PATH) -> bool:
    """Save project; returns True if updated existing, False if new."""
    result = save_project(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
        db_path=db_path,
    )
    invalidate_dashboard_cache()
    return result


def find_projects(query: str = "", limit: int = 50, db_path: str = DB_PATH):
    """Search/list projects by ID, name, client, location, type, or date."""
    if query:
        return search_projects(query, limit=limit, db_path=db_path)
    return get_project_history(limit, db_path)


def list_dashboard_projects(db_path: str = DB_PATH):
    return get_dashboard_projects(db_path=db_path)


_dashboard_cache: dict = {"rows": None, "mtime": 0.0}


def list_dashboard_projects_cached(db_path: str = DB_PATH):
    """Return dashboard rows, using a lightweight file-mtime cache."""
    try:
        mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0.0
    except OSError:
        mtime = 0.0
    if _dashboard_cache["rows"] is not None and _dashboard_cache["mtime"] == mtime:
        return _dashboard_cache["rows"]
    rows = get_dashboard_projects(db_path=db_path)
    _dashboard_cache["rows"] = rows
    _dashboard_cache["mtime"] = mtime
    return rows


def invalidate_dashboard_cache() -> None:
    _dashboard_cache["rows"] = None
    _dashboard_cache["mtime"] = 0.0


def mark_project_opened(project_id: str, db_path: str = DB_PATH) -> None:
    row = get_project_workflow_row(project_id, db_path)
    if not row:
        return
    updates = open_fields_on_start(row)
    if updates:
        update_project_workflow(project_id, updates, db_path)


def mark_project_completed(project_id: str, db_path: str = DB_PATH) -> None:
    row = get_project_workflow_row(project_id, db_path)
    if not row:
        return
    updates = completion_fields_on_finish(row)
    update_project_workflow(project_id, updates, db_path)


def remove_project(project_id: str, *, username: str = "", db_path: str = DB_PATH) -> bool:
    result = delete_project(project_id, username=username, db_path=db_path)
    if result:
        invalidate_dashboard_cache()
    return result

# ==================== services/app_logging.py ====================
"""Application logging to logs/application.log."""



_LOG_DIR = os.path.join(APP_DIR, "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "application.log")
_LOGGER: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    os.makedirs(_LOG_DIR, exist_ok=True)
    logger = logging.getLogger("water_demand_app")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(funcName)s | %(message)s")
        )
        logger.addHandler(handler)
    _LOGGER = logger
    return logger


def log_exception(
    message: str,
    *,
    exc: Optional[BaseException] = None,
    project_id: str = "",
    function: str = "",
) -> None:
    logger = get_logger()
    parts = [message]
    if project_id:
        parts.append(f"project_id={project_id}")
    if function:
        parts.append(f"function={function}")
    text = " | ".join(parts)
    if exc is not None:
        logger.error("%s\n%s", text, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    else:
        logger.error(text)

# ==================== services/automation.py ====================
"""Live automation — sync UI inputs to state and apply building parser rules."""





def apply_building_parser(project: ProjectData, residential: List[ResidentialWing]) -> None:
    """Parse building configuration into height/floors and propagate to wings."""
    if not project.building_config:
        return
    floors_above, est_height = parse_building_config(project.building_config)
    if est_height > 0 and project.building_height_m <= 0:
        project.building_height_m = est_height
    for wing in residential:
        if not wing.building_config or wing.building_config == "G+7":
            wing.building_config = project.building_config
        if wing.building_height_m <= 0 and project.building_height_m > 0:
            wing.building_height_m = project.building_height_m
        if not wing.building_type:
            wing.building_type = project.building_type
        if wing.num_wings <= 0 and project.num_wings > 0:
            wing.num_wings = project.num_wings
        elif wing.building_config and wing.building_height_m <= 0:
            _, wh = parse_building_config(wing.building_config)
            if wh > 0:
                wing.building_height_m = wh


def wings_from_ui_rows(rows: List[dict], plot_mode: str) -> List[ResidentialWing]:
    """Best-effort sync of residential table rows (no validation)."""
    wings: List[ResidentialWing] = []
    for idx, row in enumerate(rows):
        try:
            wing_name = (row["wing"].get() or "").strip()
            if not wing_name:
                continue
            wings.append(
                ResidentialWing(
                    plot=ui_plot_label(row["plot"].get(), plot_mode),
                    wing=wing_name,
                    building_config=row["config"].get(),
                    building_type=row["btype"].get(),
                    building_height_m=float(row["height"].get() or 0),
                    num_wings=max(1, int(row["num_wings"].get() or 1)),
                    flats_1bhk=max(0, int(row["b1"].get() or 0)),
                    flats_2bhk=max(0, int(row["b2"].get() or 0)),
                    flats_3bhk=max(0, int(row["b3"].get() or 0)),
                    flats_4bhk=max(0, int(row["b4"].get() or 0)),
                    flats_penthouse=max(0, int(row["ph"].get() or 0)),
                    sort_order=idx,
                )
            )
        except (ValueError, KeyError, TypeError):
            continue
    return wings


def commercial_from_ui_rows(rows: List[dict], plot_mode: str) -> List[CommercialUnit]:
    """Best-effort sync of commercial table rows (no validation)."""
    units: List[CommercialUnit] = []
    for idx, row in enumerate(rows):
        try:
            area = float(row["area"].get() or 0)
            if area <= 0:
                continue
            block = (row["block"].get() or "").strip()
            if not block:
                continue
            units.append(
                CommercialUnit(
                    plot=ui_plot_label(row["plot"].get(), plot_mode),
                    block=block,
                    comm_type=row["type"].get(),
                    floor_label=(row["floor"].get() or "").strip(),
                    area_sqm=area,
                    sort_order=idx,
                )
            )
        except (ValueError, KeyError, TypeError):
            continue
    return units


def sync_landscape(other: OtherDetails, entries: Dict[str, Any]) -> None:
    for plot, entry in entries.items():
        try:
            other.landscape_area[plot] = float(entry.get() or 0)
        except (ValueError, TypeError):
            other.landscape_area[plot] = 0.0


def sync_hvac(other: OtherDetails, entries: Dict[str, Any]) -> None:
    for plot, entry in entries.items():
        try:
            other.hvac_water[plot] = float(entry.get() or 0)
        except (ValueError, TypeError):
            other.hvac_water[plot] = 0.0


def sync_swimming_pool(
    other: OtherDetails,
    volume_entries: Dict[str, Any],
    status_vars: Dict[str, Any],
) -> None:
    for plot, status_var in status_vars.items():
        status = POOL_STATUS_LABELS.get(status_var.get(), POOL_NOT_APPLICABLE)
        other.swimming_pool_status[plot] = status
        other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
        if status == POOL_NOT_APPLICABLE:
            other.swimming_pool[plot] = 0.0
        else:
            try:
                other.swimming_pool[plot] = float(volume_entries[plot].get() or 0)
            except (ValueError, TypeError, KeyError):
                other.swimming_pool[plot] = 0.0


def auto_fire_tank_liters(
    plot: str,
    residential: List[ResidentialWing],
    project: ProjectData,
    other: OtherDetails,
) -> int:
    """Resolve fire tank capacity from wings or project-level building data."""
    heights_types = [
        (w.building_height_m, w.building_type)
        for w in residential
        if w.plot == plot and w.building_height_m > 0
    ]
    if heights_types:
        max_height = max(h for h, _ in heights_types)
        btype = next((t for h, t in heights_types if h == max_height), "")
        return fire_tank_capacity_liters(max_height, btype)
    if project.building_height_m > 0:
        return fire_tank_capacity_liters(
            project.building_height_m,
            project.building_type or "Residential Apartment",
        )
    return int(other.fire_tank.get(plot, 0))


def apply_fire_tanks(state: AppState) -> None:
    """Auto-populate fire tank capacities for all active plots."""

    for plot in active_plots(state.project.plot_mode):
        state.other.fire_tank[plot] = float(
            auto_fire_tank_liters(plot, state.residential, state.project, state.other)
        )


def prepare_live_calculation(state: AppState) -> None:
    """Run all automation steps before calculator executes."""
    apply_building_parser(state.project, state.residential)
    apply_fire_tanks(state)


def sync_pages_to_state(app: Any) -> None:
    """Pull current UI page inputs into AppState (called before live calc)."""
    state = app.app_state
    res_page = app.pages.get("Residential")
    if res_page and hasattr(res_page, "rows"):
        state.residential = wings_from_ui_rows(res_page.rows, state.project.plot_mode)

    com_page = app.pages.get("Commercial")
    if com_page and hasattr(com_page, "rows"):
        state.commercial = commercial_from_ui_rows(com_page.rows, state.project.plot_mode)

    if hasattr(app, "_le"):
        sync_landscape(state.other, app._le)
    if hasattr(app, "_he"):
        sync_hvac(state.other, app._he)
    if hasattr(app, "_pe") and hasattr(app, "_pool_status"):
        sync_swimming_pool(state.other, app._pe, app._pool_status)

    prepare_live_calculation(state)

# ==================== services/environmental_calculator.py ====================
"""Solid waste and sewage generation calculations from water-demand results."""





def _aggregate_population(results: CalculationResults, plot_mode: str) -> tuple[int, int]:
    res_pop = 0
    comm_pop = 0
    for plot_name in active_plots(plot_mode):
        plot = results.plots.get(plot_name)
        if not plot:
            continue
        res_pop += plot.res_population
        comm_pop += plot.com_population
    return res_pop, comm_pop


def _total_stp_capacity_kld(results: CalculationResults) -> float:
    if results.total:
        return float(results.total.get("Total STP Capacity (KLD)", 0) or 0)
    return 0.0


def _stp_sludge_kg_day(stp_capacity_kld: float) -> float:
    return round(stp_capacity_kld * STP_SLUDGE_KG_PER_KLD_DAY, 2)


def _owc_area_range(owc_capacity_kg_day: float) -> str:
    if owc_capacity_kg_day <= 0:
        return ""
    low = round(owc_capacity_kg_day * OWC_AREA_LOW_FACTOR)
    high = round(owc_capacity_kg_day * OWC_AREA_HIGH_FACTOR)
    return f"{low}-{high}"


def _sewage_area_range(stp_capacity_kld: float) -> str:
    if stp_capacity_kld <= 0:
        return ""
    low = round(stp_capacity_kld * SEWAGE_STP_AREA_LOW_FACTOR)
    high = round(stp_capacity_kld * SEWAGE_STP_AREA_HIGH_FACTOR)
    return f"{low}-{high}"


def calculate_solid_waste(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> SolidWasteResults:
    out = SolidWasteResults()
    if not results or not results.plots:
        return out

    res_pop, comm_pop = _aggregate_population(results, project.plot_mode)
    out.res_population = res_pop
    out.comm_population = comm_pop

    out.res_total_waste_kg_day = round(res_pop * RESIDENTIAL_WASTE_KG_PER_CAPITA_DAY, 2)
    out.res_wet_waste_kg_day = round(out.res_total_waste_kg_day * RESIDENTIAL_WET_WASTE_FRACTION, 2)
    out.res_dry_waste_kg_day = round(out.res_total_waste_kg_day * RESIDENTIAL_DRY_WASTE_FRACTION, 2)

    out.comm_total_waste_kg_day = round(comm_pop * COMMERCIAL_WASTE_KG_PER_CAPITA_DAY, 2)
    out.comm_wet_waste_kg_day = round(out.comm_total_waste_kg_day * COMMERCIAL_WET_WASTE_FRACTION, 2)
    out.comm_dry_waste_kg_day = round(out.comm_total_waste_kg_day * COMMERCIAL_DRY_WASTE_FRACTION, 2)

    out.total_waste_kg_day = round(out.res_total_waste_kg_day + out.comm_total_waste_kg_day, 2)
    out.total_wet_waste_kg_day = round(out.res_wet_waste_kg_day + out.comm_wet_waste_kg_day, 2)
    out.total_dry_waste_kg_day = round(out.res_dry_waste_kg_day + out.comm_dry_waste_kg_day, 2)

    out.wet_waste_considered_kg_day = float(math.ceil(out.res_wet_waste_kg_day))
    out.garden_waste_considered_kg_day = round(res_pop / GARDEN_WASTE_POP_DIVISOR, 2) if res_pop > 0 else 0.0

    stp_capacity = _total_stp_capacity_kld(results)
    out.stp_sludge_kg_day = _stp_sludge_kg_day(stp_capacity)
    out.owc_plant_capacity_kg_day = round(
        out.wet_waste_considered_kg_day + out.garden_waste_considered_kg_day + out.stp_sludge_kg_day,
        2,
    )

    out.res_e_waste_kg_year = round(res_pop * RESIDENTIAL_E_WASTE_KG_PER_CAPITA_YEAR, 2)
    out.comm_e_waste_kg_year = round(comm_pop * COMMERCIAL_E_WASTE_KG_PER_CAPITA_YEAR, 2)
    out.total_e_waste_kg_year = round(out.res_e_waste_kg_year + out.comm_e_waste_kg_year, 2)
    out.approx_area_sqm = _owc_area_range(out.owc_plant_capacity_kg_day)
    return out


def calculate_sewage_generation(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> SewageGenerationResults:
    out = SewageGenerationResults()
    if not results or not results.plots:
        return out

    res_pop, comm_pop = _aggregate_population(results, project.plot_mode)
    out.res_population = res_pop
    out.comm_population = comm_pop

    out.res_sewage_kld = round(
        res_pop * RESIDENTIAL_SEWAGE_LPCD * SEWAGE_GENERATION_PERCENT / 1000.0,
        2,
    )
    out.comm_sewage_kld = round(
        comm_pop * COMMERCIAL_SEWAGE_LPCD * SEWAGE_GENERATION_PERCENT / 1000.0,
        2,
    )
    out.total_sewage_kld = round(out.res_sewage_kld + out.comm_sewage_kld, 2)

    out.proposed_stp_capacity_kld = _total_stp_capacity_kld(results)
    out.stp_sludge_kg_day = _stp_sludge_kg_day(out.proposed_stp_capacity_kld)
    out.approx_area_sqm = _sewage_area_range(out.proposed_stp_capacity_kld)
    return out


def calculate_environmental(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> EnvironmentalResults:
    return EnvironmentalResults(
        solid_waste=calculate_solid_waste(results, project),
        sewage=calculate_sewage_generation(results, project),
    )

# ==================== services/result_tables.py ====================
"""Shared table row builders for OHT, STP, and Preview — single source of truth for GUI/PDF/Excel."""




TableRow = Tuple[str, str, str]  # description, value, unit


@dataclass(frozen=True)
class TableSection:
    title: str
    rows: Tuple[TableRow, ...]


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def _stp_section_rows(stp) -> Tuple[TableRow, ...]:
    """Mirror excel_exporter._build_stp data rows."""
    return (
        ("Total Water Requirement", _fmt_int(stp.total_water_lpd), "LITERS/DAY"),
        ("Sewage Generation @90%", _fmt_int(stp.sewage_lpd), "LITERS/DAY"),
        ("Capacity of Sewage Generation", _fmt_float(stp.sewage_kld), "KLD"),
        ("Say STP Capacity", _fmt_float(stp.say_stp_kld), "KLD"),
        ("Treated Water After Filtration", _fmt_int(stp.treated_water_lpd), "LITERS/DAY"),
        ("Reuse Water for Flushing", _fmt_int(stp.reuse_flushing_lpd), "LITERS/DAY"),
        ("Reuse Water for Landscape", _fmt_int(stp.reuse_landscape_lpd), "LITERS/DAY"),
        ("Reuse Water for HVAC", _fmt_int(stp.reuse_hvac_lpd), "LITERS/DAY"),
        ("Excess Treated Water", _fmt_int(stp.excess_treated_lpd), "LITERS/DAY"),
    )


def build_oht_table_sections(
    results: CalculationResults,
    plot_names: Sequence[str],
) -> List[TableSection]:
    sections: List[TableSection] = []
    for plot_name in plot_names:
        plot = results.plots.get(plot_name)
        if plot is None:
            continue
        rows: List[TableRow] = []
        if not plot.oht_rows:
            rows.append(("No OHT data", "—", ""))
        else:
            total_dom = total_flu = total_fb = total_fo = 0.0
            for row in plot.oht_rows:
                wing = str(row.get("wing", ""))
                dom = float(row.get("domestic_kld", 0) or 0)
                flu = float(row.get("flushing_kld", 0) or 0)
                fb = float(row.get("fire_break_kld", 0) or 0)
                fo = float(row.get("fire_oht_kld", 0) or 0)
                total_dom += dom
                total_flu += flu
                total_fb += fb
                total_fo += fo
                rows.extend(
                    [
                        (f"{wing} — Domestic OHT", _fmt_float(dom), "KLD"),
                        (f"{wing} — Flushing OHT", _fmt_float(flu), "KLD"),
                        (f"{wing} — Fire Break Tank", _fmt_float(fb), "KLD"),
                        (f"{wing} — Fire OHT Tank", _fmt_float(fo), "KLD"),
                    ]
                )
            rows.extend(
                [
                    ("No. of OHTs", str(len(plot.oht_rows)), "Nos"),
                    ("Total Domestic OHT Capacity", _fmt_float(total_dom), "KLD"),
                    ("Total Flushing OHT Capacity", _fmt_float(total_flu), "KLD"),
                    ("Total Fire Break Tank Capacity", _fmt_float(total_fb), "KLD"),
                    ("Total Fire OHT Tank Capacity", _fmt_float(total_fo), "KLD"),
                ]
            )
        sections.append(TableSection(title=f"OHT Details — {plot_name}", rows=tuple(rows)))
    return sections


def build_stp_table_sections(
    results: CalculationResults,
    plot_names: Sequence[str],
) -> List[TableSection]:
    sections: List[TableSection] = []
    for plot_name in plot_names:
        plot = results.plots.get(plot_name)
        if plot is None:
            continue
        if not plot.stp_sections:
            sections.append(TableSection(title=f"STP Summary — {plot_name}", rows=(("No STP data", "—", ""),)))
            continue
        for stp in plot.stp_sections:
            scope_rows = list(_stp_section_rows(stp))
            sections.append(
                TableSection(
                    title=f"STP for {stp.scope} — {plot_name}",
                    rows=tuple(scope_rows),
                )
            )
        sections.append(
            TableSection(
                title=f"Total STP — {plot_name}",
                rows=(("Proposed STP Capacity", _fmt_float(plot.stp_capacity_kld), "KLD"),),
            )
        )
    return sections


def _plot_water_rows(plot: PlotResults, project_type: str = "") -> Tuple[TableRow, ...]:
    rows: List[TableRow] = [
        ("Residential Population", _fmt_int(plot.res_population), "Nos"),
        ("Commercial Population", _fmt_int(plot.com_population), "Nos"),
        ("Total Population", _fmt_int(plot.total_population), "Nos"),
        ("Residential Water Demand", _fmt_int(plot.res_total_lpd), "LPD"),
        ("Commercial Water Demand", _fmt_int(plot.com_total_lpd), "LPD"),
    ]
    if plot.landscape_dry_lpd > 0:
        rows.append(("Landscape (Dry Season)", _fmt_int(plot.landscape_dry_lpd), "LPD"))
    if show_swimming_section(project_type) and plot.swimming_pool_lpd > 0:
        rows.append(("Swimming Pool", _fmt_int(plot.swimming_pool_lpd), "LPD"))
    if hvac_applicable(project_type) and plot.hvac_lpd > 0:
        rows.append(("HVAC Makeup Water", _fmt_int(plot.hvac_lpd), "LPD"))
    rows.append(("Grand Total Water Demand", _fmt_int(plot.dry_total_water_lpd), "LPD"))
    return tuple(rows)


def _plot_sewage_rows(plot: PlotResults) -> Tuple[TableRow, ...]:
    return (
        ("Total Sewage Generated", _fmt_int(plot.sewage_lpd), "LPD"),
        ("Proposed STP Capacity", _fmt_float(plot.stp_capacity_kld), "KLD"),
    )


def _plot_ugt_rows(plot: PlotResults) -> Tuple[TableRow, ...]:
    if not plot.ugt_sections:
        return ()
    rows: List[TableRow] = []
    for sec in plot.ugt_sections:
        rows.append(
            (
                sec.description,
                _fmt_int(sec.total_storage_liters),
                "Litres",
            )
        )
    rows.append(("Domestic UGT (summary)", _fmt_int(plot.ugt_domestic_liters), "Litres"))
    rows.append(("Flushing UGT (summary)", _fmt_int(plot.ugt_flushing_liters), "Litres"))
    return tuple(rows)


def _plot_oht_summary_rows(plot: PlotResults) -> Tuple[TableRow, ...]:
    if not plot.oht_rows:
        return ()
    total_dom = sum(float(r.get("domestic_kld", 0) or 0) for r in plot.oht_rows)
    total_flu = sum(float(r.get("flushing_kld", 0) or 0) for r in plot.oht_rows)
    total_fb = sum(float(r.get("fire_break_kld", 0) or 0) for r in plot.oht_rows)
    total_fo = sum(float(r.get("fire_oht_kld", 0) or 0) for r in plot.oht_rows)
    return (
        ("No. of OHTs", str(len(plot.oht_rows)), "Nos"),
        ("Total Domestic OHT Capacity", _fmt_float(total_dom), "KLD"),
        ("Total Flushing OHT Capacity", _fmt_float(total_flu), "KLD"),
        ("Total Fire Break Tank Capacity", _fmt_float(total_fb), "KLD"),
        ("Total Fire OHT Tank Capacity", _fmt_float(total_fo), "KLD"),
    )


def _plot_stp_summary_rows(plot: PlotResults) -> Tuple[TableRow, ...]:
    if not plot.stp_sections:
        return ()
    total_sewage = sum(s.sewage_lpd for s in plot.stp_sections)
    return (
        ("Total Sewage Generated", _fmt_int(total_sewage), "LPD"),
        ("Proposed STP Capacity", _fmt_float(plot.stp_capacity_kld), "KLD"),
    )


def _fire_fighting_rows(plot: PlotResults) -> Tuple[TableRow, ...]:
    if plot.fire_tank_liters <= 0:
        return ()
    return (("Fire Water Tank Capacity", _fmt_int(plot.fire_tank_liters), "Litres"),)


def _other_calc_rows(
    plot: PlotResults,
    project_type: str,
    other: Optional[OtherDetails],
) -> Tuple[TableRow, ...]:
    rows: List[TableRow] = []
    if other and plot.plot in other.landscape_area and other.landscape_area.get(plot.plot, 0) > 0:
        rows.append(("Landscape Area", _fmt_float(other.landscape_area[plot.plot], 0), "Sq.m"))
    if show_swimming_section(project_type) and plot.swimming_pool_lpd > 0:
        rows.append(("Swimming Pool Demand", _fmt_int(plot.swimming_pool_lpd), "LPD"))
    if hvac_applicable(project_type) and plot.hvac_lpd > 0:
        rows.append(("HVAC Makeup Water", _fmt_int(plot.hvac_lpd), "LPD"))
    return tuple(rows)


def _project_header_rows(project: ProjectData) -> Tuple[TableRow, ...]:
    return (
        ("Project Name", project.project_name or "—", ""),
        ("Reference No.", project.project_no or project.project_id or "—", ""),
        ("Date", project.date or "—", ""),
    )


def build_solid_waste_table_sections(
    project: ProjectData,
    environmental: EnvironmentalResults,
) -> List[TableSection]:
    sw = environmental.solid_waste
    if sw.res_population <= 0 and sw.comm_population <= 0:
        return [TableSection(title="Solid Waste Calculations", rows=(("Enter population data first", "—", ""),))]

    sections: List[TableSection] = [
        TableSection(title="Solid Waste Calculations", rows=_project_header_rows(project)),
        TableSection(
            title="Residential Waste Generated",
            rows=(
                ("Total Population", _fmt_int(sw.res_population), "nos"),
                ("Total Waste Generated (0.45 kg/capita/day)", _fmt_float(sw.res_total_waste_kg_day), "kgs/day"),
                ("Wet Waste Generated (60% of Total Waste)", _fmt_float(sw.res_wet_waste_kg_day), "kgs/day"),
                ("Dry Waste Generated (40% of Total Waste)", _fmt_float(sw.res_dry_waste_kg_day), "kgs/day"),
            ),
        ),
        TableSection(
            title="Commercial Waste Generated",
            rows=(
                ("Total Population", _fmt_int(sw.comm_population), "nos"),
                ("Total Waste Generated (0.25 kg/capita/day)", _fmt_float(sw.comm_total_waste_kg_day), "kgs/day"),
                ("Wet Waste Generated (40% of Total Waste)", _fmt_float(sw.comm_wet_waste_kg_day), "kgs/day"),
                ("Dry Waste Generated (60% of Total Waste)", _fmt_float(sw.comm_dry_waste_kg_day), "kgs/day"),
            ),
        ),
        TableSection(
            title="Total Waste Generated",
            rows=(
                ("Total Waste Generated", _fmt_float(sw.total_waste_kg_day), "kgs/day"),
                ("Wet Waste Generated", _fmt_float(sw.total_wet_waste_kg_day), "kgs/day"),
                ("Dry Waste Generated", _fmt_float(sw.total_dry_waste_kg_day), "kgs/day"),
            ),
        ),
        TableSection(
            title="Waste Consideration",
            rows=(
                ("Wet Waste considered", _fmt_float(sw.wet_waste_considered_kg_day, 0), "kgs/day"),
                ("Garden Waste Considered", _fmt_float(sw.garden_waste_considered_kg_day), "kgs/day"),
                ("STP Sludge produced", _fmt_float(sw.stp_sludge_kg_day), "kgs/day"),
                ("Proposed OWC Plant Capacity", _fmt_float(sw.owc_plant_capacity_kg_day), "kgs/day"),
            ),
        ),
        TableSection(
            title="Total E-Waste Generated",
            rows=(
                ("Residential E-Waste (1 kg/capita/annum)", _fmt_float(sw.res_e_waste_kg_year), "kgs/annum"),
                ("Commercial E-Waste (1.5 kg/capita/annum)", _fmt_float(sw.comm_e_waste_kg_year), "kgs/annum"),
                ("Total E-Waste (Resi.+Comm.) Generated", _fmt_float(sw.total_e_waste_kg_year), "kgs/annum"),
                ("Approx. Area Required", sw.approx_area_sqm or "—", "Sq. mtrs."),
            ),
        ),
    ]
    return sections


def build_sewage_generation_table_sections(
    project: ProjectData,
    environmental: EnvironmentalResults,
) -> List[TableSection]:
    sg = environmental.sewage
    if sg.res_population <= 0 and sg.comm_population <= 0:
        return [TableSection(title="Sewage Generation Calculations", rows=(("Enter population data first", "—", ""),))]

    return [
        TableSection(title="Sewage Generation Calculations", rows=_project_header_rows(project)),
        TableSection(
            title="Residential Sewage Generated",
            rows=(
                ("Total Population", _fmt_int(sg.res_population), "nos"),
                ("Percentage of Sewage", "90", "%"),
                ("Total Sewage Generated", _fmt_float(sg.res_sewage_kld), "KLD"),
            ),
        ),
        TableSection(
            title="Commercial Sewage Generated",
            rows=(
                ("Total Population", _fmt_int(sg.comm_population), "nos"),
                ("Percentage of Sewage", "90", "%"),
                ("Total Sewage Generated", _fmt_float(sg.comm_sewage_kld), "KLD"),
            ),
        ),
        TableSection(
            title="Total Sewage Generated",
            rows=(
                ("Total Sewage Generated", _fmt_float(sg.total_sewage_kld), "KLD"),
                ("Proposed STP Capacity", _fmt_float(sg.proposed_stp_capacity_kld), "KLD"),
                ("STP Sludge produced", _fmt_float(sg.stp_sludge_kg_day), "Kgs/Day"),
                ("Approx. Area Required", sg.approx_area_sqm or "—", "Sq. mtrs."),
            ),
        ),
    ]


def build_preview_table_sections(
    project: ProjectData,
    results: CalculationResults,
    plot_names: Sequence[str],
    other: Optional[OtherDetails] = None,
    rwh_summary: Optional[Sequence[TableRow]] = None,
    environmental: Optional[EnvironmentalResults] = None,
) -> List[TableSection]:
    """Build preview sections; only includes modules applicable to project type."""
    if not results or not results.plots:
        return [TableSection(title="Preview", rows=(("Complete project data to see preview", "—", ""),))]

    pages = visible_pages(project.project_type)
    sections: List[TableSection] = []

    project_rows: List[TableRow] = [
        ("Project Name", project.project_name or "—", ""),
        ("Reference No.", project.project_no or project.project_id or "—", ""),
        ("Project Type", project_type_label(project.project_type), ""),
        ("Client Name", project.client_name or "—", ""),
        ("Location", project.project_location or "—", ""),
        ("Engineer", project.engineer_name or "—", ""),
        ("Date", project.date or "—", ""),
    ]
    sections.append(TableSection(title="Project Summary", rows=tuple(project_rows)))

    tot = results.total
    water_rows: List[TableRow] = [
        ("Total Population", _fmt_int(tot.get("Total Population", 0)), "Nos"),
        ("Total Water Demand", _fmt_int(tot.get("Total Water (LPD)", 0)), "LPD"),
        ("Total Residential Population", _fmt_int(tot.get("Total Residential Population", 0)), "Nos"),
        ("Total Commercial Population", _fmt_int(tot.get("Total Commercial Population", 0)), "Nos"),
    ]
    for plot_name in plot_names:
        plot = results.plots.get(plot_name)
        if plot and plot.dry_total_water_lpd > 0:
            water_rows.extend(_plot_water_rows(plot, project.project_type))
    if len(water_rows) > 4:
        sections.append(TableSection(title="Water Demand Summary", rows=tuple(water_rows)))

    if "Sewage" in pages and environmental:
        sg = environmental.sewage
        if sg.res_population > 0 or sg.comm_population > 0:
            sections.extend(build_sewage_generation_table_sections(project, environmental))

    if "STP" in pages:
        stp_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot:
                stp_rows.extend(_plot_stp_summary_rows(plot))
                for stp in plot.stp_sections:
                    stp_rows.extend(_stp_section_rows(stp))
        if stp_rows:
            sections.append(TableSection(title="STP Summary", rows=tuple(stp_rows)))

    if "SolidWaste" in pages and environmental:
        sw = environmental.solid_waste
        if sw.res_population > 0 or sw.comm_population > 0:
            sw_rows: List[TableRow] = []
            for sec in build_solid_waste_table_sections(project, environmental):
                if sec.title == "Solid Waste Calculations":
                    continue
                sw_rows.extend(sec.rows)
            if sw_rows:
                sections.append(TableSection(title="Solid Waste Summary", rows=tuple(sw_rows)))

    if "OHT" in pages:
        oht_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot:
                summary = _plot_oht_summary_rows(plot)
                if summary:
                    oht_rows.extend(summary)
        if oht_rows:
            sections.append(TableSection(title="OHT Summary", rows=tuple(oht_rows)))

    if "UGT" in pages:
        ugt_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot:
                ugt_rows.extend(_plot_ugt_rows(plot))
        if ugt_rows:
            sections.append(TableSection(title="UGT Summary", rows=tuple(ugt_rows)))

        fire_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot:
                fire_rows.extend(_fire_fighting_rows(plot))
        if fire_rows:
            sections.append(TableSection(title="Fire Fighting Summary", rows=tuple(fire_rows)))

    if "RWH" in pages and rwh_summary:
        sections.append(TableSection(title="RWH Summary", rows=tuple(rwh_summary)))

    other_rows: List[TableRow] = []
    for plot_name in plot_names:
        plot = results.plots.get(plot_name)
        if plot:
            other_rows.extend(_other_calc_rows(plot, project.project_type, other))
    if other_rows:
        sections.append(TableSection(title="Other Applicable Calculations", rows=tuple(other_rows)))

    return sections


def stp_rows_for_excel_check(results: CalculationResults, plot_name: str) -> List[TableRow]:
    """Flat STP rows used to verify Excel/PDF alignment in tests."""
    plot = results.plots.get(plot_name)
    if not plot:
        return []
    rows: List[TableRow] = []
    for stp in plot.stp_sections:
        rows.extend(_stp_section_rows(stp))
    return rows


def oht_totals_for_check(results: CalculationResults, plot_name: str) -> Tuple[float, float, float, float]:
    plot = results.plots.get(plot_name)
    if not plot or not plot.oht_rows:
        return 0.0, 0.0, 0.0, 0.0
    total_dom = sum(float(r.get("domestic_kld", 0) or 0) for r in plot.oht_rows)
    total_flu = sum(float(r.get("flushing_kld", 0) or 0) for r in plot.oht_rows)
    total_fb = sum(float(r.get("fire_break_kld", 0) or 0) for r in plot.oht_rows)
    total_fo = sum(float(r.get("fire_oht_kld", 0) or 0) for r in plot.oht_rows)
    return total_dom, total_flu, total_fb, total_fo

# ==================== services/pdf_exporter.py ====================





class PDFExporter:
    def __init__(
        self,
        project: ProjectData,
        results: CalculationResults,
        logo_path: Optional[str] = None,
    ) -> None:
        self.project = project
        self.results = results
        self.logo_path = logo_path or self._default_logo_path()
        self.styles = getSampleStyleSheet()
        self.page_width = letter[0] - 40

    def _default_logo_path(self) -> Optional[str]:
        base = APP_DIR
        for name in ("logo.png", "logo.jpg"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
        return None

    def export(self, file_path: str) -> None:
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=30,
        )
        story: List[Any] = []
        story.extend(self._build_cover())
        story.append(PageBreak())
        story.extend(self._build_consolidated())
        story.append(PageBreak())
        story.extend(self._build_plot_demand("Plot-A"))
        story.append(PageBreak())
        story.extend(self._build_plot_demand("Plot-B"))
        story.append(PageBreak())
        story.extend(self._build_ugt_oht("Plot-A"))
        story.append(PageBreak())
        story.extend(self._build_ugt_oht("Plot-B"))
        story.append(PageBreak())
        story.extend(self._build_stp("Plot-A"))
        story.append(PageBreak())
        story.extend(self._build_stp("Plot-B"))

        environmental = calculate_environmental(self.results, self.project)
        story.append(PageBreak())
        story.extend(
            self._build_environmental_tables(
                "SEWAGE GENERATION",
                BRAND_STP_PURPLE,
                build_sewage_generation_table_sections(self.project, environmental),
            )
        )
        story.append(PageBreak())
        story.extend(
            self._build_environmental_tables(
                "SOLID WASTE GENERATION",
                BRAND_DEMAND_ORANGE,
                build_solid_waste_table_sections(self.project, environmental),
            )
        )
        doc.build(story, onFirstPage=self._page_template, onLaterPages=self._page_template)

    def _page_template(self, canvas, doc) -> None:
        """Draw header logo (right) and footer on every page."""
        canvas.saveState()
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = ImageReader(self.logo_path)
                iw, ih = img.getSize()
                max_w, max_h = 90, 36
                scale = min(max_w / max(iw, 1), max_h / max(ih, 1))
                w, h = iw * scale, ih * scale
                canvas.drawImage(
                    img,
                    letter[0] - w - 30,
                    letter[1] - h - 28,
                    width=w,
                    height=h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(30, letter[1] - 30, COMPANY_NAME)
        canvas.setFont("Helvetica", 6)
        canvas.drawCentredString(letter[0] / 2, 15, COMPANY_FOOTER)
        canvas.restoreState()

    def _footer(self, canvas, doc) -> None:
        self._page_template(canvas, doc)

    def _p(self, text: str, style_name: str = "Normal", **kwargs) -> Paragraph:
        style = ParagraphStyle(style_name, parent=self.styles["Normal"], **kwargs)
        return Paragraph(text, style)

    def _th(self, text: str) -> Paragraph:
        return self._p(
            f"<b>{text}</b>",
            "TH",
            fontSize=6.5,
            textColor=colors.whitesmoke,
            alignment=1,
            fontName="Helvetica-Bold",
        )

    def _tc(self, text: str, align: int = 1) -> Paragraph:
        return self._p(str(text), "TC", fontSize=6, textColor=colors.HexColor("#111111"), alignment=align)

    def _section_bar(self, title: str, color: str) -> Table:
        sec_style = ParagraphStyle(
            "Sec",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.whitesmoke,
            alignment=1,
            fontName="Helvetica-Bold",
        )
        return Table(
            [[Paragraph(f"<b>{title}</b>", sec_style)]],
            colWidths=[self.page_width],
            style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color))],
        )

    def _eng_header(self) -> Paragraph:
        return self._p(
            f"<b>DESIGN ENGINEER NAME :- MR.{self.project.engineer_name.upper()} &nbsp;&nbsp;&nbsp;&nbsp; DATE :- {self.project.date}</b>",
            "Eng",
            fontSize=7,
            fontName="Helvetica-Bold",
        )

    def _grid_style(self, header: bool = True) -> TableStyle:
        cmds = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            cmds.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND_HEADER_GRAY)))
        return TableStyle(cmds)

    def _consolidated_col_widths(self, total_width: float) -> List[float]:
        """Proportional 10-column widths that fit within printable page width."""
        return [
            total_width * 0.05,   # SR.NO
            total_width * 0.22,   # DESCRIPTION
            total_width * 0.10,   # PLOT-A RES
            total_width * 0.10,   # PLOT-A COMM
            total_width * 0.10,   # PLOT-A SUB
            total_width * 0.10,   # PLOT-B RES
            total_width * 0.10,   # PLOT-B COMM
            total_width * 0.10,   # PLOT-B SUB
            total_width * 0.08,   # TOTAL
            total_width * 0.05,   # UNITS
        ]

    def _consolidated_header_row(self) -> list:
        return [
            self._th("SR.NO"),
            self._th("DESCRIPTION"),
            self._th("PLOT-A RES"),
            self._th("PLOT-A COMM"),
            self._th("PLOT-A SUB"),
            self._th("PLOT-B RES"),
            self._th("PLOT-B COMM"),
            self._th("PLOT-B SUB"),
            self._th("TOTAL"),
            self._th("UNITS"),
        ]

    def _consolidated_table(self, data_rows: list, col_widths: List[float]) -> Table:
        rows = [self._consolidated_header_row(), *data_rows]
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._grid_style())
        return table

    def _consolidated_section_heading(self, section: str, subtitle: str = "") -> Paragraph:
        text = f"<b>{section}</b>"
        if subtitle:
            text += f"<br/><b>{subtitle}</b>"
        return self._p(
            text,
            "ConsSec",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(BRAND_DARK_GRAY),
            spaceAfter=6,
        )

    def _consolidated_subheading(self, title: str) -> Paragraph:
        return self._p(
            f"<b>{title}</b>",
            "ConsSub",
            fontSize=7.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(BRAND_DARK_GRAY),
            spaceBefore=10,
            spaceAfter=4,
        )

    def _build_consolidated(self) -> List[Any]:
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar("CONSOLIDATED STATEMENT", BRAND_DARK_GRAY))
        story.append(Spacer(1, 8))

        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        tot = self.results.total
        col_widths = self._consolidated_col_widths(self.page_width)

        def kld(v: float) -> str:
            return f"{v / 1000:.2f}"

        def empty_sr() -> Paragraph:
            return self._tc("", 0)

        # --- SECTION-8: Building / Population ---
        building_rows = [
            [
                empty_sr(),
                self._tc("Number Of Building", 0),
                self._tc(pa.num_buildings_res),
                self._tc(pa.num_buildings_com),
                self._tc(pa.num_buildings_res + pa.num_buildings_com),
                self._tc(pb.num_buildings_res),
                self._tc(pb.num_buildings_com),
                self._tc(pb.num_buildings_res + pb.num_buildings_com),
                self._tc(
                    pa.num_buildings_res + pa.num_buildings_com
                    + pb.num_buildings_res + pb.num_buildings_com
                ),
                self._tc("NO.S"),
            ],
            [
                empty_sr(),
                self._tc("Total Number Of Flats", 0),
                self._tc(pa.total_flats),
                self._tc(0),
                self._tc(pa.total_flats),
                self._tc(pb.total_flats),
                self._tc(0),
                self._tc(pb.total_flats),
                self._tc(tot.get("Total Flats", 0)),
                self._tc("NO.S"),
            ],
            [
                empty_sr(),
                self._tc("Total Residential Building Population", 0),
                self._tc(pa.res_population),
                self._tc(pa.com_population),
                self._tc(pa.total_population),
                self._tc(pb.res_population),
                self._tc(pb.com_population),
                self._tc(pb.total_population),
                self._tc(tot.get("Total Population", 0)),
                self._tc("NO.S"),
            ],
        ]

        story.append(
            self._consolidated_section_heading("SECTION-8", "BUILDING / POPULATION DETAILS")
        )
        story.append(Spacer(1, 4))
        story.append(self._consolidated_table(building_rows, col_widths))
        story.append(Spacer(1, 8))

        # --- DRY SEASON ---
        dry_specs = [
            ("Fresh Water Requirement", pa.res_domestic_lpd, pa.com_domestic_lpd, pb.res_domestic_lpd, pb.com_domestic_lpd),
            ("Flushing Water Requirement", pa.res_flushing_lpd, pa.com_flushing_lpd, pb.res_flushing_lpd, pb.com_flushing_lpd),
            ("Kitchen Water Requirement", pa.kitchen_water_lpd, 0, pb.kitchen_water_lpd, 0),
            ("Landscape Water Requirement", pa.landscape_dry_lpd, 0, pb.landscape_dry_lpd, 0),
            ("Swimming Pool Makeup Water Requirement", pa.swimming_pool_lpd, 0, pb.swimming_pool_lpd, 0),
            ("HVAC Water Requirement", pa.hvac_lpd, 0, pb.hvac_lpd, 0),
            (
                "Total Water Requirement",
                pa.dry_total_water_lpd,
                pa.com_total_lpd + pa.landscape_dry_lpd + pa.swimming_pool_lpd + pa.hvac_lpd + pa.kitchen_water_lpd,
                pb.dry_total_water_lpd,
                pb.com_total_lpd + pb.landscape_dry_lpd + pb.swimming_pool_lpd + pb.hvac_lpd + pb.kitchen_water_lpd,
            ),
            ("Total Treated Water", pa.dry_treated_water_lpd, 0, pb.dry_treated_water_lpd, 0),
            ("Excess Treated Water To Corporation Line", pa.dry_excess_treated_lpd, 0, pb.dry_excess_treated_lpd, 0),
        ]
        dry_data_rows = []
        for idx, (desc, a_res, a_com, b_res, b_com) in enumerate(dry_specs, 1):
            if idx == 1:
                a_sub = a_res + a_com
                b_sub = b_res + b_com
            elif idx == 2:
                a_sub = a_res + a_com
                b_sub = b_res + b_com
            elif idx in (3, 4, 5, 6):
                a_sub = a_res
                b_sub = b_res
            elif idx == 7:
                a_sub = pa.dry_total_water_lpd
                b_sub = pb.dry_total_water_lpd
            elif idx == 8:
                a_sub = pa.dry_treated_water_lpd
                b_sub = pb.dry_treated_water_lpd
            else:
                a_sub = pa.dry_excess_treated_lpd
                b_sub = pb.dry_excess_treated_lpd
            dry_data_rows.append(
                [
                    empty_sr(),
                    self._tc(desc, 0),
                    self._tc(kld(a_res if idx <= 6 else a_sub)),
                    self._tc(kld(a_com if idx <= 2 else 0)),
                    self._tc(kld(a_sub)),
                    self._tc(kld(b_res if idx <= 6 else b_sub)),
                    self._tc(kld(b_com if idx <= 2 else 0)),
                    self._tc(kld(b_sub)),
                    self._tc(kld(a_sub + b_sub)),
                    self._tc("KLD"),
                ]
            )

        story.append(
            KeepTogether(
                [
                    self._consolidated_subheading("DRY SEASON"),
                    Spacer(1, 4),
                    self._consolidated_table(dry_data_rows, col_widths),
                ]
            )
        )
        story.append(Spacer(1, 8))

        # --- WET SEASON ---
        wet_specs = [
            ("FRESH WATER REQUIREMENT", pa.res_domestic_lpd, pa.com_domestic_lpd),
            ("FLUSHING WATER REQUIREMENTS", pa.res_flushing_lpd, pa.com_flushing_lpd),
            ("KITCHEN WATER REQUIREMENT", pa.kitchen_water_lpd, 0),
            ("LANDSCAPE WATER REQUIRED", pa.landscape_wet_lpd, 0),
            ("SWIMMING POOL MAKEUP WATER REQUIRMENT", pa.swimming_pool_lpd, 0),
            ("HVAC WATER REQUIREMENT", pa.hvac_lpd, 0),
            ("TOTAL WATER REQUIREMENT", pa.wet_total_water_lpd, pa.com_total_lpd),
            ("TOTAL TREATED WATER", pa.wet_treated_water_lpd, 0),
            ("EXCESS TREATED WATER WATER TO COPORATION LINE", pa.wet_excess_treated_lpd, 0),
        ]
        wet_data_rows = []
        for idx, (desc, a_val, a_com) in enumerate(wet_specs, 1):
            b_val = {
                1: pb.res_domestic_lpd,
                2: pb.res_flushing_lpd,
                3: pb.kitchen_water_lpd,
                4: pb.landscape_wet_lpd,
                5: pb.swimming_pool_lpd,
                6: pb.hvac_lpd,
                7: pb.wet_total_water_lpd,
                8: pb.wet_treated_water_lpd,
                9: pb.wet_excess_treated_lpd,
            }[idx]
            b_com = (
                pb.com_domestic_lpd
                if idx == 1
                else (pb.com_flushing_lpd if idx == 2 else (pb.com_total_lpd if idx == 7 else 0))
            )
            a_sub = a_val + (a_com if idx <= 2 else 0) if idx <= 2 else a_val
            b_sub = b_val + (b_com if idx <= 2 else 0) if idx <= 2 else b_val
            if idx == 7:
                a_sub = pa.wet_total_water_lpd
                b_sub = pb.wet_total_water_lpd
            wet_data_rows.append(
                [
                    empty_sr(),
                    self._tc(desc, 0),
                    self._tc(kld(a_val if idx <= 5 else a_sub)),
                    self._tc(kld(a_com if idx <= 2 else 0)),
                    self._tc(kld(a_sub)),
                    self._tc(kld(b_val if idx <= 5 else b_sub)),
                    self._tc(kld(b_com if idx <= 2 else 0)),
                    self._tc(kld(b_sub)),
                    self._tc(kld(a_sub + b_sub)),
                    self._tc("KLD"),
                ]
            )

        story.append(
            KeepTogether(
                [
                    self._consolidated_subheading("WET SEASON"),
                    Spacer(1, 4),
                    self._consolidated_table(wet_data_rows, col_widths),
                ]
            )
        )
        story.append(Spacer(1, 8))

        # --- SECTION-9: UGT ---
        ugt_specs = [
            ("DOMESTIC UGT CAPACITY", pa.ugt_domestic_liters, pb.ugt_domestic_liters),
            ("FLUSHING UGT CAPACITY", pa.ugt_flushing_liters, pb.ugt_flushing_liters),
            ("FIRE UGT CAPACITY", pa.fire_tank_liters, pb.fire_tank_liters),
        ]
        ugt_data_rows = []
        for desc, a_v, b_v in ugt_specs:
            ugt_data_rows.append(
                [
                    empty_sr(),
                    self._tc(desc, 0),
                    self._tc(f"{a_v / 1000:.2f}"),
                    self._tc("0.00"),
                    self._tc(f"{a_v / 1000:.2f}"),
                    self._tc(f"{b_v / 1000:.2f}"),
                    self._tc("0.00"),
                    self._tc(f"{b_v / 1000:.2f}"),
                    self._tc(f"{(a_v + b_v) / 1000:.2f}"),
                    self._tc("LIT/DAY"),
                ]
            )

        story.append(
            KeepTogether(
                [
                    self._consolidated_section_heading("SECTION-9", "UGT DETAILS"),
                    Spacer(1, 4),
                    self._consolidated_table(ugt_data_rows, col_widths),
                ]
            )
        )
        story.append(Spacer(1, 8))

        # --- SECTION-10: STP ---
        stp_specs = [
            ("SEWAGE GENERATION", pa.sewage_lpd, pb.sewage_lpd),
            ("STP Capacity", pa.stp_capacity_kld * 1000, pb.stp_capacity_kld * 1000),
        ]
        stp_data_rows = []
        for desc, a_v, b_v in stp_specs:
            stp_data_rows.append(
                [
                    empty_sr(),
                    self._tc(desc, 0),
                    self._tc(f"{a_v / 1000:.2f}"),
                    self._tc("0.00"),
                    self._tc(f"{a_v / 1000:.2f}"),
                    self._tc(f"{b_v / 1000:.2f}"),
                    self._tc("0.00"),
                    self._tc(f"{b_v / 1000:.2f}"),
                    self._tc(f"{(a_v + b_v) / 1000:.2f}"),
                    self._tc("LIT/DAY"),
                ]
            )

        story.append(
            KeepTogether(
                [
                    self._consolidated_section_heading("SECTION-10", "STP DETAILS"),
                    Spacer(1, 4),
                    self._consolidated_table(stp_data_rows, col_widths),
                ]
            )
        )
        return story

    def _build_cover(self) -> List[Any]:
        story: List[Any] = []
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image(self.logo_path, width=2.5 * inch, height=1.2 * inch)
                img.hAlign = "CENTER"
                story.append(Spacer(1, 40))
                story.append(img)
            except Exception:
                story.append(Spacer(1, 80))
        else:
            story.append(Spacer(1, 80))

        story.append(
            self._p(
                f"<b>{COMPANY_NAME}</b>",
                "H1",
                fontSize=16,
                alignment=1,
                fontName="Helvetica-Bold",
            )
        )
        story.append(Spacer(1, 30))
        tc_left = ParagraphStyle(
            "TCL", parent=self.styles["Normal"], fontSize=8, alignment=0
        )
        cover_meta = [
            [Paragraph("<b>TITLE</b>", tc_left), Paragraph(": WATER DEMAND", tc_left)],
            [
                Paragraph("<b>PROJECT NAME</b>", tc_left),
                Paragraph(f": {self.project.project_name.upper()}", tc_left),
            ],
            [
                Paragraph("<b>CLIENT NAME</b>", tc_left),
                Paragraph(f": {self.project.client_name.upper()}", tc_left),
            ],
            [
                Paragraph("<b>PROJECT LOCATION</b>", tc_left),
                Paragraph(f": {self.project.project_location.upper()}", tc_left),
            ],
            [
                Paragraph("<b>PROJECT NO.</b>", tc_left),
                Paragraph(f": {self.project.project_no}", tc_left),
            ],
        ]
        t_cover = Table(cover_meta, colWidths=[130, 400])
        t_cover.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(t_cover)
        story.append(Spacer(1, 20))

        rev = self.project.revision
        rev_data = [
            [
                self._th("DATE"),
                self._th("REV. NO."),
                self._th("DESCRIPTION"),
                self._th("PRPD. BY"),
                self._th("CHKD. BY"),
                self._th("APPRD. BY"),
            ],
            [
                self._tc(rev.date or self.project.date),
                self._tc(rev.revision_no),
                self._tc(rev.description),
                self._tc(rev.prepared_by),
                self._tc(rev.checked_by),
                self._tc(rev.approved_by),
            ],
        ]
        t_rev = Table(rev_data, colWidths=[80, 60, 180, 70, 70, 70])
        t_rev.setStyle(self._grid_style())
        story.append(t_rev)
        story.append(Spacer(1, 20))
        story.append(
            self._p(COMPANY_ADDRESS, "Addr", fontSize=6, alignment=1)
        )
        story.append(self._p(COMPANY_CONTACT, "Contact", fontSize=6, alignment=1))
        return story

    def _build_plot_demand(self, plot_name: str) -> List[Any]:
        plot = self.results.plots[plot_name]
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar(f"WATER DEMAND - {plot_name}", BRAND_DEMAND_ORANGE))
        story.append(Spacer(1, 5))

        section_num = 1 if plot_name == "Plot-A" else 4
        story.append(self._p(f"<b>SECTION-{section_num} RESIDENTIAL</b>", "SecH", fontSize=7, fontName="Helvetica-Bold"))

        res_header = [
            self._th("SR.NO"),
            self._th("BLDG/WING"),
            self._th("NO. OF FLAT"),
            self._th("POPULATION PER FLAT"),
            self._th("POPULATION"),
            self._th("DOMESTIC WATER DEMAND (LIT/DAY)"),
            self._th("FLUSHING WATER DEMAND (LIT/DAY)"),
            self._th("TOTAL WATER DEMAND (LIT/DAY)"),
        ]
        res_rows = [res_header]
        for idx, w in enumerate(plot.residential_wings, 1):
            res_rows.append(
                [
                    self._tc(idx),
                    self._tc(w.wing),
                    self._tc(w.flats),
                    self._tc(w.pop_per_flat),
                    self._tc(w.population),
                    self._tc(w.domestic_lpd),
                    self._tc(w.flushing_lpd),
                    self._tc(w.total_lpd),
                ]
            )
        res_rows.append(
            [
                self._tc(""),
                self._tc("SUB-TOTAL", 0),
                self._tc(plot.total_flats),
                self._tc(""),
                self._tc(plot.res_population),
                self._tc(plot.res_domestic_lpd),
                self._tc(plot.res_flushing_lpd),
                self._tc(plot.res_total_lpd),
            ]
        )
        t_res = Table(res_rows, colWidths=[30, 80, 55, 65, 60, 90, 90, 90])
        t_res.setStyle(self._grid_style())
        story.append(t_res)
        story.append(Spacer(1, 8))

        blocks: Dict[str, list] = {}
        for cu in plot.commercial_units:
            blocks.setdefault(cu.block, []).append(cu)

        comm_section = 2 if plot_name == "Plot-A" else 6
        for block_name, units in sorted(blocks.items()):
            story.append(
                self._p(
                    f"<b>SECTION-{comm_section} COMMERCIAL - {block_name}</b>",
                    "SecH",
                    fontSize=7,
                    fontName="Helvetica-Bold",
                )
            )
            comm_header = [
                self._th("SR.NO"),
                self._th("BLDG/WING"),
                self._th("AREA (SQ.M)"),
                self._th("POPULATION PER/SQ.M"),
                self._th("POPULATION"),
                self._th("DOMESTIC WATER DEMAND (LIT/DAY)"),
                self._th("FLUSHING WATER DEMAND (LIT/DAY)"),
                self._th("TOTAL WATER DEMAND (LIT/DAY)"),
            ]
            comm_rows = [comm_header]
            for idx, u in enumerate(units, 1):
                label = u.floor_label or u.comm_type
                comm_rows.append(
                    [
                        self._tc(idx),
                        self._tc(label),
                        self._tc(f"{u.area_sqm:.0f}"),
                        self._tc(f"{u.density:.1f}"),
                        self._tc(u.population),
                        self._tc(u.domestic_lpd),
                        self._tc(u.flushing_lpd),
                        self._tc(u.total_lpd),
                    ]
                )
            comm_rows.append(
                [
                    self._tc(""),
                    self._tc("SUB-TOTAL", 0),
                    self._tc(""),
                    self._tc(""),
                    self._tc(sum(u.population for u in units)),
                    self._tc(sum(u.domestic_lpd for u in units)),
                    self._tc(sum(u.flushing_lpd for u in units)),
                    self._tc(sum(u.total_lpd for u in units)),
                ]
            )
            t_com = Table(comm_rows, colWidths=[30, 90, 55, 65, 55, 85, 85, 85])
            t_com.setStyle(self._grid_style())
            story.append(t_com)
            story.append(Spacer(1, 8))
            comm_section += 1

        other_section = 3 if plot_name == "Plot-A" else 5
        story.append(
            self._p(
                f"<b>SECTION-{other_section} WATER REQUIRMENTS FOR OTHER MEASURES</b>",
                "SecH",
                fontSize=7,
                fontName="Helvetica-Bold",
            )
        )
        other_rows = [
            [self._th("SR.NO"), self._th("DESCRIPTION"), self._th("AREA (SQ.M) / VALUE"), self._th("WATER REQUIREMENT"), self._th("UNITS")],
            [
                self._tc(1),
                self._tc(f"WATER REQUIRMENT FOR LANDSCAPE-{plot_name} (AS PER NBC-2026)", 0),
                self._tc(f"{self.results.plots[plot_name].landscape_dry_lpd / 6:.0f}" if plot.landscape_dry_lpd else "0"),
                self._tc(plot.landscape_dry_lpd),
                self._tc("LITER/DAY"),
            ],
            [
                self._tc(3),
                self._tc("KITCHEN WATER REQUIREMENT", 0),
                self._tc("0"),
                self._tc(plot.kitchen_water_lpd),
                self._tc("LITER/DAY"),
            ],
            [
                self._tc(4),
                self._tc("MAKE UP WATER FOR SWIMMING POOL", 0),
                self._tc("0"),
                self._tc(plot.swimming_pool_lpd),
                self._tc("LITER/DAY"),
            ],
            [
                self._tc(5),
                self._tc("WATER REQUIRMENT FOR HVAC", 0),
                self._tc("0"),
                self._tc(plot.hvac_lpd),
                self._tc("LITER/DAY"),
            ],
        ]
        t_other = Table(other_rows, colWidths=[30, 220, 80, 90, 70])
        t_other.setStyle(self._grid_style())
        story.append(t_other)
        story.append(Spacer(1, 8))
        story.append(
            self._p(
                f"<b>GRAND TOTAL RESIDENTIAL + COMMERCIAL: {plot.dry_total_water_lpd} LIT/DAY</b>",
                "Grand",
                fontSize=7,
                fontName="Helvetica-Bold",
            )
        )
        story.append(
            self._p(
                "<b>NOTE :- WATER DEMAND CALCULATION AS PER THE NBC-2026</b>",
                "Note",
                fontSize=6,
                fontName="Helvetica-Oblique",
            )
        )
        return story

    def _build_ugt_oht(self, plot_name: str) -> List[Any]:
        plot = self.results.plots[plot_name]
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar(f"UGT & OHT DETAILS - {plot_name}", BRAND_UGT_TEAL))
        story.append(Spacer(1, 5))

        ugt_groups = self._group_ugt_sections(plot)
        for gidx, (group_name, sections) in enumerate(ugt_groups.items(), 1):
            story.append(self._p(f"<b>{group_name}</b>", "UGTH", fontSize=7, fontName="Helvetica-Bold"))
            ugt_header = [
                self._th("SR.NO."),
                self._th("DISCRIPTION"),
                self._th("WATER REQUIREMENT (LIT/DAY)"),
                self._th("STORAGE OF WATER (DAYS)"),
                self._th("TOTAL WATER STORAGE (LIT/DAY)"),
                self._th("TOTAL WATER STORAGE (KLD)"),
            ]
            ugt_rows = [ugt_header]
            total_kld = 0.0
            for idx, sec in enumerate(sections, 1):
                ugt_rows.append(
                    [
                        self._tc(idx),
                        self._tc(sec.description, 0),
                        self._tc(sec.water_requirement_lpd),
                        self._tc(sec.storage_days),
                        self._tc(sec.total_storage_liters),
                        self._tc(f"{sec.total_storage_kld:.2f}"),
                    ]
                )
                total_kld += sec.total_storage_kld
            t_ugt = Table(ugt_rows, colWidths=[35, 160, 100, 80, 100, 80])
            t_ugt.setStyle(self._grid_style())
            story.append(t_ugt)
            story.append(
                self._p(
                    f"<b>TOTAL STORAGE CAPACITY: {total_kld:.2f} KLD</b>",
                    "Tot",
                    fontSize=7,
                    fontName="Helvetica-Bold",
                )
            )
            story.append(Spacer(1, 6))

        story.append(self._p("<b>*OHT DETAILS</b>", "OHT", fontSize=7, fontName="Helvetica-Bold"))
        oht_header = [
            self._th("SR.NO"),
            self._th("BLDG/WING"),
            self._th("DOMESTIC (KLD)"),
            self._th("FLUSHING (KLD)"),
            self._th("FIRE BREAK TANK (KLD)"),
            self._th("FIRE OHT TANK (KLD)"),
        ]
        oht_rows = [oht_header]
        total_dom = total_flu = total_fb = total_fo = 0.0
        for idx, row in enumerate(plot.oht_rows, 1):
            oht_rows.append(
                [
                    self._tc(idx),
                    self._tc(row["wing"]),
                    self._tc(f"{row['domestic_kld']:.2f}"),
                    self._tc(f"{row['flushing_kld']:.2f}"),
                    self._tc(f"{row['fire_break_kld']:.2f}"),
                    self._tc(f"{row['fire_oht_kld']:.2f}"),
                ]
            )
            total_dom += row["domestic_kld"]
            total_flu += row["flushing_kld"]
            total_fb += row["fire_break_kld"]
            total_fo += row["fire_oht_kld"]
        oht_rows.append(
            [
                self._tc(""),
                self._tc("TOTAL OHT CAPACITY", 0),
                self._tc(f"{total_dom:.2f}"),
                self._tc(f"{total_flu:.2f}"),
                self._tc(f"{total_fb:.2f}"),
                self._tc(f"{total_fo:.2f}"),
            ]
        )
        t_oht = Table(oht_rows, colWidths=[35, 120, 90, 90, 100, 100])
        t_oht.setStyle(self._grid_style())
        story.append(t_oht)
        story.append(Spacer(1, 6))
        story.append(
            self._p(
                "<b>NOTE:- FIRE WATER TANK CAPACITY TAKEN AS PER NBC-2026, "
                "SO KINDLY CONFIRM WITH FIRE LIOSANING VENDOR & NOC</b>",
                "Note",
                fontSize=6,
                fontName="Helvetica-Oblique",
            )
        )
        return story

    def _group_ugt_sections(self, plot: PlotResults) -> Dict[str, list]:
        groups: Dict[str, list] = {"FOR RESIDENTIAL": []}
        current_group = "FOR RESIDENTIAL"
        for sec in plot.ugt_sections:
            if "COMM" in sec.description.upper():
                if "COMM-A" in sec.description.upper():
                    current_group = "FOR COMMERCIAL-A"
                elif "COMM-B" in sec.description.upper() or "A&B" in sec.description.upper():
                    current_group = "FOR COMMERCIAL-B"
                else:
                    current_group = "FOR COMMERCIAL"
                groups.setdefault(current_group, [])
            groups.setdefault(current_group, []).append(sec)
        return groups

    def _build_stp(self, plot_name: str) -> List[Any]:
        plot = self.results.plots[plot_name]
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar(f"STP DETAILS - {plot_name}", BRAND_STP_PURPLE))
        story.append(Spacer(1, 5))

        for sidx, stp in enumerate(plot.stp_sections, 1):
            scope_label = f"STP FOR {stp.scope}"
            story.append(self._p(f"<b>{scope_label}</b>", "STPH", fontSize=7, fontName="Helvetica-Bold"))
            stp_header = [self._th("SR.NO."), self._th("DISCRIPTION"), self._th("CAPACITY"), self._th("UNITS")]
            stp_rows = [stp_header]
            stp_data = [
                ("TOTAL WATER REQUIREMENT FOR RESIDENTIAL TENAMENTS", stp.total_water_lpd, "LITERS/DAY"),
                ("TOTAL SEWAGE GENERATION @90% REQUREMENT (10% INFLITRATION LOSS)", stp.sewage_lpd, "LITERS/DAY"),
                ("CAPACITY OF SEWAGE GENERATION", f"{stp.sewage_kld:.2f}", "KLD"),
                ("SAY STP CAPACITY", f"{stp.say_stp_kld:.2f}", "KLD"),
                ("TREATED WATER AFTER FILTRATION STP PROCESS", stp.treated_water_lpd, "LITERS/DAY"),
                ("REUSE WATER FOR FLUSHING", stp.reuse_flushing_lpd, "LITERS/DAY"),
                ("REUSE WATER FOR LANDSCAPE", stp.reuse_landscape_lpd, "LITERS/DAY"),
                ("REUSE WATER FOR HVAC", stp.reuse_hvac_lpd, "LITERS/DAY"),
                ("EXCESS TREATED WATER TO EXTERNAL MUNCIPAL DRAIN", stp.excess_treated_lpd, "LITERS/DAY"),
            ]
            for idx, (desc, cap, unit) in enumerate(stp_data, 1):
                stp_rows.append([self._tc(idx), self._tc(desc, 0), self._tc(cap), self._tc(unit)])
            t_stp = Table(stp_rows, colWidths=[40, 280, 100, 80])
            t_stp.setStyle(self._grid_style())
            story.append(t_stp)
            story.append(Spacer(1, 10))
        return story

    def _build_environmental_tables(self, title: str, color: str, sections) -> List[Any]:
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar(title, color))
        story.append(Spacer(1, 5))
        for section in sections:
            story.append(self._p(f"<b>{section.title}</b>", "EnvSec", fontSize=7, fontName="Helvetica-Bold"))
            table_rows = [
                [self._th("DESCRIPTION"), self._th("VALUE"), self._th("UNIT")],
            ]
            for desc, value, unit in section.rows:
                table_rows.append([self._tc(desc, 0), self._tc(value, 1), self._tc(unit, 0)])
            table = Table(table_rows, colWidths=[260, 120, 100])
            table.setStyle(self._grid_style())
            story.append(table)
            story.append(Spacer(1, 8))
        return story


def export_pdf(
    file_path: str,
    project: ProjectData,
    results: CalculationResults,
    logo_path: Optional[str] = None,
) -> None:
    exporter = PDFExporter(project, results, logo_path)
    exporter.export(file_path)

# ==================== services/excel_exporter.py ====================






HEADER_FILL = PatternFill("solid", fgColor=BRAND_DARK_GRAY.replace("#", ""))
NAVY_FILL = PatternFill("solid", fgColor=BRAND_NAVY.replace("#", ""))
ORANGE_FILL = PatternFill("solid", fgColor=BRAND_ORANGE.replace("#", ""))
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
WHITE_BOLD = Font(color="FFFFFF", bold=True, size=10)
TITLE_FONT = Font(bold=True, size=14, color=BRAND_NAVY.replace("#", ""))
HEADER_FONT = Font(bold=True, size=11)


class ExcelExporter:
    def __init__(self, project: ProjectData, results: CalculationResults) -> None:
        self.project = project
        self.results = results
        self.wb = Workbook()

    def export(self, file_path: str) -> None:
        environmental = calculate_environmental(self.results, self.project)
        self._build_cover()
        self._build_consolidated()
        for plot in active_plots(self.project.plot_mode):
            self._build_plot_demand(plot)
            self._build_ugt_oht(plot)
            self._build_stp(plot)
        self._build_environmental_sheet("Sewage Generation", build_sewage_generation_table_sections(self.project, environmental))
        self._build_environmental_sheet("Solid Waste Generation", build_solid_waste_table_sections(self.project, environmental))
        self._build_summary()
        if "Sheet" in self.wb.sheetnames:
            del self.wb["Sheet"]
        self.wb.save(file_path)

    def _style_header_row(self, ws, row: int, cols: int) -> None:
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = HEADER_FILL
            cell.font = WHITE_BOLD
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = THIN_BORDER

    def _style_data_area(self, ws, start_row: int, end_row: int, cols: int) -> None:
        for r in range(start_row, end_row + 1):
            for c in range(1, cols + 1):
                cell = ws.cell(row=r, column=c)
                cell.border = THIN_BORDER
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def _auto_width(self, ws) -> None:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 3, 45)

    def _build_cover(self) -> None:
        ws = self.wb.active
        ws.title = "Cover"
        ws["A1"] = COMPANY_NAME
        ws["A1"].font = TITLE_FONT
        ws.merge_cells("A1:F1")
        ws["A3"] = "TITLE"
        ws["B3"] = "WATER DEMAND"
        ws["A4"] = "PROJECT NAME"
        ws["B4"] = self.project.project_name
        ws["A5"] = "CLIENT NAME"
        ws["B5"] = self.project.client_name
        ws["A6"] = "PROJECT LOCATION"
        ws["B6"] = self.project.project_location
        ws["A7"] = "PROJECT NO."
        ws["B7"] = self.project.project_no
        ws["A8"] = "ENGINEER"
        ws["B8"] = self.project.engineer_name
        ws["A9"] = "DATE"
        ws["B9"] = self.project.date
        rev = self.project.revision
        headers = ["DATE", "REV. NO.", "DESCRIPTION", "PRPD. BY", "CHKD. BY", "APPRD. BY"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=11, column=i, value=h)
        self._style_header_row(ws, 11, 6)
        ws.cell(row=12, column=1, value=rev.date or self.project.date)
        ws.cell(row=12, column=2, value=rev.revision_no)
        ws.cell(row=12, column=3, value=rev.description)
        ws.cell(row=12, column=4, value=rev.prepared_by)
        ws.cell(row=12, column=5, value=rev.checked_by)
        ws.cell(row=12, column=6, value=rev.approved_by)
        self._style_data_area(ws, 12, 12, 6)
        self._auto_width(ws)

    def _build_consolidated(self) -> None:
        ws = self.wb.create_sheet("Consolidated")
        ws["A1"] = "CONSOLIDATED STATEMENT"
        ws["A1"].font = HEADER_FONT
        ws.merge_cells("A1:J1")
        ws["A1"].fill = ORANGE_FILL
        headers = [
            "SR.NO", "DESCRIPTION", "PLOT-A RES", "PLOT-A COMM", "PLOT-A SUB",
            "PLOT-B RES", "PLOT-B COMM", "PLOT-B SUB", "TOTAL", "UNITS",
        ]
        for i, h in enumerate(headers, 1):
            ws.cell(row=3, column=i, value=h)
        self._style_header_row(ws, 3, 10)
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        tot = self.results.total
        rows = [
            ("Number Of Building", pa.num_buildings_res, pa.num_buildings_com, pa.num_buildings_res + pa.num_buildings_com,
             pb.num_buildings_res, pb.num_buildings_com, pb.num_buildings_res + pb.num_buildings_com,
             pa.num_buildings_res + pa.num_buildings_com + pb.num_buildings_res + pb.num_buildings_com, "NO.S"),
            ("Total Number Of Flats", pa.total_flats, 0, pa.total_flats, pb.total_flats, 0, pb.total_flats, tot.get("Total Flats", 0), "NO.S"),
            ("Total Population", pa.res_population, pa.com_population, pa.total_population,
             pb.res_population, pb.com_population, pb.total_population, tot.get("Total Population", 0), "NO.S"),
            ("Total Water Demand (Dry)", pa.res_total_lpd + pa.com_total_lpd, 0, pa.dry_total_water_lpd,
             pb.res_total_lpd + pb.com_total_lpd, 0, pb.dry_total_water_lpd, tot.get("Total Water (LPD)", 0), "LPD"),
            ("STP Capacity", pa.stp_capacity_kld, 0, pa.stp_capacity_kld,
             pb.stp_capacity_kld, 0, pb.stp_capacity_kld, tot.get("Total STP Capacity (KLD)", 0), "KLD"),
        ]
        for ridx, row in enumerate(rows, 4):
            ws.cell(row=ridx, column=1, value=ridx - 3)
            for cidx, val in enumerate(row, 2):
                ws.cell(row=ridx, column=cidx, value=val)
        self._style_data_area(ws, 4, 4 + len(rows) - 1, 10)
        self._auto_width(ws)

    def _build_plot_demand(self, plot_name: str) -> None:
        plot = self.results.plots[plot_name]
        ws = self.wb.create_sheet(f"{plot_name} Demand")
        ws["A1"] = f"WATER DEMAND - {plot_name}"
        ws["A1"].font = HEADER_FONT
        ws.merge_cells("A1:H1")

        ws["A3"] = "RESIDENTIAL"
        ws["A3"].font = Font(bold=True)
        res_headers = ["SR.NO", "WING", "FLATS", "POP/FLAT", "POPULATION", "DOMESTIC", "FLUSHING", "KITCHEN", "TOTAL"]
        for i, h in enumerate(res_headers, 1):
            ws.cell(row=4, column=i, value=h)
        self._style_header_row(ws, 4, 9)
        row = 5
        for idx, w in enumerate(plot.residential_wings, 1):
            ws.cell(row=row, column=1, value=idx)
            ws.cell(row=row, column=2, value=w.wing)
            ws.cell(row=row, column=3, value=w.flats)
            ws.cell(row=row, column=4, value=w.pop_per_flat)
            ws.cell(row=row, column=5, value=w.population)
            ws.cell(row=row, column=6, value=w.domestic_lpd)
            ws.cell(row=row, column=7, value=w.flushing_lpd)
            ws.cell(row=row, column=8, value=w.kitchen_water_lpd)
            ws.cell(row=row, column=9, value=w.total_lpd)
            row += 1
        ws.cell(row=row, column=2, value="SUB-TOTAL")
        ws.cell(row=row, column=5, value=plot.res_population)
        ws.cell(row=row, column=6, value=plot.res_domestic_lpd)
        ws.cell(row=row, column=7, value=plot.res_flushing_lpd)
        ws.cell(row=row, column=8, value=plot.kitchen_water_lpd)
        ws.cell(row=row, column=9, value=plot.res_total_lpd)
        self._style_data_area(ws, 5, row, 9)
        row += 2

        ws.cell(row=row, column=1, value="COMMERCIAL")
        ws.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        com_headers = ["SR.NO", "BLOCK", "TYPE/FLOOR", "AREA", "DENSITY", "POPULATION", "DOMESTIC", "FLUSHING", "TOTAL"]
        for i, h in enumerate(com_headers, 1):
            ws.cell(row=row, column=i, value=h)
        self._style_header_row(ws, row, 9)
        row += 1
        start_com = row
        for idx, u in enumerate(plot.commercial_units, 1):
            ws.cell(row=row, column=1, value=idx)
            ws.cell(row=row, column=2, value=u.block)
            ws.cell(row=row, column=3, value=u.floor_label or u.comm_type)
            ws.cell(row=row, column=4, value=u.area_sqm)
            ws.cell(row=row, column=5, value=u.density)
            ws.cell(row=row, column=6, value=u.population)
            ws.cell(row=row, column=7, value=u.domestic_lpd)
            ws.cell(row=row, column=8, value=u.flushing_lpd)
            ws.cell(row=row, column=9, value=u.total_lpd)
            row += 1
        self._style_data_area(ws, start_com, row - 1, 9)
        row += 1
        ws.cell(row=row, column=1, value="OTHER MEASURES")
        ws.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        ws.cell(row=row, column=1, value="Landscape (NBC-2026)")
        ws.cell(row=row, column=2, value=plot.landscape_dry_lpd)
        ws.cell(row=row + 1, column=1, value="Swimming Pool")
        ws.cell(row=row + 1, column=2, value=plot.swimming_pool_lpd if plot.swimming_pool_lpd else "NA")
        next_row = row + 2
        if hvac_applicable(self.project.project_type):
            ws.cell(row=next_row, column=1, value="HVAC")
            ws.cell(row=next_row, column=2, value=plot.hvac_lpd)
            next_row += 1
        ws.cell(row=next_row, column=1, value="Kitchen Water")
        ws.cell(row=next_row, column=2, value=plot.kitchen_water_lpd)
        ws.cell(row=next_row + 1, column=1, value="GRAND TOTAL")
        ws.cell(row=next_row + 1, column=1).font = Font(bold=True)
        ws.cell(row=next_row + 1, column=2, value=plot.dry_total_water_lpd)
        self._auto_width(ws)

    def _build_ugt_oht(self, plot_name: str) -> None:
        plot = self.results.plots[plot_name]
        ws = self.wb.create_sheet(f"{plot_name} UGT-OHT")
        ws["A1"] = f"UGT & OHT DETAILS - {plot_name}"
        ws["A1"].font = HEADER_FONT
        ws.merge_cells("A1:F1")
        headers = ["SR.NO", "DESCRIPTION", "WATER REQ (LPD)", "STORAGE DAYS", "TOTAL STORAGE (L)", "TOTAL (KLD)"]
        for i, h in enumerate(headers, 1):
            ws.cell(row=3, column=i, value=h)
        self._style_header_row(ws, 3, 6)
        row = 4
        for idx, sec in enumerate(plot.ugt_sections, 1):
            ws.cell(row=row, column=1, value=idx)
            ws.cell(row=row, column=2, value=sec.description)
            ws.cell(row=row, column=3, value=sec.water_requirement_lpd)
            ws.cell(row=row, column=4, value=sec.storage_days)
            ws.cell(row=row, column=5, value=sec.total_storage_liters)
            ws.cell(row=row, column=6, value=sec.total_storage_kld)
            row += 1
        self._style_data_area(ws, 4, row - 1, 6)
        row += 2
        ws.cell(row=row, column=1, value="OHT DETAILS")
        ws.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        oht_headers = ["SR.NO", "WING", "DOMESTIC KLD", "FLUSHING KLD", "FIRE BREAK KLD", "FIRE OHT KLD"]
        for i, h in enumerate(oht_headers, 1):
            ws.cell(row=row, column=i, value=h)
        self._style_header_row(ws, row, 6)
        row += 1
        start = row
        for idx, oht in enumerate(plot.oht_rows, 1):
            ws.cell(row=row, column=1, value=idx)
            ws.cell(row=row, column=2, value=oht["wing"])
            ws.cell(row=row, column=3, value=oht["domestic_kld"])
            ws.cell(row=row, column=4, value=oht["flushing_kld"])
            ws.cell(row=row, column=5, value=oht["fire_break_kld"])
            ws.cell(row=row, column=6, value=oht["fire_oht_kld"])
            row += 1
        self._style_data_area(ws, start, row - 1, 6)
        self._auto_width(ws)

    def _build_stp(self, plot_name: str) -> None:
        plot = self.results.plots[plot_name]
        ws = self.wb.create_sheet(f"{plot_name} STP")
        ws["A1"] = f"STP DETAILS - {plot_name}"
        ws["A1"].font = HEADER_FONT
        ws.merge_cells("A1:D1")
        row = 3
        for stp in plot.stp_sections:
            ws.cell(row=row, column=1, value=f"STP FOR {stp.scope}")
            ws.cell(row=row, column=1).font = Font(bold=True)
            row += 1
            headers = ["SR.NO", "DESCRIPTION", "CAPACITY", "UNITS"]
            for i, h in enumerate(headers, 1):
                ws.cell(row=row, column=i, value=h)
            self._style_header_row(ws, row, 4)
            row += 1
            data = [
                ("Total Water Requirement", stp.total_water_lpd, "LITERS/DAY"),
                ("Sewage Generation @90%", stp.sewage_lpd, "LITERS/DAY"),
                ("Capacity of Sewage Generation", stp.sewage_kld, "KLD"),
                ("Say STP Capacity", stp.say_stp_kld, "KLD"),
                ("Treated Water After Filtration", stp.treated_water_lpd, "LITERS/DAY"),
                ("Reuse Water for Flushing", stp.reuse_flushing_lpd, "LITERS/DAY"),
                ("Reuse Water for Landscape", stp.reuse_landscape_lpd, "LITERS/DAY"),
                ("Reuse Water for HVAC", stp.reuse_hvac_lpd, "LITERS/DAY"),
                ("Excess Treated Water", stp.excess_treated_lpd, "LITERS/DAY"),
            ]
            start = row
            for idx, (desc, cap, unit) in enumerate(data, 1):
                ws.cell(row=row, column=1, value=idx)
                ws.cell(row=row, column=2, value=desc)
                ws.cell(row=row, column=3, value=cap)
                ws.cell(row=row, column=4, value=unit)
                row += 1
            self._style_data_area(ws, start, row - 1, 4)
            row += 2
        self._auto_width(ws)

    def _build_environmental_sheet(self, sheet_title: str, sections: list[TableSection]) -> None:
        ws = self.wb.create_sheet(sheet_title)
        ws["A1"] = sheet_title.upper()
        ws["A1"].font = TITLE_FONT
        ws.merge_cells("A1:C1")
        row = 3
        for section in sections:
            ws.cell(row=row, column=1, value=section.title)
            ws.cell(row=row, column=1).font = Font(bold=True)
            row += 1
            headers = ["Description", "Value", "Unit"]
            for col, header in enumerate(headers, 1):
                ws.cell(row=row, column=col, value=header)
            self._style_header_row(ws, row, 3)
            row += 1
            start = row
            for desc, value, unit in section.rows:
                ws.cell(row=row, column=1, value=desc)
                ws.cell(row=row, column=2, value=value)
                ws.cell(row=row, column=3, value=unit)
                row += 1
            self._style_data_area(ws, start, row - 1, 3)
            row += 2
        self._auto_width(ws)

    def _build_summary(self) -> None:
        ws = self.wb.create_sheet("Summary")
        ws["A1"] = "PROJECT SUMMARY"
        ws["A1"].font = TITLE_FONT
        tot = self.results.total
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        summary = [
            ("Project Name", self.project.project_name),
            ("Client Name", self.project.client_name),
            ("Project Location", self.project.project_location),
            ("Engineer", self.project.engineer_name),
            ("Date", self.project.date),
            ("", ""),
            ("Plot-A STP Capacity (KLD)", pa.stp_capacity_kld),
            ("Plot-B STP Capacity (KLD)", pb.stp_capacity_kld),
            ("Total Water Demand (LPD)", tot.get("Total Water (LPD)", 0)),
            ("Total STP Capacity (KLD)", tot.get("Total STP Capacity (KLD)", 0)),
            ("Total Population", tot.get("Total Population", 0)),
            ("Total Flats", tot.get("Total Flats", 0)),
        ]
        for idx, (k, v) in enumerate(summary, 3):
            ws.cell(row=idx, column=1, value=k)
            ws.cell(row=idx, column=2, value=v)
            if k:
                ws.cell(row=idx, column=1).font = Font(bold=True)
        self._auto_width(ws)


TEMPLATE_PATH = os.path.normpath(
    os.path.join(APP_DIR, "..", "templates", "WaterDemand_Template.xlsx")
)


class TemplateExcelExporter:
    """Populate the master Excel template — formatting preserved, data cells only."""

    def __init__(self, project: ProjectData, results: CalculationResults) -> None:
        self.project = project
        self.results = results

    def export(self, file_path: str) -> None:
        shutil.copy2(TEMPLATE_PATH, file_path)
        wb = load_workbook(file_path)
        environmental = calculate_environmental(self.results, self.project)
        self._populate_cover(wb)
        self._populate_consolidated(wb)
        for plot in ("Plot-A", "Plot-B"):
            if plot in active_plots(self.project.plot_mode):
                self._populate_plot_demand(wb, plot)
                self._populate_ugt_oht(wb, plot)
                self._populate_stp(wb, plot)
            else:
                self._clear_plot_sheets(wb, plot)
        self._populate_summary(wb)
        self._append_environmental_sheets(
            wb,
            build_sewage_generation_table_sections(self.project, environmental),
            "Sewage Generation",
        )
        self._append_environmental_sheets(
            wb,
            build_solid_waste_table_sections(self.project, environmental),
            "Solid Waste Generation",
        )
        wb.save(file_path)

    @staticmethod
    def _set(ws, cell: str, value: Any) -> None:
        target = ws[cell]
        if type(target).__name__ == "MergedCell":
            for merged in ws.merged_cells.ranges:
                if target.coordinate in merged:
                    ws.cell(row=merged.min_row, column=merged.min_col).value = value
                    return
        target.value = value

    @staticmethod
    def _find_row(
        ws,
        needle: str,
        column: int = 1,
        start: int = 1,
        exact: bool = False,
    ) -> Optional[int]:
        needle_l = needle.lower().strip()
        for row in range(start, ws.max_row + 1):
            val = ws.cell(row=row, column=column).value
            if val is None:
                continue
            text = str(val).lower().strip()
            if exact:
                if text == needle_l:
                    return row
            elif needle_l in text:
                return row
        return None

    @staticmethod
    def _clear_range(ws, start_row: int, end_row: int, start_col: int, end_col: int) -> None:
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = ws.cell(row=row, column=col)
                if cell.value is not None and not str(cell.value).startswith("="):
                    cell.value = None

    def _populate_cover(self, wb) -> None:
        if "Cover" not in wb.sheetnames:
            return
        ws = wb["Cover"]
        rev = self.project.revision
        fields = {
            "B4": self.project.project_name,
            "B5": self.project.client_name,
            "B6": self.project.project_location,
            "B7": self.project.project_no,
            "B8": self.project.engineer_name,
            "B9": self.project.date,
            "A12": rev.date or self.project.date,
            "B12": rev.revision_no,
            "C12": rev.description,
            "D12": rev.prepared_by,
            "E12": rev.checked_by,
            "F12": rev.approved_by,
        }
        for cell, val in fields.items():
            self._set(ws, cell, val)

    def _populate_consolidated(self, wb) -> None:
        if "Consolidated" not in wb.sheetnames:
            return
        ws = wb["Consolidated"]
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        tot = self.results.total
        single = self.project.plot_mode == PLOT_MODE_SINGLE
        rows = [
            (
                4,
                pa.num_buildings_res,
                pa.num_buildings_com,
                pa.num_buildings_res + pa.num_buildings_com,
                0 if single else pb.num_buildings_res,
                0 if single else pb.num_buildings_com,
                0 if single else pb.num_buildings_res + pb.num_buildings_com,
                pa.num_buildings_res + pa.num_buildings_com
                + (0 if single else pb.num_buildings_res + pb.num_buildings_com),
            ),
            (
                5,
                pa.total_flats,
                0,
                pa.total_flats,
                0 if single else pb.total_flats,
                0,
                0 if single else pb.total_flats,
                tot.get("Total Flats", pa.total_flats),
            ),
            (
                6,
                pa.res_population,
                pa.com_population,
                pa.total_population,
                0 if single else pb.res_population,
                0 if single else pb.com_population,
                0 if single else pb.total_population,
                tot.get("Total Population", pa.total_population),
            ),
            (
                7,
                pa.res_total_lpd + pa.com_total_lpd,
                0,
                pa.dry_total_water_lpd,
                0 if single else pb.res_total_lpd + pb.com_total_lpd,
                0,
                0 if single else pb.dry_total_water_lpd,
                tot.get("Total Water (LPD)", pa.dry_total_water_lpd),
            ),
            (
                8,
                pa.stp_capacity_kld,
                0,
                pa.stp_capacity_kld,
                0 if single else pb.stp_capacity_kld,
                0,
                0 if single else pb.stp_capacity_kld,
                tot.get("Total STP Capacity (KLD)", pa.stp_capacity_kld),
            ),
        ]
        for row, c, d, e, f, g, h, i in rows:
            for col, val in zip("CDEFGHI", (c, d, e, f, g, h, i)):
                self._set(ws, f"{col}{row}", val)

    @staticmethod
    def _copy_row_style(ws, src_row: int, dest_row: int, max_col: int = 9) -> None:
        for col in range(1, max_col + 1):
            src = ws.cell(row=src_row, column=col)
            dst = ws.cell(row=dest_row, column=col)
            dst.value = None
            if src.has_style:
                dst._style = copy(src._style)
            dst.number_format = src.number_format

    @staticmethod
    def _insert_rows_before(ws, before_row: int, count: int, style_row: int, max_col: int = 9) -> None:
        if count <= 0:
            return
        ws.insert_rows(before_row, count)
        TemplateExcelExporter._copy_row_style(ws, style_row, style_row, max_col)
        for offset in range(count):
            TemplateExcelExporter._copy_row_style(ws, style_row, before_row + offset, max_col)

    def _populate_plot_demand(self, wb, plot_name: str) -> None:
        sheet_name = f"{plot_name} Demand"
        if sheet_name not in wb.sheetnames:
            return
        ws = wb[sheet_name]
        plot = self.results.plots[plot_name]

        res_hdr = self._find_row(ws, "SR.NO", start=1)
        sub_row = self._find_row(ws, "SUB-TOTAL", column=2, exact=True)
        if res_hdr and sub_row:
            data_start = res_hdr + 1
            wings = plot.residential_wings
            available = max(0, sub_row - data_start)
            if len(wings) > available:
                self._insert_rows_before(ws, sub_row, len(wings) - available, data_start, 8)
                sub_row = self._find_row(ws, "SUB-TOTAL", column=2, exact=True)
            self._clear_range(ws, data_start, sub_row - 1, 1, 8)
            row = data_start
            for idx, wing in enumerate(wings, 1):
                pop_per = wing.pop_per_flat
                if wing.flats > 0 and wing.population > 0:
                    pop_per = round(wing.population / wing.flats)
                self._set(ws, f"A{row}", idx)
                self._set(ws, f"B{row}", wing.wing)
                self._set(ws, f"C{row}", wing.flats)
                self._set(ws, f"D{row}", pop_per)
                self._set(ws, f"E{row}", wing.population)
                self._set(ws, f"F{row}", wing.domestic_lpd)
                self._set(ws, f"G{row}", wing.flushing_lpd)
                self._set(ws, f"H{row}", wing.total_lpd)
                row += 1
            self._set(ws, f"E{sub_row}", plot.res_population)
            self._set(ws, f"F{sub_row}", plot.res_domestic_lpd)
            self._set(ws, f"G{sub_row}", plot.res_flushing_lpd)
            self._set(ws, f"H{sub_row}", plot.res_total_lpd)

        comm_row = self._find_row(ws, "COMMERCIAL", exact=True)
        other_row = self._find_row(ws, "OTHER MEASURES", exact=True)
        if comm_row and other_row:
            hdr = comm_row + 1
            data_start = hdr + 1
            units = plot.commercial_units
            gap_before_other = 1 if other_row - data_start > 0 else 0
            available = max(0, other_row - data_start - gap_before_other)
            if len(units) > available:
                self._insert_rows_before(ws, other_row, len(units) - available, data_start, 9)
                other_row = self._find_row(ws, "OTHER MEASURES", exact=True)
            self._clear_range(ws, data_start, other_row - 2, 1, 9)
            row = data_start
            for idx, unit in enumerate(units, 1):
                label = unit.floor_label or unit.comm_type
                self._set(ws, f"A{row}", idx)
                self._set(ws, f"B{row}", unit.block)
                self._set(ws, f"C{row}", label)
                self._set(ws, f"D{row}", unit.area_sqm)
                self._set(ws, f"E{row}", unit.density)
                self._set(ws, f"F{row}", unit.population)
                self._set(ws, f"G{row}", unit.domestic_lpd)
                self._set(ws, f"H{row}", unit.flushing_lpd)
                self._set(ws, f"I{row}", unit.total_lpd)
                row += 1

        other_row = self._find_row(ws, "OTHER MEASURES", exact=True)
        if other_row:
            for label, value in (
                ("Landscape", plot.landscape_dry_lpd),
                ("Swimming Pool", plot.swimming_pool_lpd if plot.swimming_pool_lpd else "NA"),
                ("HVAC", plot.hvac_lpd),
                ("Kitchen", plot.kitchen_water_lpd),
            ):
                row = self._find_row(ws, label, start=other_row)
                if row:
                    self._set(ws, f"B{row}", value)
            grand = self._find_row(ws, "GRAND TOTAL", start=other_row, exact=True)
            if grand:
                self._set(ws, f"B{grand}", plot.dry_total_water_lpd)

    def _populate_ugt_oht(self, wb, plot_name: str) -> None:
        sheet_name = f"{plot_name} UGT-OHT"
        if sheet_name not in wb.sheetnames:
            return
        ws = wb[sheet_name]
        plot = self.results.plots[plot_name]
        oht_hdr = self._find_row(ws, "OHT DETAILS", start=3, exact=True)
        ugt_end = (oht_hdr - 2) if oht_hdr else 20
        sections = plot.ugt_sections
        available = max(0, ugt_end - 4 + 1)
        if len(sections) > available and oht_hdr:
            self._insert_rows_before(ws, oht_hdr, len(sections) - available, 4, 6)
            oht_hdr = self._find_row(ws, "OHT DETAILS", start=3, exact=True)
            ugt_end = oht_hdr - 2
        self._clear_range(ws, 4, ugt_end, 1, 6)
        row = 4
        for idx, sec in enumerate(plot.ugt_sections, 1):
            self._set(ws, f"A{row}", idx)
            self._set(ws, f"B{row}", sec.description)
            self._set(ws, f"C{row}", sec.water_requirement_lpd)
            self._set(ws, f"D{row}", sec.storage_days)
            self._set(ws, f"E{row}", sec.total_storage_liters)
            self._set(ws, f"F{row}", sec.total_storage_kld)
            row += 1

        if oht_hdr:
            hdr = oht_hdr + 1
            oht_rows = plot.oht_rows
            available = 20
            if len(oht_rows) > available:
                self._insert_rows_before(ws, hdr + available + 1, len(oht_rows) - available, hdr + 1, 6)
            self._clear_range(ws, hdr + 1, hdr + max(len(oht_rows), 20), 1, 6)
            row = hdr + 1
            for idx, oht in enumerate(plot.oht_rows, 1):
                self._set(ws, f"A{row}", idx)
                self._set(ws, f"B{row}", oht["wing"])
                self._set(ws, f"C{row}", oht["domestic_kld"])
                self._set(ws, f"D{row}", oht["flushing_kld"])
                self._set(ws, f"E{row}", oht["fire_break_kld"])
                self._set(ws, f"F{row}", oht["fire_oht_kld"])
                row += 1

    def _populate_stp(self, wb, plot_name: str) -> None:
        sheet_name = f"{plot_name} STP"
        if sheet_name not in wb.sheetnames:
            return
        ws = wb[sheet_name]
        plot = self.results.plots[plot_name]
        stp_labels = [
            "Total Water Requirement",
            "Sewage Generation @90%",
            "Capacity of Sewage Generation",
            "Say STP Capacity",
            "Treated Water After Filtration",
            "Reuse Water for Flushing",
            "Reuse Water for Landscape",
            "Reuse Water for HVAC",
            "Excess Treated Water",
        ]
        stp_data = []
        for stp in plot.stp_sections:
            stp_data.append(
                (
                    f"STP FOR {stp.scope}",
                    [
                        (stp.total_water_lpd, "LITERS/DAY"),
                        (stp.sewage_lpd, "LITERS/DAY"),
                        (stp.sewage_kld, "KLD"),
                        (stp.say_stp_kld, "KLD"),
                        (stp.treated_water_lpd, "LITERS/DAY"),
                        (stp.reuse_flushing_lpd, "LITERS/DAY"),
                        (stp.reuse_landscape_lpd, "LITERS/DAY"),
                        (stp.reuse_hvac_lpd, "LITERS/DAY"),
                        (stp.excess_treated_lpd, "LITERS/DAY"),
                    ],
                )
            )

        row = 3
        for title, rows in stp_data:
            title_row = self._find_row(ws, title, start=row)
            if not title_row:
                ws.cell(row=row, column=1, value=title)
                title_row = row
            hdr = title_row + 1
            data_start = hdr + 1
            self._clear_range(ws, data_start, data_start + 8, 1, 4)
            for idx, (desc, (cap, unit)) in enumerate(zip(stp_labels, rows), 1):
                r = data_start + idx - 1
                self._set(ws, f"A{r}", idx)
                self._set(ws, f"B{r}", desc)
                self._set(ws, f"C{r}", cap)
                self._set(ws, f"D{r}", unit)
            row = data_start + 12

    def _clear_plot_sheets(self, wb, plot_name: str) -> None:
        for suffix in (" Demand", " UGT-OHT", " STP"):
            name = f"{plot_name}{suffix}"
            if name not in wb.sheetnames:
                continue
            ws = wb[name]
            self._clear_range(ws, 5, ws.max_row, 1, 12)

    def _populate_summary(self, wb) -> None:
        if "Summary" not in wb.sheetnames:
            return
        ws = wb["Summary"]
        tot = self.results.total
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        single = self.project.plot_mode == PLOT_MODE_SINGLE
        fields = {
            "B3": self.project.project_name,
            "B4": self.project.client_name,
            "B5": self.project.project_location,
            "B6": self.project.engineer_name,
            "B7": self.project.date,
            "B9": pa.stp_capacity_kld,
            "B10": 0 if single else pb.stp_capacity_kld,
            "B11": tot.get("Total Water (LPD)", pa.dry_total_water_lpd),
            "B12": tot.get("Total STP Capacity (KLD)", pa.stp_capacity_kld),
            "B13": tot.get("Total Population", pa.total_population),
            "B14": tot.get("Total Flats", pa.total_flats),
        }
        for cell, val in fields.items():
            self._set(ws, cell, val)

    def _append_environmental_sheets(self, wb, sections: list[TableSection], sheet_title: str) -> None:
        if sheet_title in wb.sheetnames:
            ws = wb[sheet_title]
            self._clear_range(ws, 1, ws.max_row, 1, 6)
        else:
            ws = wb.create_sheet(sheet_title)
        ws["A1"] = sheet_title.upper()
        row = 3
        for section in sections:
            ws.cell(row=row, column=1, value=section.title)
            row += 1
            ws.cell(row=row, column=1, value="Description")
            ws.cell(row=row, column=2, value="Value")
            ws.cell(row=row, column=3, value="Unit")
            row += 1
            for desc, value, unit in section.rows:
                ws.cell(row=row, column=1, value=desc)
                ws.cell(row=row, column=2, value=value)
                ws.cell(row=row, column=3, value=unit)
                row += 1
            row += 1


def export_excel(file_path: str, project: ProjectData, results: CalculationResults) -> None:
    if os.path.isfile(TEMPLATE_PATH):
        TemplateExcelExporter(project, results).export(file_path)
    else:
        ExcelExporter(project, results).export(file_path)

# ==================== ui/components/validation.py ====================



class ValidationError(Exception):
    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def validate_required(value: str, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{field_name} is required.", field_name)
    return cleaned


def validate_positive_int(value: str, field_name: str, allow_zero: bool = False) -> int:
    cleaned = (value or "").strip()
    if not cleaned:
        if allow_zero:
            return 0
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    try:
        num = int(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a whole number.", field_name) from exc
    if num < 0 or (not allow_zero and num == 0):
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    return num


def validate_positive_float(value: str, field_name: str, allow_zero: bool = True) -> float:
    cleaned = (value or "").strip()
    if not cleaned:
        return 0.0 if allow_zero else (_ for _ in ()).throw(
            ValidationError(f"{field_name} must be a number.", field_name)
        )
    try:
        num = float(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid number.", field_name) from exc
    if num < 0 or (not allow_zero and num == 0):
        raise ValidationError(f"{field_name} must be a positive number.", field_name)
    return num


def validate_date(value: str, field_name: str = "Date") -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValidationError(f"{field_name} is required.", field_name)
    if not re.match(r"^\d{2}-\d{2}-\d{4}$", cleaned):
        raise ValidationError(f"{field_name} must be in DD-MM-YYYY format.", field_name)
    return cleaned


def safe_execute(action: Callable, on_error: Callable[[str], None]) -> bool:
    try:
        action()
        return True
    except ValidationError as exc:
        on_error(exc.message)
        return False
    except Exception as exc:
        on_error(str(exc))
        return False

# ==================== ui/gui_safe.py ====================
"""Safe GUI callback wrappers — user-friendly errors and application logging."""




F = TypeVar("F", bound=Callable[..., Any])

_USER_MESSAGE = "Something went wrong. Please try again."


def safe_command(callback: F, parent: Optional[Any] = None, title: str = "Error") -> F:
    """Wrap a GUI callback so unexpected exceptions are logged and shown safely."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return callback(*args, **kwargs)
        except Exception as exc:
            log_exception(
                str(exc),
                exc=exc,
                function=getattr(callback, "__name__", "safe_command"),
            )
            win = parent
            if win is not None and hasattr(win, "winfo_toplevel"):
                win = win.winfo_toplevel()
            messagebox.showerror(title, _USER_MESSAGE, parent=win)

    wrapper.__name__ = getattr(callback, "__name__", "safe_command")
    return wrapper  # type: ignore[return-value]

# ==================== ui/theme.py ====================
"""Centralized UI design tokens for American Edge Engineers."""



# Re-export brand colors (defined in nbc_2026 — single source of truth)
COLOR_PRIMARY = BRAND_NAVY
COLOR_ACCENT = BRAND_ORANGE
COLOR_SUCCESS = "#20A968"
COLOR_WARNING = "#F4B400"
COLOR_DANGER = "#C0392B"
COLOR_BACKGROUND = "#F4F6F8"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#DCE3EA"
COLOR_TEXT_PRIMARY = "#1F2937"
COLOR_TEXT_SECONDARY = "#687684"
COLOR_MUTED = "#7A8794"
COLOR_TABLE_HEADER = "#E8ECF0"
COLOR_TABLE_ROW_ALT = "#F8FAFB"
COLOR_TABLE_ROW_SELECTED = "#D6EAF8"

# Typography
FONT_FAMILY = "Arial"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 11)
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 10)
FONT_CAPTION = (FONT_FAMILY, 9)
FONT_STAT_VALUE = (FONT_FAMILY, 18, "bold")
FONT_STAT_LABEL = (FONT_FAMILY, 8, "bold")
FONT_HEADER_COMPANY = (FONT_FAMILY, 13, "bold")
FONT_HEADER_TAGLINE = (FONT_FAMILY, 10)

# Spacing & shape
RADIUS_CARD = 12
RADIUS_BUTTON = 8
RADIUS_BADGE = 10
PAD_PAGE = 20
PAD_CARD = 16
PAD_SECTION = 14
ROW_HEIGHT_COMPACT = 28
BUTTON_HEIGHT = 36
ENTRY_HEIGHT = 34

# Status badge labels (text + emoji for accessibility)
STATUS_BADGES = {
    "New": "🟡 New",
    "In Progress": "🟢 In Progress",
    "Completed": "🔵 Completed",
    "Pending": "🟠 Pending",
    "Delayed": "🔴 Delayed",
    "Cancelled": "⚫ Cancelled",
}

# Project type card icons (supported types only)
PROJECT_TYPE_ICONS = {
    "Residential": "🏠",
    "Commercial": "🏢",
    "Mixed Use": "🏙",
    "Industrial": "🏭",
    "Hospital": "🏥",
    "Hotel": "🏨",
    "School": "🏫",
    "College": "🎓",
    "Shopping Mall": "🛍",
    "Mall": "🛍",
    "IT Park": "💻",
    "Warehouse": "📦",
    "Township": "🏘",
}

COMPANY_TAGLINE = "Engineering Project Management System"

# ==================== ui/scheduled_callbacks.py ====================
"""Safe scheduling helpers for Tk/CustomTkinter widget callbacks."""



F = TypeVar("F", bound=Callable[..., Any])

TraceRegistration = Tuple[Any, str, str]  # (variable, mode, trace_id)


class PageLifecycleMixin:
    """Track and cancel after() jobs and variable traces for a page."""

    def _init_page_lifecycle(self) -> None:
        self._after_jobs: List[Any] = []
        self._trace_registrations: List[TraceRegistration] = []

    def schedule_after(self, delay_ms: int, callback: Callable[[], None]) -> Any:
        job = self.after(delay_ms, callback)
        self._after_jobs.append(job)
        return job

    def schedule_after_idle(self, callback: Callable[[], None]) -> Any:
        job = self.after_idle(callback)
        self._after_jobs.append(job)
        return job

    def register_trace(self, var: Any, mode: str, callback: Callable) -> str:
        trace_id = var.trace_add(mode, callback)
        self._trace_registrations.append((var, mode, trace_id))
        return trace_id

    def cancel_page_lifecycle(self) -> None:
        for job in list(self._after_jobs):
            cancel_after(self, job)
        self._after_jobs.clear()
        for var, mode, trace_id in list(self._trace_registrations):
            try:
                var.trace_remove(mode, trace_id)
            except (tk.TclError, AttributeError, ValueError):
                pass
        self._trace_registrations.clear()


def widget_is_alive(widget: Any) -> bool:
    """Return True when a Tk widget still exists and can be accessed."""
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except (tk.TclError, AttributeError, RuntimeError, ValueError):
        return False


def cancel_after(widget: Any, job_id: Any) -> None:
    if widget is None or job_id is None:
        return
    try:
        widget.after_cancel(job_id)
    except (tk.TclError, AttributeError, RuntimeError, ValueError):
        pass


def safe_widget_callback(widget: Any, callback: Callable[[], None]) -> Callable[[], None]:
    """Wrap a no-arg callback so it never touches a destroyed widget."""

    def wrapper() -> None:
        if not widget_is_alive(widget):
            return
        try:
            callback()
        except tk.TclError:
            return

    return wrapper


def safe_entry_text(entry: Any) -> str:
    if not widget_is_alive(entry):
        return ""
    try:
        return entry.get()
    except tk.TclError:
        return ""


def safe_set_entry_text(entry: Any, value: str) -> None:
    if not widget_is_alive(entry):
        return
    text = value or ""
    try:
        current = entry.get()
    except tk.TclError:
        return
    if current == text:
        return
    try:
        entry.delete(0, "end")
        if text:
            entry.insert(0, text)
    except tk.TclError:
        return


def safe_stringvar_set(var: Any, value: str, *, widget: Any = None) -> None:
    if widget is not None and not widget_is_alive(widget):
        return
    try:
        var.set(value)
    except tk.TclError:
        return

# ==================== ui/app_state.py ====================




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
            prepare_live_calculation(self)
            self.run_calculations()
        except Exception:
            self.results = None
            self.environmental = None

    def apply_project_type(self, new_type: str) -> None:
        """Apply a project type without blocking the UI."""
        old_type = self.project.project_type
        self.project.project_type = new_type
        if not is_project_type_set(new_type):
            return
        if not is_project_type_set(old_type):
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

# ==================== ui/components/scrollable_frame.py ====================




PAGE_BG = "#F0F2F5"


class ScrollablePage(PageLifecycleMixin, ctk.CTkScrollableFrame):
    """Full-size scrollable page shell used by every wizard screen."""

    _PENDING_JOB_ATTRS = ("_auto_calc_after_id",)

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", PAGE_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)
        self._init_page_lifecycle()
        self._auto_calc_after_id: str | None = None

    def cancel_pending_callbacks(self) -> None:
        self.cancel_page_lifecycle()
        for attr in self._PENDING_JOB_ATTRS:
            cancel_after(self, getattr(self, attr, None))
            setattr(self, attr, None)

    def destroy(self) -> None:
        self.cancel_pending_callbacks()
        try:
            super().destroy()
        except Exception:
            pass

    def schedule_auto_calculate(
        self,
        state,
        delay_ms: int = 300,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Debounce rapid input changes before running the full calculation engine."""
        if not widget_is_alive(self):
            return
        cancel_after(self, self._auto_calc_after_id)

        def _run() -> None:
            self._auto_calc_after_id = None
            if not widget_is_alive(self):
                return
            state.auto_calculate()
            if callback:
                callback()

        self._auto_calc_after_id = self.after(delay_ms, safe_widget_callback(self, _run))

# ==================== ui/components/wizard.py ====================
"""Shared wizard step indicator and navigation bar."""






def wizard_step_labels(project_type: str) -> list[str]:
    """Ordered workflow step labels including type selection."""
    labels = ["Project Type"]
    for key in WIZARD_PAGE_ORDER:
        if key in visible_pages(project_type):
            labels.append(key if key != "Project" else "Project Details")
    return labels


def wizard_step_index(page_key: str, project_type: str) -> tuple[int, int]:
    """Return (current_step_1based, total_steps) for a workflow page key."""
    labels = wizard_step_labels(project_type)
    lookup = "Project Type" if page_key == "Type" else ("Project Details" if page_key == "Project" else page_key)
    try:
        idx = labels.index(lookup)
    except ValueError:
        idx = 0
    return idx + 1, len(labels)


class StepIndicator(ctk.CTkFrame):
    """Compact step badge: STEP 2 OF 8 — Project Details."""

    def __init__(self, master, *, step: int, total: int, title: str, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        badge = ctk.CTkLabel(
            self,
            text=f"STEP {step} OF {total}",
            font=FONT_CAPTION,
            text_color=COLOR_ACCENT,
            fg_color="#FFF1E8",
            corner_radius=12,
            padx=12,
            pady=5,
        )
        badge.pack(side="left")
        ctk.CTkLabel(
            self,
            text=title,
            font=FONT_SECTION,
            text_color=COLOR_PRIMARY,
        ).pack(side="left", padx=(10, 0))


class WizardNavBar(ctk.CTkFrame):
    """Standard Back / Next navigation row."""

    def __init__(
        self,
        master,
        *,
        on_back: Optional[Callable[[], None]] = None,
        on_next: Optional[Callable[[], None]] = None,
        back_text: str = "← Back",
        next_text: str = "Next →",
        show_back: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        if show_back and on_back is not None:
            ctk.CTkButton(
                self,
                text=back_text,
                command=on_back,
                fg_color="#7F8C8D",
                hover_color="#667071",
                width=140,
                height=36,
            ).pack(side="left", padx=8)
        if on_next is not None:
            ctk.CTkButton(
                self,
                text=next_text,
                command=on_next,
                fg_color=COLOR_ACCENT,
                hover_color="#D06018",
                width=220,
                height=36,
            ).pack(side="right", padx=8)


def build_page_header(parent, title: str, subtitle: str = "", step: int = 0, total: int = 0) -> ctk.CTkFrame:
    """Consistent white card header for workflow pages."""
    wrapper = ctk.CTkFrame(parent, fg_color="white", corner_radius=12, border_width=1, border_color=COLOR_BORDER)
    wrapper.pack(fill="x", padx=18, pady=(14, 10))
    wrapper.grid_columnconfigure(0, weight=1)

    left = ctk.CTkFrame(wrapper, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=20, pady=15)
    ctk.CTkLabel(left, text=title, font=("Arial", 21, "bold"), text_color=COLOR_PRIMARY, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=FONT_SUBTITLE,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    if step > 0 and total > 0:
        StepIndicator(wrapper, step=step, total=total, title=title).grid(
            row=0, column=1, padx=18, pady=15, sticky="e"
        )
    return wrapper

# ==================== ui/components/type_selector.py ====================
"""Visual project type selection cards — compact grid, no scrolling."""






class ProjectTypeSelector(ctk.CTkFrame):
    """Compact grid of selectable project type cards (fits one screen)."""

    def __init__(
        self,
        master,
        *,
        initial_label: str = PROJECT_TYPE_PLACEHOLDER,
        on_selection_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_selection_change = on_selection_change
        self._selected = ctk.StringVar(value=initial_label)
        self._cards: dict[str, ctk.CTkFrame] = {}
        self._build()

    def get_selected(self) -> str:
        return self._selected.get()

    def set_selected(self, label: str) -> None:
        self._selected.set(label)
        self._refresh_highlights()

    def _build(self) -> None:
        labels = sorted(set(PROJECT_TYPE_LABELS.keys()))
        cols = 4
        for i, label in enumerate(labels):
            row, col = divmod(i, cols)
            card = self._make_card(label)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)

    def _make_card(self, label: str) -> ctk.CTkFrame:
        icon = PROJECT_TYPE_ICONS.get(label, "📋")
        frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BORDER,
            height=52,
            cursor="hand2",
        )
        frame.grid_propagate(False)
        self._cards[label] = frame

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=6)
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        check = ctk.CTkLabel(row, text="", font=FONT_SECTION, text_color=COLOR_ACCENT, width=14)
        check.pack(side="right")
        frame._check_label = check  # type: ignore[attr-defined]
        ctk.CTkLabel(
            row,
            text=f"{icon} {label}",
            font=("Arial", 11, "bold"),
            text_color=COLOR_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        def select(_event=None, lbl=label):
            self._selected.set(lbl)
            self._refresh_highlights()
            if self.on_selection_change:
                self.on_selection_change(lbl)

        frame.bind("<Button-1>", select)
        for child in frame.winfo_children():
            child.bind("<Button-1>", select)
            for sub in child.winfo_children():
                sub.bind("<Button-1>", select)

        return frame

    def _refresh_highlights(self) -> None:
        selected = self._selected.get()
        for label, card in self._cards.items():
            is_sel = label == selected and selected != PROJECT_TYPE_PLACEHOLDER
            card.configure(
                border_color=COLOR_ACCENT if is_sel else COLOR_BORDER,
                fg_color="#FFF8F0" if is_sel else COLOR_CARD,
            )
            check = getattr(card, "_check_label", None)
            if check is not None:
                check.configure(text="✓" if is_sel else "")

# ==================== ui/components/result_table.py ====================
"""Professional Description | Value | Unit tables for engineering report screens."""





TableRow = Tuple[str, str, str]

_HEADER_BG = BRAND_NAVY
_HEADER_FG = "white"
_BORDER = "#C5CED8"
_ROW_EVEN = "#FFFFFF"
_ROW_ODD = "#F4F6F8"
_VALUE_FG = "#1A5276"


class ResultTableView(ctk.CTkFrame):
    """Renders one or more titled result tables inside a scrollable or plain host."""

    def __init__(self, master, embedded: bool = True, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._embedded = embedded
        if embedded:
            self._host = ctk.CTkFrame(self, fg_color="transparent")
        else:
            self._host = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self._host.pack(fill="both", expand=True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def set_sections(self, sections: Sequence[TableSection]) -> None:
        for child in self._host.winfo_children():
            child.destroy()
        if not sections:
            self._add_empty_message("No data available.")
            return
        for section in sections:
            self._render_section(section.title, section.rows)

    def set_rows(self, title: str, rows: Iterable[TableRow]) -> None:
        for child in self._host.winfo_children():
            child.destroy()
        self._render_section(title, tuple(rows))

    def _add_empty_message(self, text: str) -> None:
        ctk.CTkLabel(
            self._host,
            text=text,
            font=("Arial", 12),
            text_color="#666666",
            anchor="w",
        ).pack(fill="x", padx=4, pady=8)

    def _render_section(self, title: str, rows: Sequence[TableRow]) -> None:
        wrapper = ctk.CTkFrame(self._host, fg_color="transparent")
        wrapper.pack(fill="x", expand=True, padx=2, pady=(8, 4))

        ctk.CTkLabel(
            wrapper,
            text=title,
            font=("Arial", 13, "bold"),
            text_color=BRAND_NAVY,
            anchor="w",
        ).pack(fill="x", padx=2, pady=(0, 6))

        table = ctk.CTkFrame(wrapper, fg_color="white", corner_radius=6, border_width=1, border_color=_BORDER)
        table.pack(fill="x", expand=True, padx=0, pady=0)
        table.grid_columnconfigure(0, weight=13, uniform="result_cols")
        table.grid_columnconfigure(1, weight=4, uniform="result_cols")
        table.grid_columnconfigure(2, weight=3, uniform="result_cols")

        headers = ("Description", "Value", "Unit")
        for col, label in enumerate(headers):
            cell = ctk.CTkFrame(table, fg_color=_HEADER_BG, corner_radius=0)
            cell.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 1, 0), pady=(0, 1))
            ctk.CTkLabel(
                cell,
                text=label,
                font=("Arial", 11, "bold"),
                text_color=_HEADER_FG,
                anchor="w" if col == 0 else "e" if col == 1 else "w",
            ).pack(fill="x", padx=10, pady=6)

        if not rows:
            empty = ctk.CTkFrame(table, fg_color=_ROW_EVEN, corner_radius=0)
            empty.grid(row=1, column=0, columnspan=3, sticky="nsew")
            ctk.CTkLabel(empty, text="No rows", font=("Arial", 11), text_color="#888888").pack(padx=10, pady=8)
            return

        for ridx, (desc, value, unit) in enumerate(rows, start=1):
            bg = _ROW_EVEN if ridx % 2 == 1 else _ROW_ODD
            values = (desc, value, unit)
            anchors = ("w", "e", "w")
            for col, (text, anchor) in enumerate(zip(values, anchors)):
                cell = ctk.CTkFrame(table, fg_color=bg, corner_radius=0)
                cell.grid(row=ridx, column=col, sticky="nsew", padx=(0 if col == 0 else 1, 0), pady=(0, 1))
                font = ("Arial", 11, "bold") if desc.startswith("Total") else ("Arial", 11)
                fg = _VALUE_FG if col == 1 else "#222222"
                ctk.CTkLabel(
                    cell,
                    text=text,
                    font=font,
                    text_color=fg,
                    anchor=anchor,
                    wraplength=900 if col == 0 else 0,
                ).pack(fill="x", padx=10, pady=5)

# ==================== ui/components/preview_dialog.py ====================




class PreviewDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        project: ProjectData,
        results: CalculationResults,
        on_export_pdf: Optional[Callable] = None,
    ) -> None:
        super().__init__(master)
        self.title("Report Preview - 8 Pages")
        self.geometry("900x650")
        self.transient(master)
        self.grab_set()

        self.tabview = ctk.CTkTabview(self, width=880, height=580)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self._add_cover_tab(project)
        self._add_consolidated_tab(results)
        self._add_plot_tab("Plot-A", results.plots["Plot-A"])
        self._add_plot_tab("Plot-B", results.plots["Plot-B"])
        self._add_ugt_tab("Plot-A", results.plots["Plot-A"])
        self._add_ugt_tab("Plot-B", results.plots["Plot-B"])
        self._add_stp_tab("Plot-A", results.plots["Plot-A"])
        self._add_stp_tab("Plot-B", results.plots["Plot-B"])

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        if on_export_pdf:
            ctk.CTkButton(btn_frame, text="Export PDF", command=on_export_pdf, fg_color="#C0392B").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Close", command=self.destroy, fg_color="gray").pack(side="right", padx=5)

    def _text_tab(self, name: str, content: str) -> None:
        tab = self.tabview.add(name)
        textbox = ctk.CTkTextbox(tab, font=("Courier", 11))
        textbox.pack(fill="both", expand=True, padx=5, pady=5)
        textbox.insert("1.0", content)
        textbox.configure(state="disabled")

    def _add_cover_tab(self, project: ProjectData) -> None:
        rev = project.revision
        content = f"""
AMERICAN EDGE ENGINEERS PVT. LTD.
{'=' * 50}

TITLE          : WATER DEMAND
PROJECT NAME   : {project.project_name}
CLIENT NAME    : {project.client_name}
LOCATION       : {project.project_location}
PROJECT NO.    : {project.project_no}

REVISION TABLE
Date: {rev.date or project.date}  |  Rev: {rev.revision_no}
Description: {rev.description}
Prepared: {rev.prepared_by}  |  Checked: {rev.checked_by}  |  Approved: {rev.approved_by}

Engineer: {project.engineer_name}
Date: {project.date}
"""
        self._text_tab("Page 1 - Cover", content)

    def _add_consolidated_tab(self, results: CalculationResults) -> None:
        pa = results.plots["Plot-A"]
        pb = results.plots["Plot-B"]
        tot = results.total
        content = f"""
CONSOLIDATED STATEMENT
{'=' * 60}

Buildings (Plot-A): Res={pa.num_buildings_res}, Comm={pa.num_buildings_com}
Buildings (Plot-B): Res={pb.num_buildings_res}, Comm={pb.num_buildings_com}

Flats: Plot-A={pa.total_flats}, Plot-B={pb.total_flats}, Total={tot.get('Total Flats', 0)}

Population: Plot-A={pa.total_population}, Plot-B={pb.total_population}, Total={tot.get('Total Population', 0)}

DRY SEASON
  Plot-A Total Water: {pa.dry_total_water_lpd:,} LPD ({pa.dry_total_water_lpd/1000:.2f} KLD)
  Plot-B Total Water: {pb.dry_total_water_lpd:,} LPD ({pb.dry_total_water_lpd/1000:.2f} KLD)
  Grand Total: {tot.get('Total Water (LPD)', 0):,} LPD

WET SEASON
  Plot-A Total Water: {pa.wet_total_water_lpd:,} LPD
  Plot-B Total Water: {pb.wet_total_water_lpd:,} LPD

UGT DETAILS
  Plot-A Domestic UGT: {pa.ugt_domestic_liters:,} L
  Plot-A Flushing UGT: {pa.ugt_flushing_liters:,} L
  Plot-A Fire Tank: {pa.fire_tank_liters:,} L
  Plot-B Domestic UGT: {pb.ugt_domestic_liters:,} L
  Plot-B Flushing UGT: {pb.ugt_flushing_liters:,} L
  Plot-B Fire Tank: {pb.fire_tank_liters:,} L

STP DETAILS
  Plot-A STP: {pa.stp_capacity_kld} KLD
  Plot-B STP: {pb.stp_capacity_kld} KLD
  Total STP: {tot.get('Total STP Capacity (KLD)', 0)} KLD
"""
        self._text_tab("Page 2 - Consolidated", content)

    def _add_plot_tab(self, plot_name: str, plot) -> None:
        page_num = 3 if plot_name == "Plot-A" else 4
        lines = [f"WATER DEMAND - {plot_name}", "=" * 50, "", "RESIDENTIAL:"]
        for idx, w in enumerate(plot.residential_wings, 1):
            lines.append(
                f"  {idx}. {w.wing}: {w.flats} flats x {w.pop_per_flat} = {w.population} pop | "
                f"Dom={w.domestic_lpd:,} Flu={w.flushing_lpd:,} Total={w.total_lpd:,} LPD"
            )
        lines.append(
            f"  Sub-Total: Pop={plot.res_population:,} Dom={plot.res_domestic_lpd:,} "
            f"Flu={plot.res_flushing_lpd:,} Total={plot.res_total_lpd:,}"
        )
        lines.append("")
        lines.append("COMMERCIAL:")
        for idx, u in enumerate(plot.commercial_units, 1):
            lines.append(
                f"  {idx}. [{u.block}] {u.floor_label or u.comm_type}: {u.area_sqm:.0f} sqm, "
                f"pop={u.population} | Dom={u.domestic_lpd:,} Flu={u.flushing_lpd:,} Total={u.total_lpd:,}"
            )
        lines.append("")
        lines.append("OTHER MEASURES:")
        lines.append(f"  Landscape (NBC-2026): {plot.landscape_dry_lpd:,} LPD (wet: {plot.landscape_wet_lpd:,})")
        lines.append(f"  Swimming Pool: {plot.swimming_pool_lpd:,} LPD")
        lines.append(f"  HVAC: {plot.hvac_lpd:,} LPD")
        lines.append("")
        lines.append(f"GRAND TOTAL: {plot.dry_total_water_lpd:,} LPD")
        self._text_tab(f"Page {page_num} - {plot_name}", "\n".join(lines))

    def _add_ugt_tab(self, plot_name: str, plot) -> None:
        page_num = 5 if plot_name == "Plot-A" else 6
        lines = [f"UGT & OHT DETAILS - {plot_name}", "=" * 50, ""]
        for idx, sec in enumerate(plot.ugt_sections, 1):
            lines.append(
                f"  {idx}. {sec.description}: Req={sec.water_requirement_lpd:,} LPD, "
                f"{sec.storage_days} days -> {sec.total_storage_liters:,} L ({sec.total_storage_kld:.2f} KLD)"
            )
        lines.append("")
        lines.append("OHT DETAILS:")
        for idx, oht in enumerate(plot.oht_rows, 1):
            lines.append(
                f"  {idx}. {oht['wing']}: Dom={oht['domestic_kld']:.2f} Flu={oht['flushing_kld']:.2f} "
                f"FireBreak={oht['fire_break_kld']:.2f} FireOHT={oht['fire_oht_kld']:.2f} KLD"
            )
        self._text_tab(f"Page {page_num} - {plot_name} UGT", "\n".join(lines))

    def _add_stp_tab(self, plot_name: str, plot) -> None:
        page_num = 7 if plot_name == "Plot-A" else 8
        lines = [f"STP DETAILS - {plot_name}", "=" * 50, ""]
        for stp in plot.stp_sections:
            lines.append(f"STP FOR {stp.scope}")
            lines.append(f"  Total Water: {stp.total_water_lpd:,} LPD")
            lines.append(f"  Sewage @90%: {stp.sewage_lpd:,} LPD ({stp.sewage_kld:.2f} KLD)")
            lines.append(f"  Say STP Capacity: {stp.say_stp_kld:.2f} KLD")
            lines.append(f"  Treated Water: {stp.treated_water_lpd:,} LPD")
            lines.append(f"  Reuse Flushing: {stp.reuse_flushing_lpd:,} LPD")
            lines.append(f"  Reuse Landscape: {stp.reuse_landscape_lpd:,} LPD")
            lines.append(f"  Reuse HVAC: {stp.reuse_hvac_lpd:,} LPD")
            lines.append(f"  Excess Treated: {stp.excess_treated_lpd:,} LPD")
            lines.append("")
        self._text_tab(f"Page {page_num} - {plot_name} STP", "\n".join(lines))

# ==================== ui/splash_screen.py ====================




class SplashScreen(ctk.CTkFrame):
    """Branded splash screen shown on application startup."""

    def __init__(self, master, on_complete, duration_ms: int = 2500) -> None:
        super().__init__(master, fg_color=BRAND_NAVY)
        self.on_complete = on_complete
        self.duration_ms = duration_ms
        self._progress = 0.0
        self._build()
        self._animate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=1, column=0)

        ctk.CTkLabel(
            center,
            text="AMERICAN EDGE",
            font=("Arial", 36, "bold"),
            text_color=BRAND_ORANGE,
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            center,
            text="ENGINEERS PVT. LTD.",
            font=("Arial", 18),
            text_color="white",
        ).pack(pady=(0, 20))
        ctk.CTkLabel(
            center,
            text="Water Demand Design Software",
            font=("Arial", 15),
            text_color="#CCCCCC",
        ).pack(pady=(0, 30))

        self.progress = ctk.CTkProgressBar(center, width=320, mode="determinate")
        self.progress.pack(pady=8)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(center, text="Loading application...", font=("Arial", 11), text_color="#AAAAAA")
        self.status_label.pack(pady=(8, 0))
        ctk.CTkLabel(center, text="NBC-2026 Compliant", font=("Arial", 10, "italic"), text_color="#888888").pack(pady=(16, 0))

    def _animate(self) -> None:
        self._progress = min(1.0, self._progress + 0.04)
        self.progress.set(self._progress)
        if self._progress < 1.0:
            self.after(40, self._animate)
        else:
            self.status_label.configure(text="Ready")
            self.after(300, self.on_complete)

# ==================== ui/dashboard.py ====================





class MainDashboard(ctk.CTkFrame):
    """Fixed-height Project Home dashboard — only the project table scrolls."""

    def __init__(
        self,
        master,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color=COLOR_BACKGROUND)
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_exit = on_exit
        self.project_hub: Optional[ProjectHub] = None
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        hero = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        hero.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        hero.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(18, 12), pady=14)
        ctk.CTkLabel(left, text="Project Home", font=FONT_TITLE, text_color=COLOR_PRIMARY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Create, open and manage engineering projects.",
            font=FONT_SUBTITLE,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            hero,
            text="+ New Project",
            command=safe_command(self.on_new_project, parent=self),
            fg_color=COLOR_SUCCESS,
            hover_color="#1B8F58",
            width=140,
            height=36,
            font=("Arial", 11, "bold"),
        ).grid(row=0, column=1, padx=(8, 18), pady=14, sticky="e")

        ctk.CTkLabel(
            self,
            text="PROJECT OVERVIEW",
            font=("Arial", 11, "bold"),
            text_color=COLOR_PRIMARY,
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 4))

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        for i in range(4):
            stats_row.grid_columnconfigure(i, weight=1)

        for column, (key, title) in enumerate([
            ("total", "TOTAL PROJECTS"),
            ("active", "ACTIVE PROJECTS"),
            ("completed", "COMPLETED PROJECTS"),
            ("this_month", "THIS MONTH"),
        ]):
            self._stat_labels[key] = self._make_stat_card(stats_row, column, title, "0")

        self.project_hub = ProjectHub(
            self,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
            on_edit_project=self.on_open_project,
            on_stats_changed=self._update_stats,
        )
        self.project_hub.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 12))

    def _make_stat_card(self, parent, column: int, title: str, value: str):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
            height=58,
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 4 if column < 3 else 0))
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=title, font=FONT_STAT_LABEL, text_color=COLOR_TEXT_SECONDARY).pack(
            anchor="w", padx=10, pady=(6, 0)
        )
        value_label = ctk.CTkLabel(card, text=value, font=FONT_STAT_VALUE, text_color=COLOR_PRIMARY)
        value_label.pack(anchor="w", padx=10, pady=(0, 6))
        return value_label

    def _update_stats(self, stats: dict) -> None:
        mapping = {
            "total": stats.get("total", 0),
            "active": stats.get("active", 0),
            "completed": stats.get("completed", 0),
            "this_month": stats.get("this_month", 0),
        }
        for key, value in mapping.items():
            label = self._stat_labels.get(key)
            if label is not None:
                label.configure(text=str(value))

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()


DashboardScreen = MainDashboard

# ==================== ui/project_hub.py ====================





class ProjectHub(PageLifecycleMixin, ctk.CTkFrame):
    """Compact project table with filters; only the table area scrolls."""

    def __init__(
        self,
        master,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_edit_project: Optional[Callable[[str], None]] = None,
        on_stats_changed: Optional[Callable[[dict], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        self._init_page_lifecycle()
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_edit_project = on_edit_project or on_open_project
        self.on_stats_changed = on_stats_changed
        self._all_rows: list[dict] = []
        self._filtered_rows: list[dict] = []
        self._row_widgets: dict[str, ctk.CTkFrame] = {}
        self._selected_id: Optional[str] = None
        self._search_job = None
        self._last_stats_rows: list[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        filters = ctk.CTkFrame(self, fg_color="#F8FAFB", corner_radius=8)
        filters.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        filters.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(filters, text="PROJECT FILTERS", font=("Arial", 10, "bold"), text_color=BRAND_NAVY).grid(
            row=0, column=0, columnspan=8, sticky="w", padx=10, pady=(8, 4)
        )

        ctk.CTkLabel(filters, text="Engineer:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, padx=(10, 4), pady=(0, 4), sticky="w"
        )
        self.engineer_var = ctk.StringVar(value="All Engineers")
        self.engineer_combo = ctk.CTkComboBox(
            filters,
            values=["All Engineers"],
            variable=self.engineer_var,
            command=self._on_filter_change,
            width=140,
            height=28,
        )
        self.engineer_combo.grid(row=1, column=1, padx=(0, 10), pady=(0, 4), sticky="w")

        ctk.CTkLabel(filters, text="Status:", font=("Arial", 10, "bold")).grid(
            row=1, column=2, padx=(0, 4), pady=(0, 4), sticky="w"
        )
        self.status_var = ctk.StringVar(value="All Status")
        self.status_combo = ctk.CTkComboBox(
            filters,
            values=STATUS_FILTER_OPTIONS,
            variable=self.status_var,
            command=self._on_filter_change,
            width=120,
            height=28,
        )
        self.status_combo.grid(row=1, column=3, padx=(0, 10), pady=(0, 4), sticky="w")

        ctk.CTkLabel(filters, text="Search:", font=("Arial", 10, "bold")).grid(
            row=1, column=4, padx=(0, 4), pady=(0, 4), sticky="w"
        )
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filters,
            textvariable=self.search_var,
            placeholder_text="Project Name / Client / Project ID",
            height=28,
        )
        self.search_entry.grid(row=1, column=5, sticky="ew", padx=(0, 6), pady=(0, 4))
        self.search_entry.bind("<Return>", lambda _e: self._apply_filters())

        ctk.CTkLabel(filters, text="From:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, padx=(10, 4), pady=(0, 8), sticky="w"
        )
        self.from_date_var = ctk.StringVar()
        self.from_date_entry = ctk.CTkEntry(filters, textvariable=self.from_date_var, placeholder_text="DD-MM-YYYY", width=110, height=28)
        self.from_date_entry.grid(row=2, column=1, padx=(0, 10), pady=(0, 8), sticky="w")

        ctk.CTkLabel(filters, text="To:", font=("Arial", 10, "bold")).grid(
            row=2, column=2, padx=(0, 4), pady=(0, 8), sticky="w"
        )
        self.to_date_var = ctk.StringVar()
        self.to_date_entry = ctk.CTkEntry(filters, textvariable=self.to_date_var, placeholder_text="DD-MM-YYYY", width=110, height=28)
        self.to_date_entry.grid(row=2, column=3, padx=(0, 10), pady=(0, 8), sticky="w")

        btn_row = ctk.CTkFrame(filters, fg_color="transparent")
        btn_row.grid(row=2, column=4, columnspan=2, sticky="w", pady=(0, 8))
        ctk.CTkButton(
            btn_row, text="Search", width=70, height=28, fg_color=BRAND_ORANGE,
            command=safe_command(self._apply_filters, parent=self),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="Clear Filters", width=90, height=28,
            fg_color="#E8ECF0", hover_color=COLOR_BORDER, text_color=COLOR_PRIMARY,
            command=safe_command(self._clear_filters, parent=self),
        ).pack(side="left")

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 4))
        header_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header_row,
            text="PROJECTS",
            font=("Arial", 11, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=0, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(
            header_row,
            text="",
            font=("Arial", 9),
            text_color="#7A8794",
            anchor="e",
        )
        self.status_label.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            header_row,
            text="Engineer Performance",
            width=140,
            height=24,
            font=("Arial", 9),
            fg_color="#E8ECF0",
            hover_color="#DCE3EA",
            text_color=BRAND_NAVY,
            command=self._show_performance_dialog,
        ).grid(row=0, column=2, padx=(8, 0), sticky="e")

        self.table_wrap = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            label_text="",
        )
        self.table_wrap.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.table_wrap.grid_columnconfigure(0, weight=1)

        self._header_columns = [
            ("Project ID", 88),
            ("Date", 72),
            ("Project Name", 110),
            ("Client", 88),
            ("Engineer", 72),
            ("Type", 72),
            ("Status", 92),
            ("Time Taken", 72),
            ("Updated", 72),
            ("Actions", 48),
        ]
        self._table_header = ctk.CTkFrame(self.table_wrap, fg_color="#E8ECF0", corner_radius=4)
        self._table_header.pack(fill="x", pady=(0, 2))
        for i, (text, width) in enumerate(self._header_columns):
            ctk.CTkLabel(
                self._table_header,
                text=text,
                font=("Arial", 8, "bold"),
                width=width,
                anchor="w",
            ).grid(row=0, column=i, padx=2, pady=3, sticky="w")

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.icursor("end")

    def _clear_filters(self) -> None:
        self.engineer_var.set("All Engineers")
        self.status_var.set("All Status")
        self.search_var.set("")
        self.from_date_var.set("")
        self.to_date_var.set("")
        self._apply_filters()

    def refresh(self) -> None:
        self._all_rows = list_dashboard_projects_cached()
        engineers = list_engineer_options(self._all_rows)
        self.engineer_combo.configure(values=engineers)
        if self.engineer_var.get() not in engineers:
            self.engineer_var.set("All Engineers")
        self._apply_filters()

    def _on_filter_change(self, *_args) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        engineer = self.engineer_var.get()
        status = self.status_var.get()
        search = self.search_var.get()
        from_dt = parse_filter_date(self.from_date_var.get())
        to_dt = parse_filter_date(self.to_date_var.get())
        self._filtered_rows = filter_rows(
            self._all_rows,
            engineer=engineer,
            status_label=status,
            search=search,
            from_date=from_dt,
            to_date=to_dt,
        )
        self._last_stats_rows = rows_for_stats(self._all_rows, engineer=engineer, status_label=status)
        stats = compute_statistics(self._last_stats_rows)
        if self.on_stats_changed:
            self.on_stats_changed(stats)
        self._render_table()
        eng_label = engineer if engineer != "All Engineers" else "All Engineers"
        count_text = f"{eng_label} — {len(self._filtered_rows)} project(s)"
        self.status_label.configure(
            text=f"Showing {len(self._filtered_rows)} of {len(self._all_rows)} projects  |  {count_text}"
        )

    def _render_table(self) -> None:
        for widget in list(self.table_wrap.winfo_children()):
            if widget is not self._table_header:
                widget.destroy()
        self._row_widgets.clear()
        self._selected_id = None

        if not self._filtered_rows:
            query = self.search_var.get().strip()
            if query:
                msg = "No matching projects found."
                btn_text = "Clear Filters"
                cmd = self._clear_filters
            elif not self._all_rows:
                msg = "No projects found.\nCreate your first engineering project to get started."
                btn_text = "+ New Project"
                cmd = self.on_new_project
            else:
                msg = "No projects found for the selected filters."
                btn_text = "Clear Filters"
                cmd = self._clear_filters
            ctk.CTkLabel(
                self.table_wrap,
                text=msg,
                font=("Arial", 10),
                text_color=COLOR_TEXT_SECONDARY,
                justify="center",
            ).pack(pady=(16, 8))
            ctk.CTkButton(
                self.table_wrap,
                text=btn_text,
                width=140,
                height=30,
                fg_color=BRAND_ORANGE,
                command=safe_command(cmd, parent=self),
            ).pack(pady=(0, 16))
            return

        for row in self._filtered_rows:
            self._add_row(row)

    def _format_performance(self, row: dict) -> str:
        title = (row.get("performance_title") or "").strip()
        detail = (row.get("performance_detail") or "").strip()
        if title and detail:
            return f"{title} ({detail})"
        return title or detail or "—"

    def _status_badge(self, label: str) -> str:
        return STATUS_BADGES.get(label, label)

    def _add_row(self, row: dict) -> None:
        pid = row["project_id"]
        frame = ctk.CTkFrame(self.table_wrap, fg_color="transparent", corner_radius=2)
        frame.pack(fill="x", pady=0)
        self._row_widgets[pid] = frame

        values = [
            pid,
            row.get("created_display", row.get("date", "—"))[:10],
            row.get("project_name", ""),
            row.get("client_name", "") or "—",
            row.get("engineer_name", "") or "—",
            row.get("project_type_label", "—"),
            self._status_badge(row.get("status_label", "")),
            row.get("time_taken_display", "—"),
            row.get("updated_display", "—")[:10],
        ]
        widths = [w for _, w in self._header_columns[:-1]]
        for i, (value, width) in enumerate(zip(values, widths)):
            text = (value or "")[:28]
            lbl = ctk.CTkLabel(frame, text=text, font=("Arial", 8), width=width, anchor="w")
            lbl.grid(row=0, column=i, padx=2, pady=2, sticky="w")
            lbl.bind("<Button-1>", lambda _e, p=pid: self._select_row(p))
            frame.bind("<Button-1>", lambda _e, p=pid: self._select_row(p))
        frame.bind("<Double-Button-1>", lambda _e, p=pid: self._open_project(p))

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=0, column=len(values), padx=1, pady=1, sticky="w")
        ctk.CTkButton(
            actions,
            text="⋮",
            width=32,
            height=22,
            font=("Arial", 12, "bold"),
            fg_color="#E8ECF0",
            hover_color=COLOR_BORDER,
            text_color=COLOR_PRIMARY,
            command=safe_command(lambda p=pid, r=row: self._show_actions_menu(p, r), parent=self),
        ).pack(side="left")

    def _show_actions_menu(self, project_id: str, row: dict) -> None:
        menu = ctk.CTkToplevel(self)
        menu.title("Actions")
        menu.geometry("200x220")
        menu.resizable(False, False)
        menu.transient(self.winfo_toplevel())
        menu.grab_set()
        body = ctk.CTkFrame(menu, fg_color="white")
        body.pack(fill="both", expand=True, padx=10, pady=10)
        for label, cmd in [
            ("Open Project", lambda: self._menu_action(menu, lambda: self._open_project(project_id))),
            ("Edit Project", lambda: self._menu_action(menu, lambda: self._edit_project(project_id))),
            ("Delete Project", lambda: self._menu_action(menu, lambda: self._delete_project(project_id, row))),
        ]:
            ctk.CTkButton(
                body,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="#E8ECF0",
                text_color=COLOR_PRIMARY,
                command=cmd,
            ).pack(fill="x", pady=2)

    def _menu_action(self, menu, action) -> None:
        menu.grab_release()
        menu.destroy()
        action()

    def _select_row(self, project_id: str) -> None:
        self._selected_id = project_id
        for pid, row in self._row_widgets.items():
            row.configure(fg_color="#D6EAF8" if pid == project_id else "transparent")

    def _open_project(self, project_id: str) -> None:
        mark_project_opened(project_id)
        self.on_open_project(project_id)

    def _edit_project(self, project_id: str) -> None:
        mark_project_opened(project_id)
        self.on_edit_project(project_id)

    def _delete_project(self, project_id: str, row: dict) -> None:
        if not project_id:
            messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete Project")
        dialog.geometry("480x300")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        body = ctk.CTkFrame(dialog, fg_color="white")
        body.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(body, text="Are you sure you want to delete this project?", font=("Arial", 18, "bold"), text_color=BRAND_NAVY).pack(
            anchor="w", pady=(0, 8)
        )
        ctk.CTkLabel(
            body,
            text=(
                f"Project ID: {project_id}\n"
                f"Project: {row.get('project_name', '')}\n"
                f"Client: {row.get('client_name', '') or '—'}\n"
                f"Engineer: {row.get('engineer_name', '') or '—'}"
            ),
            font=("Arial", 11),
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(
            body,
            text="This action cannot be undone.",
            font=("Arial", 10, "bold"),
            text_color="#C0392B",
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")

        def _cancel() -> None:
            dialog.grab_release()
            dialog.destroy()

        def _confirm() -> None:
            try:
                if remove_project(project_id):
                    dialog.grab_release()
                    dialog.destroy()
                    self.refresh()
                    messagebox.showinfo("Delete Project", "Project deleted successfully.")
                else:
                    messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")
            except Exception:
                messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")

        ctk.CTkButton(buttons, text="Cancel", width=120, fg_color="#95A5A6", command=_cancel).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(buttons, text="Delete", width=100, fg_color="#C0392B", command=_confirm).pack(
            side="right"
        )

    def _show_performance_dialog(self) -> None:
        summary = compute_engineer_performance(self._last_stats_rows)
        dialog = ctk.CTkToplevel(self)
        dialog.title("Engineer Performance")
        dialog.geometry("620x360")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        body = ctk.CTkScrollableFrame(dialog, fg_color="white")
        body.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            body,
            text="ENGINEER PERFORMANCE",
            font=("Arial", 14, "bold"),
            text_color=BRAND_NAVY,
        ).pack(anchor="w", pady=(0, 8))

        if not summary:
            ctk.CTkLabel(
                body,
                text="No engineer performance data available yet.",
                font=("Arial", 10),
                text_color="#8A949E",
            ).pack(anchor="w", pady=8)
            return

        header = ctk.CTkFrame(body, fg_color="#E8ECF0", corner_radius=4)
        header.pack(fill="x", pady=(0, 4))
        perf_cols = [
            ("Engineer", 140),
            ("Projects", 70),
            ("Completed", 80),
            ("In Progress", 80),
            ("Delayed", 70),
            ("Avg. Time", 80),
        ]
        for i, (text, width) in enumerate(perf_cols):
            ctk.CTkLabel(header, text=text, font=("Arial", 9, "bold"), width=width, anchor="w").grid(
                row=0, column=i, padx=4, pady=4, sticky="w"
            )

        for item in summary:
            row_frame = ctk.CTkFrame(body, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)
            values = [
                item["engineer"],
                str(item["projects"]),
                str(item["completed"]),
                str(item["in_progress"]),
                str(item["delayed"]),
                item["avg_time_display"],
            ]
            for i, (value, (text, width)) in enumerate(zip(values, perf_cols)):
                ctk.CTkLabel(row_frame, text=value, font=("Arial", 9), width=width, anchor="w").grid(
                    row=0, column=i, padx=4, pady=2, sticky="w"
                )

# ==================== ui/project_edit_dialog.py ====================





class ProjectEditDialog(ctk.CTkToplevel):
    """Edit project header metadata without opening the calculator."""

    def __init__(
        self,
        master,
        project_id: str,
        user=None,
        on_saved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.project_id = project_id
        self.user = user
        self.on_saved = on_saved
        self.title("Edit Project")
        self.geometry("480x360")
        self.transient(master)
        self.grab_set()

        summary = get_project_summary(project_id)
        if not summary:
            messagebox.showerror("Error", "Project not found.")
            self.destroy()
            return

        ctk.CTkLabel(self, text="Edit Project Details", font=("Arial", 16, "bold")).pack(pady=12)
        ctk.CTkLabel(self, text=f"ID: {project_id}", font=("Arial", 10), text_color="#666666").pack()

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=8)

        self.entries = {}
        for key, label, value in [
            ("project_name", "Project Name", summary["project_name"]),
            ("client_name", "Client Name", summary["client_name"]),
            ("project_location", "Location", summary["project_location"]),
            ("engineer_name", "Engineer", summary.get("engineer_name", "")),
        ]:
            ctk.CTkLabel(form, text=label, anchor="w").pack(fill="x", pady=(8, 2))
            ent = ctk.CTkEntry(form, width=400)
            ent.insert(0, value)
            ent.pack(fill="x")
            self.entries[key] = ent

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=16)
        ctk.CTkButton(btn_row, text="Save", fg_color=BRAND_ORANGE, command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="gray", command=self.destroy).pack(side="left", padx=8)

    def _save(self) -> None:
        try:
            update_project_metadata(
                self.project_id,
                validate_required(self.entries["project_name"].get(), "Project Name"),
                validate_required(self.entries["client_name"].get(), "Client Name"),
                validate_required(self.entries["project_location"].get(), "Location"),
                self.entries["engineer_name"].get().strip(),
                updated_by=getattr(self.user, "username", "") if self.user else "",
            )
            messagebox.showinfo("Saved", "Project updated successfully.")
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except ValidationError as exc:
            messagebox.showerror("Validation", exc.message)

# ==================== ui/pages/project_page.py ====================




FORM_PAD_X = 16
FORM_ROW_PAD_Y = 6
SECTION_PAD_Y = (14, 4)
FIELD_WIDTH = 420
COMBO_WIDTH = 280
SMALL_FIELD_WIDTH = 90


def build_professional_page_header(parent, title: str, subtitle: str = "", step: str = ""):
    """Create a consistent, non-technical-friendly page header."""
    wrapper = ctk.CTkFrame(parent, fg_color="white", corner_radius=12, border_width=1, border_color="#DCE3EA")
    wrapper.pack(fill="x", padx=18, pady=(14, 10))
    wrapper.grid_columnconfigure(0, weight=1)
    left = ctk.CTkFrame(wrapper, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=20, pady=15)
    ctk.CTkLabel(left, text=title, font=("Arial", 21, "bold"), text_color=BRAND_NAVY, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(left, text=subtitle, font=("Arial", 10), text_color="#687684", anchor="w").pack(anchor="w", pady=(4, 0))
    if step:
        ctk.CTkLabel(
            wrapper,
            text=step,
            font=("Arial", 10, "bold"),
            text_color=BRAND_NAVY,
            fg_color="#EAF2F8",
            corner_radius=12,
            padx=14,
            pady=7,
        ).grid(row=0, column=1, padx=18, pady=15, sticky="e")
    return wrapper


def show_report_signoff(_project_type: str) -> bool:
    """Report Sign-off is common to every project type."""
    return True


def show_project_engineering_configuration(project_type: str) -> bool:
    """Show building-level configuration only for residential-family project types."""
    return project_type in (
        PROJECT_TYPE_RESIDENTIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_TOWNSHIP,
    )


class ProjectPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_type_change=None, on_back=None) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_type_change = on_type_change
        self.on_back = on_back
        self.entries: dict = {}
        self._engineering_widgets: list = []
        self._signoff_widgets: list = []
        self._details_visible = False
        self._deferred_sync_job = None
        self._build()

    def cancel_pending_callbacks(self) -> None:
        super().cancel_pending_callbacks()
        cancel_after(self, self._deferred_sync_job)
        self._deferred_sync_job = None

    def _add_section_header(self, parent, row: int, text: str) -> None:
        label = ctk.CTkLabel(parent, text=text, font=("Arial", 13, "bold"), text_color=COLOR_PRIMARY, anchor="w")
        label.grid(row=row, column=0, columnspan=2, padx=FORM_PAD_X, pady=SECTION_PAD_Y, sticky="w")

    def _add_label(self, parent, row: int, text: str, *, bold: bool = False, section: bool = False) -> ctk.CTkLabel:
        font = ("Arial", 14, "bold") if section else ("Arial", 13, "bold" if bold else "normal")
        kwargs = {"font": font, "anchor": "w"}
        if section:
            kwargs["text_color"] = BRAND_NAVY
        label = ctk.CTkLabel(parent, text=text, **kwargs)
        label.grid(
            row=row,
            column=0,
            padx=FORM_PAD_X,
            pady=SECTION_PAD_Y if section else (FORM_ROW_PAD_Y, FORM_ROW_PAD_Y),
            sticky="w",
        )
        return label

    def _add_entry_row(self, parent, row: int, label: str, key: str, default: str = "") -> ctk.CTkEntry:
        self._add_label(parent, row, label, bold=True)
        value = getattr(self.state.project, key, "") or ""
        if key == "project_name" and not value:
            value = default
        ent = ctk.CTkEntry(parent, width=FIELD_WIDTH, height=34)
        ent.insert(0, value)
        ent.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        self.entries[key] = ent
        return ent

    def _build(self) -> None:
        step, total = wizard_step_index("Project", self.state.project.project_type)
        build_page_header(
            self,
            "Project Details",
            "Enter the basic project information. Only required fields are shown.",
            step=step,
            total=total,
        )

        self.workflow_hint = ctk.CTkLabel(
            self,
            text="Choose a project type to unlock engineering workflow tabs.",
            font=("Arial", 11, "italic"),
            text_color="#666666",
            anchor="w",
        )
        self.workflow_hint.pack(fill="x", padx=16, pady=(0, 6))

        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form = ctk.CTkFrame(
            self.details_frame,
            fg_color=COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.form.pack(fill="x", padx=16, pady=8)
        self.form.grid_columnconfigure(0, weight=0)
        self.form.grid_columnconfigure(1, weight=1)

        if not self.state.project.project_no:
            self.state.project.project_no = next_project_number()

        row = 0
        self._add_section_header(self.form, row, "SECTION 1 — PROJECT INFORMATION")
        row += 1
        self._add_entry_row(self.form, row, "Project Name *", "project_name", "NEW PROJECT")
        row += 1
        self._add_label(self.form, row, "Project Number", bold=True)
        self.project_no_label = ctk.CTkLabel(
            self.form,
            text=self.state.project.project_no or "—",
            font=("Arial", 12),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self.project_no_label.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        row += 1
        self._add_section_header(self.form, row, "SECTION 2 — CLIENT INFORMATION")
        row += 1
        self._add_entry_row(self.form, row, "Client Name *", "client_name")
        row += 1

        engineering_header = ctk.CTkLabel(
            self.form,
            text="SECTION 3 — ENGINEERING CONFIGURATION",
            font=("Arial", 14, "bold"),
            text_color=COLOR_PRIMARY,
            anchor="w",
        )
        engineering_header.grid(row=row, column=0, columnspan=2, padx=FORM_PAD_X, pady=SECTION_PAD_Y, sticky="w")
        self._engineering_widgets.append(engineering_header)
        row += 1

        self._add_label(self.form, row, "Building Configuration")
        self.building_config_var = ctk.StringVar(value=self.state.project.building_config or "G+7")
        building_combo = ctk.CTkComboBox(
            self.form,
            values=list(BUILDING_CONFIG_EXAMPLES),
            variable=self.building_config_var,
            command=lambda *_: self._sync_building_height(),
            width=COMBO_WIDTH,
            height=34,
        )
        building_combo.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        self._engineering_widgets.extend([self.form.grid_slaves(row=row, column=0)[0], building_combo])
        row += 1

        self._add_label(self.form, row, "Building Height (m)")
        self.height_entry = ctk.CTkEntry(self.form, width=SMALL_FIELD_WIDTH, height=34)
        self.height_entry.insert(0, str(self.state.project.building_height_m or ""))
        self.height_entry.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        self.height_entry.bind("<KeyRelease>", lambda *_: self.schedule_auto_calculate(self.state))
        self._engineering_widgets.extend([self.form.grid_slaves(row=row, column=0)[0], self.height_entry])
        row += 1

        self._add_label(self.form, row, "Number of Wings")
        self.wings_entry = ctk.CTkEntry(self.form, width=SMALL_FIELD_WIDTH, height=34)
        self.wings_entry.insert(0, str(self.state.project.num_wings or 1))
        self.wings_entry.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        self._engineering_widgets.extend([self.form.grid_slaves(row=row, column=0)[0], self.wings_entry])
        row += 1

        self._add_label(self.form, row, "Building Type")
        self.building_type_var = ctk.StringVar(value=self.state.project.building_type or BUILDING_TYPES[0])
        building_type_combo = ctk.CTkComboBox(
            self.form,
            values=list(BUILDING_TYPES),
            variable=self.building_type_var,
            width=COMBO_WIDTH,
            height=34,
        )
        building_type_combo.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
        self._engineering_widgets.extend([self.form.grid_slaves(row=row, column=0)[0], building_type_combo])
        row += 1

        signoff_header = ctk.CTkLabel(
            self.form,
            text="SECTION 4 — REPORT SIGN-OFF",
            font=("Arial", 14, "bold"),
            text_color=COLOR_PRIMARY,
            anchor="w",
        )
        signoff_header.grid(row=row, column=0, columnspan=2, padx=FORM_PAD_X, pady=SECTION_PAD_Y, sticky="w")
        self._signoff_widgets.append(signoff_header)
        row += 1

        for label, attr, default in [
            ("Engineer Name", "engineer_var", "Akash"),
            ("Prepared By", "prepared_var", "Akash"),
            ("Checked By", "checked_var", "Akash"),
            ("Approved By", "approved_var", "Omkar"),
        ]:
            self._add_label(self.form, row, label)
            if label == "Engineer Name":
                existing = self.state.project.engineer_name
            elif label == "Prepared By":
                existing = self.state.project.revision.prepared_by
            elif label == "Checked By":
                existing = self.state.project.revision.checked_by
            else:
                existing = self.state.project.revision.approved_by
            var = ctk.StringVar(value=existing or default)
            setattr(self, attr, var)
            combo = ctk.CTkComboBox(
                self.form,
                values=list(STAFF_NAMES),
                variable=var,
                width=COMBO_WIDTH,
                height=34,
            )
            combo.grid(row=row, column=1, padx=FORM_PAD_X, pady=FORM_ROW_PAD_Y, sticky="w")
            self._signoff_widgets.extend([self.form.grid_slaves(row=row, column=0)[0], combo])
            row += 1

        btn_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=12)
        if self.on_back is not None:
            ctk.CTkButton(
                btn_frame,
                text="← Back",
                command=self.on_back,
                fg_color="#7F8C8D",
                hover_color="#667071",
                width=140,
            ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="Next →",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).pack(side="right", padx=8)

        self._apply_section_visibility()

        if is_project_type_set(self.state.project.project_type):
            self._show_details()
        else:
            self._hide_details()

    def _set_widgets_visible(self, widgets: list, show: bool) -> None:
        for widget in widgets:
            try:
                if show:
                    widget.grid()
                else:
                    widget.grid_remove()
            except Exception:
                pass

    def _set_engineering_configuration_visibility(self) -> None:
        show = show_project_engineering_configuration(self.state.project.project_type)
        self._set_widgets_visible(self._engineering_widgets, show)

    def _set_report_signoff_visibility(self) -> None:
        self._set_widgets_visible(self._signoff_widgets, show_report_signoff(self.state.project.project_type))

    def _apply_section_visibility(self) -> None:
        self._set_engineering_configuration_visibility()
        self._set_report_signoff_visibility()

    def section_rows_visible(self, start_row: int, end_row: int) -> bool:
        widgets = self._signoff_widgets if start_row >= self._signoff_start_row else self._engineering_widgets
        if not widgets:
            return False
        visible = False
        for widget in widgets:
            visible = True
            if not widget.winfo_ismapped():
                return False
        return visible

    @property
    def _engineering_start_row(self) -> int:
        return 5

    @property
    def _engineering_end_row(self) -> int:
        return 9

    @property
    def _signoff_start_row(self) -> int:
        return 10

    @property
    def _signoff_end_row(self) -> int:
        return 15

    def _update_workflow_hint(self) -> None:
        if not hasattr(self, "workflow_hint"):
            return
        if not is_project_type_set(self.state.project.project_type):
            self.workflow_hint.configure(text="Choose a project type to unlock engineering workflow tabs.")
            return
        tabs = visible_nav_labels(self.state.project.project_type)
        tab_text = " → ".join(tabs[:8])
        if len(tabs) > 8:
            tab_text += " → …"
        self.workflow_hint.configure(text=f"Active workflow: {tab_text}")

    def _show_details(self) -> None:
        self._details_visible = True
        self.details_frame.pack(fill="x", padx=0, pady=0)
        self._update_workflow_hint()
        self._sync_building_height()

    def _hide_details(self) -> None:
        self._details_visible = False
        self.details_frame.pack_forget()
        self._update_workflow_hint()

    def _sync_building_height(self) -> None:
        if not self._details_visible or not widget_is_alive(self):
            return
        if not widget_is_alive(getattr(self, "height_entry", None)):
            return
        config = self.building_config_var.get().strip()
        _, height = parse_building_config(config)
        if height > 0 and not safe_entry_text(self.height_entry).strip():
            safe_set_entry_text(self.height_entry, str(int(height)))
        self.state.project.building_config = config
        try:
            self.state.project.building_height_m = float(safe_entry_text(self.height_entry) or height or 0)
        except ValueError:
            pass
        self.schedule_auto_calculate(self.state)

    def _save_and_next(self) -> None:
        if not is_project_type_set(self.state.project.project_type):
            messagebox.showwarning("Project Type", "Please select a project type before continuing.")
            return

        try:
            today = datetime.now().strftime("%d-%m-%Y")
            self.state.project.project_name = validate_required(
                self.entries["project_name"].get(), "Project Name"
            )
            self.state.project.client_name = validate_required(
                self.entries["client_name"].get(), "Client Name"
            )
            self.state.project.engineer_name = validate_required(
                self.engineer_var.get(), "Engineer Name"
            )
            if not self.state.project.project_no:
                self.state.project.project_no = next_project_number()
            self.state.project.date = today

            if show_project_engineering_configuration(self.state.project.project_type):
                self.state.project.building_config = self.building_config_var.get().strip()
                self.state.project.building_height_m = float(self.height_entry.get() or 0)
                self.state.project.num_wings = validate_positive_int(
                    self.wings_entry.get(), "Number of Wings"
                )
                self.state.project.building_type = self.building_type_var.get()

            self.state.project.revision = RevisionInfo(
                date=today,
                revision_no="R0",
                description="ISSUED FOR REFERENCE",
                prepared_by=self.prepared_var.get().strip(),
                checked_by=self.checked_var.get().strip(),
                approved_by=self.approved_var.get().strip(),
            )

            try:
                upsert_client({
                    "client_name": self.state.project.client_name,
                    "engineer_name": self.state.project.engineer_name,
                })
            except Exception:
                traceback.print_exc()

            self.on_next()

            cancel_after(self, self._deferred_sync_job)
            self._deferred_sync_job = self.after(
                100,
                safe_widget_callback(self, self._deferred_post_navigation_sync),
            )
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Validation Error", f"Please check the entered values.\n\n{exc}")
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Project Details",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )

    def _deferred_post_navigation_sync(self) -> None:
        self._deferred_sync_job = None
        if not widget_is_alive(self):
            return
        try:
            self.state.sync_building_defaults()
        except Exception:
            traceback.print_exc()
        try:
            self.schedule_auto_calculate(self.state)
        except Exception:
            pass

    def refresh(self) -> None:
        if not widget_is_alive(self):
            return
        project = self.state.project

        for key in ("project_name", "client_name"):
            entry = self.entries.get(key)
            if entry is not None:
                value = getattr(project, key, "") or ""
                safe_set_entry_text(entry, value)

        if hasattr(self, "building_config_var"):
            safe_stringvar_set(self.building_config_var, project.building_config or "G+7")
        if hasattr(self, "height_entry"):
            height = project.building_height_m or 0
            target = str(int(height)) if float(height).is_integer() else str(height)
            safe_set_entry_text(self.height_entry, target)
        if hasattr(self, "wings_entry"):
            safe_set_entry_text(self.wings_entry, str(project.num_wings or 1))
        if hasattr(self, "building_type_var"):
            safe_stringvar_set(self.building_type_var, project.building_type or BUILDING_TYPES[0])

        if hasattr(self, "engineer_var"):
            safe_stringvar_set(self.engineer_var, project.engineer_name or "Akash")
        if hasattr(self, "prepared_var"):
            safe_stringvar_set(self.prepared_var, project.revision.prepared_by or "Akash")
        if hasattr(self, "checked_var"):
            safe_stringvar_set(self.checked_var, project.revision.checked_by or "Akash")
        if hasattr(self, "approved_var"):
            safe_stringvar_set(self.approved_var, project.revision.approved_by or "Omkar")

        self._apply_section_visibility()
        if is_project_type_set(project.project_type):
            self._show_details()
        else:
            self._hide_details()
        self._update_workflow_hint()

# ==================== ui/pages/residential_page.py ====================




class ResidentialPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_back = on_back
        self.rows: list = []
        self.table_frame = ctk.CTkFrame(self)
        self.subtotal_labels: dict = {}
        self._build()

    def _plot_values(self) -> list[str]:
        return plot_dropdown_choices(self.state.project.plot_mode)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if self.state.project.plot_mode == PLOT_MODE_SINGLE else "Plot A + B"
        ctk.CTkLabel(
            header,
            text=f"Residential / Building Details ({plot_text})",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="Enter BHK units only — Population, Domestic, Flushing & Kitchen auto-calculate per NBC",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        headers = [
            "Plot", "Wing", "Config", "Bldg Type", "Ht(m)", "Wings",
            "1BHK", "2BHK", "3BHK", "4BHK", "PH",
            "Pop", "Dom", "Flush", "Total", "Kit", "",
        ]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 9, "bold")).grid(row=0, column=i, padx=1, pady=4)

        if not self.state.residential:
            self._add_default_rows()
        else:
            for wing in self.state.residential:
                self._add_row(wing)

        sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        sub_frame.pack(fill="x", padx=15, pady=5)
        for plot in self._plot_values():
            lbl = ctk.CTkLabel(sub_frame, text=f"{plot} Population: 0", font=("Arial", 12))
            lbl.pack(side="left", padx=15)
            self.subtotal_labels[plot] = lbl

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Wing", command=lambda: self._add_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="+ Add Bungalow", command=self._add_bungalow, fg_color="#2980B9").grid(
            row=0, column=1, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=2, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Save & Next ->",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
        ).grid(row=0, column=3, padx=10)

        self._update_subtotals()

    def _add_default_rows(self) -> None:
        default_plot = self._plot_values()[0]
        for wing in [
            ResidentialWing(plot=default_plot, wing="WING - A", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
            ResidentialWing(plot=default_plot, wing="WING - B", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
        ]:
            self._add_row(wing)

    def _add_bungalow(self) -> None:
        count = sum(
            1 for r in self.rows
            if "BUNGLOW" in r["wing"].get().upper() or "BUNGALOW" in r["wing"].get().upper()
        )
        letter = chr(65 + count)
        self._add_row(
            ResidentialWing(
                plot=self._plot_values()[0],
                wing=f"BUNGLOW-{letter}",
                building_config="G+1",
                building_height_m=6.0,
                num_wings=1,
                flats_3bhk=1,
            )
        )

    def _add_row(self, wing: ResidentialWing | None = None) -> None:
        r = len(self.rows) + 1
        config_values = list(BUILDING_CONFIG_EXAMPLES)
        plot_var = ctk.StringVar(
            value=ui_plot_label(wing.plot, self.state.project.plot_mode) if wing else self._plot_values()[0]
        )
        plot_cb = ctk.CTkComboBox(self.table_frame, values=self._plot_values(), variable=plot_var, width=72)
        w_ent = ctk.CTkEntry(self.table_frame, width=78)
        w_ent.insert(0, wing.wing if wing else "")
        cfg_var = ctk.StringVar(value=wing.building_config if wing else "G+7")
        cfg_cb = ctk.CTkComboBox(self.table_frame, values=config_values, variable=cfg_var, width=72)
        btype_var = ctk.StringVar(value=wing.building_type if wing else BUILDING_TYPES[0])
        btype_cb = ctk.CTkComboBox(self.table_frame, values=list(BUILDING_TYPES), variable=btype_var, width=95)
        ht_ent = ctk.CTkEntry(self.table_frame, width=48)
        ht_ent.insert(0, str(wing.building_height_m if wing and wing.building_height_m else ""))
        wings_ent = ctk.CTkEntry(self.table_frame, width=42)
        wings_ent.insert(0, str(wing.num_wings if wing else 1))
        b1_ent = ctk.CTkEntry(self.table_frame, width=40)
        b1_ent.insert(0, str(wing.flats_1bhk if wing else ""))
        b2_ent = ctk.CTkEntry(self.table_frame, width=40)
        b2_ent.insert(0, str(wing.flats_2bhk if wing else ""))
        b3_ent = ctk.CTkEntry(self.table_frame, width=40)
        b3_ent.insert(0, str(wing.flats_3bhk if wing else ""))
        b4_ent = ctk.CTkEntry(self.table_frame, width=40)
        b4_ent.insert(0, str(wing.flats_4bhk if wing else ""))
        ph_ent = ctk.CTkEntry(self.table_frame, width=40)
        ph_ent.insert(0, str(wing.flats_penthouse if wing else ""))
        pop_lbl = ctk.CTkLabel(self.table_frame, text="0", width=42)
        dom_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        flu_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        tot_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        kit_lbl = ctk.CTkLabel(self.table_frame, text="0", width=42)

        def update(*_):
            try:
                b1 = max(0, int(b1_ent.get() or 0))
                b2 = max(0, int(b2_ent.get() or 0))
                b3 = max(0, int(b3_ent.get() or 0))
                b4 = max(0, int(b4_ent.get() or 0))
                ph = max(0, int(ph_ent.get() or 0))
                temp = ResidentialWing(
                    building_config=cfg_var.get(),
                    building_height_m=float(ht_ent.get() or 0),
                    flats_1bhk=b1,
                    flats_2bhk=b2,
                    flats_3bhk=b3,
                    flats_4bhk=b4,
                    flats_penthouse=ph,
                )
                pop = temp.population
                dom, flu, tot = residential_demand(pop)
                kitchen = temp.kitchen_water
                pop_lbl.configure(text=str(pop))
                dom_lbl.configure(text=str(dom))
                flu_lbl.configure(text=str(flu))
                tot_lbl.configure(text=str(tot))
                kit_lbl.configure(text=str(kitchen))
                if not ht_ent.get().strip() and temp.building_height_m > 0:
                    ht_ent.delete(0, "end")
                    ht_ent.insert(0, str(int(temp.building_height_m)))
            except ValueError:
                pop_lbl.configure(text="0")
                dom_lbl.configure(text="0")
                flu_lbl.configure(text="0")
                tot_lbl.configure(text="0")
                kit_lbl.configure(text="0")
            self._update_subtotals()
            self._sync_and_calculate()

        for ent in (ht_ent, wings_ent, b1_ent, b2_ent, b3_ent, b4_ent, ph_ent):
            ent.bind("<KeyRelease>", update)
        for var in (plot_var, cfg_var, btype_var):
            var.trace_add("write", update)

        widgets = [
            plot_cb, w_ent, cfg_cb, btype_cb, ht_ent, wings_ent,
            b1_ent, b2_ent, b3_ent, b4_ent, ph_ent,
            pop_lbl, dom_lbl, flu_lbl, tot_lbl, kit_lbl,
        ]
        for j, widget in enumerate(widgets):
            widget.grid(row=r, column=j, padx=1, pady=4)

        def remove_row():
            for widget in widgets + [rm_btn]:
                widget.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()
            self._update_subtotals()
            self._sync_and_calculate()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=26, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=16, padx=1, pady=4)

        self.rows.append({
            "row_idx": r,
            "plot": plot_var,
            "wing": w_ent,
            "config": cfg_var,
            "btype": btype_var,
            "height": ht_ent,
            "num_wings": wings_ent,
            "b1": b1_ent,
            "b2": b2_ent,
            "b3": b3_ent,
            "b4": b4_ent,
            "ph": ph_ent,
            "pop_lbl": pop_lbl,
            "widgets": widgets + [rm_btn],
        })
        update()

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=1, pady=4)

    def _update_subtotals(self) -> None:
        totals = {plot: 0 for plot in self._plot_values()}
        for row in self.rows:
            try:
                plot = row["plot"].get()
                temp = ResidentialWing(
                    flats_1bhk=int(row["b1"].get() or 0),
                    flats_2bhk=int(row["b2"].get() or 0),
                    flats_3bhk=int(row["b3"].get() or 0),
                    flats_4bhk=int(row["b4"].get() or 0),
                    flats_penthouse=int(row["ph"].get() or 0),
                )
                totals[plot] = totals.get(plot, 0) + temp.population
                row["pop_lbl"].configure(text=str(temp.population))
            except ValueError:
                pass
        for plot, lbl in self.subtotal_labels.items():
            lbl.configure(text=f"{plot} Population: {totals.get(plot, 0):,}")

    def _sync_and_calculate(self) -> None:
        self.state.residential = wings_from_ui_rows(self.rows, self.state.project.plot_mode)
        self.schedule_auto_calculate(self.state)

    def _save_and_next(self) -> None:
        wings: list = []
        try:
            for idx, row in enumerate(self.rows):
                wing_name = validate_required(row["wing"].get(), "Wing Name")
                b1 = validate_positive_int(row["b1"].get(), "1 BHK Units", allow_zero=True)
                b2 = validate_positive_int(row["b2"].get(), "2 BHK Units", allow_zero=True)
                b3 = validate_positive_int(row["b3"].get(), "3 BHK Units", allow_zero=True)
                b4 = validate_positive_int(row["b4"].get(), "4 BHK Units", allow_zero=True)
                ph = validate_positive_int(row["ph"].get(), "Penthouse Units", allow_zero=True)
                if b1 + b2 + b3 + b4 + ph <= 0:
                    raise ValidationError(f"Enter at least one BHK unit count for wing '{wing_name}'.")
                height = float(row["height"].get() or 0)
                num_wings = validate_positive_int(row["num_wings"].get(), "No. of Wings", allow_zero=False)
                wings.append(ResidentialWing(
                    plot=row["plot"].get(),
                    wing=wing_name,
                    building_config=row["config"].get(),
                    building_type=row["btype"].get(),
                    building_height_m=height,
                    num_wings=num_wings,
                    flats_1bhk=b1,
                    flats_2bhk=b2,
                    flats_3bhk=b3,
                    flats_4bhk=b4,
                    flats_penthouse=ph,
                    sort_order=idx,
                ))
            if not wings:
                raise ValidationError("Add at least one residential wing.")
            self.state.residential = wings
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        self._update_subtotals()

# ==================== ui/pages/commercial_page.py ====================




class CommercialPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_back = on_back
        self.rows: list = []
        self.table_frame = ctk.CTkFrame(self)
        self._build()

    def _plot_values(self) -> list[str]:
        return plot_dropdown_choices(self.state.project.plot_mode)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if self.state.project.plot_mode == PLOT_MODE_SINGLE else "Plot A + B"
        ctk.CTkLabel(
            header,
            text=f"Commercial Details ({plot_text})",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="Select Occupancy Type and Area — Population & demand auto-calculate per NBC",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        self.table_frame.pack(fill="both", expand=True, padx=15, pady=10)
        headers = [
            "Plot", "Block", "Occupancy Type", "Floor", "Area (sq.m)",
            "Pop", "Dom", "Flush", "Total", "",
        ]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 11, "bold")).grid(row=0, column=i, padx=3, pady=5)
        for col in range(len(headers)):
            self.table_frame.grid_columnconfigure(col, weight=1 if col in (2, 3) else 0)

        if not self.state.commercial:
            self._add_default_row()
        else:
            for unit in self.state.commercial:
                self._add_row(unit)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Commercial", command=lambda: self._add_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Save & Next ->",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
        ).grid(row=0, column=2, padx=10)

    def _add_default_row(self) -> None:
        self._add_row(CommercialUnit(
            plot=self._plot_values()[0],
            block="COMM-A",
            comm_type="Retail Shop",
            floor_label="Ground Floor",
            area_sqm=437,
        ))

    def _add_row(self, unit: CommercialUnit | None = None) -> None:
        r = len(self.rows) + 1
        type_values = list(COMMERCIAL_OCCUPANCY_TYPES)
        default_type = unit.comm_type if unit else "Office"
        if default_type not in type_values:
            for alias, spec in COMMERCIAL_TYPES.items():
                if alias == default_type or spec.label == default_type:
                    default_type = spec.label if spec.label in type_values else type_values[0]
                    break
            else:
                default_type = type_values[0]

        plot_var = ctk.StringVar(
            value=ui_plot_label(unit.plot, self.state.project.plot_mode) if unit else self._plot_values()[0]
        )
        plot_cb = ctk.CTkComboBox(self.table_frame, values=self._plot_values(), variable=plot_var, width=85)
        block_ent = ctk.CTkEntry(self.table_frame, width=75)
        block_ent.insert(0, unit.block if unit else "COMM-A")
        type_var = ctk.StringVar(value=default_type)
        type_cb = ctk.CTkComboBox(self.table_frame, values=type_values, variable=type_var, width=130)
        floor_ent = ctk.CTkEntry(self.table_frame, width=100)
        floor_ent.insert(0, unit.floor_label if unit else "")
        area_ent = ctk.CTkEntry(self.table_frame, width=80)
        area_ent.insert(0, str(unit.area_sqm if unit else ""))
        pop_lbl = ctk.CTkLabel(self.table_frame, text="0", width=55)
        dom_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)
        flu_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)
        tot_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)

        def update(*_):
            try:
                area = float(area_ent.get() or 0)
                spec = COMMERCIAL_TYPES.get(type_var.get(), COMMERCIAL_TYPES["Office"])
                pop = commercial_population(area, spec)
                dom, flu, tot = commercial_demand(pop, spec)
                pop_lbl.configure(text=str(pop))
                dom_lbl.configure(text=str(dom))
                flu_lbl.configure(text=str(flu))
                tot_lbl.configure(text=str(tot))
            except ValueError:
                pop_lbl.configure(text="0")
                dom_lbl.configure(text="0")
                flu_lbl.configure(text="0")
                tot_lbl.configure(text="0")
            self._sync_and_calculate()

        area_ent.bind("<KeyRelease>", update)
        type_var.trace_add("write", update)
        update()

        plot_cb.grid(row=r, column=0, padx=3, pady=5)
        block_ent.grid(row=r, column=1, padx=3, pady=5)
        type_cb.grid(row=r, column=2, padx=3, pady=5)
        floor_ent.grid(row=r, column=3, padx=3, pady=5)
        area_ent.grid(row=r, column=4, padx=3, pady=5)
        pop_lbl.grid(row=r, column=5, padx=3, pady=5)
        dom_lbl.grid(row=r, column=6, padx=3, pady=5)
        flu_lbl.grid(row=r, column=7, padx=3, pady=5)
        tot_lbl.grid(row=r, column=8, padx=3, pady=5)

        def remove_row():
            for w in row_data["widgets"]:
                w.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()
            self._sync_and_calculate()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=28, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=9, padx=3, pady=5)

        row_data = {
            "row_idx": r,
            "plot": plot_var,
            "block": block_ent,
            "type": type_var,
            "floor": floor_ent,
            "area": area_ent,
            "widgets": [
                plot_cb, block_ent, type_cb, floor_ent, area_ent,
                pop_lbl, dom_lbl, flu_lbl, tot_lbl, rm_btn,
            ],
        }
        self.rows.append(row_data)

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=3, pady=5)

    def _sync_and_calculate(self) -> None:
        self.state.commercial = commercial_from_ui_rows(self.rows, self.state.project.plot_mode)
        self.schedule_auto_calculate(self.state)

    def _save_and_next(self) -> None:
        units: list = []
        try:
            for idx, row in enumerate(self.rows):
                area = validate_positive_float(row["area"].get(), "Area (sq.m)", allow_zero=False)
                if area > 0:
                    units.append(CommercialUnit(
                        plot=row["plot"].get(),
                        block=validate_required(row["block"].get(), "Block"),
                        comm_type=row["type"].get(),
                        floor_label=row["floor"].get().strip(),
                        area_sqm=area,
                        sort_order=idx,
                    ))
            self.state.commercial = units
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        pass

# ==================== ui/pages/other_page.py ====================




class OtherPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_calculate, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_calculate = on_calculate
        self.on_back = on_back
        self.entries: dict = {}
        self.pool_status_vars: dict = {}
        self.pool_entries: dict = {}
        self.oht_rows: list = []
        self.oht_frame = ctk.CTkFrame(self)
        self.fire_labels: dict = {}
        self._build()

    def _plots(self) -> list[str]:
        return plot_choices(self.state.project.plot_mode)

    def _auto_fire_tank(self, plot: str) -> int:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return fire_tank_capacity_liters(max_height, btype)
        return int(self.state.other.fire_tank.get(plot, 0))

    def _pool_label_for_plot(self, plot: str) -> str:
        status = self.state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
        if self.state.other.swimming_pool_na.get(plot, False):
            status = POOL_NOT_APPLICABLE
        for label, value in POOL_STATUS_LABELS.items():
            if value == status:
                return label
        return "Not Applicable"

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header,
            text="Landscape / Pool / HVAC / Fire Tank / OHT",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="UGT, OHT, STP & Fire Tank auto-calculate — updates on every change",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        row = 0
        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=200)
            ent.insert(0, str(self.state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            ent.grid(row=row, column=1, padx=15, pady=8)
            ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
            self.entries[f"landscape_{plot}"] = ent
            row += 1

        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Swimming Pool {plot}", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            status_var = ctk.StringVar(value=self._pool_label_for_plot(plot))
            status_cb = ctk.CTkComboBox(
                form, values=list(POOL_STATUS_LABELS.keys()), variable=status_var, width=160,
                command=lambda *_: self._toggle_pool_fields(),
            )
            status_cb.grid(row=row, column=1, padx=15, pady=8, sticky="w")
            self.pool_status_vars[plot] = status_var
            pool_ent = ctk.CTkEntry(form, width=200)
            pool_ent.insert(0, str(int(self.state.other.swimming_pool.get(plot, 0))))
            pool_ent.grid(row=row, column=2, padx=15, pady=8)
            pool_ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
            self.pool_entries[plot] = pool_ent
            row += 1
        self._toggle_pool_fields()

        self.hvac_entries: dict = {}
        if hvac_applicable(self.state.project.project_type):
            for plot in self._plots():
                ctk.CTkLabel(
                    form, text=f"HVAC Water {plot} (L/day)", font=("Arial", 13)
                ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
                ent = ctk.CTkEntry(form, width=200)
                ent.insert(0, str(int(self.state.other.hvac_water.get(plot, 0))))
                ent.grid(row=row, column=1, padx=15, pady=8)
                ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
                self.hvac_entries[plot] = ent
                row += 1
        else:
            ctk.CTkLabel(
                form,
                text="HVAC: Applicable only for Commercial and IT Park projects",
                font=("Arial", 12, "italic"),
                text_color="#7F8C8D",
            ).grid(row=row, column=0, columnspan=3, padx=15, pady=8, sticky="w")
            row += 1

        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Fire Tank {plot} (litres)", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            auto_val = self._auto_fire_tank(plot)
            lbl = ctk.CTkLabel(
                form, text=f"{auto_val:,} (auto — NBC Table 7)", font=("Arial", 12)
            )
            lbl.grid(row=row, column=1, columnspan=2, padx=15, pady=8, sticky="w")
            self.fire_labels[plot] = lbl
            row += 1

        ctk.CTkLabel(self, text="OHT Details (Optional — auto-calculated if empty)", font=("Arial", 14, "bold")).pack(
            pady=(15, 5)
        )
        self.oht_frame.pack(fill="x", padx=15, pady=5)
        oht_headers = ["Plot", "Wing/Block", "Domestic KLD", "Flushing KLD", "Fire Break KLD", "Fire OHT KLD", ""]
        for i, h in enumerate(oht_headers):
            ctk.CTkLabel(self.oht_frame, text=h, font=("Arial", 11, "bold")).grid(row=0, column=i, padx=3, pady=3)

        if self.state.other.oht_details:
            for oht in self.state.other.oht_details:
                self._add_oht_row(oht)
        else:
            self._add_oht_row()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="+ Add OHT Row", command=lambda: self._add_oht_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Next -> Generate Report",
            command=self._finish,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).grid(row=0, column=2, padx=10)

        self._sync_and_calc()

    def _toggle_pool_fields(self) -> None:
        for plot, var in self.pool_status_vars.items():
            ent = self.pool_entries.get(plot)
            if not ent:
                continue
            if var.get() == "Not Applicable":
                ent.configure(state="disabled")
            else:
                ent.configure(state="normal")
        self._sync_and_calc()

    def _sync_and_calc(self) -> None:
        try:
            for plot in self._plots():
                self.state.other.landscape_area[plot] = float(
                    self.entries[f"landscape_{plot}"].get() or 0
                )
                status = POOL_STATUS_LABELS.get(
                    self.pool_status_vars[plot].get(), POOL_NOT_APPLICABLE
                )
                self.state.other.swimming_pool_status[plot] = status
                self.state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
                if status == POOL_NOT_APPLICABLE:
                    self.state.other.swimming_pool[plot] = 0.0
                else:
                    self.state.other.swimming_pool[plot] = float(
                        self.pool_entries[plot].get() or 0
                    )
                if hvac_applicable(self.state.project.project_type):
                    self.state.other.hvac_water[plot] = float(
                        self.hvac_entries[plot].get() or 0
                    )
                else:
                    self.state.other.hvac_water[plot] = 0.0
                self.state.other.fire_tank[plot] = float(self._auto_fire_tank(plot))
            self.state.auto_calculate()
            for plot, lbl in self.fire_labels.items():
                lbl.configure(text=f"{self._auto_fire_tank(plot):,} (auto — NBC Table 7)")
        except (ValueError, KeyError):
            pass

    def _add_oht_row(self, oht: OHTDetail | None = None) -> None:
        r = len(self.oht_rows) + 1
        plot_var = ctk.StringVar(value=oht.plot if oht else self._plots()[0])
        plot_cb = ctk.CTkComboBox(self.oht_frame, values=self._plots(), variable=plot_var, width=90)
        wing_ent = ctk.CTkEntry(self.oht_frame, width=100)
        wing_ent.insert(0, oht.wing if oht else "")
        dom_ent = ctk.CTkEntry(self.oht_frame, width=80)
        dom_ent.insert(0, str(oht.domestic_kld if oht else ""))
        flu_ent = ctk.CTkEntry(self.oht_frame, width=80)
        flu_ent.insert(0, str(oht.flushing_kld if oht else ""))
        fb_ent = ctk.CTkEntry(self.oht_frame, width=80)
        fb_ent.insert(0, str(oht.fire_break_kld if oht else ""))
        fo_ent = ctk.CTkEntry(self.oht_frame, width=80)
        fo_ent.insert(0, str(oht.fire_oht_kld if oht else ""))

        plot_cb.grid(row=r, column=0, padx=3, pady=3)
        wing_ent.grid(row=r, column=1, padx=3, pady=3)
        dom_ent.grid(row=r, column=2, padx=3, pady=3)
        flu_ent.grid(row=r, column=3, padx=3, pady=3)
        fb_ent.grid(row=r, column=4, padx=3, pady=3)
        fo_ent.grid(row=r, column=5, padx=3, pady=3)

        def remove():
            for w in widgets:
                w.destroy()
            self.oht_rows = [row for row in self.oht_rows if row["idx"] != r]

        rm_btn = ctk.CTkButton(self.oht_frame, text="X", width=30, fg_color="#C0392B", command=remove)
        rm_btn.grid(row=r, column=6, padx=3, pady=3)
        widgets = [plot_cb, wing_ent, dom_ent, flu_ent, fb_ent, fo_ent, rm_btn]
        self.oht_rows.append({
            "idx": r,
            "plot": plot_var,
            "wing": wing_ent,
            "dom": dom_ent,
            "flu": flu_ent,
            "fb": fb_ent,
            "fo": fo_ent,
        })

    def _finish(self) -> None:
        try:
            for plot in self._plots():
                self.state.other.landscape_area[plot] = validate_positive_float(
                    self.entries[f"landscape_{plot}"].get(), f"Landscape {plot}"
                )
                status = POOL_STATUS_LABELS.get(
                    self.pool_status_vars[plot].get(), POOL_NOT_APPLICABLE
                )
                self.state.other.swimming_pool_status[plot] = status
                self.state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
                if status != POOL_NOT_APPLICABLE:
                    self.state.other.swimming_pool[plot] = validate_positive_float(
                        self.pool_entries[plot].get(), f"Swimming Pool {plot}"
                    )
                else:
                    self.state.other.swimming_pool[plot] = 0.0
                if hvac_applicable(self.state.project.project_type):
                    self.state.other.hvac_water[plot] = validate_positive_float(
                        self.hvac_entries[plot].get(), f"HVAC {plot}"
                    )
                else:
                    self.state.other.hvac_water[plot] = 0.0
                self.state.other.fire_tank[plot] = float(self._auto_fire_tank(plot))
            oht_list = []
            for row in self.oht_rows:
                wing = row["wing"].get().strip()
                if wing:
                    oht_list.append(OHTDetail(
                        plot=row["plot"].get(),
                        wing=wing,
                        domestic_kld=validate_positive_float(row["dom"].get(), f"OHT Domestic ({wing})"),
                        flushing_kld=validate_positive_float(row["flu"].get(), f"OHT Flushing ({wing})"),
                        fire_break_kld=validate_positive_float(row["fb"].get(), f"OHT Fire Break ({wing})"),
                        fire_oht_kld=validate_positive_float(row["fo"].get(), f"OHT Fire OHT ({wing})"),
                    ))
            self.state.other.oht_details = oht_list
            self.state.auto_calculate()
            self.on_calculate()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        for plot, lbl in self.fire_labels.items():
            lbl.configure(text=f"{self._auto_fire_tank(plot):,} (auto — NBC Table 7)")
        self._sync_and_calc()

# ==================== ui/pages/final_page.py ====================





class FinalPage(ScrollablePage):
    def __init__(
        self,
        master,
        state: AppState,
        on_back,
        on_generate_all: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.state = state
        self.on_back = on_back
        self.on_generate_all = on_generate_all
        self.summary_label = None
        self.detail_text = None
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(header, text="Generate Report", font=("Arial", 22, "bold"), text_color="white").pack(pady=12)
        ctk.CTkLabel(
            header,
            text="Calculate, validate, export PDF & Excel, save project, and open preview",
            font=("Arial", 11),
            text_color="#DDDDDD",
        ).pack(pady=(0, 10))

        if self.on_generate_all:
            ctk.CTkButton(
                self,
                text="Generate Report",
                command=self.on_generate_all,
                fg_color=BRAND_ORANGE,
                hover_color="#D06018",
                height=48,
                font=("Arial", 16, "bold"),
            ).pack(pady=(5, 10), padx=20, fill="x")

        self.summary_label = ctk.CTkLabel(self, text="", font=("Arial", 15, "bold"), justify="center")
        self.summary_label.pack(pady=10)

        self.detail_text = ctk.CTkTextbox(self, height=260, font=("Courier", 11))
        self.detail_text.pack(fill="both", expand=True, padx=20, pady=10)

        act_frame = ctk.CTkFrame(self, fg_color="transparent")
        act_frame.pack(pady=15)
        ctk.CTkButton(act_frame, text="Preview Report", command=self._preview, fg_color="#8E44AD", width=150).grid(row=0, column=0, padx=8)
        ctk.CTkButton(act_frame, text="Generate 8-Page PDF", command=self._export_pdf, fg_color="#C0392B", width=160).grid(row=0, column=1, padx=8)
        ctk.CTkButton(act_frame, text="Export Excel", command=self._export_excel, fg_color="#27AE60", width=130).grid(row=0, column=2, padx=8)
        ctk.CTkButton(act_frame, text="Save JSON", command=self._save_json, fg_color="#2980B9", width=110).grid(row=0, column=3, padx=8)
        ctk.CTkButton(act_frame, text="Save to Database", command=self._save_db, fg_color="#16A085", width=140).grid(row=0, column=4, padx=8)
        ctk.CTkButton(act_frame, text="<- Back to Edit", command=self.on_back, fg_color="gray", width=120).grid(row=0, column=5, padx=8)

    def refresh(self) -> None:
        if not self.state.results:
            self.summary_label.configure(text="No calculations available. Complete project data and use Generate Report.")
            return
        tot = self.state.results.total
        plots = plot_choices(self.state.project.plot_mode)
        parts = []
        for plot_name in plots:
            plot = self.state.results.plots.get(plot_name)
            if plot:
                parts.append(f"{plot_name} STP: {plot.stp_capacity_kld} KLD")
        summary = (
            "  |  ".join(parts) + "\n"
            f"Total Project Demand: {tot.get('Total Water (LPD)', 0):,} LPD "
            f"({tot.get('Total Water (LPD)', 0) / 1000:.2f} KLD)"
        )
        self.summary_label.configure(text=summary)

        lines = ["DETAILED CALCULATION SUMMARY", "=" * 50, ""]
        for plot_name in plots:
            plot = self.state.results.plots.get(plot_name)
            if not plot:
                continue
            lines.append(f"{plot_name}:")
            lines.append(f"  Residential: {plot.res_population} pop, {plot.res_total_lpd:,} LPD")
            lines.append(f"  Commercial: {plot.com_population} pop, {plot.com_total_lpd:,} LPD")
            lines.append(f"  Landscape: {plot.landscape_dry_lpd:,} LPD (dry), {plot.landscape_wet_lpd:,} LPD (wet)")
            lines.append(f"  Total Water (Dry): {plot.dry_total_water_lpd:,} LPD")
            lines.append(f"  UGT Domestic: {plot.ugt_domestic_liters:,} L")
            lines.append(f"  UGT Flushing: {plot.ugt_flushing_liters:,} L")
            lines.append(f"  Fire Tank: {plot.fire_tank_liters:,} L")
            lines.append(f"  STP Capacity: {plot.stp_capacity_kld} KLD")
            lines.append("")
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state="disabled")

    def _ensure_results(self) -> bool:
        if not self.state.results:
            messagebox.showwarning("No Data", "Please complete project data and calculate first.")
            return False
        return True

    def _preview(self) -> None:
        if not self._ensure_results():
            return
        PreviewDialog(self.winfo_toplevel(), self.state.project, self.state.results, on_export_pdf=self._export_pdf)

    def _export_pdf(self) -> None:
        if not self._ensure_results():
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="8_Page_Water_Demand_Report.pdf",
        )
        if not file_path:
            return

        def do_export():
            logo = os.path.join(APP_DIR, "assets", "logo.png")
            export_pdf(file_path, self.state.project, self.state.results, logo if os.path.exists(logo) else None)

        if safe_execute(do_export, lambda msg: messagebox.showerror("PDF Error", msg)):
            messagebox.showinfo("Success", "8-Page Professional PDF Exported Successfully!")

    def _export_excel(self) -> None:
        if not self._ensure_results():
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="Water_Demand_Report.xlsx",
        )
        if not file_path:
            return

        def do_export():
            export_excel(file_path, self.state.project, self.state.results)

        if safe_execute(do_export, lambda msg: messagebox.showerror("Excel Error", msg)):
            messagebox.showinfo("Success", "Excel Exported Successfully with Plot Tabs!")

    def _save_json(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Water Demand Project", "*.wdproj.json"), ("JSON files", "*.json")],
            initialfile=f"{self.state.project.project_id}.wdproj.json",
        )
        if not file_path:
            return

        def do_save():
            save_project_json(
                file_path,
                self.state.project,
                self.state.residential,
                self.state.commercial,
                self.state.other,
                self.state.results.to_dict() if self.state.results else None,
            )

        if safe_execute(do_save, lambda msg: messagebox.showerror("Save Error", msg)):
            messagebox.showinfo("Success", f"Project saved to {file_path}")

    def _save_db(self) -> None:
        def do_save():
            save_project(
                self.state.project,
                self.state.residential,
                self.state.commercial,
                self.state.other,
                self.state.results.to_dict() if self.state.results else None,
            )

        if safe_execute(do_save, lambda msg: messagebox.showerror("Database Error", msg)):
            messagebox.showinfo("Success", "Project saved to database successfully!")

# ==================== _app_sidebar.py ====================




APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "assets", "logo.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(os.path.dirname(APP_DIR), "logo.png")


# ============================================================
# PROJECT WORKSPACE (embedded in single main window)
# ============================================================

def _raise_page(page) -> None:
    """Reliably bring a page to the front in the shared workspace container."""
    try:
        page.grid(row=0, column=0, sticky="nsew")
    except Exception:
        pass
    try:
        page.tkraise()
    except Exception:
        try:
            page.lift()
        except Exception:
            pass
    try:
        parent_frame = getattr(page, "_parent_frame", None)
        if parent_frame is not None:
            parent_frame.tkraise()
    except Exception:
        pass


def _destroy_page(page) -> None:
    """Cancel pending callbacks and destroy a workflow page safely."""
    if page is None:
        return
    cancel = getattr(page, "cancel_pending_callbacks", None)
    if callable(cancel):
        try:
            cancel()
        except Exception:
            pass
    master = None
    try:
        master = page.master
    except Exception:
        pass
    try:
        page.destroy()
    except Exception:
        pass
    if master is not None and widget_is_alive(master):
        try:
            master.update_idletasks()
        except Exception:
            pass


class ProjectWorkspace(ctk.CTkFrame):
    NAV = [
        ("Project", "Project Details"),
        ("Residential", "Residential"),
        ("Commercial", "Commercial"),
        ("Hospital", "Hospital Details"),
        ("Hotel", "Hotel / Kitchen"),
        ("FoodCourt", "Food Court"),
        ("Landscape", "Landscape"),
        ("Swimming", "Swimming Pool"),
        ("HVAC", "HVAC"),
        ("UGT", "UGT / Fire Tank"),
        ("Sewage", "Sewage Generation"),
        ("OHT", "OHT Details"),
        ("STP", "STP Summary"),
        ("SolidWaste", "Solid Waste Generation"),
        ("Preview", "Preview"),
        ("Report", "Generate Report"),
        ("Settings", "Settings"),
    ]

    def __init__(
        self,
        master,
        on_home=None,
        initial_state=None,
        on_autosave=None,
        on_header_update=None,
        current_user=None,
        on_logout=None,
        on_new_project=None,
        on_back_to_type_selector=None,
    ):
        super().__init__(master, fg_color="#F0F2F5", corner_radius=0)
        self.on_home = on_home
        self.on_autosave = on_autosave
        self.on_header_update = on_header_update
        self.current_user = current_user
        self.on_logout = on_logout
        self.on_new_project = on_new_project
        self.on_back_to_type_selector = on_back_to_type_selector
        self.app_state = initial_state if initial_state is not None else AppState()
        self._last_autosave_at = ""
        self._pages_built = False
        self._autosave_job = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = self._build_sidebar()
        self.container = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.pages: dict = {}
        self._current_page = "Project"
        self._calc_job = None
        self._calc_dirty = True
        self._project_list_cache: list | None = None

    def ensure_pages_built(self) -> None:
        if self._pages_built:
            return
        self._build_pages()
        self._pages_built = True
        self.show("Project")

    def suspend_pending_work(self) -> None:
        """Cancel timers while the workspace is hidden (e.g. on the type selector)."""
        cancel_after(self, self._calc_job)
        self._calc_job = None
        for page in self.pages.values():
            cancel = getattr(page, "cancel_pending_callbacks", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception:
                    pass

    def _teardown_pages(self) -> None:
        """Destroy all workflow pages and flush pending Tk events."""
        self.suspend_pending_work()
        for page in list(self.pages.values()):
            _destroy_page(page)
        self.pages.clear()

    def reset_for_new_type(self) -> None:
        """Drop cached workflow pages before a new project/type is shown."""
        self._teardown_pages()
        self._current_page = "Project"
        self._calc_dirty = True

    def apply_state(self, state: AppState) -> None:
        """Install project state and reset stale lazily-built pages."""
        self._teardown_pages()
        self.app_state = state
        self._current_page = "Project"
        self._calc_dirty = True
        self._build_pages()
        self._rebuild_sidebar()
        self.show("Project")
        if widget_is_alive(self):
            self._calc_job = self.after(80, safe_widget_callback(self, self._run_scheduled_calc))
        if self.on_header_update:
            self.on_header_update()

    def autosave_before_close(self) -> None:
        try:
            self._calc()
            persist_project_state(self.app_state, db_path=DB_PATH)
        except Exception:
            pass

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        try:
            self._calc()
            persist_project_state(self.app_state, db_path=DB_PATH)
            self._last_autosave_at = datetime.now().strftime("%H:%M:%S")
            if self.on_autosave:
                self.on_autosave()
        except Exception:
            pass
        self._schedule_autosave()

    def _plots(self) -> list[str]:
        return plot_choices(self.app_state.project.plot_mode)

    def _nav_visible(self, key: str) -> bool:
        return key in visible_pages(self.app_state.project.project_type)

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        ctk.CTkLabel(
            sb,
            text="Project Navigation",
            font=("Arial", 14, "bold"),
            text_color="white",
            justify="center",
        ).pack(pady=(20, 12))
        if self.on_home:
            ctk.CTkButton(
                sb,
                text="Project Home",
                height=36,
                anchor="w",
                fg_color="#2980B9",
                hover_color=BRAND_ORANGE,
                text_color="white",
                font=("Arial", 12, "bold"),
                command=self.on_home,
            ).pack(fill="x", padx=8, pady=(0, 8))
        if self.current_user:
            ctk.CTkLabel(
                sb,
                text=f"{self.current_user.full_name}\n({self.current_user.role_label})",
                font=("Arial", 9),
                text_color="#CCCCCC",
                justify="center",
            ).pack(pady=(0, 4))
        pid = self.app_state.project.project_id
        ctk.CTkLabel(
            sb,
            text=f"ID: {pid}",
            font=("Arial", 8),
            text_color="#999999",
            wraplength=200,
        ).pack(pady=(0, 4))
        if is_project_type_set(self.app_state.project.project_type):
            self._project_type_label = ctk.CTkLabel(
                sb,
                text=project_type_label(self.app_state.project.project_type),
                font=("Arial", 9, "bold"),
                text_color=BRAND_ORANGE,
                wraplength=200,
            )
        else:
            self._project_type_label = ctk.CTkLabel(
                sb,
                text="Select project type",
                font=("Arial", 9, "italic"),
                text_color="#AAAAAA",
                wraplength=200,
            )
        self._project_type_label.pack(pady=(0, 8))
        self.nav_btns = {}
        for key, label in self.NAV:
            btn = ctk.CTkButton(
                sb,
                text=label,
                height=36,
                anchor="w",
                fg_color="transparent",
                hover_color=BRAND_ORANGE,
                text_color="white",
                font=("Arial", 12),
                command=lambda k=key: self.show(k),
            )
            self.nav_btns[key] = btn
            if self._nav_visible(key):
                btn.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self.on_new_project if self.on_new_project else self._new).pack(
            side="bottom", fill="x", padx=10, pady=(4, 4 if self.on_logout else 15)
        )
        if self.on_logout:
            ctk.CTkButton(sb, text="Logout", fg_color="#C0392B", command=self._logout).pack(
                side="bottom", fill="x", padx=10, pady=(4, 15)
            )
        return sb

    def _logout(self) -> None:
        if self.on_logout and messagebox.askyesno("Logout", "Return to login screen?"):
            self.on_logout()

    def _rebuild_sidebar(self) -> None:
        allowed = set(visible_pages(self.app_state.project.project_type))
        for key, btn in self.nav_btns.items():
            if key in allowed:
                if not btn.winfo_ismapped():
                    btn.pack(fill="x", padx=8, pady=2)
            else:
                btn.pack_forget()
        if hasattr(self, "_project_type_label"):
            if is_project_type_set(self.app_state.project.project_type):
                self._project_type_label.configure(
                    text=project_type_label(self.app_state.project.project_type),
                    font=("Arial", 9, "bold"),
                    text_color=BRAND_ORANGE,
                )
            else:
                self._project_type_label.configure(
                    text="Select project type",
                    font=("Arial", 9, "italic"),
                    text_color="#AAAAAA",
                )

    def _project_details_back(self):
        if self.on_back_to_type_selector:
            self.on_back_to_type_selector()
        elif self.on_home:
            self.on_home()
        elif self.on_new_project:
            self.on_new_project()

    def _build_pages(self) -> None:
        """Build only the lightweight Project Details page initially."""
        if "Project" not in self.pages:
            self.pages["Project"] = ProjectPage(
                self.container,
                self.app_state,
                on_next=self._next_from_project,
                on_type_change=self._on_project_type_changed,
                on_back=self._project_details_back,
            )
        page = self.pages.get("Project")
        if page is not None:
            try:
                page.grid(row=0, column=0, sticky="nsew")
            except Exception:
                pass

    def _build_single_page(self, key: str) -> bool:
        if key in self.pages:
            return True
        visible = visible_pages(self.app_state.project.project_type)
        if key != "Project" and key not in visible:
            return False

        if key == "Residential":
            self.pages[key] = ResidentialPage(
                self.container, self.app_state,
                on_next=self._next_from_residential,
                on_back=lambda: self.show("Project"),
            )
        elif key == "Commercial":
            self.pages[key] = CommercialPage(
                self.container, self.app_state,
                on_next=lambda: self._wizard_show_next("Commercial"),
                on_back=self._back_from_commercial,
            )
        elif key == "Hospital":
            self.pages[key] = self._placeholder_page(
                "Hospital Details",
                "Enter hospital bed counts and medical water requirements.\nUse Commercial page with Hospital occupancy for NBC calculations.",
                lambda: self._wizard_show_next("Hospital"), "Hospital")
        elif key == "Hotel":
            self.pages[key] = self._placeholder_page(
                "Hotel / Kitchen / Laundry",
                "Hotel kitchen and laundry water demands are calculated from commercial occupancy rules.\nAdd Hotel-type units on the Commercial page.",
                lambda: self._wizard_show_next("Hotel"), "Hotel")
        elif key == "FoodCourt":
            self.pages[key] = self._placeholder_page(
                "Food Court",
                "Food court water demand uses Restaurant occupancy (÷1.4 population density).\nAdd Restaurant units on the Commercial page.",
                lambda: self._wizard_show_next("FoodCourt"), "FoodCourt")
        elif key == "Landscape":
            self.pages[key] = self._form_page("Landscape (NBC-2026)", self._landscape_ui, "Landscape")
        elif key == "Swimming":
            self.pages[key] = self._form_page("Swimming Pool", self._pool_ui, "Swimming")
        elif key == "HVAC":
            self.pages[key] = self._form_page("HVAC Water", self._hvac_ui, "HVAC")
        elif key == "UGT":
            self.pages[key] = self._form_page("UGT / Fire Tank", self._ugt_ui, "UGT")
        elif key == "Sewage":
            self.pages[key] = self._sewage_page()
        elif key == "OHT":
            self.pages[key] = self._oht_page()
        elif key == "STP":
            self.pages[key] = self._stp_page()
        elif key == "SolidWaste":
            self.pages[key] = self._solid_waste_page()
        elif key == "Preview":
            self.pages[key] = self._preview_page()
        elif key == "Report":
            self.pages[key] = FinalPage(
                self.container, self.app_state,
                on_back=lambda: self.show("Preview"),
                on_generate_all=self._generate_report_all,
            )
        elif key == "Settings":
            self.pages[key] = self._settings_page()
        else:
            return False

        try:
            self.pages[key].grid(row=0, column=0, sticky="nsew")
        except Exception:
            pass
        return True

    def _placeholder_page(self, title: str, body: str, on_next, page_key: str):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(frame, text=body, font=("Arial", 12), justify="left", wraplength=900).pack(
            anchor="w", padx=20, pady=20
        )
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")
        ctk.CTkButton(nav, text="Next →", width=140, fg_color=BRAND_ORANGE, command=on_next).pack(side="right")
        return frame

    def _discard_inapplicable_pages(self) -> None:
        allowed = visible_pages(self.app_state.project.project_type)
        for key in list(self.pages.keys()):
            if key == "Project" or key in allowed:
                continue
            page = self.pages.pop(key, None)
            if page is not None:
                _destroy_page(page)

    def _on_project_type_changed(self) -> None:
        self._discard_inapplicable_pages()
        self._rebuild_sidebar()
        if not is_project_type_set(self.app_state.project.project_type):
            self.show("Project")
            if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
                self.pages["Project"].refresh()
            return
        self._schedule_calc(120)
        visible = visible_pages(self.app_state.project.project_type)
        if self._current_page not in visible:
            self.show("Project")
        if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
            self.pages["Project"].refresh()

    def _wizard_show_previous(self, current: str) -> None:
        project_type = self.app_state.project.project_type
        if not is_project_type_set(project_type):
            self.show("Project")
            return
        pages = visible_pages(project_type)
        if current not in pages:
            self.show("Project")
            return
        previous = None
        for key in WIZARD_PAGE_ORDER:
            if key not in pages:
                continue
            if key == current:
                break
            previous = key
        if previous:
            self._navigate_to_page(previous)

    def _navigate_to_page(self, target: str) -> bool:
        project_type = self.app_state.project.project_type
        if target != "Project" and not is_project_type_set(project_type):
            self.show("Project")
            return False
        allowed = visible_pages(project_type)
        if target not in allowed:
            self.show("Project")
            return False
        if not self._ensure_page_available(target):
            return False
        try:
            page = self.pages.get(target)
            if page is None or not page.winfo_exists():
                if not self._ensure_page_available(target):
                    return False
            self.show(target)
            return self._current_page == target
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Navigation Error",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )
            return False

    def _wizard_show_next(self, current: str) -> None:
        try:
            project_type = self.app_state.project.project_type
            if not is_project_type_set(project_type):
                messagebox.showwarning("Project Type", "Please select a project type before continuing.")
                self.show("Project")
                return

            pages = visible_pages(project_type)
            if current not in pages:
                self.show("Project")
                return

            nxt = wizard_next_page(current, project_type)
            if nxt is None:
                return

            if not self._ensure_page_available(nxt):
                messagebox.showerror("Navigation Error", f"Unable to open the next section: {nxt}")
                return

            page = self.pages.get(nxt)
            if page is None:
                messagebox.showerror("Navigation Error", f"The next section '{nxt}' could not be opened.")
                return

            for key, other in list(self.pages.items()):
                if key == nxt:
                    continue
                try:
                    other.grid_remove()
                except Exception:
                    try:
                        other.pack_forget()
                    except Exception:
                        pass

            page.grid(row=0, column=0, sticky="nsew")
            page.tkraise()
            try:
                parent_frame = getattr(page, "_parent_frame", None)
                if parent_frame is not None:
                    parent_frame.tkraise()
            except Exception:
                pass

            self._current_page = nxt
            for key, btn in self.nav_btns.items():
                try:
                    btn.configure(fg_color=BRAND_ORANGE if key == nxt else "transparent")
                except Exception:
                    pass

            if nxt == "STP":
                self._refresh_stp(silent=True)
            elif nxt == "Sewage":
                self._refresh_sewage(silent=True)
            elif nxt == "SolidWaste":
                self._refresh_solid_waste(silent=True)
            elif nxt == "OHT":
                self._refresh_oht(silent=True)
            elif nxt == "Preview":
                self._refresh_preview(silent=True)

            self.after(150, safe_widget_callback(self, lambda: self._schedule_calc(50)))

        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Navigation Error",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )

    def _form_page(self, title, builder, page_key):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        builder(frame)

        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")

        next_commands = {
            "Landscape": self._save_landscape,
            "Swimming": self._save_pool,
            "HVAC": lambda: (self._sync_hvac_live(), self._wizard_show_next("HVAC")),
            "UGT": lambda: self._wizard_show_next("UGT"),
        }
        next_command = next_commands.get(page_key, lambda pk=page_key: self._wizard_show_next(pk))
        ctk.CTkButton(nav, text="Next →", width=140, fg_color=BRAND_ORANGE, command=next_command).pack(side="right")
        return frame

    def _landscape_ui(self, parent):
        self._le = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(self.app_state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_landscape_live(), self._schedule_calc()))
            self._le[plot] = entry
        ctk.CTkLabel(parent, text="Auto: 6 L/sq.m/day per NBC-2026 (live)", font=("Arial", 11, "italic")).pack(anchor="w", padx=20)

    def _sync_landscape_live(self) -> None:
        if hasattr(self, "_le"):
            sync_landscape(self.app_state.other, self._le)

    def _save_landscape(self):
        try:
            for plot, entry in self._le.items():
                self.app_state.other.landscape_area[plot] = validate_positive_float(entry.get(), f"Landscape {plot}")
            self._wizard_show_next("Landscape")
        except ValidationError as exc:
            messagebox.showerror("Error", exc.message)

    def _pool_ui(self, parent):
        self._pe = {}
        self._pool_status = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Swimming Pool {plot}", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            status = self.app_state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
            if self.app_state.other.swimming_pool_na.get(plot, False):
                status = POOL_NOT_APPLICABLE
            label = next((k for k, v in POOL_STATUS_LABELS.items() if v == status), "Not Applicable")
            status_var = ctk.StringVar(value=label)
            ctk.CTkComboBox(
                form,
                values=list(POOL_STATUS_LABELS.keys()),
                variable=status_var,
                width=180,
                command=lambda *_: (self._sync_pool_live(), self._schedule_calc()),
            ).grid(row=i, column=1, padx=10, pady=8, sticky="w")
            self._pool_status[plot] = status_var
            entry = ctk.CTkEntry(form, width=180)
            entry.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            entry.grid(row=i, column=2, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_pool_live(), self._schedule_calc()))
            self._pe[plot] = entry

    def _sync_pool_live(self) -> None:
        if hasattr(self, "_pe") and hasattr(self, "_pool_status"):
            sync_swimming_pool(self.app_state.other, self._pe, self._pool_status)

    def _save_pool(self):
        for plot in self._plots():
            status = POOL_STATUS_LABELS.get(self._pool_status[plot].get(), POOL_NOT_APPLICABLE)
            self.app_state.other.swimming_pool_status[plot] = status
            self.app_state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
            if status == POOL_NOT_APPLICABLE:
                self.app_state.other.swimming_pool[plot] = 0.0
            else:
                self.app_state.other.swimming_pool[plot] = float(self._pe[plot].get() or 0)
        self._wizard_show_next("Swimming")

    def _hvac_ui(self, parent):
        self._he = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_hvac_live(), self._schedule_calc()))
            self._he[plot] = entry

    def _sync_hvac_live(self) -> None:
        if hasattr(self, "_he"):
            sync_hvac(self.app_state.other, self._he)

    def _plot_building_info(self, plot: str) -> tuple[float, str]:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.app_state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return max_height, btype
        project = self.app_state.project
        if project.building_height_m > 0:
            return project.building_height_m, project.building_type or "Residential Apartment"
        return 0.0, ""

    def _ugt_ui(self, parent):
        self._ugt_labels = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        row = 0
        for plot in self._plots():
            height, btype = self._plot_building_info(plot)
            ctk.CTkLabel(form, text=f"{plot} — Building Height (m)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(
                form,
                text=f"{height:.1f}" if height else "Set on Residential page",
                font=("Arial", 12),
            ).grid(row=row, column=1, padx=10, pady=8, sticky="w")
            row += 1
            ctk.CTkLabel(form, text=f"{plot} — Building Type", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(form, text=btype or "Set on Residential page", font=("Arial", 12)).grid(
                row=row, column=1, padx=10, pady=8, sticky="w"
            )
            row += 1
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            ctk.CTkLabel(form, text=f"{plot} — Fire Tank Capacity (litres)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            lbl = ctk.CTkLabel(form, text=f"{auto_val:,} (auto — NBC Table 7)", font=("Arial", 12))
            lbl.grid(row=row, column=1, padx=10, pady=8, sticky="w")
            self._ugt_labels[plot] = lbl
            row += 1
        ctk.CTkLabel(
            parent,
            text="UGT storage: Domestic 2-day, Flushing 1-day, Fire 1-day (auto-calculated in report)",
            font=("Arial", 11, "italic"),
        ).pack(anchor="w", padx=20, pady=5)

    def _refresh_ugt(self) -> None:
        for plot, lbl in getattr(self, "_ugt_labels", {}).items():
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            lbl.configure(text=f"{auto_val:,} (auto — NBC Table 7)")

    def _result_page(self, title: str, subtitle: str, table_attr: str, page_key: str):
        frame = ScrollablePage(self.container)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
            text=subtitle,
            font=("Arial", 11, "italic"),
            text_color="#555555",
        ).pack(anchor="w", padx=16, pady=(0, 4))
        table = ResultTableView(frame, embedded=True)
        table.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        setattr(self, table_attr, table)
        ctk.CTkLabel(
            frame,
            text="Updates automatically as you enter data on other pages.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 6))
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(2, 12))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")
        ctk.CTkButton(
            nav, text="Next →", width=140, fg_color=BRAND_ORANGE,
            command=lambda pk=page_key: self._wizard_show_next(pk),
        ).pack(side="right")
        return frame

    def _sewage_page(self):
        return self._result_page(
            "Sewage Generation",
            "Sewage Generation Calculations — auto-calculated from residential/commercial data.",
            "sewage_table",
            "Sewage",
        )

    def _refresh_sewage(self, silent: bool = False) -> None:
        if not hasattr(self, "sewage_table"):
            return
        if not self.app_state.environmental:
            self.sewage_table.set_rows("Sewage Generation Calculations", [("Enter project data first", "—", "")])
            return
        sections = build_sewage_generation_table_sections(
            self.app_state.project,
            self.app_state.environmental,
        )
        self.sewage_table.set_sections(sections)

    def _solid_waste_page(self):
        return self._result_page(
            "Solid Waste Generation",
            "Solid waste and e-waste calculations — auto-calculated from population and STP data.",
            "solid_waste_table",
            "SolidWaste",
        )

    def _refresh_solid_waste(self, silent: bool = False) -> None:
        if not hasattr(self, "solid_waste_table"):
            return
        if not self.app_state.environmental:
            self.solid_waste_table.set_rows("Solid Waste Calculations", [("Enter project data first", "—", "")])
            return
        sections = build_solid_waste_table_sections(
            self.app_state.project,
            self.app_state.environmental,
        )
        self.solid_waste_table.set_sections(sections)

    def _oht_page(self):
        return self._result_page(
            "OHT Details",
            "Overhead tank capacities auto-calculate from residential/commercial demand.",
            "oht_table",
            "OHT",
        )

    def _refresh_oht(self, silent: bool = False) -> None:
        if not hasattr(self, "oht_table"):
            return
        if not self.app_state.results:
            self.oht_table.set_rows("OHT Details", [("Enter residential/commercial data first", "—", "")])
            return
        sections = build_oht_table_sections(self.app_state.results, self._plots())
        self.oht_table.set_sections(sections)

    def _save_dict(self, entries, target):
        for plot, entry in entries.items():
            target[plot] = float(entry.get() or 0)

    def _stp_page(self):
        return self._result_page(
            "STP Summary",
            "Sewage treatment summary — auto-calculated from project inputs.",
            "stp_table",
            "STP",
        )

    def _refresh_stp(self, silent: bool = False):
        if not hasattr(self, "stp_table"):
            return
        if not self.app_state.results:
            self.stp_table.set_rows("STP Summary", [("Enter project data to calculate STP", "—", "")])
            return
        sections = build_stp_table_sections(self.app_state.results, self._plots())
        self.stp_table.set_sections(sections)

    def _preview_page(self):
        frame = ScrollablePage(self.container)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Report Preview", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.preview_table = ResultTableView(frame, embedded=True)
        self.preview_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ctk.CTkLabel(
            frame,
            text="Summary updates live — no Calculate button required.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 6))
        ctk.CTkButton(frame, text="Open Full Preview", fg_color="#2980B9", height=38, command=self._open_preview).pack(pady=6)
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(2, 12))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda: self._wizard_show_previous("Preview"),
        ).pack(side="left")
        ctk.CTkButton(
            nav, text="Next → Generate Report", width=190, fg_color=BRAND_ORANGE,
            command=lambda: self._navigate_to_page("Report"),
        ).pack(side="right")
        return frame

    def _refresh_preview(self, silent: bool = False) -> None:
        if not hasattr(self, "preview_table"):
            return
        if not self.app_state.results:
            self.preview_table.set_rows(
                "Preview",
                [("Complete Project, Residential, and Commercial pages first", "—", "")],
            )
            return
        sections = build_preview_table_sections(
            self.app_state.project,
            self.app_state.results,
            self._plots(),
            other=self.app_state.other,
            rwh_summary=None,
            environmental=self.app_state.environmental,
        )
        self.preview_table.set_sections(sections)

    def _settings_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Settings", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
            text=(
                f"Database:\n{DB_PATH}\n\n"
                f"Logo:\n{LOGO_PATH}\n\n"
                "NBC-2026 Standards:\n"
                "Residential 105+30 LPCD\n"
                "Landscape 6 L/sq.m\n"
                "STP 90% sewage"
            ),
            font=("Arial", 12),
            justify="left",
            anchor="w",
            wraplength=900,
        ).pack(fill="x", anchor="w", padx=20, pady=10)
        ctk.CTkButton(frame, text="Export JSON", fg_color="#2980B9", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(frame, text="Import JSON", fg_color="#2980B9", command=self._imp_json).pack(pady=8)
        ctk.CTkButton(
            frame, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda: self._wizard_show_previous("Settings"),
        ).pack(pady=(8, 14))
        return frame

    def _auto_fire_tank(self, plot: str) -> int:
        height, btype = self._plot_building_info(plot)
        if height > 0:
            return fire_tank_capacity_liters(height, btype)
        return int(self.app_state.other.fire_tank.get(plot, 0))

    def _next_from_project(self):
        self._wizard_show_next("Project")

    def _next_from_residential(self):
        self._wizard_show_next("Residential")

    def _back_from_commercial(self):
        if show_residential_section(self.app_state.project.project_type):
            self.show("Residential")
        else:
            self.show("Project")

    def _resolve_page_name(self, name: str) -> str:
        return name

    def _ensure_page_available(self, name: str) -> bool:
        if name in self.pages:
            try:
                return bool(self.pages[name].winfo_exists())
            except Exception:
                return True
        try:
            return self._build_single_page(name)
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Open Page",
                f"Unable to open '{name}'. Please check the project information and try again.\n\n{exc}",
            )
            return False

    def show(self, name: str) -> None:
        if not is_project_type_set(self.app_state.project.project_type) and name != "Project":
            name = "Project"
        name = self._resolve_page_name(name)
        allowed = visible_pages(self.app_state.project.project_type)
        if name not in allowed:
            name = "Project"

        if not self._ensure_page_available(name):
            return

        try:
            self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        except Exception:
            pass

        self._current_page = name
        page = self.pages[name]

        for key, other in list(self.pages.items()):
            if key == name:
                continue
            try:
                other.grid_remove()
            except Exception:
                pass

        _raise_page(page)
        if name == "Project" and hasattr(page, "refresh") and widget_is_alive(page):
            page.refresh()
        if name == "STP":
            self._refresh_stp()
        elif name == "Sewage":
            self._refresh_sewage()
        elif name == "SolidWaste":
            self._refresh_solid_waste()
        elif name == "OHT":
            self._refresh_oht()
        elif name == "Preview":
            if self._calc_dirty:
                self._calc()
            self._refresh_preview(silent=True)
        elif name == "UGT":
            self._refresh_ugt()
        elif name == "Report" and hasattr(page, "refresh"):
            page.refresh()
        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=BRAND_ORANGE if key == name else "transparent")

    def _schedule_calc(self, delay_ms: int = 300) -> None:
        self._calc_dirty = True
        cancel_after(self, self._calc_job)
        if widget_is_alive(self):
            self._calc_job = self.after(delay_ms, safe_widget_callback(self, self._run_scheduled_calc))

    def _run_scheduled_calc(self) -> None:
        self._calc_job = None
        if not widget_is_alive(self):
            return
        self._calc()

    def _calc(self):
        try:
            sync_pages_to_state(self)
            self.app_state.auto_calculate()
            self._calc_dirty = False
            self._refresh_live_panels()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _refresh_live_panels(self) -> None:
        """Update auto-calculated panels without manual refresh buttons."""
        if hasattr(self, "_ugt_labels"):
            self._refresh_ugt()
        if hasattr(self, "oht_table"):
            self._refresh_oht(silent=True)
        if hasattr(self, "stp_table"):
            self._refresh_stp(silent=True)
        if hasattr(self, "sewage_table"):
            self._refresh_sewage(silent=True)
        if hasattr(self, "solid_waste_table"):
            self._refresh_solid_waste(silent=True)
        if hasattr(self, "preview_table"):
            self._refresh_preview(silent=True)

    def _open_preview(self):
        self._calc()
        if self.app_state.results:
            PreviewDialog(
                self,
                self.app_state.project,
                self.app_state.results,
                on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
            )

    def _validate_for_report(self) -> bool:
        project = self.app_state.project
        try:
            validate_required(project.project_name, "Project Name")
            validate_required(project.client_name, "Client Name")
            validate_required(project.engineer_name, "Engineer Name")
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)
            return False
        self._calc()
        if not self.app_state.results:
            messagebox.showerror(
                "Validation Error",
                "Could not calculate water demand. Complete residential/commercial data first.",
            )
            return False
        return True

    def _generate_report_all(self) -> None:
        """One-button workflow: validate, calculate, PDF, Excel, save, preview."""
        if not self._validate_for_report():
            return

        project = self.app_state.project
        reports_dir = os.path.join(os.path.dirname(DB_PATH), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]+", "_", project.project_name or "Water_Demand")[:50].strip("_") or "Water_Demand"
        pdf_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.pdf")
        xlsx_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.xlsx")

        try:
            persist_project_state(self.app_state, db_path=DB_PATH)
            logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            export_pdf(pdf_path, self.app_state.project, self.app_state.results, logo)
            export_excel(xlsx_path, self.app_state.project, self.app_state.results)
            mark_project_completed(project.project_id, db_path=DB_PATH)
        except Exception as exc:
            messagebox.showerror("Generate Report", str(exc))
            return

        messagebox.showinfo(
            "Generate Report",
            f"Report generated successfully.\n\nPDF: {pdf_path}\nExcel: {xlsx_path}\n\nProject saved to database.",
        )
        self.show("Preview")
        PreviewDialog(
            self,
            self.app_state.project,
            self.app_state.results,
            on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
        )

    def _new(self):
        if not messagebox.askyesno("New Project", "Start a new project? Unsaved changes will be auto-saved first."):
            return
        try:
            self._autosave_before_close()
        except Exception:
            pass
        self.app_state = create_new_project_state(db_path=DB_PATH)
        self.apply_state(self.app_state)

    def _save_db(self):
        try:
            self._calc()
            is_update = persist_project_state(self.app_state, self.current_user, DB_PATH)
            if self.on_header_update:
                self.on_header_update()
            action = "updated" if is_update else "saved"
            messagebox.showinfo("Saved", f"Project {action}.\nID: {self.app_state.project.project_id}")
            if self.on_autosave:
                self.on_autosave()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _open_db(self):
        projs = find_projects()
        if not projs:
            messagebox.showinfo("Open Project", "No saved projects.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open Project")
        dialog.geometry("640x440")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Select Project", font=("Arial", 15, "bold")).pack(pady=8)
        search_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text="Search...", width=580).pack(padx=12, pady=4)
        scroll = ctk.CTkScrollableFrame(dialog, width=600, height=300)
        scroll.pack(padx=10, pady=4)
        selected = ctk.StringVar()
        row_widgets: list = []

        def populate(query: str = "") -> None:
            for w in row_widgets:
                w.destroy()
            row_widgets.clear()
            for proj in find_projects(query):
                rb = ctk.CTkRadioButton(
                    scroll,
                    text=(
                        f"{proj['project_id']} | {proj['project_name']} | "
                        f"{proj['client_name']} | {proj.get('project_location', '')}"
                    ),
                    variable=selected,
                    value=proj["project_id"],
                )
                rb.pack(anchor="w", padx=8, pady=3)
                row_widgets.append(rb)

        search_var.trace_add("write", lambda *_: populate(search_var.get()))
        populate()

        def load_selected():
            pid = selected.get()
            if not pid:
                messagebox.showwarning("Open Project", "Select a project.")
                return
            try:
                self.apply_state(load_project_state(pid, DB_PATH))
                dialog.destroy()
                messagebox.showinfo("Loaded", f"Project loaded.\nID: {pid}")
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))

        ctk.CTkButton(dialog, text="Open", fg_color=BRAND_ORANGE, command=load_selected).pack(pady=10)

    def _exp_json(self):
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            _save_json_file(fp, self.app_state)
            messagebox.showinfo("Saved", "JSON exported.")

    def _imp_json(self):
        fp = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if fp:
            proj, res, com, oth, _ = _load_json_file(fp)
            self.app_state.project = proj
            self.app_state.residential = res
            self.app_state.commercial = com
            self.app_state.other = oth
            self.app_state.run_calculations()
            messagebox.showinfo("Loaded", "JSON imported.")


def _save_json_file(fp, state):
    snap = build_project_snapshot(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
    )
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)


def _load_json_file(fp):
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    return parse_project_snapshot(data)


# Backward-compatible alias for tests and legacy entry points
WaterDemandApp = ProjectWorkspace

# ==================== app_launcher.py ====================
"""Application entry point — Splash → Project Home → unified project workflow."""





APP_VERSION = "2.0.0"
APP_TITLE = "American Edge Engineers - Water Demand Report Generator"


def _find_logo_path() -> str:
    """Find the company logo in common application locations."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(app_dir, "logo.png"),
        os.path.join(app_dir, "assets", "logo.png"),
        os.path.join(os.path.dirname(app_dir), "logo.png"),
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "assets", "logo.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return os.path.join(app_dir, "assets", "logo.png")


class Application(ctk.CTk):
    """Single main window: dashboard and project workflow share one shell."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_TITLE} v{APP_VERSION}")

        self.geometry("1360x900")
        self.minsize(1180, 760)
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        self.configure(fg_color="#F0F2F5")

        init_db(DB_PATH)
        init_lookup_tables(DB_PATH)

        self._workspace = None
        self._dashboard: Optional[MainDashboard] = None
        self._type_selector = None
        self._mode = "splash"
        self._last_saved_at = ""
        self._autosave_job = None
        self._save_state = "saved"  # saved | saving | error

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_shell()
        self._show_splash()

    def _build_shell(self) -> None:
        self.header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=82)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(0, weight=0)
        self.header.grid_columnconfigure(1, weight=1)
        self.header.grid_columnconfigure(2, weight=0)

        self._header_logo_image = None
        self.header_logo_label = None
        logo_path = _find_logo_path()
        if logo_path and os.path.isfile(logo_path):
            try:
                logo_pil = PILImage.open(logo_path).convert("RGBA")
                max_w, max_h = 210, 60
                iw, ih = logo_pil.size
                scale = min(max_w / max(iw, 1), max_h / max(ih, 1))
                logo_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
                self._header_logo_image = ctk.CTkImage(
                    light_image=logo_pil,
                    dark_image=logo_pil,
                    size=logo_size,
                )
                self.header_logo_label = ctk.CTkLabel(
                    self.header,
                    text="",
                    image=self._header_logo_image,
                    fg_color="transparent",
                    width=logo_size[0],
                    height=logo_size[1],
                )
                self.header_logo_label.grid(
                    row=0, column=0, rowspan=2, padx=(18, 12), pady=8, sticky="w"
                )
            except Exception:
                self.header_logo_label = None

        title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        title_frame.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 12), pady=8)
        ctk.CTkLabel(
            title_frame,
            text=COMPANY_NAME,
            font=FONT_HEADER_COMPANY,
            text_color="white",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame,
            text=COMPANY_TAGLINE,
            font=FONT_HEADER_TAGLINE,
            text_color="#AFC3D6",
            anchor="w",
        ).pack(anchor="w")

        self.header_meta = ctk.CTkLabel(
            self.header,
            text="Project Home",
            font=("Arial", 11),
            text_color="white",
            anchor="e",
        )
        self.header_meta.grid(row=0, column=2, rowspan=2, padx=(8, 18), sticky="e")

        self.body = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.status_bar = ctk.CTkFrame(self, fg_color="#E8ECF0", corner_radius=0, height=28)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Auto Calculation: ON  |  Ready",
            font=("Arial", 10),
            text_color="#555555",
            anchor="w",
        )
        self.status_label.pack(side="left", padx=12, pady=4)
        self.save_status_label = ctk.CTkLabel(
            self.status_bar,
            text="🟢 All changes saved",
            font=("Arial", 10),
            text_color="#555555",
            anchor="e",
        )
        self.save_status_label.pack(side="right", padx=12, pady=4)

        self._bind_shortcuts()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-n>", lambda _e: self._shortcut_new())
        self.bind_all("<Control-N>", lambda _e: self._shortcut_new())
        self.bind_all("<Control-o>", lambda _e: self._shortcut_open())
        self.bind_all("<Control-O>", lambda _e: self._shortcut_open())
        self.bind_all("<Control-s>", lambda _e: self._shortcut_save())
        self.bind_all("<Control-S>", lambda _e: self._shortcut_save())
        self.bind_all("<Escape>", lambda _e: self.focus_set())

    def _shortcut_new(self) -> None:
        if self._mode in ("dashboard", "type_selector"):
            self._start_new_project()

    def _shortcut_open(self) -> None:
        if self._mode == "dashboard" and self._dashboard and self._dashboard.project_hub:
            self._dashboard.project_hub.focus_search()

    def _shortcut_save(self) -> None:
        if self._workspace is not None and self._mode == "project":
            try:
                self._set_save_state("saving")
                self._workspace.autosave_before_close()
                self._on_project_autosaved()
            except Exception:
                self._set_save_state("error")

    def _set_save_state(self, state: str) -> None:
        self._save_state = state
        labels = {
            "saved": "🟢 All changes saved",
            "saving": "🟠 Saving changes...",
            "error": "🔴 Unable to save changes",
        }
        self.save_status_label.configure(text=labels.get(state, labels["saved"]))

    def _update_status(self) -> None:
        if self._workspace is not None and self._mode == "project":
            pid = self._workspace.app_state.project.project_id
            saved = f"Last saved: {self._last_saved_at}" if self._last_saved_at else "Last saved: —"
            self.status_label.configure(text=f"Project ID: {pid}  |  Auto Calculation: ON  |  {saved}")
            if self._save_state == "saved":
                self._set_save_state("saved")
        else:
            self.status_label.configure(text="Auto Calculation: ON  |  Project Home")
            self.save_status_label.configure(text="")

    def _update_header_meta(self) -> None:
        if self._workspace is not None and self._mode == "project":
            p = self._workspace.app_state.project
            ptype = project_type_label(p.project_type) if is_project_type_set(p.project_type) else "—"
            self.header_meta.configure(
                text=f"{p.project_name or 'Untitled'}  |  {p.project_id}  |  {ptype}"
            )
        else:
            self.header_meta.configure(text="Project Home")

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.grid_remove()

    def _show_splash(self) -> None:
        self._mode = "splash"
        self._clear_body()
        splash = SplashScreen(self.body, on_complete=self._show_dashboard)
        splash.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _show_dashboard(self) -> None:
        self._mode = "dashboard"
        self._clear_body()
        if self._workspace is not None:
            self._workspace.grid_remove()
        self._dashboard = MainDashboard(
            self.body,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_open_project=safe_command(self._open_project, parent=self),
            on_exit=self._exit_application,
        )
        self._dashboard.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _ensure_workspace(self):
        if self._workspace is not None:
            return self._workspace

        self._workspace = ProjectWorkspace(
            self.body,
            on_home=safe_command(self._show_dashboard, parent=self),
            on_autosave=self._on_project_autosaved,
            on_header_update=self._on_workspace_header_update,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_back_to_type_selector=safe_command(self._back_to_project_type_selector, parent=self),
        )
        return self._workspace

    def _destroy_type_selector(self) -> None:
        """Remove the project-type step UI so the workspace is not covered."""
        if self._type_selector is None:
            return
        try:
            self._type_selector.destroy()
        except Exception:
            traceback.print_exc()
        self._type_selector = None

    def _back_to_project_type_selector(self) -> None:
        """Return to Step 1 while keeping the current draft project state."""
        if self._workspace is None:
            self._start_new_project()
            return
        reset = getattr(self._workspace, "reset_for_new_type", None)
        if callable(reset):
            reset()
        self._show_project_type_selector(self._workspace.app_state)

    def _show_project(self, state: AppState) -> None:
        self._destroy_type_selector()
        ws = self._ensure_workspace()
        if self._dashboard is not None:
            self._dashboard.grid_remove()
        ws.grid(row=0, column=0, sticky="nsew")

        ws.app_state = state
        ws._calc_dirty = True
        ws.apply_state(state)
        ws._pages_built = True

        self._mode = "project"
        if state.project.project_id:
            try:
                mark_project_opened(state.project.project_id, DB_PATH)
            except Exception:
                traceback.print_exc()

        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        self._schedule_autosave()
        self._update_header_meta()
        self._update_status()

    def _start_new_project(self) -> None:
        state = create_new_project_state(DB_PATH)
        self._show_project_type_selector(state)

    def _show_project_type_selector(self, state: AppState) -> None:
        self._mode = "type_selector"
        self._clear_body()
        if self._workspace is not None:
            suspend = getattr(self._workspace, "suspend_pending_work", None)
            if callable(suspend):
                suspend()
            self._workspace.grid_remove()
        if self._dashboard is not None:
            self._dashboard.grid_remove()

        if self._type_selector is not None:
            try:
                self._type_selector.destroy()
            except Exception:
                pass

        frame = ctk.CTkFrame(self.body, fg_color="#F4F6F8")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self._type_selector = frame

        card = ctk.CTkFrame(
            frame,
            fg_color="white",
            corner_radius=18,
            border_width=1,
            border_color="#DCE3EA",
        )
        card.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="STEP 1 — SELECT PROJECT TYPE",
            font=("Arial", 10, "bold"),
            text_color=BRAND_ORANGE,
            fg_color="#FFF1E8",
            corner_radius=12,
            padx=12,
            pady=6,
        ).grid(row=0, column=0, pady=(20, 8))
        ctk.CTkLabel(
            card,
            text="Create a New Project",
            font=("Arial", 24, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=1, column=0, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Choose the type of project you are preparing a water-demand report for.",
            font=("Arial", 12),
            text_color="#64748B",
        ).grid(row=2, column=0, pady=(0, 12))

        initial_label = (
            project_type_label(state.project.project_type)
            if is_project_type_set(state.project.project_type)
            else PROJECT_TYPE_PLACEHOLDER
        )
        help_text = ctk.StringVar(value="Select a project type to continue.")

        def on_type_change(label: str) -> None:
            if label == PROJECT_TYPE_PLACEHOLDER:
                help_text.set("Select a project type to continue.")
            else:
                help_text.set(f"Selected: {label}. Click Continue to open the project workflow.")

        selector_wrap = ctk.CTkFrame(card, fg_color="transparent")
        selector_wrap.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 8))
        type_selector = ProjectTypeSelector(selector_wrap, initial_label=initial_label, on_selection_change=on_type_change)
        type_selector.pack(fill="x")
        if initial_label != PROJECT_TYPE_PLACEHOLDER:
            type_selector.set_selected(initial_label)
            on_type_change(initial_label)

        ctk.CTkLabel(
            card,
            textvariable=help_text,
            font=("Arial", 10),
            text_color="#6B7280",
            wraplength=700,
        ).grid(row=4, column=0, pady=(4, 8))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=5, column=0, pady=(0, 20))

        def cancel():
            self._destroy_type_selector()
            self._show_dashboard()

        def continue_project():
            label = type_selector.get_selected().strip()
            if label == PROJECT_TYPE_PLACEHOLDER:
                messagebox.showwarning(
                    "Project Type Required",
                    "Please select the project type before continuing.",
                )
                return
            try:
                new_type = project_type_key(label)
                old_type = state.project.project_type
                state.apply_project_type(new_type)
                self._destroy_type_selector()
                if self._workspace is not None:
                    self._workspace.app_state = state
                    self._workspace.reset_for_new_type()
                self._show_project(state)
            except Exception as exc:
                traceback.print_exc()
                messagebox.showerror(
                    "Navigation Error",
                    "Unable to open the next section. Please try again.",
                )

        ctk.CTkButton(
            buttons,
            text="← Back to Project Home",
            width=190,
            height=42,
            fg_color="#8A969C",
            hover_color="#6F7A80",
            font=("Arial", 11, "bold"),
            command=cancel,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            buttons,
            text="Continue →",
            width=200,
            height=42,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            font=("Arial", 11, "bold"),
            command=continue_project,
        ).pack(side="left", padx=8)

        self._update_header_meta()
        self._update_status()

    def _open_project(self, project_id: str) -> None:
        try:
            state = load_project_state(project_id, DB_PATH)
        except ValueError as exc:
            messagebox.showerror("Open Project", str(exc))
            return
        self._show_project(state)

    def _exit_application(self) -> None:
        if self._workspace is not None:
            try:
                self._workspace.autosave_before_close()
            except Exception:
                pass
        self.destroy()

    def _on_workspace_header_update(self) -> None:
        self._update_header_meta()
        self._update_status()

    def _on_project_autosaved(self) -> None:
        self._last_saved_at = datetime.now().strftime("%H:%M:%S")
        self._set_save_state("saved")
        self._update_status()
        if self._dashboard is not None:
            self._dashboard.refresh_stats()

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        if self._workspace is not None and self._mode == "project":
            try:
                self._workspace.autosave_before_close()
                self._on_project_autosaved()
            except Exception:
                pass
        self._schedule_autosave()


def main() -> None:
    Application().mainloop()

if __name__ == "__main__":
    main()
