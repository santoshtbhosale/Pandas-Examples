from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
import tkinter as tk

from ui.scheduled_callbacks import cancel_after, PageLifecycleMixin, safe_widget_callback, widget_is_alive

PAGE_BG = "#F0F2F5"


class ScrollablePage(PageLifecycleMixin, ctk.CTkScrollableFrame):
    """Full-size scrollable page shell used by every wizard screen."""

    _PENDING_JOB_ATTRS = ("_auto_calc_after_id",)

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", PAGE_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)
        self._init_page_lifecycle()
        self._auto_calc_after_id: str | None = None
        self._replace_configure_binding()

    def _replace_configure_binding(self) -> None:
        """Replace CTk's default Configure handler with a destroy-safe version."""
        try:
            self.unbind("<Configure>")
        except (tk.TclError, AttributeError, RuntimeError, ValueError):
            pass
        self.bind("<Configure>", self._on_configure_safe, add="+")

    def _on_configure_safe(self, event=None) -> None:
        if not widget_is_alive(self):
            return
        parent_canvas = getattr(self, "_parent_canvas", None)
        if not widget_is_alive(parent_canvas):
            return
        try:
            bbox = parent_canvas.bbox("all")
            if bbox is not None:
                parent_canvas.configure(scrollregion=bbox)
        except tk.TclError:
            return

    def cancel_pending_callbacks(self) -> None:
        self.prepare_for_destroy()

    def prepare_for_destroy(self) -> None:
        if getattr(self, "_lifecycle_prepared", False):
            return
        self._lifecycle_prepared = True
        self.cancel_page_lifecycle()
        for attr in self._PENDING_JOB_ATTRS:
            setattr(self, attr, None)
        self._detach_page_bindings()

    def _detach_page_bindings(self) -> None:
        try:
            self.unbind("<Configure>")
        except (tk.TclError, AttributeError, RuntimeError, ValueError):
            pass
        parent_canvas = getattr(self, "_parent_canvas", None)
        if parent_canvas is not None and widget_is_alive(parent_canvas):
            try:
                parent_canvas.unbind("<Configure>")
            except (tk.TclError, AttributeError, RuntimeError, ValueError):
                pass

    def destroy(self) -> None:
        self.prepare_for_destroy()
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
        if self._auto_calc_after_id in self._after_jobs:
            try:
                self._after_jobs.remove(self._auto_calc_after_id)
            except ValueError:
                pass
        self._auto_calc_after_id = None

        def _run() -> None:
            self._auto_calc_after_id = None
            if not widget_is_alive(self):
                return
            if hasattr(self, "_is_active_page") and not self._is_active_page():
                return
            state.auto_calculate()
            if callback:
                callback()

        self._auto_calc_after_id = self.schedule_after(
            delay_ms,
            safe_widget_callback(self, _run),
        )
