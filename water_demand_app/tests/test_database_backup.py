"""Tests for database backup service."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from services.database import init_db
from services.database_backup import backup_database, list_backups, prune_backups, restore_database


class TestDatabaseBackup(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        init_db(self.db_path)

    def test_backup_and_restore(self) -> None:
        backup_path = backup_database(self.db_path, reason="test")
        self.assertTrue(os.path.isfile(backup_path))
        backups = list_backups(self.db_path)
        self.assertGreaterEqual(len(backups), 1)
        os.remove(self.db_path)
        restore_database(backup_path, self.db_path)
        self.assertTrue(os.path.isfile(self.db_path))

    def test_prune_backups(self) -> None:
        for _ in range(3):
            backup_database(self.db_path, reason="test")
        prune_backups(2, self.db_path)
        self.assertLessEqual(len(list_backups(self.db_path)), 2)


if __name__ == "__main__":
    unittest.main()
