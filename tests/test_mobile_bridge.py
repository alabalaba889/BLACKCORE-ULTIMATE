import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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

    def test_panel_served_from_same_origin(self):
        server = create_server("127.0.0.1", 0, "T" * 40)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen("http://127.0.0.1:%d/" % server.server_port, timeout=3) as response:
                body = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertIn("BLACKCORE", body)
                self.assertIn("Content-Security-Policy", response.headers)
            with urlopen("http://127.0.0.1:%d/manifest.webmanifest" % server.server_port, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("manifest+json", response.headers.get("Content-Type", ""))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_status_requires_valid_bearer_token(self):
        server = create_server("127.0.0.1", 0, "S" * 40)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:%d" % server.server_port
        try:
            with self.assertRaises(HTTPError) as raised:
                urlopen(base + "/api/status", timeout=3)
            self.assertEqual(raised.exception.code, 401)
            request = Request(base + "/api/status", headers={"Authorization": "Bearer " + "S" * 40})
            with urlopen(request, timeout=3) as response:
                data = json.loads(response.read())
                self.assertEqual(response.status, 200)
                self.assertFalse(data["capabilities"]["remote_control"])
            request = Request(base + "/api/status", method="POST")
            with self.assertRaises(HTTPError) as denied:
                urlopen(request, timeout=3)
            self.assertEqual(denied.exception.code, 405)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

if __name__ == "__main__":
    unittest.main()
