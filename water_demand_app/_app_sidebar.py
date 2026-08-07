
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
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar()
        self.container = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.pages = {}
        self._pages()
        self.show("Project")

    def _plots(self) -> list[str]:
        return plot_choices(self.app_state.project.plot_mode)

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text="AMERICAN EDGE\nENGINEERS", font=("Arial", 14, "bold"), text_color=BRAND_ORANGE, justify="center").pack(pady=(20, 5))
        ctk.CTkLabel(sb, text="Water Demand Generator", font=("Arial", 10), text_color="white").pack(pady=(0, 15))
        self.nav_btns = {}
        for k, lbl in self.NAV:
            if k == "Residential" and not show_residential_section(self.app_state.project.project_type):
                continue
            if k == "Commercial" and not show_commercial_section(self.app_state.project.project_type):
                continue
            if k == "HVAC" and not hvac_applicable(self.app_state.project.project_type):
                continue
            b = ctk.CTkButton(sb, text=lbl, height=36, anchor="w", fg_color="transparent", hover_color=BRAND_ORANGE,
                              text_color="white", font=("Arial", 12), command=lambda x=k: self.show(x))
            b.pack(fill="x", padx=8, pady=2)
            self.nav_btns[k] = b
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(side="bottom", fill="x", padx=10, pady=4)
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self._new).pack(side="bottom", fill="x", padx=10, pady=(4, 15))

    def _pages(self):
        self.pages["Project"] = ProjectPage(self.container, self.app_state, on_next=self._next_from_project)
        self.pages["Residential"] = ResidentialPage(self.container, self.app_state, on_next=self._next_from_residential, on_back=lambda: self.show("Project"))
        self.pages["Commercial"] = CommercialPage(self.container, self.app_state, on_next=lambda: self.show("Landscape"), on_back=self._back_from_commercial)
        self.pages["Landscape"] = self._form_page("Landscape (NBC-2026)", self._landscape_ui)
        self.pages["Swimming"] = self._form_page("Swimming Pool", self._pool_ui)
        if hvac_applicable(self.app_state.project.project_type):
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
        for i, plot in enumerate(self._plots()):
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
        self._pool_status = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Swimming Pool {plot}", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            status = self.app_state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
            if self.app_state.other.swimming_pool_na.get(plot, False):
                status = POOL_NOT_APPLICABLE
            label = next((k for k, v in POOL_STATUS_LABELS.items() if v == status), "Not Applicable")
            status_var = ctk.StringVar(value=label)
            ctk.CTkComboBox(form, values=list(POOL_STATUS_LABELS.keys()), variable=status_var, width=160).grid(
                row=i, column=1, padx=10, pady=8, sticky="w"
            )
            self._pool_status[plot] = status_var
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            e.grid(row=i, column=2, padx=10, pady=8)
            self._pe[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=self._save_pool).pack(pady=12)

    def _save_pool(self):
        for plot in self._plots():
            status = POOL_STATUS_LABELS.get(self._pool_status[plot].get(), POOL_NOT_APPLICABLE)
            self.app_state.other.swimming_pool_status[plot] = status
            self.app_state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
            if status == POOL_NOT_APPLICABLE:
                self.app_state.other.swimming_pool[plot] = 0.0
            else:
                self.app_state.other.swimming_pool[plot] = float(self._pe[plot].get() or 0)
        self.app_state.auto_calculate()
        next_page = "HVAC" if hvac_applicable(self.app_state.project.project_type) else "UGT"
        self.show(next_page)

    def _hvac_ui(self, p):
        self._he = {}
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            e = ctk.CTkEntry(form, width=180)
            e.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            e.grid(row=i, column=1, padx=10, pady=8)
            self._he[plot] = e
        ctk.CTkButton(p, text="Save & Next", fg_color=BRAND_ORANGE, command=lambda: (self._save_dict(self._he, self.app_state.other.hvac_water), self.show("UGT"))).pack(pady=12)

    def _ugt_ui(self, p):
        form = ctk.CTkFrame(p)
        form.pack(padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Fire Tank {plot} (litres)", font=("Arial", 13)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            auto_val = self._auto_fire_tank(plot)
            ctk.CTkLabel(form, text=f"{auto_val:,} (auto from NBC height table)", font=("Arial", 12)).grid(
                row=i, column=1, padx=10, pady=8, sticky="w"
            )
            self.app_state.other.fire_tank[plot] = float(auto_val)
        ctk.CTkLabel(p, text="UGT: Domestic 2-day, Flushing 1-day storage (auto-calculated)", font=("Arial", 11, "italic")).pack(pady=5)
        ctk.CTkButton(p, text="Save & Go to OHT", fg_color=BRAND_ORANGE, command=lambda: self.show("OHT")).pack(pady=12)

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
        for pn in self._plots():
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
            text=(
                f"Database:\n{DB_PATH}\n\n"
                f"Logo:\n{LOGO_PATH}\n\n"
                "NBC-2026 Standards:\n"
                "Residential 105+30 LPCD\n"
                "Landscape 6 L/sq.m\n"
                "STP 90% sewage"
            ),
            font=("Arial", 12),
            justify="left",
            anchor="w",
            wraplength=900,
        ).pack(fill="x", anchor="w", padx=20, pady=10)
        ctk.CTkButton(f, text="Export JSON", fg_color="#2980B9", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(f, text="Import JSON", fg_color="#2980B9", command=self._imp_json).pack(pady=8)
        return f

    def _auto_fire_tank(self, plot: str) -> int:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.app_state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return fire_tank_capacity_liters(max_height, btype)
        return int(self.app_state.other.fire_tank.get(plot, 0))

    def _next_from_project(self):
        ptype = self.app_state.project.project_type
        if show_residential_section(ptype):
            self.show("Residential")
        elif show_commercial_section(ptype):
            self.show("Commercial")
        else:
            self.show("Landscape")

    def _next_from_residential(self):
        if show_commercial_section(self.app_state.project.project_type):
            self.show("Commercial")
        else:
            self.show("Landscape")

    def _back_from_commercial(self):
        if show_residential_section(self.app_state.project.project_type):
            self.show("Residential")
        else:
            self.show("Project")

    def show(self, name):
        if name == "HVAC" and not hvac_applicable(self.app_state.project.project_type):
            self.show("UGT")
            return
        if name == "Residential" and not show_residential_section(self.app_state.project.project_type):
            self.show("Commercial" if show_commercial_section(self.app_state.project.project_type) else "Landscape")
            return
        if name == "Commercial" and not show_commercial_section(self.app_state.project.project_type):
            self.show("Residential" if show_residential_section(self.app_state.project.project_type) else "Landscape")
            return
        self.pages[name].tkraise()
        if hasattr(self.pages[name], "refresh"):
            self.pages[name].refresh()
        for k, b in self.nav_btns.items():
            b.configure(fg_color=BRAND_ORANGE if k == name else "transparent")

    def _calc(self):
        try:
            self.app_state.auto_calculate()
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
