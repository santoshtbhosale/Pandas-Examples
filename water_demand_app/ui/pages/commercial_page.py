from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    COMMERCIAL_OCCUPANCY_TYPES,
    COMMERCIAL_TYPES,
    PLOT_MODE_SINGLE,
    commercial_demand,
    commercial_population,
    plot_dropdown_choices,
    ui_plot_label,
)
from models.commercial import CommercialUnit
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_float, validate_required


class CommercialPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_back = on_back
        self.rows: list = []
        self.table_frame = ctk.CTkFrame(self)
        self._build()

    def _plot_values(self) -> list[str]:
        return plot_dropdown_choices(self.state.project.plot_mode)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if self.state.project.plot_mode == PLOT_MODE_SINGLE else "Plot A + B"
        ctk.CTkLabel(
            header,
            text=f"Commercial Details ({plot_text})",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="Select Occupancy Type and Area — Population & demand auto-calculate per NBC",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        self.table_frame.pack(fill="both", expand=True, padx=15, pady=10)
        headers = [
            "Plot", "Block", "Occupancy Type", "Floor", "Area (sq.m)",
            "Pop", "Dom", "Flush", "Total", "",
        ]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 11, "bold")).grid(row=0, column=i, padx=3, pady=5)
        for col in range(len(headers)):
            self.table_frame.grid_columnconfigure(col, weight=1 if col in (2, 3) else 0)

        if not self.state.commercial:
            self._add_default_row()
        else:
            for unit in self.state.commercial:
                self._add_row(unit)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Commercial", command=lambda: self._add_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Save & Next ->",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
        ).grid(row=0, column=2, padx=10)

    def _add_default_row(self) -> None:
        self._add_row(CommercialUnit(
            plot=self._plot_values()[0],
            block="COMM-A",
            comm_type="Retail Shop",
            floor_label="Ground Floor",
            area_sqm=437,
        ))

    def _add_row(self, unit: CommercialUnit | None = None) -> None:
        r = len(self.rows) + 1
        type_values = list(COMMERCIAL_OCCUPANCY_TYPES)
        default_type = unit.comm_type if unit else "Office"
        if default_type not in type_values:
            for alias, spec in COMMERCIAL_TYPES.items():
                if alias == default_type or spec.label == default_type:
                    default_type = spec.label if spec.label in type_values else type_values[0]
                    break
            else:
                default_type = type_values[0]

        plot_var = ctk.StringVar(
            value=ui_plot_label(unit.plot, self.state.project.plot_mode) if unit else self._plot_values()[0]
        )
        plot_cb = ctk.CTkComboBox(self.table_frame, values=self._plot_values(), variable=plot_var, width=85)
        block_ent = ctk.CTkEntry(self.table_frame, width=75)
        block_ent.insert(0, unit.block if unit else "COMM-A")
        type_var = ctk.StringVar(value=default_type)
        type_cb = ctk.CTkComboBox(self.table_frame, values=type_values, variable=type_var, width=130)
        floor_ent = ctk.CTkEntry(self.table_frame, width=100)
        floor_ent.insert(0, unit.floor_label if unit else "")
        area_ent = ctk.CTkEntry(self.table_frame, width=80)
        area_ent.insert(0, str(unit.area_sqm if unit else ""))
        pop_lbl = ctk.CTkLabel(self.table_frame, text="0", width=55)
        dom_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)
        flu_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)
        tot_lbl = ctk.CTkLabel(self.table_frame, text="0", width=60)

        def update(*_):
            try:
                area = float(area_ent.get() or 0)
                spec = COMMERCIAL_TYPES.get(type_var.get(), COMMERCIAL_TYPES["Office"])
                pop = commercial_population(area, spec)
                dom, flu, tot = commercial_demand(pop, spec)
                pop_lbl.configure(text=str(pop))
                dom_lbl.configure(text=str(dom))
                flu_lbl.configure(text=str(flu))
                tot_lbl.configure(text=str(tot))
            except ValueError:
                pop_lbl.configure(text="0")
                dom_lbl.configure(text="0")
                flu_lbl.configure(text="0")
                tot_lbl.configure(text="0")
            self._sync_and_calculate()

        area_ent.bind("<KeyRelease>", update)
        type_var.trace_add("write", update)
        update()

        plot_cb.grid(row=r, column=0, padx=3, pady=5)
        block_ent.grid(row=r, column=1, padx=3, pady=5)
        type_cb.grid(row=r, column=2, padx=3, pady=5)
        floor_ent.grid(row=r, column=3, padx=3, pady=5)
        area_ent.grid(row=r, column=4, padx=3, pady=5)
        pop_lbl.grid(row=r, column=5, padx=3, pady=5)
        dom_lbl.grid(row=r, column=6, padx=3, pady=5)
        flu_lbl.grid(row=r, column=7, padx=3, pady=5)
        tot_lbl.grid(row=r, column=8, padx=3, pady=5)

        def remove_row():
            for w in row_data["widgets"]:
                w.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()
            self._sync_and_calculate()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=28, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=9, padx=3, pady=5)

        row_data = {
            "row_idx": r,
            "plot": plot_var,
            "block": block_ent,
            "type": type_var,
            "floor": floor_ent,
            "area": area_ent,
            "widgets": [
                plot_cb, block_ent, type_cb, floor_ent, area_ent,
                pop_lbl, dom_lbl, flu_lbl, tot_lbl, rm_btn,
            ],
        }
        self.rows.append(row_data)

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=3, pady=5)

    def _sync_and_calculate(self) -> None:
        from services.automation import commercial_from_ui_rows
        self.state.commercial = commercial_from_ui_rows(self.rows, self.state.project.plot_mode)
        self.schedule_auto_calculate(self.state)

    def _save_and_next(self) -> None:
        units: list = []
        try:
            for idx, row in enumerate(self.rows):
                area = validate_positive_float(row["area"].get(), "Area (sq.m)", allow_zero=False)
                if area > 0:
                    units.append(CommercialUnit(
                        plot=row["plot"].get(),
                        block=validate_required(row["block"].get(), "Block"),
                        comm_type=row["type"].get(),
                        floor_label=row["floor"].get().strip(),
                        area_sqm=area,
                        sort_order=idx,
                    ))
            self.state.commercial = units
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        pass
