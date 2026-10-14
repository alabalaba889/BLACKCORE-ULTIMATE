import tempfile
import unittest
from pathlib import Path
from blackcore_core.ai_provider import AIClient, _messages_for_request
from blackcore_core.roblox_lab import inspect_project, preview_patch

class AIAndRobloxLabTests(unittest.TestCase):
    def test_ai_messages_reject_invalid_role(self):
        with self.assertRaises(ValueError):
            _messages_for_request([{"role": "tool", "content": "do something"}])

    def test_ai_messages_reject_oversized_content(self):
        with self.assertRaises(ValueError):
            _messages_for_request([{"role": "user", "content": "x" * 20001}])

    def test_hosted_provider_requires_key(self):
        with self.assertRaises(ValueError):
            AIClient({"BLACKCORE_AI_PROVIDER": "openai_compatible"})

    def test_remote_plain_http_is_blocked(self):
        with self.assertRaises(ValueError):
            AIClient({"BLACKCORE_AI_PROVIDER": "openai_compatible",
                      "BLACKCORE_AI_API_KEY": "test-only",
                      "BLACKCORE_AI_ENDPOINT": "http://example.com/api"})

    def test_luau_inspection_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "Main.server.luau"
            script.write_text("local x = wait(1)\nremote:FireServer(value)\n", encoding="utf-8")
            report = inspect_project(temp)
            self.assertTrue(report["read_only"])
            self.assertFalse(report["executed_code"])
            self.assertEqual(report["files_scanned"], 1)
            self.assertIn("BC001", [item["code"] for item in report["findings"]])
            self.assertIn("BC003", [item["code"] for item in report["findings"]])
            self.assertTrue(script.exists())

    def test_patch_preview_does_not_change_source(self):
        original = "local x = 1\n"
        proposed = "local x = 2\n"
        diff = preview_patch(original, proposed, filename="Module.luau")
        self.assertIn("-local x = 1", diff)
        self.assertIn("+local x = 2", diff)
        self.assertEqual(original, "local x = 1\n")

if __name__ == "__main__":
    unittest.main()
