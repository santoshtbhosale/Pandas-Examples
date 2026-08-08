from __future__ import annotations

import os
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import ROLE_LABELS, USER_ROLES, UserSession
from services.login_service import authenticate_with_role
from services.session_service import (
    clear_remembered_username,
    load_remembered_username,
    save_remembered_username,
)

APP_VERSION = "2.0.0"
ROLE_OPTIONS = ["Select Role"] + [ROLE_LABELS[r] for r in USER_ROLES]


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
    """Professional login screen with role selection and security validation."""

    def __init__(
        self,
        master,
        on_login_success: Callable[[UserSession], None],
        on_exit: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="#E8EDF2")
        self.on_login_success = on_login_success
        self.on_exit = on_exit
        self._logo_image: Optional[ctk.CTkImage] = None
        self._loading = False
        self._pwd_visible = False
        self._build()
        remembered = load_remembered_username()
        if remembered:
            self.username_entry.insert(0, remembered)
            self.remember_var.set(True)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self, width=480, corner_radius=16, fg_color="white",
            border_width=1, border_color="#D9DEE5",
        )
        card.grid(row=0, column=0, padx=24, pady=24)
        card.grid_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=36, pady=28)

        logo_path = _logo_path()
        if logo_path:
            try:
                img = Image.open(logo_path)
                self._logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(88, 88))
                ctk.CTkLabel(content, text="", image=self._logo_image).pack(pady=(0, 10))
            except Exception:
                pass

        ctk.CTkLabel(
            content, text="PlanetCode Engineering Suite",
            font=("Arial", 18, "bold"), text_color=BRAND_NAVY,
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            content, text="Engineering Design & Project Management System",
            font=("Arial", 11), text_color="#5C6B7A",
        ).pack(pady=(0, 20))

        self._label_field(content, "Username / Employee ID")
        self.username_entry = ctk.CTkEntry(content, height=40, corner_radius=8, placeholder_text="Enter username or employee ID")
        self.username_entry.pack(fill="x", pady=(0, 12))
        self.username_entry.bind("<Return>", lambda _e: self._attempt_login())

        self._label_field(content, "Password")
        pwd_row = ctk.CTkFrame(content, fg_color="transparent")
        pwd_row.pack(fill="x", pady=(0, 12))
        pwd_row.grid_columnconfigure(0, weight=1)
        self.password_entry = ctk.CTkEntry(pwd_row, height=40, corner_radius=8, show="•", placeholder_text="Enter password")
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self.show_pwd_btn = ctk.CTkButton(
            pwd_row, text="👁", width=44, height=36, corner_radius=8,
            fg_color="#E8ECF0", text_color="#333333", hover_color="#D0D5DC",
            command=self._toggle_password,
        )
        self.show_pwd_btn.grid(row=0, column=1, padx=(8, 0))
        self.password_entry.bind("<Return>", lambda _e: self._attempt_login())

        self._label_field(content, "Role")
        self.role_var = ctk.StringVar(value="Select Role")
        self.role_menu = ctk.CTkOptionMenu(
            content, variable=self.role_var, values=ROLE_OPTIONS, height=40, corner_radius=8,
        )
        self.role_menu.pack(fill="x", pady=(0, 12))

        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(content, text="Remember Me", variable=self.remember_var, font=("Arial", 11)).pack(
            anchor="w", pady=(0, 12),
        )

        self.error_label = ctk.CTkLabel(content, text="", font=("Arial", 11), text_color="#C0392B")
        self.error_label.pack(fill="x", pady=(0, 8))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 12))
        btn_row.grid_columnconfigure((0, 1), weight=1)
        self.login_btn = ctk.CTkButton(
            btn_row, text="LOGIN", command=self._attempt_login,
            fg_color=BRAND_ORANGE, hover_color="#D06018", height=42, corner_radius=8,
            font=("Arial", 14, "bold"),
        )
        self.login_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="EXIT", command=self._exit_app,
            fg_color="#7F8C8D", hover_color="#6C7A7B", height=42, corner_radius=8,
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(content, text=f"Version {APP_VERSION}", font=("Arial", 10), text_color="#8A96A3").pack()
        self.username_entry.focus_set()

    def _label_field(self, parent, text: str) -> None:
        ctk.CTkLabel(parent, text=text, font=("Arial", 12), anchor="w").pack(fill="x", pady=(0, 6))

    def _toggle_password(self) -> None:
        self._pwd_visible = not self._pwd_visible
        self.password_entry.configure(show="" if self._pwd_visible else "•")

    def _set_loading(self, loading: bool) -> None:
        self._loading = loading
        state = "disabled" if loading else "normal"
        self.login_btn.configure(text="Logging in..." if loading else "LOGIN", state=state)
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.role_menu.configure(state=state)
        self.show_pwd_btn.configure(state=state)

    def _exit_app(self) -> None:
        if self.on_exit:
            self.on_exit()
        else:
            self.winfo_toplevel().destroy()

    def reset(self) -> None:
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
        self.role_var.set("Select Role")
        self._set_loading(False)
        if not self.remember_var.get():
            self.username_entry.delete(0, "end")
        self.username_entry.focus_set()

    def _attempt_login(self) -> None:
        if self._loading:
            return
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        role = self.role_var.get()

        if not username:
            self.error_label.configure(text="Please enter username.")
            return
        if not password:
            self.error_label.configure(text="Please enter password.")
            return
        if not role or role == "Select Role":
            self.error_label.configure(text="Please select your role.")
            return

        self.error_label.configure(text="")
        self._set_loading(True)
        self.update_idletasks()

        user, error = authenticate_with_role(username, password, role)
        self._set_loading(False)
        if user is None:
            self.error_label.configure(text=error or "Invalid username, password, or role.")
            self.password_entry.delete(0, "end")
            return

        if self.remember_var.get():
            save_remembered_username(user.username)
        else:
            clear_remembered_username()
        self.on_login_success(user)
