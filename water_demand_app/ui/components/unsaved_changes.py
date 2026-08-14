"""Unsaved-changes confirmation helpers."""

from __future__ import annotations

from tkinter import messagebox


def confirm_unsaved_changes(action: str) -> str:
    """
    Ask the user how to handle unsaved changes.

    Returns:
        "save" — save then proceed
        "discard" — proceed without saving
        "cancel" — do not proceed
    """
    choice = messagebox.askyesnocancel(
        "Unsaved Changes",
        (
            f"You have unsaved changes.\n\n"
            f"Save your work before you {action}?\n\n"
            "Yes — Save and continue\n"
            "No — Continue without saving\n"
            "Cancel — Stay on this page"
        ),
        icon=messagebox.WARNING,
    )
    if choice is None:
        return "cancel"
    if choice:
        return "save"
    return "discard"
