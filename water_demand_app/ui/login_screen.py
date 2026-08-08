from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.auth_db import authenticate


class LoginScreen(ctk.CTkFrame):
    """Username/password login screen."""

    def __init__(self, master, on_login_success: Callable[[UserSession], None]) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.on_login_success = on_login_success
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        card = ctk.CTkFrame(self, width=420, corner_radius=12)
        card.grid(row=1, column=0, pady=20)
        card.grid_propagate(False)

        header = ctk.CTkFrame(card, fg_color=BRAND_NAVY, corner_radius=8)
        header.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkLabel(header, text="Sign In", font=("Arial", 22, "bold"), text_color="white").pack(pady=14)
        ctk.CTkLabel(
            header,
            text="American Edge Engineers",
            font=("Arial", 11),
            text_color=BRAND_ORANGE,
        ).pack(pady=(0, 10))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=8)

        ctk.CTkLabel(form, text="Username", font=("Arial", 13), anchor="w").pack(fill="x", pady=(8, 4))
        self.username_entry = ctk.CTkEntry(form, width=340, placeholder_text="Enter username")
        self.username_entry.pack(pady=(0, 8))
        self.username_entry.bind("<Return>", lambda _e: self._attempt_login())

        ctk.CTkLabel(form, text="Password", font=("Arial", 13), anchor="w").pack(fill="x", pady=(8, 4))
        self.password_entry = ctk.CTkEntry(form, width=340, show="•", placeholder_text="Enter password")
        self.password_entry.pack(pady=(0, 8))
        self.password_entry.bind("<Return>", lambda _e: self._attempt_login())

        self.error_label = ctk.CTkLabel(form, text="", font=("Arial", 11), text_color="#C0392B")
        self.error_label.pack(pady=(4, 0))

        ctk.CTkButton(
            form,
            text="Login",
            command=self._attempt_login,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            height=40,
            font=("Arial", 14, "bold"),
        ).pack(pady=16, fill="x")

        ctk.CTkLabel(
            form,
            text="Default: superadmin / Super@123  |  leader / Leader@123  |  akash / Akash@123",
            font=("Arial", 9),
            text_color="#888888",
            wraplength=340,
        ).pack(pady=(0, 16))

        self.username_entry.focus_set()

    def reset(self) -> None:
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
        self.username_entry.focus_set()

    def _attempt_login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username:
            self.error_label.configure(text="Username is required.")
            return
        if not password:
            self.error_label.configure(text="Password is required.")
            return
        user = authenticate(username, password)
        if user is None:
            self.error_label.configure(text="Invalid username or password.")
            self.password_entry.delete(0, "end")
            return
        self.error_label.configure(text="")
        self.on_login_success(user)
