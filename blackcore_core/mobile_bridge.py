"""Authenticated, read-only BLACKCORE mobile bridge and same-origin PWA."""
import argparse
import hmac
import io
import json
import mimetypes
import os
import platform
import shutil
import ssl
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import psutil
except ImportError:
    psutil = None

WEB_ROOT = Path(__file__).resolve().parent.parent / "mobile_web"
WEB_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/style.css": "style.css",
    "/app.js": "app.js",
    "/manifest.webmanifest": "manifest.webmanifest",
    "/sw.js": "sw.js",
}
STARTED_AT = time.time()
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def collect_status():
    """Return a privacy-conscious, read-only snapshot; optional metrics degrade gracefully."""
    now = time.time()
    data = {
        "product": "BLACKCORE ULTIMATE",
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "timestamp": int(now),
        "bridge_uptime_seconds": max(0, int(now - STARTED_AT)),
        "cpu_count": os.cpu_count(),
        "capabilities": {
            "telemetry": True,
            "remote_control": False,
            "arbitrary_commands": False,
            "screen_streaming": False,
            "file_access": False,
            "plugin_execution": False,
        },
    }
    try:
        disk = shutil.disk_usage(Path.home())
        data["disk"] = {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent_used": round(disk.used * 100 / disk.total, 1) if disk.total else 0,
        }
    except OSError:
        data["disk"] = None

    if psutil is None:
        data.update(cpu_percent=None, memory=None, network=None, uptime_seconds=None,
                    process_count=None, battery=None)
        data["note"] = "Install psutil for extended CPU, RAM, network and uptime metrics."
        return data

    try:
        memory = psutil.virtual_memory()
        data["cpu_percent"] = psutil.cpu_percent(interval=0.05)
        data["memory"] = {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_bytes": memory.used,
            "percent_used": memory.percent,
        }
    except (OSError, RuntimeError, AttributeError):
        data.update(cpu_percent=None, memory=None)

    try:
        counters = psutil.net_io_counters()
        data["network"] = {
            "bytes_sent": counters.bytes_sent,
            "bytes_received": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_received": counters.packets_recv,
        }
    except (OSError, RuntimeError, AttributeError):
        data["network"] = None

    try:
        data["uptime_seconds"] = max(0, int(now - psutil.boot_time()))
    except (OSError, RuntimeError, AttributeError):
        data["uptime_seconds"] = None

    try:
        data["process_count"] = len(psutil.pids())
    except (OSError, RuntimeError, AttributeError):
        data["process_count"] = None

    try:
        battery = psutil.sensors_battery()
        data["battery"] = None if battery is None else {
            "percent": battery.percent,
            "plugged": battery.power_plugged,
        }
    except (OSError, RuntimeError, AttributeError):
        data["battery"] = None
    return data


