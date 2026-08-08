"""Shared table row builders for OHT, STP, and Preview — single source of truth for GUI/PDF/Excel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from config.nbc_2026 import (
    hvac_applicable,
    project_type_label,
    show_swimming_section,
)
from config.page_visibility import visible_pages
from models.calculations import CalculationResults, PlotResults
from models.other_details import OtherDetails
from models.project import ProjectData

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


def build_preview_table_sections(
    project: ProjectData,
    results: CalculationResults,
    plot_names: Sequence[str],
    other: Optional[OtherDetails] = None,
    rwh_summary: Optional[Sequence[TableRow]] = None,
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

    if "STP" in pages:
        sewage_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot and plot.sewage_lpd > 0:
                sewage_rows.extend(_plot_sewage_rows(plot))
        if sewage_rows:
            sections.append(TableSection(title="Sewage Summary", rows=tuple(sewage_rows)))

        stp_rows: List[TableRow] = []
        for plot_name in plot_names:
            plot = results.plots.get(plot_name)
            if plot:
                stp_rows.extend(_plot_stp_summary_rows(plot))
                for stp in plot.stp_sections:
                    stp_rows.extend(_stp_section_rows(stp))
        if stp_rows:
            sections.append(TableSection(title="STP Summary", rows=tuple(stp_rows)))

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
