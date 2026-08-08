"""Solid waste and sewage generation calculations from water-demand results."""

from __future__ import annotations

import math
from typing import Optional

from config.environmental import (
    COMMERCIAL_DRY_WASTE_FRACTION,
    COMMERCIAL_E_WASTE_KG_PER_CAPITA_YEAR,
    COMMERCIAL_SEWAGE_LPCD,
    COMMERCIAL_WASTE_KG_PER_CAPITA_DAY,
    COMMERCIAL_WET_WASTE_FRACTION,
    GARDEN_WASTE_POP_DIVISOR,
    OWC_AREA_HIGH_FACTOR,
    OWC_AREA_LOW_FACTOR,
    RESIDENTIAL_DRY_WASTE_FRACTION,
    RESIDENTIAL_E_WASTE_KG_PER_CAPITA_YEAR,
    RESIDENTIAL_SEWAGE_LPCD,
    RESIDENTIAL_WASTE_KG_PER_CAPITA_DAY,
    RESIDENTIAL_WET_WASTE_FRACTION,
    SEWAGE_GENERATION_PERCENT,
    SEWAGE_STP_AREA_HIGH_FACTOR,
    SEWAGE_STP_AREA_LOW_FACTOR,
    STP_SLUDGE_KG_PER_KLD_DAY,
)
from config.nbc_2026 import PLOT_MODE_SINGLE, active_plots
from models.calculations import CalculationResults
from models.environmental import EnvironmentalResults, SewageGenerationResults, SolidWasteResults
from models.project import ProjectData


def _aggregate_population(results: CalculationResults, plot_mode: str) -> tuple[int, int]:
    res_pop = 0
    comm_pop = 0
    for plot_name in active_plots(plot_mode):
        plot = results.plots.get(plot_name)
        if not plot:
            continue
        res_pop += plot.res_population
        comm_pop += plot.com_population
    return res_pop, comm_pop


def _total_stp_capacity_kld(results: CalculationResults) -> float:
    if results.total:
        return float(results.total.get("Total STP Capacity (KLD)", 0) or 0)
    return 0.0


def _stp_sludge_kg_day(stp_capacity_kld: float) -> float:
    return round(stp_capacity_kld * STP_SLUDGE_KG_PER_KLD_DAY, 2)


def _owc_area_range(owc_capacity_kg_day: float) -> str:
    if owc_capacity_kg_day <= 0:
        return ""
    low = round(owc_capacity_kg_day * OWC_AREA_LOW_FACTOR)
    high = round(owc_capacity_kg_day * OWC_AREA_HIGH_FACTOR)
    return f"{low}-{high}"


def _sewage_area_range(stp_capacity_kld: float) -> str:
    if stp_capacity_kld <= 0:
        return ""
    low = round(stp_capacity_kld * SEWAGE_STP_AREA_LOW_FACTOR)
    high = round(stp_capacity_kld * SEWAGE_STP_AREA_HIGH_FACTOR)
    return f"{low}-{high}"


def calculate_solid_waste(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> SolidWasteResults:
    out = SolidWasteResults()
    if not results or not results.plots:
        return out

    res_pop, comm_pop = _aggregate_population(results, project.plot_mode)
    out.res_population = res_pop
    out.comm_population = comm_pop

    out.res_total_waste_kg_day = round(res_pop * RESIDENTIAL_WASTE_KG_PER_CAPITA_DAY, 2)
    out.res_wet_waste_kg_day = round(out.res_total_waste_kg_day * RESIDENTIAL_WET_WASTE_FRACTION, 2)
    out.res_dry_waste_kg_day = round(out.res_total_waste_kg_day * RESIDENTIAL_DRY_WASTE_FRACTION, 2)

    out.comm_total_waste_kg_day = round(comm_pop * COMMERCIAL_WASTE_KG_PER_CAPITA_DAY, 2)
    out.comm_wet_waste_kg_day = round(out.comm_total_waste_kg_day * COMMERCIAL_WET_WASTE_FRACTION, 2)
    out.comm_dry_waste_kg_day = round(out.comm_total_waste_kg_day * COMMERCIAL_DRY_WASTE_FRACTION, 2)

    out.total_waste_kg_day = round(out.res_total_waste_kg_day + out.comm_total_waste_kg_day, 2)
    out.total_wet_waste_kg_day = round(out.res_wet_waste_kg_day + out.comm_wet_waste_kg_day, 2)
    out.total_dry_waste_kg_day = round(out.res_dry_waste_kg_day + out.comm_dry_waste_kg_day, 2)

    out.wet_waste_considered_kg_day = float(math.ceil(out.res_wet_waste_kg_day))
    out.garden_waste_considered_kg_day = round(res_pop / GARDEN_WASTE_POP_DIVISOR, 2) if res_pop > 0 else 0.0

    stp_capacity = _total_stp_capacity_kld(results)
    out.stp_sludge_kg_day = _stp_sludge_kg_day(stp_capacity)
    out.owc_plant_capacity_kg_day = round(
        out.wet_waste_considered_kg_day + out.garden_waste_considered_kg_day + out.stp_sludge_kg_day,
        2,
    )

    out.res_e_waste_kg_year = round(res_pop * RESIDENTIAL_E_WASTE_KG_PER_CAPITA_YEAR, 2)
    out.comm_e_waste_kg_year = round(comm_pop * COMMERCIAL_E_WASTE_KG_PER_CAPITA_YEAR, 2)
    out.total_e_waste_kg_year = round(out.res_e_waste_kg_year + out.comm_e_waste_kg_year, 2)
    out.approx_area_sqm = _owc_area_range(out.owc_plant_capacity_kg_day)
    return out


def calculate_sewage_generation(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> SewageGenerationResults:
    out = SewageGenerationResults()
    if not results or not results.plots:
        return out

    res_pop, comm_pop = _aggregate_population(results, project.plot_mode)
    out.res_population = res_pop
    out.comm_population = comm_pop

    out.res_sewage_kld = round(
        res_pop * RESIDENTIAL_SEWAGE_LPCD * SEWAGE_GENERATION_PERCENT / 1000.0,
        2,
    )
    out.comm_sewage_kld = round(
        comm_pop * COMMERCIAL_SEWAGE_LPCD * SEWAGE_GENERATION_PERCENT / 1000.0,
        2,
    )
    out.total_sewage_kld = round(out.res_sewage_kld + out.comm_sewage_kld, 2)

    out.proposed_stp_capacity_kld = _total_stp_capacity_kld(results)
    out.stp_sludge_kg_day = _stp_sludge_kg_day(out.proposed_stp_capacity_kld)
    out.approx_area_sqm = _sewage_area_range(out.proposed_stp_capacity_kld)
    return out


def calculate_environmental(
    results: Optional[CalculationResults],
    project: ProjectData,
) -> EnvironmentalResults:
    return EnvironmentalResults(
        solid_waste=calculate_solid_waste(results, project),
        sewage=calculate_sewage_generation(results, project),
    )
