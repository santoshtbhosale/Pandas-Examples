from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class ResidentialWing:
    plot: str = "Plot-A"
    wing: str = ""
    flats: int = 0
    pop_per_flat: int = 5
    sort_order: int = 0

    @property
    def population(self) -> int:
        return self.flats * self.pop_per_flat

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResidentialWing":
        return cls(
            plot=data.get("plot", data.get("Plot", "Plot-A")),
            wing=data.get("wing", data.get("Wing", "")),
            flats=int(data.get("flats", data.get("No. Of Flats", 0)) or 0),
            pop_per_flat=int(data.get("pop_per_flat", data.get("Pop/Flat", 5)) or 5),
            sort_order=int(data.get("sort_order", 0)),
        )

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Plot": self.plot,
            "Wing": self.wing,
            "No. Of Flats": self.flats,
            "Population": self.population,
        }
