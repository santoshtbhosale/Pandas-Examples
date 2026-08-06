
# ============================================================
# MAIN APPLICATION
# ============================================================

class WaterDemandApp(ctk.CTk):
    NAV = [
        ("Project", "Project Details"), ("Residential", "Residential"), ("Commercial", "Commercial"),
        ("Landscape", "Landscape"), ("Swimming", "Swimming Pool"), ("HVAC", "HVAC"),
        ("UGT", "UGT / Fire Tank"), ("OHT", "OHT Details"), ("STP", "STP Summary"),
        ("Preview", "Preview"), ("Report", "Generate Report"),
        ("RWH", "Rain Water Harvesting"),
        ("Settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.app_state = AppState()
        self.title("American Edge Engineers - Water Demand Report Generator")
        self.geometry("1280x850")
        self.minsize(1100, 700)
        self.configure(fg_color="#F0F2F5")
        init_db()
        self._sidebar()
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        self.pages = {}
        self._pages()
        self.show("Project")

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        ctk.CTkLabel(sb, text="AMERICAN EDGE\nENGINEERS", font=("Arial", 14, "bold"), text_color=BRAND_ORANGE, justify="center").pack(pady=(20, 5))
        ctk.CTkLabel(sb, text="Water Demand Generator", font=("Arial", 10), text_color="white").pack(pady=(0, 15))
        self.nav_btns = {}
        for k, lbl in self.NAV:
            b = ctk.CTkButton(sb, text=lbl, height=36, anchor="w", fg_color="transparent", hover_color=BRAND_ORANGE,
                              text_color="white", font=("Arial", 12), command=lambda x=k: self.show(x))
            b.pack(fill="x", padx=8, pady=2)
            self.nav_btns[k] = b
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self._new).pack(side="bottom", fill="x", padx=10, pady=(4, 15))

    def _pages(self):
        self.pages["Project"] = ProjectPage(self.container, self.app_state, on_next=lambda: self.show("Residential"))
        self.pages["Residential"] = ResidentialPage(self.container, self.app_state, on_next=lambda: self.show("Commercial"), on_back=lambda: self.show("Project"))
        self.pages["Commercial"] = CommercialPage(self.container, self.app_state, on_next=lambda: self.show("Landscape"), on_back=lambda: self.show("Residential"))
        self.pages["Landscape"] = self._form_page("Landscape (NBC-2026)", self._landscape_ui)
        self.pages["Swimming"] = self._form_page("Swimming Pool", self._pool_ui)
        self.pages["HVAC"] = self._form_page("HVAC Water", self._hvac_ui)
        self.pages["UGT"] = self._form_page("UGT / Fire Tank", self._ugt_ui)
        self.pages["Report"] = FinalPage(self.container, self.app_state, on_back=lambda: self.show("Preview"))
        self.pages["STP"] = self._stp_page()
        self.pages["Preview"] = self._preview_page()
        try:
            from ui.pages.rwh_page import RWHPage
            from rwh.database import init_rwh_db
            init_rwh_db()
            self.pages["RWH"] = RWHPage(
                self.container,
                seed_project=self.app_state.project,
                on_back=lambda: self.show("Report"),
            )
        except Exception:
            pass
        self.pages["Settings"] = self._settings_page()
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

    def _form_page(self, title, builder):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        builder(f)
        return f

    def _landscape_ui(self, p):
        self._le = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(["Plot-A", "Plot-B"]):
            ctk.CTkLabel(form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(self.app_state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._le[plot] = e
        ctk.CTkLabel(p, text="Auto: 6 L/sq.m/day per NBC-2026", font=("Arial", 11, "italic")).pack()
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=self._save_landscape).pack(pady=12)

    def _save_landscape(self):
        try:
            for plot, e in self._le.items():
                self.app_state.other.landscape_area[plot] = validate_positive_float(e.get(), f"Landscape {plot}")
            self.show("Swimming")
        except ValidationError as ex:
            messagebox.showerror("Error", ex.message)

    def _pool_ui(self, p):
        self._pe = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(["Plot-A", "Plot-B"]):
            ctk.CTkLabel(form, text=f"Pool Makeup {plot} (L/day)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._pe[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=lambda: (self._save_dict(self._pe, self.app_state.other.swimming_pool), self.show("HVAC"))).pack(pady=12)

    def _hvac_ui(self, p):
        self._he = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(["Plot-A", "Plot-B"]):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._he[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=lambda: (self._save_dict(self._he, self.app_state.other.hvac_water), self.show("UGT"))).pack(pady=12)

    def _ugt_ui(self, p):
        self._fe = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(["Plot-A", "Plot-B"]):
            ctk.CTkLabel(form, text=f"Fire Tank {plot} (litres)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            d = 300000 if plot == "Plot-A" else 230000
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.fire_tank.get(plot, d))))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._fe[plot] = e
        ctk.CTkLabel(p, text="UGT: Domestic 2-day, Flushing 1-day storage (auto-calculated)", font=("Arial", 11, "italic")).pack(pady=5)
        ctk.CTkButton(p, text="Save & Go to OHT", fg_color=BRAND_ORANGE, command=lambda: (self._save_dict(self._fe, self.app_state.other.fire_tank), self.show("OHT"))).pack(pady=12)

    def _save_dict(self, entries, target):
        for plot, e in entries.items():
            target[plot] = float(e.get() or 0)

    def _stp_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="STP Summary", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.stp_box = ctk.CTkTextbox(f, height=400, font=("Courier", 11))
        self.stp_box.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkButton(f, text="Calculate STP", fg_color=BRAND_ORANGE, command=self._refresh_stp).pack(pady=10)
        return f

    def _refresh_stp(self):
        self._calc()
        if not self.app_state.results:
            return
        lines = []
        for pn in ("Plot-A", "Plot-B"):
            pl = self.app_state.results.plots[pn]
            lines.append(f"=== {pn} ===")
            for s in pl.stp_sections:
                lines.append(
                    f"  {s.scope}: Water {s.total_water_lpd:,} | Sewage {s.sewage_lpd:,} | "
                    f"Say {s.say_stp_kld} KLD | Treated {s.treated_water_lpd:,} | Excess {s.excess_treated_lpd:,}"
                )
            lines.append(f"  Total STP: {pl.stp_capacity_kld} KLD\n")
        self.stp_box.delete("1.0", "end")
        self.stp_box.insert("1.0", "\n".join(lines))

    def _preview_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="Report Preview (8 Pages)", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkButton(f, text="Calculate & Open Preview", fg_color="#8E44AD", height=42, command=self._open_preview).pack(pady=20)
        ctk.CTkButton(f, text="Go to Generate Report", fg_color=BRAND_ORANGE, height=38, command=lambda: (self._calc(), self.show("Report"))).pack(pady=8)
        return f

    def _settings_page(self):
        f = ScrollablePage(self.container)
        h = ctk.CTkFrame(f, fg_color=BRAND_NAVY, corner_radius=8)
        h.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(h, text="Settings", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            f,
            text=f"Database: {DB_PATH}\nLogo: {LOGO_PATH}\n\nNBC-2026 Standards:\nResidential 105+30 LPCD\nLandscape 6 L/sq.m\nSTP 90% sewage",
            font=("Arial", 12),
            justify="left",
        ).pack(anchor="w", padx=20, pady=10)
        ctk.CTkButton(f, text="Export JSON", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(f, text="Import JSON", command=self._imp_json).pack(pady=8)
        return f

    def show(self, name):
        self.pages[name].tkraise()
        if hasattr(self.pages[name], "refresh"):
            self.pages[name].refresh()
        for k, b in self.nav_btns.items():
            b.configure(fg_color=BRAND_ORANGE if k == name else "transparent")

    def _calc(self):
        try:
            self.app_state.run_calculations()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _open_preview(self):
        self._calc()
        if self.app_state.results:
            PreviewDialog(self, self.app_state.project, self.app_state.results, on_export_pdf=lambda: self.pages["Report"]._export_pdf())

    def _new(self):
        if messagebox.askyesno("New", "Start new project?"):
            self.app_state = AppState()
            for p in self.pages.values():
                p.destroy()
            self._pages()
            self.show("Project")

    def _save_db(self):
        try:
            self._calc()
            save_project(
                self.app_state.project,
                self.app_state.residential,
                self.app_state.commercial,
                self.app_state.other,
                self.app_state.results.to_dict() if self.app_state.results else None,
            )
            messagebox.showinfo("Saved", "Project saved to database.")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _open_db(self):
        projs = list_projects()
        if not projs:
            messagebox.showinfo("DB", "No projects.")
            return
        d = ctk.CTkToplevel(self)
        d.title("Recent Projects")
        d.geometry("520x420")
        d.transient(self)
        d.grab_set()
        ctk.CTkLabel(d, text="Select Project", font=("Arial", 15, "bold")).pack(pady=8)
        sf = ctk.CTkScrollableFrame(d, width=480, height=300)
        sf.pack(padx=10)
        sel = ctk.StringVar()
        for p in projs:
            ctk.CTkRadioButton(
                sf,
                text=f"{p['project_name']} | {p['client_name']} | {p['date']}",
                variable=sel,
                value=p["project_id"],
            ).pack(anchor="w", padx=8, pady=3)

        def go():
            pid = sel.get()
            if not pid:
                return
            data = load_project_from_db(pid)
            proj, res, com, oth, _ = parse_project_snapshot(data)
            self.app_state.project = proj
            self.app_state.residential = res
            self.app_state.commercial = com
            self.app_state.other = oth
            self.app_state.run_calculations()
            d.destroy()
            messagebox.showinfo("Loaded", "Project loaded.")

        ctk.CTkButton(d, text="Load", fg_color=BRAND_ORANGE, command=go).pack(pady=10)

    def _exp_json(self):
        fp = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if fp:
            _save_json_file(fp, self.app_state)
            messagebox.showinfo("Saved", "JSON exported.")

    def _imp_json(self):
        fp = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if fp:
            proj, res, com, oth, _ = _load_json_file(fp)
            self.app_state.project = proj
            self.app_state.residential = res
            self.app_state.commercial = com
            self.app_state.other = oth
            self.app_state.run_calculations()
            messagebox.showinfo("Loaded", "JSON imported.")


def _save_json_file(fp, state):
    snap = build_project_snapshot(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
    )
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)


def _load_json_file(fp):
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    return parse_project_snapshot(data)


def main():
    WaterDemandApp().mainloop()


if __name__ == "__main__":
    main()
