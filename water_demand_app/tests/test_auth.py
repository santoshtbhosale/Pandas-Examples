"""Tests for user authentication and password hashing."""

import os
import sys
import tempfile
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from models.user import ROLE_ADMIN, ROLE_ENGINEER, ROLE_VIEWER, UserSession
from services.auth_db import (
    authenticate,
    count_active_users,
    hash_password,
    init_users_table,
    list_users,
    verify_password,
)


class TestPasswordHashing(unittest.TestCase):
    def test_hash_and_verify(self) -> None:
        salt_hex, pwd_hash = hash_password("Test@123")
        self.assertTrue(verify_password("Test@123", salt_hex, pwd_hash))
        self.assertFalse(verify_password("Wrong", salt_hex, pwd_hash))

    def test_same_password_different_salt(self) -> None:
        s1, h1 = hash_password("Admin@123")
        s2, h2 = hash_password("Admin@123")
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(h1, h2)


class TestAuthDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_seed_default_users(self) -> None:
        init_users_table(self.db_path)
        self.assertGreaterEqual(count_active_users(self.db_path), 5)
        users = list_users(self.db_path)
        roles = {u.role for u in users}
        self.assertIn(ROLE_ADMIN, roles)
        self.assertIn(ROLE_ENGINEER, roles)
        self.assertIn(ROLE_VIEWER, roles)

    def test_authenticate_admin(self) -> None:
        init_users_table(self.db_path)
        user = authenticate("admin", "Admin@123", self.db_path)
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.role, ROLE_ADMIN)
        self.assertEqual(user.username, "admin")

    def test_authenticate_engineer(self) -> None:
        init_users_table(self.db_path)
        user = authenticate("akash", "Akash@123", self.db_path)
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.role, ROLE_ENGINEER)

    def test_authenticate_invalid_password(self) -> None:
        init_users_table(self.db_path)
        self.assertIsNone(authenticate("admin", "wrong", self.db_path))

    def test_authenticate_unknown_user(self) -> None:
        init_users_table(self.db_path)
        self.assertIsNone(authenticate("nobody", "pass", self.db_path))


class TestUserSession(unittest.TestCase):
    def test_engineer_can_launch(self) -> None:
        user = UserSession(1, "akash", "Akash", ROLE_ENGINEER)
        self.assertTrue(user.can_launch_water_demand())

    def test_viewer_cannot_launch(self) -> None:
        user = UserSession(5, "omkar", "Omkar", ROLE_VIEWER)
        self.assertFalse(user.can_launch_water_demand())

    def test_admin_can_launch(self) -> None:
        user = UserSession(1, "admin", "Admin", ROLE_ADMIN)
        self.assertTrue(user.can_launch_water_demand())


if __name__ == "__main__":
    unittest.main()
