from __future__ import annotations

import os
import sys
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE, show_commercial_section, show_residential_section
from services.database import init_db, list_projects, load_project_from_db
from services.json_io import load_project_json, save_project_json
from ui.app_state import AppState
from ui.pages.commercial_page import CommercialPage
from ui.pages.final_page import FinalPage
from ui.pages.other_page import OtherPage
from ui.pages.project_page import ProjectPage
from ui.pages.residential_page import ResidentialPage
from ui.pages.rwh_page import RWHPage
from rwh.database import init_rwh_db


class WaterDemandApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.state = AppState()
        self.title("Water Demand Report Generator - Advanced 8-Page Edition")
        self.geometry("1100x800")
        self.minsize(1000, 700)
        self.configure(fg_color="#F5F6FA")

        init_db()
        init_rwh_db()

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_menu()
        self._build_nav()
        self.container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.container.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames: dict = {}
        self._create_pages()
        self.show_frame("Project")

    def _build_menu(self) -> None:
        menubar_frame = ctk.CTkFrame(self, height=35, fg_color=BRAND_NAVY, corner_radius=0)
        menubar_frame.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            menubar_frame, text="New Project", width=100, height=28,
            fg_color="transparent", hover_color=BRAND_ORANGE, command=self._new_project,
        ).pack(side="left", padx=5, pady=3)
        ctk.CTkButton(
            menubar_frame, text="Open JSON", width=100, height=28,
            fg_color="transparent", hover_color=BRAND_ORANGE, command=self._open_json,
        ).pack(side="left", padx=5, pady=3)
        ctk.CTkButton(
            menubar_frame, text="Save JSON", width=100, height=28,
            fg_color="transparent", hover_color=BRAND_ORANGE, command=self._save_json,
        ).pack(side="left", padx=5, pady=3)
        ctk.CTkButton(
            menubar_frame, text="Open from DB", width=110, height=28,
            fg_color="transparent", hover_color=BRAND_ORANGE, command=self._open_db,
        ).pack(side="left", padx=5, pady=3)

    def _build_nav(self) -> None:
        nav = ctk.CTkFrame(self, height=45, fg_color="#ECF0F1")
        nav.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.nav_buttons: dict = {}
        pages = [
            ("Project", "1. Project"),
            ("Residential", "2. Residential"),
            ("Commercial", "3. Commercial"),
            ("Other", "4. Other"),
            ("Final", "5. Report"),
            ("RWH", "6. Rain Water Harvesting"),
        ]
        for key, label in pages:
            btn = ctk.CTkButton(
                nav, text=label, width=130, height=32,
                fg_color="#BDC3C7", text_color="#2C3E50",
                hover_color=BRAND_ORANGE,
                command=lambda k=key: self.show_frame(k),
            )
            btn.pack(side="left", padx=4, pady=6)
            self.nav_buttons[key] = btn

    def _create_pages(self) -> None:
        self.frames["Project"] = ProjectPage(self.container, self.state, on_next=self._next_from_project)
        self.frames["Residential"] = ResidentialPage(
            self.container, self.state,
            on_next=self._next_from_residential,
            on_back=lambda: self.show_frame("Project"),
        )
        self.frames["Commercial"] = CommercialPage(
            self.container, self.state,
            on_next=lambda: self.show_frame("Other"),
            on_back=self._back_from_commercial,
        )
        self.frames["Other"] = OtherPage(
            self.container, self.state,
            on_calculate=self._calculate_and_show,
            on_back=lambda: self.show_frame("Commercial"),
        )
        self.frames["Final"] = FinalPage(
            self.container, self.state,
            on_back=lambda: self.show_frame("Other"),
        )
        logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
        self.frames["RWH"] = RWHPage(
            self.container,
            logo_path=logo if os.path.exists(logo) else None,
            on_back=lambda: self.show_frame("Final"),
            seed_project=self.state.project,
        )
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def _next_from_project(self) -> None:
        ptype = self.state.project.project_type
        if show_residential_section(ptype):
            self.show_frame("Residential")
        elif show_commercial_section(ptype):
            self.show_frame("Commercial")
        else:
            self.show_frame("Other")

    def _next_from_residential(self) -> None:
        if show_commercial_section(self.state.project.project_type):
            self.show_frame("Commercial")
        else:
            self.show_frame("Other")

    def _back_from_commercial(self) -> None:
        if show_residential_section(self.state.project.project_type):
            self.show_frame("Residential")
        else:
            self.show_frame("Project")

    def _update_nav_visibility(self) -> None:
        ptype = self.state.project.project_type
        show_res = show_residential_section(ptype)
        show_com = show_commercial_section(ptype)
        if "Residential" in self.nav_buttons:
            self.nav_buttons["Residential"].pack_forget()
            if show_res:
                self.nav_buttons["Residential"].pack(side="left", padx=4, pady=6)
        if "Commercial" in self.nav_buttons:
            self.nav_buttons["Commercial"].pack_forget()
            if show_com:
                self.nav_buttons["Commercial"].pack(side="left", padx=4, pady=6)

    def show_frame(self, page_name: str) -> None:
        ptype = self.state.project.project_type
        if page_name == "Residential" and not show_residential_section(ptype):
            page_name = "Commercial" if show_commercial_section(ptype) else "Other"
        if page_name == "Commercial" and not show_commercial_section(ptype):
            page_name = "Residential" if show_residential_section(ptype) else "Other"
        if page_name not in self.frames:
            messagebox.showwarning("Navigation", f"The '{page_name}' page is not available.")
            return
        frame = self.frames[page_name]
        if hasattr(frame, "lift"):
            frame.lift()
        elif hasattr(frame, "_parent_frame"):
            frame._parent_frame.tkraise()
        else:
            frame.tkraise()
        if hasattr(frame, "refresh"):
            frame.refresh()
        self._update_nav_visibility()
        for key, btn in self.nav_buttons.items():
            if key == page_name:
                btn.configure(fg_color=BRAND_ORANGE, text_color="white")
            else:
                btn.configure(fg_color="#BDC3C7", text_color="#2C3E50")

    def _calculate_and_show(self) -> None:
        try:
            self.state.run_calculations()
            self.show_frame("Final")
        except Exception as exc:
            messagebox.showerror("Calculation Error", str(exc))

    def _new_project(self) -> None:
        if messagebox.askyesno("New Project", "Start a new project? Unsaved changes will be lost."):
            self.state = AppState()
            self._recreate_pages()

    def _recreate_pages(self) -> None:
        for frame in self.frames.values():
            frame.destroy()
        self.frames.clear()
        self._create_pages()
        self.show_frame("Project")

    def _open_json(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Water Demand Project", "*.wdproj.json"), ("JSON files", "*.json")],
        )
        if not file_path:
            return
        try:
            project, residential, commercial, other, calculated = load_project_json(file_path)
            self.state.project = project
            self.state.residential = residential
            self.state.commercial = commercial
            self.state.other = other
            self.state.run_calculations()
            self._recreate_pages()
            messagebox.showinfo("Success", "Project loaded successfully!")
        except Exception as exc:
            messagebox.showerror("Open Error", str(exc))

    def _save_json(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Water Demand Project", "*.wdproj.json"), ("JSON files", "*.json")],
            initialfile=f"{self.state.project.project_id}.wdproj.json",
        )
        if not file_path:
            return
        try:
            save_project_json(
                file_path,
                self.state.project,
                self.state.residential,
                self.state.commercial,
                self.state.other,
                self.state.results.to_dict() if self.state.results else None,
            )
            messagebox.showinfo("Success", "Project saved successfully!")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))

    def _open_db(self) -> None:
        projects = list_projects()
        if not projects:
            messagebox.showinfo("Database", "No saved projects found in database.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open Project from Database")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Select a project:", font=("Arial", 14, "bold")).pack(pady=10)
        listbox_frame = ctk.CTkScrollableFrame(dialog, width=460, height=280)
        listbox_frame.pack(padx=10, pady=5)

        selected_id = ctk.StringVar()

        for proj in projects:
            label = f"{proj['project_name']} | {proj['client_name']} | {proj['date']}"
            ctk.CTkRadioButton(
                listbox_frame, text=label, variable=selected_id, value=proj["project_id"],
            ).pack(anchor="w", padx=10, pady=3)

        def load_selected():
            pid = selected_id.get()
            if not pid:
                messagebox.showwarning("Select", "Please select a project.")
                return
            try:
                data = load_project_from_db(pid)
                from services.database import parse_project_snapshot
                project, residential, commercial, other, calculated = parse_project_snapshot(data)
                self.state.project = project
                self.state.residential = residential
                self.state.commercial = commercial
                self.state.other = other
                self.state.run_calculations()
                self._recreate_pages()
                dialog.destroy()
                messagebox.showinfo("Success", "Project loaded from database!")
            except Exception as exc:
                messagebox.showerror("Load Error", str(exc))

        ctk.CTkButton(dialog, text="Load", command=load_selected, fg_color=BRAND_ORANGE).pack(pady=10)


def run_app() -> None:
    app = WaterDemandApp()
    app.mainloop()
