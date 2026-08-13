from __future__ import annotations

import traceback

import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    BUILDING_CONFIG_EXAMPLES,
    BUILDING_TYPES,
    PROJECT_TYPE_TOWNSHIP,
    PROJECT_TYPE_MIXED,
    PROJECT_TYPE_RESIDENTIAL,
    STAFF_NAMES,
    is_project_type_set,
    parse_building_config,
    project_type_label,
)
from config.page_visibility import visible_nav_labels
from models.project import RevisionInfo
from services.lookup_db import next_project_number, search_clients, upsert_client
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_int, validate_required


def build_professional_page_header(parent, title: str, subtitle: str = "", step: str = ""):
    """Create a consistent, non-technical-friendly page header."""
    wrapper = ctk.CTkFrame(parent, fg_color="white", corner_radius=12, border_width=1, border_color="#DCE3EA")
    wrapper.pack(fill="x", padx=18, pady=(14, 10))
    wrapper.grid_columnconfigure(0, weight=1)
    left = ctk.CTkFrame(wrapper, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=20, pady=15)
    ctk.CTkLabel(left, text=title, font=("Arial", 21, "bold"), text_color=BRAND_NAVY, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(left, text=subtitle, font=("Arial", 10), text_color="#687684", anchor="w").pack(anchor="w", pady=(4, 0))
    if step:
        ctk.CTkLabel(
            wrapper,
            text=step,
            font=("Arial", 10, "bold"),
            text_color=BRAND_NAVY,
            fg_color="#EAF2F8",
            corner_radius=12,
            padx=14,
            pady=7,
        ).grid(row=0, column=1, padx=18, pady=15, sticky="e")
    return wrapper


def show_project_engineering_configuration(project_type: str) -> bool:
    """Show building-level configuration only for residential-family project types."""
    return project_type in (
        PROJECT_TYPE_RESIDENTIAL,
        PROJECT_TYPE_MIXED,
        PROJECT_TYPE_TOWNSHIP,
    )


class ProjectPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_type_change=None, on_back=None) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_type_change = on_type_change
        self.on_back = on_back
        self.entries: dict = {}
        self._details_visible = False
        self._build()

    def _build(self) -> None:
        build_professional_page_header(
            self,
            "Project Details",
            "Enter the basic project information first. Fields are kept simple and only required information is shown.",
            "STEP 2 • PROJECT DETAILS",
        )

        self.workflow_hint = ctk.CTkLabel(
            self,
            text="Choose a project type to unlock engineering workflow tabs.",
            font=("Arial", 11, "italic"),
            text_color="#666666",
            anchor="w",
        )
        self.workflow_hint.pack(fill="x", padx=16, pady=(0, 6))

        self.details_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form = ctk.CTkFrame(
            self.details_frame,
            fg_color="white",
            corner_radius=12,
            border_width=1,
            border_color="#DCE3EA",
        )
        self.form.pack(fill="x", padx=16, pady=8)
        self.form.grid_columnconfigure(1, weight=0)

        row = 0
        for key, label, default in [
            ("project_name", "Project Name", "PROPOSED RESIDENTIAL & COMM. AT PUNAVALE"),
            ("client_name", "Client Name", "MR.PRATHMESH GAIKWAD"),
        ]:
            ctk.CTkLabel(self.form, text=label, font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=16, pady=8, sticky="w"
            )
            ent = ctk.CTkEntry(self.form, width=480, height=34)
            ent.insert(0, getattr(self.state.project, key, default) or default)
            ent.grid(row=row, column=1, padx=16, pady=8, sticky="w")
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

        ctk.CTkLabel(
            self.form,
            text="Project Type",
            font=("Arial", 13, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        self.project_type_display = ctk.CTkLabel(
            self.form,
            text=project_type_label(self.state.project.project_type),
            font=("Arial", 13, "bold"),
            text_color=BRAND_ORANGE,
            anchor="w",
        )
        self.project_type_display.grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        engineering_start_row = row

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
            width=300,
            height=34,
        ).grid(row=row, column=1, padx=16, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Height (m)", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.height_entry = ctk.CTkEntry(self.form, width=120, height=34)
        self.height_entry.insert(0, str(self.state.project.building_height_m or ""))
        self.height_entry.grid(row=row, column=1, padx=16, pady=6, sticky="w")
        self.height_entry.bind("<KeyRelease>", lambda *_: self.schedule_auto_calculate(self.state))
        row += 1

        ctk.CTkLabel(self.form, text="Number of Wings", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.wings_entry = ctk.CTkEntry(self.form, width=120, height=34)
        self.wings_entry.insert(0, str(self.state.project.num_wings or 1))
        self.wings_entry.grid(row=row, column=1, padx=16, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(self.form, text="Building Type", font=("Arial", 13)).grid(
            row=row, column=0, padx=16, pady=6, sticky="w"
        )
        self.building_type_var = ctk.StringVar(value=self.state.project.building_type or BUILDING_TYPES[0])
        ctk.CTkComboBox(
            self.form,
            values=list(BUILDING_TYPES),
            variable=self.building_type_var,
            width=320,
            height=34,
        ).grid(row=row, column=1, padx=16, pady=6, sticky="w")
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
            ctk.CTkComboBox(
                self.form,
                values=list(STAFF_NAMES),
                variable=var,
                width=300,
                height=34,
            ).grid(row=row, column=1, padx=16, pady=6, sticky="w")
            row += 1

        btn_frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        btn_frame.pack(pady=12)
        if self.on_back is not None:
            ctk.CTkButton(
                btn_frame,
                text="← Back",
                command=self.on_back,
                fg_color="#7F8C8D",
                hover_color="#667071",
                width=140,
            ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="Next →",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).pack(side="left", padx=8)

        self._engineering_start_row = engineering_start_row
        self._engineering_end_row = row - 1
        self._set_engineering_configuration_visibility()

        if is_project_type_set(self.state.project.project_type):
            self._show_details()
        else:
            self._hide_details()

    def _set_engineering_configuration_visibility(self) -> None:
        if not hasattr(self, "_engineering_start_row"):
            return
        show = show_project_engineering_configuration(self.state.project.project_type)
        for widget in self.form.winfo_children():
            try:
                info = widget.grid_info()
                if not info:
                    continue
                row = int(info.get("row", -1))
                if self._engineering_start_row <= row <= self._engineering_end_row:
                    if show:
                        widget.grid()
                    else:
                        widget.grid_remove()
            except Exception:
                pass

    def _update_workflow_hint(self) -> None:
        if not hasattr(self, "workflow_hint"):
            return
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
            self.state.project.project_name = validate_required(
                self.entries["project_name"].get(), "Project Name"
            )
            self.state.project.client_name = validate_required(
                self.entries["client_name"].get(), "Client Name"
            )
            self.state.project.engineer_name = validate_required(
                self.engineer_var.get(), "Engineer Name"
            )
            if not self.state.project.project_no:
                self.state.project.project_no = next_project_number()
            self.state.project.date = today

            if show_project_engineering_configuration(self.state.project.project_type):
                self.state.project.building_config = self.building_config_var.get().strip()
                self.state.project.building_height_m = float(self.height_entry.get() or 0)
                self.state.project.num_wings = validate_positive_int(
                    self.wings_entry.get(), "Number of Wings"
                )
                self.state.project.building_type = self.building_type_var.get()

            self.state.project.revision = RevisionInfo(
                date=today,
                revision_no="R0",
                description="ISSUED FOR REFERENCE",
                prepared_by=self.prepared_var.get().strip(),
                checked_by=self.checked_var.get().strip(),
                approved_by=self.approved_var.get().strip(),
            )

            try:
                upsert_client({
                    "client_name": self.state.project.client_name,
                    "engineer_name": self.state.project.engineer_name,
                })
            except Exception:
                traceback.print_exc()

            self.on_next()

            try:
                self.after(100, self._deferred_post_navigation_sync)
            except Exception:
                pass
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Validation Error", f"Please check the entered values.\n\n{exc}")
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror(
                "Project Details",
                f"Unable to open the next section. Please check the project information and try again.\n\n{exc}",
            )

    def _deferred_post_navigation_sync(self) -> None:
        try:
            self.state.sync_building_defaults()
        except Exception:
            traceback.print_exc()
        try:
            self.schedule_auto_calculate(self.state)
        except Exception:
            pass

    def refresh(self) -> None:
        project = self.state.project

        if hasattr(self, "date_label"):
            self.date_label.configure(text=project.date or datetime.now().strftime("%d-%m-%Y"))
        if hasattr(self, "project_no_label"):
            self.project_no_label.configure(text=project.project_no or "—")
        if hasattr(self, "project_type_display"):
            self.project_type_display.configure(
                text=project_type_label(project.project_type)
                if is_project_type_set(project.project_type)
                else "Select Project Type"
            )

        for key in ("project_name", "client_name"):
            entry = self.entries.get(key)
            if entry is not None:
                value = getattr(project, key, "") or ""
                if entry.get() != value:
                    entry.delete(0, "end")
                    entry.insert(0, value)

        if hasattr(self, "building_config_var"):
            self.building_config_var.set(project.building_config or "G+7")
        if hasattr(self, "height_entry"):
            height = project.building_height_m or 0
            current = self.height_entry.get()
            target = str(int(height)) if float(height).is_integer() else str(height)
            if current != target:
                self.height_entry.delete(0, "end")
                self.height_entry.insert(0, target)
        if hasattr(self, "wings_entry"):
            target = str(project.num_wings or 1)
            if self.wings_entry.get() != target:
                self.wings_entry.delete(0, "end")
                self.wings_entry.insert(0, target)
        if hasattr(self, "building_type_var"):
            self.building_type_var.set(project.building_type or BUILDING_TYPES[0])

        if hasattr(self, "engineer_var"):
            self.engineer_var.set(project.engineer_name or "Akash")
        if hasattr(self, "prepared_var"):
            self.prepared_var.set(project.revision.prepared_by or "Akash")
        if hasattr(self, "checked_var"):
            self.checked_var.set(project.revision.checked_by or "Akash")
        if hasattr(self, "approved_var"):
            self.approved_var.set(project.revision.approved_by or "Omkar")

        self._set_engineering_configuration_visibility()
        if is_project_type_set(project.project_type):
            self._show_details()
        else:
            self._hide_details()
        self._update_workflow_hint()
