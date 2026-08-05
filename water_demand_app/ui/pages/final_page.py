from __future__ import annotations

import os

import customtkinter as ctk
from tkinter import filedialog, messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from services.database import save_project
from services.excel_exporter import export_excel
from services.json_io import save_project_json
from services.pdf_exporter import export_pdf
from ui.app_state import AppState
from ui.components.preview_dialog import PreviewDialog
from ui.components.scrollable_frame import ScrollablePage
from ui.components.validation import safe_execute


class FinalPage(ScrollablePage):
    def __init__(self, master, state: AppState, on_back) -> None:
        super().__init__(master)
        self.state = state
        self.on_back = on_back
        self.summary_label = None
        self.detail_text = None
        self._build()

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(header, text="Calculations Ready!", font=("Arial", 22, "bold"), text_color="white").pack(pady=12)

        self.summary_label = ctk.CTkLabel(self, text="", font=("Arial", 15, "bold"), justify="center")
        self.summary_label.pack(pady=10)

        self.detail_text = ctk.CTkTextbox(self, height=280, font=("Courier", 11))
        self.detail_text.pack(fill="both", expand=True, padx=20, pady=10)

        act_frame = ctk.CTkFrame(self, fg_color="transparent")
        act_frame.pack(pady=15)
        ctk.CTkButton(act_frame, text="Preview Report", command=self._preview, fg_color="#8E44AD", width=150).grid(row=0, column=0, padx=8)
        ctk.CTkButton(act_frame, text="Generate 8-Page PDF", command=self._export_pdf, fg_color="#C0392B", width=160).grid(row=0, column=1, padx=8)
        ctk.CTkButton(act_frame, text="Export Excel", command=self._export_excel, fg_color="#27AE60", width=130).grid(row=0, column=2, padx=8)
        ctk.CTkButton(act_frame, text="Save JSON", command=self._save_json, fg_color="#2980B9", width=110).grid(row=0, column=3, padx=8)
        ctk.CTkButton(act_frame, text="Save to Database", command=self._save_db, fg_color="#16A085", width=140).grid(row=0, column=4, padx=8)
        ctk.CTkButton(act_frame, text="<- Back to Edit", command=self.on_back, fg_color="gray", width=120).grid(row=0, column=5, padx=8)

    def refresh(self) -> None:
        if not self.state.results:
            self.summary_label.configure(text="No calculations available. Go back and calculate.")
            return
        tot = self.state.results.total
        pa = self.state.results.plots["Plot-A"]
        pb = self.state.results.plots["Plot-B"]
        summary = (
            f"Plot-A STP: {pa.stp_capacity_kld} KLD  |  Plot-B STP: {pb.stp_capacity_kld} KLD\n"
            f"Total Project Demand: {tot.get('Total Water (LPD)', 0):,} LPD "
            f"({tot.get('Total Water (LPD)', 0) / 1000:.2f} KLD)"
        )
        self.summary_label.configure(text=summary)

        lines = ["DETAILED CALCULATION SUMMARY", "=" * 50, ""]
        for plot_name in ("Plot-A", "Plot-B"):
            plot = self.state.results.plots[plot_name]
            lines.append(f"{plot_name}:")
            lines.append(f"  Residential: {plot.res_population} pop, {plot.res_total_lpd:,} LPD")
            lines.append(f"  Commercial: {plot.com_population} pop, {plot.com_total_lpd:,} LPD")
            lines.append(f"  Landscape: {plot.landscape_dry_lpd:,} LPD (dry), {plot.landscape_wet_lpd:,} LPD (wet)")
            lines.append(f"  Total Water (Dry): {plot.dry_total_water_lpd:,} LPD")
            lines.append(f"  UGT Domestic: {plot.ugt_domestic_liters:,} L")
            lines.append(f"  UGT Flushing: {plot.ugt_flushing_liters:,} L")
            lines.append(f"  Fire Tank: {plot.fire_tank_liters:,} L")
            lines.append(f"  STP Capacity: {plot.stp_capacity_kld} KLD")
            lines.append("")
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state="disabled")

    def _ensure_results(self) -> bool:
        if not self.state.results:
            messagebox.showwarning("No Data", "Please calculate first from the Other Details page.")
            return False
        return True

    def _preview(self) -> None:
        if not self._ensure_results():
            return
        PreviewDialog(self.winfo_toplevel(), self.state.project, self.state.results, on_export_pdf=self._export_pdf)

    def _export_pdf(self) -> None:
        if not self._ensure_results():
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="8_Page_Water_Demand_Report.pdf",
        )
        if not file_path:
            return

        def do_export():
            logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
            export_pdf(file_path, self.state.project, self.state.results, logo if os.path.exists(logo) else None)

        if safe_execute(do_export, lambda msg: messagebox.showerror("PDF Error", msg)):
            messagebox.showinfo("Success", "8-Page Professional PDF Exported Successfully!")

    def _export_excel(self) -> None:
        if not self._ensure_results():
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="Water_Demand_Report.xlsx",
        )
        if not file_path:
            return

        def do_export():
            export_excel(file_path, self.state.project, self.state.results)

        if safe_execute(do_export, lambda msg: messagebox.showerror("Excel Error", msg)):
            messagebox.showinfo("Success", "Excel Exported Successfully with Plot Tabs!")

    def _save_json(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Water Demand Project", "*.wdproj.json"), ("JSON files", "*.json")],
            initialfile=f"{self.state.project.project_id}.wdproj.json",
        )
        if not file_path:
            return

        def do_save():
            save_project_json(
                file_path,
                self.state.project,
                self.state.residential,
                self.state.commercial,
                self.state.other,
                self.state.results.to_dict() if self.state.results else None,
            )

        if safe_execute(do_save, lambda msg: messagebox.showerror("Save Error", msg)):
            messagebox.showinfo("Success", f"Project saved to {file_path}")

    def _save_db(self) -> None:
        def do_save():
            save_project(
                self.state.project,
                self.state.residential,
                self.state.commercial,
                self.state.other,
                self.state.results.to_dict() if self.state.results else None,
            )

        if safe_execute(do_save, lambda msg: messagebox.showerror("Database Error", msg)):
            messagebox.showinfo("Success", "Project saved to database successfully!")
