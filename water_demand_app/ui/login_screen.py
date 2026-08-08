from __future__ import annotations

import os
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.auth_db import authenticate

APP_VERSION = "2.0.0"


def _logo_path() -> Optional[str]:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for candidate in (
        os.path.join(base, "assets", "logo.png"),
        os.path.join(os.path.dirname(base), "logo.png"),
    ):
        if os.path.exists(candidate):
            return candidate
    return None


class LoginScreen(ctk.CTkFrame):
    """Modern corporate login screen for PlanetCode Engineering Suite."""

    def __init__(self, master, on_login_success: Callable[[UserSession], None]) -> None:
        super().__init__(master, fg_color="#E8EDF2")
        self.on_login_success = on_login_success
        self._logo_image: Optional[ctk.CTkImage] = None
        self._loading = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self, width=460, corner_radius=16, fg_color="white", border_width=1, border_color="#D9DEE5")
        card.grid(row=0, column=0, padx=24, pady=24)
        card.grid_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=32)

        logo_path = _logo_path()
        if logo_path:
            try:
                img = Image.open(logo_path)
                self._logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(96, 96))
                ctk.CTkLabel(content, text="", image=self._logo_image).pack(pady=(0, 12))
            except Exception:
                pass

        ctk.CTkLabel(
            content,
            text="PLANETCODE ENGINEERING SUITE",
            font=("Arial", 18, "bold"),
            text_color=BRAND_NAVY,
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            content,
            text="Engineering Software",
            font=("Arial", 12),
            text_color="#5C6B7A",
        ).pack(pady=(0, 24))

        ctk.CTkLabel(content, text="Username / Employee ID", font=("Arial", 12), anchor="w").pack(fill="x", pady=(0, 6))
        self.username_entry = ctk.CTkEntry(
            content, height=40, corner_radius=8, placeholder_text="Enter username or employee ID"
        )
        self.username_entry.pack(fill="x", pady=(0, 14))
        self.username_entry.bind("<Return>", lambda _e: self._attempt_login())

        ctk.CTkLabel(content, text="Password", font=("Arial", 12), anchor="w").pack(fill="x", pady=(0, 6))
        pwd_row = ctk.CTkFrame(content, fg_color="transparent")
        pwd_row.pack(fill="x", pady=(0, 10))
        pwd_row.grid_columnconfigure(0, weight=1)
        self.password_entry = ctk.CTkEntry(pwd_row, height=40, corner_radius=8, show="•", placeholder_text="Enter password")
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self._pwd_visible = False
        self.show_pwd_btn = ctk.CTkButton(
            pwd_row, text="Show", width=72, height=36, corner_radius=8, command=self._toggle_password
        )
        self.show_pwd_btn.grid(row=0, column=1, padx=(8, 0))
        self.password_entry.bind("<Return>", lambda _e: self._attempt_login())

        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(content, text="Remember Me", variable=self.remember_var, font=("Arial", 11)).pack(
            anchor="w", pady=(4, 12)
        )

        self.error_label = ctk.CTkLabel(content, text="", font=("Arial", 11), text_color="#C0392B")
        self.error_label.pack(fill="x", pady=(0, 8))

        self.login_btn = ctk.CTkButton(
            content,
            text="LOGIN",
            command=self._attempt_login,
            fg_color=BRAND_ORANGE,
            hover_color="#D06018",
            height=42,
            corner_radius=8,
            font=("Arial", 14, "bold"),
        )
        self.login_btn.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(
            content,
            text="Forgot Password?",
            font=("Arial", 11),
            text_color="#5C6B7A",
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            content,
            text=f"Version {APP_VERSION}",
            font=("Arial", 10),
            text_color="#8A96A3",
        ).pack()

        self.username_entry.focus_set()

    def _toggle_password(self) -> None:
        self._pwd_visible = not self._pwd_visible
        self.password_entry.configure(show="" if self._pwd_visible else "•")
        self.show_pwd_btn.configure(text="Hide" if self._pwd_visible else "Show")

    def _set_loading(self, loading: bool) -> None:
        self._loading = loading
        state = "disabled" if loading else "normal"
        self.login_btn.configure(text="Logging in..." if loading else "LOGIN", state=state)
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.show_pwd_btn.configure(state=state)

    def reset(self) -> None:
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
        self._set_loading(False)
        self.username_entry.focus_set()

    def _attempt_login(self) -> None:
        if self._loading:
            return
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username:
            self.error_label.configure(text="Please enter username.")
            return
        if not password:
            self.error_label.configure(text="Please enter password.")
            return

        self.error_label.configure(text="")
        self._set_loading(True)
        self.update_idletasks()

        user = authenticate(username, password)
        self._set_loading(False)
        if user is None:
            self.error_label.configure(text="Invalid username or password.")
            self.password_entry.delete(0, "end")
            return
        self.on_login_success(user)
