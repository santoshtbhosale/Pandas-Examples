from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from services.database import get_project_summary, update_project_metadata
from ui.components.validation import ValidationError, validate_required


class ProjectEditDialog(ctk.CTkToplevel):
    """Edit project header metadata without opening the calculator."""

    def __init__(
        self,
        master,
        project_id: str,
        user=None,
        on_saved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.project_id = project_id
        self.user = user
        self.on_saved = on_saved
        self.title("Edit Project")
        self.geometry("480x360")
        self.transient(master)
        self.grab_set()

        summary = get_project_summary(project_id)
        if not summary:
            messagebox.showerror("Error", "Project not found.")
            self.destroy()
            return

        ctk.CTkLabel(self, text="Edit Project Details", font=("Arial", 16, "bold")).pack(pady=12)
        ctk.CTkLabel(self, text=f"ID: {project_id}", font=("Arial", 10), text_color="#666666").pack()

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=8)

        self.entries = {}
        for key, label, value in [
            ("project_name", "Project Name", summary["project_name"]),
            ("client_name", "Client Name", summary["client_name"]),
            ("project_location", "Location", summary["project_location"]),
            ("engineer_name", "Engineer", summary.get("engineer_name", "")),
        ]:
            ctk.CTkLabel(form, text=label, anchor="w").pack(fill="x", pady=(8, 2))
            ent = ctk.CTkEntry(form, width=400)
            ent.insert(0, value)
            ent.pack(fill="x")
            self.entries[key] = ent

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=16)
        ctk.CTkButton(btn_row, text="Save", fg_color=BRAND_ORANGE, command=self._save).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Cancel", fg_color="gray", command=self.destroy).pack(side="left", padx=8)

    def _save(self) -> None:
        try:
            update_project_metadata(
                self.project_id,
                validate_required(self.entries["project_name"].get(), "Project Name"),
                validate_required(self.entries["client_name"].get(), "Client Name"),
                validate_required(self.entries["project_location"].get(), "Location"),
                self.entries["engineer_name"].get().strip(),
                updated_by=getattr(self.user, "username", "") if self.user else "",
            )
            messagebox.showinfo("Saved", "Project updated successfully.")
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except ValidationError as exc:
            messagebox.showerror("Validation", exc.message)
