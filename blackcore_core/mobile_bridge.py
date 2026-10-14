"""Authenticated read-only HTTPS bridge for BLACKCORE mobile clients."""
import argparse, hmac, json, os, platform, shutil, ssl, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
try:
    import psutil
except ImportError:
    psutil = None

def collect_status():
    data = {"product":"BLACKCORE ULTIMATE","platform":platform.platform(),"timestamp":int(time.time()),
            "capabilities":{"telemetry":True,"remote_control":False,"arbitrary_commands":False,"screen_streaming":False}}
    try:
        d=shutil.disk_usage(Path.home())
        data["disk"]={"total_bytes":d.total,"used_bytes":d.used,"percent_used":round(d.used*100/d.total,1) if d.total else 0}
    except OSError: data["disk"]=None
    if psutil:
        try:
            m=psutil.virtual_memory()
            data["cpu_percent"]=psutil.cpu_percent(interval=0.05)
            data["memory"]={"total_bytes":m.total,"available_bytes":m.available,"percent_used":m.percent}
        except Exception: data.update(cpu_percent=None,memory=None)
    else: data.update(cpu_percent=None,memory=None,note="Install psutil for CPU and memory metrics.")
    return data

def make_handler(token):
    class Handler(BaseHTTPRequestHandler):
        server_version="BLACKCORE-MobileBridge"; sys_version=""
        def log_message(self, fmt, *args): print("[mobile-bridge] "+(fmt % args))
        def send_json(self, code, payload):
            body=json.dumps(payload,separators=(",",":")).encode()
            self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            path=urlparse(self.path).path
            if path=="/api/health": self.send_json(200,{"ok":True,"auth_required":True}); return
            if path not in ("/api/status","/api/v1/status"): self.send_json(404,{"error":"not_found"}); return
            auth=self.headers.get("Authorization","")
            if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:],token):
                self.send_json(401,{"error":"unauthorized"}); return
            self.send_json(200,collect_status())
        def do_POST(self): self.send_json(405,{"error":"read_only_bridge"})
        def do_PUT(self): self.send_json(405,{"error":"read_only_bridge"})
        def do_DELETE(self): self.send_json(405,{"error":"read_only_bridge"})
    return Handler

def create_server(host, port, token, certfile=None, keyfile=None):
    if len(token)<32: raise ValueError("BLACKCORE_BRIDGE_TOKEN must have at least 32 characters.")
    if host not in ("127.0.0.1","::1","localhost") and not (certfile and keyfile):
        raise ValueError("Non-loopback binding requires TLS certificate and key.")
    if bool(certfile)!=bool(keyfile): raise ValueError("Provide both TLS certificate and key.")
    server=ThreadingHTTPServer((host,port),make_handler(token)); server.daemon_threads=True
    if certfile:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=certfile,keyfile=keyfile); server.socket=context.wrap_socket(server.socket,server_side=True)
    return server

def main(argv=None):
    p=argparse.ArgumentParser(description="BLACKCORE read-only mobile bridge")
    p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8765)
    p.add_argument("--cert",default=os.environ.get("BLACKCORE_BRIDGE_CERT")); p.add_argument("--key",default=os.environ.get("BLACKCORE_BRIDGE_KEY"))
    a=p.parse_args(argv); token=os.environ.get("BLACKCORE_BRIDGE_TOKEN","")
    if len(token)<32: p.error("Set BLACKCORE_BRIDGE_TOKEN to a random secret of at least 32 characters.")
    server=create_server(a.host,a.port,token,a.cert,a.key)
    print("BLACKCORE bridge started; read-only telemetry only; remote commands are disabled.")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__": main()
