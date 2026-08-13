from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ui.scheduled_callbacks import cancel_after, safe_widget_callback, widget_is_alive

PAGE_BG = "#F0F2F5"


class ScrollablePage(ctk.CTkScrollableFrame):
    """Full-size scrollable page shell used by every wizard screen."""

    _PENDING_JOB_ATTRS = ("_resize_after_id", "_auto_calc_after_id")

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", PAGE_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)
        self._resize_after_id: str | None = None
        self._auto_calc_after_id: str | None = None
        self.bind("<Configure>", self._on_self_configure, add="+")
        self.bind("<Map>", self._schedule_resize, add="+")
        self._schedule_after_idle(self._sync_to_parent)

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

    def grid(self, **kwargs):
        kwargs.setdefault("sticky", "nsew")
        super().grid(**kwargs)
        self._schedule_resize()

    def pack(self, **kwargs):
        kwargs.setdefault("fill", "both")
        kwargs.setdefault("expand", True)
        super().pack(**kwargs)
        self._schedule_resize()

    def _schedule_after_idle(self, callback: Callable[[], None]) -> None:
        cancel_after(self, self._resize_after_id)
        wrapped = safe_widget_callback(self, callback)
        self._resize_after_id = self.after_idle(wrapped)

    def _on_self_configure(self, event) -> None:
        if event.widget is not self or not widget_is_alive(self):
            return
        self._schedule_resize()

    def _schedule_resize(self, _event=None) -> None:
        if not widget_is_alive(self):
            return
        cancel_after(self, self._resize_after_id)
        self._resize_after_id = self.after_idle(safe_widget_callback(self, self._sync_to_parent))

    def _sync_to_parent(self) -> None:
        self._resize_after_id = None
        if not widget_is_alive(self):
            return
        parent = self.master
        if parent is None or not widget_is_alive(parent):
            return
        width = parent.winfo_width()
        height = parent.winfo_height()
        if width > 20 and height > 20:
            try:
                self.configure(width=width, height=height)
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