def make_handler(token, remote_control=False):
    action_lock = __import__("threading").Lock()
    last_action = [0.0]
    allowed_keys = {"enter", "esc", "tab", "space", "backspace", "delete", "up", "down", "left", "right", "home", "end", "ctrl", "alt", "shift", "ctrl+c", "ctrl+v", "ctrl+z", "ctrl+s", "alt+tab"}
    class Handler(BaseHTTPRequestHandler):
        server_version = "BLACKCORE-MobileBridge"
        sys_version = ""

        def log_message(self, fmt, *args):
            # Avoid logging request headers/tokens; only method/path/status are emitted.
            print("[blackcore-mobile] " + (fmt % args))

        def send_bytes(self, code, body, content_type, no_store=False):
            try:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Cache-Control", "no-store" if no_store else "no-cache")
                if content_type.startswith("text/html"):
                    self.send_header("Content-Security-Policy",
                        "default-src 'self'; script-src 'self'; style-src 'self'; "
                        "connect-src 'self'; img-src 'self' data:; manifest-src 'self'; "
                        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def send_json(self, code, payload):
            body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            self.send_bytes(code, body, "application/json; charset=utf-8", no_store=True)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in WEB_FILES:
                target = WEB_ROOT / WEB_FILES[path]
                try:
                    body = target.read_bytes()
                except OSError:
                    self.send_json(503, {"error": "mobile_panel_unavailable"})
                    return
                mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if target.suffix == ".webmanifest":
                    mime = "application/manifest+json"
                self.send_bytes(200, body, mime + ("; charset=utf-8" if mime.startswith(("text/", "application/javascript")) else ""))
                return
            if path == "/api/screen.jpg":
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], token):
                    self.send_json(401, {"error": "unauthorized"})
                    return
                if not remote_control or pyautogui is None:
                    self.send_json(403, {"error": "remote_control_disabled"})
                    return
                try:
                    image = pyautogui.screenshot()
                    image.thumbnail((1280, 720))
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=65, optimize=True)
                    self.send_bytes(200, buffer.getvalue(), "image/jpeg", no_store=True)
                except Exception:
                    self.send_json(503, {"error": "screen_capture_unavailable"})
                return
            if path == "/api/health":
                self.send_json(200, {"ok": True, "auth_required": True, "mode": "read_only"})
                return
            if path not in ("/api/status", "/api/v1/status"):
                self.send_json(404, {"error": "not_found"})
                return
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], token):
                self.send_json(401, {"error": "unauthorized"})
                return
            self.send_json(200, collect_status())

        def _read_only(self):
            self.send_json(405, {"error": "read_only_bridge", "message": "Remote actions are disabled unless explicitly enabled on the PC."})

        def do_POST(self):
            if urlparse(self.path).path != "/api/control":
                self._read_only()
                return
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], token):
                self.send_json(401, {"error": "unauthorized"})
                return
            if not remote_control or pyautogui is None:
                self.send_json(403, {"error": "remote_control_disabled"})
                return
            if self.headers.get("X-Blackcore-Confirm") != "YES":
                self.send_json(403, {"error": "explicit_confirmation_required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 2 or length > 4096:
                self.send_json(413, {"error": "invalid_request_size"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.send_json(400, {"error": "invalid_json"})
                return
            if not isinstance(payload, dict) or payload.get("action") not in {"move", "click", "type", "key"}:
                self.send_json(400, {"error": "unsupported_action"})
                return
            with action_lock:
                now = time.monotonic()
                if now - last_action[0] < 0.12:
                    self.send_json(429, {"error": "rate_limited"})
                    return
                last_action[0] = now
            try:
                action = payload["action"]
                if action in {"move", "click"}:
                    x, y = payload.get("x"), payload.get("y")
                    if type(x) is not int or type(y) is not int:
                        self.send_json(400, {"error": "coordinates_must_be_integers"})
                        return
                    width, height = pyautogui.size()
                    if not (0 <= x < width and 0 <= y < height):
                        self.send_json(400, {"error": "coordinates_out_of_bounds", "width": width, "height": height})
                        return
                    if action == "move":
                        pyautogui.moveTo(x, y, duration=0.1)
                    else:
                        button = payload.get("button", "left")
                        if button not in {"left", "right", "middle"}:
                            self.send_json(400, {"error": "invalid_mouse_button"})
                            return
                        pyautogui.click(x=x, y=y, button=button)
                elif action == "type":
                    value = payload.get("text")
                    if not isinstance(value, str) or len(value) > 300 or any(ord(c) < 32 and c not in "\n\t" for c in value):
                        self.send_json(400, {"error": "invalid_text"})
                        return
                    pyautogui.write(value, interval=0.01)
                elif action == "key":
                    key = payload.get("key")
                    if not isinstance(key, str) or key.lower() not in allowed_keys:
                        self.send_json(400, {"error": "key_not_allowlisted"})
                        return
                    pyautogui.hotkey(*key.lower().split("+")) if "+" in key else pyautogui.press(key.lower())
                self.send_json(200, {"ok": True, "action": action, "mode": "user_authorized_remote_control"})
            except Exception:
                self.send_json(503, {"error": "remote_action_failed"})

        def do_PUT(self): self._read_only()
        def do_PATCH(self): self._read_only()
        def do_DELETE(self): self._read_only()
        def do_OPTIONS(self):
            self.send_json(405, {"error": "read_only_bridge"})

    return Handler


def create_server(host, port, token, certfile=None, keyfile=None, remote_control=False):
    if len(token) < 32:
        raise ValueError("BLACKCORE_BRIDGE_TOKEN must have at least 32 characters.")
    if host not in LOOPBACK_HOSTS and not (certfile and keyfile):
        raise ValueError("Non-loopback binding requires TLS certificate and key.")
    if bool(certfile) != bool(keyfile):
        raise ValueError("Provide both TLS certificate and key.")
    if remote_control and host in LOOPBACK_HOSTS:
        raise ValueError("Remote control requires a LAN-bound host and TLS.")
    if remote_control and not (certfile and keyfile):
        raise ValueError("Remote control requires TLS.")
    if remote_control and (platform.system() != "Windows" or pyautogui is None):
        raise ValueError("Remote control requires Windows and the optional pyautogui dependency.")
    server = ThreadingHTTPServer((host, port), make_handler(token, remote_control=remote_control))
    server.daemon_threads = True
    server.timeout = 1
    if certfile:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="BLACKCORE read-only mobile bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cert", default=os.environ.get("BLACKCORE_BRIDGE_CERT"))
    parser.add_argument("--key", default=os.environ.get("BLACKCORE_BRIDGE_KEY"))
    parser.add_argument("--enable-remote-control", action="store_true",
                        help="Enable allowlisted screen/mouse/keyboard actions. Requires Windows, pyautogui and HTTPS.")
    args = parser.parse_args(argv)
    token = os.environ.get("BLACKCORE_BRIDGE_TOKEN", "")
    if len(token) < 32:
        parser.error("Set BLACKCORE_BRIDGE_TOKEN to a random secret of at least 32 characters.")
    server = create_server(args.host, args.port, token, args.cert, args.key,
                           remote_control=args.enable_remote_control)
    mode = "remote control ENABLED (allowlisted actions only)" if args.enable_remote_control else "read-only telemetry"
    print("BLACKCORE mobile panel/bridge ready: " + mode + ". Keep it on a trusted private network.")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping BLACKCORE mobile bridge.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
