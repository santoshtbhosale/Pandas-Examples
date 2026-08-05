from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE, COMMERCIAL_TYPES
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

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header, text="Commercial Details (Plot A & B)", font=("Arial", 20, "bold"), text_color="white"
        ).pack(pady=12)

        self.table_frame.pack(fill="both", expand=True, padx=15, pady=10)
        headers = ["Plot", "Block", "Type", "Floor", "Area (sq.m)", "Pop (Auto)", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=4, pady=5)

        if not self.state.commercial:
            self._add_default_row()
        else:
            for unit in self.state.commercial:
                self._add_row(unit)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Commercial", command=lambda: self._add_row(), fg_color="#2980B9").grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame, text="Save & Next -> Other", command=self._save_and_next,
            fg_color=BRAND_ORANGE, hover_color="#D06018"
        ).grid(row=0, column=2, padx=10)

    def _add_default_row(self) -> None:
        self._add_row(CommercialUnit(
            plot="Plot-A", block="COMM-A", comm_type="Shop - Ground Floor",
            floor_label="Ground Floor (Shop)", area_sqm=437,
        ))

    def _add_row(self, unit: CommercialUnit | None = None) -> None:
        r = len(self.rows) + 1
        type_values = list(COMMERCIAL_TYPES.keys())
        plot_var = ctk.StringVar(value=unit.plot if unit else "Plot-A")
        plot_cb = ctk.CTkComboBox(self.table_frame, values=["Plot-A", "Plot-B"], variable=plot_var, width=90)
        block_ent = ctk.CTkEntry(self.table_frame, width=80)
        block_ent.insert(0, unit.block if unit else "COMM-A")
        type_var = ctk.StringVar(value=unit.comm_type if unit else "Shop - Ground Floor")
        type_cb = ctk.CTkComboBox(self.table_frame, values=type_values, variable=type_var, width=150)
        floor_ent = ctk.CTkEntry(self.table_frame, width=120)
        floor_ent.insert(0, unit.floor_label if unit else "")
        area_ent = ctk.CTkEntry(self.table_frame, width=90)
        area_ent.insert(0, str(unit.area_sqm if unit else ""))
        pop_var = ctk.StringVar(value="0")
        pop_lbl = ctk.CTkLabel(self.table_frame, textvariable=pop_var, width=70)

        def update_pop(*_):
            try:
                from config.nbc_2026 import commercial_population
                area = float(area_ent.get() or 0)
                spec = COMMERCIAL_TYPES.get(type_var.get(), COMMERCIAL_TYPES["Shop - Ground Floor"])
                pop_var.set(str(commercial_population(area, spec)))
            except ValueError:
                pop_var.set("0")

        area_ent.bind("<KeyRelease>", update_pop)
        type_var.trace_add("write", update_pop)
        update_pop()

        plot_cb.grid(row=r, column=0, padx=4, pady=5)
        block_ent.grid(row=r, column=1, padx=4, pady=5)
        type_cb.grid(row=r, column=2, padx=4, pady=5)
        floor_ent.grid(row=r, column=3, padx=4, pady=5)
        area_ent.grid(row=r, column=4, padx=4, pady=5)
        pop_lbl.grid(row=r, column=5, padx=4, pady=5)

        def remove_row():
            for w in row_data["widgets"]:
                w.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=30, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=6, padx=4, pady=5)

        row_data = {
            "row_idx": r, "plot": plot_var, "block": block_ent, "type": type_var,
            "floor": floor_ent, "area": area_ent, "pop_var": pop_var,
            "widgets": [plot_cb, block_ent, type_cb, floor_ent, area_ent, pop_lbl, rm_btn],
        }
        self.rows.append(row_data)

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=4, pady=5)

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
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        pass
