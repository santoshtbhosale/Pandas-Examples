from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class WingResult:
    wing: str
    flats: int
    pop_per_flat: int
    population: int
    domestic_lpd: int
    flushing_lpd: int
    kitchen_water_lpd: int
    total_lpd: int


@dataclass
class CommercialResult:
    block: str
    comm_type: str
    floor_label: str
    area_sqm: float
    density: float
    population: int
    domestic_lpd: int
    flushing_lpd: int
    total_lpd: int


@dataclass
class UGTResult:
    description: str
    water_requirement_lpd: int
    storage_days: int
    total_storage_liters: int
    total_storage_kld: float


@dataclass
class STPResult:
    scope: str
    total_water_lpd: int
    sewage_lpd: int
    sewage_kld: float
    say_stp_kld: float
    treated_water_lpd: int
    reuse_flushing_lpd: int
    reuse_landscape_lpd: int
    reuse_hvac_lpd: int
    excess_treated_lpd: int


@dataclass
class PlotResults:
    plot: str
    residential_wings: List[WingResult] = field(default_factory=list)
    commercial_units: List[CommercialResult] = field(default_factory=list)
    res_population: int = 0
    com_population: int = 0
    total_population: int = 0
    res_domestic_lpd: int = 0
    res_flushing_lpd: int = 0
    res_total_lpd: int = 0
    com_domestic_lpd: int = 0
    com_flushing_lpd: int = 0
    com_total_lpd: int = 0
    landscape_dry_lpd: int = 0
    landscape_wet_lpd: int = 0
    swimming_pool_lpd: int = 0
    hvac_lpd: int = 0
    kitchen_water_lpd: int = 0
    dry_total_water_lpd: int = 0
    wet_total_water_lpd: int = 0
    dry_treated_water_lpd: int = 0
    wet_treated_water_lpd: int = 0
    dry_excess_treated_lpd: int = 0
    wet_excess_treated_lpd: int = 0
    ugt_sections: List[UGTResult] = field(default_factory=list)
    oht_rows: List[Dict[str, Any]] = field(default_factory=list)
    stp_sections: List[STPResult] = field(default_factory=list)
    num_buildings_res: int = 0
    num_buildings_com: int = 0
    total_flats: int = 0
    fire_tank_liters: int = 0
    ugt_domestic_liters: int = 0
    ugt_flushing_liters: int = 0
    sewage_lpd: int = 0
    stp_capacity_kld: float = 0.0

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Population": self.total_population,
            "Res Pop": self.res_population,
            "Com Pop": self.com_population,
            "Total Water (LPD)": self.dry_total_water_lpd,
            "Sewage Gen (LPD)": self.sewage_lpd,
            "STP Capacity (KLD)": self.stp_capacity_kld,
            "UGT Domestic (Liters)": self.ugt_domestic_liters,
            "UGT Flushing (Liters)": self.ugt_flushing_liters,
            "Fire Tank (Liters)": self.fire_tank_liters,
        }


@dataclass
class CalculationResults:
    plots: Dict[str, PlotResults] = field(default_factory=dict)
    total: Dict[str, Any] = field(default_factory=dict)

    def legacy_dict(self) -> Dict[str, Dict[str, Any]]:
        legacy: Dict[str, Dict[str, Any]] = {}
        for plot_name, plot in self.plots.items():
            legacy[plot_name] = plot.legacy_dict()
        legacy["Total"] = self.total
        return legacy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plots": {
                k: {
                    **v.legacy_dict(),
                    "residential_wings": [asdict(w) for w in v.residential_wings],
                    "commercial_units": [asdict(c) for c in v.commercial_units],
                    "ugt_sections": [asdict(u) for u in v.ugt_sections],
                    "stp_sections": [asdict(s) for s in v.stp_sections],
                    "oht_rows": v.oht_rows,
                    "landscape_dry_lpd": v.landscape_dry_lpd,
                    "landscape_wet_lpd": v.landscape_wet_lpd,
                    "dry_total_water_lpd": v.dry_total_water_lpd,
                    "wet_total_water_lpd": v.wet_total_water_lpd,
                }
                for k, v in self.plots.items()
            },
            "total": self.total,
        }
