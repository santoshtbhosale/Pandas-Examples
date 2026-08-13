"""Safe GUI callback wrappers — show errors instead of crashing the application."""

from __future__ import annotations

import traceback
from tkinter import messagebox
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def safe_command(callback: F, parent: Optional[Any] = None, title: str = "Error") -> F:
    """Wrap a GUI callback so unexpected exceptions are shown and logged."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return callback(*args, **kwargs)
        except Exception as exc:
            traceback.print_exc()
            win = parent
            if win is not None and hasattr(win, "winfo_toplevel"):
                win = win.winfo_toplevel()
            messagebox.showerror(title, f"An unexpected error occurred:\n{exc}", parent=win)

    wrapper.__name__ = getattr(callback, "__name__", "safe_command")
    return wrapper  # type: ignore[return-value]
