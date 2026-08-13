from __future__ import annotations

import customtkinter as ctk

PAGE_BG = "#F0F2F5"


class ScrollablePage(ctk.CTkScrollableFrame):
    """Full-size scrollable page shell used by every wizard screen."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", PAGE_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)
        self._resize_after_id: str | None = None
        self.bind("<Map>", self._schedule_resize, add="+")
        if master is not None:
            master.bind("<Configure>", self._on_master_configure, add="+")
        self.after_idle(self._sync_to_parent)

    def grid(self, **kwargs):
        kwargs.setdefault("sticky", "nsew")
        super().grid(**kwargs)
        self._schedule_resize()

    def pack(self, **kwargs):
        kwargs.setdefault("fill", "both")
        kwargs.setdefault("expand", True)
        super().pack(**kwargs)
        self._schedule_resize()

    def _schedule_resize(self, _event=None) -> None:
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after_idle(self._sync_to_parent)

    def _on_master_configure(self, event) -> None:
        if event.widget is self.master:
            self._schedule_resize()

    def _sync_to_parent(self) -> None:
        self._resize_after_id = None
        parent = self.master
        if parent is None:
            return
        width = parent.winfo_width()
        height = parent.winfo_height()
        if width > 20 and height > 20:
            self.configure(width=width, height=height)

    def schedule_auto_calculate(self, state, delay_ms: int = 300, callback: Optional[Callable[[], None]] = None) -> None:
        """Debounce rapid input changes before running the full calculation engine."""
        job_attr = "_auto_calc_after_id"
        existing = getattr(self, job_attr, None)
        if existing is not None:
            self.after_cancel(existing)

        def _run() -> None:
            setattr(self, job_attr, None)
            state.auto_calculate()
            if callback:
                callback()

        setattr(self, job_attr, self.after(delay_ms, _run))
