from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.auth_db import count_active_users
from services.database import list_projects


class DashboardScreen(ctk.CTkFrame):
    """Post-login dashboard with module launcher and logout."""

    def __init__(
        self,
        master,
        user: UserSession,
        on_launch_water_demand: Callable[[], None],
        on_logout: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.on_launch_water_demand = on_launch_water_demand
        self.on_logout = on_logout
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text="AMERICAN EDGE ENGINEERS",
            font=("Arial", 16, "bold"),
            text_color=BRAND_ORANGE,
        ).grid(row=0, column=0, padx=24, pady=20, sticky="w")

        user_frame = ctk.CTkFrame(top, fg_color="transparent")
        user_frame.grid(row=0, column=1, padx=16, sticky="e")
        ctk.CTkLabel(
            user_frame,
            text=f"{self.user.full_name}  •  {self.user.role_label}",
            font=("Arial", 12),
            text_color="white",
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            user_frame,
            text="Logout",
            command=self._confirm_logout,
            fg_color="#C0392B",
            hover_color="#A93226",
            width=90,
            height=32,
        ).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=32, pady=24)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text=f"Welcome, {self.user.full_name}",
            font=("Arial", 26, "bold"),
            text_color=BRAND_NAVY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Select a module to begin your engineering workflow.",
            font=("Arial", 13),
            text_color="#666666",
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 24))

        cards = ctk.CTkFrame(body, fg_color="transparent")
        cards.grid(row=2, column=0, sticky="ew")
        cards.grid_columnconfigure((0, 1, 2), weight=1)

        self._module_card(
            cards,
            0,
            "Water Demand Calculator",
            "NBC-2026 water demand, UGT/OHT/STP sizing,\nPDF & Excel report generation.",
            "Launch Module",
            self._launch_water_demand,
            enabled=self.user.can_launch_water_demand(),
        )
        project_count = len(list_projects())
        self._stat_card(cards, 1, "Saved Projects", str(project_count), "Projects in database")
        self._stat_card(cards, 2, "Active Users", str(count_active_users()), "Registered accounts")

        if not self.user.can_launch_water_demand():
            ctk.CTkLabel(
                body,
                text="Your account has Viewer access. Contact an administrator for module access.",
                font=("Arial", 12),
                text_color="#C0392B",
            ).grid(row=3, column=0, sticky="w", pady=(20, 0))

    def _module_card(
        self,
        parent,
        column: int,
        title: str,
        description: str,
        button_text: str,
        command: Callable[[], None],
        enabled: bool = True,
    ) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="white", border_width=1, border_color="#DDDDDD")
        card.grid(row=0, column=column, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Arial", 16, "bold"), text_color=BRAND_NAVY).pack(
            anchor="w", padx=20, pady=(20, 8)
        )
        ctk.CTkLabel(card, text=description, font=("Arial", 12), text_color="#555555", justify="left").pack(
            anchor="w", padx=20, pady=(0, 16)
        )
        ctk.CTkButton(
            card,
            text=button_text,
            command=command,
            fg_color=BRAND_ORANGE if enabled else "#AAAAAA",
            hover_color="#D06018" if enabled else "#AAAAAA",
            state="normal" if enabled else "disabled",
            height=36,
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def _stat_card(self, parent, column: int, title: str, value: str, subtitle: str) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="white", border_width=1, border_color="#DDDDDD")
        card.grid(row=0, column=column, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"), text_color=BRAND_NAVY).pack(
            anchor="w", padx=20, pady=(20, 8)
        )
        ctk.CTkLabel(card, text=value, font=("Arial", 32, "bold"), text_color=BRAND_ORANGE).pack(
            anchor="w", padx=20, pady=(0, 4)
        )
        ctk.CTkLabel(card, text=subtitle, font=("Arial", 11), text_color="#888888").pack(
            anchor="w", padx=20, pady=(0, 20)
        )

    def _launch_water_demand(self) -> None:
        if not self.user.can_launch_water_demand():
            messagebox.showwarning("Access Denied", "Your role does not have permission to launch this module.")
            return
        self.on_launch_water_demand()

    def _confirm_logout(self) -> None:
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.on_logout()

    def refresh_stats(self) -> None:
        """Rebuild dashboard to refresh project/user counts."""
        for child in self.winfo_children():
            child.destroy()
        self._build()
