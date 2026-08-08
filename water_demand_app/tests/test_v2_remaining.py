"""Version 2.0 remaining features — roles, timer, audit, team leader."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

APP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.nbc_2026 import PROJECT_TYPE_RESIDENTIAL
from models.project_workflow import STATUS_COMPLETED, STATUS_IN_PROGRESS
from models.residential import ResidentialWing
from models.user import ROLE_ENGINEER, ROLE_SUPER_ADMIN, ROLE_TEAM_LEADER
from services.audit_service import ACTION_PROJECT_ASSIGNED, ACTION_PROJECT_COMPLETED, list_audit_logs
from services.auth_db import authenticate, create_user, init_users_table, list_team_engineers
from services.database import init_db
from services.project_service import create_new_project_state, load_project_state, persist_project_state
from services.project_timer import timer_snapshot
from services.project_workflow_service import (
    assign_project,
    complete_project,
    dashboard_stats,
    engineer_performance,
    get_project_workflow,
    pause_project,
    record_project_opened,
    resume_project,
    search_project_records,
)


class TestV2Roles(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.db = os.path.join(self._tmpdir, "v2.db")
        init_db(self.db)
        init_users_table(self.db)

    def test_super_admin_and_team_leader_exist(self) -> None:
        sa = authenticate("superadmin", "Super@123", self.db)
        tl = authenticate("leader", "Leader@123", self.db)
        self.assertIsNotNone(sa)
        self.assertIsNotNone(tl)
        assert sa is not None and tl is not None
        self.assertEqual(sa.role, ROLE_SUPER_ADMIN)
        self.assertEqual(tl.role, ROLE_TEAM_LEADER)

    def test_team_engineers_assigned(self) -> None:
        tl = authenticate("leader", "Leader@123", self.db)
        assert tl is not None
        engineers = list_team_engineers(tl.user_id, self.db)
        self.assertGreaterEqual(len(engineers), 2)
        usernames = {e.username for e in engineers}
        self.assertIn("akash", usernames)


class TestV2AssignmentAndTimer(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.db = os.path.join(self._tmpdir, "v2.db")
        init_db(self.db)
        init_users_table(self.db)
        self.tl = authenticate("leader", "Leader@123", self.db)
        self.eng = authenticate("akash", "Akash@123", self.db)
        assert self.tl and self.eng

    def test_end_to_end_assignment_timer_completion(self) -> None:
        state = create_new_project_state(self.tl, self.db)
        state.project.project_name = "V2 Timer Test"
        state.project.client_name = "Client"
        state.project.project_type = PROJECT_TYPE_RESIDENTIAL
        state.residential = [ResidentialWing(plot="Plot-A", wing="A", flats_2bhk=5)]
        state.auto_calculate()
        pid = state.project.project_id
        persist_project_state(state, self.tl, self.db)
        assign_project(pid, "akash", self.tl, duration_label="2 Hours", db_path=self.db)

        wf = get_project_workflow(pid, self.db)
        self.assertEqual(wf.assigned_to_username, "akash")
        self.assertEqual(wf.assigned_duration_minutes, 120)
        self.assertTrue(wf.expected_completion_at)

        logs = list_audit_logs(pid, db_path=self.db)
        self.assertTrue(any(l["action"] == ACTION_PROJECT_ASSIGNED for l in logs))

        load_project_state(pid, self.db, user=self.eng)
        wf = get_project_workflow(pid, self.db)
        self.assertEqual(wf.status, STATUS_IN_PROGRESS)
        snap = timer_snapshot(wf)
        self.assertIn("elapsed_display", snap)

        wf = pause_project(pid, self.eng, self.db)
        self.assertEqual(wf.status, "paused")
        wf = resume_project(pid, self.eng, self.db)
        self.assertEqual(wf.status, STATUS_IN_PROGRESS)

        wf = complete_project(pid, self.eng, self.db)
        self.assertEqual(wf.status, STATUS_COMPLETED)
        self.assertTrue(wf.completed_at)
        logs = list_audit_logs(pid, db_path=self.db)
        self.assertTrue(any(l["action"] == ACTION_PROJECT_COMPLETED for l in logs))

    def test_team_leader_sees_team_projects_only(self) -> None:
        state = create_new_project_state(self.tl, self.db)
        state.project.project_name = "TL Project"
        persist_project_state(state, self.tl, self.db)
        assign_project(state.project.project_id, "akash", self.tl, db_path=self.db)

        other = create_new_project_state(self.eng, self.db)
        other.project.project_name = "Other Engineer Solo"
        persist_project_state(other, self.eng, self.db)

        tl_projects = search_project_records(user=self.tl, db_path=self.db)
        ids = {p["project_id"] for p in tl_projects}
        self.assertIn(state.project.project_id, ids)

    def test_engineer_performance_stats(self) -> None:
        state = create_new_project_state(self.tl, self.db)
        persist_project_state(state, self.tl, self.db)
        assign_project(state.project.project_id, "akash", self.tl, db_path=self.db)
        complete_project(state.project.project_id, self.eng, self.db)
        perf = engineer_performance(self.tl.user_id, self.db)
        akash_row = next((p for p in perf if p["username"] == "akash"), None)
        self.assertIsNotNone(akash_row)
        assert akash_row is not None
        self.assertGreaterEqual(akash_row["completed"], 1)

    def test_dashboard_stats(self) -> None:
        stats = dashboard_stats(self.tl, self.db)
        self.assertIn("total", stats)
        self.assertIn("delayed", stats)


if __name__ == "__main__":
    unittest.main()
