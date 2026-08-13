from __future__ import annotations

import json
import os
import re
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    POOL_NOT_APPLICABLE,
    POOL_STATUS_LABELS,
    fire_tank_capacity_liters,
    is_project_type_set,
    plot_choices,
    project_type_label,
    show_residential_section,
)
from config.page_visibility import WIZARD_PAGE_ORDER, visible_pages, wizard_next_page
from services.automation import sync_hvac, sync_landscape, sync_pages_to_state, sync_swimming_pool
from services.database import DB_PATH, build_project_snapshot, init_db, parse_project_snapshot
from services.excel_exporter import export_excel
from services.lookup_db import init_lookup_tables
from services.pdf_exporter import export_pdf
from services.project_service import create_new_project_state, find_projects, load_project_state, persist_project_state
from services.result_tables import (
    build_oht_table_sections,
    build_preview_table_sections,
    build_sewage_generation_table_sections,
    build_solid_waste_table_sections,
    build_stp_table_sections,
)
from ui.app_state import AppState
from ui.components.preview_dialog import PreviewDialog
from ui.components.result_table import ResultTableView
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_float, validate_required
from ui.pages.commercial_page import CommercialPage
from ui.pages.final_page import FinalPage
from ui.pages.project_page import ProjectPage
from ui.pages.residential_page import ResidentialPage

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "assets", "logo.png")
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(os.path.dirname(APP_DIR), "logo.png")


# ============================================================
# PROJECT WORKSPACE (embedded in single main window)
# ============================================================

def _raise_page(page) -> None:
    """Reliably bring a page to the front in the shared workspace container."""
    try:
        page.grid(row=0, column=0, sticky="nsew")
    except Exception:
        pass
    try:
        page.tkraise()
    except Exception:
        try:
            page.lift()
        except Exception:
            pass
    try:
        parent_frame = getattr(page, "_parent_frame", None)
        if parent_frame is not None:
            parent_frame.tkraise()
    except Exception:
        pass


