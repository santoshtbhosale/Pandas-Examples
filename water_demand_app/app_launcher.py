"""Application entry point — Splash → Project Home → unified project workflow."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import customtkinter as ctk
from PIL import Image as PILImage
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    PROJECT_TYPE_LABELS,
    PROJECT_TYPE_PLACEHOLDER,
    is_project_type_set,
    project_type_key,
    project_type_label,
)
from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from services.project_service import create_new_project_state, load_project_state
from ui.app_state import AppState
from ui.dashboard import MainDashboard
from ui.gui_safe import safe_command
from ui.splash_screen import SplashScreen

APP_VERSION = "2.0.0"
APP_TITLE = "American Edge Engineers - Water Demand Report Generator"


def _find_logo_path() -> str:
    """Find the company logo in common application locations."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(app_dir, "logo.png"),
        os.path.join(app_dir, "assets", "logo.png"),
        os.path.join(os.path.dirname(app_dir), "logo.png"),
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "assets", "logo.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return os.path.join(app_dir, "assets", "logo.png")


class Application(ctk.CTk):
    """Single main window: dashboard and project workflow share one shell."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_TITLE} v{APP_VERSION}")

        self.geometry("1360x900")
        self.minsize(1180, 760)
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        self.configure(fg_color="#F0F2F5")

        init_db(DB_PATH)
        init_lookup_tables(DB_PATH)

        self._workspace = None
        self._dashboard: Optional[MainDashboard] = None
        self._type_selector = None
        self._mode = "splash"
        self._last_saved_at = ""
        self._autosave_job = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_shell()
        self._show_splash()

    def _build_shell(self) -> None:
        self.header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=82)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(0, weight=0)
        self.header.grid_columnconfigure(1, weight=1)
        self.header.grid_columnconfigure(2, weight=0)

        self._header_logo_image = None
        self.header_logo_label = None
        logo_path = _find_logo_path()
        if logo_path and os.path.isfile(logo_path):
            try:
                logo_pil = PILImage.open(logo_path).convert("RGBA")
                max_w, max_h = 210, 60
                iw, ih = logo_pil.size
                scale = min(max_w / max(iw, 1), max_h / max(ih, 1))
                logo_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
                self._header_logo_image = ctk.CTkImage(
                    light_image=logo_pil,
                    dark_image=logo_pil,
                    size=logo_size,
                )
                self.header_logo_label = ctk.CTkLabel(
                    self.header,
                    text="",
                    image=self._header_logo_image,
                    fg_color="transparent",
                    width=logo_size[0],
                    height=logo_size[1],
                )
                self.header_logo_label.grid(
                    row=0, column=0, rowspan=2, padx=(18, 12), pady=8, sticky="w"
                )
            except Exception:
                self.header_logo_label = None

        self.header_meta = ctk.CTkLabel(
            self.header,
            text="Project Home",
            font=("Arial", 11),
            text_color="white",
            anchor="e",
        )
        self.header_meta.grid(row=0, column=2, rowspan=2, padx=(8, 18), sticky="e")

        self.body = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.status_bar = ctk.CTkFrame(self, fg_color="#E8ECF0", corner_radius=0, height=28)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Auto Calculation: ON  |  Ready",
            font=("Arial", 10),
            text_color="#555555",
            anchor="w",
        )
        self.status_label.pack(side="left", padx=12, pady=4)

    def _update_status(self) -> None:
        if self._workspace is not None and self._mode == "project":
            pid = self._workspace.app_state.project.project_id
            saved = f"Last Saved: {self._last_saved_at}" if self._last_saved_at else "Last Saved: —"
            self.status_label.configure(text=f"Project ID: {pid}  |  Auto Calculation: ON  |  {saved}")
        else:
            self.status_label.configure(text="Auto Calculation: ON  |  Project Home")

    def _update_header_meta(self) -> None:
        if self._workspace is not None and self._mode == "project":
            p = self._workspace.app_state.project
            ptype = project_type_label(p.project_type) if is_project_type_set(p.project_type) else "—"
            self.header_meta.configure(
                text=f"{p.project_name or 'Untitled'}  |  {p.project_id}  |  {ptype}"
            )
        else:
            self.header_meta.configure(text="Project Home")

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.grid_remove()

    def _show_splash(self) -> None:
        self._mode = "splash"
        self._clear_body()
        splash = SplashScreen(self.body, on_complete=self._show_dashboard)
        splash.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _show_dashboard(self) -> None:
        self._mode = "dashboard"
        self._clear_body()
        if self._workspace is not None:
            self._workspace.grid_remove()
        self._dashboard = MainDashboard(
            self.body,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_open_project=safe_command(self._open_project, parent=self),
            on_exit=self._exit_application,
        )
        self._dashboard.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _ensure_workspace(self):
        if self._workspace is not None:
            return self._workspace
        from _app_sidebar import ProjectWorkspace

        self._workspace = ProjectWorkspace(
            self.body,
            on_home=safe_command(self._show_dashboard, parent=self),
            on_autosave=self._on_project_autosaved,
            on_header_update=self._on_workspace_header_update,
            on_new_project=safe_command(self._start_new_project, parent=self),
        )
        return self._workspace

    def _show_project(self, state: AppState) -> None:
        ws = self._ensure_workspace()
        if self._dashboard is not None:
            self._dashboard.grid_remove()
        ws.grid(row=0, column=0, sticky="nsew")

        ws.app_state = state
        ws._calc_dirty = True
        ws.apply_state(state)
        ws._pages_built = True
        ws.show("Project")

        self._mode = "project"

        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

        self._schedule_autosave()
        self._update_header_meta()
        self._update_status()

    def _start_new_project(self) -> None:
        state = create_new_project_state(DB_PATH)
        self._show_project_type_selector(state)

    def _show_project_type_selector(self, state: AppState) -> None:
        self._mode = "type_selector"
        self._clear_body()
        if self._workspace is not None:
            self._workspace.grid_remove()
        if self._dashboard is not None:
            self._dashboard.grid_remove()

        if self._type_selector is not None:
            try:
                self._type_selector.destroy()
            except Exception:
                pass

        frame = ctk.CTkFrame(self.body, fg_color="#F4F6F8")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self._type_selector = frame

        card = ctk.CTkFrame(
            frame,
            fg_color="white",
            corner_radius=18,
            border_width=1,
            border_color="#DCE3EA",
            width=760,
            height=520,
        )
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="STEP 1 OF 2",
            font=("Arial", 10, "bold"),
            text_color=BRAND_ORANGE,
            fg_color="#FFF1E8",
            corner_radius=12,
            padx=12,
            pady=6,
        ).grid(row=0, column=0, pady=(34, 10))
        ctk.CTkLabel(
            card,
            text="Create a New Project",
            font=("Arial", 27, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=1, column=0, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Choose the type of project you are preparing a water-demand report for.",
            font=("Arial", 12),
            text_color="#64748B",
        ).grid(row=2, column=0, pady=(0, 22))

        section = ctk.CTkFrame(card, fg_color="#F7F9FB", corner_radius=12, border_width=1, border_color="#E3E8ED")
        section.grid(row=3, column=0, sticky="ew", padx=55, pady=0)
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            section,
            text="Project Type",
            font=("Arial", 12, "bold"),
            text_color=BRAND_NAVY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        selected = ctk.StringVar(value=PROJECT_TYPE_PLACEHOLDER)
        combo = ctk.CTkComboBox(
            section,
            values=[PROJECT_TYPE_PLACEHOLDER] + sorted(set(PROJECT_TYPE_LABELS.keys())),
            variable=selected,
            width=560,
            height=44,
            font=("Arial", 12),
        )
        combo.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        help_text = ctk.StringVar(value="Select a project type to continue.")
        help_label = ctk.CTkLabel(
            section,
            textvariable=help_text,
            font=("Arial", 10),
            text_color="#6B7280",
            anchor="w",
            justify="left",
            wraplength=540,
        )
        help_label.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))

        descriptions = {
            "Residential": "For residential buildings, apartments, villas and housing projects.",
            "Commercial": "For offices, shops, commercial buildings and business developments.",
            "Mixed Use": "For projects containing both residential and commercial components.",
            "Township": "For larger developments with multiple residential/commercial components.",
            "Hotel": "For hotels and hospitality projects.",
            "Hospital": "For hospitals and healthcare facilities.",
            "School": "For schools and educational campuses.",
            "College": "For colleges and higher-education campuses.",
            "Shopping Mall": "For malls, food courts and retail developments.",
            "Mall": "For malls, food courts and retail developments.",
            "IT Park": "For IT parks and technology office campuses.",
            "Industrial": "For industrial and manufacturing projects.",
            "Warehouse": "For warehouses and storage facilities.",
        }

        def update_help(*_):
            label = selected.get()
            if label == PROJECT_TYPE_PLACEHOLDER:
                help_text.set(
                    "Select a project type to continue. The application will then show only "
                    "the engineering sections relevant to your project."
                )
            else:
                help_text.set(
                    descriptions.get(
                        label,
                        "The application will automatically show the relevant engineering sections for this project type.",
                    )
                )

        combo.configure(command=lambda *_: update_help())
        update_help()

        ctk.CTkLabel(
            card,
            text="What happens next?",
            font=("Arial", 12, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=4, column=0, pady=(18, 4))
        ctk.CTkLabel(
            card,
            text="1. Select project type   →   2. Enter project details   →   3. Enter engineering inputs   →   4. Review & generate report",
            font=("Arial", 10),
            text_color="#687684",
        ).grid(row=5, column=0, pady=(0, 18))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=6, column=0, pady=(0, 24))

        def cancel():
            self._type_selector = None
            self._show_dashboard()

        def continue_project():
            label = selected.get()
            if label == PROJECT_TYPE_PLACEHOLDER:
                messagebox.showwarning(
                    "Project Type Required",
                    "Please select the project type before continuing.",
                )
                combo.focus_set()
                return
            state.project.project_type = project_type_key(label)
            self._type_selector = None
            if self._workspace is not None:
                try:
                    self._workspace.reset_for_new_type()
                except Exception:
                    pass
            self._show_project(state)

        ctk.CTkButton(
            buttons,
            text="← Back to Project Home",
            width=190,
            height=42,
            fg_color="#8A969C",
            hover_color="#6F7A80",
            font=("Arial", 11, "bold"),
            command=cancel,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            buttons,
            text="Continue to Project Details  →",
            width=245,
            height=42,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            font=("Arial", 11, "bold"),
            command=continue_project,
        ).pack(side="left", padx=8)

        self._update_header_meta()
        self._update_status()

    def _open_project(self, project_id: str) -> None:
        try:
            state = load_project_state(project_id, DB_PATH)
        except ValueError as exc:
            messagebox.showerror("Open Project", str(exc))
            return
        self._show_project(state)

    def _exit_application(self) -> None:
        if self._workspace is not None:
            try:
                self._workspace.autosave_before_close()
            except Exception:
                pass
        self.destroy()

    def _on_workspace_header_update(self) -> None:
        self._update_header_meta()
        self._update_status()

    def _on_project_autosaved(self) -> None:
        self._last_saved_at = datetime.now().strftime("%H:%M:%S")
        self._update_status()
        if self._dashboard is not None:
            self._dashboard.refresh_stats()

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        if self._workspace is not None and self._mode == "project":
            try:
                self._workspace.autosave_before_close()
                self._on_project_autosaved()
            except Exception:
                pass
        self._schedule_autosave()


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
