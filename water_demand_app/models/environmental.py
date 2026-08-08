from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SolidWasteResults:
    res_population: int = 0
    comm_population: int = 0
    res_total_waste_kg_day: float = 0.0
    res_wet_waste_kg_day: float = 0.0
    res_dry_waste_kg_day: float = 0.0
    comm_total_waste_kg_day: float = 0.0
    comm_wet_waste_kg_day: float = 0.0
    comm_dry_waste_kg_day: float = 0.0
    total_waste_kg_day: float = 0.0
    total_wet_waste_kg_day: float = 0.0
    total_dry_waste_kg_day: float = 0.0
    wet_waste_considered_kg_day: float = 0.0
    garden_waste_considered_kg_day: float = 0.0
    stp_sludge_kg_day: float = 0.0
    owc_plant_capacity_kg_day: float = 0.0
    res_e_waste_kg_year: float = 0.0
    comm_e_waste_kg_year: float = 0.0
    total_e_waste_kg_year: float = 0.0
    approx_area_sqm: str = ""


@dataclass
class SewageGenerationResults:
    res_population: int = 0
    comm_population: int = 0
    res_sewage_kld: float = 0.0
    comm_sewage_kld: float = 0.0
    total_sewage_kld: float = 0.0
    proposed_stp_capacity_kld: float = 0.0
    stp_sludge_kg_day: float = 0.0
    approx_area_sqm: str = ""


@dataclass
class EnvironmentalResults:
    solid_waste: SolidWasteResults = field(default_factory=SolidWasteResults)
    sewage: SewageGenerationResults = field(default_factory=SewageGenerationResults)
