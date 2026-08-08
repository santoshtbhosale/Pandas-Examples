"""Tests for project management."""

import os
import sys
import tempfile
import unittest

APP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from services.database import get_project_history, project_exists, search_projects
from services.project_service import (
    create_new_project_state,
    generate_project_id,
    load_project_state,
    persist_project_state,
)


class TestProjectService(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_generate_unique_project_id(self) -> None:
        id1 = generate_project_id(self.db_path)
        state = create_new_project_state(self.db_path)
        persist_project_state(state, self.db_path)
        id2 = generate_project_id(self.db_path)
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("WD-"))

    def test_create_and_persist_new_project(self) -> None:
        state = create_new_project_state(self.db_path)
        self.assertTrue(state.project.project_id.startswith("WD-"))
        self.assertTrue(state.project.project_no.startswith("AE-"))
        is_update = persist_project_state(state, self.db_path)
        self.assertFalse(is_update)
        self.assertTrue(project_exists(state.project.project_id, self.db_path))

    def test_update_existing_project(self) -> None:
        state = create_new_project_state(self.db_path)
        persist_project_state(state, self.db_path)
        state.project.project_name = "UPDATED NAME"
        is_update = persist_project_state(state, self.db_path)
        self.assertTrue(is_update)
        loaded = load_project_state(state.project.project_id, self.db_path)
        self.assertEqual(loaded.project.project_name, "UPDATED NAME")

    def test_search_projects(self) -> None:
        state = create_new_project_state(self.db_path)
        state.project.project_name = "Punevalle Tower"
        state.project.client_name = "Gaikwad"
        persist_project_state(state, self.db_path)
        results = search_projects("Punevalle", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        results = search_projects("Gaikwad", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        results = search_projects("nonexistent", db_path=self.db_path)
        self.assertEqual(len(results), 0)

    def test_project_history(self) -> None:
        for i in range(3):
            state = create_new_project_state(self.db_path)
            state.project.project_name = f"Project {i}"
            persist_project_state(state, self.db_path)
        history = get_project_history(10, self.db_path)
        self.assertEqual(len(history), 3)


if __name__ == "__main__":
    unittest.main()
