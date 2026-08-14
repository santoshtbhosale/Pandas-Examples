"""Application entry point — Splash → Project Home → unified project workflow."""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from typing import Optional

import customtkinter as ctk
from PIL import Image as PILImage
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    COMPANY_NAME,
    PROJECT_TYPE_LABELS,
    PROJECT_TYPE_PLACEHOLDER,
    is_project_type_set,
    project_type_key,
    project_type_label,
)
from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from services.project_service import create_new_project_state, load_project_state, mark_project_opened
from services.app_logging import log_exception
from ui.app_state import AppState
from ui.components.type_selector import ProjectTypeSelector
from ui.dashboard import MainDashboard
from ui.gui_safe import safe_command
from ui.splash_screen import SplashScreen
from ui.theme import COLOR_BACKGROUND, COMPANY_TAGLINE, FONT_HEADER_COMPANY, FONT_HEADER_TAGLINE

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
        self._save_state = "saved"  # saved | saving | error
        self._type_navigation_busy = False

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

        title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        title_frame.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 12), pady=8)
        ctk.CTkLabel(
            title_frame,
            text=COMPANY_NAME,
            font=FONT_HEADER_COMPANY,
            text_color="white",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame,
            text=COMPANY_TAGLINE,
            font=FONT_HEADER_TAGLINE,
            text_color="#AFC3D6",
            anchor="w",
        ).pack(anchor="w")

        self.header_meta = ctk.CTkLabel(
            self.header,
            text="Project Home",
            font=("Arial", 11),
            text_color="white",
            anchor="e",
        )
        self.header_meta.grid(row=0, column=2, rowspan=2, padx=(8, 18), sticky="e")

        self.body = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND, corner_radius=0)
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
        self.save_status_label = ctk.CTkLabel(
            self.status_bar,
            text="🟢 All changes saved",
            font=("Arial", 10),
            text_color="#555555",
            anchor="e",
        )
        self.save_status_label.pack(side="right", padx=12, pady=4)

        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", safe_command(self._on_close_request, parent=self))

    def _confirm_workspace_leave(self, action: str) -> bool:
        if self._workspace is None:
            return True
        confirm = getattr(self._workspace, "confirm_leave", None)
        if callable(confirm):
            return confirm(action)
        return True

    def _on_close_request(self) -> None:
        if self._confirm_workspace_leave("close the application"):
            self._exit_application()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-n>", lambda _e: self._shortcut_new())
        self.bind_all("<Control-N>", lambda _e: self._shortcut_new())
        self.bind_all("<Control-o>", lambda _e: self._shortcut_open())
        self.bind_all("<Control-O>", lambda _e: self._shortcut_open())
        self.bind_all("<Control-s>", lambda _e: self._shortcut_save())
        self.bind_all("<Control-S>", lambda _e: self._shortcut_save())
        self.bind_all("<Escape>", lambda _e: self.focus_set())

    def _shortcut_new(self) -> None:
        if self._mode in ("dashboard", "type_selector"):
            self._start_new_project()

    def _shortcut_open(self) -> None:
        if self._mode == "dashboard" and self._dashboard and self._dashboard.project_hub:
            self._dashboard.project_hub.focus_search()

    def _shortcut_save(self) -> None:
        if self._workspace is not None and self._mode == "project":
            try:
                self._set_save_state("saving")
                self._workspace.autosave_before_close()
                self._on_project_autosaved()
            except Exception:
                self._set_save_state("error")

    def _set_save_state(self, state: str) -> None:
        self._save_state = state
        labels = {
            "saved": "🟢 All changes saved",
            "saving": "🟠 Saving changes...",
            "error": "🔴 Unable to save changes",
        }
        self.save_status_label.configure(text=labels.get(state, labels["saved"]))

    def _update_status(self) -> None:
        if self._workspace is not None and self._mode == "project":
            pid = self._workspace.app_state.project.project_id
            saved = f"Last saved: {self._last_saved_at}" if self._last_saved_at else "Last saved: —"
            self.status_label.configure(text=f"Project ID: {pid}  |  Auto Calculation: ON  |  {saved}")
            if self._save_state == "saved":
                self._set_save_state("saved")
        else:
            self.status_label.configure(text="Auto Calculation: ON  |  Project Home")
            self.save_status_label.configure(text="")

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
        if not self._confirm_workspace_leave("return to Project Home"):
            return
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
            on_back_to_type_selector=safe_command(self._back_to_project_type_selector, parent=self),
        )
        return self._workspace

    def _destroy_type_selector(self) -> None:
        """Remove the project-type step UI so the workspace is not covered."""
        if self._type_selector is None:
            return
        try:
            self._type_selector.destroy()
        except Exception:
            traceback.print_exc()
        self._type_selector = None

    def _back_to_project_type_selector(self) -> None:
        """Return to Step 1 while keeping the current draft project state."""
        if not self._confirm_workspace_leave("return to project type selection"):
            return
        if self._workspace is None:
            self._start_new_project()
            return
        reset = getattr(self._workspace, "reset_for_new_type", None)
        if callable(reset):
            reset()
        self._show_project_type_selector(self._workspace.app_state)

    def _show_project(self, state: AppState) -> None:
        self._destroy_type_selector()
        ws = self._ensure_workspace()
        if self._dashboard is not None:
            self._dashboard.grid_remove()
        ws.grid(row=0, column=0, sticky="nsew")

        ws.app_state = state
        ws._calc_dirty = True
        ws.apply_state(state)
        ws._pages_built = True

        self._mode = "project"
        if state.project.project_id:
            try:
                mark_project_opened(state.project.project_id, DB_PATH)
            except Exception:
                traceback.print_exc()

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
        if self._mode == "project" and not self._confirm_workspace_leave("start a new project"):
            return
        state = create_new_project_state(DB_PATH)
        self._show_project_type_selector(state)

    def select_project_type(self, state: AppState, label: str) -> None:
        """Single source of truth: set type, reset workflow, open Project Details."""
        if self._type_navigation_busy:
            return
        clean = (label or "").strip()
        if not clean or clean == PROJECT_TYPE_PLACEHOLDER:
            return

        self._type_navigation_busy = True
        try:
            new_type = project_type_key(clean)
            state.apply_project_type(new_type)
            self._destroy_type_selector()
            if self._workspace is not None:
                suspend = getattr(self._workspace, "suspend_pending_work", None)
                if callable(suspend):
                    suspend()
                self._workspace.app_state = state
                self._workspace.reset_for_new_type()
            self._show_project(state)
        except Exception as exc:
            log_exception("Project type navigation failed", exc=exc, function="select_project_type")
            messagebox.showerror(
                "Navigation Error",
                "Unable to open Project Details. Please try again.",
            )
        finally:
            self._type_navigation_busy = False

    def _show_project_type_selector(self, state: AppState) -> None:
        self._mode = "type_selector"
        self._clear_body()
        if self._workspace is not None:
            suspend = getattr(self._workspace, "suspend_pending_work", None)
            if callable(suspend):
                suspend()
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
        )
        card.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="STEP 1 — SELECT PROJECT TYPE",
            font=("Arial", 9, "bold"),
            text_color=BRAND_ORANGE,
            fg_color="#FFF1E8",
            corner_radius=10,
            padx=10,
            pady=4,
        ).grid(row=0, column=0, pady=(12, 4))
        ctk.CTkLabel(
            card,
            text="Create a New Project",
            font=("Arial", 20, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=1, column=0, pady=(0, 2))
        ctk.CTkLabel(
            card,
            text="Select a project type to continue.",
            font=("Arial", 11),
            text_color="#64748B",
        ).grid(row=2, column=0, pady=(0, 6))

        initial_label = (
            project_type_label(state.project.project_type)
            if is_project_type_set(state.project.project_type)
            else PROJECT_TYPE_PLACEHOLDER
        )

        selector_wrap = ctk.CTkFrame(card, fg_color="transparent")
        selector_wrap.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 4))
        type_selector = ProjectTypeSelector(
            selector_wrap,
            initial_label=initial_label,
            on_project_type_selected=lambda lbl: self.select_project_type(state, lbl),
        )
        type_selector.pack(fill="x")
        if initial_label != PROJECT_TYPE_PLACEHOLDER:
            type_selector.set_selected(initial_label)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=4, column=0, pady=(4, 12))

        def cancel():
            if not self._confirm_workspace_leave("return to Project Home"):
                return
            self._destroy_type_selector()
            self._show_dashboard()

        ctk.CTkButton(
            buttons,
            text="← Back to Project Home",
            width=200,
            height=36,
            fg_color="#8A969C",
            hover_color="#6F7A80",
            font=("Arial", 11, "bold"),
            command=cancel,
        ).pack()

        self._update_header_meta()
        self._update_status()

    def _open_project(self, project_id: str) -> None:
        if not self._confirm_workspace_leave("open another project"):
            return
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
        try:
            from services.database_backup import backup_database

            backup_database(DB_PATH, reason="exit")
        except Exception:
            pass
        self.destroy()

    def _on_workspace_header_update(self) -> None:
        self._update_header_meta()
        self._update_status()

    def _on_project_autosaved(self) -> None:
        self._last_saved_at = datetime.now().strftime("%H:%M:%S")
        self._set_save_state("saved")
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
