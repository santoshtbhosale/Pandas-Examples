#!/usr/bin/env python3
"""
American Edge Engineers - Water Demand Report Generator
Single-file production application with NBC-2026 calculations.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tkcalendar import DateEntry
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "water_demand.db")
LOGO_PATH = os.path.join(APP_DIR, "logo.png")
JSON_SCHEMA_VERSION = "1.0"


# ==================== config/nbc_2026.py ====================
"""NBC-2026 water demand constants and calculation parameters."""



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
    revision: RevisionInfo = field(default_factory=RevisionInfo)

    def __post_init__(self) -> None:
        if not self.project_id:
            self.project_id = "WD-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not self.date:
            self.date = datetime.now().strftime("%d-%m-%Y")

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

    def _apply_auto_fire_tanks(self) -> None:
        for plot in self._plots:
            heights_types = [
                (w.building_height_m, w.building_type)
                for w in self.residential
                if w.plot == plot and w.building_height_m > 0
            ]
            if heights_types:
                max_height = max(h for h, _ in heights_types)
                btype = next((t for h, t in heights_types if h == max_height), "")
                self.other.fire_tank[plot] = float(
                    fire_tank_capacity_liters(max_height, btype)
                )

    def _calculate_plot(self, plot: str) -> PlotResults:
        plot_res = PlotResults(plot=plot)
        res_wings = [w for w in self.residential if w.plot == plot]
        com_units = [c for c in self.commercial if c.plot == plot]

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
            updated_at TEXT
        )
        """
    )
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


def save_project(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
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
            json_snapshot, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM projects WHERE project_id = ?), ?
        ), ?)
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


