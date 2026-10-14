import tempfile
import unittest
from pathlib import Path

from blackcore_core.plugin_manager import PluginRegistry
from blackcore_core.remote_sessions import PairingManager
from blackcore_core.versioned_backups import create_versioned_backup, restore_versioned_backup


class StageSixTests(unittest.TestCase):
    def test_plugin_requires_approval_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = PluginRegistry(str(Path(temp) / "registry.json"))
            manifest = {"name": "Safe Demo", "version": "1.0", "permissions": ["read_metrics"], "entrypoint": "main.py"}
            with self.assertRaises(PermissionError):
                registry.register(manifest)
            item = registry.register(manifest, approved_permissions=[], user_approved=True)
            self.assertFalse(item["enabled"])
            self.assertFalse(item["execution_supported"])
            with self.assertRaises(ValueError):
                registry.register(manifest, approved_permissions=["launch_apps"], user_approved=True)
            with self.assertRaises(PermissionError):
                registry.set_enabled("Safe Demo", True)
            enabled = registry.set_enabled("Safe Demo", True, user_approved=True)
            self.assertTrue(enabled["enabled"])
            self.assertFalse(enabled["execution_supported"])

    def test_versioned_backup_integrity_and_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "settings.ini"
            source.write_text("safe=1", encoding="utf-8")
            backup = create_versioned_backup(str(source), str(root / "backups"))
            source.write_text("safe=0", encoding="utf-8")
            with self.assertRaises(PermissionError):
                restore_versioned_backup(backup["backup_path"], str(source), backup["sha256"])
            restored = restore_versioned_backup(backup["backup_path"], str(source), backup["sha256"], confirmed=True)
            self.assertEqual(restored.read_text(encoding="utf-8"), "safe=1")
            Path(backup["backup_path"]).write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                restore_versioned_backup(backup["backup_path"], str(source), backup["sha256"], confirmed=True)
            self.assertEqual(source.read_text(encoding="utf-8"), "safe=1")


class StageSevenTests(unittest.TestCase):
    def test_pairing_permissions_expiry_and_revocation(self):
        now = [1000.0]
        manager = PairingManager(pairing_ttl=60, session_ttl=120, clock=lambda: now[0])
        code = manager.create_pairing_code(approved_permissions=["mouse"])
        paired = manager.pair(code, "Android principal")
        self.assertTrue(manager.authorize(paired["session_token"], "mouse_move", approved=True))
        with self.assertRaises(PermissionError):
            manager.authorize(paired["session_token"], "key_press", approved=True)
        with self.assertRaises(PermissionError):
            manager.authorize(paired["session_token"], "mouse_click")
        self.assertTrue(manager.revoke(paired["session_token"]))
        with self.assertRaises(PermissionError):
            manager.authorize(paired["session_token"], "mouse_move", approved=True)

    def test_pairing_code_is_one_time_and_rate_limited(self):
        now = [1000.0]
        manager = PairingManager(clock=lambda: now[0], max_attempts=2)
        code = manager.create_pairing_code(approved_permissions=[])
        manager.pair(code, "phone")
        with self.assertRaises(PermissionError):
            manager.pair(code, "second phone")
        with self.assertRaises(PermissionError):
            manager.pair("999999", "third phone")
        with self.assertRaises(PermissionError):
            manager.pair("888888", "fourth phone")

    def test_expired_session_is_rejected(self):
        now = [1000.0]
        manager = PairingManager(session_ttl=60, clock=lambda: now[0])
        code = manager.create_pairing_code(approved_permissions=["view_screen"])
        paired = manager.pair(code, "phone")
        now[0] += 61
        with self.assertRaises(PermissionError):
            manager.authorize(paired["session_token"], "screen_snapshot", approved=True)


if __name__ == "__main__":
    unittest.main()
