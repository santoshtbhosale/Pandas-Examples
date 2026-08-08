"""Inactivity session timeout with warning dialog."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from services.audit_service import ACTION_SESSION_TIMEOUT, log_audit
from services.session_service import WARNING_BEFORE_SECONDS, get_timeout_minutes


class SessionManager:
    """Tracks user activity and triggers logout after configurable inactivity."""

    def __init__(
        self,
        root: ctk.CTk,
        get_user: Callable[[], Optional[object]],
        on_logout: Callable[[], None],
        on_continue: Optional[Callable[[], None]] = None,
    ) -> None:
        self.root = root
        self.get_user = get_user
        self.on_logout = on_logout
        self.on_continue = on_continue
        self._timeout_job: Optional[str] = None
        self._warning_job: Optional[str] = None
        self._warning_dialog: Optional[ctk.CTkToplevel] = None
        self._active = False
        self._timeout_ms = get_timeout_minutes() * 60 * 1000
        self._warning_ms = max(0, self._timeout_ms - WARNING_BEFORE_SECONDS * 1000)

    def start(self) -> None:
        self._active = True
        self._bind_activity()
        self._schedule()

    def stop(self) -> None:
        self._active = False
        self._cancel_jobs()
        self._close_warning()
        for seq in ("<Key>", "<Button>", "<Motion>"):
            try:
                self.root.unbind_all(seq)
            except Exception:
                pass

    def touch(self) -> None:
        if self._active:
            self._close_warning()
            self._schedule()

    def _bind_activity(self) -> None:
        for seq in ("<Key>", "<Button>", "<Motion>"):
            self.root.bind_all(seq, self._on_activity, add="+")

    def _on_activity(self, _event=None) -> None:
        self.touch()

    def _cancel_jobs(self) -> None:
        for job in (self._timeout_job, self._warning_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        self._timeout_job = None
        self._warning_job = None

    def _schedule(self) -> None:
        self._cancel_jobs()
        if not self._active:
            return
        if self._warning_ms > 0:
            self._warning_job = self.root.after(self._warning_ms, self._show_warning)
        self._timeout_job = self.root.after(self._timeout_ms, self._expire_session)

    def _show_warning(self) -> None:
        if not self._active or self._warning_dialog is not None:
            return
        user = self.get_user()
        if user is None:
            return
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Session Expiring")
        dialog.geometry("400x180")
        dialog.transient(self.root)
        dialog.grab_set()
        self._warning_dialog = dialog
        ctk.CTkLabel(
            dialog,
            text="Your session is about to expire.",
            font=("Arial", 14, "bold"),
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            dialog,
            text="Unsaved project data is preserved in the database.",
            font=("Arial", 11),
            text_color="#666666",
        ).pack(pady=(0, 16))
        row = ctk.CTkFrame(dialog, fg_color="transparent")
        row.pack()
        ctk.CTkButton(row, text="Continue Session", command=self._continue_session, width=140).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Logout", fg_color="#C0392B", command=self._logout_now, width=100).pack(side="left", padx=8)
        dialog.protocol("WM_DELETE_WINDOW", self._continue_session)

    def _close_warning(self) -> None:
        if self._warning_dialog is not None:
            try:
                self._warning_dialog.destroy()
            except Exception:
                pass
            self._warning_dialog = None

    def _continue_session(self) -> None:
        self._close_warning()
        if self.on_continue:
            self.on_continue()
        self.touch()

    def _logout_now(self) -> None:
        self._close_warning()
        self.on_logout()

    def _expire_session(self) -> None:
        if not self._active:
            return
        user = self.get_user()
        if user is not None:
            log_audit(
                ACTION_SESSION_TIMEOUT,
                username=getattr(user, "username", ""),
                user_id=getattr(user, "user_id", 0),
            )
        self._close_warning()
        messagebox.showinfo("Session Expired", "You have been logged out due to inactivity.", parent=self.root)
        self.on_logout()
