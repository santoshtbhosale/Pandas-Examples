"""Regression tests for PDF Page 2 consolidated statement layout."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from typing import Any, List

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config.nbc_2026 import PROJECT_TYPE_RESIDENTIAL
from models.calculations import CalculationResults, PlotResults
from models.project import ProjectData
from reportlab.platypus import KeepTogether, Table
from services.pdf_exporter import PDFExporter, export_pdf


def _reference_results() -> CalculationResults:
    plot_a = PlotResults(
        plot="Plot-A",
        res_population=2835,
        com_population=0,
        stp_capacity_kld=370.0,
        dry_total_water_lpd=500000,
    )
    plot_b = PlotResults(plot="Plot-B")
    return CalculationResults(
        plots={"Plot-A": plot_a, "Plot-B": plot_b},
        total={
            "Total Residential Population": 2835,
            "Total Commercial Population": 0,
            "Total STP Capacity (KLD)": 370.0,
            "Total Water (LPD)": 500000,
            "Total Population": 2835,
        },
    )


def _count_tables(story: List[Any]) -> int:
    count = 0
    for item in story:
        if isinstance(item, Table):
            count += 1
        elif isinstance(item, KeepTogether):
            count += _count_tables(item._content)
    return count


def _extract_pdf_text(pdf_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore[no-redef]

    reader = PdfReader(pdf_path)
    return "".join((page.extract_text() or "") for page in reader.pages)


def _extract_page_text(pdf_path: str, page_index: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore[no-redef]

    reader = PdfReader(pdf_path)
    return reader.pages[page_index].extract_text() or ""


class TestPDFConsolidatedLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectData(
            project_name="LAYOUT TEST",
            project_type=PROJECT_TYPE_RESIDENTIAL,
            engineer_name="Test Engineer",
        )
        self.results = _reference_results()

    def test_consolidated_story_uses_separate_tables(self) -> None:
        exporter = PDFExporter(self.project, self.results)
        story = exporter._build_consolidated()
        self.assertGreaterEqual(_count_tables(story), 6)

    def test_consolidated_headings_and_no_section_seven(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            out_path = tmp.name
        try:
            export_pdf(out_path, self.project, self.results)
            pdf_text = _extract_pdf_text(out_path).upper()
            page2 = _extract_page_text(out_path, 1).upper()

            self.assertIn("CONSOLIDATED STATEMENT", pdf_text)
            self.assertIn("SECTION-8", pdf_text)
            self.assertIn("BUILDING / POPULATION DETAILS", pdf_text)
            self.assertIn("DRY SEASON", pdf_text)
            self.assertIn("WET SEASON", pdf_text)
            self.assertIn("SECTION-9", pdf_text)
            self.assertIn("UGT DETAILS", pdf_text)
            self.assertIn("SECTION-10", pdf_text)
            self.assertIn("STP DETAILS", pdf_text)
            self.assertNotIn("SECTION-7", pdf_text)
            self.assertNotIn("RWH", pdf_text)
            self.assertNotIn("RAIN WATER", pdf_text)

            self.assertIn("SECTION-8", page2)
            self.assertIn("DRY SEASON", page2)
            self.assertIn("WET SEASON", page2)
            self.assertNotIn("SECTION-7", page2)
        finally:
            if os.path.isfile(out_path):
                os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
