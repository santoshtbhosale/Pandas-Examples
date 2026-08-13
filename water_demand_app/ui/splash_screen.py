from __future__ import annotations

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE


class SplashScreen(ctk.CTkFrame):
    """Branded splash screen shown on application startup."""

    def __init__(self, master, on_complete, duration_ms: int = 2500) -> None:
        super().__init__(master, fg_color=BRAND_NAVY)
        self.on_complete = on_complete
        self.duration_ms = duration_ms
        self._progress = 0.0
        self._build()
        self._animate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=1, column=0)

        ctk.CTkLabel(
            center,
            text="AMERICAN EDGE",
            font=("Arial", 36, "bold"),
            text_color=BRAND_ORANGE,
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            center,
            text="ENGINEERS PVT. LTD.",
            font=("Arial", 18),
            text_color="white",
        ).pack(pady=(0, 20))
        ctk.CTkLabel(
            center,
            text="Water Demand Design Software",
            font=("Arial", 15),
            text_color="#CCCCCC",
        ).pack(pady=(0, 30))

        self.progress = ctk.CTkProgressBar(center, width=320, mode="determinate")
        self.progress.pack(pady=8)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(center, text="Loading application...", font=("Arial", 11), text_color="#AAAAAA")
        self.status_label.pack(pady=(8, 0))
        ctk.CTkLabel(center, text="NBC-2026 Compliant", font=("Arial", 10, "italic"), text_color="#888888").pack(pady=(16, 0))

    def _animate(self) -> None:
        self._progress = min(1.0, self._progress + 0.04)
        self.progress.set(self._progress)
        if self._progress < 1.0:
            self.after(40, self._animate)
        else:
            self.status_label.configure(text="Ready")
            self.after(300, self.on_complete)
