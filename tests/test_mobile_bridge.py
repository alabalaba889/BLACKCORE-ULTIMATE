import json
import threading
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from blackcore_core.mobile_bridge import create_server, collect_status


class MobileBridgeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.token = "S" * 40
        self.server = create_server("127.0.0.1", 0, self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_short_token_rejected(self):
        with self.assertRaisesRegex(ValueError, "32 characters"):
            create_server("127.0.0.1", 0, "short")

    def test_lan_requires_tls(self):
        with self.assertRaisesRegex(ValueError, "requires TLS"):
            create_server("0.0.0.0", 0, "x" * 40)

    def test_capabilities_explicitly_disable_remote_actions(self):
        caps = collect_status()["capabilities"]
        self.assertTrue(caps["telemetry"])
        for disabled in ("remote_control", "arbitrary_commands", "screen_streaming",
                         "file_access", "plugin_execution"):
            self.assertFalse(caps[disabled], disabled)

    def test_mobile_panel_and_assets_same_origin_with_strict_csp(self):
        for path, expected in (("/", "BLACKCORE"), ("/style.css", "--green"),
                               ("/app.js", "somente leitura"), ("/manifest.webmanifest", "BLACKCORE")):
            with urlopen(self.base + path, timeout=3) as response:
                body = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertIn(expected, body)
                if path == "/":
                    csp = response.headers.get("Content-Security-Policy", "")
                    self.assertIn("script-src 'self'", csp)
                    self.assertNotIn("'unsafe-inline'", csp)
                    self.assertIn("X-Frame-Options", response.headers)
                self.assertIn("X-Content-Type-Options", response.headers)

    def test_status_requires_bearer_token_and_is_read_only(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + "/api/status", timeout=3)
        self.assertEqual(raised.exception.code, 401)
        request = Request(self.base + "/api/status", headers={"Authorization": "Bearer " + self.token})
        with urlopen(request, timeout=3) as response:
            data = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertFalse(data["capabilities"]["remote_control"])
            self.assertIn("bridge_uptime_seconds", data)
            self.assertIn("cpu_count", data)
            self.assertIn("network", data)
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            request = Request(self.base + "/api/status", method=method)
            with self.assertRaises(HTTPError) as denied:
                urlopen(request, timeout=3)
            self.assertEqual(denied.exception.code, 405)

    def test_remote_control_is_disabled_by_default(self):
        request = Request(self.base + "/api/control", data=b'{"action":"key","key":"enter"}',
                          headers={"Authorization": "Bearer " + self.token,
                                   "X-Blackcore-Confirm": "YES",
                                   "Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as denied:
            urlopen(request, timeout=3)
        self.assertEqual(denied.exception.code, 403)
        request = Request(self.base + "/api/screen.jpg",
                          headers={"Authorization": "Bearer " + self.token})
        with self.assertRaises(HTTPError) as denied_screen:
            urlopen(request, timeout=3)
        self.assertEqual(denied_screen.exception.code, 403)

    def test_remote_control_requires_tls_and_non_loopback(self):
        with self.assertRaisesRegex(ValueError, "LAN-bound host and TLS"):
            create_server("127.0.0.1", 0, self.token, remote_control=True)

    def test_unknown_path_does_not_serve_files(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + "/../../README.md", timeout=3)
        self.assertEqual(raised.exception.code, 404)

    def test_health_does_not_expose_sensitive_data(self):
        with urlopen(self.base + "/api/health", timeout=3) as response:
            data = json.loads(response.read())
        self.assertEqual(data, {"ok": True, "auth_required": True, "mode": "read_only"})

    def test_android_network_config_requires_tls_and_allows_user_installed_ca(self):
        root = Path(__file__).resolve().parents[1]
        config_path = root / "android" / "app" / "src" / "main" / "res" / "xml" / "network_security_config.xml"
        config = ET.parse(config_path).getroot()
        base = config.find("base-config")
        self.assertIsNotNone(base)
        self.assertEqual(base.attrib.get("cleartextTrafficPermitted"), "false")
        trusted = {item.attrib.get("src") for item in base.findall("./trust-anchors/certificates")}
        self.assertEqual(trusted, {"system", "user"})

        manifest_path = root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
        manifest = ET.parse(manifest_path).getroot()
        android_ns = "{http://schemas.android.com/apk/res/android}"
        application = manifest.find("application")
        self.assertIsNotNone(application)
        self.assertEqual(application.attrib.get(android_ns + "usesCleartextTraffic"), "false")
        self.assertEqual(application.attrib.get(android_ns + "networkSecurityConfig"), "@xml/network_security_config")


if __name__ == "__main__":
    unittest.main()
