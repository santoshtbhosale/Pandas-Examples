from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

from config.nbc_2026 import COMMERCIAL_TYPES, CommercialTypeSpec, commercial_population


@dataclass
class CommercialUnit:
    plot: str = "Plot-A"
    block: str = "COMM-A"
    comm_type: str = "Shop - Ground Floor"
    floor_label: str = ""
    area_sqm: float = 0.0
    density_override: float = 0.0
    sort_order: int = 0

    def type_spec(self) -> CommercialTypeSpec:
        return COMMERCIAL_TYPES.get(self.comm_type, COMMERCIAL_TYPES["Shop - Ground Floor"])

    @property
    def auto_population(self) -> int:
        spec = self.type_spec()
        if self.density_override > 0:
            raw = self.area_sqm / self.density_override
            if spec.use_ceil:
                import math
                return int(math.ceil(raw))
            return int(round(raw))
        return commercial_population(self.area_sqm, spec)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommercialUnit":
        return cls(
            plot=data.get("plot", data.get("Plot", "Plot-A")),
            block=data.get("block", data.get("Block", "COMM-A")),
            comm_type=data.get("comm_type", data.get("Commercial Type", "Shop - Ground Floor")),
            floor_label=data.get("floor_label", data.get("Floor", "")),
            area_sqm=float(data.get("area_sqm", data.get("Area", 0)) or 0),
            density_override=float(data.get("density_override", 0) or 0),
            sort_order=int(data.get("sort_order", 0)),
        )

    def legacy_dict(self) -> Dict[str, Any]:
        return {
            "Plot": self.plot,
            "Commercial Type": self.comm_type,
            "Area": self.area_sqm,
            "Auto Population": self.auto_population,
        }
