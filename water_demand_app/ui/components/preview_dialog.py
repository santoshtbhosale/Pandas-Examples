from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Dict, List, Optional

from models.calculations import CalculationResults
from models.project import ProjectData


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
