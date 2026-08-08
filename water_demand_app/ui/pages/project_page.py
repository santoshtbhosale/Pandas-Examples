from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    BUILDING_CONFIG_EXAMPLES,
    BUILDING_TYPES,
    PLOT_MODE_LABELS,
    PROJECT_TYPE_LABELS,
    PROJECT_TYPE_PLACEHOLDER,
    STAFF_NAMES,
    is_project_type_set,
    parse_building_config,
    project_type_key,
    project_type_label,
)
from config.page_visibility import visible_nav_labels
from models.project import RevisionInfo
from services.lookup_db import next_project_number, search_clients, search_locations, upsert_client, upsert_location
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_int, validate_required


class ProjectPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_type_change=None) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_type_change = on_type_change
        self.entries: dict = {}
        self._details_visible = False
        self._build()

    def _build(self) -> None:
        self.header_label = ctk.CTkLabel(self, text="", font=("Arial", 22, "bold"), text_color=BRAND_NAVY)
        self.header_label.pack(pady=(10, 4))

        self.header_frame = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        self.header_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.header_title = ctk.CTkLabel(
            self.header_frame, text="", font=("Arial", 18, "bold"), text_color="white"
        )
        self.header_title.pack(pady=12)
        ctk.CTkLabel(
            self.header_frame, text="American Edge Engineers Pvt. Ltd.", font=("Arial", 12), text_color=BRAND_ORANGE
        ).pack(pady=(0, 10))

        self.type_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        self.type_frame.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            self.type_frame,
            text="Project Type",
            font=("Arial", 16, "bold"),
            text_color=BRAND_NAVY,
        ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            self.type_frame,
            text="Select the building use type. Only relevant workflow tabs will appear.",
            font=("Arial", 11),
            text_color="#666666",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        type_row = ctk.CTkFrame(self.type_frame, fg_color="transparent")
        type_row.pack(fill="x", padx=20, pady=(0, 8))
        initial_label = project_type_label(self.state.project.project_type)
        self.project_type_var = ctk.StringVar(value=initial_label)
        type_values = [PROJECT_TYPE_PLACEHOLDER] + sorted(set(PROJECT_TYPE_LABELS.keys()))
        self.type_combo = ctk.CTkComboBox(
            type_row,
            values=type_values,
            variable=self.project_type_var,
            width=420,
            command=self._on_project_type_selected,
        )
        self.type_combo.pack(side="left")

        self.workflow_hint = ctk.CTkLabel(
            self.type_frame,
            text="",
            font=("Arial", 11, "italic"),
            text_color=BRAND_ORANGE,
            wraplength=700,
            justify="left",
        )
        self.workflow_hint.pack(anchor="w", padx=20, pady=(4, 16))

        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form = ctk.CTkFrame(self.details_frame)
        self.form.pack(fill="both", expand=True, padx=20, pady=10)
        row = 0

        for key, label, default in [
            ("project_name", "Project Name", "PROPOSED RESIDENTIAL & COMM. AT PUNAVALE"),
            ("client_name", "Client Name", "MR.PRATHMESH GAIKWAD"),
            ("project_location", "Location", "PUNAVALE, PUNE"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
            ent = ctk.CTkEntry(self.form, width=400)
            val = getattr(self.state.project, key if key != "project_location" else "project_location", default)
            ent.insert(0, val or default)
            ent.grid(row=row, column=1, padx=20, pady=8, sticky="w")
            self.entries[key] = ent
            if key == "client_name":
                ent.bind("<KeyRelease>", self._on_client_type)
            if key == "project_location":
                ent.bind("<KeyRelease>", self._on_location_type)
            row += 1

        for key, label, attr in [
            ("client_address", "Client Address", "client_address"),
            ("client_contact", "Contact", "client_contact"),
            ("client_email", "Email", "client_email"),
            ("client_gst", "GST", "client_gst"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 13)).grid(row=row, column=0, padx=20, pady=6, sticky="w")
            ent = ctk.CTkEntry(self.form, width=400)
            ent.insert(0, getattr(self.state.project, attr, "") or "")
            ent.grid(row=row, column=1, padx=20, pady=6, sticky="w")
            self.entries[key] = ent
            row += 1

        ctk.CTkLabel(self.form, text="Building Configuration", font=("Arial", 14)).grid(
            row=row, column=0, padx=20, pady=8, sticky="w"
        )
        self.building_config_var = ctk.StringVar(value=self.state.project.building_config or "G+7")
        ctk.CTkComboBox(
            self.form,
            values=list(BUILDING_CONFIG_EXAMPLES),
            variable=self.building_config_var,
            width=400,
            command=lambda *_: self._sync_building_height(),
        ).grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Height (m)", font=("Arial", 14)).grid(
            row=row, column=0, padx=20, pady=8, sticky="w"
        )
        self.height_entry = ctk.CTkEntry(self.form, width=120)
        self.height_entry.insert(0, str(self.state.project.building_height_m or ""))
        self.height_entry.grid(row=row, column=1, padx=20, pady=8, sticky="w")
        self.height_entry.bind("<KeyRelease>", lambda *_: self._sync_building_height())
        row += 1

        ctk.CTkLabel(self.form, text="Number of Wings", font=("Arial", 14)).grid(
            row=row, column=0, padx=20, pady=8, sticky="w"
        )
        self.wings_entry = ctk.CTkEntry(self.form, width=120)
        self.wings_entry.insert(0, str(self.state.project.num_wings or 1))
        self.wings_entry.grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Type", font=("Arial", 14)).grid(
            row=row, column=0, padx=20, pady=8, sticky="w"
        )
        self.building_type_var = ctk.StringVar(value=self.state.project.building_type or BUILDING_TYPES[0])
        ctk.CTkComboBox(
            self.form, values=list(BUILDING_TYPES), variable=self.building_type_var, width=400
        ).grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        for label, attr, default in [
            ("Engineer Name", "engineer_var", "Akash"),
            ("Prepared By", "prepared_var", "Akash"),
            ("Checked By", "checked_var", "Akash"),
            ("Approved By", "approved_var", "Omkar"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
            if label == "Engineer Name":
                existing = self.state.project.engineer_name
            elif label == "Prepared By":
                existing = self.state.project.revision.prepared_by
            elif label == "Checked By":
                existing = self.state.project.revision.checked_by
            else:
                existing = self.state.project.revision.approved_by
            var = ctk.StringVar(value=existing or default)
            setattr(self, attr, var)
            ctk.CTkComboBox(self.form, values=list(STAFF_NAMES), variable=var, width=400).grid(
                row=row, column=1, padx=20, pady=8, sticky="w"
            )
            row += 1

        ctk.CTkLabel(self.form, text="Plot Mode", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
        plot_label = next(
            (k for k, v in PLOT_MODE_LABELS.items() if v == self.state.project.plot_mode),
            "Single Plot",
        )
        self.plot_mode_var = ctk.StringVar(value=plot_label)
        ctk.CTkComboBox(
            self.form, values=list(PLOT_MODE_LABELS.keys()), variable=self.plot_mode_var, width=400
        ).grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Project Number (Auto)", font=("Arial", 14)).grid(
            row=row, column=0, padx=20, pady=8, sticky="w"
        )
        if not self.state.project.project_no:
            self.state.project.project_no = next_project_number()
        self.project_no_label = ctk.CTkLabel(
            self.form, text=self.state.project.project_no, font=("Arial", 14, "bold")
        )
        self.project_no_label.grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Date (Today)", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
        self.date_label = ctk.CTkLabel(self.form, text=datetime.now().strftime("%d-%m-%Y"), font=("Arial", 14))
        self.date_label.grid(row=row, column=1, padx=20, pady=8, sticky="w")
        row += 1

        for key, label in [("city", "City"), ("state", "State"), ("rainfall_zone", "Rainfall Zone"), ("climate", "Climate")]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 13)).grid(row=row, column=0, padx=20, pady=4, sticky="w")
            ent = ctk.CTkEntry(self.form, width=400)
            ent.insert(0, getattr(self.state.project, key, "") or "")
            ent.grid(row=row, column=1, padx=20, pady=4, sticky="w")
            self.entries[key] = ent
            row += 1

        btn_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(
            btn_frame, text="Next ->", command=self._save_and_next,
            fg_color=BRAND_ORANGE, hover_color="#D06018", width=220,
        ).pack()

        if is_project_type_set(self.state.project.project_type):
            self._show_details()
        else:
            self._hide_details()

    def _update_workflow_hint(self) -> None:
        if not is_project_type_set(self.state.project.project_type):
            self.workflow_hint.configure(text="Choose a project type to unlock project details and workflow tabs.")
            return
        tabs = visible_nav_labels(self.state.project.project_type)
        tab_text = " → ".join(tabs[:8])
        if len(tabs) > 8:
            tab_text += " → …"
        self.workflow_hint.configure(text=f"Active workflow: {tab_text}")

    def _show_details(self) -> None:
        self._details_visible = True
        self.details_frame.pack(fill="both", expand=True, padx=0, pady=8)
        self.header_title.configure(text="STEP 1 — PROJECT DETAILS")
        self.header_label.configure(text="")
        self._update_workflow_hint()
        self._sync_building_height()

    def _hide_details(self) -> None:
        self._details_visible = False
        self.details_frame.pack_forget()
        self.header_title.configure(text="SELECT PROJECT TYPE")
        self.header_label.configure(text="Start by choosing your project type")
        self._update_workflow_hint()

    def _sync_building_height(self) -> None:
        if not self._details_visible:
            return
        config = self.building_config_var.get().strip()
        _, height = parse_building_config(config)
        if height > 0 and not self.height_entry.get().strip():
            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(int(height)))
        self.state.project.building_config = config
        try:
            self.state.project.building_height_m = float(self.height_entry.get() or height or 0)
        except ValueError:
            pass
        self.state.auto_calculate()

    def _on_project_type_selected(self, _choice: str) -> None:
        label = self.project_type_var.get()
        if label == PROJECT_TYPE_PLACEHOLDER:
            self.state.project.project_type = ""
            self._hide_details()
            if self.on_type_change:
                self.on_type_change()
            return
        new_type = project_type_key(label)
        old_type = self.state.project.project_type
        if new_type != old_type:
            self.state.apply_project_type(new_type)
        self._show_details()
        if self.on_type_change:
            self.on_type_change()

    def _on_client_type(self, _event=None) -> None:
        if not self._details_visible:
            return
        text = self.entries["client_name"].get().strip()
        matches = search_clients(text)
        if not matches:
            return
        best = matches[0]
        if text.lower() not in best["client_name"].lower() and text.lower() not in best["client_key"]:
            return
        for key, field in [
            ("client_name", "client_name"),
            ("client_address", "address"),
            ("client_contact", "contact"),
            ("client_email", "email"),
            ("client_gst", "gst"),
        ]:
            if field in best and best[field] and key in self.entries:
                self.entries[key].delete(0, "end")
                self.entries[key].insert(0, best[field])
        if best.get("engineer_name"):
            self.engineer_var.set(best["engineer_name"])

    def _on_location_type(self, _event=None) -> None:
        if not self._details_visible:
            return
        text = self.entries["project_location"].get().strip()
        matches = search_locations(text)
        if not matches:
            return
        best = matches[0]
        for key, src in [("city", "city"), ("state", "state"), ("rainfall_zone", "rainfall_zone"), ("climate", "climate")]:
            if src in best and best[src] and key in self.entries:
                self.entries[key].delete(0, "end")
                self.entries[key].insert(0, best[src])

    def _save_and_next(self) -> None:
        if not is_project_type_set(self.state.project.project_type):
            messagebox.showwarning("Project Type", "Please select a project type before continuing.")
            return
        try:
            today = datetime.now().strftime("%d-%m-%Y")
            self.state.project.project_name = validate_required(self.entries["project_name"].get(), "Project Name")
            self.state.project.client_name = validate_required(self.entries["client_name"].get(), "Client Name")
            self.state.project.project_location = validate_required(
                self.entries["project_location"].get(), "Location"
            )
            self.state.project.engineer_name = validate_required(self.engineer_var.get(), "Engineer Name")
            if not self.state.project.project_no:
                self.state.project.project_no = next_project_number()
            self.state.project.date = today
            self.state.project.plot_mode = PLOT_MODE_LABELS.get(
                self.plot_mode_var.get(), self.state.project.plot_mode
            )
            self.state.project.project_type = project_type_key(self.project_type_var.get())
            self.state.project.building_config = self.building_config_var.get().strip()
            self.state.project.building_height_m = float(self.height_entry.get() or 0)
            self.state.project.num_wings = validate_positive_int(self.wings_entry.get(), "Number of Wings")
            self.state.project.building_type = self.building_type_var.get()
            for key in ("client_address", "client_contact", "client_email", "client_gst", "city", "state", "rainfall_zone", "climate"):
                setattr(self.state.project, key, self.entries[key].get().strip())
            self.state.project.revision = RevisionInfo(
                date=today,
                revision_no="R0",
                description="ISSUED FOR REFERENCE",
                prepared_by=self.prepared_var.get().strip(),
                checked_by=self.checked_var.get().strip(),
                approved_by=self.approved_var.get().strip(),
            )
            upsert_client({
                "client_name": self.state.project.client_name,
                "address": self.state.project.client_address,
                "engineer_name": self.state.project.engineer_name,
                "contact": self.state.project.client_contact,
                "email": self.state.project.client_email,
                "gst": self.state.project.client_gst,
            })
            upsert_location({
                "city": self.state.project.city or self.state.project.project_location,
                "state": self.state.project.state,
                "rainfall_zone": self.state.project.rainfall_zone,
                "climate": self.state.project.climate,
                "full_label": self.state.project.project_location,
            })
            self.state.sync_building_defaults()
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        if hasattr(self, "date_label"):
            self.date_label.configure(text=datetime.now().strftime("%d-%m-%Y"))
        if hasattr(self, "project_no_label") and self.state.project.project_no:
            self.project_no_label.configure(text=self.state.project.project_no)
        if is_project_type_set(self.state.project.project_type):
            self.project_type_var.set(project_type_label(self.state.project.project_type))
            if not self._details_visible:
                self._show_details()
        self._update_workflow_hint()
