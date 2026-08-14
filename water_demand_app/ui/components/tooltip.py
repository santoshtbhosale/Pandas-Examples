"""Lightweight hover tooltips for form fields."""

from __future__ import annotations

import customtkinter as ctk

from ui.scheduled_callbacks import cancel_after, widget_is_alive
from ui.theme import COLOR_BORDER, COLOR_MUTED, COLOR_PRIMARY, FONT_CAPTION


class ToolTip:
    """Show help text when the pointer rests on a widget."""

    def __init__(self, widget, text: str, *, delay_ms: int = 400) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._tip_window = None
        self._after_id = None
        self._destroyed = False
        widget.bind("<Enter>", self._schedule_show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def destroy(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        self._cancel_schedule()
        self._hide()
        for sequence, handler in (
            ("<Enter>", self._schedule_show),
            ("<Leave>", self._hide),
            ("<ButtonPress>", self._hide),
        ):
            if widget_is_alive(self.widget):
                try:
                    self.widget.unbind(sequence, handler)
                except Exception:
                    pass

    def _schedule_show(self, _event=None) -> None:
        if self._destroyed:
            return
        self._cancel_schedule()
        if widget_is_alive(self.widget):
            self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_schedule(self) -> None:
        cancel_after(self.widget, self._after_id)
        self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._destroyed or self._tip_window is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            return
        self._tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        frame = ctk.CTkFrame(tw, fg_color="white", corner_radius=6, border_width=1, border_color=COLOR_BORDER)
        frame.pack()
        ctk.CTkLabel(
            frame,
            text=self.text,
            font=FONT_CAPTION,
            text_color=COLOR_PRIMARY,
            justify="left",
            wraplength=320,
        ).pack(padx=10, pady=8)

    def _hide(self, _event=None) -> None:
        self._cancel_schedule()
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


def attach_tooltip(widget, text: str) -> ToolTip:
    """Attach a tooltip and return the ToolTip instance."""
    return ToolTip(widget, text)
