from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ui.scheduled_callbacks import cancel_after, safe_widget_callback, widget_is_alive

PAGE_BG = "#F0F2F5"


class ScrollablePage(ctk.CTkScrollableFrame):
    """Full-size scrollable page shell used by every wizard screen."""

    _PENDING_JOB_ATTRS = ("_auto_calc_after_id",)

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", PAGE_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)
        self._auto_calc_after_id: str | None = None

    def cancel_pending_callbacks(self) -> None:
        for attr in self._PENDING_JOB_ATTRS:
            cancel_after(self, getattr(self, attr, None))
            setattr(self, attr, None)

    def destroy(self) -> None:
        self.cancel_pending_callbacks()
        try:
            super().destroy()
        except Exception:
            pass

    def schedule_auto_calculate(
        self,
        state,
        delay_ms: int = 300,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Debounce rapid input changes before running the full calculation engine."""
        if not widget_is_alive(self):
            return
        cancel_after(self, self._auto_calc_after_id)

        def _run() -> None:
            self._auto_calc_after_id = None
            if not widget_is_alive(self):
                return
            state.auto_calculate()
            if callback:
                callback()

        self._auto_calc_after_id = self.after(delay_ms, safe_widget_callback(self, _run))
