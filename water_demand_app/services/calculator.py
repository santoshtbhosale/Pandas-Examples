from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from config.nbc_2026 import (
    PLOT_MODE_SINGLE,
    PLOTS,
    UGT_DOMESTIC_DAYS,
    UGT_FLUSHING_DAYS,
    UGT_FIRE_DAYS,
    active_plots,
    commercial_demand,
    fire_tank_capacity_liters,
    hvac_applicable,
    landscape_demand,
    residential_demand,
    round_storage_liters,
    say_stp_capacity_kld,
    treated_water_lpd,
    wet_landscape_demand,
)
from models.calculations import (
    CalculationResults,
    CommercialResult,
    PlotResults,
    STPResult,
    UGTResult,
    WingResult,
)
from models.commercial import CommercialUnit
from models.other_details import OtherDetails, OHTDetail
from models.project import ProjectData
from models.residential import ResidentialWing


class WaterDemandCalculator:
    def __init__(
        self,
        residential: List[ResidentialWing],
        commercial: List[CommercialUnit],
        other: OtherDetails,
        project: Optional[ProjectData] = None,
    ) -> None:
        self.residential = residential
        self.commercial = commercial
        self.other = other
        self.project = project or ProjectData()
        self._plots = active_plots(self.project.plot_mode)

    def calculate(self) -> CalculationResults:
        self._apply_auto_fire_tanks()
        results = CalculationResults()
        for plot in PLOTS:
            if plot in self._plots:
                results.plots[plot] = self._calculate_plot(plot)
            else:
                results.plots[plot] = PlotResults(plot=plot)
        results.total = self._calculate_totals(results.plots)
        return results

    def _apply_auto_fire_tanks(self) -> None:
        for plot in self._plots:
            heights_types = [
                (w.building_height_m, w.building_type)
                for w in self.residential
                if w.plot == plot and w.building_height_m > 0
            ]
            if heights_types:
                max_height = max(h for h, _ in heights_types)
                btype = next((t for h, t in heights_types if h == max_height), "")
                self.other.fire_tank[plot] = float(
                    fire_tank_capacity_liters(max_height, btype)
                )

    def _calculate_plot(self, plot: str) -> PlotResults:
        plot_res = PlotResults(plot=plot)
        res_wings = [w for w in self.residential if w.plot == plot]
        com_units = [c for c in self.commercial if c.plot == plot]

        for wing in sorted(res_wings, key=lambda w: w.sort_order):
            dom, flu, tot = residential_demand(wing.population)
            kitchen = wing.kitchen_water
            wr = WingResult(
                wing=wing.wing,
                flats=wing.effective_flats,
                pop_per_flat=wing.pop_per_flat,
                population=wing.population,
                domestic_lpd=dom,
                flushing_lpd=flu,
                kitchen_water_lpd=kitchen,
                total_lpd=tot,
            )
            plot_res.residential_wings.append(wr)
            plot_res.res_population += wing.population
            plot_res.res_domestic_lpd += dom
            plot_res.res_flushing_lpd += flu
            plot_res.res_total_lpd += tot
            plot_res.kitchen_water_lpd += kitchen
            plot_res.total_flats += wing.effective_flats

        plot_res.num_buildings_res = len(res_wings)

        blocks: Dict[str, List[CommercialUnit]] = defaultdict(list)
        for unit in sorted(com_units, key=lambda c: c.sort_order):
            blocks[unit.block].append(unit)

        for unit in sorted(com_units, key=lambda c: (c.block, c.sort_order)):
            spec = unit.type_spec()
            density = unit.density_override if unit.density_override > 0 else spec.density_divisor
            pop = unit.auto_population
            dom, flu, tot = commercial_demand(pop, spec)
            cr = CommercialResult(
                block=unit.block,
                comm_type=unit.comm_type,
                floor_label=unit.floor_label,
                area_sqm=unit.area_sqm,
                density=density,
                population=pop,
                domestic_lpd=dom,
                flushing_lpd=flu,
                total_lpd=tot,
            )
            plot_res.commercial_units.append(cr)
            plot_res.com_population += pop
            plot_res.com_domestic_lpd += dom
            plot_res.com_flushing_lpd += flu
            plot_res.com_total_lpd += tot

        plot_res.num_buildings_com = len(blocks)
        plot_res.total_population = plot_res.res_population + plot_res.com_population

        landscape_area = self.other.landscape_area.get(plot, 0.0)
        plot_res.landscape_dry_lpd = landscape_demand(landscape_area)
        plot_res.landscape_wet_lpd = wet_landscape_demand(plot_res.landscape_dry_lpd)

        pool_na = (
            self.other.swimming_pool_status.get(plot, "not_applicable") == "not_applicable"
            or self.other.swimming_pool_na.get(plot, False)
        )
        plot_res.swimming_pool_lpd = 0 if pool_na else int(self.other.swimming_pool.get(plot, 0))

        if hvac_applicable(self.project.project_type):
            plot_res.hvac_lpd = int(self.other.hvac_water.get(plot, 0))
        else:
            plot_res.hvac_lpd = 0

        dry_other = (
            plot_res.landscape_dry_lpd
            + plot_res.swimming_pool_lpd
            + plot_res.hvac_lpd
            + plot_res.kitchen_water_lpd
        )
        wet_other = (
            plot_res.landscape_wet_lpd
            + plot_res.swimming_pool_lpd
            + plot_res.hvac_lpd
            + plot_res.kitchen_water_lpd
        )

        plot_res.dry_total_water_lpd = (
            plot_res.res_total_lpd + plot_res.com_total_lpd + dry_other
        )
        plot_res.wet_total_water_lpd = (
            plot_res.res_total_lpd + plot_res.com_total_lpd + wet_other
        )

        plot_res.fire_tank_liters = int(self.other.fire_tank.get(plot, 0))
        plot_res.ugt_domestic_liters = round_storage_liters(
            (plot_res.res_domestic_lpd + plot_res.com_domestic_lpd) * UGT_DOMESTIC_DAYS
        )
        plot_res.ugt_flushing_liters = round_storage_liters(
            (plot_res.res_flushing_lpd + plot_res.com_flushing_lpd) * UGT_FLUSHING_DAYS
        )

        plot_res.ugt_sections = self._build_ugt_sections(plot, plot_res, blocks)
        plot_res.oht_rows = self._build_oht_rows(plot, plot_res)
        plot_res.stp_sections = self._build_stp_sections(plot, plot_res, blocks)

        total_sewage = sum(s.sewage_lpd for s in plot_res.stp_sections)
        plot_res.sewage_lpd = total_sewage
        plot_res.stp_capacity_kld = sum(s.say_stp_kld for s in plot_res.stp_sections)

        plot_res.dry_treated_water_lpd = sum(
            s.treated_water_lpd for s in plot_res.stp_sections
        )
        plot_res.wet_treated_water_lpd = plot_res.dry_treated_water_lpd

        plot_res.dry_excess_treated_lpd = sum(s.excess_treated_lpd for s in plot_res.stp_sections)
        plot_res.wet_excess_treated_lpd = plot_res.dry_excess_treated_lpd

        return plot_res

    def _build_ugt_sections(
        self,
        plot: str,
        plot_res: PlotResults,
        blocks: Dict[str, List[CommercialUnit]],
    ) -> List[UGTResult]:
        sections: List[UGTResult] = []

        res_dom = plot_res.res_domestic_lpd
        res_flu = plot_res.res_flushing_lpd
        res_fire = self._residential_fire_tank(plot)

        sections.append(
            UGTResult(
                description="DOMESTIC WATER TANK",
                water_requirement_lpd=res_dom,
                storage_days=UGT_DOMESTIC_DAYS,
                total_storage_liters=round_storage_liters(res_dom * UGT_DOMESTIC_DAYS),
                total_storage_kld=round_storage_liters(res_dom * UGT_DOMESTIC_DAYS) / 1000.0,
            )
        )
        sections.append(
            UGTResult(
                description="FLUSHING WATER TANK NEAR STP",
                water_requirement_lpd=res_flu,
                storage_days=UGT_FLUSHING_DAYS,
                total_storage_liters=round_storage_liters(res_flu * UGT_FLUSHING_DAYS),
                total_storage_kld=round_storage_liters(res_flu * UGT_FLUSHING_DAYS) / 1000.0,
            )
        )
        sections.append(
            UGTResult(
                description="FIRE WATER TANK",
                water_requirement_lpd=res_fire,
                storage_days=UGT_FIRE_DAYS,
                total_storage_liters=int(res_fire),
                total_storage_kld=res_fire / 1000.0,
            )
        )

        for block_name in sorted(blocks.keys()):
            block_dom = sum(u.domestic_lpd for u in plot_res.commercial_units if u.block == block_name)
            block_flu = sum(u.flushing_lpd for u in plot_res.commercial_units if u.block == block_name)
            block_fire = int(self.other.get_fire_tank(plot, block_name) or 0)
            if block_fire == 0 and block_name in self.other.fire_tank_commercial.get(plot, {}):
                block_fire = int(self.other.fire_tank_commercial[plot][block_name])

            if block_dom > 0 or block_flu > 0 or block_fire > 0:
                sections.append(
                    UGTResult(
                        description=f"DOMESTIC WATER TANK ({block_name})",
                        water_requirement_lpd=block_dom,
                        storage_days=UGT_DOMESTIC_DAYS,
                        total_storage_liters=round_storage_liters(block_dom * UGT_DOMESTIC_DAYS),
                        total_storage_kld=round_storage_liters(block_dom * UGT_DOMESTIC_DAYS) / 1000.0,
                    )
                )
                flushing_label = f"FLUSHING WATER TANK ({block_name})"
                if block_name == "COMM-A":
                    flushing_label = "FLUSHING WATER TANK (A&B)"
                sections.append(
                    UGTResult(
                        description=flushing_label,
                        water_requirement_lpd=block_flu,
                        storage_days=UGT_FLUSHING_DAYS,
                        total_storage_liters=round_storage_liters(block_flu * UGT_FLUSHING_DAYS),
                        total_storage_kld=round_storage_liters(block_flu * UGT_FLUSHING_DAYS) / 1000.0,
                    )
                )
                if block_fire > 0:
                    sections.append(
                        UGTResult(
                            description=f"FIRE WATER TANK ({block_name})",
                            water_requirement_lpd=block_fire,
                            storage_days=UGT_FIRE_DAYS,
                            total_storage_liters=block_fire,
                            total_storage_kld=block_fire / 1000.0,
                        )
                    )

        return sections

    def _residential_fire_tank(self, plot: str) -> int:
        return int(self.other.fire_tank.get(plot, 0))

    def _build_oht_rows(self, plot: str, plot_res: PlotResults) -> List[Dict[str, float]]:
        oht_by_wing: Dict[str, OHTDetail] = {
            o.wing: o for o in self.other.oht_details if o.plot == plot
        }
        rows: List[Dict[str, float]] = []

        for wr in plot_res.residential_wings:
            oht = oht_by_wing.get(wr.wing)
            if oht:
                rows.append(
                    {
                        "wing": wr.wing,
                        "domestic_kld": oht.domestic_kld,
                        "flushing_kld": oht.flushing_kld,
                        "fire_break_kld": oht.fire_break_kld,
                        "fire_oht_kld": oht.fire_oht_kld,
                    }
                )
            else:
                rows.append(
                    {
                        "wing": wr.wing,
                        "domestic_kld": round(wr.domestic_lpd / 1000.0, 2),
                        "flushing_kld": round(wr.flushing_lpd / 1000.0, 2),
                        "fire_break_kld": 0.0,
                        "fire_oht_kld": 0.0,
                    }
                )

        block_totals: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"domestic_kld": 0.0, "flushing_kld": 0.0}
        )
        for cu in plot_res.commercial_units:
            block_totals[cu.block]["domestic_kld"] += cu.domestic_lpd / 1000.0
            block_totals[cu.block]["flushing_kld"] += cu.flushing_lpd / 1000.0

        for block_name in sorted(block_totals.keys()):
            oht = oht_by_wing.get(block_name)
            bt = block_totals[block_name]
            rows.append(
                {
                    "wing": block_name,
                    "domestic_kld": oht.domestic_kld if oht else round(bt["domestic_kld"], 2),
                    "flushing_kld": oht.flushing_kld if oht else round(bt["flushing_kld"], 2),
                    "fire_break_kld": oht.fire_break_kld if oht else 0.0,
                    "fire_oht_kld": oht.fire_oht_kld if oht else 20.0,
                }
            )

        return rows

    def _build_stp_sections(
        self,
        plot: str,
        plot_res: PlotResults,
        blocks: Dict[str, List[CommercialUnit]],
    ) -> List[STPResult]:
        sections: List[STPResult] = []

        res_water = plot_res.res_total_lpd
        if res_water > 0:
            sections.append(
                self._stp_calc(
                    "RESIDENTIAL",
                    res_water,
                    plot_res.res_flushing_lpd,
                    plot_res.landscape_dry_lpd,
                    plot_res.hvac_lpd,
                )
            )

        com_blocks = sorted(blocks.keys())
        if com_blocks:
            if plot == "Plot-A" and len(com_blocks) >= 1:
                comm_a_units = [u for u in plot_res.commercial_units if u.block == "COMM-A"]
                comm_b_units = [u for u in plot_res.commercial_units if u.block == "COMM-B"]
                comm_ab_water = sum(u.total_lpd for u in comm_a_units + comm_b_units)
                comm_ab_flushing = sum(u.flushing_lpd for u in comm_a_units + comm_b_units)
                if comm_ab_water > 0:
                    sections.append(
                        self._stp_calc(
                            "COMMERCIAL A & B",
                            comm_ab_water,
                            comm_ab_flushing,
                            0,
                            0,
                        )
                    )
            else:
                for block_name in com_blocks:
                    block_water = sum(
                        u.total_lpd
                        for u in plot_res.commercial_units
                        if u.block == block_name
                    )
                    block_flushing = sum(
                        u.flushing_lpd
                        for u in plot_res.commercial_units
                        if u.block == block_name
                    )
                    block_landscape = plot_res.landscape_dry_lpd if block_name == com_blocks[-1] else 0
                    if block_water > 0:
                        scope = f"COMMERCIAL {block_name.replace('COMM-', '')}"
                        if plot == "Plot-B":
                            scope = "RESIDENTIAL & COMMERCIAL"
                        sections.append(
                            self._stp_calc(scope, block_water, block_flushing, block_landscape, 0)
                        )

        if not sections and plot_res.dry_total_water_lpd > 0:
            sections.append(
                self._stp_calc(
                    "TOTAL",
                    plot_res.dry_total_water_lpd,
                    plot_res.res_flushing_lpd + plot_res.com_flushing_lpd,
                    plot_res.landscape_dry_lpd,
                    plot_res.hvac_lpd,
                )
            )

        return sections

    def _stp_calc(
        self,
        scope: str,
        water_lpd: int,
        flushing_reuse: int,
        landscape_reuse: int,
        hvac_reuse: int,
    ) -> STPResult:
        sewage = int(water_lpd * 0.90)
        sewage_kld = sewage / 1000.0
        say_kld = say_stp_capacity_kld(sewage)
        treated = treated_water_lpd(say_kld)
        excess = treated - flushing_reuse - landscape_reuse - hvac_reuse
        return STPResult(
            scope=scope,
            total_water_lpd=water_lpd,
            sewage_lpd=sewage,
            sewage_kld=round(sewage_kld, 2),
            say_stp_kld=say_kld,
            treated_water_lpd=treated,
            reuse_flushing_lpd=flushing_reuse,
            reuse_landscape_lpd=landscape_reuse,
            reuse_hvac_lpd=hvac_reuse,
            excess_treated_lpd=max(0, excess),
        )

    def _calculate_totals(self, plots: Dict[str, PlotResults]) -> Dict[str, Any]:
        plot_a = plots.get("Plot-A")
        plot_b = plots.get("Plot-B")
        if not plot_a:
            return {}
        active = [p for p in (plot_a, plot_b) if p and (p.total_population > 0 or p.dry_total_water_lpd > 0)]
        if self.project.plot_mode == PLOT_MODE_SINGLE:
            active = [plot_a]
        total_pop = sum(p.total_population for p in active)
        total_water = sum(p.dry_total_water_lpd for p in active)
        total_stp = sum(p.stp_capacity_kld for p in active)
        total_res_pop = sum(p.res_population for p in active)
        total_com_pop = sum(p.com_population for p in active)
        total_flats = sum(p.total_flats for p in active)
        return {
            "Total Population": total_pop,
            "Total Water (LPD)": total_water,
            "Total STP Capacity (KLD)": total_stp,
            "Total Residential Population": total_res_pop,
            "Total Commercial Population": total_com_pop,
            "Total Flats": total_flats,
            "Plot-A Res Pop": plot_a.res_population,
            "Plot-B Res Pop": plot_b.res_population if plot_b else 0,
            "Plot-A Total Water (LPD)": plot_a.dry_total_water_lpd,
            "Plot-B Total Water (LPD)": plot_b.dry_total_water_lpd if plot_b else 0,
            "Plot-A STP Capacity (KLD)": plot_a.stp_capacity_kld,
            "Plot-B STP Capacity (KLD)": plot_b.stp_capacity_kld if plot_b else 0,
        }


def perform_calculations(
    residential_data: List[dict],
    commercial_data: List[dict],
    other_data: dict,
    project_data: Optional[dict] = None,
) -> tuple:
    residential = [ResidentialWing.from_dict(r) for r in residential_data]
    commercial = [CommercialUnit.from_dict(c) for c in commercial_data]
    other = OtherDetails.from_dict(other_data)
    project = ProjectData.from_dict(project_data or {})
    calc = WaterDemandCalculator(residential, commercial, other, project)
    results = calc.calculate()
    return results, results.legacy_dict()
