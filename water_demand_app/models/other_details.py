from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List


@dataclass
class OHTDetail:
    plot: str = "Plot-A"
    wing: str = ""
    domestic_kld: float = 0.0
    flushing_kld: float = 0.0
    fire_break_kld: float = 0.0
    fire_oht_kld: float = 0.0
    sort_order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHTDetail":
        return cls(
            plot=data.get("plot", "Plot-A"),
            wing=data.get("wing", ""),
            domestic_kld=float(data.get("domestic_kld", 0) or 0),
            flushing_kld=float(data.get("flushing_kld", 0) or 0),
            fire_break_kld=float(data.get("fire_break_kld", 0) or 0),
            fire_oht_kld=float(data.get("fire_oht_kld", 0) or 0),
            sort_order=int(data.get("sort_order", 0)),
        )


@dataclass
class OtherDetails:
    landscape_area: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 765.0, "Plot-B": 762.0})
    swimming_pool: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 0.0, "Plot-B": 0.0})
    swimming_pool_status: Dict[str, str] = field(
        default_factory=lambda: {"Plot-A": "not_applicable", "Plot-B": "not_applicable"}
    )
    swimming_pool_na: Dict[str, bool] = field(default_factory=lambda: {"Plot-A": True, "Plot-B": True})
    hvac_water: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 0.0, "Plot-B": 0.0})
    fire_tank: Dict[str, float] = field(default_factory=lambda: {"Plot-A": 300000.0, "Plot-B": 230000.0})
    fire_tank_commercial: Dict[str, Dict[str, float]] = field(default_factory=dict)
    oht_details: List[OHTDetail] = field(default_factory=list)

    def get_fire_tank(self, plot: str, block: str = "") -> float:
        if block and block in self.fire_tank_commercial.get(plot, {}):
            return self.fire_tank_commercial[plot][block]
        return self.fire_tank.get(plot, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "landscape_area": self.landscape_area,
            "swimming_pool": self.swimming_pool,
            "swimming_pool_status": self.swimming_pool_status,
            "swimming_pool_na": self.swimming_pool_na,
            "hvac_water": self.hvac_water,
            "fire_tank": self.fire_tank,
            "fire_tank_commercial": self.fire_tank_commercial,
            "oht_details": [o.to_dict() for o in self.oht_details],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OtherDetails":
        legacy_fire = {}
        if "Fire Tank Plot-A" in data:
            legacy_fire = {
                "Plot-A": float(data.get("Fire Tank Plot-A", 300000) or 300000),
                "Plot-B": float(data.get("Fire Tank Plot-B", 230000) or 230000),
            }
        oht_list = [OHTDetail.from_dict(o) for o in data.get("oht_details", [])]
        pool_na = data.get("swimming_pool_na", {"Plot-A": True, "Plot-B": True})
        pool_status = data.get("swimming_pool_status", {})
        if not pool_status:
            pool_status = {
                plot: "not_applicable" if pool_na.get(plot, True) else "applicable"
                for plot in ("Plot-A", "Plot-B")
            }
        return cls(
            landscape_area=data.get("landscape_area", {"Plot-A": 765.0, "Plot-B": 762.0}),
            swimming_pool=data.get("swimming_pool", {"Plot-A": 0.0, "Plot-B": 0.0}),
            swimming_pool_status=pool_status,
            swimming_pool_na=pool_na,
            hvac_water=data.get("hvac_water", {"Plot-A": 0.0, "Plot-B": 0.0}),
            fire_tank=data.get("fire_tank", legacy_fire or {"Plot-A": 300000.0, "Plot-B": 230000.0}),
            fire_tank_commercial=data.get("fire_tank_commercial", {}),
            oht_details=oht_list,
        )

    def legacy_dict(self) -> Dict[str, float]:
        return {
            f"Fire Tank {plot}": self.fire_tank.get(plot, 0.0)
            for plot in ("Plot-A", "Plot-B")
        }
