"""Centralized UI design tokens for American Edge Engineers."""

from __future__ import annotations

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    COMPANY_NAME,
)

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
