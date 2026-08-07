from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

from config.nbc_2026 import bhk_flat_count, bhk_population, kitchen_water_lpd


@dataclass
class ResidentialWing:
    plot: str = "Plot-A"
    wing: str = ""
    building_type: str = "High Rise Tower"
    building_height_m: float = 0.0
    flats: int = 0
    flats_1bhk: int = 0
    flats_2bhk: int = 0
    flats_3bhk: int = 0
    flats_penthouse: int = 0
    pop_per_flat: int = 5
    sort_order: int = 0

    @property
    def has_bhk_mix(self) -> bool:
        return bhk_flat_count(
            self.flats_1bhk, self.flats_2bhk, self.flats_3bhk, self.flats_penthouse
        ) > 0

    @property
    def effective_flats(self) -> int:
        bhk_total = bhk_flat_count(
            self.flats_1bhk, self.flats_2bhk, self.flats_3bhk, self.flats_penthouse
        )
        return bhk_total if bhk_total > 0 else self.flats

    @property
    def population(self) -> int:
        if self.has_bhk_mix:
            return bhk_population(
                self.flats_1bhk, self.flats_2bhk, self.flats_3bhk, self.flats_penthouse
            )
        return self.flats * self.pop_per_flat

    @property
    def kitchen_water(self) -> int:
        if not self.has_bhk_mix:
            return 0
        return kitchen_water_lpd(
            self.flats_1bhk, self.flats_2bhk, self.flats_3bhk, self.flats_penthouse
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResidentialWing":
        return cls(
            plot=data.get("plot", data.get("Plot", "Plot-A")),
            wing=data.get("wing", data.get("Wing", "")),
            building_type=data.get("building_type", "High Rise Tower"),
            building_height_m=float(data.get("building_height_m", 0) or 0),
            flats=int(data.get("flats", data.get("No. Of Flats", 0)) or 0),
            flats_1bhk=int(data.get("flats_1bhk", 0) or 0),
            flats_2bhk=int(data.get("flats_2bhk", 0) or 0),
            flats_3bhk=int(data.get("flats_3bhk", 0) or 0),
            flats_penthouse=int(data.get("flats_penthouse", data.get("flats_ph", 0)) or 0),
            pop_per_flat=int(data.get("pop_per_flat", data.get("Pop/Flat", 5)) or 5),
            sort_order=int(data.get("sort_order", 0)),
        )

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Plot": self.plot,
            "Wing": self.wing,
            "No. Of Flats": self.effective_flats,
            "Population": self.population,
        }
