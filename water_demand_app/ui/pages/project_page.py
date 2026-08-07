from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox
from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    PLOT_MODE_LABELS,
    PROJECT_TYPE_LABELS,
    STAFF_NAMES,
)
from models.project import ProjectData, RevisionInfo
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_required


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
            header, text="WATER DEMAND REPORT GENERATOR", font=("Arial", 22, "bold"), text_color="white"
        ).pack(pady=12)
        ctk.CTkLabel(
            header, text="American Edge Engineers Pvt. Ltd.", font=("Arial", 12), text_color=BRAND_ORANGE
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

        row = len(fields)
        for label, attr, default in [
            ("Engineer Name", "engineer_var", "Akash"),
            ("Prepared By", "prepared_var", "Akash"),
            ("Checked By", "checked_var", "Akash"),
            ("Approved By", "approved_var", "Omkar"),
        ]:
            ctk.CTkLabel(form, text=label, font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
            existing = getattr(self.state.project.revision, label.split()[-1].lower().replace("by", "_by"), None)
            if label == "Engineer Name":
                existing = self.state.project.engineer_name
            elif label == "Prepared By":
                existing = self.state.project.revision.prepared_by
            elif label == "Checked By":
                existing = self.state.project.revision.checked_by
            elif label == "Approved By":
                existing = self.state.project.revision.approved_by
            var = ctk.StringVar(value=existing or default)
            setattr(self, attr, var)
            ctk.CTkComboBox(form, values=list(STAFF_NAMES), variable=var, width=400).grid(
                row=row, column=1, padx=20, pady=10
            )
            row += 1

        ctk.CTkLabel(form, text="Plot Mode", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        plot_label = next(
            (k for k, v in PLOT_MODE_LABELS.items() if v == self.state.project.plot_mode),
            "Plot A + B",
        )
        self.plot_mode_var = ctk.StringVar(value=plot_label)
        ctk.CTkComboBox(
            form, values=list(PLOT_MODE_LABELS.keys()), variable=self.plot_mode_var, width=400
        ).grid(row=row, column=1, padx=20, pady=10)
        row += 1

        ctk.CTkLabel(form, text="Project Type", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        type_label = next(
            (k for k, v in PROJECT_TYPE_LABELS.items() if v == self.state.project.project_type),
            "Mixed Use",
        )
        self.project_type_var = ctk.StringVar(value=type_label)
        ctk.CTkComboBox(
            form, values=list(PROJECT_TYPE_LABELS.keys()), variable=self.project_type_var, width=400
        ).grid(row=row, column=1, padx=20, pady=10)
        row += 1

        ctk.CTkLabel(form, text="Date (Today)", font=("Arial", 14)).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        self.date_label = ctk.CTkLabel(form, text=datetime.now().strftime("%d-%m-%Y"), font=("Arial", 14))
        self.date_label.grid(row=row, column=1, padx=20, pady=10, sticky="w")
        row += 1

        ctk.CTkLabel(form, text="Revision Details", font=("Arial", 16, "bold")).grid(
            row=row, column=0, columnspan=2, pady=(20, 5)
        )
        row += 1
        for key, label, default in [
            ("revision_no", "Rev. No.", "R0"),
            ("description", "Description", "ISSUED FOR REFERENCE"),
        ]:
            ctk.CTkLabel(form, text=label, font=("Arial", 13)).grid(row=row, column=0, padx=20, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=400)
            val = getattr(self.state.project.revision, key, default)
            ent.insert(0, val or default)
            ent.grid(row=row, column=1, padx=20, pady=8)
            self.entries[key] = ent
            row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(
            btn_frame, text="Next -> Building Details", command=self._save_and_next,
            fg_color=BRAND_ORANGE, hover_color="#D06018", width=220,
        ).pack()

    def _save_and_next(self) -> None:
        try:
            today = datetime.now().strftime("%d-%m-%Y")
            self.state.project.project_name = validate_required(self.entries["project_name"].get(), "Project Name")
            self.state.project.client_name = validate_required(self.entries["client_name"].get(), "Client Name")
            self.state.project.project_location = validate_required(
                self.entries["project_location"].get(), "Project Location"
            )
            self.state.project.engineer_name = validate_required(self.engineer_var.get(), "Engineer Name")
            self.state.project.project_no = self.entries["project_no"].get().strip()
            self.state.project.date = today
            self.state.project.plot_mode = PLOT_MODE_LABELS.get(
                self.plot_mode_var.get(), self.state.project.plot_mode
            )
            self.state.project.project_type = PROJECT_TYPE_LABELS.get(
                self.project_type_var.get(), self.state.project.project_type
            )
            self.state.project.revision = RevisionInfo(
                date=today,
                revision_no=self.entries["revision_no"].get().strip() or "R0",
                description=self.entries["description"].get().strip() or "ISSUED FOR REFERENCE",
                prepared_by=self.prepared_var.get().strip(),
                checked_by=self.checked_var.get().strip(),
                approved_by=self.approved_var.get().strip(),
            )
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        self.date_label.configure(text=datetime.now().strftime("%d-%m-%Y"))
