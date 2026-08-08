
# ============================================================
# MAIN APPLICATION
# ============================================================

def _raise_page(page) -> None:
    """Bring a page (especially CTkScrollableFrame) to the front."""
    if hasattr(page, "lift"):
        page.lift()
    elif hasattr(page, "_parent_frame"):
        page._parent_frame.tkraise()
    else:
        page.tkraise()


class WaterDemandApp(ctk.CTk):
    NAV = [
        ("Project", "1. Project Details"),
        ("Residential", "2. Residential"),
        ("Commercial", "3. Commercial"),
        ("Hospital", "Hospital Details"),
        ("Hotel", "Hotel / Kitchen"),
        ("FoodCourt", "Food Court"),
        ("Landscape", "Landscape"),
        ("Swimming", "Swimming Pool"),
        ("HVAC", "HVAC"),
        ("UGT", "UGT / Fire Tank"),
        ("OHT", "OHT Details"),
        ("STP", "STP Summary"),
        ("Preview", "Preview"),
        ("Report", "Generate Report"),
        ("RWH", "Rain Water Harvesting"),
        ("Settings", "Settings"),
    ]

    def __init__(self, current_user=None, on_logout=None, initial_state=None, on_autosave=None):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.current_user = current_user
        self.on_logout = on_logout
        self.on_autosave = on_autosave
        self.app_state = initial_state if initial_state is not None else AppState()
        self._last_autosave_at = ""
        self.title(self._window_title())
        self.geometry("1280x850")
        self.minsize(1100, 700)
        self.configure(fg_color="#F0F2F5")
        init_db()
        init_lookup_tables(DB_PATH)
        self._autosave_job = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = self._build_sidebar()
        self.container = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.pages: dict = {}
        self._current_page = "Project"
        self._build_pages()
        self.show("Project")
        self._schedule_autosave()

    def _window_title(self) -> str:
        pid = self.app_state.project.project_id
        name = self.app_state.project.project_name or "Untitled"
        return f"Water Demand — {name} [{pid}]"

    def _reload_ui_from_state(self) -> None:
        for page in self.pages.values():
            page.destroy()
        self.pages.clear()
        self._rebuild_sidebar()
        self._build_pages()
        self.title(self._window_title())
        self.show("Project")

    def _autosave_before_close(self) -> None:
        try:
            self._calc()
            from services.project_service import persist_project_state
            persist_project_state(self.app_state, self.current_user, DB_PATH)
        except Exception:
            pass

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        try:
            self._calc()
            from services.project_service import persist_project_state
            persist_project_state(self.app_state, self.current_user, DB_PATH)
            self._last_autosave_at = datetime.now().strftime("%H:%M:%S")
            if self.on_autosave:
                self.on_autosave()
        except Exception:
            pass
        self._schedule_autosave()

    def _plots(self) -> list[str]:
        return plot_choices(self.app_state.project.plot_mode)

    def _nav_visible(self, key: str) -> bool:
        from config.page_visibility import visible_pages
        return key in visible_pages(self.app_state.project.project_type)

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=230, fg_color=BRAND_NAVY, corner_radius=0)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        ctk.CTkLabel(
            sb,
            text="AMERICAN EDGE\nENGINEERS",
            font=("Arial", 14, "bold"),
            text_color=BRAND_ORANGE,
            justify="center",
        ).pack(pady=(20, 5))
        ctk.CTkLabel(sb, text="Water Demand Generator", font=("Arial", 10), text_color="white").pack(pady=(0, 10))
        if self.current_user:
            ctk.CTkLabel(
                sb,
                text=f"{self.current_user.full_name}\n({self.current_user.role_label})",
                font=("Arial", 9),
                text_color="#CCCCCC",
                justify="center",
            ).pack(pady=(0, 4))
        pid = self.app_state.project.project_id
        ctk.CTkLabel(
            sb,
            text=f"ID: {pid}",
            font=("Arial", 8),
            text_color="#999999",
            wraplength=200,
        ).pack(pady=(0, 4))
        from config.nbc_2026 import is_project_type_set, project_type_label
        if is_project_type_set(self.app_state.project.project_type):
            ctk.CTkLabel(
                sb,
                text=project_type_label(self.app_state.project.project_type),
                font=("Arial", 9, "bold"),
                text_color=BRAND_ORANGE,
                wraplength=200,
            ).pack(pady=(0, 8))
        else:
            ctk.CTkLabel(
                sb,
                text="Select project type",
                font=("Arial", 9, "italic"),
                text_color="#AAAAAA",
                wraplength=200,
            ).pack(pady=(0, 8))
        self.nav_btns = {}
        for key, label in self.NAV:
            if not self._nav_visible(key):
                continue
            btn = ctk.CTkButton(
                sb,
                text=label,
                height=36,
                anchor="w",
                fg_color="transparent",
                hover_color=BRAND_ORANGE,
                text_color="white",
                font=("Arial", 12),
                command=lambda k=key: self.show(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_btns[key] = btn
        ctk.CTkButton(sb, text="Save Project", fg_color=BRAND_ORANGE, command=self._save_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="Open Project", fg_color="#2980B9", command=self._open_db).pack(
            side="bottom", fill="x", padx=10, pady=4
        )
        ctk.CTkButton(sb, text="New Project", fg_color="#27AE60", command=self._new).pack(
            side="bottom", fill="x", padx=10, pady=(4, 4 if self.on_logout else 15)
        )
        if self.on_logout:
            ctk.CTkButton(sb, text="Logout", fg_color="#C0392B", command=self._logout).pack(
                side="bottom", fill="x", padx=10, pady=(4, 15)
            )
        return sb

    def _logout(self) -> None:
        if self.on_logout and messagebox.askyesno("Logout", "Return to login screen?"):
            self.on_logout()

    def _rebuild_sidebar(self) -> None:
        self.sidebar.destroy()
        self.sidebar = self._build_sidebar()

    def _build_pages(self) -> None:
        self.pages["Project"] = ProjectPage(
            self.container,
            self.app_state,
            on_next=self._next_from_project,
            on_type_change=self._on_project_type_changed,
        )
        self.pages["Residential"] = ResidentialPage(
            self.container,
            self.app_state,
            on_next=self._next_from_residential,
            on_back=lambda: self.show("Project"),
        )
        self.pages["Commercial"] = CommercialPage(
            self.container,
            self.app_state,
            on_next=lambda: self._wizard_show_next("Commercial"),
            on_back=self._back_from_commercial,
        )
        self.pages["Hospital"] = self._placeholder_page(
            "Hospital Details",
            "Enter hospital bed counts and medical water requirements.\n"
            "Use Commercial page with Hospital occupancy for NBC calculations.",
            lambda: self._wizard_show_next("Hospital"),
        )
        self.pages["Hotel"] = self._placeholder_page(
            "Hotel / Kitchen / Laundry",
            "Hotel kitchen and laundry water demands are calculated from commercial occupancy rules.\n"
            "Add Hotel-type units on the Commercial page.",
            lambda: self._wizard_show_next("Hotel"),
        )
        self.pages["FoodCourt"] = self._placeholder_page(
            "Food Court",
            "Food court water demand uses Restaurant occupancy (÷1.4 population density).\n"
            "Add Restaurant units on the Commercial page.",
            lambda: self._wizard_show_next("FoodCourt"),
        )
        self.pages["Landscape"] = self._form_page("Landscape (NBC-2026)", self._landscape_ui)
        self.pages["Swimming"] = self._form_page("Swimming Pool", self._pool_ui)
        self.pages["HVAC"] = self._form_page("HVAC Water", self._hvac_ui)
        self.pages["UGT"] = self._form_page("UGT / Fire Tank", self._ugt_ui)
        self.pages["OHT"] = self._oht_page()
        self.pages["STP"] = self._stp_page()
        self.pages["Preview"] = self._preview_page()
        self.pages["Report"] = FinalPage(
            self.container,
            self.app_state,
            on_back=lambda: self.show("Preview"),
            on_generate_all=self._generate_report_all,
        )
        self.pages["RWH"] = self._create_rwh_page()
        self.pages["Settings"] = self._settings_page()
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _placeholder_page(self, title: str, body: str, on_next):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(frame, text=body, font=("Arial", 12), justify="left", wraplength=900).pack(
            anchor="w", padx=20, pady=20
        )
        ctk.CTkButton(frame, text="Next ->", fg_color=BRAND_ORANGE, command=on_next).pack(pady=12)
        return frame

    def _on_project_type_changed(self) -> None:
        from config.nbc_2026 import is_project_type_set
        from config.page_visibility import visible_pages, wizard_first_page_after_project
        self._rebuild_sidebar()
        if not is_project_type_set(self.app_state.project.project_type):
            self.show("Project")
            if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
                self.pages["Project"].refresh()
            return
        self._calc()
        visible = visible_pages(self.app_state.project.project_type)
        if self._current_page not in visible:
            self.show("Project")
        if "Project" in self.pages and hasattr(self.pages["Project"], "refresh"):
            self.pages["Project"].refresh()

    def _wizard_show_next(self, current: str) -> None:
        from config.page_visibility import wizard_next_page
        nxt = wizard_next_page(current, self.app_state.project.project_type)
        if nxt:
            self.show(nxt)
        else:
            self.show("Preview")

    def _create_rwh_page(self):
        try:
            init_rwh_db(DB_PATH)
            return RWHPage(
                self.container,
                logo_path=LOGO_PATH if os.path.exists(LOGO_PATH) else None,
                db_path=DB_PATH,
                seed_project=self.app_state.project,
                on_back=lambda: self.show("Report"),
            )
        except Exception as exc:
            return self._rwh_placeholder_page(str(exc))

    def _rwh_placeholder_page(self, reason: str = ""):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(
            header,
            text="Rain Water Harvesting",
            font=("Arial", 18, "bold"),
            text_color="white",
        ).pack(pady=10)
        message = (
            "The Rain Water Harvesting module is not available in this build.\n\n"
            "Use the modular application entry point or rebuild main.py with RWH modules included."
        )
        if reason:
            message += f"\n\nDetails: {reason}"
        ctk.CTkLabel(frame, text=message, font=("Arial", 12), justify="left", wraplength=900).pack(
            anchor="w", padx=20, pady=20
        )
        ctk.CTkButton(frame, text="Back to Generate Report", fg_color=BRAND_ORANGE, command=lambda: self.show("Report")).pack(
            pady=12
        )
        return frame

    def _form_page(self, title, builder):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        builder(frame)
        return frame

    def _landscape_ui(self, parent):
        self._le = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Landscape Area {plot} (sq.m)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(self.app_state.other.landscape_area.get(plot, 765 if plot == "Plot-A" else 762)))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_landscape_live(), self._calc()))
            self._le[plot] = entry
        ctk.CTkLabel(parent, text="Auto: 6 L/sq.m/day per NBC-2026 (live)", font=("Arial", 11, "italic")).pack(anchor="w", padx=20)
        ctk.CTkButton(parent, text="Next ->", fg_color=BRAND_ORANGE, command=self._save_landscape).pack(pady=12)

    def _sync_landscape_live(self) -> None:
        from services.automation import sync_landscape
        if hasattr(self, "_le"):
            sync_landscape(self.app_state.other, self._le)

    def _save_landscape(self):
        try:
            for plot, entry in self._le.items():
                self.app_state.other.landscape_area[plot] = validate_positive_float(entry.get(), f"Landscape {plot}")
            self._calc()
            self._wizard_show_next("Landscape")
        except ValidationError as exc:
            messagebox.showerror("Error", exc.message)

    def _pool_ui(self, parent):
        self._pe = {}
        self._pool_status = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"Swimming Pool {plot}", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            status = self.app_state.other.swimming_pool_status.get(plot, POOL_NOT_APPLICABLE)
            if self.app_state.other.swimming_pool_na.get(plot, False):
                status = POOL_NOT_APPLICABLE
            label = next((k for k, v in POOL_STATUS_LABELS.items() if v == status), "Not Applicable")
            status_var = ctk.StringVar(value=label)
            ctk.CTkComboBox(
                form,
                values=list(POOL_STATUS_LABELS.keys()),
                variable=status_var,
                width=180,
                command=lambda *_: (self._sync_pool_live(), self._calc()),
            ).grid(row=i, column=1, padx=10, pady=8, sticky="w")
            self._pool_status[plot] = status_var
            entry = ctk.CTkEntry(form, width=180)
            entry.insert(0, str(int(self.app_state.other.swimming_pool.get(plot, 0))))
            entry.grid(row=i, column=2, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_pool_live(), self._calc()))
            self._pe[plot] = entry
        ctk.CTkButton(parent, text="Next ->", fg_color=BRAND_ORANGE, command=self._save_pool).pack(pady=12)

    def _sync_pool_live(self) -> None:
        from services.automation import sync_swimming_pool
        if hasattr(self, "_pe") and hasattr(self, "_pool_status"):
            sync_swimming_pool(self.app_state.other, self._pe, self._pool_status)

    def _save_pool(self):
        for plot in self._plots():
            status = POOL_STATUS_LABELS.get(self._pool_status[plot].get(), POOL_NOT_APPLICABLE)
            self.app_state.other.swimming_pool_status[plot] = status
            self.app_state.other.swimming_pool_na[plot] = status == POOL_NOT_APPLICABLE
            if status == POOL_NOT_APPLICABLE:
                self.app_state.other.swimming_pool[plot] = 0.0
            else:
                self.app_state.other.swimming_pool[plot] = float(self._pe[plot].get() or 0)
        self._calc()
        self._wizard_show_next("Swimming")

    def _hvac_ui(self, parent):
        self._he = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        for i, plot in enumerate(self._plots()):
            ctk.CTkLabel(form, text=f"HVAC {plot} (L/day)", font=("Arial", 13)).grid(
                row=i, column=0, padx=10, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form, width=220)
            entry.insert(0, str(int(self.app_state.other.hvac_water.get(plot, 0))))
            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entry.bind("<KeyRelease>", lambda *_: (self._sync_hvac_live(), self._calc()))
            self._he[plot] = entry
        ctk.CTkButton(
            parent,
            text="Next ->",
            fg_color=BRAND_ORANGE,
            command=lambda: (self._sync_hvac_live(), self._calc(), self._wizard_show_next("HVAC")),
        ).pack(pady=12)

    def _sync_hvac_live(self) -> None:
        from services.automation import sync_hvac
        if hasattr(self, "_he"):
            sync_hvac(self.app_state.other, self._he)

    def _plot_building_info(self, plot: str) -> tuple[float, str]:
        heights_types = [
            (w.building_height_m, w.building_type)
            for w in self.app_state.residential
            if w.plot == plot and w.building_height_m > 0
        ]
        if heights_types:
            max_height = max(h for h, _ in heights_types)
            btype = next((t for h, t in heights_types if h == max_height), "")
            return max_height, btype
        project = self.app_state.project
        if project.building_height_m > 0:
            return project.building_height_m, project.building_type or "Residential Apartment"
        return 0.0, ""

    def _ugt_ui(self, parent):
        self._ugt_labels = {}
        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=20, pady=10)
        row = 0
        for plot in self._plots():
            height, btype = self._plot_building_info(plot)
            ctk.CTkLabel(form, text=f"{plot} — Building Height (m)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(
                form,
                text=f"{height:.1f}" if height else "Set on Residential page",
                font=("Arial", 12),
            ).grid(row=row, column=1, padx=10, pady=8, sticky="w")
            row += 1
            ctk.CTkLabel(form, text=f"{plot} — Building Type", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            ctk.CTkLabel(form, text=btype or "Set on Residential page", font=("Arial", 12)).grid(
                row=row, column=1, padx=10, pady=8, sticky="w"
            )
            row += 1
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            ctk.CTkLabel(form, text=f"{plot} — Fire Tank Capacity (litres)", font=("Arial", 13, "bold")).grid(
                row=row, column=0, padx=10, pady=8, sticky="w"
            )
            lbl = ctk.CTkLabel(form, text=f"{auto_val:,} (auto — NBC Table 7)", font=("Arial", 12))
            lbl.grid(row=row, column=1, padx=10, pady=8, sticky="w")
            self._ugt_labels[plot] = lbl
            row += 1
        ctk.CTkLabel(
            parent,
            text="UGT storage: Domestic 2-day, Flushing 1-day, Fire 1-day (auto-calculated in report)",
            font=("Arial", 11, "italic"),
        ).pack(anchor="w", padx=20, pady=5)
        ctk.CTkButton(parent, text="Next ->", fg_color=BRAND_ORANGE, command=lambda: self._wizard_show_next("UGT")).pack(pady=12)

    def _refresh_ugt(self) -> None:
        for plot, lbl in getattr(self, "_ugt_labels", {}).items():
            auto_val = self._auto_fire_tank(plot)
            self.app_state.other.fire_tank[plot] = float(auto_val)
            lbl.configure(text=f"{auto_val:,} (auto — NBC Table 7)")

    def _oht_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="OHT Details", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
            text="Overhead tank capacities auto-calculate from residential/commercial demand.",
            font=("Arial", 11, "italic"),
        ).pack(anchor="w", padx=20, pady=(0, 5))
        self.oht_box = ctk.CTkTextbox(frame, height=420, font=("Courier", 11))
        self.oht_box.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(
            frame,
            text="Updates automatically as you enter data on other pages.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 8))
        return frame

    def _refresh_oht(self, silent: bool = False) -> None:
        lines = ["OHT DETAILS (auto-calculated)", "=" * 60, ""]
        if not self.app_state.results:
            lines.append("Enter residential/commercial data first.")
        else:
            for plot_name in self._plots():
                plot = self.app_state.results.plots[plot_name]
                lines.append(plot_name)
                if not plot.oht_rows:
                    lines.append("  No OHT rows")
                for row in plot.oht_rows:
                    lines.append(
                        f"  {row['wing']}: Dom {row['domestic_kld']} KLD | "
                        f"Flush {row['flushing_kld']} KLD | "
                        f"Fire Break {row['fire_break_kld']} KLD | "
                        f"Fire OHT {row['fire_oht_kld']} KLD"
                    )
                lines.append("")
        self.oht_box.delete("1.0", "end")
        self.oht_box.insert("1.0", "\n".join(lines))

    def _save_dict(self, entries, target):
        for plot, entry in entries.items():
            target[plot] = float(entry.get() or 0)

    def _stp_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="STP Summary", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.stp_box = ctk.CTkTextbox(frame, height=420, font=("Courier", 11))
        self.stp_box.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(
            frame,
            text="Updates automatically as you enter data on other pages.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 8))
        return frame

    def _refresh_stp(self, silent: bool = False):
        if not self.app_state.results:
            self.stp_box.delete("1.0", "end")
            self.stp_box.insert("1.0", "Enter project data to calculate STP.")
            return
        lines = []
        for plot_name in self._plots():
            plot = self.app_state.results.plots[plot_name]
            lines.append(f"=== {plot_name} ===")
            for section in plot.stp_sections:
                lines.append(
                    f"  {section.scope}: Water {section.total_water_lpd:,} | Sewage {section.sewage_lpd:,} | "
                    f"Say {section.say_stp_kld} KLD | Treated {section.treated_water_lpd:,} | "
                    f"Excess {section.excess_treated_lpd:,}"
                )
            lines.append(f"  Total STP: {plot.stp_capacity_kld} KLD\n")
        self.stp_box.delete("1.0", "end")
        self.stp_box.insert("1.0", "\n".join(lines))

    def _preview_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Report Preview", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        self.preview_box = ctk.CTkTextbox(frame, height=360, font=("Courier", 11))
        self.preview_box.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(
            frame,
            text="Summary updates live — no Calculate button required.",
            font=("Arial", 10, "italic"),
            text_color="#666666",
        ).pack(pady=(0, 6))
        ctk.CTkButton(frame, text="Open Full Preview", fg_color="#2980B9", height=38, command=self._open_preview).pack(pady=6)
        ctk.CTkButton(
            frame,
            text="Go to Generate Report",
            fg_color=BRAND_ORANGE,
            height=38,
            command=lambda: (self._calc(), self.show("Report")),
        ).pack(pady=6)
        return frame

    def _refresh_preview(self, silent: bool = False) -> None:
        lines = ["WATER DEMAND REPORT SUMMARY", "=" * 60, ""]
        if not self.app_state.results:
            lines.append("Complete Project, Residential, and Commercial pages first.")
        else:
            project = self.app_state.project
            lines.extend(
                [
                    f"Project: {project.project_name}",
                    f"Client: {project.client_name}",
                    f"Location: {project.project_location}",
                    f"Engineer: {project.engineer_name}",
                    "",
                ]
            )
            total = self.app_state.results.total
            lines.append(f"Total Water Demand: {total.get('Total Water (LPD)', 0):,} LPD")
            lines.append(f"Total STP Capacity: {total.get('Total STP Capacity (KLD)', 0)} KLD")
            lines.append(f"Total Population: {total.get('Total Population', 0):,}")
            lines.append("")
            for plot_name in self._plots():
                plot = self.app_state.results.plots[plot_name]
                lines.append(
                    f"{plot_name}: Res {plot.res_population} pop / {plot.res_total_lpd:,} LPD | "
                    f"Comm {plot.com_population} pop / {plot.com_total_lpd:,} LPD | "
                    f"Grand Total {plot.dry_total_water_lpd:,} LPD"
                )
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", "\n".join(lines))

    def _settings_page(self):
        frame = ScrollablePage(self.container)
        header = ctk.CTkFrame(frame, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header, text="Settings", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(
            frame,
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
        ctk.CTkButton(frame, text="Export JSON", fg_color="#2980B9", command=self._exp_json).pack(pady=8)
        ctk.CTkButton(frame, text="Import JSON", fg_color="#2980B9", command=self._imp_json).pack(pady=8)
        return frame

    def _auto_fire_tank(self, plot: str) -> int:
        height, btype = self._plot_building_info(plot)
        if height > 0:
            return fire_tank_capacity_liters(height, btype)
        return int(self.app_state.other.fire_tank.get(plot, 0))

    def _next_from_project(self):
        from config.page_visibility import wizard_first_page_after_project
        self.show(wizard_first_page_after_project(self.app_state.project.project_type))

    def _next_from_residential(self):
        self._wizard_show_next("Residential")

    def _back_from_commercial(self):
        if show_residential_section(self.app_state.project.project_type):
            self.show("Residential")
        else:
            self.show("Project")

    def _resolve_page_name(self, name: str) -> str:
        return name

    def show(self, name: str) -> None:
        from config.nbc_2026 import is_project_type_set
        from config.page_visibility import visible_pages
        if not is_project_type_set(self.app_state.project.project_type) and name != "Project":
            name = "Project"
        name = self._resolve_page_name(name)
        allowed = visible_pages(self.app_state.project.project_type)
        if name not in allowed:
            name = "Project"
        if name not in self.pages:
            messagebox.showwarning(
                "Navigation",
                f"The '{name}' page is not available.\n"
                "It may be hidden for the current project type or not yet loaded.",
            )
            return
        self._current_page = name
        page = self.pages[name]
        _raise_page(page)
        if hasattr(page, "refresh"):
            page.refresh()
        if name == "STP":
            self._refresh_stp()
        elif name == "OHT":
            self._refresh_oht()
        elif name == "Preview":
            self._calc()
            self._refresh_preview(silent=True)
        elif name == "UGT":
            self._refresh_ugt()
        elif name == "Report" and hasattr(page, "refresh"):
            page.refresh()
        for key, btn in self.nav_btns.items():
            btn.configure(fg_color=BRAND_ORANGE if key == name else "transparent")

    def _calc(self):
        try:
            from services.automation import sync_pages_to_state
            sync_pages_to_state(self)
            self.app_state.auto_calculate()
            self._refresh_live_panels()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _refresh_live_panels(self) -> None:
        """Update auto-calculated panels without manual refresh buttons."""
        if hasattr(self, "_ugt_labels"):
            self._refresh_ugt()
        if self._current_page == "OHT" and hasattr(self, "oht_box"):
            self._refresh_oht(silent=True)
        elif self._current_page == "STP" and hasattr(self, "stp_box"):
            self._refresh_stp(silent=True)
        elif self._current_page == "Preview" and hasattr(self, "preview_box"):
            self._refresh_preview(silent=True)

    def _open_preview(self):
        self._calc()
        if self.app_state.results:
            PreviewDialog(
                self,
                self.app_state.project,
                self.app_state.results,
                on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
            )

    def _validate_for_report(self) -> bool:
        project = self.app_state.project
        try:
            validate_required(project.project_name, "Project Name")
            validate_required(project.client_name, "Client Name")
            validate_required(project.project_location, "Location")
            validate_required(project.engineer_name, "Engineer Name")
        except ValidationError as exc:
            messagebox.showerror("Validation Error", exc.message)
            return False
        self._calc()
        if not self.app_state.results:
            messagebox.showerror(
                "Validation Error",
                "Could not calculate water demand. Complete residential/commercial data first.",
            )
            return False
        return True

    def _generate_report_all(self) -> None:
        """One-button workflow: validate, calculate, PDF, Excel, save, preview."""
        if not self._validate_for_report():
            return
        import re

        project = self.app_state.project
        reports_dir = os.path.join(os.path.dirname(DB_PATH), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]+", "_", project.project_name or "Water_Demand")[:50].strip("_") or "Water_Demand"
        pdf_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.pdf")
        xlsx_path = os.path.join(reports_dir, f"{safe_name}_Water_Demand.xlsx")

        try:
            from services.project_service import persist_project_state
            persist_project_state(self.app_state, self.current_user, DB_PATH)
            logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            export_pdf(pdf_path, self.app_state.project, self.app_state.results, logo)
            export_excel(xlsx_path, self.app_state.project, self.app_state.results)
        except Exception as exc:
            messagebox.showerror("Generate Report", str(exc))
            return

        messagebox.showinfo(
            "Generate Report",
            f"Report generated successfully.\n\nPDF: {pdf_path}\nExcel: {xlsx_path}\n\nProject saved to database.",
        )
        self.show("Preview")
        PreviewDialog(
            self,
            self.app_state.project,
            self.app_state.results,
            on_export_pdf=lambda: self.pages["Report"]._export_pdf(),
        )

    def _new(self):
        if not messagebox.askyesno("New Project", "Start a new project? Unsaved changes will be auto-saved first."):
            return
        try:
            self._autosave_before_close()
        except Exception:
            pass
        from services.project_service import create_new_project_state
        self.app_state = create_new_project_state(self.current_user, DB_PATH)
        self._reload_ui_from_state()

    def _save_db(self):
        try:
            self._calc()
            from services.project_service import persist_project_state
            is_update = persist_project_state(self.app_state, self.current_user, DB_PATH)
            self.title(self._window_title())
            action = "updated" if is_update else "saved"
            messagebox.showinfo("Saved", f"Project {action}.\nID: {self.app_state.project.project_id}")
            if self.on_autosave:
                self.on_autosave()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _open_db(self):
        from services.project_service import find_projects, load_project_state
        projs = find_projects()
        if not projs:
            messagebox.showinfo("Open Project", "No saved projects.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open Project")
        dialog.geometry("640x440")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Select Project", font=("Arial", 15, "bold")).pack(pady=8)
        search_var = ctk.StringVar()
        ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text="Search...", width=580).pack(padx=12, pady=4)
        scroll = ctk.CTkScrollableFrame(dialog, width=600, height=300)
        scroll.pack(padx=10, pady=4)
        selected = ctk.StringVar()
        row_widgets: list = []

        def populate(query: str = "") -> None:
            for w in row_widgets:
                w.destroy()
            row_widgets.clear()
            for proj in find_projects(query):
                rb = ctk.CTkRadioButton(
                    scroll,
                    text=(
                        f"{proj['project_id']} | {proj['project_name']} | "
                        f"{proj['client_name']} | {proj.get('project_location', '')}"
                    ),
                    variable=selected,
                    value=proj["project_id"],
                )
                rb.pack(anchor="w", padx=8, pady=3)
                row_widgets.append(rb)

        search_var.trace_add("write", lambda *_: populate(search_var.get()))
        populate()

        def load_selected():
            pid = selected.get()
            if not pid:
                messagebox.showwarning("Open Project", "Select a project.")
                return
            try:
                self.app_state = load_project_state(pid, DB_PATH)
                self._reload_ui_from_state()
                dialog.destroy()
                messagebox.showinfo("Loaded", f"Project loaded.\nID: {pid}")
            except ValueError as exc:
                messagebox.showerror("Error", str(exc))

        ctk.CTkButton(dialog, text="Open", fg_color=BRAND_ORANGE, command=load_selected).pack(pady=10)

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
