from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    BUILDING_CONFIG_EXAMPLES,
    BUILDING_TYPES,
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
from services.lookup_db import next_project_number, search_clients, upsert_client
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
        self.header_frame = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        self.header_frame.pack(fill="x", padx=10, pady=(10, 8))
        self.header_title = ctk.CTkLabel(
            self.header_frame, text="PROJECT DETAILS", font=("Arial", 18, "bold"), text_color="white"
        )
        self.header_title.pack(pady=12)
        ctk.CTkLabel(
            self.header_frame,
            text="American Edge Engineers Pvt. Ltd.",
            font=("Arial", 12),
            text_color=BRAND_ORANGE,
        ).pack(pady=(0, 10))

        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form = ctk.CTkFrame(self.details_frame, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        self.form.pack(fill="x", padx=16, pady=8)
        self.form.grid_columnconfigure(1, weight=1)

        row = 0
        for key, label, default in [
            ("project_name", "Project Name", "PROPOSED RESIDENTIAL & COMM. AT PUNAVALE"),
            ("client_name", "Client Name", "MR.PRATHMESH GAIKWAD"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=16, pady=8, sticky="w"
            )
            ent = ctk.CTkEntry(self.form)
            ent.insert(0, getattr(self.state.project, key, default) or default)
            ent.grid(row=row, column=1, padx=16, pady=8, sticky="ew")
            self.entries[key] = ent
            if key == "client_name":
                ent.bind("<KeyRelease>", self._on_client_type)
            row += 1

        if not self.state.project.project_no:
            self.state.project.project_no = next_project_number()

        ctk.CTkLabel(self.form, text="Reference No.", font=("Arial", 13, "bold")).grid(
            row=row, column=0, padx=16, pady=8, sticky="w"
        )
        self.project_no_label = ctk.CTkLabel(
            self.form, text=self.state.project.project_no, font=("Arial", 13)
        )
        self.project_no_label.grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Date", font=("Arial", 13, "bold")).grid(
            row=row, column=0, padx=16, pady=8, sticky="w"
        )
        self.date_label = ctk.CTkLabel(
            self.form, text=datetime.now().strftime("%d-%m-%Y"), font=("Arial", 13)
        )
        self.date_label.grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Project Type", font=("Arial", 13, "bold"), text_color=BRAND_NAVY).grid(
            row=row, column=0, padx=16, pady=8, sticky="nw"
        )
        type_cell = ctk.CTkFrame(self.form, fg_color="transparent")
        type_cell.grid(row=row, column=1, padx=16, pady=8, sticky="ew")
        type_cell.grid_columnconfigure(0, weight=1)
        initial_label = project_type_label(self.state.project.project_type)
        self.project_type_var = ctk.StringVar(value=initial_label)
        type_values = [PROJECT_TYPE_PLACEHOLDER] + sorted(set(PROJECT_TYPE_LABELS.keys()))
        self.type_combo = ctk.CTkComboBox(
            type_cell,
            values=type_values,
            variable=self.project_type_var,
            command=self._on_project_type_selected,
        )
        self.type_combo.grid(row=0, column=0, sticky="ew")
        self.workflow_hint = ctk.CTkLabel(
            type_cell,
            text="",
            font=("Arial", 11, "italic"),
            text_color=BRAND_ORANGE,
            justify="left",
            anchor="w",
            wraplength=640,
        )
        self.workflow_hint.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        row += 1

        ctk.CTkLabel(
            self.form,
            text="Engineering Configuration",
            font=("Arial", 14, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=row, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Configuration", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.building_config_var = ctk.StringVar(value=self.state.project.building_config or "G+7")
        ctk.CTkComboBox(
            self.form,
            values=list(BUILDING_CONFIG_EXAMPLES),
            variable=self.building_config_var,
            command=lambda *_: self._sync_building_height(),
        ).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(self.form, text="Building Height (m)", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.height_entry = ctk.CTkEntry(self.form, width=120)
        self.height_entry.insert(0, str(self.state.project.building_height_m or ""))
        self.height_entry.grid(row=row, column=1, padx=16, pady=6, sticky="w")
        self.height_entry.bind("<KeyRelease>", lambda *_: self.schedule_auto_calculate(self.state))
        row += 1

        ctk.CTkLabel(self.form, text="Number of Wings", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.wings_entry = ctk.CTkEntry(self.form, width=120)
        self.wings_entry.insert(0, str(self.state.project.num_wings or 1))
        self.wings_entry.grid(row=row, column=1, padx=16, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Type", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.building_type_var = ctk.StringVar(value=self.state.project.building_type or BUILDING_TYPES[0])
        ctk.CTkComboBox(
            self.form, values=list(BUILDING_TYPES), variable=self.building_type_var
        ).grid(row=row, column=1, padx=16, pady=6, sticky="ew")
        row += 1

        ctk.CTkLabel(
            self.form,
            text="Report Sign-off",
            font=("Arial", 14, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=row, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")
        row += 1

        for label, attr, default in [
            ("Engineer Name", "engineer_var", "Akash"),
            ("Prepared By", "prepared_var", "Akash"),
            ("Checked By", "checked_var", "Akash"),
            ("Approved By", "approved_var", "Omkar"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 13)).grid(
                row=row, column=0, padx=16, pady=6, sticky="w"
            )
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
            ctk.CTkComboBox(self.form, values=list(STAFF_NAMES), variable=var).grid(
                row=row, column=1, padx=16, pady=6, sticky="ew"
            )
            row += 1

        btn_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(
            btn_frame,
            text="Next ->",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).pack()

        if is_project_type_set(self.state.project.project_type):
            self._show_details()
        else:
            self._hide_details()

    def _update_workflow_hint(self) -> None:
        if not is_project_type_set(self.state.project.project_type):
            self.workflow_hint.configure(text="Choose a project type to unlock engineering workflow tabs.")
            return
        tabs = visible_nav_labels(self.state.project.project_type)
        tab_text = " → ".join(tabs[:8])
        if len(tabs) > 8:
            tab_text += " → …"
        self.workflow_hint.configure(text=f"Active workflow: {tab_text}")

    def _show_details(self) -> None:
        self._details_visible = True
        self.details_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self._update_workflow_hint()
        self._sync_building_height()

    def _hide_details(self) -> None:
        self._details_visible = False
        self.details_frame.pack_forget()
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
        self.schedule_auto_calculate(self.state)

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
        if best.get("client_name"):
            self.entries["client_name"].delete(0, "end")
            self.entries["client_name"].insert(0, best["client_name"])
        if best.get("engineer_name"):
            self.engineer_var.set(best["engineer_name"])

    def _save_and_next(self) -> None:
        if not is_project_type_set(self.state.project.project_type):
            messagebox.showwarning("Project Type", "Please select a project type before continuing.")
            return
        try:
            today = datetime.now().strftime("%d-%m-%Y")
            self.state.project.project_name = validate_required(self.entries["project_name"].get(), "Project Name")
            self.state.project.client_name = validate_required(self.entries["client_name"].get(), "Client Name")
            self.state.project.engineer_name = validate_required(self.engineer_var.get(), "Engineer Name")
            if not self.state.project.project_no:
                self.state.project.project_no = next_project_number()
            self.state.project.date = today
            self.state.project.project_type = project_type_key(self.project_type_var.get())
            self.state.project.building_config = self.building_config_var.get().strip()
            self.state.project.building_height_m = float(self.height_entry.get() or 0)
            self.state.project.num_wings = validate_positive_int(self.wings_entry.get(), "Number of Wings")
            self.state.project.building_type = self.building_type_var.get()
            if not self.state.project.project_location:
                self.state.project.project_location = self.state.project.project_name
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
