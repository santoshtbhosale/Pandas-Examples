"""Rain Water Harvesting input/output models."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from rwh.config import (
    CATCHMENT_SURFACES,
    DEFAULT_ANNUAL_RAINFALL_MM,
    DEFAULT_COLLECTION_EFFICIENCY,
    DEFAULT_MAX_DAILY_RAINFALL_MM,
    DEFAULT_RAINY_DAYS,
)


@dataclass
class RWHCatchmentSurface:
    surface_type: str = "RCC Roof"
    area_sqm: float = 0.0
    runoff_coefficient: float = 0.85
    label: str = ""
    sort_order: int = 0

    def resolved_coefficient(self) -> float:
        if self.surface_type == "Custom":
            return self.runoff_coefficient
        spec = CATCHMENT_SURFACES.get(self.surface_type)
        return spec.runoff_coefficient if spec else self.runoff_coefficient

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RWHCatchmentSurface":
        return cls(
            surface_type=data.get("surface_type", "RCC Roof"),
            area_sqm=float(data.get("area_sqm", 0) or 0),
            runoff_coefficient=float(data.get("runoff_coefficient", 0.85) or 0.85),
            label=data.get("label", ""),
            sort_order=int(data.get("sort_order", 0) or 0),
        )


@dataclass
class RWHProjectData:
    rwh_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = ""
    client_name: str = ""
    project_location: str = ""
    engineer_name: str = "AKASH KHADE"
    project_no: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%d-%m-%Y"))
    annual_rainfall_mm: float = DEFAULT_ANNUAL_RAINFALL_MM
    rainy_days: int = DEFAULT_RAINY_DAYS
    max_daily_rainfall_mm: float = DEFAULT_MAX_DAILY_RAINFALL_MM
    collection_efficiency: float = DEFAULT_COLLECTION_EFFICIENCY
    proposed_tank_liters: float = 0.0  # 0 = use recommended
    notes: str = ""
    surfaces: List[RWHCatchmentSurface] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["surfaces"] = [s.to_dict() for s in self.surfaces]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RWHProjectData":
        surfaces = [RWHCatchmentSurface.from_dict(s) for s in data.get("surfaces", [])]
        return cls(
            rwh_id=data.get("rwh_id", str(uuid.uuid4())),
            project_name=data.get("project_name", ""),
            client_name=data.get("client_name", ""),
            project_location=data.get("project_location", ""),
            engineer_name=data.get("engineer_name", "AKASH KHADE"),
            project_no=data.get("project_no", ""),
            date=data.get("date", datetime.now().strftime("%d-%m-%Y")),
            annual_rainfall_mm=float(data.get("annual_rainfall_mm", DEFAULT_ANNUAL_RAINFALL_MM) or DEFAULT_ANNUAL_RAINFALL_MM),
            rainy_days=int(data.get("rainy_days", DEFAULT_RAINY_DAYS) or DEFAULT_RAINY_DAYS),
            max_daily_rainfall_mm=float(
                data.get("max_daily_rainfall_mm", DEFAULT_MAX_DAILY_RAINFALL_MM) or DEFAULT_MAX_DAILY_RAINFALL_MM
            ),
            collection_efficiency=float(
                data.get("collection_efficiency", DEFAULT_COLLECTION_EFFICIENCY) or DEFAULT_COLLECTION_EFFICIENCY
            ),
            proposed_tank_liters=float(data.get("proposed_tank_liters", 0) or 0),
            notes=data.get("notes", ""),
            surfaces=surfaces,
        )


@dataclass
class RWHSurfaceResult:
    surface_type: str
    label: str
    area_sqm: float
    runoff_coefficient: float
    annual_harvest_liters: float
    peak_day_liters: float


@dataclass
class RWHResults:
    surfaces: List[RWHSurfaceResult] = field(default_factory=list)
    total_catchment_sqm: float = 0.0
    annual_harvest_liters: float = 0.0
    annual_harvest_cum: float = 0.0
    daily_average_liters: float = 0.0
    peak_day_liters: float = 0.0
    recommended_tank_liters: float = 0.0
    design_tank_liters: float = 0.0
    collection_efficiency: float = DEFAULT_COLLECTION_EFFICIENCY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surfaces": [asdict(s) for s in self.surfaces],
            "total_catchment_sqm": self.total_catchment_sqm,
            "annual_harvest_liters": self.annual_harvest_liters,
            "annual_harvest_cum": self.annual_harvest_cum,
            "daily_average_liters": self.daily_average_liters,
            "peak_day_liters": self.peak_day_liters,
            "recommended_tank_liters": self.recommended_tank_liters,
            "design_tank_liters": self.design_tank_liters,
            "collection_efficiency": self.collection_efficiency,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["RWHResults"]:
        if not data:
            return None
        surfaces = [RWHSurfaceResult(**s) for s in data.get("surfaces", [])]
        return cls(
            surfaces=surfaces,
            total_catchment_sqm=float(data.get("total_catchment_sqm", 0) or 0),
            annual_harvest_liters=float(data.get("annual_harvest_liters", 0) or 0),
            annual_harvest_cum=float(data.get("annual_harvest_cum", 0) or 0),
            daily_average_liters=float(data.get("daily_average_liters", 0) or 0),
            peak_day_liters=float(data.get("peak_day_liters", 0) or 0),
            recommended_tank_liters=float(data.get("recommended_tank_liters", 0) or 0),
            design_tank_liters=float(data.get("design_tank_liters", 0) or 0),
            collection_efficiency=float(data.get("collection_efficiency", DEFAULT_COLLECTION_EFFICIENCY) or DEFAULT_COLLECTION_EFFICIENCY),
        )
