import tempfile
import unittest
from pathlib import Path
from blackcore_core.action_guard import ActionRequest, authorize
from blackcore_core.backups import create_backup, restore_backup
from blackcore_core.monitor import append_history, disk_stats, format_bytes, sparkline
from blackcore_core.plugins import validate_manifest

class CoreTests(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(None), "indisponível")

    def test_sparkline_handles_empty_and_missing_samples(self):
        self.assertEqual(sparkline([]), "—")
        self.assertEqual(sparkline([None, None]), "··")
        self.assertEqual(len(sparkline([1, 2, 3], width=2)), 2)

    def test_history_is_bounded_and_does_not_mutate_input(self):
        original = [1, 2]
        result = append_history(original, 3, limit=2)
        self.assertEqual(original, [1, 2])
        self.assertEqual(result, [2, 3])

    def test_disk_stats(self):
        result = disk_stats()
        self.assertGreater(result["total_bytes"], 0)
        self.assertGreaterEqual(result["used_percent"], 0)

    def test_action_requires_confirmation(self):
        request = ActionRequest("delete", "Remove file", destructive=True)
        self.assertFalse(authorize(request, lambda _: False).allowed)
        self.assertTrue(authorize(request, lambda _: True).allowed)

    def test_backup_restore_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.txt"
            source.write_text("original", encoding="utf-8")
            backup = create_backup(str(source), str(root / "backups"))
            source.write_text("changed", encoding="utf-8")
            with self.assertRaises(PermissionError):
                restore_backup(str(backup), str(source))
            restore_backup(str(backup), str(source), confirmed=True)
            self.assertEqual(source.read_text(encoding="utf-8"), "original")

    def test_plugin_manifest(self):
        valid = validate_manifest({"name":"Demo","version":"1.0","permissions":["read_metrics"],"entrypoint":"plugin.py"})
        self.assertEqual(valid["permissions"], ["read_metrics"])
        with self.assertRaises(ValueError):
            validate_manifest({"name":"Bad","version":"1","permissions":["admin_everything"],"entrypoint":"../bad.py"})

if __name__ == "__main__":
    unittest.main()
