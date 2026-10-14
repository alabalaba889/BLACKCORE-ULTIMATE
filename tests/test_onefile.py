import tempfile
import unittest
from pathlib import Path

import BLACKCORE_ULTIMATE_ONEFILE as app


class OneFileEditionTests(unittest.TestCase):
    def test_remote_plain_http_endpoint_is_blocked(self):
        with self.assertRaises(ValueError):
            app.safe_endpoint("http://example.com/api", "openai_compatible")

    def test_ollama_local_endpoint_is_allowed(self):
        self.assertEqual(app.safe_endpoint("http://127.0.0.1:11434/api/chat", "ollama"),
                         "http://127.0.0.1:11434/api/chat")

    def test_ollama_remote_https_is_blocked(self):
        with self.assertRaises(ValueError):
            app.safe_endpoint("https://remote.example/api", "ollama")

    def test_plugin_path_traversal_is_blocked(self):
        with self.assertRaises(ValueError):
            app.validate_plugin_manifest({
                "name": "Example", "version": "1.0.0", "entrypoint": "../run.py"
            })

    def test_plugin_is_metadata_only(self):
        result = app.validate_plugin_manifest({
            "name": "Example", "version": "1.0.0", "entrypoint": "main.py",
            "permissions": ["read_project"]
        })
        self.assertFalse(result["enabled"])
        self.assertFalse(result["execution_supported"])

    def test_diff_does_not_modify_source(self):
        original = "before\\n"
        diff = app.make_diff(original, "after\\n", "src/main.luau")
        self.assertIn("-before", diff)
        self.assertIn("+after", diff)
        self.assertEqual(original, "before\\n")

    def test_diff_rejects_traversal_name(self):
        with self.assertRaises(ValueError):
            app.make_diff("x", "y", "../../bad.lua")

    def test_roblox_scan_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "test.server.lua").write_text("event:FireServer()\\n", encoding="utf-8")
            report = app.inspect_roblox_project(tmp)
            self.assertTrue(report["read_only"])
            self.assertFalse(report["executed_code"])
            self.assertEqual(report["files_scanned"], 1)
            self.assertGreaterEqual(len(report["findings"]), 1)

    def test_backup_restore_requires_confirmation_and_valid_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "original.txt"
            source.write_text("hello blackcore", encoding="utf-8")
            record = app.create_backup(str(source), str(root / "backups"))
            destination = root / "restored.txt"
            with self.assertRaises(PermissionError):
                app.restore_backup(record["backup_path"], str(destination), record["sha256"])
            with self.assertRaises(ValueError):
                app.restore_backup(record["backup_path"], str(destination), "0" * 64, confirmed=True)
            app.restore_backup(record["backup_path"], str(destination), record["sha256"], confirmed=True)
            self.assertEqual(destination.read_text(encoding="utf-8"), "hello blackcore")

    def test_ai_rejects_missing_hosted_key_before_network(self):
        with self.assertRaisesRegex(ValueError, "BLACKCORE_AI_API_KEY"):
            app.ask_ai([{"role": "user", "content": "hello"}], {
                "BLACKCORE_AI_PROVIDER": "openai_compatible",
                "BLACKCORE_AI_ENDPOINT": "https://api.example.com/chat"
            })


if __name__ == "__main__":
    unittest.main()
