"""Route users to the correct post-login dashboard by role."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from models.user import UserSession
from ui.dashboard import DashboardScreen
from ui.engineer_dashboard import EngineerDashboard
from ui.super_admin_dashboard import SuperAdminDashboard
from ui.team_leader_dashboard import TeamLeaderDashboard


def create_dashboard(
    master,
    user: UserSession,
    on_new_project: Callable[[], None],
    on_open_project: Callable[[str], None],
    on_launch_water_demand: Callable[[], None],
    on_logout: Callable[[], None],
    on_assign_and_open: Callable[[str], None] | None = None,
) -> ctk.CTkFrame:
    if user.is_super_admin():
        return SuperAdminDashboard(master, user=user, on_logout=on_logout)
    if user.is_team_leader():
        return TeamLeaderDashboard(
            master,
            user=user,
            on_open_project=on_open_project,
            on_logout=on_logout,
            on_assign_and_open=on_assign_and_open or on_open_project,
        )
    if user.is_engineer():
        return EngineerDashboard(
            master,
            user=user,
            on_new_project=on_new_project,
            on_open_project=on_open_project,
            on_launch_water_demand=on_launch_water_demand,
            on_logout=on_logout,
        )
    return DashboardScreen(
        master,
        user=user,
        on_new_project=on_new_project,
        on_open_project=on_open_project,
        on_launch_water_demand=on_launch_water_demand,
        on_logout=on_logout,
    )
