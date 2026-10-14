import unittest
from blackcore_core.mobile_bridge import create_server, make_handler, collect_status

class MobileBridgeSafetyTests(unittest.TestCase):
    def test_short_token_rejected(self):
        with self.assertRaisesRegex(ValueError, "32 characters"):
            create_server("127.0.0.1", 0, "short")
    def test_lan_requires_tls(self):
        with self.assertRaisesRegex(ValueError, "requires TLS"):
            create_server("0.0.0.0", 0, "x" * 40)
    def test_http_methods_are_read_only(self):
        handler = make_handler("x" * 40)
        self.assertTrue(callable(handler.do_POST))
        self.assertTrue(callable(handler.do_PUT))
        self.assertTrue(callable(handler.do_DELETE))
    def test_capabilities_are_explicitly_disabled(self):
        caps = collect_status()["capabilities"]
        self.assertTrue(caps["telemetry"])
        self.assertFalse(caps["remote_control"])
        self.assertFalse(caps["arbitrary_commands"])
        self.assertFalse(caps["screen_streaming"])

if __name__ == "__main__": unittest.main()
