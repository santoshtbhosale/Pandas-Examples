"""Modal progress dialog for long-running export operations."""

from __future__ import annotations

import threading
import traceback
from typing import Callable, Optional, TypeVar

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE

T = TypeVar("T")


def run_with_progress(
    parent,
    title: str,
    message: str,
    func: Callable[[], T],
    *,
    on_success: Optional[Callable[[T], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Optional[T]:
    """Run func in a background thread while showing a modal progress dialog."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("420x160")
    dialog.resizable(False, False)
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()

    body = ctk.CTkFrame(dialog, fg_color="white")
    body.pack(fill="both", expand=True, padx=18, pady=18)
    ctk.CTkLabel(body, text=title, font=("Arial", 15, "bold"), text_color=BRAND_NAVY).pack(anchor="w")
    ctk.CTkLabel(body, text=message, font=("Arial", 11), text_color="#555555", wraplength=380).pack(
        anchor="w", pady=(8, 12)
    )
    bar = ctk.CTkProgressBar(body, mode="indeterminate", width=360)
    bar.pack(fill="x")
    bar.start()

    result: dict = {"value": None, "error": None}

    def finish() -> None:
        if not dialog.winfo_exists():
            return
        try:
            bar.stop()
            dialog.grab_release()
            dialog.destroy()
        except Exception:
            pass
        if result["error"] is not None:
            if on_error:
                on_error(result["error"])
            else:
                from tkinter import messagebox
                messagebox.showerror(title, f"Operation failed:\n\n{result['error']}")
        elif on_success is not None:
            on_success(result["value"])

    def worker() -> None:
        try:
            result["value"] = func()
        except Exception as exc:
            result["error"] = exc
            traceback.print_exc()
        finally:
            try:
                parent.after(0, finish)
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()
    dialog.wait_window()
    return result["value"]
