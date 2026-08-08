from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.project_service import find_projects
from ui.project_edit_dialog import ProjectEditDialog


class ProjectHub(ctk.CTkFrame):
    """Dashboard project management: new, open, search, history, edit."""

    def __init__(
        self,
        master,
        user: UserSession,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        enabled: bool = True,
    ) -> None:
        super().__init__(master, fg_color="white", corner_radius=10, border_width=1, border_color="#DDDDDD")
        self.user = user
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.enabled = enabled
        self._selected_id: Optional[str] = None
        self._row_widgets: dict[str, ctk.CTkFrame] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="Project Management",
            font=("Arial", 16, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=0, column=0, sticky="w")

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.grid(row=0, column=1, sticky="e")
        ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search by name, client, location, ID...",
            width=280,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(search_frame, text="Clear", width=60, command=self._clear_search).pack(side="left")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        btn_state = "normal" if self.enabled else "disabled"
        ctk.CTkButton(
            actions, text="+ New Project", fg_color="#27AE60", command=self._new_project,
            state=btn_state, width=120,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions, text="Open Project", fg_color=BRAND_ORANGE, command=self._open_selected,
            state=btn_state, width=120,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions, text="Edit Project", fg_color="#2980B9", command=self._edit_selected,
            state=btn_state, width=110,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions, text="Refresh", fg_color="#7F8C8D", command=self.refresh, width=80,
        ).pack(side="left")

        self.history_frame = ctk.CTkScrollableFrame(self, height=220, label_text="Project History")
        self.history_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))

        cols = ctk.CTkFrame(self.history_frame, fg_color="#E8ECF0", corner_radius=4)
        cols.pack(fill="x", pady=(0, 4))
        for i, (text, width) in enumerate([
            ("Project ID", 130), ("Name", 180), ("Client", 120), ("Location", 120),
            ("No.", 90), ("Updated", 140),
        ]):
            ctk.CTkLabel(cols, text=text, font=("Arial", 10, "bold"), width=width, anchor="w").grid(
                row=0, column=i, padx=4, pady=4, sticky="w"
            )

        self.status_label = ctk.CTkLabel(
            self, text="", font=("Arial", 10), text_color="#888888", anchor="w"
        )
        self.status_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 12))

    def _clear_search(self) -> None:
        self.search_var.set("")

    def _on_search(self) -> None:
        self.refresh(self.search_var.get())

    def refresh(self, query: str = "") -> None:
        for w in list(self.history_frame.winfo_children())[1:]:
            w.destroy()
        self._row_widgets.clear()
        self._selected_id = None

        projects = find_projects(query, user=self.user)
        if not projects:
            ctk.CTkLabel(
                self.history_frame,
                text="No projects found. Click '+ New Project' to create one.",
                font=("Arial", 11),
                text_color="#888888",
            ).pack(pady=20)
            self.status_label.configure(text="0 projects")
            return

        for proj in projects:
            self._add_row(proj)

        self.status_label.configure(text=f"{len(projects)} project(s) — select a row, then Open or Edit")

    def _add_row(self, proj: dict) -> None:
        pid = proj["project_id"]
        row = ctk.CTkFrame(self.history_frame, fg_color="transparent", corner_radius=4)
        row.pack(fill="x", pady=1)
        self._row_widgets[pid] = row

        updated = (proj.get("updated_at") or "")[:16].replace("T", " ")
        values = [
            pid,
            proj.get("project_name", ""),
            proj.get("client_name", ""),
            proj.get("project_location", ""),
            proj.get("project_no", ""),
            updated,
        ]
        widths = [130, 180, 120, 120, 90, 140]
        for i, (val, width) in enumerate(zip(values, widths)):
            lbl = ctk.CTkLabel(row, text=val[:28], font=("Arial", 10), width=width, anchor="w")
            lbl.grid(row=0, column=i, padx=4, pady=3, sticky="w")
            lbl.bind("<Button-1>", lambda e, p=pid: self._select_row(p))
            row.bind("<Button-1>", lambda e, p=pid: self._select_row(p))
        row.bind("<Double-Button-1>", lambda e, p=pid: self._open_project_id(p))

    def _select_row(self, project_id: str) -> None:
        self._selected_id = project_id
        for pid, row in self._row_widgets.items():
            row.configure(fg_color="#D6EAF8" if pid == project_id else "transparent")

    def _open_project_id(self, project_id: str) -> None:
        if not self.enabled:
            messagebox.showwarning("Access Denied", "Your role cannot open projects.")
            return
        self.on_open_project(project_id)

    def _new_project(self) -> None:
        if not self.enabled:
            return
        self.on_new_project()

    def _open_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo("Select Project", "Select a project from the history list first.")
            return
        self._open_project_id(self._selected_id)

    def _edit_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo("Select Project", "Select a project to edit.")
            return
        ProjectEditDialog(self.winfo_toplevel(), self._selected_id, self.user, on_saved=self.refresh)
