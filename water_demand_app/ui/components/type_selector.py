"""Visual project type selection cards — one-click, 3-column grid, no scrolling."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import PROJECT_TYPE_LABELS, PROJECT_TYPE_PLACEHOLDER
from ui.theme import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_PRIMARY,
    FONT_CAPTION,
    PROJECT_TYPE_ICONS,
)

TYPE_DESCRIPTIONS = {
    "Residential": "Residential buildings",
    "Commercial": "Commercial buildings",
    "Mixed Use": "Mixed-use developments",
    "Industrial": "Industrial facilities",
    "Hospital": "Healthcare facilities",
    "Hotel": "Hotels and hospitality",
    "School": "School campuses",
    "College": "College campuses",
    "Shopping Mall": "Retail shopping malls",
    "Mall": "Retail malls",
    "IT Park": "IT parks and tech campuses",
    "Warehouse": "Warehouses and logistics",
    "Township": "Township developments",
}


def _bind_recursive(widget, sequence: str, handler) -> None:
    """Bind an event on a widget and every descendant."""
    try:
        widget.bind(sequence, handler, add="+")
    except Exception:
        pass
    for child in widget.winfo_children():
        _bind_recursive(child, sequence, handler)


class ProjectTypeSelector(ctk.CTkFrame):
    """Compact 3-column grid; one click selects type and opens the workflow."""

    def __init__(
        self,
        master,
        *,
        initial_label: str = PROJECT_TYPE_PLACEHOLDER,
        on_project_type_selected: Optional[Callable[[str], None]] = None,
        on_selection_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_project_type_selected = on_project_type_selected or on_selection_change
        self._selected = ctk.StringVar(value=initial_label)
        self._cards: dict[str, ctk.CTkFrame] = {}
        self._busy = False
        self._build()

    def get_selected(self) -> str:
        return self._selected.get()

    def set_selected(self, label: str) -> None:
        """Update highlight only (no navigation)."""
        self._selected.set(label)
        self._refresh_highlights()

    def select_type(self, label: str) -> None:
        """Programmatic one-click selection (same as user click)."""
        self._on_project_type_selected(label)

    def _build(self) -> None:
        labels = sorted(set(PROJECT_TYPE_LABELS.keys()))
        cols = 3
        for i, label in enumerate(labels):
            row, col = divmod(i, cols)
            card = self._make_card(label)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)

    def _make_card(self, label: str) -> ctk.CTkFrame:
        icon = PROJECT_TYPE_ICONS.get(label, "📋")
        description = TYPE_DESCRIPTIONS.get(label, "Water demand report")

        frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=2,
            border_color=COLOR_BORDER,
            height=72,
            cursor="hand2",
        )
        frame.grid_propagate(False)
        self._cards[label] = frame

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=8)

        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")
        check = ctk.CTkLabel(title_row, text="", font=FONT_CAPTION, text_color=COLOR_ACCENT, width=16)
        check.pack(side="right")
        frame._check_label = check  # type: ignore[attr-defined]
        ctk.CTkLabel(
            title_row,
            text=f"{icon}  {label}",
            font=("Arial", 12, "bold"),
            text_color=COLOR_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            inner,
            text=description,
            font=FONT_CAPTION,
            text_color="#687684",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        def select(_event=None, lbl=label):
            self._on_project_type_selected(lbl)

        def on_enter(_event=None, card=frame, lbl=label):
            if self._busy or self._selected.get() == lbl:
                return
            card.configure(border_color=COLOR_PRIMARY, fg_color="#F8FAFC")

        def on_leave(_event=None, card=frame, lbl=label):
            if self._busy:
                return
            is_sel = self._selected.get() == lbl and lbl != PROJECT_TYPE_PLACEHOLDER
            card.configure(
                border_color=COLOR_ACCENT if is_sel else COLOR_BORDER,
                fg_color="#FFF8F0" if is_sel else COLOR_CARD,
            )

        _bind_recursive(frame, "<Button-1>", select)
        _bind_recursive(frame, "<Enter>", on_enter)
        _bind_recursive(frame, "<Leave>", on_leave)

        return frame

    def _on_project_type_selected(self, label: str) -> None:
        if self._busy or label == PROJECT_TYPE_PLACEHOLDER:
            return
        self._busy = True
        self._selected.set(label)
        self._refresh_highlights()
        if self.on_project_type_selected:
            try:
                self.on_project_type_selected(label)
            except Exception:
                self._busy = False
                raise

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
