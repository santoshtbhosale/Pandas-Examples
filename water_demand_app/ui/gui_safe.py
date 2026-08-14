"""Safe GUI callback wrappers — user-friendly errors and application logging."""

from __future__ import annotations

import traceback
from tkinter import messagebox
from typing import Any, Callable, Optional, TypeVar

from services.app_logging import log_exception

F = TypeVar("F", bound=Callable[..., Any])

_USER_MESSAGE = "Something went wrong. Please try again."


def safe_command(callback: F, parent: Optional[Any] = None, title: str = "Error") -> F:
    """Wrap a GUI callback so unexpected exceptions are logged and shown safely."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return callback(*args, **kwargs)
        except Exception as exc:
            log_exception(
                str(exc),
                exc=exc,
                function=getattr(callback, "__name__", "safe_command"),
            )
            win = parent
            if win is not None and hasattr(win, "winfo_toplevel"):
                win = win.winfo_toplevel()
            messagebox.showerror(title, _USER_MESSAGE, parent=win)

    wrapper.__name__ = getattr(callback, "__name__", "safe_command")
    return wrapper  # type: ignore[return-value]
