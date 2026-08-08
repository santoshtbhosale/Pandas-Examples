from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    BUILDING_CONFIG_EXAMPLES,
    BUILDING_TYPES,
    PLOT_MODE_SINGLE,
    plot_dropdown_choices,
    residential_demand,
    ui_plot_label,
)
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

    def _plot_values(self) -> list[str]:
        return plot_dropdown_choices(self.state.project.plot_mode)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        plot_text = "Single Plot" if self.state.project.plot_mode == PLOT_MODE_SINGLE else "Plot A + B"
        ctk.CTkLabel(
            header,
            text=f"Residential / Building Details ({plot_text})",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="Enter BHK units only — Population, Domestic, Flushing & Kitchen auto-calculate per NBC",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        headers = [
            "Plot", "Wing", "Config", "Bldg Type", "Ht(m)", "Wings",
            "1BHK", "2BHK", "3BHK", "4BHK", "PH",
            "Pop", "Dom", "Flush", "Total", "Kit", "",
        ]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 9, "bold")).grid(row=0, column=i, padx=1, pady=4)

        if not self.state.residential:
            self._add_default_rows()
        else:
            for wing in self.state.residential:
                self._add_row(wing)

        sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        sub_frame.pack(fill="x", padx=15, pady=5)
        for plot in self._plot_values():
            lbl = ctk.CTkLabel(sub_frame, text=f"{plot} Population: 0", font=("Arial", 12))
            lbl.pack(side="left", padx=15)
            self.subtotal_labels[plot] = lbl

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="+ Add Wing", command=lambda: self._add_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="+ Add Bungalow", command=self._add_bungalow, fg_color="#2980B9").grid(
            row=0, column=1, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=2, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Save & Next ->",
            command=self._save_and_next,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
        ).grid(row=0, column=3, padx=10)

        self._update_subtotals()

    def _add_default_rows(self) -> None:
        default_plot = self._plot_values()[0]
        for wing in [
            ResidentialWing(plot=default_plot, wing="WING - A", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
            ResidentialWing(plot=default_plot, wing="WING - B", building_config="G+7", flats_2bhk=73, flats_3bhk=73),
        ]:
            self._add_row(wing)

    def _add_bungalow(self) -> None:
        count = sum(
            1 for r in self.rows
            if "BUNGLOW" in r["wing"].get().upper() or "BUNGALOW" in r["wing"].get().upper()
        )
        letter = chr(65 + count)
        self._add_row(
            ResidentialWing(
                plot=self._plot_values()[0],
                wing=f"BUNGLOW-{letter}",
                building_config="G+1",
                building_height_m=6.0,
                num_wings=1,
                flats_3bhk=1,
            )
        )

    def _add_row(self, wing: ResidentialWing | None = None) -> None:
        r = len(self.rows) + 1
        config_values = list(BUILDING_CONFIG_EXAMPLES)
        plot_var = ctk.StringVar(
            value=ui_plot_label(wing.plot, self.state.project.plot_mode) if wing else self._plot_values()[0]
        )
        plot_cb = ctk.CTkComboBox(self.table_frame, values=self._plot_values(), variable=plot_var, width=72)
        w_ent = ctk.CTkEntry(self.table_frame, width=78)
        w_ent.insert(0, wing.wing if wing else "")
        cfg_var = ctk.StringVar(value=wing.building_config if wing else "G+7")
        cfg_cb = ctk.CTkComboBox(self.table_frame, values=config_values, variable=cfg_var, width=72)
        btype_var = ctk.StringVar(value=wing.building_type if wing else BUILDING_TYPES[0])
        btype_cb = ctk.CTkComboBox(self.table_frame, values=list(BUILDING_TYPES), variable=btype_var, width=95)
        ht_ent = ctk.CTkEntry(self.table_frame, width=48)
        ht_ent.insert(0, str(wing.building_height_m if wing and wing.building_height_m else ""))
        wings_ent = ctk.CTkEntry(self.table_frame, width=42)
        wings_ent.insert(0, str(wing.num_wings if wing else 1))
        b1_ent = ctk.CTkEntry(self.table_frame, width=40)
        b1_ent.insert(0, str(wing.flats_1bhk if wing else ""))
        b2_ent = ctk.CTkEntry(self.table_frame, width=40)
        b2_ent.insert(0, str(wing.flats_2bhk if wing else ""))
        b3_ent = ctk.CTkEntry(self.table_frame, width=40)
        b3_ent.insert(0, str(wing.flats_3bhk if wing else ""))
        b4_ent = ctk.CTkEntry(self.table_frame, width=40)
        b4_ent.insert(0, str(wing.flats_4bhk if wing else ""))
        ph_ent = ctk.CTkEntry(self.table_frame, width=40)
        ph_ent.insert(0, str(wing.flats_penthouse if wing else ""))
        pop_lbl = ctk.CTkLabel(self.table_frame, text="0", width=42)
        dom_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        flu_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        tot_lbl = ctk.CTkLabel(self.table_frame, text="0", width=48)
        kit_lbl = ctk.CTkLabel(self.table_frame, text="0", width=42)

        def update(*_):
            try:
                b1 = max(0, int(b1_ent.get() or 0))
                b2 = max(0, int(b2_ent.get() or 0))
                b3 = max(0, int(b3_ent.get() or 0))
                b4 = max(0, int(b4_ent.get() or 0))
                ph = max(0, int(ph_ent.get() or 0))
                temp = ResidentialWing(
                    building_config=cfg_var.get(),
                    building_height_m=float(ht_ent.get() or 0),
                    flats_1bhk=b1,
                    flats_2bhk=b2,
                    flats_3bhk=b3,
                    flats_4bhk=b4,
                    flats_penthouse=ph,
                )
                pop = temp.population
                dom, flu, tot = residential_demand(pop)
                kitchen = temp.kitchen_water
                pop_lbl.configure(text=str(pop))
                dom_lbl.configure(text=str(dom))
                flu_lbl.configure(text=str(flu))
                tot_lbl.configure(text=str(tot))
                kit_lbl.configure(text=str(kitchen))
                if not ht_ent.get().strip() and temp.building_height_m > 0:
                    ht_ent.delete(0, "end")
                    ht_ent.insert(0, str(int(temp.building_height_m)))
            except ValueError:
                pop_lbl.configure(text="0")
                dom_lbl.configure(text="0")
                flu_lbl.configure(text="0")
                tot_lbl.configure(text="0")
                kit_lbl.configure(text="0")
            self._update_subtotals()
            self._sync_and_calculate()

        for ent in (ht_ent, wings_ent, b1_ent, b2_ent, b3_ent, b4_ent, ph_ent):
            ent.bind("<KeyRelease>", update)
        for var in (plot_var, cfg_var, btype_var):
            var.trace_add("write", update)

        widgets = [
            plot_cb, w_ent, cfg_cb, btype_cb, ht_ent, wings_ent,
            b1_ent, b2_ent, b3_ent, b4_ent, ph_ent,
            pop_lbl, dom_lbl, flu_lbl, tot_lbl, kit_lbl,
        ]
        for j, widget in enumerate(widgets):
            widget.grid(row=r, column=j, padx=1, pady=4)

        def remove_row():
            for widget in widgets + [rm_btn]:
                widget.destroy()
            self.rows = [row for row in self.rows if row["row_idx"] != r]
            self._regrid()
            self._update_subtotals()
            self._sync_and_calculate()

        rm_btn = ctk.CTkButton(self.table_frame, text="X", width=26, fg_color="#C0392B", command=remove_row)
        rm_btn.grid(row=r, column=16, padx=1, pady=4)

        self.rows.append({
            "row_idx": r,
            "plot": plot_var,
            "wing": w_ent,
            "config": cfg_var,
            "btype": btype_var,
            "height": ht_ent,
            "num_wings": wings_ent,
            "b1": b1_ent,
            "b2": b2_ent,
            "b3": b3_ent,
            "b4": b4_ent,
            "ph": ph_ent,
            "pop_lbl": pop_lbl,
            "widgets": widgets + [rm_btn],
        })
        update()

    def _regrid(self) -> None:
        for i, row in enumerate(self.rows, 1):
            row["row_idx"] = i
            for j, widget in enumerate(row["widgets"]):
                widget.grid(row=i, column=j, padx=1, pady=4)

    def _update_subtotals(self) -> None:
        totals = {plot: 0 for plot in self._plot_values()}
        for row in self.rows:
            try:
                plot = row["plot"].get()
                temp = ResidentialWing(
                    flats_1bhk=int(row["b1"].get() or 0),
                    flats_2bhk=int(row["b2"].get() or 0),
                    flats_3bhk=int(row["b3"].get() or 0),
                    flats_4bhk=int(row["b4"].get() or 0),
                    flats_penthouse=int(row["ph"].get() or 0),
                )
                totals[plot] = totals.get(plot, 0) + temp.population
                row["pop_lbl"].configure(text=str(temp.population))
            except ValueError:
                pass
        for plot, lbl in self.subtotal_labels.items():
            lbl.configure(text=f"{plot} Population: {totals.get(plot, 0):,}")

    def _sync_and_calculate(self) -> None:
        from services.automation import wings_from_ui_rows
        self.state.residential = wings_from_ui_rows(self.rows, self.state.project.plot_mode)
        self.state.auto_calculate()

    def _save_and_next(self) -> None:
        wings: list = []
        try:
            for idx, row in enumerate(self.rows):
                wing_name = validate_required(row["wing"].get(), "Wing Name")
                b1 = validate_positive_int(row["b1"].get(), "1 BHK Units", allow_zero=True)
                b2 = validate_positive_int(row["b2"].get(), "2 BHK Units", allow_zero=True)
                b3 = validate_positive_int(row["b3"].get(), "3 BHK Units", allow_zero=True)
                b4 = validate_positive_int(row["b4"].get(), "4 BHK Units", allow_zero=True)
                ph = validate_positive_int(row["ph"].get(), "Penthouse Units", allow_zero=True)
                if b1 + b2 + b3 + b4 + ph <= 0:
                    raise ValidationError(f"Enter at least one BHK unit count for wing '{wing_name}'.")
                height = float(row["height"].get() or 0)
                num_wings = validate_positive_int(row["num_wings"].get(), "No. of Wings", allow_zero=False)
                wings.append(ResidentialWing(
                    plot=row["plot"].get(),
                    wing=wing_name,
                    building_config=row["config"].get(),
                    building_type=row["btype"].get(),
                    building_height_m=height,
                    num_wings=num_wings,
                    flats_1bhk=b1,
                    flats_2bhk=b2,
                    flats_3bhk=b3,
                    flats_4bhk=b4,
                    flats_penthouse=ph,
                    sort_order=idx,
                ))
            if not wings:
                raise ValidationError("Add at least one residential wing.")
            self.state.residential = wings
            self.state.auto_calculate()
            self.on_next()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        self._update_subtotals()
