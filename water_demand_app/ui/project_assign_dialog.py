"""Dialog for Team Leader to create and assign a project."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_ORANGE, project_type_key
from models.project_workflow import DURATION_PRESETS_MINUTES
from models.user import UserRecord


class ProjectAssignDialog(ctk.CTkToplevel):
    def __init__(self, master, engineers: List[UserRecord], project_types: List[str]) -> None:
        super().__init__(master)
        self.title("Assign Project")
        self.geometry("480x420")
        self.resizable(False, False)
        self.result: Optional[Dict[str, Any]] = None
        self._engineers = engineers
        self._build(project_types)
        self.transient(master)
        self.grab_set()

    def _build(self, project_types: List[str]) -> None:
        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=20)
        self._entries: dict = {}
        row = 0
        for key, label in [
            ("project_name", "Project Name"),
            ("client_name", "Client Name"),
        ]:
            ctk.CTkLabel(form, text=label).grid(row=row, column=0, sticky="w", pady=6)
            ent = ctk.CTkEntry(form, width=280)
            ent.grid(row=row, column=1, pady=6)
            self._entries[key] = ent
            row += 1
        ctk.CTkLabel(form, text="Project Type").grid(row=row, column=0, sticky="w", pady=6)
        self.type_var = ctk.StringVar(value=project_types[0] if project_types else "Residential")
        ctk.CTkComboBox(form, values=project_types, variable=self.type_var, width=280).grid(row=row, column=1, pady=6)
        row += 1
        ctk.CTkLabel(form, text="Engineer").grid(row=row, column=0, sticky="w", pady=6)
        eng_names = [f"{e.full_name} ({e.username})" for e in self._engineers]
        self.eng_var = ctk.StringVar(value=eng_names[0] if eng_names else "")
        ctk.CTkComboBox(form, values=eng_names, variable=self.eng_var, width=280).grid(row=row, column=1, pady=6)
        row += 1
        ctk.CTkLabel(form, text="Expected Time").grid(row=row, column=0, sticky="w", pady=6)
        self.dur_var = ctk.StringVar(value="2 Hours")
        ctk.CTkComboBox(form, values=list(DURATION_PRESETS_MINUTES.keys()) + ["Custom"], variable=self.dur_var, width=280).grid(row=row, column=1, pady=6)
        row += 1
        ctk.CTkLabel(form, text="Priority").grid(row=row, column=0, sticky="w", pady=6)
        self.pri_var = ctk.StringVar(value="Normal")
        ctk.CTkComboBox(form, values=["Low", "Normal", "High", "Urgent"], variable=self.pri_var, width=280).grid(row=row, column=1, pady=6)
        row += 1
        ctk.CTkButton(form, text="Assign", fg_color=BRAND_ORANGE, command=self._ok).grid(row=row, column=1, sticky="e", pady=16)
        ctk.CTkButton(form, text="Cancel", command=self.destroy).grid(row=row, column=0, sticky="w", pady=16)

    def _ok(self) -> None:
        eng_sel = self.eng_var.get()
        username = eng_sel.split("(")[-1].rstrip(")") if "(" in eng_sel else eng_sel
        duration = self.dur_var.get()
        custom_minutes = 0
        if duration == "Custom":
            from tkinter import simpledialog
            custom_minutes = int(simpledialog.askstring("Custom Duration", "Minutes:", parent=self) or "120")
            duration = "Custom"
        self.result = {
            "project_name": self._entries["project_name"].get().strip() or "NEW PROJECT",
            "client_name": self._entries["client_name"].get().strip(),
            "project_type": project_type_key(self.type_var.get()),
            "engineer_username": username,
            "duration": duration if duration != "Custom" else "2 Hours",
            "custom_minutes": custom_minutes,
            "priority": self.pri_var.get(),
        }
        if duration == "Custom":
            self.result["duration"] = "Custom"
        self.destroy()
