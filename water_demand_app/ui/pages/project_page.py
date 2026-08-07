from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    PLOT_MODE_LABELS,
    PROJECT_TYPE_LABELS,
    STAFF_APPROVAL,
    STAFF_ENGINEERS,
)
from models.project import ProjectData, RevisionInfo
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_date, validate_required


class ProjectPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.entries: dict = {}
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header,
            text="WATER DEMAND REPORT GENERATOR",
            font=("Arial", 22, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="American Edge Engineers Pvt. Ltd.",
            font=("Arial", 12),
            text_color=BRAND_ORANGE,
        ).pack(pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        fields = [
            ("project_name", "Project Name", "PROPOSED RESIDENTIAL & COMM. AT PUNAVALE"),
            ("client_name", "Client Name", "MR.PRATHMESH GAIKWAD"),
            ("project_location", "Project Location", "PUNAVALE, PUNE"),
            ("project_no", "Project No.", "078"),
        ]
        for i, (key, label, default) in enumerate(fields):
            ctk.CTkLabel(form, text=label, font=("Arial", 14)).grid(row=i, column=0, padx=20, pady=10, sticky="w")
            ent = ctk.CTkEntry(form, width=400)
            val = getattr(self.state.project, key, default)
            ent.insert(0, val or default)
            ent.grid(row=i, column=1, padx=20, pady=10)
            self.entries[key] = ent

        ctk.CTkLabel(form, text="Engineer Name", font=("Arial", 14)).grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.engineer_var = ctk.StringVar(value=self.state.project.engineer_name or STAFF_ENGINEERS[0])
        ctk.CTkComboBox(
            form, values=list(STAFF_ENGINEERS), variable=self.engineer_var, width=400
        ).grid(row=4, column=1, padx=20, pady=10)

        ctk.CTkLabel(form, text="Plot Mode", font=("Arial", 14)).grid(row=5, column=0, padx=20, pady=10, sticky="w")
        plot_label = next(
            (k for k, v in PLOT_MODE_LABELS.items() if v == self.state.project.plot_mode),
            list(PLOT_MODE_LABELS.keys())[0],
        )
        self.plot_mode_var = ctk.StringVar(value=plot_label)
        ctk.CTkComboBox(
            form, values=list(PLOT_MODE_LABELS.keys()), variable=self.plot_mode_var, width=400
        ).grid(row=5, column=1, padx=20, pady=10)

        ctk.CTkLabel(form, text="Project Type", font=("Arial", 14)).grid(row=6, column=0, padx=20, pady=10, sticky="w")
        type_label = next(
            (k for k, v in PROJECT_TYPE_LABELS.items() if v == self.state.project.project_type),
            list(PROJECT_TYPE_LABELS.keys())[1],
        )
        self.project_type_var = ctk.StringVar(value=type_label)
        ctk.CTkComboBox(
            form, values=list(PROJECT_TYPE_LABELS.keys()), variable=self.project_type_var, width=400
        ).grid(row=6, column=1, padx=20, pady=10)

        ctk.CTkLabel(form, text="Date", font=("Arial", 14)).grid(row=7, column=0, padx=20, pady=10, sticky="w")
        self.date_entry = DateEntry(form, width=18, date_pattern="dd-mm-yyyy")
        self.date_entry.grid(row=7, column=1, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(form, text="Revision Details", font=("Arial", 16, "bold")).grid(
            row=8, column=0, columnspan=2, pady=(20, 5)
        )
        rev_fields = [
            ("revision_no", "Rev. No.", "R0", "entry"),
            ("description", "Description", "ISSUED FOR REFERENCE", "entry"),
            ("prepared_by", "Prepared By", "AKASH", "combo"),
            ("checked_by", "Checked By", "AKASH", "combo"),
            ("approved_by", "Approved By", "SWAPNIL", "combo"),
        ]
        for i, (key, label, default, kind) in enumerate(rev_fields, start=9):
            ctk.CTkLabel(form, text=label, font=("Arial", 13)).grid(row=i, column=0, padx=20, pady=8, sticky="w")
            val = getattr(self.state.project.revision, key, default)
            if kind == "combo":
                var = ctk.StringVar(value=val or default)
                ctk.CTkComboBox(form, values=list(STAFF_APPROVAL), variable=var, width=400).grid(
                    row=i, column=1, padx=20, pady=8
                )
                self.entries[key] = var
            else:
                ent = ctk.CTkEntry(form, width=400)
                ent.insert(0, val or default)
                ent.grid(row=i, column=1, padx=20, pady=8)
                self.entries[key] = ent

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(
            btn_frame,
            text="Next -> Residential Details",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).pack()

    def _field_value(self, key: str) -> str:
        widget = self.entries[key]
        return widget.get().strip() if hasattr(widget, "get") else str(widget.get()).strip()

    def _save_and_next(self) -> None:
        try:
            self.state.project.project_name = validate_required(self.entries["project_name"].get(), "Project Name")
            self.state.project.client_name = validate_required(self.entries["client_name"].get(), "Client Name")
            self.state.project.project_location = validate_required(
                self.entries["project_location"].get(), "Project Location"
            )
            self.state.project.engineer_name = validate_required(self.engineer_var.get(), "Engineer Name")
            self.state.project.project_no = self.entries["project_no"].get().strip()
            self.state.project.plot_mode = PLOT_MODE_LABELS.get(
                self.plot_mode_var.get(), self.state.project.plot_mode
            )
            self.state.project.project_type = PROJECT_TYPE_LABELS.get(
                self.project_type_var.get(), self.state.project.project_type
            )
            self.state.project.date = validate_date(self.date_entry.get())
            self.state.project.revision = RevisionInfo(
                date=self.state.project.date,
                revision_no=self._field_value("revision_no") or "R0",
                description=self._field_value("description") or "ISSUED FOR REFERENCE",
                prepared_by=self._field_value("prepared_by"),
                checked_by=self._field_value("checked_by"),
                approved_by=self._field_value("approved_by"),
            )
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        pass
