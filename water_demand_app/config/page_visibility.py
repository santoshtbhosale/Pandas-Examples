"""Navigation and section visibility by project type."""

from __future__ import annotations

from typing import FrozenSet, Tuple

from config.nbc_2026 import (
    PROJECT_TYPE_COLLEGE,
    PROJECT_TYPE_COMMERCIAL,
    PROJECT_TYPE_HOSPITAL,
    PROJECT_TYPE_HOTEL,
    PROJECT_TYPE_INDUSTRIAL,
    PROJECT_TYPE_IT_PARK,
    PROJECT_TYPE_MALL,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
    PROJECT_TYPE_SCHOOL,
    PROJECT_TYPE_TOWNSHIP,
    PROJECT_TYPE_WAREHOUSE,
)

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
    "OHT",
    "STP",
    "Preview",
    "Report",
    "RWH",
    "Settings",
)

_COMMON_TAIL: FrozenSet[str] = frozenset(
    {"Landscape", "UGT", "OHT", "STP", "Preview", "Report", "RWH", "Settings"}
)

_PAGES_BY_TYPE: dict[str, FrozenSet[str]] = {
    PROJECT_TYPE_RESIDENTIAL: frozenset({"Project", "Residential", *_COMMON_TAIL}),
    PROJECT_TYPE_COMMERCIAL: frozenset({"Project", "Commercial", "HVAC", *_COMMON_TAIL}),
    PROJECT_TYPE_MIXED: frozenset(
        {"Project", "Residential", "Commercial", "Swimming", "HVAC", *_COMMON_TAIL}
    ),
    PROJECT_TYPE_HOSPITAL: frozenset({"Project", "Hospital", *_COMMON_TAIL}),
    PROJECT_TYPE_HOTEL: frozenset({"Project", "Hotel", "Swimming", *_COMMON_TAIL}),
    PROJECT_TYPE_SCHOOL: frozenset({"Project", "Commercial", "Landscape", "UGT", "OHT", "STP", "Preview", "Report", "RWH", "Settings"}),
    PROJECT_TYPE_COLLEGE: frozenset({"Project", "Commercial", "Landscape", "UGT", "OHT", "STP", "Preview", "Report", "RWH", "Settings"}),
    PROJECT_TYPE_IT_PARK: frozenset({"Project", "Commercial", "HVAC", *_COMMON_TAIL}),
    PROJECT_TYPE_MALL: frozenset({"Project", "Commercial", "HVAC", "FoodCourt", *_COMMON_TAIL}),
    PROJECT_TYPE_INDUSTRIAL: frozenset({"Project", "Commercial", *_COMMON_TAIL}),
    PROJECT_TYPE_WAREHOUSE: frozenset({"Project", "Commercial", *_COMMON_TAIL}),
    PROJECT_TYPE_TOWNSHIP: frozenset(
        {"Project", "Residential", "Commercial", "Swimming", "HVAC", *_COMMON_TAIL}
    ),
}


def visible_pages(project_type: str) -> FrozenSet[str]:
    return _PAGES_BY_TYPE.get(project_type, _PAGES_BY_TYPE[PROJECT_TYPE_MIXED])


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
    for key in WIZARD_PAGE_ORDER:
        if key == "Project":
            continue
        if key in visible_pages(project_type):
            return key
    return "Preview"
