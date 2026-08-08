"""Shared dashboard header with user info and profile."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.session_service import SessionContext
from ui.user_profile_dialog import UserProfileDialog


def build_dashboard_header(
    parent,
    title: str,
    user: UserSession,
    on_logout: Callable[[], None],
    session: Optional[SessionContext] = None,
) -> ctk.CTkFrame:
    top = ctk.CTkFrame(parent, fg_color=BRAND_NAVY, corner_radius=0, height=72)
    top.grid_propagate(False)
    top.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        top, text=title, font=("Arial", 16, "bold"), text_color=BRAND_ORANGE,
    ).grid(row=0, column=0, padx=24, pady=20, sticky="w")

    uf = ctk.CTkFrame(top, fg_color="transparent")
    uf.grid(row=0, column=1, sticky="e", padx=16)
    ctk.CTkLabel(
        uf,
        text=f"Logged in as: {user.full_name}\n{user.role_label}",
        font=("Arial", 11),
        text_color="white",
        justify="right",
    ).pack(side="left", padx=(0, 12))
    ctk.CTkButton(
        uf, text="Profile", width=72, height=30, fg_color="#2980B9",
        command=lambda: UserProfileDialog(parent.winfo_toplevel(), user, session),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        uf, text="Logout", command=on_logout, fg_color="#C0392B", width=90, height=30,
    ).pack(side="left")
    return top
