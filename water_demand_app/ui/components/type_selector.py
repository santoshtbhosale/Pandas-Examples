"""Visual project type selection cards."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import PROJECT_TYPE_LABELS, PROJECT_TYPE_PLACEHOLDER
from ui.theme import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_BODY,
    FONT_SECTION,
    PROJECT_TYPE_ICONS,
)


TYPE_DESCRIPTIONS = {
    "Residential": "Apartments, villas and housing projects.",
    "Commercial": "Offices, shops and business developments.",
    "Mixed Use": "Residential and commercial combined.",
    "Township": "Large multi-component developments.",
    "Hotel": "Hotels and hospitality projects.",
    "Hospital": "Hospitals and healthcare facilities.",
    "School": "Schools and educational campuses.",
    "College": "Colleges and higher-education campuses.",
    "Shopping Mall": "Malls and retail developments.",
    "Mall": "Malls and retail developments.",
    "IT Park": "IT parks and technology campuses.",
    "Industrial": "Industrial and manufacturing projects.",
    "Warehouse": "Warehouses and storage facilities.",
}


class ProjectTypeSelector(ctk.CTkFrame):
    """Grid of selectable project type cards."""

    def __init__(
        self,
        master,
        *,
        initial_label: str = PROJECT_TYPE_PLACEHOLDER,
        on_selection_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_selection_change = on_selection_change
        self._selected = ctk.StringVar(value=initial_label)
        self._cards: dict[str, ctk.CTkFrame] = {}
        self._build()

    def get_selected(self) -> str:
        return self._selected.get()

    def set_selected(self, label: str) -> None:
        self._selected.set(label)
        self._refresh_highlights()

    def _build(self) -> None:
        labels = sorted(set(PROJECT_TYPE_LABELS.keys()))
        cols = 3
        for i, label in enumerate(labels):
            row, col = divmod(i, cols)
            card = self._make_card(label)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            for c in range(cols):
                self.grid_columnconfigure(c, weight=1)

    def _make_card(self, label: str) -> ctk.CTkFrame:
        icon = PROJECT_TYPE_ICONS.get(label, "📋")
        frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=2,
            border_color=COLOR_BORDER,
            width=200,
            height=88,
            cursor="hand2",
        )
        frame.grid_propagate(False)
        self._cards[label] = frame

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=8)
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")
        check = ctk.CTkLabel(title_row, text="", font=FONT_SECTION, text_color=COLOR_ACCENT, width=16)
        check.pack(side="right")
        frame._check_label = check  # type: ignore[attr-defined]
        ctk.CTkLabel(
            title_row,
            text=f"{icon}  {label}",
            font=FONT_SECTION,
            text_color=COLOR_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            inner,
            text=TYPE_DESCRIPTIONS.get(label, ""),
            font=("Arial", 9),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            wraplength=170,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        def select(_event=None, lbl=label):
            self._selected.set(lbl)
            self._refresh_highlights()
            if self.on_selection_change:
                self.on_selection_change(lbl)

        frame.bind("<Button-1>", select)
        for child in frame.winfo_children():
            child.bind("<Button-1>", select)
            for sub in child.winfo_children():
                sub.bind("<Button-1>", select)

        return frame

    def _refresh_highlights(self) -> None:
        selected = self._selected.get()
        for label, card in self._cards.items():
            is_sel = label == selected and selected != PROJECT_TYPE_PLACEHOLDER
            card.configure(
                border_color=COLOR_ACCENT if is_sel else COLOR_BORDER,
                fg_color="#FFF8F0" if is_sel else COLOR_CARD,
            )
            check = getattr(card, "_check_label", None)
            if check is not None:
                check.configure(text="✓" if is_sel else "")
