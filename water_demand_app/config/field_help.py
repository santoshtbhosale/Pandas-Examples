"""User-friendly help text for engineering form fields."""

from __future__ import annotations

FIELD_HELP = {
    "project_name": "Enter the official project name as it should appear on the report.",
    "client_name": "Name of the client or developer commissioning this report.",
    "engineer_name": "Lead engineer responsible for preparing this water demand report.",
    "project_location": "City or site location for the project.",
    "building_height": "Maximum building height in metres (used for fire tank and UGT sizing).",
    "num_wings": "Total number of residential wings or blocks in the project.",
    "building_type": "Building classification used for NBC fire tank and demand rules.",
    "building_config": "Floor configuration such as G+7 (ground plus seven upper floors).",
    "prepared_by": "Person who prepared the report (appears in sign-off section).",
    "checked_by": "Person who reviewed the calculations.",
    "approved_by": "Person who approved the final report.",
    "bhk_units": "Enter the number of flats for each BHK type. Population and water demand auto-calculate.",
    "occupancy_type": "NBC occupancy category — determines per-capita water demand rates.",
    "commercial_area": "Net usable floor area in square metres for this commercial unit.",
    "landscape_area": "Landscape area in sq.m — NBC rate is 6 L/sq.m/day.",
    "swimming_pool": "Pool volume in litres if applicable, or mark as Not Applicable.",
    "hvac_water": "HVAC makeup water requirement in litres per day for this plot.",
}
