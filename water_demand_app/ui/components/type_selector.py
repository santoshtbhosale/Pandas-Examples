"""Visual project type selection cards — compact grid, no scrolling."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import PROJECT_TYPE_LABELS, PROJECT_TYPE_PLACEHOLDER
from ui.theme import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_PRIMARY,
    FONT_SECTION,
    PROJECT_TYPE_ICONS,
)


class ProjectTypeSelector(ctk.CTkFrame):
    """Compact grid of selectable project type cards (fits one screen)."""

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
        cols = 4
        for i, label in enumerate(labels):
            row, col = divmod(i, cols)
            card = self._make_card(label)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)

    def _make_card(self, label: str) -> ctk.CTkFrame:
        icon = PROJECT_TYPE_ICONS.get(label, "📋")
        frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            corner_radius=8,
            border_width=2,
            border_color=COLOR_BORDER,
            height=52,
            cursor="hand2",
        )
        frame.grid_propagate(False)
        self._cards[label] = frame

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8, pady=6)
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        check = ctk.CTkLabel(row, text="", font=FONT_SECTION, text_color=COLOR_ACCENT, width=14)
        check.pack(side="right")
        frame._check_label = check  # type: ignore[attr-defined]
        ctk.CTkLabel(
            row,
            text=f"{icon} {label}",
            font=("Arial", 11, "bold"),
            text_color=COLOR_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

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
