from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
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
        self.oht_rows: list = []
        self.oht_frame = ctk.CTkFrame(self)
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header, text="Other / Fire Tank / OHT Details", font=("Arial", 20, "bold"), text_color="white"
        ).pack(pady=12)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        fields = [
            ("landscape_a", "Landscape Area Plot-A (sq.m)", str(self.state.other.landscape_area.get("Plot-A", 765))),
            ("landscape_b", "Landscape Area Plot-B (sq.m)", str(self.state.other.landscape_area.get("Plot-B", 762))),
            ("pool_a", "Swimming Pool Plot-A (L/day)", str(int(self.state.other.swimming_pool.get("Plot-A", 0)))),
            ("pool_b", "Swimming Pool Plot-B (L/day)", str(int(self.state.other.swimming_pool.get("Plot-B", 0)))),
            ("hvac_a", "HVAC Water Plot-A (L/day)", str(int(self.state.other.hvac_water.get("Plot-A", 0)))),
            ("hvac_b", "HVAC Water Plot-B (L/day)", str(int(self.state.other.hvac_water.get("Plot-B", 0)))),
            ("fire_a", "Fire Tank Plot-A (litres)", str(int(self.state.other.fire_tank.get("Plot-A", 300000)))),
            ("fire_b", "Fire Tank Plot-B (litres)", str(int(self.state.other.fire_tank.get("Plot-B", 230000)))),
        ]
        for i, (key, label, default) in enumerate(fields):
            ctk.CTkLabel(form, text=label, font=("Arial", 13)).grid(row=i, column=0, padx=15, pady=8, sticky="w")
            ent = ctk.CTkEntry(form, width=200)
            ent.insert(0, default)
            ent.grid(row=i, column=1, padx=15, pady=8)
            self.entries[key] = ent

        ctk.CTkLabel(self, text="OHT Details (Optional - auto-calculated if empty)", font=("Arial", 14, "bold")).pack(pady=(15, 5))
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
        ctk.CTkButton(btn_frame, text="+ Add OHT Row", command=lambda: self._add_oht_row(), fg_color="#2980B9").grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="<- Back", command=self.on_back, fg_color="gray").grid(row=0, column=1, padx=10)
        ctk.CTkButton(
            btn_frame, text="Calculate & Generate Report", command=self._calculate,
            fg_color=BRAND_ORANGE, hover_color="#D06018", width=220,
        ).grid(row=0, column=2, padx=10)

    def _add_oht_row(self, oht: OHTDetail | None = None) -> None:
        r = len(self.oht_rows) + 1
        plot_var = ctk.StringVar(value=oht.plot if oht else "Plot-A")
        plot_cb = ctk.CTkComboBox(self.oht_frame, values=["Plot-A", "Plot-B"], variable=plot_var, width=90)
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
            "idx": r, "plot": plot_var, "wing": wing_ent,
            "dom": dom_ent, "flu": flu_ent, "fb": fb_ent, "fo": fo_ent,
        })

    def _calculate(self) -> None:
        try:
            self.state.other.landscape_area = {
                "Plot-A": validate_positive_float(self.entries["landscape_a"].get(), "Landscape Plot-A"),
                "Plot-B": validate_positive_float(self.entries["landscape_b"].get(), "Landscape Plot-B"),
            }
            self.state.other.swimming_pool = {
                "Plot-A": validate_positive_float(self.entries["pool_a"].get(), "Swimming Pool Plot-A"),
                "Plot-B": validate_positive_float(self.entries["pool_b"].get(), "Swimming Pool Plot-B"),
            }
            self.state.other.hvac_water = {
                "Plot-A": validate_positive_float(self.entries["hvac_a"].get(), "HVAC Plot-A"),
                "Plot-B": validate_positive_float(self.entries["hvac_b"].get(), "HVAC Plot-B"),
            }
            self.state.other.fire_tank = {
                "Plot-A": validate_positive_float(self.entries["fire_a"].get(), "Fire Tank Plot-A"),
                "Plot-B": validate_positive_float(self.entries["fire_b"].get(), "Fire Tank Plot-B"),
            }
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
            self.on_calculate()
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)

    def refresh(self) -> None:
        pass
