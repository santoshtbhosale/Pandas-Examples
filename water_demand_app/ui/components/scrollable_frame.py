from __future__ import annotations

import customtkinter as ctk


class ScrollablePage(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
