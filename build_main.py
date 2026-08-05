#!/usr/bin/env python3
"""Build single-file main.py from water_demand_app modules."""
import ast
import os

BASE = "water_demand_app"
OUT = "main.py"

HEADER = '''#!/usr/bin/env python3
"""
American Edge Engineers - Water Demand Report Generator
Single-file production application with NBC-2026 calculations.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
from tkcalendar import DateEntry
from openpyxl import Workbook
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

'''


def remove_imports(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    remove = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for i in range(node.lineno - 1, node.end_lineno):
                remove.add(i)
    return "".join(line for i, line in enumerate(lines) if i not in remove)


def patch_source(src: str) -> str:
    src = src.replace('os.path.dirname(os.path.dirname(__file__))', "APP_DIR")
    src = src.replace('os.path.join(base, "assets", name)', 'os.path.join(base, name)')
    src = src.replace(
        'os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "water_demand.db")',
        "DB_PATH",
    )
    src = src.replace(
        'os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")',
        "LOGO_PATH",
    )
    return src


FILES = [
    "config/nbc_2026.py",
    "models/project.py",
    "models/residential.py",
    "models/commercial.py",
    "models/other_details.py",
    "models/calculations.py",
    "services/calculator.py",
    "services/database.py",
    "services/pdf_exporter.py",
    "services/excel_exporter.py",
    "ui/components/validation.py",
    "ui/app_state.py",
    "ui/components/scrollable_frame.py",
    "ui/components/preview_dialog.py",
    "ui/pages/project_page.py",
    "ui/pages/residential_page.py",
    "ui/pages/commercial_page.py",
    "ui/pages/other_page.py",
    "ui/pages/final_page.py",
    "_app_sidebar.py",
]

# Extend NBC commercial types before build
nbc_path = os.path.join(BASE, "config/nbc_2026.py")
with open(nbc_path) as f:
    nbc = f.read()
if "Hospital" not in nbc:
    extra = '''
    "Hospital": CommercialTypeSpec("Hospital", 15.0, 340, 110),
    "School": CommercialTypeSpec("School", 10.0, 25, 20),
    "Mall": CommercialTypeSpec("Mall", 5.0, 25, 20),
    "Custom": CommercialTypeSpec("Custom", 10.0, 25, 20),
'''
    nbc = nbc.replace('"Shop": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),', '"Shop": CommercialTypeSpec("Shop - Ground Floor", 3.0, 25, 20),' + extra)
    with open(nbc_path, "w") as f:
        f.write(nbc)

parts = [HEADER]
for rel in FILES:
    path = os.path.join(BASE, rel)
    with open(path) as f:
        src = patch_source(remove_imports(f.read()))
    parts.append(f"\n# {'='*20} {rel} {'='*20}\n")
    parts.append(src)

content = "".join(parts)

# Post-process: add duplicate wing only to residential page (once)
if "class ResidentialPage" in content and content.count("def _duplicate_last") == 0:
    content = content.replace(
        'ctk.CTkButton(btn_frame, text="+ Add Bungalow", command=self._add_bungalow, fg_color="#2980B9").grid(row=0, column=1, padx=10)',
        'ctk.CTkButton(btn_frame, text="+ Add Bungalow", command=self._add_bungalow, fg_color="#2980B9").grid(row=0, column=1, padx=10)\n'
        '        ctk.CTkButton(btn_frame, text="Duplicate Wing", command=self._duplicate_last, fg_color="#8E44AD").grid(row=0, column=4, padx=10)',
    )
    dup_method = '''
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

'''
    content = content.replace("    def _regrid(self) -> None:", dup_method + "    def _regrid(self) -> None:")

with open(OUT, "w") as f:
    f.write(content)

print(f"Built {OUT}: {len(content.splitlines())} lines")
