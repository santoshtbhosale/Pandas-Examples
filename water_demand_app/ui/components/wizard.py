"""Shared wizard step indicator and navigation bar."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.page_visibility import WIZARD_PAGE_ORDER, visible_pages
from ui.theme import (
    COLOR_ACCENT,
    COLOR_BORDER,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_CAPTION,
    FONT_SECTION,
    FONT_SUBTITLE,
)


def wizard_step_labels(project_type: str) -> list[str]:
    """Ordered workflow step labels including type selection."""
    labels = ["Project Type"]
    for key in WIZARD_PAGE_ORDER:
        if key in visible_pages(project_type):
            labels.append(key if key != "Project" else "Project Details")
    return labels


def wizard_step_index(page_key: str, project_type: str) -> tuple[int, int]:
    """Return (current_step_1based, total_steps) for a workflow page key."""
    labels = wizard_step_labels(project_type)
    lookup = "Project Type" if page_key == "Type" else ("Project Details" if page_key == "Project" else page_key)
    try:
        idx = labels.index(lookup)
    except ValueError:
        idx = 0
    return idx + 1, len(labels)


class StepIndicator(ctk.CTkFrame):
    """Compact step badge: STEP 2 OF 8 — Project Details."""

    def __init__(self, master, *, step: int, total: int, title: str, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        badge = ctk.CTkLabel(
            self,
            text=f"STEP {step} OF {total}",
            font=FONT_CAPTION,
            text_color=COLOR_ACCENT,
            fg_color="#FFF1E8",
            corner_radius=12,
            padx=12,
            pady=5,
        )
        badge.pack(side="left")
        ctk.CTkLabel(
            self,
            text=title,
            font=FONT_SECTION,
            text_color=COLOR_PRIMARY,
        ).pack(side="left", padx=(10, 0))


class WizardNavBar(ctk.CTkFrame):
    """Standard Back / Next navigation row."""

    def __init__(
        self,
        master,
        *,
        on_back: Optional[Callable[[], None]] = None,
        on_next: Optional[Callable[[], None]] = None,
        back_text: str = "← Back",
        next_text: str = "Next →",
        show_back: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        if show_back and on_back is not None:
            ctk.CTkButton(
                self,
                text=back_text,
                command=on_back,
                fg_color="#7F8C8D",
                hover_color="#667071",
                width=140,
                height=36,
            ).pack(side="left", padx=8)
        if on_next is not None:
            ctk.CTkButton(
                self,
                text=next_text,
                command=on_next,
                fg_color=COLOR_ACCENT,
                hover_color="#D06018",
                width=220,
                height=36,
            ).pack(side="right", padx=8)


def build_page_header(parent, title: str, subtitle: str = "", step: int = 0, total: int = 0) -> ctk.CTkFrame:
    """Consistent white card header for workflow pages."""
    wrapper = ctk.CTkFrame(parent, fg_color="white", corner_radius=12, border_width=1, border_color=COLOR_BORDER)
    wrapper.pack(fill="x", padx=18, pady=(14, 10))
    wrapper.grid_columnconfigure(0, weight=1)

    left = ctk.CTkFrame(wrapper, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=20, pady=15)
    ctk.CTkLabel(left, text=title, font=("Arial", 21, "bold"), text_color=COLOR_PRIMARY, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=FONT_SUBTITLE,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    if step > 0 and total > 0:
        StepIndicator(wrapper, step=step, total=total, title=title).grid(
            row=0, column=1, padx=18, pady=15, sticky="e"
        )
    return wrapper
