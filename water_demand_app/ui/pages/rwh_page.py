"""Rain Water Harvesting GUI page — CustomTkinter, matches app theme."""

from __future__ import annotations

import os
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from rwh.calculator import RWHCalculator, default_surfaces
from rwh.config import CATCHMENT_SURFACES, RWH_HEADER_TEAL
from rwh.database import init_rwh_db, list_rwh_projects, load_rwh_project, save_rwh_project
from rwh.models import RWHCatchmentSurface, RWHProjectData, RWHResults
from rwh.pdf_exporter import export_rwh_pdf
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_float, validate_required


class RWHPage(ScrollablePage):
    """Standalone Rain Water Harvesting module screen."""

    SURFACE_TYPES = list(CATCHMENT_SURFACES.keys())

    def __init__(
        self,
        master,
        logo_path: Optional[str] = None,
        db_path: Optional[str] = None,
        on_back: Optional[Callable] = None,
        seed_project: Optional[Any] = None,
    ) -> None:
        super().__init__(master)
        self.logo_path = logo_path
        self.db_path = db_path
        self.on_back = on_back
        self.seed_project = seed_project
        self.project = RWHProjectData(surfaces=default_surfaces())
        self.results: Optional[RWHResults] = None
        self.meta_entries: Dict[str, ctk.CTkEntry] = {}
        self.param_entries: Dict[str, ctk.CTkEntry] = {}
        self.surface_rows: List[Dict[str, Any]] = []
        self._build()
        init_rwh_db(self.db_path)
        if seed_project is not None:
            self._seed_from_water_demand(seed_project)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header,
            text="Rain Water Harvesting",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(
            header,
            text="Independent Module",
            font=("Arial", 11),
            text_color=RWH_HEADER_TEAL,
        ).pack(side="right", padx=16)

        ctk.CTkLabel(
            self,
            text="Estimate annual harvestable rainwater from catchment surfaces and size storage tanks. "
            "This module is separate from Water Demand calculations.",
            font=("Arial", 12),
            text_color="#555555",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self._build_meta_form()
        self._build_params_form()
        self._build_surfaces_section()
        self._build_results_panel()
        self._build_actions()

    def _section(self, title: str, color: str = BRAND_NAVY) -> ctk.CTkFrame:
        box = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#D0D5DD")
        box.pack(fill="x", padx=15, pady=8)
        bar = ctk.CTkFrame(box, fg_color=color, corner_radius=6)
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(bar, text=title, font=("Arial", 14, "bold"), text_color="white").pack(pady=6)
        body = ctk.CTkFrame(box, fg_color="transparent")
        body.pack(fill="x", padx=12, pady=(0, 12))
        return body

    def _build_meta_form(self) -> None:
        body = self._section("Project Details")
        fields = [
            ("project_name", "Project Name", self.project.project_name),
            ("client_name", "Client Name", self.project.client_name),
            ("project_location", "Location", self.project.project_location),
            ("engineer_name", "Engineer", self.project.engineer_name),
            ("project_no", "Project No.", self.project.project_no),
            ("date", "Date (DD-MM-YYYY)", self.project.date),
        ]
        for i, (key, label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            ctk.CTkLabel(body, text=label, font=("Arial", 12)).grid(row=r, column=c * 2, padx=8, pady=6, sticky="w")
            ent = ctk.CTkEntry(body, width=220)
            ent.insert(0, value)
            ent.grid(row=r, column=c * 2 + 1, padx=8, pady=6, sticky="w")
            self.meta_entries[key] = ent

    def _build_params_form(self) -> None:
        body = self._section("Climate & System Parameters", color=RWH_HEADER_TEAL)
        fields = [
            ("annual_rainfall_mm", "Annual Rainfall (mm)", str(self.project.annual_rainfall_mm)),
            ("rainy_days", "Rainy Days / Year", str(self.project.rainy_days)),
            ("max_daily_rainfall_mm", "Max Daily Rainfall (mm)", str(self.project.max_daily_rainfall_mm)),
            ("collection_efficiency", "Collection Efficiency (0-1)", str(self.project.collection_efficiency)),
            ("proposed_tank_liters", "Proposed Tank (L, 0=auto)", str(self.project.proposed_tank_liters)),
        ]
        for i, (key, label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            ctk.CTkLabel(body, text=label, font=("Arial", 12)).grid(row=r, column=c * 2, padx=8, pady=6, sticky="w")
            ent = ctk.CTkEntry(body, width=180)
            ent.insert(0, value)
            ent.grid(row=r, column=c * 2 + 1, padx=8, pady=6, sticky="w")
            self.param_entries[key] = ent
        ctk.CTkLabel(body, text="Notes", font=("Arial", 12)).grid(row=3, column=0, padx=8, pady=6, sticky="nw")
        self.notes_box = ctk.CTkTextbox(body, width=520, height=60, font=("Arial", 12))
        self.notes_box.grid(row=3, column=1, columnspan=3, padx=8, pady=6, sticky="w")
        if self.project.notes:
            self.notes_box.insert("1.0", self.project.notes)

    def _build_surfaces_section(self) -> None:
        body = self._section("Catchment Surfaces", color=BRAND_ORANGE)
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(btn_row, text="+ Add Surface", fg_color="#27AE60", width=120, command=lambda: self._add_surface_row()).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Load Defaults", fg_color="#2980B9", width=120, command=self._load_default_surfaces).pack(side="left", padx=4)

        self.surfaces_frame = ctk.CTkFrame(body, fg_color="#FFFFFF")
        self.surfaces_frame.pack(fill="x")
        headers = ["Label", "Surface Type", "Area (m²)", "Runoff Coeff.", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.surfaces_frame, text=h, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=4, pady=4)
        for surf in self.project.surfaces:
            self._add_surface_row(surf)
        if not self.surface_rows:
            self._add_surface_row()

    def _build_results_panel(self) -> None:
        body = self._section("Calculation Results", color="#8E44AD")
        self.results_box = ctk.CTkTextbox(body, height=180, font=("Courier", 12))
        self.results_box.pack(fill="x", padx=4, pady=4)
        self.results_box.insert("1.0", "Click Calculate to compute harvestable rainwater and tank sizing.")
        self.results_box.configure(state="disabled")

    def _build_actions(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(pady=16)
        if self.on_back:
            ctk.CTkButton(bar, text="<- Back", fg_color="gray", width=100, command=self.on_back).grid(row=0, column=0, padx=6)
        ctk.CTkButton(bar, text="Calculate", fg_color=BRAND_ORANGE, width=120, command=self._calculate).grid(row=0, column=1, padx=6)
        ctk.CTkButton(bar, text="Save to Database", fg_color="#16A085", width=140, command=self._save_db).grid(row=0, column=2, padx=6)
        ctk.CTkButton(bar, text="Open from DB", fg_color="#2980B9", width=120, command=self._open_db).grid(row=0, column=3, padx=6)
        ctk.CTkButton(bar, text="Export PDF", fg_color="#C0392B", width=120, command=self._export_pdf).grid(row=0, column=4, padx=6)
        ctk.CTkButton(bar, text="Copy WD Project Info", fg_color="#8E44AD", width=160, command=self._copy_wd_meta).grid(row=0, column=5, padx=6)

    def _add_surface_row(self, surf: Optional[RWHCatchmentSurface] = None) -> None:
        r = len(self.surface_rows) + 1
        label_ent = ctk.CTkEntry(self.surfaces_frame, width=160)
        label_ent.insert(0, (surf.label if surf else ""))
        type_var = ctk.StringVar(value=surf.surface_type if surf else "RCC Roof")
        type_cb = ctk.CTkComboBox(
            self.surfaces_frame,
            values=self.SURFACE_TYPES,
            variable=type_var,
            width=140,
            command=lambda _v, row_idx=None: self._on_type_change(len(self.surface_rows)),
        )
        area_ent = ctk.CTkEntry(self.surfaces_frame, width=100)
        area_ent.insert(0, str(surf.area_sqm if surf else ""))
        coeff_ent = ctk.CTkEntry(self.surfaces_frame, width=90)
        coeff_ent.insert(0, str(surf.runoff_coefficient if surf else CATCHMENT_SURFACES["RCC Roof"].runoff_coefficient))

        label_ent.grid(row=r, column=0, padx=4, pady=4)
        type_cb.grid(row=r, column=1, padx=4, pady=4)
        area_ent.grid(row=r, column=2, padx=4, pady=4)
        coeff_ent.grid(row=r, column=3, padx=4, pady=4)

        row_data = {
            "label": label_ent,
            "type": type_var,
            "type_cb": type_cb,
            "area": area_ent,
            "coeff": coeff_ent,
            "widgets": [label_ent, type_cb, area_ent, coeff_ent],
        }

        def remove(rd=row_data):
            for w in rd["widgets"]:
                w.destroy()
            if rd.get("rm"):
                rd["rm"].destroy()
            self.surface_rows = [x for x in self.surface_rows if x is not rd]
            self._regrid_surfaces()

        rm = ctk.CTkButton(self.surfaces_frame, text="X", width=32, fg_color="#C0392B", command=remove)
        rm.grid(row=r, column=4, padx=4, pady=4)
        row_data["rm"] = rm
        row_data["widgets"].append(rm)
        self.surface_rows.append(row_data)
        # Bind type change for this row
        type_cb.configure(command=lambda _v, rd=row_data: self._sync_coeff_for_row(rd))

    def _sync_coeff_for_row(self, row: Dict[str, Any]) -> None:
        stype = row["type"].get()
        spec = CATCHMENT_SURFACES.get(stype)
        if spec and stype != "Custom":
            row["coeff"].delete(0, "end")
            row["coeff"].insert(0, str(spec.runoff_coefficient))

    def _on_type_change(self, _idx: int) -> None:
        pass

    def _regrid_surfaces(self) -> None:
        for i, row in enumerate(self.surface_rows, 1):
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=4, pady=4)

    def _load_default_surfaces(self) -> None:
        for row in self.surface_rows:
            for w in row["widgets"]:
                w.destroy()
        self.surface_rows.clear()
        for surf in default_surfaces():
            self._add_surface_row(surf)

    def _collect(self) -> RWHProjectData:
        name = validate_required(self.meta_entries["project_name"].get(), "Project Name")
        surfaces: List[RWHCatchmentSurface] = []
        for i, row in enumerate(self.surface_rows):
            area_raw = row["area"].get().strip()
            if not area_raw:
                continue
            area = validate_positive_float(area_raw, f"Surface area #{i + 1}", allow_zero=False)
            coeff = validate_positive_float(row["coeff"].get(), f"Runoff coeff #{i + 1}", allow_zero=False)
            if coeff > 1:
                raise ValidationError("Runoff coefficient must be between 0 and 1.")
            surfaces.append(
                RWHCatchmentSurface(
                    surface_type=row["type"].get(),
                    area_sqm=area,
                    runoff_coefficient=coeff,
                    label=row["label"].get().strip() or row["type"].get(),
                    sort_order=i,
                )
            )
        if not surfaces:
            raise ValidationError("Add at least one catchment surface with area > 0.")

        eff = validate_positive_float(self.param_entries["collection_efficiency"].get(), "Collection Efficiency", allow_zero=False)
        if eff > 1:
            raise ValidationError("Collection efficiency must be between 0 and 1 (e.g. 0.90).")

        return RWHProjectData(
            rwh_id=self.project.rwh_id,
            project_name=name,
            client_name=self.meta_entries["client_name"].get().strip(),
            project_location=self.meta_entries["project_location"].get().strip(),
            engineer_name=self.meta_entries["engineer_name"].get().strip() or "AKASH KHADE",
            project_no=self.meta_entries["project_no"].get().strip(),
            date=self.meta_entries["date"].get().strip(),
            annual_rainfall_mm=validate_positive_float(self.param_entries["annual_rainfall_mm"].get(), "Annual Rainfall", allow_zero=False),
            rainy_days=int(validate_positive_float(self.param_entries["rainy_days"].get(), "Rainy Days", allow_zero=False)),
            max_daily_rainfall_mm=validate_positive_float(self.param_entries["max_daily_rainfall_mm"].get(), "Max Daily Rainfall", allow_zero=False),
            collection_efficiency=eff,
            proposed_tank_liters=validate_positive_float(self.param_entries["proposed_tank_liters"].get(), "Proposed Tank", allow_zero=True),
            notes=self.notes_box.get("1.0", "end").strip(),
            surfaces=surfaces,
        )

    def _calculate(self) -> None:
        try:
            self.project = self._collect()
            self.results = RWHCalculator(self.project).calculate()
            self._show_results()
        except ValidationError as ex:
            messagebox.showerror("Validation Error", ex.message)
        except Exception as ex:
            messagebox.showerror("Calculation Error", str(ex))

    def _show_results(self) -> None:
        if not self.results:
            return
        r = self.results
        lines = [
            "RAIN WATER HARVESTING — RESULTS",
            "=" * 48,
            f"Total Catchment Area     : {r.total_catchment_sqm:,.1f} m²",
            f"Annual Harvestable Water : {r.annual_harvest_liters:,.0f} Litres  ({r.annual_harvest_cum:,.2f} m³)",
            f"Daily Average            : {r.daily_average_liters:,.1f} Litres/day",
            f"Peak Day Potential       : {r.peak_day_liters:,.0f} Litres",
            f"Recommended Tank         : {r.recommended_tank_liters:,.0f} Litres",
            f"Design Tank Capacity     : {r.design_tank_liters:,.0f} Litres",
            "",
            "Surface Breakdown:",
        ]
        for i, s in enumerate(r.surfaces, 1):
            lines.append(
                f"  {i}. {s.label} [{s.surface_type}]  "
                f"{s.area_sqm:.0f} m² × K={s.runoff_coefficient:.2f}  →  {s.annual_harvest_liters:,.0f} L/yr"
            )
        self.results_box.configure(state="normal")
        self.results_box.delete("1.0", "end")
        self.results_box.insert("1.0", "\n".join(lines))
        self.results_box.configure(state="disabled")

    def _save_db(self) -> None:
        try:
            if not self.results:
                self._calculate()
            if not self.results:
                return
            save_rwh_project(self.project, self.results, self.db_path)
            messagebox.showinfo("Saved", "Rain Water Harvesting project saved to database.")
        except ValidationError as ex:
            messagebox.showerror("Validation Error", ex.message)
        except Exception as ex:
            messagebox.showerror("Save Error", str(ex))

    def _open_db(self) -> None:
        projects = list_rwh_projects(self.db_path)
        if not projects:
            messagebox.showinfo("Open", "No saved Rain Water Harvesting projects found.")
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Open RWH Project")
        dlg.geometry("560x360")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        ctk.CTkLabel(dlg, text="Select a saved RWH project", font=("Arial", 14, "bold")).pack(pady=10)
        box = ctk.CTkTextbox(dlg, height=220, font=("Courier", 11))
        box.pack(fill="both", expand=True, padx=12, pady=6)
        for i, p in enumerate(projects, 1):
            box.insert(
                "end",
                f"{i}. {p['project_name']} | {p['client_name']} | {p['date']} | "
                f"Harvest {float(p['annual_harvest_liters']):,.0f} L\n",
            )
        box.configure(state="disabled")
        idx_ent = ctk.CTkEntry(dlg, width=80, placeholder_text="No.")
        idx_ent.pack(pady=6)

        def load():
            try:
                idx = int(idx_ent.get().strip()) - 1
                snap = load_rwh_project(projects[idx]["rwh_id"], self.db_path)
                self.project = RWHProjectData.from_dict(snap["project"])
                self.results = RWHResults.from_dict(snap.get("results"))
                self._populate_form()
                self._show_results() if self.results else None
                dlg.destroy()
            except Exception as ex:
                messagebox.showerror("Open Error", str(ex))

        ctk.CTkButton(dlg, text="Load", fg_color=BRAND_ORANGE, command=load).pack(pady=8)

    def _populate_form(self) -> None:
        mapping = {
            "project_name": self.project.project_name,
            "client_name": self.project.client_name,
            "project_location": self.project.project_location,
            "engineer_name": self.project.engineer_name,
            "project_no": self.project.project_no,
            "date": self.project.date,
        }
        for key, value in mapping.items():
            ent = self.meta_entries[key]
            ent.delete(0, "end")
            ent.insert(0, value)
        params = {
            "annual_rainfall_mm": self.project.annual_rainfall_mm,
            "rainy_days": self.project.rainy_days,
            "max_daily_rainfall_mm": self.project.max_daily_rainfall_mm,
            "collection_efficiency": self.project.collection_efficiency,
            "proposed_tank_liters": self.project.proposed_tank_liters,
        }
        for key, value in params.items():
            ent = self.param_entries[key]
            ent.delete(0, "end")
            ent.insert(0, str(value))
        self.notes_box.delete("1.0", "end")
        self.notes_box.insert("1.0", self.project.notes)
        for row in self.surface_rows:
            for w in row["widgets"]:
                w.destroy()
        self.surface_rows.clear()
        for surf in self.project.surfaces:
            self._add_surface_row(surf)
        if not self.surface_rows:
            self._add_surface_row()

    def _export_pdf(self) -> None:
        try:
            if not self.results:
                self._calculate()
            if not self.results:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile="Rain_Water_Harvesting_Report.pdf",
            )
            if not path:
                return
            logo = self.logo_path if self.logo_path and os.path.exists(self.logo_path) else None
            export_rwh_pdf(path, self.project, self.results, logo)
            messagebox.showinfo("Success", "Rain Water Harvesting PDF exported successfully!")
        except ValidationError as ex:
            messagebox.showerror("Validation Error", ex.message)
        except Exception as ex:
            messagebox.showerror("PDF Error", str(ex))

    def _seed_from_water_demand(self, project: Any) -> None:
        """Optional: prefill meta from Water Demand project without coupling calculations."""
        try:
            if getattr(project, "project_name", ""):
                self.meta_entries["project_name"].delete(0, "end")
                self.meta_entries["project_name"].insert(0, project.project_name)
            if getattr(project, "client_name", ""):
                self.meta_entries["client_name"].delete(0, "end")
                self.meta_entries["client_name"].insert(0, project.client_name)
            if getattr(project, "project_location", ""):
                self.meta_entries["project_location"].delete(0, "end")
                self.meta_entries["project_location"].insert(0, project.project_location)
            if getattr(project, "engineer_name", ""):
                self.meta_entries["engineer_name"].delete(0, "end")
                self.meta_entries["engineer_name"].insert(0, project.engineer_name)
            if getattr(project, "project_no", ""):
                self.meta_entries["project_no"].delete(0, "end")
                self.meta_entries["project_no"].insert(0, project.project_no)
            if getattr(project, "date", ""):
                self.meta_entries["date"].delete(0, "end")
                self.meta_entries["date"].insert(0, project.date)
        except Exception:
            pass

    def _copy_wd_meta(self) -> None:
        if self.seed_project is None:
            messagebox.showinfo("Info", "No Water Demand project is linked for copying.")
            return
        self._seed_from_water_demand(self.seed_project)
        messagebox.showinfo("Copied", "Project details copied from Water Demand module.")

    def refresh(self) -> None:
        """Called by app shell when page is shown — refresh seed meta hint only."""
        if self.seed_project is not None and not self.meta_entries["project_name"].get().strip():
            self._seed_from_water_demand(self.seed_project)
