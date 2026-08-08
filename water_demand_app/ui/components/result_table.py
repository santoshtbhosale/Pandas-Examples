"""Professional Description | Value | Unit tables for engineering report screens."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY
from services.result_tables import TableSection

TableRow = Tuple[str, str, str]

_HEADER_BG = BRAND_NAVY
_HEADER_FG = "white"
_BORDER = "#C5CED8"
_ROW_EVEN = "#FFFFFF"
_ROW_ODD = "#F4F6F8"
_VALUE_FG = "#1A5276"


class ResultTableView(ctk.CTkFrame):
    """Renders one or more titled result tables inside a scrollable host."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._host = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self._host.pack(fill="both", expand=True)

    def set_sections(self, sections: Sequence[TableSection]) -> None:
        for child in self._host.winfo_children():
            child.destroy()
        if not sections:
            self._add_empty_message("No data available.")
            return
        for section in sections:
            self._render_section(section.title, section.rows)

    def set_rows(self, title: str, rows: Iterable[TableRow]) -> None:
        for child in self._host.winfo_children():
            child.destroy()
        self._render_section(title, tuple(rows))

    def _add_empty_message(self, text: str) -> None:
        ctk.CTkLabel(
            self._host,
            text=text,
            font=("Arial", 12),
            text_color="#666666",
            anchor="w",
        ).pack(fill="x", padx=12, pady=8)

    def _render_section(self, title: str, rows: Sequence[TableRow]) -> None:
        wrapper = ctk.CTkFrame(self._host, fg_color="transparent")
        wrapper.pack(fill="x", padx=8, pady=(10, 4))

        ctk.CTkLabel(
            wrapper,
            text=title,
            font=("Arial", 13, "bold"),
            text_color=BRAND_NAVY,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(0, 6))

        table = ctk.CTkFrame(wrapper, fg_color="white", corner_radius=6, border_width=1, border_color=_BORDER)
        table.pack(fill="x", padx=2, pady=2)
        table.columnconfigure(0, weight=3, uniform="cols")
        table.columnconfigure(1, weight=1, uniform="cols")
        table.columnconfigure(2, weight=1, uniform="cols")

        headers = ("Description", "Value", "Unit")
        for col, label in enumerate(headers):
            cell = ctk.CTkFrame(table, fg_color=_HEADER_BG, corner_radius=0)
            cell.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 1, 0), pady=(0, 1))
            ctk.CTkLabel(
                cell,
                text=label,
                font=("Arial", 11, "bold"),
                text_color=_HEADER_FG,
                anchor="w" if col == 0 else "e" if col == 1 else "w",
            ).pack(fill="x", padx=10, pady=6)

        if not rows:
            empty = ctk.CTkFrame(table, fg_color=_ROW_EVEN, corner_radius=0)
            empty.grid(row=1, column=0, columnspan=3, sticky="nsew")
            ctk.CTkLabel(empty, text="No rows", font=("Arial", 11), text_color="#888888").pack(padx=10, pady=8)
            return

        for ridx, (desc, value, unit) in enumerate(rows, start=1):
            bg = _ROW_EVEN if ridx % 2 == 1 else _ROW_ODD
            values = (desc, value, unit)
            anchors = ("w", "e", "w")
            for col, (text, anchor) in enumerate(zip(values, anchors)):
                cell = ctk.CTkFrame(table, fg_color=bg, corner_radius=0)
                cell.grid(row=ridx, column=col, sticky="nsew", padx=(0 if col == 0 else 1, 0), pady=(0, 1))
                font = ("Arial", 11, "bold") if desc.startswith("Total") else ("Arial", 11)
                fg = _VALUE_FG if col == 1 else "#222222"
                ctk.CTkLabel(
                    cell,
                    text=text,
                    font=font,
                    text_color=fg,
                    anchor=anchor,
                ).pack(fill="x", padx=10, pady=5)
