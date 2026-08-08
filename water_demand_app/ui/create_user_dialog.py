"""Create / edit user dialog for Super Admin user management."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import ROLE_ENGINEER, ROLE_LABELS, USER_ROLES, UserRecord
from services.auth_db import (
    create_user,
    list_users,
    reset_user_password,
    update_user,
    username_exists,
)


class CreateUserDialog(ctk.CTkToplevel):
    """Professional create / edit user form."""

    def __init__(
        self,
        master,
        actor_username: str,
        on_saved: Optional[Callable[[], None]] = None,
        edit_user: Optional[UserRecord] = None,
    ) -> None:
        super().__init__(master)
        self.actor_username = actor_username
        self.on_saved = on_saved
        self.edit_user = edit_user
        self._team_leader_map: Dict[str, int] = {}

        self.title("Edit User" if edit_user else "Create User")
        self.geometry("520x640")
        self.minsize(480, 600)
        self.configure(fg_color="#F5F7FA")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self._build()
        if edit_user:
            self._load_user(edit_user)
        self._on_role_changed()
        self.after(100, self.lift)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0)
        header.pack(fill="x")
        title = "Edit User" if self.edit_user else "Create User"
        ctk.CTkLabel(header, text=title, font=("Arial", 18, "bold"), text_color="white").pack(pady=14)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        self.error_label = ctk.CTkLabel(body, text="", font=("Arial", 11), text_color="#C0392B")
        self.error_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        row = 1
        self.full_name_entry = self._field(body, row, "Full Name *")
        row += 1
        self.username_entry = self._field(body, row, "Username *")
        row += 1
        self.employee_id_entry = self._field(body, row, "Employee ID *")
        row += 1

        if not self.edit_user:
            self.password_entry = self._password_field(body, row, "Password *")
            row += 1
            self.confirm_password_entry = self._password_field(body, row, "Confirm Password *")
            row += 1
        else:
            self.password_entry = None
            self.confirm_password_entry = None

        ctk.CTkLabel(body, text="Role *", font=("Arial", 12), anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(10, 4)
        )
        self.role_var = ctk.StringVar(value=ROLE_LABELS[ROLE_ENGINEER])
        self.role_menu = ctk.CTkOptionMenu(
            body,
            variable=self.role_var,
            values=[ROLE_LABELS[r] for r in USER_ROLES],
            command=lambda _v: self._on_role_changed(),
        )
        self.role_menu.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        row += 2

        self.team_entry = self._field(body, row, "Team")
        row += 1

        self.team_leader_label = ctk.CTkLabel(body, text="Team Leader", font=("Arial", 12), anchor="w")
        self.team_leader_label.grid(row=row, column=0, sticky="ew", pady=(10, 4))
        self.team_leader_var = ctk.StringVar(value="")
        leaders = self._team_leader_options()
        self.team_leader_menu = ctk.CTkOptionMenu(
            body,
            variable=self.team_leader_var,
            values=leaders or ["(No team leaders available)"],
        )
        self.team_leader_menu.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        row += 2

        ctk.CTkLabel(body, text="Status", font=("Arial", 12), anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(10, 4)
        )
        self.active_var = ctk.StringVar(value="Active")
        self.status_menu = ctk.CTkOptionMenu(
            body,
            variable=self.active_var,
            values=["Active", "Inactive"],
        )
        self.status_menu.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        row += 2

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=row, column=0, sticky="ew", pady=(16, 8))
        save_text = "Save Changes" if self.edit_user else "Create User"
        ctk.CTkButton(btn_row, text=save_text, fg_color=BRAND_ORANGE, command=self._save, width=140).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="Cancel", fg_color="#7F8C8D", command=self.destroy, width=100).pack(side="left")

    def _field(self, parent, row: int, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=("Arial", 12), anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(10, 4)
        )
        entry = ctk.CTkEntry(parent, height=36, corner_radius=8)
        entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        return entry

    def _password_field(self, parent, row: int, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=("Arial", 12), anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(10, 4)
        )
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 4))
        frame.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(frame, height=36, corner_radius=8, show="•")
        entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            frame, text="Show", width=64, height=32, command=lambda e=entry: self._toggle_password(e)
        ).grid(row=0, column=1, padx=(8, 0))
        return entry

    def _toggle_password(self, entry: ctk.CTkEntry) -> None:
        entry.configure(show="" if entry.cget("show") == "•" else "•")

    def _team_leader_options(self) -> List[str]:
        self._team_leader_map.clear()
        options: List[str] = []
        for user in list_users():
            if user.role == "team_leader" and user.is_active:
                label = f"{user.full_name} ({user.username})"
                options.append(label)
                self._team_leader_map[label] = user.user_id
        return options

    def _role_key(self) -> str:
        label = self.role_var.get()
        for key, value in ROLE_LABELS.items():
            if value == label:
                return key
        return ROLE_ENGINEER

    def _on_role_changed(self) -> None:
        show_tl = self._role_key() == ROLE_ENGINEER
        if show_tl:
            self.team_leader_label.grid()
            self.team_leader_menu.grid()
        else:
            self.team_leader_label.grid_remove()
            self.team_leader_menu.grid_remove()

    def _load_user(self, user: UserRecord) -> None:
        self.full_name_entry.insert(0, user.full_name)
        self.username_entry.insert(0, user.username)
        self.username_entry.configure(state="disabled")
        self.employee_id_entry.insert(0, user.employee_id)
        self.role_var.set(ROLE_LABELS.get(user.role, user.role))
        self.team_entry.insert(0, user.team)
        self.active_var.set("Active" if user.is_active else "Inactive")
        if user.team_leader_id:
            for label, uid in self._team_leader_map.items():
                if uid == user.team_leader_id:
                    self.team_leader_var.set(label)
                    break

    def _set_error(self, message: str) -> None:
        self.error_label.configure(text=message)

    def _save(self) -> None:
        self._set_error("")
        full_name = self.full_name_entry.get().strip()
        username = self.username_entry.get().strip().lower()
        employee_id = self.employee_id_entry.get().strip()
        team = self.team_entry.get().strip()
        role = self._role_key()
        is_active = self.active_var.get() == "Active"

        if not full_name:
            self._set_error("Full Name is required.")
            return
        if not username:
            self._set_error("Username is required.")
            return
        if not employee_id:
            self._set_error("Employee ID is required.")
            return
        if not self.edit_user:
            password = self.password_entry.get() if self.password_entry else ""
            confirm = self.confirm_password_entry.get() if self.confirm_password_entry else ""
            if not password:
                self._set_error("Password is required.")
                return
            if password != confirm:
                self._set_error("Confirm Password must match Password.")
                return
        else:
            password = ""

        if not role:
            self._set_error("Role is required.")
            return

        team_leader_id = 0
        if role == ROLE_ENGINEER:
            tl_label = self.team_leader_var.get()
            team_leader_id = self._team_leader_map.get(tl_label, 0)

        exclude_id = self.edit_user.user_id if self.edit_user else 0
        if username_exists(username, exclude_user_id=exclude_id):
            self._set_error("Username must be unique.")
            return

        try:
            if self.edit_user:
                update_user(
                    self.edit_user.user_id,
                    full_name=full_name,
                    role=role,
                    employee_id=employee_id,
                    team=team,
                    team_leader_id=team_leader_id,
                    is_active=is_active,
                )
                messagebox.showinfo("User Updated", "User updated successfully.", parent=self)
            else:
                create_user(
                    username,
                    password,
                    full_name,
                    role,
                    employee_id=employee_id,
                    team=team,
                    team_leader_id=team_leader_id,
                )
                from services.audit_service import ACTION_USER_CREATED, log_audit

                log_audit(ACTION_USER_CREATED, self.actor_username, 0, reason=f"Created {username}")
                messagebox.showinfo("User Created", "User created successfully.", parent=self)
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as exc:
            self._set_error(str(exc))


class ViewUserDialog(ctk.CTkToplevel):
    """Read-only user details."""

    def __init__(self, master, user: UserRecord) -> None:
        super().__init__(master)
        self.title("View User")
        self.geometry("420x360")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text="User Details", font=("Arial", 16, "bold"), text_color=BRAND_NAVY).pack(pady=12)
        leader_name = "—"
        if user.team_leader_id:
            leader = next((u for u in list_users(include_inactive=True) if u.user_id == user.team_leader_id), None)
            if leader:
                leader_name = f"{leader.full_name} ({leader.username})"

        details = [
            ("Full Name", user.full_name),
            ("Username", user.username),
            ("Employee ID", user.employee_id or "—"),
            ("Role", ROLE_LABELS.get(user.role, user.role)),
            ("Team", user.team or "—"),
            ("Team Leader", leader_name),
            ("Status", "Active" if user.is_active else "Inactive"),
            ("Created", (user.created_at or "")[:19].replace("T", " ")),
        ]
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=8)
        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(frame, text=label, font=("Arial", 11, "bold"), anchor="w").grid(
                row=i, column=0, sticky="w", pady=4
            )
            ctk.CTkLabel(frame, text=value, font=("Arial", 11), anchor="w").grid(
                row=i, column=1, sticky="w", padx=(12, 0), pady=4
            )
        ctk.CTkButton(self, text="Close", command=self.destroy, fg_color=BRAND_ORANGE).pack(pady=16)


class ResetPasswordDialog(ctk.CTkToplevel):
    """Reset a user's password."""

    def __init__(self, master, user: UserRecord, on_saved: Optional[Callable[[], None]] = None) -> None:
        super().__init__(master)
        self.user = user
        self.on_saved = on_saved
        self.title("Reset Password")
        self.geometry("420x280")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text=f"Reset password for {user.username}", font=("Arial", 14, "bold")).pack(pady=12)
        self.error_label = ctk.CTkLabel(self, text="", text_color="#C0392B")
        self.error_label.pack()
        self.password_entry = ctk.CTkEntry(self, width=320, show="•", placeholder_text="New password")
        self.password_entry.pack(pady=6)
        self.confirm_entry = ctk.CTkEntry(self, width=320, show="•", placeholder_text="Confirm password")
        self.confirm_entry.pack(pady=6)
        ctk.CTkButton(self, text="Reset Password", fg_color=BRAND_ORANGE, command=self._save).pack(pady=12)
        ctk.CTkButton(self, text="Cancel", fg_color="#7F8C8D", command=self.destroy).pack()

    def _save(self) -> None:
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        if not password:
            self.error_label.configure(text="Password is required.")
            return
        if password != confirm:
            self.error_label.configure(text="Confirm Password must match Password.")
            return
        reset_user_password(self.user.user_id, password)
        messagebox.showinfo("Done", "Password reset successfully.", parent=self)
        if self.on_saved:
            self.on_saved()
        self.destroy()
