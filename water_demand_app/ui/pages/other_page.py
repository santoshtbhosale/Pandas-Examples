from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import (
    BRAND_NAVY,
    BRAND_ORANGE,
    POOL_NOT_APPLICABLE,
    POOL_STATUS_LABELS,
    fire_tank_capacity_liters,
    hvac_applicable,
    plot_choices,
)
from models.other_details import OHTDetail
from ui.app_state import AppState
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import ValidationError, validate_positive_float


class OtherPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_calculate, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_calculate = on_calculate
        self.on_back = on_back
        self.entries: dict = {}
        self.pool_status_vars: dict = {}
        self.pool_entries: dict = {}
        self.oht_rows: list = []
        self.oht_frame = ctk.CTkFrame(self)
        self.fire_labels: dict = {}
        self._build()

    def _plots(self) -> list[str]:
        return plot_choices(self.state.project.plot_mode)

    def _auto_fire_tank(self, plot: str) -> int:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return fire_tank_capacity_liters(max_height, btype)
        return int(self.state.other.fire_tank.get(plot, 0))

    def _pool_label_for_plot(self, plot: str) -> str:
        status = self.state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
        if self.state.other.swimming_pool_na.get(plot, False):
            status = POOL_NOT_APPLICABLE
        for label, value in POOL_STATUS_LABELS.items():
            if value == status:
                return label
        return "Not Applicable"

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header,
            text="Landscape / Pool / HVAC / Fire Tank / OHT",
            font=("Arial", 20, "bold"),
            text_color="white",
        ).pack(pady=12)
        ctk.CTkLabel(
            header,
            text="UGT, OHT, STP & Fire Tank auto-calculate — updates on every change",
            font=("Arial", 11),
            text_color="#ECF0F1",
        ).pack(pady=(0, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        row = 0
        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=200)
            ent.insert(0, str(self.state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            ent.grid(row=row, column=1, padx=15, pady=8)
            ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
            self.entries[f"landscape_{plot}"] = ent
            row += 1

        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Swimming Pool {plot}", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            status_var = ctk.StringVar(value=self._pool_label_for_plot(plot))
            status_cb = ctk.CTkComboBox(
                form, values=list(POOL_STATUS_LABELS.keys()), variable=status_var, width=160,
                command=lambda *_: self._toggle_pool_fields(),
            )
            status_cb.grid(row=row, column=1, padx=15, pady=8, sticky="w")
            self.pool_status_vars[plot] = status_var
            pool_ent = ctk.CTkEntry(form, width=200)
            pool_ent.insert(0, str(int(self.state.other.swimming_pool.get(plot, 0))))
            pool_ent.grid(row=row, column=2, padx=15, pady=8)
            pool_ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
            self.pool_entries[plot] = pool_ent
            row += 1
        self._toggle_pool_fields()

        self.hvac_entries: dict = {}
        if hvac_applicable(self.state.project.project_type):
            for plot in self._plots():
                ctk.CTkLabel(
                    form, text=f"HVAC Water {plot} (L/day)", font=("Arial", 13)
                ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
                ent = ctk.CTkEntry(form, width=200)
                ent.insert(0, str(int(self.state.other.hvac_water.get(plot, 0))))
                ent.grid(row=row, column=1, padx=15, pady=8)
                ent.bind("<KeyRelease>", lambda *_: self._sync_and_calc())
                self.hvac_entries[plot] = ent
                row += 1
        else:
            ctk.CTkLabel(
                form,
                text="HVAC: Applicable only for Commercial and IT Park projects",
                font=("Arial", 12, "italic"),
                text_color="#7F8C8D",
            ).grid(row=row, column=0, columnspan=3, padx=15, pady=8, sticky="w")
            row += 1

        for plot in self._plots():
            ctk.CTkLabel(
                form, text=f"Fire Tank {plot} (litres)", font=("Arial", 13)
            ).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            auto_val = self._auto_fire_tank(plot)
            lbl = ctk.CTkLabel(
                form, text=f"{auto_val:,} (auto — NBC Table 7)", font=("Arial", 12)
            )
            lbl.grid(row=row, column=1, columnspan=2, padx=15, pady=8, sticky="w")
            self.fire_labels[plot] = lbl
            row += 1

        ctk.CTkLabel(self, text="OHT Details (Optional — auto-calculated if empty)", font=("Arial", 14, "bold")).pack(
            pady=(15, 5)
        )
        self.oht_frame.pack(fill="x", padx=15, pady=5)
        oht_headers = ["Plot", "Wing/Block", "Domestic KLD", "Flushing KLD", "Fire Break KLD", "Fire OHT KLD", ""]
        for i, h in enumerate(oht_headers):
            ctk.CTkLabel(self.oht_frame, text=h, font=("Arial", 11, "bold")).grid(row=0, column=i, padx=3, pady=3)

        if self.state.other.oht_details:
            for oht in self.state.other.oht_details:
                self._add_oht_row(oht)
        else:
            self._add_oht_row()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="+ Add OHT Row", command=lambda: self._add_oht_row(), fg_color="#2980B9").grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Next -> Generate Report",
            command=self._finish,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            width=220,
        ).grid(row=0, column=2, padx=10)

        self._sync_and_calc()

    def _toggle_pool_fields(self) -> None:
        for plot, var in self.pool_status_vars.items():
            ent = self.pool_entries.get(plot)
            if not ent:
                continue
            if var.get() == "Not Applicable":
                ent.configure(state="disabled")
            else:
                ent.configure(state="normal")
        self._sync_and_calc()

    def _sync_and_calc(self) -> None:
        try:
            for plot in self._plots():
                self.state.other.landscape_area[plot] = float(
                    self.entries[f"landscape_{plot}"].get() or 0
                )
                status = POOL_STATUS_LABELS.get(
                    self.pool_status_vars[plot].get(), POOL_NOT_APPLICABLE
                )
                self.state.other.swimming_pool_status[plot] = status
                self.state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
                if status == POOL_NOT_APPLICABLE:
                    self.state.other.swimming_pool[plot] = 0.0
                else:
                    self.state.other.swimming_pool[plot] = float(
                        self.pool_entries[plot].get() or 0
                    )
                if hvac_applicable(self.state.project.project_type):
                    self.state.other.hvac_water[plot] = float(
                        self.hvac_entries[plot].get() or 0
                    )
                else:
                    self.state.other.hvac_water[plot] = 0.0
                self.state.other.fire_tank[plot] = float(self._auto_fire_tank(plot))
            self.state.auto_calculate()
            for plot, lbl in self.fire_labels.items():
                lbl.configure(text=f"{self._auto_fire_tank(plot):,} (auto — NBC Table 7)")
        except (ValueError, KeyError):
            pass

    def _add_oht_row(self, oht: OHTDetail | None = None) -> None:
        r = len(self.oht_rows) + 1
        plot_var = ctk.StringVar(value=oht.plot if oht else self._plots()[0])
        plot_cb = ctk.CTkComboBox(self.oht_frame, values=self._plots(), variable=plot_var, width=90)
        wing_ent = ctk.CTkEntry(self.oht_frame, width=100)
        wing_ent.insert(0, oht.wing if oht else "")
        dom_ent = ctk.CTkEntry(self.oht_frame, width=80)
        dom_ent.insert(0, str(oht.domestic_kld if oht else ""))
        flu_ent = ctk.CTkEntry(self.oht_frame, width=80)
        flu_ent.insert(0, str(oht.flushing_kld if oht else ""))
        fb_ent = ctk.CTkEntry(self.oht_frame, width=80)
        fb_ent.insert(0, str(oht.fire_break_kld if oht else ""))
        fo_ent = ctk.CTkEntry(self.oht_frame, width=80)
        fo_ent.insert(0, str(oht.fire_oht_kld if oht else ""))

        plot_cb.grid(row=r, column=0, padx=3, pady=3)
        wing_ent.grid(row=r, column=1, padx=3, pady=3)
        dom_ent.grid(row=r, column=2, padx=3, pady=3)
        flu_ent.grid(row=r, column=3, padx=3, pady=3)
        fb_ent.grid(row=r, column=4, padx=3, pady=3)
        fo_ent.grid(row=r, column=5, padx=3, pady=3)

        def remove():
            for w in widgets:
                w.destroy()
            self.oht_rows = [row for row in self.oht_rows if row["idx"] != r]

        rm_btn = ctk.CTkButton(self.oht_frame, text="X", width=30, fg_color="#C0392B", command=remove)
        rm_btn.grid(row=r, column=6, padx=3, pady=3)
        widgets = [plot_cb, wing_ent, dom_ent, flu_ent, fb_ent, fo_ent, rm_btn]
        self.oht_rows.append({
            "idx": r,
            "plot": plot_var,
            "wing": wing_ent,
            "dom": dom_ent,
            "flu": flu_ent,
            "fb": fb_ent,
            "fo": fo_ent,
        })

    def _finish(self) -> None:
        try:
            for plot in self._plots():
                self.state.other.landscape_area[plot] = validate_positive_float(
                    self.entries[f"landscape_{plot}"].get(), f"Landscape {plot}"
                )
                status = POOL_STATUS_LABELS.get(
                    self.pool_status_vars[plot].get(), POOL_NOT_APPLICABLE
                )
                self.state.other.swimming_pool_status[plot] = status
                self.state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
                if status != POOL_NOT_APPLICABLE:
                    self.state.other.swimming_pool[plot] = validate_positive_float(
                        self.pool_entries[plot].get(), f"Swimming Pool {plot}"
                    )
                else:
                    self.state.other.swimming_pool[plot] = 0.0
                if hvac_applicable(self.state.project.project_type):
                    self.state.other.hvac_water[plot] = validate_positive_float(
                        self.hvac_entries[plot].get(), f"HVAC {plot}"
                    )
                else:
                    self.state.other.hvac_water[plot] = 0.0
                self.state.other.fire_tank[plot] = float(self._auto_fire_tank(plot))
            oht_list = []
            for row in self.oht_rows:
                wing = row["wing"].get().strip()
                if wing:
                    oht_list.append(OHTDetail(
                        plot=row["plot"].get(),
                        wing=wing,
                        domestic_kld=validate_positive_float(row["dom"].get(), f"OHT Domestic ({wing})"),
                        flushing_kld=validate_positive_float(row["flu"].get(), f"OHT Flushing ({wing})"),
                        fire_break_kld=validate_positive_float(row["fb"].get(), f"OHT Fire Break ({wing})"),
                        fire_oht_kld=validate_positive_float(row["fo"].get(), f"OHT Fire OHT ({wing})"),
                    ))
            self.state.other.oht_details = oht_list
            self.state.auto_calculate()
            self.on_calculate()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        for plot, lbl in self.fire_labels.items():
            lbl.configure(text=f"{self._auto_fire_tank(plot):,} (auto — NBC Table 7)")
        self._sync_and_calc()