class ProjectWorkspace(ctk.CTkFrame):
    NAV = [
        ("Project", "Project Details"),
        ("Residential", "Residential"),
        ("Commercial", "Commercial"),
        ("Hospital", "Hospital Details"),
        ("Hotel", "Hotel / Kitchen"),
        ("FoodCourt", "Food Court"),
        ("Landscape", "Landscape"),
        ("Swimming", "Swimming Pool"),
        ("HVAC", "HVAC"),
        ("UGT", "UGT / Fire Tank"),
        ("Sewage", "Sewage Generation"),
        ("OHT", "OHT Details"),
        ("STP", "STP Summary"),
        ("SolidWaste", "Solid Waste Generation"),
        ("Preview", "Preview"),
        ("Report", "Generate Report"),
        ("Settings", "Settings"),
    ]

    def __init__(
        self,
        master,
        on_home=None,
        initial_state=None,
        on_autosave=None,
        on_header_update=None,
        current_user=None,
        on_logout=None,
        on_new_project=None,
        on_back_to_type_selector=None,
    ):
        super().__init__(master, fg_color="#F0F2F5", corner_radius=0)
        self.on_home = on_home
        self.on_autosave = on_autosave
        self.on_header_update = on_header_update
        self.current_user = current_user
        self.on_logout = on_logout
        self.on_new_project = on_new_project
        self.on_back_to_type_selector = on_back_to_type_selector
        self.app_state = initial_state if initial_state is not None else AppState()
        self._last_autosave_at = ""
        self._pages_built = False
        self._autosave_job = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = self._build_sidebar()
        self.container = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.pages: dict = {}
        self._current_page = "Project"
        self._calc_job = None
        self._calc_dirty = True
        self._project_list_cache: list | None = None

    def ensure_pages_built(self) -> None:
        if self._pages_built:
            return
        self._build_pages()
        self._pages_built = True
        self.show("Project")

    def reset_for_new_type(self) -> None:
        """Drop cached workflow pages before a new project/type is shown."""
        for key, page in list(self.pages.items()):
            try:
                page.destroy()
            except Exception:
                pass
        self.pages.clear()
        self._current_page = "Project"
        self._calc_dirty = True
        if self._calc_job is not None:
            try:
                self.after_cancel(self._calc_job)
            except Exception:
                pass
            self._calc_job = None

    def apply_state(self, state: AppState) -> None:
        """Install project state and reset stale lazily-built pages."""
        for key, page in list(self.pages.items()):
            try:
                page.destroy()
            except Exception:
                pass
        self.pages.clear()
        self.app_state = state
        self._current_page = "Project"
        self._calc_dirty = True
        self._build_pages()
        self._rebuild_sidebar()
        project_page = self.pages.get("Project")
        if project_page is not None:
            if hasattr(project_page, "refresh"):
                project_page.refresh()
            if is_project_type_set(self.app_state.project.project_type) and hasattr(project_page, "_show_details"):
                project_page._show_details()
        self.show("Project")
        if self._calc_job is not None:
            try:
                self.after_cancel(self._calc_job)
            except Exception:
                pass
        self._calc_job = self.after(80, self._run_scheduled_calc)
        if self.on_header_update:
            self.on_header_update()

    def autosave_before_close(self) -> None:
        try:
            self._calc()
            persist_project_state(self.app_state, db_path=DB_PATH)
        except Exception:
            pass

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        try:
            self._calc()
            from services.project_service import persist_project_state
            persist_project_state(self.app_state, db_path=DB_PATH)
            self._last_autosave_at = datetime.now().strftime("%H:%M:%S")
            if self.on_autosave:
                self.on_autosave()
        except Exception:
            pass
        self._schedule_autosave()

    def _plots(self) -> list[str]:
        return plot_choices(self.app_state.project.plot_mode)

    def _nav_visible(self, key: str) -> bool:
        return key in visible_pages(self.app_state.project.project_type)

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        ctk.CTkLabel(
            sb,
            text="Project Navigation",
            font=("Arial", 14, "bold"),
            text_color="white",
            justify="center",
        ).pack(pady=(20, 12))
        if self.on_home:
            ctk.CTkButton(
                sb,
                text="Project Home",
                height=36,
                anchor="w",
                fg_color="#2980B9",
                hover_color=BRAND_ORANGE,
                text_color="white",
                font=("Arial", 12, "bold"),
                command=self.on_home,
            ).pack(fill="x", padx=8, pady=(0, 8))
        if self.current_user:
            ctk.CTkLabel(
                sb,
                text=f"{self.current_user.full_name}\n({self.current_user.role_label})",
                font=("Arial", 9),
                text_color="#CCCCCC",
                justify="center",
            ).pack(pady=(0, 4))
        pid = self.app_state.project.project_id
        ctk.CTkLabel(
            sb,
            text=f"ID: {pid}",
            font=("Arial", 8),
            text_color="#999999",
            wraplength=200,
        ).pack(pady=(0, 4))
        if is_project_type_set(self.app_state.project.project_type):
            self._project_type_label = ctk.CTkLabel(
                sb,
                text=project_type_label(self.app_state.project.project_type),
                font=("Arial", 9, "bold"),
                text_color=BRAND_ORANGE,
                wraplength=200,
            )
        else:
            self._project_type_label = ctk.CTkLabel(
                sb,
                text="Select project type",
                font=("Arial", 9, "italic"),
                text_color="#AAAAAA",
                wraplength=200,
            )
        self._project_type_label.pack(pady=(0, 8))
        self.nav_btns = {}
        for key, label in self.NAV:
            btn = ctk.CTkButton(
                sb,
                text=label,
                height=36,
                anchor="w",
                fg_color="transparent",
                hover_color=BRAND_ORANGE,
                text_color="white",
                font=("Arial", 12),
                command=lambda k=key: self.show(k),
            )
            self.nav_btns[key] = btn
            if self._nav_visible(key):
                btn.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self.on_new_project if self.on_new_project else self._new).pack(
            side="bottom", fill="x", padx=10, pady=(4, 4 if self.on_logout else 15)
        )
        if self.on_logout:
            ctk.CTkButton(sb, text="Logout", fg_color="#C0392B", command=self._logout).pack(
                side="bottom", fill="x", padx=10, pady=(4, 15)
            )
        return sb

    def _logout(self) -> None:
        if self.on_logout and messagebox.askyesno("Logout", "Return to login screen?"):
            self.on_logout()

    def _rebuild_sidebar(self) -> None:
        allowed = set(visible_pages(self.app_state.project.project_type))
        for key, btn in self.nav_btns.items():
            if key in allowed:
                if not btn.winfo_ismapped():
                    btn.pack(fill="x", padx=8, pady=2)
            else:
                btn.pack_forget()
        if hasattr(self, "_project_type_label"):
            if is_project_type_set(self.app_state.project.project_type):
                self._project_type_label.configure(
                    text=project_type_label(self.app_state.project.project_type),
                    font=("Arial", 9, "bold"),
                    text_color=BRAND_ORANGE,
                )
            else:
                self._project_type_label.configure(
                    text="Select project type",
                    font=("Arial", 9, "italic"),
                    text_color="#AAAAAA",
                )

    def _project_details_back(self):
        if self.on_back_to_type_selector:
            self.on_back_to_type_selector()
        elif self.on_home:
            self.on_home()
        elif self.on_new_project:
            self.on_new_project()

    def _build_pages(self) -> None:
        """Build only the lightweight Project Details page initially."""
        if "Project" not in self.pages:
            self.pages["Project"] = ProjectPage(
                self.container,
                self.app_state,
                on_next=self._next_from_project,
                on_type_change=self._on_project_type_changed,
                on_back=self._project_details_back,
            )
        page = self.pages.get("Project")
        if page is not None:
            try:
                page.grid(row=0, column=0, sticky="nsew")
            except Exception:
                pass

    def _build_single_page(self, key: str) -> bool:
        if key in self.pages:
            return True
        visible = visible_pages(self.app_state.project.project_type)
        if key != "Project" and key not in visible:
            return False

        if key == "Residential":
            self.pages[key] = ResidentialPage(
                self.container, self.app_state,
                on_next=self._next_from_residential,
                on_back=lambda: self.show("Project"),
            )
        elif key == "Commercial":
            self.pages[key] = CommercialPage(
                self.container, self.app_state,
                on_next=lambda: self._wizard_show_next("Commercial"),
                on_back=self._back_from_commercial,
            )
        elif key == "Hospital":
            self.pages[key] = self._placeholder_page(
                "Hospital Details",
                "Enter hospital bed counts and medical water requirements.\nUse Commercial page with Hospital occupancy for NBC calculations.",
                lambda: self._wizard_show_next("Hospital"), "Hospital")
        elif key == "Hotel":
            self.pages[key] = self._placeholder_page(
                "Hotel / Kitchen / Laundry",
                "Hotel kitchen and laundry water demands are calculated from commercial occupancy rules.\nAdd Hotel-type units on the Commercial page.",
                lambda: self._wizard_show_next("Hotel"), "Hotel")
        elif key == "FoodCourt":
            self.pages[key] = self._placeholder_page(
                "Food Court",
                "Food court water demand uses Restaurant occupancy (÷1.4 population density).\nAdd Restaurant units on the Commercial page.",
                lambda: self._wizard_show_next("FoodCourt"), "FoodCourt")
        elif key == "Landscape":
            self.pages[key] = self._form_page("Landscape (NBC-2026)", self._landscape_ui, "Landscape")
        elif key == "Swimming":
            self.pages[key] = self._form_page("Swimming Pool", self._pool_ui, "Swimming")
        elif key == "HVAC":
            self.pages[key] = self._form_page("HVAC Water", self._hvac_ui, "HVAC")
        elif key == "UGT":
            self.pages[key] = self._form_page("UGT / Fire Tank", self._ugt_ui, "UGT")
        elif key == "Sewage":
            self.pages[key] = self._sewage_page()
        elif key == "OHT":
            self.pages[key] = self._oht_page()
        elif key == "STP":
            self.pages[key] = self._stp_page()
        elif key == "SolidWaste":
            self.pages[key] = self._solid_waste_page()
        elif key == "Preview":
            self.pages[key] = self._preview_page()
        elif key == "Report":
            self.pages[key] = FinalPage(
                self.container, self.app_state,
                on_back=lambda: self.show("Preview"),
                on_generate_all=self._generate_report_all,
            )
        elif key == "Settings":
            self.pages[key] = self._settings_page()
        else:
            return False

        try:
            self.pages[key].grid(row=0, column=0, sticky="nsew")
        except Exception:
            pass
        return True

    def _placeholder_page(self, title: str, body: str, on_next, page_key: str):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(frame, text=body, font=("Arial", 12), justify="left", wraplength=900).pack(
            anchor="w", padx=20, pady=20
        )
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")
        ctk.CTkButton(nav, text="Next →", width=140, fg_color=BRAND_ORANGE, command=on_next).pack(side="right")
        return frame

    def _discard_inapplicable_pages(self) -> None:
        allowed = visible_pages(self.app_state.project.project_type)
        for key in list(self.pages.keys()):
            if key == "Project" or key in allowed:
                continue
            page = self.pages.pop(key, None)
            if page is not None:
                try:
                    page.destroy()
                except Exception:
                    pass

    def _on_project_type_changed(self) -> None:
        self._discard_inapplicable_pages()
        self._rebuild_sidebar()
        if not is_project_type_set(self.app_state.project.project_type):
            self.show("Project")
            if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
                self.pages["Project"].refresh()
            return
        self._schedule_calc(120)
        visible = visible_pages(self.app_state.project.project_type)
        if self._current_page not in visible:
            self.show("Project")
        if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
            self.pages["Project"].refresh()

    def _wizard_show_previous(self, current: str) -> None:
        project_type = self.app_state.project.project_type
        if not is_project_type_set(project_type):
            self.show("Project")
            return
        pages = visible_pages(project_type)
        if current not in pages:
            self.show("Project")
            return
        previous = None
        for key in WIZARD_PAGE_ORDER:
            if key not in pages:
                continue
            if key == current:
                break
            previous = key
        if previous:
            self._navigate_to_page(previous)

    def _navigate_to_page(self, target: str) -> bool:
        project_type = self.app_state.project.project_type
        if target != "Project" and not is_project_type_set(project_type):
            self.show("Project")
            return False
        allowed = visible_pages(project_type)
        if target not in allowed:
            self.show("Project")
            return False
        if not self._ensure_page_available(target):
            return False
        try:
            page = self.pages.get(target)
            if page is None or not page.winfo_exists():
                if not self._ensure_page_available(target):
                    return False
            self.show(target)
            return self._current_page == target
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Navigation Error",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )
            return False

    def _wizard_show_next(self, current: str) -> None:
        try:
            project_type = self.app_state.project.project_type
            if not is_project_type_set(project_type):
                messagebox.showwarning("Project Type", "Please select a project type before continuing.")
                self.show("Project")
                return

            pages = visible_pages(project_type)
            if current not in pages:
                self.show("Project")
                return

            nxt = wizard_next_page(current, project_type)
            if nxt is None:
                return

            if not self._ensure_page_available(nxt):
                messagebox.showerror("Navigation Error", f"Unable to open the next section: {nxt}")
                return

            page = self.pages.get(nxt)
            if page is None:
                messagebox.showerror("Navigation Error", f"The next section '{nxt}' could not be opened.")
                return

            for key, other in list(self.pages.items()):
                if key == nxt:
                    continue
                try:
                    other.grid_remove()
                except Exception:
                    try:
                        other.pack_forget()
                    except Exception:
                        pass

            page.grid(row=0, column=0, sticky="nsew")
            page.tkraise()
            try:
                parent_frame = getattr(page, "_parent_frame", None)
                if parent_frame is not None:
                    parent_frame.tkraise()
            except Exception:
                pass

            self._current_page = nxt
            for key, btn in self.nav_btns.items():
                try:
                    btn.configure(fg_color=BRAND_ORANGE if key == nxt else "transparent")
                except Exception:
                    pass

            if nxt == "STP":
                self._refresh_stp(silent=True)
            elif nxt == "Sewage":
                self._refresh_sewage(silent=True)
            elif nxt == "SolidWaste":
                self._refresh_solid_waste(silent=True)
            elif nxt == "OHT":
                self._refresh_oht(silent=True)
            elif nxt == "Preview":
                self._refresh_preview(silent=True)

            self.after(150, lambda: self._schedule_calc(50))

        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Navigation Error",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )

    def _form_page(self, title, builder, page_key):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        builder(frame)

        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")

        next_commands = {
            "Landscape": self._save_landscape,
            "Swimming": self._save_pool,
            "HVAC": lambda: (self._sync_hvac_live(), self._wizard_show_next("HVAC")),
            "UGT": lambda: self._wizard_show_next("UGT"),
        }
        next_command = next_commands.get(page_key, lambda pk=page_key: self._wizard_show_next(pk))
        ctk.CTkButton(nav, text="Next →", width=140, fg_color=BRAND_ORANGE, command=next_command).pack(side="right")
        return frame

    def _landscape_ui(self, parent):
        self._le = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(self.app_state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_landscape_live(), self._schedule_calc()))
            self._le[plot] = entry
        ctk.CTkLabel(parent, text="Auto: 6 L/sq.m/day per NBC-2026 (live)", font=("Arial", 11, "italic")).pack(anchor="w", padx=20)

    def _sync_landscape_live(self) -> None:
        if hasattr(self, "_le"):
            sync_landscape(self.app_state.other, self._le)

    def _save_landscape(self):
        try:
            for plot, entry in self._le.items():
                self.app_state.other.landscape_area[plot] = validate_positive_float(entry.get(), f"Landscape {plot}")
            self._wizard_show_next("Landscape")
        except ValidationError as exc:
            messagebox.showerror("Error", exc.message)

    def _pool_ui(self, parent):
        self._pe = {}
        self._pool_status = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Swimming Pool {plot}", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            status = self.app_state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
            if self.app_state.other.swimming_pool_na.get(plot, False):
                status = POOL_NOT_APPLICABLE
            label = next((k for k, v in POOL_STATUS_LABELS.items() if v == status), "Not Applicable")
            status_var = ctk.StringVar(value=label)
            ctk.CTkComboBox(
                form,
                values=list(POOL_STATUS_LABELS.keys()),
                variable=status_var,
                width=180,
                command=lambda *_: (self._sync_pool_live(), self._schedule_calc()),
            ).grid(row=i, column=1, padx=10, pady=8, sticky="w")
            self._pool_status[plot] = status_var
            entry = ctk.CTkEntry(form, width=180)
            entry.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            entry.grid(row=i, column=2, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_pool_live(), self._schedule_calc()))
            self._pe[plot] = entry

    def _sync_pool_live(self) -> None:
        if hasattr(self, "_pe") and hasattr(self, "_pool_status"):
            sync_swimming_pool(self.app_state.other, self._pe, self._pool_status)

    def _save_pool(self):
        for plot in self._plots():
            status = POOL_STATUS_LABELS.get(self._pool_status[plot].get(), POOL_NOT_APPLICABLE)
            self.app_state.other.swimming_pool_status[plot] = status
            self.app_state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
            if status == POOL_NOT_APPLICABLE:
                self.app_state.other.swimming_pool[plot] = 0.0
            else:
                self.app_state.other.swimming_pool[plot] = float(self._pe[plot].get() or 0)
        self._wizard_show_next("Swimming")

    def _hvac_ui(self, parent):
        self._he = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_hvac_live(), self._schedule_calc()))
            self._he[plot] = entry

    def _sync_hvac_live(self) -> None:
        if hasattr(self, "_he"):
            sync_hvac(self.app_state.other, self._he)

    def _plot_building_info(self, plot: str) -> tuple[float, str]:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.app_state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return max_height, btype
        project = self.app_state.project
        if project.building_height_m > 0:
            return project.building_height_m, project.building_type or "Residential Apartment"
        return 0.0, ""

    def _ugt_ui(self, parent):
        self._ugt_labels = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        row = 0
        for plot in self._plots():
            height, btype = self._plot_building_info(plot)
            ctk.CTkLabel(form, text=f"{plot} — Building Height (m)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(
                form,
                text=f"{height:.1f}" if height else "Set on Residential page",
                font=("Arial", 12),
            ).grid(row=row, column=1, padx=10, pady=8, sticky="w")
            row += 1
            ctk.CTkLabel(form, text=f"{plot} — Building Type", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(form, text=btype or "Set on Residential page", font=("Arial", 12)).grid(
                row=row, column=1, padx=10, pady=8, sticky="w"
            )
            row += 1
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            ctk.CTkLabel(form, text=f"{plot} — Fire Tank Capacity (litres)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            lbl = ctk.CTkLabel(form, text=f"{auto_val:,} (auto — NBC Table 7)", font=("Arial", 12))
            lbl.grid(row=row, column=1, padx=10, pady=8, sticky="w")
            self._ugt_labels[plot] = lbl
            row += 1
        ctk.CTkLabel(
            parent,
            text="UGT storage: Domestic 2-day, Flushing 1-day, Fire 1-day (auto-calculated in report)",
            font=("Arial", 11, "italic"),
        ).pack(anchor="w", padx=20, pady=5)

    def _refresh_ugt(self) -> None:
        for plot, lbl in getattr(self, "_ugt_labels", {}).items():
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            lbl.configure(text=f"{auto_val:,} (auto — NBC Table 7)")

    def _result_page(self, title: str, subtitle: str, table_attr: str, page_key: str):
        frame = ScrollablePage(self.container)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
            text=subtitle,
            font=("Arial", 11, "italic"),
            text_color="#555555",
        ).pack(anchor="w", padx=16, pady=(0, 4))
        table = ResultTableView(frame, embedded=True)
        table.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        setattr(self, table_attr, table)
        ctk.CTkLabel(
            frame,
            text="Updates automatically as you enter data on other pages.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 6))
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(2, 12))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda pk=page_key: self._wizard_show_previous(pk),
        ).pack(side="left")
        ctk.CTkButton(
            nav, text="Next →", width=140, fg_color=BRAND_ORANGE,
            command=lambda pk=page_key: self._wizard_show_next(pk),
        ).pack(side="right")
        return frame

    def _sewage_page(self):
        return self._result_page(
            "Sewage Generation",
            "Sewage Generation Calculations — auto-calculated from residential/commercial data.",
            "sewage_table",
            "Sewage",
        )

    def _refresh_sewage(self, silent: bool = False) -> None:
        if not hasattr(self, "sewage_table"):
            return
        if not self.app_state.environmental:
            self.sewage_table.set_rows("Sewage Generation Calculations", [("Enter project data first", "—", "")])
            return
        sections = build_sewage_generation_table_sections(
            self.app_state.project,
            self.app_state.environmental,
        )
        self.sewage_table.set_sections(sections)

    def _solid_waste_page(self):
        return self._result_page(
            "Solid Waste Generation",
            "Solid waste and e-waste calculations — auto-calculated from population and STP data.",
            "solid_waste_table",
            "SolidWaste",
        )

    def _refresh_solid_waste(self, silent: bool = False) -> None:
        if not hasattr(self, "solid_waste_table"):
            return
        if not self.app_state.environmental:
            self.solid_waste_table.set_rows("Solid Waste Calculations", [("Enter project data first", "—", "")])
            return
        sections = build_solid_waste_table_sections(
            self.app_state.project,
            self.app_state.environmental,
        )
        self.solid_waste_table.set_sections(sections)

    def _oht_page(self):
        return self._result_page(
            "OHT Details",
            "Overhead tank capacities auto-calculate from residential/commercial demand.",
            "oht_table",
            "OHT",
        )

    def _refresh_oht(self, silent: bool = False) -> None:
        if not hasattr(self, "oht_table"):
            return
        if not self.app_state.results:
            self.oht_table.set_rows("OHT Details", [("Enter residential/commercial data first", "—", "")])
            return
        sections = build_oht_table_sections(self.app_state.results, self._plots())
        self.oht_table.set_sections(sections)

    def _save_dict(self, entries, target):
        for plot, entry in entries.items():
            target[plot] = float(entry.get() or 0)

    def _stp_page(self):
        return self._result_page(
            "STP Summary",
            "Sewage treatment summary — auto-calculated from project inputs.",
            "stp_table",
            "STP",
        )

    def _refresh_stp(self, silent: bool = False):
        if not hasattr(self, "stp_table"):
            return
        if not self.app_state.results:
            self.stp_table.set_rows("STP Summary", [("Enter project data to calculate STP", "—", "")])
            return
        sections = build_stp_table_sections(self.app_state.results, self._plots())
        self.stp_table.set_sections(sections)

    def _preview_page(self):
        frame = ScrollablePage(self.container)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Report Preview", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.preview_table = ResultTableView(frame, embedded=True)
        self.preview_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ctk.CTkLabel(
            frame,
            text="Summary updates live — no Calculate button required.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 6))
        ctk.CTkButton(frame, text="Open Full Preview", fg_color="#2980B9", height=38, command=self._open_preview).pack(pady=6)
        nav = ctk.CTkFrame(frame, fg_color="transparent")
        nav.pack(fill="x", padx=16, pady=(2, 12))
        ctk.CTkButton(
            nav, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda: self._wizard_show_previous("Preview"),
        ).pack(side="left")
        ctk.CTkButton(
            nav, text="Next → Generate Report", width=190, fg_color=BRAND_ORANGE,
            command=lambda: self._navigate_to_page("Report"),
        ).pack(side="right")
        return frame

    def _refresh_preview(self, silent: bool = False) -> None:
        if not hasattr(self, "preview_table"):
            return
        if not self.app_state.results:
            self.preview_table.set_rows(
                "Preview",
                [("Complete Project, Residential, and Commercial pages first", "—", "")],
            )
            return
        sections = build_preview_table_sections(
            self.app_state.project,
            self.app_state.results,
            self._plots(),
            other=self.app_state.other,
            rwh_summary=None,
            environmental=self.app_state.environmental,
        )
        self.preview_table.set_sections(sections)

    def _settings_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Settings", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
            text=(
                f"Database:\n{DB_PATH}\n\n"
                f"Logo:\n{LOGO_PATH}\n\n"
                "NBC-2026 Standards:\n"
                "Residential 105+30 LPCD\n"
                "Landscape 6 L/sq.m\n"
                "STP 90% sewage"
            ),
            font=("Arial", 12),
            justify="left",
            anchor="w",
            wraplength=900,
        ).pack(fill="x", anchor="w", padx=20, pady=10)
        ctk.CTkButton(frame, text="Export JSON", fg_color="#2980B9", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(frame, text="Import JSON", fg_color="#2980B9", command=self._imp_json).pack(pady=8)
        ctk.CTkButton(
            frame, text="← Back", width=120, fg_color="#7F8C8D",
            command=lambda: self._wizard_show_previous("Settings"),
        ).pack(pady=(8, 14))
        return frame

    def _auto_fire_tank(self, plot: str) -> int:
        height, btype = self._plot_building_info(plot)
        if height > 0:
            return fire_tank_capacity_liters(height, btype)
        return int(self.app_state.other.fire_tank.get(plot, 0))

    def _next_from_project(self):
        self._wizard_show_next("Project")

    def _next_from_residential(self):
        self._wizard_show_next("Residential")

    def _back_from_commercial(self):
        if show_residential_section(self.app_state.project.project_type):
            self.show("Residential")
        else:
            self.show("Project")

    def _resolve_page_name(self, name: str) -> str:
        return name

    def _ensure_page_available(self, name: str) -> bool:
        if name in self.pages:
            try:
                return bool(self.pages[name].winfo_exists())
            except Exception:
                return True
        try:
            return self._build_single_page(name)
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Open Page",
                f"Unable to open '{name}'. Please check the project information and try again.\n\n{exc}",
            )
            return False

    def show(self, name: str) -> None:
        if not is_project_type_set(self.app_state.project.project_type) and name != "Project":
            name = "Project"
        name = self._resolve_page_name(name)
        allowed = visible_pages(self.app_state.project.project_type)
        if name not in allowed:
            name = "Project"

        if not self._ensure_page_available(name):
            return

        try:
            self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        except Exception:
            pass

        self._current_page = name
        page = self.pages[name]

        for key, other in list(self.pages.items()):
            if key == name:
                continue
            try:
                other.grid_remove()
            except Exception:
                pass

        _raise_page(page)
        if name == "Project" and hasattr(page, "refresh"):
            page.refresh()
        if name == "STP":
            self._refresh_stp()
        elif name == "Sewage":
            self._refresh_sewage()
        elif name == "SolidWaste":
            self._refresh_solid_waste()
        elif name == "OHT":
            self._refresh_oht()
        elif name == "Preview":
            if self._calc_dirty:
                self._calc()
            self._refresh_preview(silent=True)
        elif name == "UGT":
            self._refresh_ugt()
        elif name == "Report" and hasattr(page, "refresh"):
            page.refresh()
        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=BRAND_ORANGE if key == name else "transparent")

    def _schedule_calc(self, delay_ms: int = 300) -> None:
        self._calc_dirty = True
        if self._calc_job is not None:
            self.after_cancel(self._calc_job)
        self._calc_job = self.after(delay_ms, self._run_scheduled_calc)

    def _run_scheduled_calc(self) -> None:
        self._calc_job = None
        self._calc()

    def _calc(self):
        try:
            sync_pages_to_state(self)
            self.app_state.auto_calculate()
            self._calc_dirty = False
            self._refresh_live_panels()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _refresh_live_panels(self) -> None:
        """Update auto-calculated panels without manual refresh buttons."""
        if hasattr(self, "_ugt_labels"):
            self._refresh_ugt()
        if hasattr(self, "oht_table"):
            self._refresh_oht(silent=True)
        if hasattr(self, "stp_table"):
            self._refresh_stp(silent=True)
        if hasattr(self, "sewage_table"):
            self._refresh_sewage(silent=True)
        if hasattr(self, "solid_waste_table"):
            self._refresh_solid_waste(silent=True)
        if hasattr(self, "preview_table"):
            self._refresh_preview(silent=True)

    def _open_preview(self):
        self._calc()
        if self.app_state.results:
            PreviewDialog(
                self,
                self.app_state.project,
                self.app_state.results,
                on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
            )

    def _validate_for_report(self) -> bool:
        project = self.app_state.project
        try:
            validate_required(project.project_name, "Project Name")
            validate_required(project.client_name, "Client Name")
            validate_required(project.engineer_name, "Engineer Name")
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)
            return False
        self._calc()
        if not self.app_state.results:
            messagebox.showerror(
                "Validation Error",
                "Could not calculate water demand. Complete residential/commercial data first.",
            )
            return False
        return True

    def _generate_report_all(self) -> None:
        """One-button workflow: validate, calculate, PDF, Excel, save, preview."""
        if not self._validate_for_report():
            return
        import re

        project = self.app_state.project
        reports_dir = os.path.join(os.path.dirname(DB_PATH), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]+", "_", project.project_name or "Water_Demand")[:50].strip("_") or "Water_Demand"
        pdf_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.pdf")
        xlsx_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.xlsx")

        try:
            persist_project_state(self.app_state, db_path=DB_PATH)
            logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            export_pdf(pdf_path, self.app_state.project, self.app_state.results, logo)
            export_excel(xlsx_path, self.app_state.project, self.app_state.results)
        except Exception as exc:
            messagebox.showerror("Generate Report", str(exc))
            return

        messagebox.showinfo(
            "Generate Report",
            f"Report generated successfully.\n\nPDF: {pdf_path}\nExcel: {xlsx_path}\n\nProject saved to database.",
        )
        self.show("Preview")
        PreviewDialog(
            self,
            self.app_state.project,
            self.app_state.results,
            on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
        )

    def _new(self):
        if not messagebox.askyesno("New Project", "Start a new project? Unsaved changes will be auto-saved first."):
            return
        try:
            self._autosave_before_close()
        except Exception:
            pass
        self.app_state = create_new_project_state(db_path=DB_PATH)
        self.apply_state(self.app_state)

    def _save_db(self):
        try:
            self._calc()
            is_update = persist_project_state(self.app_state, self.current_user, DB_PATH)
            if self.on_header_update:
                self.on_header_update()
            action = "updated" if is_update else "saved"
            messagebox.showinfo("Saved", f"Project {action}.\nID: {self.app_state.project.project_id}")
            if self.on_autosave:
                self.on_autosave()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _open_db(self):
        projs = find_projects()
        if not projs:
            messagebox.showinfo("Open Project", "No saved projects.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open Project")
        dialog.geometry("640x440")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Select Project", font=("Arial", 15, "bold")).pack(pady=8)
        search_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text="Search...", width=580).pack(padx=12, pady=4)
        scroll = ctk.CTkScrollableFrame(dialog, width=600, height=300)
        scroll.pack(padx=10, pady=4)
        selected = ctk.StringVar()
        row_widgets: list = []

        def populate(query: str = "") -> None:
            for w in row_widgets:
                w.destroy()
            row_widgets.clear()
            for proj in find_projects(query):
                rb = ctk.CTkRadioButton(
                    scroll,
                    text=(
                        f"{proj['project_id']} | {proj['project_name']} | "
                        f"{proj['client_name']} | {proj.get('project_location', '')}"
                    ),
                    variable=selected,
                    value=proj["project_id"],
                )
                rb.pack(anchor="w", padx=8, pady=3)
                row_widgets.append(rb)

        search_var.trace_add("write", lambda *_: populate(search_var.get()))
        populate()

        def load_selected():
            pid = selected.get()
            if not pid:
                messagebox.showwarning("Open Project", "Select a project.")
                return
            try:
                self.apply_state(load_project_state(pid, DB_PATH))
                dialog.destroy()
                messagebox.showinfo("Loaded", f"Project loaded.\nID: {pid}")
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))

        ctk.CTkButton(dialog, text="Open", fg_color=BRAND_ORANGE, command=load_selected).pack(pady=10)

    def _exp_json(self):
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            _save_json_file(fp, self.app_state)
            messagebox.showinfo("Saved", "JSON exported.")

    def _imp_json(self):
        fp = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if fp:
            proj, res, com, oth, _ = _load_json_file(fp)
            self.app_state.project = proj
            self.app_state.residential = res
            self.app_state.commercial = com
            self.app_state.other = oth
            self.app_state.run_calculations()
            messagebox.showinfo("Loaded", "JSON imported.")


def _save_json_file(fp, state):
    snap = build_project_snapshot(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
    )
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)


def _load_json_file(fp):
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    return parse_project_snapshot(data)


# Backward-compatible alias for tests and legacy entry points
WaterDemandApp = ProjectWorkspace
