"""Live automation — sync UI inputs to state and apply building parser rules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.nbc_2026 import (
    POOL_NOT_APPLICABLE,
    POOL_STATUS_LABELS,
    fire_tank_capacity_liters,
    parse_building_config,
    ui_plot_label,
)
from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing
from ui.app_state import AppState
from ui.scheduled_callbacks import safe_widget_text, widget_is_alive


def apply_building_parser(project: ProjectData, residential: List[ResidentialWing]) -> None:
    """Parse building configuration into height/floors and propagate to wings."""
    if not project.building_config:
        return
    floors_above, est_height = parse_building_config(project.building_config)
    if est_height > 0 and project.building_height_m <= 0:
        project.building_height_m = est_height
    for wing in residential:
        if not wing.building_config or wing.building_config == "G+7":
            wing.building_config = project.building_config
        if wing.building_height_m <= 0 and project.building_height_m > 0:
            wing.building_height_m = project.building_height_m
        if not wing.building_type:
            wing.building_type = project.building_type
        if wing.num_wings <= 0 and project.num_wings > 0:
            wing.num_wings = project.num_wings
        elif wing.building_config and wing.building_height_m <= 0:
            _, wh = parse_building_config(wing.building_config)
            if wh > 0:
                wing.building_height_m = wh


def wings_from_ui_rows(rows: List[dict], plot_mode: str) -> List[ResidentialWing]:
    """Best-effort sync of residential table rows (no validation)."""
    wings: List[ResidentialWing] = []
    for idx, row in enumerate(rows):
        try:
            wing_name = safe_widget_text(row["wing"]).strip()
            if not wing_name:
                continue
            wings.append(
                ResidentialWing(
                    plot=ui_plot_label(safe_widget_text(row["plot"]), plot_mode),
                    wing=wing_name,
                    building_config=safe_widget_text(row["config"]),
                    building_type=safe_widget_text(row["btype"]),
                    building_height_m=float(safe_widget_text(row["height"]) or 0),
                    num_wings=max(1, int(safe_widget_text(row["num_wings"]) or 1)),
                    flats_1bhk=max(0, int(safe_widget_text(row["b1"]) or 0)),
                    flats_2bhk=max(0, int(safe_widget_text(row["b2"]) or 0)),
                    flats_3bhk=max(0, int(safe_widget_text(row["b3"]) or 0)),
                    flats_4bhk=max(0, int(safe_widget_text(row["b4"]) or 0)),
                    flats_penthouse=max(0, int(safe_widget_text(row["ph"]) or 0)),
                    sort_order=idx,
                )
            )
        except (ValueError, KeyError, TypeError):
            continue
    return wings


def commercial_from_ui_rows(rows: List[dict], plot_mode: str) -> List[CommercialUnit]:
    """Best-effort sync of commercial table rows (no validation)."""
    units: List[CommercialUnit] = []
    for idx, row in enumerate(rows):
        try:
            area = float(safe_widget_text(row["area"]) or 0)
            if area <= 0:
                continue
            block = safe_widget_text(row["block"]).strip()
            if not block:
                continue
            units.append(
                CommercialUnit(
                    plot=ui_plot_label(safe_widget_text(row["plot"]), plot_mode),
                    block=block,
                    comm_type=safe_widget_text(row["type"]),
                    floor_label=safe_widget_text(row["floor"]).strip(),
                    area_sqm=area,
                    sort_order=idx,
                )
            )
        except (ValueError, KeyError, TypeError):
            continue
    return units


def sync_landscape(other: OtherDetails, entries: Dict[str, Any]) -> None:
    for plot, entry in entries.items():
        try:
            other.landscape_area[plot] = float(safe_widget_text(entry) or 0)
        except (ValueError, TypeError):
            other.landscape_area[plot] = 0.0


def sync_hvac(other: OtherDetails, entries: Dict[str, Any]) -> None:
    for plot, entry in entries.items():
        try:
            other.hvac_water[plot] = float(safe_widget_text(entry) or 0)
        except (ValueError, TypeError):
            other.hvac_water[plot] = 0.0


def sync_swimming_pool(
    other: OtherDetails,
    volume_entries: Dict[str, Any],
    status_vars: Dict[str, Any],
) -> None:
    for plot, status_var in status_vars.items():
        try:
            status = POOL_STATUS_LABELS.get(status_var.get(), POOL_NOT_APPLICABLE)
        except (AttributeError, RuntimeError, ValueError):
            status = POOL_NOT_APPLICABLE
        other.swimming_pool_status[plot] = status
        other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
        if status == POOL_NOT_APPLICABLE:
            other.swimming_pool[plot] = 0.0
        else:
            try:
                other.swimming_pool[plot] = float(safe_widget_text(volume_entries[plot]) or 0)
            except (ValueError, TypeError, KeyError):
                other.swimming_pool[plot] = 0.0


def auto_fire_tank_liters(
    plot: str,
    residential: List[ResidentialWing],
    project: ProjectData,
    other: OtherDetails,
) -> int:
    """Resolve fire tank capacity from wings or project-level building data."""
    heights_types = [
        (w.building_height_m, w.building_type)
        for w in residential
        if w.plot == plot and w.building_height_m > 0
    ]
    if heights_types:
        max_height = max(h for h, _ in heights_types)
        btype = next((t for h, t in heights_types if h == max_height), "")
        return fire_tank_capacity_liters(max_height, btype)
    if project.building_height_m > 0:
        return fire_tank_capacity_liters(
            project.building_height_m,
            project.building_type or "Residential Apartment",
        )
    return int(other.fire_tank.get(plot, 0))


def apply_fire_tanks(state: AppState) -> None:
    """Auto-populate fire tank capacities for all active plots."""
    from config.nbc_2026 import active_plots

    for plot in active_plots(state.project.plot_mode):
        state.other.fire_tank[plot] = float(
            auto_fire_tank_liters(plot, state.residential, state.project, state.other)
        )


def prepare_live_calculation(state: AppState) -> None:
    """Run all automation steps before calculator executes."""
    apply_building_parser(state.project, state.residential)
    apply_fire_tanks(state)


def sync_project_page_to_state(app: Any, page: Any) -> None:
    """Pull Project Details inputs into AppState when the page is still alive."""
    if not widget_is_alive(page):
        return
    project = app.app_state.project
    entries = getattr(page, "entries", None) or {}
    for key in ("project_name", "client_name"):
        entry = entries.get(key)
        if entry is not None and widget_is_alive(entry):
            value = safe_widget_text(entry).strip()
            if value:
                setattr(project, key, value)
    if not hasattr(page, "building_config_var"):
        return
    try:
        project.building_config = page.building_config_var.get().strip()
    except (AttributeError, RuntimeError, ValueError):
        pass
    height_entry = getattr(page, "height_entry", None)
    if height_entry is not None and widget_is_alive(height_entry):
        try:
            project.building_height_m = float(safe_widget_text(height_entry) or 0)
        except ValueError:
            pass
    wings_entry = getattr(page, "wings_entry", None)
    if wings_entry is not None and widget_is_alive(wings_entry):
        try:
            project.num_wings = max(1, int(safe_widget_text(wings_entry) or 1))
        except ValueError:
            pass
    building_type_var = getattr(page, "building_type_var", None)
    if building_type_var is not None:
        try:
            project.building_type = building_type_var.get()
        except (AttributeError, RuntimeError, ValueError):
            pass


def sync_pages_to_state(app: Any) -> None:
    """Pull current UI page inputs into AppState (called before live calc)."""
    state = app.app_state
    res_page = app.pages.get("Residential")
    if res_page is not None and widget_is_alive(res_page) and hasattr(res_page, "rows"):
        state.residential = wings_from_ui_rows(res_page.rows, state.project.plot_mode)

    com_page = app.pages.get("Commercial")
    if com_page is not None and widget_is_alive(com_page) and hasattr(com_page, "rows"):
        state.commercial = commercial_from_ui_rows(com_page.rows, state.project.plot_mode)

    proj_page = app.pages.get("Project")
    if proj_page is not None and widget_is_alive(proj_page):
        sync_project_page_to_state(app, proj_page)

    if hasattr(app, "_le") and isinstance(app._le, dict):
        sync_landscape(state.other, app._le)
    if hasattr(app, "_he") and isinstance(app._he, dict):
        sync_hvac(state.other, app._he)
    if hasattr(app, "_pe") and hasattr(app, "_pool_status"):
        sync_swimming_pool(state.other, app._pe, app._pool_status)

    prepare_live_calculation(state)