def list_projects(db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT project_id, project_name, client_name, date FROM projects ORDER BY updated_at DESC"
    )
    rows = [
        {"project_id": r[0], "project_name": r[1], "client_name": r[2], "date": r[3]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return rows


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
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 6)
        canvas.drawCentredString(letter[0] / 2, 15, COMPANY_FOOTER)
        canvas.restoreState()

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

    def _build_consolidated(self) -> List[Any]:
        story: List[Any] = [self._eng_header(), Spacer(1, 5)]
        story.append(self._section_bar("CONSOLIDATED STATEMENT", BRAND_DARK_GRAY))
        story.append(Spacer(1, 5))

        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        tot = self.results.total

        def kld(v: float) -> str:
            return f"{v / 1000:.2f}"

        header = [
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

        rows = [header]
        rows.append(
            [
                self._tc("SECTION-8", 0),
                self._tc("Number Of Building", 0),
                self._tc(pa.num_buildings_res),
                self._tc(pa.num_buildings_com),
                self._tc(pa.num_buildings_res + pa.num_buildings_com),
                self._tc(pb.num_buildings_res),
                self._tc(pb.num_buildings_com),
                self._tc(pb.num_buildings_res + pb.num_buildings_com),
                self._tc(pa.num_buildings_res + pa.num_buildings_com + pb.num_buildings_res + pb.num_buildings_com),
                self._tc("NO.S"),
            ]
        )
        rows.append(
            [
                self._tc("", 0),
                self._tc("Total Number Of Flats", 0),
                self._tc(pa.total_flats),
                self._tc(0),
                self._tc(pa.total_flats),
                self._tc(pb.total_flats),
                self._tc(0),
                self._tc(pb.total_flats),
                self._tc(tot.get("Total Flats", 0)),
                self._tc("NO.S"),
            ]
        )
        rows.append(
            [
                self._tc("", 0),
                self._tc("Total Residential Building Population", 0),
                self._tc(pa.res_population),
                self._tc(pa.com_population),
                self._tc(pa.total_population),
                self._tc(pb.res_population),
                self._tc(pb.com_population),
                self._tc(pb.total_population),
                self._tc(tot.get("Total Population", 0)),
                self._tc("NO.S"),
            ]
        )

        dry_rows = [
            ("Fresh Water Requirement", pa.res_domestic_lpd, pa.com_domestic_lpd, pb.res_domestic_lpd, pb.com_domestic_lpd),
            ("Flushing Water Requirement", pa.res_flushing_lpd, pa.com_flushing_lpd, pb.res_flushing_lpd, pb.com_flushing_lpd),
            ("Kitchen Water Requirement", pa.kitchen_water_lpd, 0, pb.kitchen_water_lpd, 0),
            ("Landscape Water Requirement", pa.landscape_dry_lpd, 0, pb.landscape_dry_lpd, 0),
            ("Swimming Pool Makeup Water Requirement", pa.swimming_pool_lpd, 0, pb.swimming_pool_lpd, 0),
            ("HVAC Water Requirement", pa.hvac_lpd, 0, pb.hvac_lpd, 0),
            ("Total Water Requirement", pa.dry_total_water_lpd, pa.com_total_lpd + pa.landscape_dry_lpd + pa.swimming_pool_lpd + pa.hvac_lpd + pa.kitchen_water_lpd, pb.dry_total_water_lpd, pb.com_total_lpd + pb.landscape_dry_lpd + pb.swimming_pool_lpd + pb.hvac_lpd + pb.kitchen_water_lpd),
            ("Total Treated Water", pa.dry_treated_water_lpd, 0, pb.dry_treated_water_lpd, 0),
            ("Excess Treated Water To Corporation Line", pa.dry_excess_treated_lpd, 0, pb.dry_excess_treated_lpd, 0),
        ]
        for idx, (desc, a_res, a_com, b_res, b_com) in enumerate(dry_rows, 1):
            a_sub = (a_res if idx <= 2 else 0) + (a_com if idx <= 2 else a_res)
            if idx == 1:
                a_sub = a_res + a_com
            elif idx == 2:
                a_sub = a_res + a_com
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
            if idx <= 6:
                b_sub = b_res + (b_com if idx <= 2 else 0) if idx <= 2 else b_res
            rows.append(
                [
                    self._tc(f"SECTION-7" if idx == 1 else "", 0),
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

        wet_rows = [
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
        for idx, (desc, a_val, a_com) in enumerate(wet_rows, 1):
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
            b_com = pb.com_domestic_lpd if idx == 1 else (pb.com_flushing_lpd if idx == 2 else (pb.com_total_lpd if idx == 7 else 0))
            a_sub = a_val + (a_com if idx <= 2 else 0) if idx <= 2 else a_val
            b_sub = b_val + (b_com if idx <= 2 else 0) if idx <= 2 else b_val
            if idx == 7:
                a_sub = pa.wet_total_water_lpd
                b_sub = pb.wet_total_water_lpd
            rows.append(
                [
                    self._tc(f"SECTION-9" if idx == 1 else "", 0),
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

        ugt_rows = [
            ("DOMESTIC UGT CAPACITY", pa.ugt_domestic_liters, pb.ugt_domestic_liters),
            ("FLUSHING UGT CAPACITY", pa.ugt_flushing_liters, pb.ugt_flushing_liters),
            ("FIRE UGT CAPACITY", pa.fire_tank_liters, pb.fire_tank_liters),
        ]
        for idx, (desc, a_v, b_v) in enumerate(ugt_rows, 1):
            rows.append(
                [
                    self._tc(f"SECTION-10" if idx == 1 else "UGT DETAILS", 0),
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

        stp_rows = [
            ("SEWAGE GENERATION", pa.sewage_lpd, pb.sewage_lpd),
            ("STP Capacity", pa.stp_capacity_kld * 1000, pb.stp_capacity_kld * 1000),
        ]
        for idx, (desc, a_v, b_v) in enumerate(stp_rows, 1):
            rows.append(
                [
                    self._tc("STP DETAILS" if idx == 1 else "", 0),
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

        col_widths = [35, 130, 55, 55, 55, 55, 55, 55, 55, 45]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(self._grid_style())
        story.append(t)
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
        self._build_cover()
        self._build_consolidated()
        for plot in active_plots(self.project.plot_mode):
            self._build_plot_demand(plot)
            self._build_ugt_oht(plot)
            self._build_stp(plot)
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

# ==================== ui/app_state.py ====================




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

    def auto_calculate(self) -> None:
        """Recalculate whenever inputs change (no manual Calculate button)."""
        try:
            self.run_calculations()
        except Exception:
            self.results = None

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



class ScrollablePage(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

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

# ==================== ui/pages/project_page.py ====================



class ProjectPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.entries: dict = {}
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header, text="WATER DEMAND REPORT GENERATOR", font=("Arial", 22, "bold"), text_color="white"
        ).pack(pady=12)
        ctk.CTkLabel(
            header, text="American Edge Engineers Pvt. Ltd.", font=("Arial", 12), text_color=BRAND_ORANGE
        ).pack(pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        fields = [
            ("project_name", "Project Name", "PROPOSED RESIDENTIAL & COMM. AT PUNAVALE"),
            ("client_name", "Client Name", "MR.PRATHMESH GAIKWAD"),
            ("project_location", "Project Location", "PUNAVALE, PUNE"),
            ("project_no", "Project No.", "078"),
        ]
        for i, (key, label, default) in enumerate(fields):
            ctk.CTkLabel(form, text=label, font=("Arial", 14)).grid(row=i, column=0, padx=20, pady=10, sticky="w")
            ent = ctk.CTkEntry(form, width=400)
            val = getattr(self.state.project, key, default)
            ent.insert(0, val or default)
            ent.grid(row=i, column=1, padx=20, pady=10)
            self.entries[key] = ent

        row = len(fields)
        for label, attr, default in [
            ("Engineer Name", "engineer_var", "Akash"),
            ("Prepared By", "prepared_var", "Akash"),
            ("Checked By", "checked_var", "Akash"),
            ("Approved By", "approved_var", "Omkar"),
        ]:
            ctk.CTkLabel(form, text=label, font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
            existing = getattr(self.state.project.revision, label.split()[-1].lower().replace("by", "_by"), None)
            if label == "Engineer Name":
                existing = self.state.project.engineer_name
            elif label == "Prepared By":
                existing = self.state.project.revision.prepared_by
            elif label == "Checked By":
                existing = self.state.project.revision.checked_by
            elif label == "Approved By":
                existing = self.state.project.revision.approved_by
            var = ctk.StringVar(value=existing or default)
            setattr(self, attr, var)
            ctk.CTkComboBox(form, values=list(STAFF_NAMES), variable=var, width=400).grid(
                row=row, column=1, padx=20, pady=10
            )
            row += 1

        ctk.CTkLabel(form, text="Plot Mode", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        plot_label = next(
            (k for k, v in PLOT_MODE_LABELS.items() if v == self.state.project.plot_mode),
            "Plot A + B",
        )
        self.plot_mode_var = ctk.StringVar(value=plot_label)
        ctk.CTkComboBox(
            form, values=list(PLOT_MODE_LABELS.keys()), variable=self.plot_mode_var, width=400
        ).grid(row=row, column=1, padx=20, pady=10)
        row += 1

        ctk.CTkLabel(form, text="Project Type", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        type_label = next(
            (k for k, v in PROJECT_TYPE_LABELS.items() if v == self.state.project.project_type),
            "Mixed Use",
        )
        self.project_type_var = ctk.StringVar(value=type_label)
        ctk.CTkComboBox(
            form, values=list(PROJECT_TYPE_LABELS.keys()), variable=self.project_type_var, width=400
        ).grid(row=row, column=1, padx=20, pady=10)
        row += 1

        ctk.CTkLabel(form, text="Date (Today)", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        self.date_label = ctk.CTkLabel(form, text=datetime.now().strftime("%d-%m-%Y"), font=("Arial", 14))
        self.date_label.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        row += 1

        ctk.CTkLabel(form, text="Revision Details", font=("Arial", 16, "bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 5)
        )
        row += 1
        for key, label, default in [
            ("revision_no", "Rev. No.", "R0"),
            ("description", "Description", "ISSUED FOR REFERENCE"),
        ]:
            ctk.CTkLabel(form, text=label, font=("Arial", 13)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=400)
            val = getattr(self.state.project.revision, key, default)
            ent.insert(0, val or default)
            ent.grid(row=row, column=1, padx=20, pady=8)
            self.entries[key] = ent
            row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(
            btn_frame, text="Next -> Building Details", command=self._save_and_next,
            fg_color=BRAND_ORANGE, hover_color="#D06018", width=220,
        ).pack()

    def _save_and_next(self) -> None:
        try:
            today = datetime.now().strftime("%d-%m-%Y")
            self.state.project.project_name = validate_required(self.entries["project_name"].get(), "Project Name")
            self.state.project.client_name = validate_required(self.entries["client_name"].get(), "Client Name")
            self.state.project.project_location = validate_required(
                self.entries["project_location"].get(), "Project Location"
            )
            self.state.project.engineer_name = validate_required(self.engineer_var.get(), "Engineer Name")
            self.state.project.project_no = self.entries["project_no"].get().strip()
            self.state.project.date = today
            self.state.project.plot_mode = PLOT_MODE_LABELS.get(
                self.plot_mode_var.get(), self.state.project.plot_mode
            )
            self.state.project.project_type = PROJECT_TYPE_LABELS.get(
                self.project_type_var.get(), self.state.project.project_type
            )
            self.state.project.revision = RevisionInfo(
                date=today,
                revision_no=self.entries["revision_no"].get().strip() or "R0",
                description=self.entries["description"].get().strip() or "ISSUED FOR REFERENCE",
                prepared_by=self.prepared_var.get().strip(),
                checked_by=self.checked_var.get().strip(),
                approved_by=self.approved_var.get().strip(),
            )
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        self.date_label.configure(text=datetime.now().strftime("%d-%m-%Y"))

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
        return plot_choices(self.state.project.plot_mode)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if len(self._plot_values()) == 1 else "Plot A + B"
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
        for wing in [
            ResidentialWing(plot="Plot-A", wing="WING - A", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
            ResidentialWing(plot="Plot-A", wing="WING - B", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
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
                plot="Plot-A",
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
        plot_var = ctk.StringVar(value=wing.plot if wing else self._plot_values()[0])
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
            self.state.auto_calculate()

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
            self.state.auto_calculate()

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


    def _duplicate_last(self) -> None:
        if not self.rows:
            self._add_row()
            return
        last = self.rows[-1]
        wing = ResidentialWing(
            plot=last["plot"].get(),
            wing=last["wing"].get() + " (Copy)",
            flats=int(last["flats"].get() or 0),
            pop_per_flat=int(last["pop"].get() or 5),
        )
        self._add_row(wing)

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

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if len(plot_choices(self.state.project.plot_mode)) == 1 else "Plot A + B"
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
            plot="Plot-A",
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

        plot_var = ctk.StringVar(value=unit.plot if unit else plot_choices(self.state.project.plot_mode)[0])
        plot_cb = ctk.CTkComboBox(
            self.table_frame, values=plot_choices(self.state.project.plot_mode), variable=plot_var, width=85
        )
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
            self.state.auto_calculate()

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
            self.state.auto_calculate()

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


    def _duplicate_last(self) -> None:
        if not self.rows:
            self._add_row()
            return
        last = self.rows[-1]
        wing = ResidentialWing(
            plot=last["plot"].get(),
            wing=last["wing"].get() + " (Copy)",
            flats=int(last["flats"].get() or 0),
            pop_per_flat=int(last["pop"].get() or 5),
        )
        self._add_row(wing)

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=3, pady=5)

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
    def __init__(self, master, state: AppState, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_back = on_back
        self.summary_label = None
        self.detail_text = None
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(header, text="Calculations Ready!", font=("Arial", 22, "bold"), text_color="white").pack(pady=12)

        self.summary_label = ctk.CTkLabel(self, text="", font=("Arial", 15, "bold"), justify="center")
        self.summary_label.pack(pady=10)

        self.detail_text = ctk.CTkTextbox(self, height=280, font=("Courier", 11))
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
            self.summary_label.configure(text="No calculations available. Go back and calculate.")
            return
        tot = self.state.results.total
        pa = self.state.results.plots["Plot-A"]
        pb = self.state.results.plots["Plot-B"]
        summary = (
            f"Plot-A STP: {pa.stp_capacity_kld} KLD  |  Plot-B STP: {pb.stp_capacity_kld} KLD\n"
            f"Total Project Demand: {tot.get('Total Water (LPD)', 0):,} LPD "
            f"({tot.get('Total Water (LPD)', 0) / 1000:.2f} KLD)"
        )
        self.summary_label.configure(text=summary)

        lines = ["DETAILED CALCULATION SUMMARY", "=" * 50, ""]
        for plot_name in ("Plot-A", "Plot-B"):
            plot = self.state.results.plots[plot_name]
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
            messagebox.showwarning("No Data", "Please calculate first from the Other Details page.")
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

# ============================================================
# MAIN APPLICATION
# ============================================================

class WaterDemandApp(ctk.CTk):
    NAV = [
        ("Project", "Project Details"), ("Residential", "Residential"), ("Commercial", "Commercial"),
        ("Landscape", "Landscape"), ("Swimming", "Swimming Pool"), ("HVAC", "HVAC"),
        ("UGT", "UGT / Fire Tank"), ("OHT", "OHT Details"), ("STP", "STP Summary"),
        ("Preview", "Preview"), ("Report", "Generate Report"),
        ("RWH", "Rain Water Harvesting"),
        ("Settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.app_state = AppState()
        self.title("American Edge Engineers - Water Demand Report Generator")
        self.geometry("1280x850")
        self.minsize(1100, 700)
        self.configure(fg_color="#F0F2F5")
        init_db()
        self._sidebar()
        self.container = ctk.CTkFrame(self, fg_color="#F0F2F5")
        self.container.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        self.pages = {}
        self._pages()
        self.show("Project")

    def _plots(self) -> list[str]:
        return plot_choices(self.app_state.project.plot_mode)

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        ctk.CTkLabel(sb, text="AMERICAN EDGE\nENGINEERS", font=("Arial", 14, "bold"), text_color=BRAND_ORANGE, justify="center").pack(pady=(20, 5))
        ctk.CTkLabel(sb, text="Water Demand Generator", font=("Arial", 10), text_color="white").pack(pady=(0, 15))
        self.nav_btns = {}
        for k, lbl in self.NAV:
            if k == "Residential" and not show_residential_section(self.app_state.project.project_type):
                continue
            if k == "Commercial" and not show_commercial_section(self.app_state.project.project_type):
                continue
            if k == "HVAC" and not hvac_applicable(self.app_state.project.project_type):
                continue
            b = ctk.CTkButton(sb, text=lbl, height=36, anchor="w", fg_color="transparent", hover_color=BRAND_ORANGE,
                              text_color="white", font=("Arial", 12), command=lambda x=k: self.show(x))
            b.pack(fill="x", padx=8, pady=2)
            self.nav_btns[k] = b
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self._new).pack(side="bottom", fill="x", padx=10, pady=(4, 15))

    def _pages(self):
        self.pages["Project"] = ProjectPage(self.container, self.app_state, on_next=self._next_from_project)
        self.pages["Residential"] = ResidentialPage(self.container, self.app_state, on_next=self._next_from_residential, on_back=lambda: self.show("Project"))
        self.pages["Commercial"] = CommercialPage(self.container, self.app_state, on_next=lambda: self.show("Landscape"), on_back=self._back_from_commercial)
        self.pages["Landscape"] = self._form_page("Landscape (NBC-2026)", self._landscape_ui)
        self.pages["Swimming"] = self._form_page("Swimming Pool", self._pool_ui)
        if hvac_applicable(self.app_state.project.project_type):
            self.pages["HVAC"] = self._form_page("HVAC Water", self._hvac_ui)
        self.pages["UGT"] = self._form_page("UGT / Fire Tank", self._ugt_ui)
        self.pages["Report"] = FinalPage(self.container, self.app_state, on_back=lambda: self.show("Preview"))
        self.pages["STP"] = self._stp_page()
        self.pages["Preview"] = self._preview_page()
        try:
            init_rwh_db()
            self.pages["RWH"] = RWHPage(
                self.container,
                seed_project=self.app_state.project,
                on_back=lambda: self.show("Report"),
            )
        except Exception:
            pass
        self.pages["Settings"] = self._settings_page()
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

    def _form_page(self, title, builder):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        builder(f)
        return f

    def _landscape_ui(self, p):
        self._le = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(self.app_state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._le[plot] = e
        ctk.CTkLabel(p, text="Auto: 6 L/sq.m/day per NBC-2026", font=("Arial", 11, "italic")).pack()
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=self._save_landscape).pack(pady=12)

    def _save_landscape(self):
        try:
            for plot, e in self._le.items():
                self.app_state.other.landscape_area[plot] = validate_positive_float(e.get(), f"Landscape {plot}")
            self.show("Swimming")
        except ValidationError as ex:
            messagebox.showerror("Error", ex.message)

    def _pool_ui(self, p):
        self._pe = {}
        self._pool_status = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Swimming Pool {plot}", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            status = self.app_state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
            if self.app_state.other.swimming_pool_na.get(plot, False):
                status = POOL_NOT_APPLICABLE
            label = next((k for k, v in POOL_STATUS_LABELS.items() if v == status), "Not Applicable")
            status_var = ctk.StringVar(value=label)
            ctk.CTkComboBox(form, values=list(POOL_STATUS_LABELS.keys()), variable=status_var, width=160).grid(
                row=i, column=1, padx=10, pady=8, sticky="w"
            )
            self._pool_status[plot] = status_var
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            e.grid(row=i, column=2, padx=10, pady=8)
            self._pe[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=self._save_pool).pack(pady=12)

    def _save_pool(self):
        for plot in self._plots():
            status = POOL_STATUS_LABELS.get(self._pool_status[plot].get(), POOL_NOT_APPLICABLE)
            self.app_state.other.swimming_pool_status[plot] = status
            self.app_state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
            if status == POOL_NOT_APPLICABLE:
                self.app_state.other.swimming_pool[plot] = 0.0
            else:
                self.app_state.other.swimming_pool[plot] = float(self._pe[plot].get() or 0)
        self.app_state.auto_calculate()
        next_page = "HVAC" if hvac_applicable(self.app_state.project.project_type) else "UGT"
        self.show(next_page)

    def _hvac_ui(self, p):
        self._he = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._he[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=lambda: (self._save_dict(self._he, self.app_state.other.hvac_water), self.show("UGT"))).pack(pady=12)

    def _ugt_ui(self, p):
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Fire Tank {plot} (litres)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            auto_val = self._auto_fire_tank(plot)
            ctk.CTkLabel(form, text=f"{auto_val:,} (auto from NBC height table)", font=("Arial", 12)).grid(
                row=i, column=1, padx=10, pady=8, sticky="w"
            )
            self.app_state.other.fire_tank[plot] = float(auto_val)
        ctk.CTkLabel(p, text="UGT: Domestic 2-day, Flushing 1-day storage (auto-calculated)", font=("Arial", 11, "italic")).pack(pady=5)
        ctk.CTkButton(p, text="Save & Go to OHT", fg_color=BRAND_ORANGE, command=lambda: self.show("OHT")).pack(pady=12)

    def _save_dict(self, entries, target):
        for plot, e in entries.items():
            target[plot] = float(e.get() or 0)

    def _stp_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="STP Summary", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.stp_box = ctk.CTkTextbox(f, height=400, font=("Courier", 11))
        self.stp_box.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkButton(f, text="Calculate STP", fg_color=BRAND_ORANGE, command=self._refresh_stp).pack(pady=10)
        return f

    def _refresh_stp(self):
        self._calc()
        if not self.app_state.results:
            return
        lines = []
        for pn in self._plots():
            pl = self.app_state.results.plots[pn]
            lines.append(f"=== {pn} ===")
            for s in pl.stp_sections:
                lines.append(
                    f"  {s.scope}: Water {s.total_water_lpd:,} | Sewage {s.sewage_lpd:,} | "
                    f"Say {s.say_stp_kld} KLD | Treated {s.treated_water_lpd:,} | Excess {s.excess_treated_lpd:,}"
                )
            lines.append(f"  Total STP: {pl.stp_capacity_kld} KLD\n")
        self.stp_box.delete("1.0", "end")
        self.stp_box.insert("1.0", "\n".join(lines))

    def _preview_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="Report Preview (8 Pages)", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkButton(f, text="Calculate & Open Preview", fg_color="#8E44AD", height=42, command=self._open_preview).pack(pady=20)
        ctk.CTkButton(f, text="Go to Generate Report", fg_color=BRAND_ORANGE, height=38, command=lambda: (self._calc(), self.show("Report"))).pack(pady=8)
        return f

    def _settings_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="Settings", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            f,
            text=f"Database: {DB_PATH}\nLogo: {LOGO_PATH}\n\nNBC-2026 Standards:\nResidential 105+30 LPCD\nLandscape 6 L/sq.m\nSTP 90% sewage",
            font=("Arial", 12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=10)
        ctk.CTkButton(f, text="Export JSON", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(f, text="Import JSON", command=self._imp_json).pack(pady=8)
        return f

    def _auto_fire_tank(self, plot: str) -> int:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.app_state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return fire_tank_capacity_liters(max_height, btype)
        return int(self.app_state.other.fire_tank.get(plot, 0))

    def _next_from_project(self):
        ptype = self.app_state.project.project_type
        if show_residential_section(ptype):
            self.show("Residential")
        elif show_commercial_section(ptype):
            self.show("Commercial")
        else:
            self.show("Landscape")

    def _next_from_residential(self):
        if show_commercial_section(self.app_state.project.project_type):
            self.show("Commercial")
        else:
            self.show("Landscape")

    def _back_from_commercial(self):
        if show_residential_section(self.app_state.project.project_type):
            self.show("Residential")
        else:
            self.show("Project")

    def show(self, name):
        if name == "HVAC" and not hvac_applicable(self.app_state.project.project_type):
            self.show("UGT")
            return
        if name == "Residential" and not show_residential_section(self.app_state.project.project_type):
            self.show("Commercial" if show_commercial_section(self.app_state.project.project_type) else "Landscape")
            return
        if name == "Commercial" and not show_commercial_section(self.app_state.project.project_type):
            self.show("Residential" if show_residential_section(self.app_state.project.project_type) else "Landscape")
            return
        self.pages[name].tkraise()
        if hasattr(self.pages[name], "refresh"):
            self.pages[name].refresh()
        for k, b in self.nav_btns.items():
            b.configure(fg_color=BRAND_ORANGE if k == name else "transparent")

    def _calc(self):
        try:
            self.app_state.auto_calculate()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _open_preview(self):
        self._calc()
        if self.app_state.results:
            PreviewDialog(self, self.app_state.project, self.app_state.results, on_export_pdf=lambda: self.pages["Report"]._export_pdf())

    def _new(self):
        if messagebox.askyesno("New", "Start new project?"):
            self.app_state = AppState()
            for p in self.pages.values():
                p.destroy()
            self._pages()
            self.show("Project")

    def _save_db(self):
        try:
            self._calc()
            save_project(
                self.app_state.project,
                self.app_state.residential,
                self.app_state.commercial,
                self.app_state.other,
                self.app_state.results.to_dict() if self.app_state.results else None,
            )
            messagebox.showinfo("Saved", "Project saved to database.")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _open_db(self):
        projs = list_projects()
        if not projs:
            messagebox.showinfo("DB", "No projects.")
            return
        d = ctk.CTkToplevel(self)
        d.title("Recent Projects")
        d.geometry("520x420")
        d.transient(self)
        d.grab_set()
        ctk.CTkLabel(d, text="Select Project", font=("Arial", 15, "bold")).pack(pady=8)
        sf = ctk.CTkScrollableFrame(d, width=480, height=300)
        sf.pack(padx=10)
        sel = ctk.StringVar()
        for p in projs:
            ctk.CTkRadioButton(
                sf,
                text=f"{p['project_name']} | {p['client_name']} | {p['date']}",
                variable=sel,
                value=p["project_id"],
            ).pack(anchor="w", padx=8, pady=3)

        def go():
            pid = sel.get()
            if not pid:
                return
            data = load_project_from_db(pid)
            proj, res, com, oth, _ = parse_project_snapshot(data)
            self.app_state.project = proj
            self.app_state.residential = res
            self.app_state.commercial = com
            self.app_state.other = oth
            self.app_state.run_calculations()
            d.destroy()
            messagebox.showinfo("Loaded", "Project loaded.")

        ctk.CTkButton(d, text="Load", fg_color=BRAND_ORANGE, command=go).pack(pady=10)

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


def main():
    WaterDemandApp().mainloop()


if __name__ == "__main__":
    main()
