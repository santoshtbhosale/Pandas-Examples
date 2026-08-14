from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from services.project_service import list_dashboard_projects_cached, mark_project_opened, remove_project
from services.project_workflow import (
    STATUS_FILTER_OPTIONS,
    compute_engineer_performance,
    compute_statistics,
    filter_rows,
    list_engineer_options,
    parse_filter_date,
    rows_for_stats,
)
from ui.gui_safe import safe_command
from ui.scheduled_callbacks import PageLifecycleMixin, cancel_after
from ui.theme import COLOR_BORDER, COLOR_CARD, COLOR_PRIMARY, COLOR_TEXT_SECONDARY, STATUS_BADGES


class ProjectHub(PageLifecycleMixin, ctk.CTkFrame):
    """Compact project table with filters; only the table area scrolls."""

    def __init__(
        self,
        master,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_edit_project: Optional[Callable[[str], None]] = None,
        on_stats_changed: Optional[Callable[[dict], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color=COLOR_BORDER)
        self._init_page_lifecycle()
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_edit_project = on_edit_project or on_open_project
        self.on_stats_changed = on_stats_changed
        self._all_rows: list[dict] = []
        self._filtered_rows: list[dict] = []
        self._row_widgets: dict[str, ctk.CTkFrame] = {}
        self._selected_id: Optional[str] = None
        self._search_job = None
        self._last_stats_rows: list[dict] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        filters = ctk.CTkFrame(self, fg_color="#F8FAFB", corner_radius=8)
        filters.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        filters.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(filters, text="PROJECT FILTERS", font=("Arial", 10, "bold"), text_color=BRAND_NAVY).grid(
            row=0, column=0, columnspan=8, sticky="w", padx=10, pady=(8, 4)
        )

        ctk.CTkLabel(filters, text="Engineer:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, padx=(10, 4), pady=(0, 4), sticky="w"
        )
        self.engineer_var = ctk.StringVar(value="All Engineers")
        self.engineer_combo = ctk.CTkComboBox(
            filters,
            values=["All Engineers"],
            variable=self.engineer_var,
            command=self._on_filter_change,
            width=140,
            height=28,
        )
        self.engineer_combo.grid(row=1, column=1, padx=(0, 10), pady=(0, 4), sticky="w")

        ctk.CTkLabel(filters, text="Status:", font=("Arial", 10, "bold")).grid(
            row=1, column=2, padx=(0, 4), pady=(0, 4), sticky="w"
        )
        self.status_var = ctk.StringVar(value="All Status")
        self.status_combo = ctk.CTkComboBox(
            filters,
            values=STATUS_FILTER_OPTIONS,
            variable=self.status_var,
            command=self._on_filter_change,
            width=120,
            height=28,
        )
        self.status_combo.grid(row=1, column=3, padx=(0, 10), pady=(0, 4), sticky="w")

        ctk.CTkLabel(filters, text="Search:", font=("Arial", 10, "bold")).grid(
            row=1, column=4, padx=(0, 4), pady=(0, 4), sticky="w"
        )
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filters,
            textvariable=self.search_var,
            placeholder_text="Project Name / Client / Project ID",
            height=28,
        )
        self.search_entry.grid(row=1, column=5, sticky="ew", padx=(0, 6), pady=(0, 4))
        self.search_entry.bind("<Return>", lambda _e: self._apply_filters())

        ctk.CTkLabel(filters, text="From:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, padx=(10, 4), pady=(0, 8), sticky="w"
        )
        self.from_date_var = ctk.StringVar()
        self.from_date_entry = ctk.CTkEntry(filters, textvariable=self.from_date_var, placeholder_text="DD-MM-YYYY", width=110, height=28)
        self.from_date_entry.grid(row=2, column=1, padx=(0, 10), pady=(0, 8), sticky="w")

        ctk.CTkLabel(filters, text="To:", font=("Arial", 10, "bold")).grid(
            row=2, column=2, padx=(0, 4), pady=(0, 8), sticky="w"
        )
        self.to_date_var = ctk.StringVar()
        self.to_date_entry = ctk.CTkEntry(filters, textvariable=self.to_date_var, placeholder_text="DD-MM-YYYY", width=110, height=28)
        self.to_date_entry.grid(row=2, column=3, padx=(0, 10), pady=(0, 8), sticky="w")

        btn_row = ctk.CTkFrame(filters, fg_color="transparent")
        btn_row.grid(row=2, column=4, columnspan=2, sticky="w", pady=(0, 8))
        ctk.CTkButton(
            btn_row, text="Search", width=70, height=28, fg_color=BRAND_ORANGE,
            command=safe_command(self._apply_filters, parent=self),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="Clear Filters", width=90, height=28,
            fg_color="#E8ECF0", hover_color=COLOR_BORDER, text_color=COLOR_PRIMARY,
            command=safe_command(self._clear_filters, parent=self),
        ).pack(side="left")

        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 4))
        header_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header_row,
            text="PROJECTS",
            font=("Arial", 11, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=0, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(
            header_row,
            text="",
            font=("Arial", 9),
            text_color="#7A8794",
            anchor="e",
        )
        self.status_label.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            header_row,
            text="Engineer Performance",
            width=140,
            height=24,
            font=("Arial", 9),
            fg_color="#E8ECF0",
            hover_color="#DCE3EA",
            text_color=BRAND_NAVY,
            command=self._show_performance_dialog,
        ).grid(row=0, column=2, padx=(8, 0), sticky="e")

        self.table_wrap = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            label_text="",
        )
        self.table_wrap.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.table_wrap.grid_columnconfigure(0, weight=1)

        self._header_columns = [
            ("Project ID", 88),
            ("Date", 72),
            ("Project Name", 110),
            ("Client", 88),
            ("Engineer", 72),
            ("Type", 72),
            ("Status", 92),
            ("Time Taken", 72),
            ("Updated", 72),
            ("Actions", 48),
        ]
        self._table_header = ctk.CTkFrame(self.table_wrap, fg_color="#E8ECF0", corner_radius=4)
        self._table_header.pack(fill="x", pady=(0, 2))
        for i, (text, width) in enumerate(self._header_columns):
            ctk.CTkLabel(
                self._table_header,
                text=text,
                font=("Arial", 8, "bold"),
                width=width,
                anchor="w",
            ).grid(row=0, column=i, padx=2, pady=3, sticky="w")

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.icursor("end")

    def _clear_filters(self) -> None:
        self.engineer_var.set("All Engineers")
        self.status_var.set("All Status")
        self.search_var.set("")
        self.from_date_var.set("")
        self.to_date_var.set("")
        self._apply_filters()

    def refresh(self) -> None:
        self._all_rows = list_dashboard_projects_cached()
        engineers = list_engineer_options(self._all_rows)
        self.engineer_combo.configure(values=engineers)
        if self.engineer_var.get() not in engineers:
            self.engineer_var.set("All Engineers")
        self._apply_filters()

    def _on_filter_change(self, *_args) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        engineer = self.engineer_var.get()
        status = self.status_var.get()
        search = self.search_var.get()
        from_dt = parse_filter_date(self.from_date_var.get())
        to_dt = parse_filter_date(self.to_date_var.get())
        self._filtered_rows = filter_rows(
            self._all_rows,
            engineer=engineer,
            status_label=status,
            search=search,
            from_date=from_dt,
            to_date=to_dt,
        )
        self._last_stats_rows = rows_for_stats(self._all_rows, engineer=engineer, status_label=status)
        stats = compute_statistics(self._last_stats_rows)
        if self.on_stats_changed:
            self.on_stats_changed(stats)
        self._render_table()
        eng_label = engineer if engineer != "All Engineers" else "All Engineers"
        count_text = f"{eng_label} — {len(self._filtered_rows)} project(s)"
        self.status_label.configure(
            text=f"Showing {len(self._filtered_rows)} of {len(self._all_rows)} projects  |  {count_text}"
        )

    def _render_table(self) -> None:
        for widget in list(self.table_wrap.winfo_children()):
            if widget is not self._table_header:
                widget.destroy()
        self._row_widgets.clear()
        self._selected_id = None

        if not self._filtered_rows:
            query = self.search_var.get().strip()
            if query:
                msg = "No matching projects found."
                btn_text = "Clear Filters"
                cmd = self._clear_filters
            elif not self._all_rows:
                msg = "No projects found.\nCreate your first engineering project to get started."
                btn_text = "+ New Project"
                cmd = self.on_new_project
            else:
                msg = "No projects found for the selected filters."
                btn_text = "Clear Filters"
                cmd = self._clear_filters
            ctk.CTkLabel(
                self.table_wrap,
                text=msg,
                font=("Arial", 10),
                text_color=COLOR_TEXT_SECONDARY,
                justify="center",
            ).pack(pady=(16, 8))
            ctk.CTkButton(
                self.table_wrap,
                text=btn_text,
                width=140,
                height=30,
                fg_color=BRAND_ORANGE,
                command=safe_command(cmd, parent=self),
            ).pack(pady=(0, 16))
            return

        for row in self._filtered_rows:
            self._add_row(row)

    def _format_performance(self, row: dict) -> str:
        title = (row.get("performance_title") or "").strip()
        detail = (row.get("performance_detail") or "").strip()
        if title and detail:
            return f"{title} ({detail})"
        return title or detail or "—"

    def _status_badge(self, label: str) -> str:
        return STATUS_BADGES.get(label, label)

    def _add_row(self, row: dict) -> None:
        pid = row["project_id"]
        frame = ctk.CTkFrame(self.table_wrap, fg_color="transparent", corner_radius=2)
        frame.pack(fill="x", pady=0)
        self._row_widgets[pid] = frame

        values = [
            pid,
            row.get("created_display", row.get("date", "—"))[:10],
            row.get("project_name", ""),
            row.get("client_name", "") or "—",
            row.get("engineer_name", "") or "—",
            row.get("project_type_label", "—"),
            self._status_badge(row.get("status_label", "")),
            row.get("time_taken_display", "—"),
            row.get("updated_display", "—")[:10],
        ]
        widths = [w for _, w in self._header_columns[:-1]]
        for i, (value, width) in enumerate(zip(values, widths)):
            text = (value or "")[:28]
            lbl = ctk.CTkLabel(frame, text=text, font=("Arial", 8), width=width, anchor="w")
            lbl.grid(row=0, column=i, padx=2, pady=2, sticky="w")
            lbl.bind("<Button-1>", lambda _e, p=pid: self._select_row(p))
            frame.bind("<Button-1>", lambda _e, p=pid: self._select_row(p))
        frame.bind("<Double-Button-1>", lambda _e, p=pid: self._open_project(p))

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=0, column=len(values), padx=1, pady=1, sticky="w")
        ctk.CTkButton(
            actions,
            text="⋮",
            width=32,
            height=22,
            font=("Arial", 12, "bold"),
            fg_color="#E8ECF0",
            hover_color=COLOR_BORDER,
            text_color=COLOR_PRIMARY,
            command=safe_command(lambda p=pid, r=row: self._show_actions_menu(p, r), parent=self),
        ).pack(side="left")

    def _show_actions_menu(self, project_id: str, row: dict) -> None:
        menu = ctk.CTkToplevel(self)
        menu.title("Actions")
        menu.geometry("200x220")
        menu.resizable(False, False)
        menu.transient(self.winfo_toplevel())
        menu.grab_set()
        body = ctk.CTkFrame(menu, fg_color="white")
        body.pack(fill="both", expand=True, padx=10, pady=10)
        for label, cmd in [
            ("Open Project", lambda: self._menu_action(menu, lambda: self._open_project(project_id))),
            ("Edit Project", lambda: self._menu_action(menu, lambda: self._edit_project(project_id))),
            ("Delete Project", lambda: self._menu_action(menu, lambda: self._delete_project(project_id, row))),
        ]:
            ctk.CTkButton(
                body,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="#E8ECF0",
                text_color=COLOR_PRIMARY,
                command=cmd,
            ).pack(fill="x", pady=2)

    def _menu_action(self, menu, action) -> None:
        menu.grab_release()
        menu.destroy()
        action()

    def _select_row(self, project_id: str) -> None:
        self._selected_id = project_id
        for pid, row in self._row_widgets.items():
            row.configure(fg_color="#D6EAF8" if pid == project_id else "transparent")

    def _open_project(self, project_id: str) -> None:
        mark_project_opened(project_id)
        self.on_open_project(project_id)

    def _edit_project(self, project_id: str) -> None:
        mark_project_opened(project_id)
        self.on_edit_project(project_id)

    def _delete_project(self, project_id: str, row: dict) -> None:
        if not project_id:
            messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete Project")
        dialog.geometry("480x300")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        body = ctk.CTkFrame(dialog, fg_color="white")
        body.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(body, text="Are you sure you want to delete this project?", font=("Arial", 18, "bold"), text_color=BRAND_NAVY).pack(
            anchor="w", pady=(0, 8)
        )
        ctk.CTkLabel(
            body,
            text=(
                f"Project ID: {project_id}\n"
                f"Project: {row.get('project_name', '')}\n"
                f"Client: {row.get('client_name', '') or '—'}\n"
                f"Engineer: {row.get('engineer_name', '') or '—'}"
            ),
            font=("Arial", 11),
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(
            body,
            text="This action cannot be undone.",
            font=("Arial", 10, "bold"),
            text_color="#C0392B",
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")

        def _cancel() -> None:
            dialog.grab_release()
            dialog.destroy()

        def _confirm() -> None:
            try:
                if remove_project(project_id):
                    dialog.grab_release()
                    dialog.destroy()
                    self.refresh()
                    messagebox.showinfo("Delete Project", "Project deleted successfully.")
                else:
                    messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")
            except Exception:
                messagebox.showerror("Delete Project", "Unable to delete the project. Please try again.")

        ctk.CTkButton(buttons, text="Cancel", width=120, fg_color="#95A5A6", command=_cancel).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(buttons, text="Delete", width=100, fg_color="#C0392B", command=_confirm).pack(
            side="right"
        )

    def _show_performance_dialog(self) -> None:
        summary = compute_engineer_performance(self._last_stats_rows)
        dialog = ctk.CTkToplevel(self)
        dialog.title("Engineer Performance")
        dialog.geometry("620x360")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        body = ctk.CTkScrollableFrame(dialog, fg_color="white")
        body.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            body,
            text="ENGINEER PERFORMANCE",
            font=("Arial", 14, "bold"),
            text_color=BRAND_NAVY,
        ).pack(anchor="w", pady=(0, 8))

        if not summary:
            ctk.CTkLabel(
                body,
                text="No engineer performance data available yet.",
                font=("Arial", 10),
                text_color="#8A949E",
            ).pack(anchor="w", pady=8)
            return

        header = ctk.CTkFrame(body, fg_color="#E8ECF0", corner_radius=4)
        header.pack(fill="x", pady=(0, 4))
        perf_cols = [
            ("Engineer", 140),
            ("Projects", 70),
            ("Completed", 80),
            ("In Progress", 80),
            ("Delayed", 70),
            ("Avg. Time", 80),
        ]
        for i, (text, width) in enumerate(perf_cols):
            ctk.CTkLabel(header, text=text, font=("Arial", 9, "bold"), width=width, anchor="w").grid(
                row=0, column=i, padx=4, pady=4, sticky="w"
            )

        for item in summary:
            row_frame = ctk.CTkFrame(body, fg_color="transparent")
            row_frame.pack(fill="x", pady=1)
            values = [
                item["engineer"],
                str(item["projects"]),
                str(item["completed"]),
                str(item["in_progress"]),
                str(item["delayed"]),
                item["avg_time_display"],
            ]
            for i, (value, (text, width)) in enumerate(zip(values, perf_cols)):
                ctk.CTkLabel(row_frame, text=value, font=("Arial", 9), width=width, anchor="w").grid(
                    row=0, column=i, padx=4, pady=2, sticky="w"
                )
