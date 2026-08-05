from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.residential import ResidentialWing
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_int, validate_required


class ResidentialPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_next, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_next = on_next
        self.on_back = on_back
        self.rows: list = []
        self.table_frame = ctk.CTkFrame(self)
        self.subtotal_labels: dict = {}
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header, text="Residential Details (Plot A & B)", font=("Arial", 20, "bold"), text_color="white"
        ).pack(pady=12)

        self.table_frame.pack(fill="both", expand=True, padx=15, pady=10)
        headers = ["Plot", "Wing Name", "No. Of Flats", "Pop/Flat", "Population", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=5, pady=5)

        if not self.state.residential:
            self._add_default_rows()
        else:
            for wing in self.state.residential:
                self._add_row(wing)

        sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        sub_frame.pack(fill="x", padx=15, pady=5)
        for plot in ("Plot-A", "Plot-B"):
            lbl = ctk.CTkLabel(sub_frame, text=f"{plot} Population: 0", font=("Arial", 12))
            lbl.pack(side="left", padx=15)
            self.subtotal_labels[plot] = lbl

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Wing", command=lambda: self._add_row(), fg_color="#2980B9").grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="+ Add Bungalow", command=self._add_bungalow, fg_color="#2980B9").grid(row=0, column=1, padx=10)
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=2, padx=10)
        ctk.CTkButton(
            btn_frame, text="Save & Next -> Commercial", command=self._save_and_next,
            fg_color=BRAND_ORANGE, hover_color="#D06018"
        ).grid(row=0, column=3, padx=10)

        self._update_subtotals()

    def _add_default_rows(self) -> None:
        defaults = [
            ResidentialWing(plot="Plot-A", wing="WING - A", flats=146, pop_per_flat=5),
            ResidentialWing(plot="Plot-A", wing="WING - B", flats=146, pop_per_flat=5),
        ]
        for wing in defaults:
            self._add_row(wing)

    def _add_bungalow(self) -> None:
        count = sum(1 for r in self.rows if "BUNGLOW" in r["wing"].get().upper() or "BUNGALOW" in r["wing"].get().upper())
        letter = chr(65 + count)
        self._add_row(ResidentialWing(plot="Plot-A", wing=f"BUNGLOW-{letter}", flats=1, pop_per_flat=5))

    def _add_row(self, wing: ResidentialWing | None = None) -> None:
        r = len(self.rows) + 1
        plot_var = ctk.StringVar(value=wing.plot if wing else "Plot-A")
        plot_cb = ctk.CTkComboBox(self.table_frame, values=["Plot-A", "Plot-B"], variable=plot_var, width=100)
        w_ent = ctk.CTkEntry(self.table_frame, width=160)
        w_ent.insert(0, wing.wing if wing else "")
        f_ent = ctk.CTkEntry(self.table_frame, width=90)
        f_ent.insert(0, str(wing.flats if wing else ""))
        p_ent = ctk.CTkEntry(self.table_frame, width=80)
        p_ent.insert(0, str(wing.pop_per_flat if wing else 5))
        pop_lbl = ctk.CTkLabel(self.table_frame, text="0", width=80)

        def update(*_):
            try:
                f = int(f_ent.get() or 0)
                p = int(p_ent.get() or 0)
                pop_lbl.configure(text=str(f * p))
            except ValueError:
                pop_lbl.configure(text="0")
            self._update_subtotals()

        f_ent.bind("<KeyRelease>", update)
        p_ent.bind("<KeyRelease>", update)
        plot_var.trace_add("write", update)

        plot_cb.grid(row=r, column=0, padx=5, pady=5)
        w_ent.grid(row=r, column=1, padx=5, pady=5)
        f_ent.grid(row=r, column=2, padx=5, pady=5)
        p_ent.grid(row=r, column=3, padx=5, pady=5)
        pop_lbl.grid(row=r, column=4, padx=5, pady=5)

        def remove_row():
            for widget in (plot_cb, w_ent, f_ent, p_ent, pop_lbl, rm_btn):
                widget.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()
            self._update_subtotals()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=30, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=5, padx=5, pady=5)

        self.rows.append({
            "row_idx": r, "plot": plot_var, "wing": w_ent, "flats": f_ent,
            "pop": p_ent, "pop_lbl": pop_lbl, "widgets": [plot_cb, w_ent, f_ent, p_ent, pop_lbl, rm_btn],
        })
        update()

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=5, pady=5)

    def _update_subtotals(self) -> None:
        totals = {"Plot-A": 0, "Plot-B": 0}
        for row in self.rows:
            try:
                plot = row["plot"].get()
                pop = int(row["flats"].get() or 0) * int(row["pop"].get() or 0)
                totals[plot] = totals.get(plot, 0) + pop
                row["pop_lbl"].configure(text=str(pop))
            except ValueError:
                pass
        for plot, lbl in self.subtotal_labels.items():
            lbl.configure(text=f"{plot} Population: {totals.get(plot, 0):,}")

    def _save_and_next(self) -> None:
        wings: list = []
        try:
            for idx, row in enumerate(self.rows):
                wing_name = validate_required(row["wing"].get(), "Wing Name")
                flats = validate_positive_int(row["flats"].get(), "No. Of Flats")
                pop_per_flat = validate_positive_int(row["pop"].get(), "Pop/Flat")
                wings.append(ResidentialWing(
                    plot=row["plot"].get(),
                    wing=wing_name,
                    flats=flats,
                    pop_per_flat=pop_per_flat,
                    sort_order=idx,
                ))
            if not wings:
                raise ValidationError("Add at least one residential wing.")
            self.state.residential = wings
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        self._update_subtotals()
