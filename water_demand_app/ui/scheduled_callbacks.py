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
        try:
            callback()
        except tk.TclError:
            return

    return wrapper


def safe_entry_text(entry: Any) -> str:
    if not widget_is_alive(entry):
        return ""
    try:
        return entry.get()
    except tk.TclError:
        return ""


def safe_set_entry_text(entry: Any, value: str) -> None:
    if not widget_is_alive(entry):
        return
    text = value or ""
    try:
        current = entry.get()
    except tk.TclError:
        return
    if current == text:
        return
    try:
        entry.delete(0, "end")
        if text:
            entry.insert(0, text)
    except tk.TclError:
        return


def safe_stringvar_set(var: Any, value: str, *, widget: Any = None) -> None:
    if widget is not None and not widget_is_alive(widget):
        return
    try:
        var.set(value)
    except tk.TclError:
        return
