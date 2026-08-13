from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.nbc_2026 import (
    BRAND_DARK_GRAY,
    BRAND_DEMAND_ORANGE,
    BRAND_HEADER_GRAY,
    BRAND_STP_PURPLE,
    BRAND_UGT_TEAL,
    COMPANY_ADDRESS,
    COMPANY_CONTACT,
    COMPANY_FOOTER,
    COMPANY_NAME,
)
from models.calculations import CalculationResults, PlotResults
from models.project import ProjectData


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
        base = os.path.dirname(os.path.dirname(__file__))
        for name in ("logo.png", "logo.jpg"):
            path = os.path.join(base, "assets", name)
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
        from services.environmental_calculator import calculate_environmental
        from services.result_tables import (
            build_sewage_generation_table_sections,
            build_solid_waste_table_sections,
        )

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
