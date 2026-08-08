"""ReportLab PDF exporter for Rain Water Harvesting reports."""

from __future__ import annotations

import os
from typing import Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from rwh.config import RWH_BRAND_NAVY, RWH_BRAND_ORANGE, RWH_HEADER_TEAL
from rwh.models import RWHProjectData, RWHResults

COMPANY_NAME = "AMERICAN EDGE ENGINEERS PVT. LTD."
COMPANY_FOOTER = (
    "American Edge Engineers Pvt. Ltd. | Austin | New York | Pune | Info@americanedgeee.com"
)


class RWHPDFExporter:
    def __init__(
        self,
        project: RWHProjectData,
        results: RWHResults,
        logo_path: Optional[str] = None,
    ) -> None:
        self.project = project
        self.results = results
        self.logo_path = logo_path
        self.styles = getSampleStyleSheet()
        self.page_width = A4[0] - 60

    def export(self, file_path: str) -> None:
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=40,
            bottomMargin=36,
        )
        story: List[Any] = []
        story.extend(self._build_header())
        story.append(Spacer(1, 12))
        story.extend(self._build_meta())
        story.append(Spacer(1, 10))
        story.extend(self._build_climate())
        story.append(Spacer(1, 10))
        story.extend(self._build_surfaces())
        story.append(Spacer(1, 10))
        story.extend(self._build_summary())
        if self.project.notes.strip():
            story.append(Spacer(1, 8))
            story.append(self._p(f"<b>Notes:</b> {self.project.notes}", size=8))
        story.append(Spacer(1, 12))
        story.append(
            self._p(
                "<i>Formula: Annual Harvest (L) = Catchment Area (m²) × Annual Rainfall (mm) "
                "× Runoff Coefficient × Collection Efficiency</i>",
                size=7,
            )
        )
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 6)
        canvas.drawCentredString(A4[0] / 2, 16, COMPANY_FOOTER)
        canvas.restoreState()

    def _p(self, text: str, size: float = 9, bold: bool = False, align: int = 0, color=colors.black):
        style = ParagraphStyle(
            f"RWH_{size}_{bold}_{align}",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            leading=size + 2,
            alignment=align,
            textColor=color,
        )
        return Paragraph(text, style)

    def _build_header(self) -> List[Any]:
        items: List[Any] = []
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = Image(self.logo_path, width=1.8 * inch, height=0.75 * inch)
                img.hAlign = "LEFT"
                items.append(img)
            except Exception:
                pass
        title = Table(
            [[self._p("<b>RAIN WATER HARVESTING REPORT</b>", size=14, bold=True, align=1, color=colors.white)]],
            colWidths=[self.page_width],
            rowHeights=[28],
        )
        title.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(RWH_HEADER_TEAL)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                ]
            )
        )
        items.append(Spacer(1, 6))
        items.append(title)
        items.append(self._p(f"<b>{COMPANY_NAME}</b>", size=9, bold=True, align=1))
        return items

    def _build_meta(self) -> List[Any]:
        p = self.project
        rows = [
            [self._p("<b>TITLE</b>", size=8), self._p(": RAIN WATER HARVESTING", size=8)],
            [self._p("<b>PROJECT NAME</b>", size=8), self._p(f": {p.project_name.upper()}", size=8)],
            [self._p("<b>CLIENT NAME</b>", size=8), self._p(f": {p.client_name.upper()}", size=8)],
            [self._p("<b>PROJECT LOCATION</b>", size=8), self._p(f": {p.project_location.upper()}", size=8)],
            [self._p("<b>PROJECT NO.</b>", size=8), self._p(f": {p.project_no}", size=8)],
            [self._p("<b>ENGINEER</b>", size=8), self._p(f": MR.{p.engineer_name.upper()}", size=8)],
            [self._p("<b>DATE</b>", size=8), self._p(f": {p.date}", size=8)],
        ]
        t = Table(rows, colWidths=[130, self.page_width - 130])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECF0F1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return [t]

    def _build_climate(self) -> List[Any]:
        p = self.project
        header = self._p("<b>CLIMATE & SYSTEM PARAMETERS</b>", size=9, bold=True, align=1, color=colors.white)
        bar = Table([[header]], colWidths=[self.page_width], rowHeights=[18])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(RWH_BRAND_NAVY)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        rows = [
            [
                self._p("<b>Parameter</b>", size=8, bold=True, align=1),
                self._p("<b>Value</b>", size=8, bold=True, align=1),
                self._p("<b>Unit</b>", size=8, bold=True, align=1),
            ],
            [self._p("Annual Rainfall", size=8), self._p(f"{p.annual_rainfall_mm:.1f}", size=8, align=1), self._p("mm", size=8, align=1)],
            [self._p("No. of Rainy Days", size=8), self._p(str(p.rainy_days), size=8, align=1), self._p("days", size=8, align=1)],
            [self._p("Max Daily Rainfall", size=8), self._p(f"{p.max_daily_rainfall_mm:.1f}", size=8, align=1), self._p("mm", size=8, align=1)],
            [self._p("Collection Efficiency", size=8), self._p(f"{p.collection_efficiency * 100:.0f}", size=8, align=1), self._p("%", size=8, align=1)],
        ]
        t = Table(rows, colWidths=[220, 120, 80])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D5F5E3")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return [bar, Spacer(1, 4), t]

    def _build_surfaces(self) -> List[Any]:
        header = self._p("<b>CATCHMENT SURFACE BREAKDOWN</b>", size=9, bold=True, align=1, color=colors.white)
        bar = Table([[header]], colWidths=[self.page_width], rowHeights=[18])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(RWH_BRAND_ORANGE)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        rows = [
            [
                self._p("<b>Sr</b>", size=7, bold=True, align=1),
                self._p("<b>Surface / Label</b>", size=7, bold=True, align=1),
                self._p("<b>Type</b>", size=7, bold=True, align=1),
                self._p("<b>Area (m²)</b>", size=7, bold=True, align=1),
                self._p("<b>Coeff (K)</b>", size=7, bold=True, align=1),
                self._p("<b>Annual (L)</b>", size=7, bold=True, align=1),
                self._p("<b>Peak Day (L)</b>", size=7, bold=True, align=1),
            ]
        ]
        for i, s in enumerate(self.results.surfaces, 1):
            rows.append(
                [
                    self._p(str(i), size=7, align=1),
                    self._p(s.label, size=7),
                    self._p(s.surface_type, size=7),
                    self._p(f"{s.area_sqm:.1f}", size=7, align=1),
                    self._p(f"{s.runoff_coefficient:.2f}", size=7, align=1),
                    self._p(f"{s.annual_harvest_liters:,.0f}", size=7, align=1),
                    self._p(f"{s.peak_day_liters:,.0f}", size=7, align=1),
                ]
            )
        t = Table(rows, colWidths=[28, 120, 90, 70, 60, 80, 80])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FDEBD0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return [bar, Spacer(1, 4), t]

    def _build_summary(self) -> List[Any]:
        r = self.results
        header = self._p("<b>HARVESTING SUMMARY</b>", size=9, bold=True, align=1, color=colors.white)
        bar = Table([[header]], colWidths=[self.page_width], rowHeights=[18])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(RWH_HEADER_TEAL)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        rows = [
            [self._p("<b>Description</b>", size=8, bold=True), self._p("<b>Value</b>", size=8, bold=True, align=1), self._p("<b>Unit</b>", size=8, bold=True, align=1)],
            [self._p("Total Catchment Area", size=8), self._p(f"{r.total_catchment_sqm:,.1f}", size=8, align=1), self._p("m²", size=8, align=1)],
            [self._p("Annual Harvestable Water", size=8), self._p(f"{r.annual_harvest_liters:,.0f}", size=8, align=1), self._p("Litres", size=8, align=1)],
            [self._p("Annual Harvestable Water", size=8), self._p(f"{r.annual_harvest_cum:,.2f}", size=8, align=1), self._p("m³ / KL", size=8, align=1)],
            [self._p("Daily Average Availability", size=8), self._p(f"{r.daily_average_liters:,.1f}", size=8, align=1), self._p("Litres/day", size=8, align=1)],
            [self._p("Peak Day Harvest Potential", size=8), self._p(f"{r.peak_day_liters:,.0f}", size=8, align=1), self._p("Litres", size=8, align=1)],
            [self._p("Recommended Tank Capacity", size=8), self._p(f"{r.recommended_tank_liters:,.0f}", size=8, align=1), self._p("Litres", size=8, align=1)],
            [self._p("<b>Design Tank Capacity</b>", size=8, bold=True), self._p(f"<b>{r.design_tank_liters:,.0f}</b>", size=8, bold=True, align=1), self._p("Litres", size=8, align=1)],
        ]
        t = Table(rows, colWidths=[260, 120, 90])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D5F5E3")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D5F5E3")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return [bar, Spacer(1, 4), t]


def export_rwh_pdf(
    file_path: str,
    project: RWHProjectData,
    results: RWHResults,
    logo_path: Optional[str] = None,
) -> None:
    RWHPDFExporter(project, results, logo_path).export(file_path)
