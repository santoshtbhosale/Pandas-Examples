"""Safe scheduling helpers for Tk/CustomTkinter widget callbacks."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def widget_is_alive(widget: Any) -> bool:
    """Return True when a Tk widget still exists and can be accessed."""
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except (tk.TclError, AttributeError, RuntimeError, ValueError):
        return False


def cancel_after(widget: Any, job_id: Any) -> None:
    if widget is None or job_id is None:
        return
    try:
        widget.after_cancel(job_id)
    except (tk.TclError, AttributeError, RuntimeError, ValueError):
        pass


def safe_widget_callback(widget: Any, callback: Callable[[], None]) -> Callable[[], None]:
    """Wrap a no-arg callback so it never touches a destroyed widget."""

    def wrapper() -> None:
        if not widget_is_alive(widget):
            return
        callback()

    return wrapper
