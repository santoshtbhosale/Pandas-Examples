from __future__ import annotations

import os
import shutil
from typing import Any, Dict, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config.nbc_2026 import BRAND_DARK_GRAY, BRAND_NAVY, BRAND_ORANGE, COMPANY_NAME, active_plots, hvac_applicable
from models.calculations import CalculationResults
from models.project import ProjectData


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


        self._auto_width(ws)


TEMPLATE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "templates", "WaterDemand_Template.xlsx")
)


class TemplateExcelExporter:
    """Populate the master Excel template without altering formatting."""

    def __init__(self, project: ProjectData, results: CalculationResults) -> None:
        self.project = project
        self.results = results

    def export(self, file_path: str) -> None:
        shutil.copy2(TEMPLATE_PATH, file_path)
        wb = load_workbook(file_path)
        self._populate_cover(wb)
        self._populate_consolidated(wb)
        for plot in active_plots(self.project.plot_mode):
            self._populate_plot_sheets(wb, plot)
        self._populate_summary(wb)
        wb.save(file_path)

    def _set(self, ws, cell: str, value: Any) -> None:
        ws[cell] = value

    def _populate_cover(self, wb) -> None:
        ws = wb["Cover"] if "Cover" in wb.sheetnames else wb.active
        rev = self.project.revision
        mapping = {
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
        for cell, val in mapping.items():
            try:
                self._set(ws, cell, val)
            except Exception:
                pass

    def _populate_consolidated(self, wb) -> None:
        if "Consolidated" not in wb.sheetnames:
            return
        ws = wb["Consolidated"]
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        tot = self.results.total
        rows = [
            (4, pa.num_buildings_res, pa.num_buildings_com, pa.num_buildings_res + pa.num_buildings_com,
             pb.num_buildings_res, pb.num_buildings_com, pb.num_buildings_res + pb.num_buildings_com,
             pa.num_buildings_res + pa.num_buildings_com + pb.num_buildings_res + pb.num_buildings_com),
            (5, pa.total_flats, 0, pa.total_flats, pb.total_flats, 0, pb.total_flats, tot.get("Total Flats", 0)),
            (6, pa.res_population, pa.com_population, pa.total_population,
             pb.res_population, pb.com_population, pb.total_population, tot.get("Total Population", 0)),
            (7, pa.res_total_lpd + pa.com_total_lpd, 0, pa.dry_total_water_lpd,
             pb.res_total_lpd + pb.com_total_lpd, 0, pb.dry_total_water_lpd, tot.get("Total Water (LPD)", 0)),
            (8, pa.stp_capacity_kld, 0, pa.stp_capacity_kld,
             pb.stp_capacity_kld, 0, pb.stp_capacity_kld, tot.get("Total STP Capacity (KLD)", 0)),
        ]
        for row, c, d, e, f, g, h, i in rows:
            for col, val in zip("CDEFGHI", (c, d, e, f, g, h, i)):
                try:
                    self._set(ws, f"{col}{row}", val)
                except Exception:
                    pass

    def _populate_plot_sheets(self, wb, plot_name: str) -> None:
        plot = self.results.plots[plot_name]
        demand_name = f"{plot_name} Demand"
        if demand_name in wb.sheetnames:
            ws = wb[demand_name]
            row = 5
            for idx, w in enumerate(plot.residential_wings, 1):
                try:
                    self._set(ws, f"A{row}", idx)
                    self._set(ws, f"B{row}", w.wing)
                    self._set(ws, f"C{row}", w.flats)
                    self._set(ws, f"E{row}", w.population)
                    self._set(ws, f"F{row}", w.domestic_lpd)
                    self._set(ws, f"G{row}", w.flushing_lpd)
                    self._set(ws, f"H{row}", w.kitchen_water_lpd)
                    self._set(ws, f"I{row}", w.total_lpd)
                    row += 1
                except Exception:
                    pass
            try:
                self._set(ws, f"E{row}", plot.res_population)
                self._set(ws, f"F{row}", plot.res_domestic_lpd)
                self._set(ws, f"G{row}", plot.res_flushing_lpd)
                self._set(ws, f"H{row}", plot.kitchen_water_lpd)
                self._set(ws, f"I{row}", plot.res_total_lpd)
            except Exception:
                pass

        ugt_name = f"{plot_name} UGT-OHT"
        if ugt_name in wb.sheetnames:
            ws = wb[ugt_name]
            row = 4
            for idx, sec in enumerate(plot.ugt_sections, 1):
                try:
                    self._set(ws, f"A{row}", idx)
                    self._set(ws, f"B{row}", sec.description)
                    self._set(ws, f"C{row}", sec.water_requirement_lpd)
                    self._set(ws, f"D{row}", sec.storage_days)
                    self._set(ws, f"E{row}", sec.total_storage_liters)
                    self._set(ws, f"F{row}", sec.total_storage_kld)
                    row += 1
                except Exception:
                    pass
            try:
                self._set(ws, f"B{row + 2}", plot.fire_tank_liters)
            except Exception:
                pass

        stp_name = f"{plot_name} STP"
        if stp_name in wb.sheetnames:
            ws = wb[stp_name]
            row = 4
            for stp in plot.stp_sections:
                try:
                    self._set(ws, f"A{row}", 1)
                    self._set(ws, f"B{row}", "Total Water Requirement")
                    self._set(ws, f"C{row}", stp.total_water_lpd)
                    row += 1
                    self._set(ws, f"A{row}", 2)
                    self._set(ws, f"B{row}", "Say STP Capacity")
                    self._set(ws, f"C{row}", stp.say_stp_kld)
                    row += 3
                except Exception:
                    pass

    def _populate_summary(self, wb) -> None:
        if "Summary" not in wb.sheetnames:
            return
        ws = wb["Summary"]
        tot = self.results.total
        pa = self.results.plots["Plot-A"]
        pb = self.results.plots["Plot-B"]
        mapping = {
            "B3": self.project.project_name,
            "B4": self.project.client_name,
            "B5": self.project.project_location,
            "B6": self.project.engineer_name,
            "B7": self.project.date,
            "B9": pa.stp_capacity_kld,
            "B10": pb.stp_capacity_kld,
            "B11": tot.get("Total Water (LPD)", 0),
            "B12": tot.get("Total STP Capacity (KLD)", 0),
            "B13": tot.get("Total Population", 0),
            "B14": tot.get("Total Flats", 0),
        }
        for cell, val in mapping.items():
            try:
                self._set(ws, cell, val)
            except Exception:
                pass


def export_excel(file_path: str, project: ProjectData, results: CalculationResults) -> None:
    if os.path.isfile(TEMPLATE_PATH):
        TemplateExcelExporter(project, results).export(file_path)
    else:
        ExcelExporter(project, results).export(file_path)
