#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLACKCORE ULTIMATE — edição de arquivo único.
Python 3.10+; interface Tkinter; dependências opcionais: psutil.
Este programa privilegia operação local e consentimento explícito.
Não inicia servidor remoto, não executa saída da IA e não executa plugins.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "BLACKCORE ULTIMATE"
BG, PANEL, GREEN, MUTED = "#080d0b", "#101a15", "#39ff88", "#8eb9a0"
MAX_AI_CHARS = 20_000
MAX_AI_RESPONSE = 2_000_000
MAX_SCAN_FILES = 500
MAX_SCRIPT_BYTES = 1_000_000
PERMISSIONS = {"view_screen", "mouse", "keyboard", "launch_app", "read_project", "write_project"}
RULES = [
    ("BC001", "warning", re.compile(r"\bwait\s*\("), "wait() pode ser impreciso; avalie task.wait() no contexto."),
    ("BC002", "warning", re.compile(r"\bloadstring\s*\("), "Código dinâmico requer validação e controle rigoroso."),
    ("BC003", "info", re.compile(r"\bFireServer\s*\("), "Confirme a validação dos dados no servidor."),
    ("BC004", "info", re.compile(r"\bOnServerEvent\s*:\s*Connect\s*\("), "Verifique tipos, permissões, distância e limites no handler."),
    ("BC005", "info", re.compile(r"\bGetAsync\s*\("), "Considere falhas de rede, limites e tratamento de erros."),
    ("BC006", "warning", re.compile(r"\bLocalPlayer\b"), "LocalPlayer só existe no contexto do cliente."),
]


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_STATE_HOME")
    return Path(base).expanduser() / "BLACKCORE" if base else Path.home() / ".blackcore"


def safe_endpoint(url: str, provider: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("Endpoint de IA inválido.")
    local_http = parsed.scheme == "http" and parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}
    if not (local_http or parsed.scheme == "https"):
        raise ValueError("Use HTTP apenas para localhost ou HTTPS para serviço remoto.")
    if provider == "ollama" and not local_http:
        raise ValueError("Ollama só pode usar endpoint HTTP local.")
    return url


def ask_ai(messages: list[dict], environ=None, timeout: float = 45.0) -> str:
    env = os.environ if environ is None else environ
    provider = env.get("BLACKCORE_AI_PROVIDER", "ollama").strip().lower()
    if provider not in {"ollama", "openai_compatible"}:
        raise ValueError("BLACKCORE_AI_PROVIDER deve ser ollama ou openai_compatible.")
    endpoint = env.get("BLACKCORE_AI_ENDPOINT", "").strip()
    if not endpoint:
        endpoint = "http://127.0.0.1:11434/api/chat" if provider == "ollama" else "https://api.openai.com/v1/chat/completions"
    safe_endpoint(endpoint, provider)
    model = env.get("BLACKCORE_AI_MODEL", "").strip() or ("llama3.2" if provider == "ollama" else "gpt-4o-mini")
    if provider == "openai_compatible" and not env.get("BLACKCORE_AI_API_KEY", "").strip():
        raise ValueError("Configure BLACKCORE_AI_API_KEY no ambiente local; nunca a grave neste arquivo.")
    if not isinstance(messages, list) or not messages or len(messages) > 40:
        raise ValueError("Envie entre 1 e 40 mensagens.")
    clean = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") not in {"system", "user", "assistant"}:
            raise ValueError("Formato ou papel de mensagem inválido.")
        text = msg.get("content")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_AI_CHARS:
            raise ValueError("Mensagem vazia ou acima de 20.000 caracteres.")
        clean.append({"role": msg["role"], "content": text})
    payload = {"model": model, "messages": clean, "stream": False}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = env.get("BLACKCORE_AI_API_KEY", "").strip()
    if provider == "openai_compatible":
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=max(1, min(float(timeout), 120))) as response:
            raw = response.read(MAX_AI_RESPONSE + 1)
        if len(raw) > MAX_AI_RESPONSE:
            raise RuntimeError("Resposta da IA excedeu o limite.")
        data = json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Provedor de IA retornou HTTP {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        raise RuntimeError("Falha de conexão ou resposta inválida do provedor de IA.") from None
    try:
        answer = data["message"]["content"] if provider == "ollama" else data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Resposta da IA em formato não reconhecido.") from None
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("A IA retornou uma resposta vazia.")
    return answer.strip()


def inspect_roblox_project(root: str, max_files: int = MAX_SCAN_FILES,
                           max_file_bytes: int = MAX_SCRIPT_BYTES) -> dict:
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError("Escolha uma pasta de projeto existente.")
    if not 1 <= max_files <= 5000 or not 1 <= max_file_bytes <= 10_000_000:
        raise ValueError("Limites de inspeção inválidos.")
    findings, skipped, scanned = [], [], 0
    for current, dirs, names in os.walk(base, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.suffix.lower() not in {".lua", ".luau"}:
                continue
            if scanned >= max_files:
                skipped.append("Limite máximo de arquivos atingido.")
                return {"root": str(base), "files_scanned": scanned, "findings": findings,
                        "skipped": skipped, "read_only": True, "executed_code": False}
            try:
                if path.is_symlink() or path.stat().st_size > max_file_bytes:
                    skipped.append(f"{path.relative_to(base)}: link ou arquivo acima do limite.")
                    continue
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                skipped.append(f"{path.relative_to(base)}: não foi possível ler.")
                continue
            scanned += 1
            for line_no, line in enumerate(source.splitlines(), 1):
                for code, severity, pattern, explanation in RULES:
                    if pattern.search(line):
                        findings.append({"code": code, "severity": severity, "file": str(path.relative_to(base)),
                                         "line": line_no, "message": explanation})
    return {"root": str(base), "files_scanned": scanned, "findings": findings,
            "skipped": skipped, "read_only": True, "executed_code": False}


def make_diff(original: str, proposed: str, filename: str = "script.luau") -> str:
    name = Path(filename)
    if not isinstance(original, str) or not isinstance(proposed, str):
        raise TypeError("Os dois textos precisam ser strings.")
    if name.is_absolute() or ".." in name.parts or not filename or len(filename) > 200:
        raise ValueError("Nome de arquivo inválido.")
    return "".join(difflib.unified_diff(original.splitlines(keepends=True),
        proposed.splitlines(keepends=True), fromfile="a/" + filename, tofile="b/" + filename))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(source: str, backup_dir: str) -> dict:
    raw = Path(source).expanduser()
    if raw.is_symlink() or not raw.is_file():
        raise ValueError("Escolha um arquivo regular, não um link simbólico.")
    src, root = raw.resolve(strict=True), Path(backup_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    backup_id = f"{int(time.time())}-{uuid.uuid4().hex[:12]}"
    target = root / f"{backup_id}.backup"
    shutil.copy2(src, target)
    record = {"id": backup_id, "source_name": src.name, "backup_path": str(target),
              "sha256": sha256_file(target), "size_bytes": target.stat().st_size,
              "created_unix": int(time.time())}
    metadata = root / f"{backup_id}.json"
    temp = metadata.with_suffix(".json.tmp")
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, metadata)
    return record


def restore_backup(backup: str, destination: str, expected_sha256: str, *, confirmed: bool = False) -> str:
    if not confirmed:
        raise PermissionError("Restauração bloqueada sem confirmação explícita.")
    src_raw, dst_raw = Path(backup).expanduser(), Path(destination).expanduser()
    if src_raw.is_symlink() or dst_raw.is_symlink() or not src_raw.is_file():
        raise ValueError("Backup ou destino inválido/link simbólico.")
    src = src_raw.resolve(strict=True)
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256)) or sha256_file(src) != expected_sha256:
        raise ValueError("SHA-256 não confere; restauração cancelada.")
    dst = dst_raw.resolve()
    if dst.exists() and not dst.is_file():
        raise ValueError("Destino não é um arquivo regular.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".blackcore-restore-", dir=str(dst.parent))
    try:
        with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
            shutil.copyfileobj(inp, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_name, dst)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return str(dst)


def validate_plugin_manifest(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Manifesto precisa ser um objeto JSON.")
    name, version, entrypoint = data.get("name"), data.get("version"), data.get("entrypoint")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}", name):
        raise ValueError("Nome do plugin inválido.")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Versão precisa seguir MAJOR.MINOR.PATCH.")
    if not isinstance(entrypoint, str) or not entrypoint or Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts or "\\" in entrypoint or ":" in entrypoint:
        raise ValueError("Caminho de entrada do plugin inválido.")
    requested = data.get("permissions", [])
    if not isinstance(requested, list) or any(not isinstance(p, str) or p not in PERMISSIONS for p in requested):
        raise ValueError("Permissões do plugin inválidas.")
    return {"name": name, "version": version, "entrypoint": entrypoint,
            "permissions": sorted(set(requested)), "enabled": False, "execution_supported": False}


def metrics_snapshot() -> dict:
    result = {"platform": platform.platform(), "cpu_percent": None, "ram_percent": None,
              "disk_percent": None, "network_sent_bytes": None, "network_received_bytes": None,
              "processes": [], "gpu": [], "notes": []}
    try:
        import psutil
        result["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        result["ram_percent"] = psutil.virtual_memory().percent
        result["disk_percent"] = psutil.disk_usage(str(Path.home().anchor or "/")).percent
        counters = psutil.net_io_counters()
        result["network_sent_bytes"], result["network_received_bytes"] = counters.bytes_sent, counters.bytes_recv
        for p in sorted(psutil.process_iter(["pid", "name", "memory_info"]), key=lambda x: x.info.get("memory_info").rss if x.info.get("memory_info") else 0, reverse=True)[:12]:
            try:
                result["processes"].append({"pid": p.info["pid"], "name": (p.info.get("name") or "?")[:100],
                                            "memory_mb": round(p.info["memory_info"].rss / (1024 ** 2), 1) if p.info.get("memory_info") else 0})
            except (psutil.Error, OSError):
                continue
    except ImportError:
        result["notes"].append("Instale psutil para métricas detalhadas de CPU/RAM/rede/processos.")
    except (OSError, RuntimeError, AttributeError):
        result["notes"].append("Algumas métricas não estão disponíveis neste sistema.")
    if platform.system() == "Windows":
        try:
            proc = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=1.5, check=False, shell=False)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines()[:8]:
                    parts = [x.strip() for x in line.split(",")]
                    if len(parts) == 4:
                        result["gpu"].append({"name": parts[0][:100], "usage_percent": int(parts[1]),
                                              "vram_used_mb": int(parts[2]), "vram_total_mb": int(parts[3])})
        except (OSError, subprocess.TimeoutExpired, ValueError):
            result["notes"].append("GPU NVIDIA indisponível via nvidia-smi.")
    return result


def open_allowed_app(name: str) -> None:
    if name not in {"notepad", "calculator"}:
        raise ValueError("Aplicativo fora da lista permitida.")
    system = platform.system()
    if system == "Windows":
        command = ["notepad.exe"] if name == "notepad" else ["calc.exe"]
    elif system == "Darwin":
        command = ["open", "-a", "TextEdit" if name == "notepad" else "Calculator"]
    else:
        command = ["xdg-open", str(Path.home())] if name == "notepad" else ["xcalc"]
    subprocess.Popen(command, shell=False, close_fds=True)


def run_self_tests() -> int:
    import unittest
    class CoreTests(unittest.TestCase):
        def test_endpoint_blocks_remote_http(self):
            with self.assertRaises(ValueError):
                safe_endpoint("http://example.com/api", "openai_compatible")
        def test_endpoint_accepts_local_ollama(self):
            self.assertTrue(safe_endpoint("http://127.0.0.1:11434/api/chat", "ollama"))
        def test_plugin_rejects_traversal(self):
            with self.assertRaises(ValueError):
                validate_plugin_manifest({"name":"demo","version":"1.0.0","entrypoint":"../evil.py"})
        def test_plugin_is_not_executable(self):
            item = validate_plugin_manifest({"name":"demo","version":"1.0.0","entrypoint":"main.py"})
            self.assertFalse(item["execution_supported"])
        def test_diff_is_preview_only(self):
            self.assertIn("+new", make_diff("old\n", "new\n"))
        def test_diff_blocks_traversal_filename(self):
            with self.assertRaises(ValueError):
                make_diff("a", "b", "../evil.lua")
        def test_backup_requires_confirmation_and_checks_hash(self):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "source.txt"
                source.write_text("original", encoding="utf-8")
                record = create_backup(str(source), str(Path(tmp) / "backups"))
                destination = Path(tmp) / "destination.txt"
                with self.assertRaises(PermissionError):
                    restore_backup(record["backup_path"], str(destination), record["sha256"])
                restore_backup(record["backup_path"], str(destination), record["sha256"], confirmed=True)
                self.assertEqual(destination.read_text(encoding="utf-8"), "original")
                with self.assertRaises(ValueError):
                    restore_backup(record["backup_path"], str(destination), "0" * 64, confirmed=True)
        def test_scan_is_read_only(self):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp, "main.server.lua").write_text("RemoteEvent:FireServer()\n", encoding="utf-8")
                report = inspect_roblox_project(tmp)
                self.assertTrue(report["read_only"])
                self.assertFalse(report["executed_code"])
                self.assertEqual(report["files_scanned"], 1)
                self.assertTrue(report["findings"])
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoreTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


class BlackcoreApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BLACKCORE ULTIMATE // ONE FILE")
        self.root.geometry("1040x760")
        self.root.minsize(800, 600)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.chat = []
        self.busy = False
        self.log_path = app_data_dir() / "logs"
        self.log_path.mkdir(parents=True, exist_ok=True)
        self._build()
        self.root.after(150, self._poll)
        self.log("Aplicativo iniciado; operações remotas permanecem desativadas.")

    def log(self, message):
        try:
            with (self.log_path / "blackcore.log").open("a", encoding="utf-8") as stream:
                stream.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(message).replace("\n", " ")[:1000] + "\n")
        except OSError:
            pass

    def label(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", padx=10, pady=(8, 2))

    def button(self, parent, text, command):
        tk.Button(parent, text=text, command=command, bg="#153c28", fg=GREEN, activebackground="#20583a",
                  activeforeground="white", relief="flat", padx=10, pady=7).pack(anchor="w", padx=10, pady=4)

    def _build(self):
        top = tk.Frame(self.root, bg=BG); top.pack(fill="x", padx=16, pady=12)
        tk.Label(top, text="BLACKCORE", font=("Consolas", 25, "bold"), fg=GREEN, bg=BG).pack(side="left")
        tk.Label(top, text="ULTIMATE / SINGLE-FILE EDITION", font=("Consolas", 10), fg=MUTED, bg=BG).pack(side="left", padx=14, pady=10)
        self.tabs = ttk.Notebook(self.root); self.tabs.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.dashboard = tk.Frame(self.tabs, bg=PANEL)
        self.ai_tab = tk.Frame(self.tabs, bg=PANEL)
        self.roblox_tab = tk.Frame(self.tabs, bg=PANEL)
        self.recovery_tab = tk.Frame(self.tabs, bg=PANEL)
        self.future_tab = tk.Frame(self.tabs, bg=PANEL)
        for tab, name in [(self.dashboard,"PC"),(self.ai_tab,"IA"),(self.roblox_tab,"Roblox Studio Lab"),(self.recovery_tab,"Backups / Plugins"),(self.future_tab,"Sistemas futuros")]:
            self.tabs.add(tab, text=name)
        self._build_dashboard(); self._build_ai(); self._build_roblox(); self._build_recovery(); self._build_future()

    def _build_dashboard(self):
        self.label(self.dashboard, "Monitor de leitura; métricas dependem do hardware e do psutil opcional.")
        self.metrics = tk.Text(self.dashboard, bg="#050806", fg=GREEN, font=("Consolas", 10), state="disabled")
        self.metrics.pack(fill="both", expand=True, padx=10, pady=8)
        self.button(self.dashboard, "ATUALIZAR MÉTRICAS", self.refresh_metrics)
        row = tk.Frame(self.dashboard, bg=PANEL); row.pack(fill="x", padx=10, pady=8)
        self.button(row, "ABRIR BLOCO DE NOTAS", lambda: self.confirm_app("notepad"))
        self.button(row, "ABRIR CALCULADORA", lambda: self.confirm_app("calculator"))
        self.refresh_metrics()

    def refresh_metrics(self):
        data = metrics_snapshot()
        lines = [f"Sistema: {data['platform']}", f"CPU: {data['cpu_percent'] if data['cpu_percent'] is not None else 'indisponível'}%",
                 f"RAM: {data['ram_percent'] if data['ram_percent'] is not None else 'indisponível'}%",
                 f"Disco: {data['disk_percent'] if data['disk_percent'] is not None else 'indisponível'}%"]
        if data["network_sent_bytes"] is not None:
            lines += [f"Rede enviada acumulada: {data['network_sent_bytes']} bytes",
                      f"Rede recebida acumulada: {data['network_received_bytes']} bytes"]
        lines += ["", "Processos por memória:"]
        lines += [f"PID {p['pid']} | {p['memory_mb']} MB | {p['name']}" for p in data["processes"]] or ["Lista de processos indisponível."]
        lines += ["", "GPU NVIDIA:"]
        lines += [f"{g['name']} | {g['usage_percent']}% | VRAM {g['vram_used_mb']}/{g['vram_total_mb']} MB" for g in data["gpu"]] or ["Não detectada por nvidia-smi."]
        lines += [""] + data["notes"]
        self.metrics.configure(state="normal"); self.metrics.delete("1.0", "end")
        self.metrics.insert("end", "\n".join(lines)); self.metrics.configure(state="disabled")
        self.log("Métricas atualizadas.")

    def confirm_app(self, name):
        label = "Bloco de Notas" if name == "notepad" else "Calculadora"
        if messagebox.askyesno(APP_NAME, f"Permitir abrir {label}?"):
            try:
                open_allowed_app(name); self.log("Aplicativo permitido aberto: " + name)
            except (OSError, ValueError) as exc:
                messagebox.showerror(APP_NAME, str(exc))

    def _build_ai(self):
        self.label(self.ai_tab, "Chat de IA. Configure Ollama local ou provedor HTTPS por variáveis de ambiente.")
        self.ai_view = tk.Text(self.ai_tab, bg="#050806", fg=GREEN, wrap="word", state="disabled")
        self.ai_view.pack(fill="both", expand=True, padx=10, pady=6)
        self.ai_input = tk.Text(self.ai_tab, height=4, bg="#07100b", fg=GREEN, insertbackground=GREEN, wrap="word")
        self.ai_input.pack(fill="x", padx=10, pady=6)
        self.ai_status = tk.StringVar(value="A IA não executa comandos nem altera arquivos.")
        tk.Label(self.ai_tab, textvariable=self.ai_status, bg=PANEL, fg=MUTED).pack(anchor="w", padx=10)
        self.button(self.ai_tab, "ENVIAR MENSAGEM", self.send_ai)

    def _append_chat(self, who, text):
        self.ai_view.configure(state="normal"); self.ai_view.insert("end", f"{who}: {text}\n\n")
        self.ai_view.see("end"); self.ai_view.configure(state="disabled")

    def send_ai(self):
        if self.busy: return
        prompt = self.ai_input.get("1.0", "end").strip()
        if not prompt: return
        if len(prompt) > MAX_AI_CHARS:
            messagebox.showerror(APP_NAME, "Limite de 20.000 caracteres.")
            return
        self.ai_input.delete("1.0", "end")
        self.chat.append({"role":"user","content":prompt}); self._append_chat("VOCÊ", prompt)
        self.busy = True; self.ai_status.set("Aguardando provedor…")
        recent = self.chat[-20:]
        def worker():
            try: self.events.put(("ai_ok", ask_ai(recent)))
            except Exception as exc: self.events.put(("ai_error", str(exc)[:500]))
        threading.Thread(target=worker, daemon=True).start()

    def _build_roblox(self):
        self.label(self.roblox_tab, "Análise heurística somente leitura; scripts não são executados nem alterados.")
        row = tk.Frame(self.roblox_tab, bg=PANEL); row.pack(fill="x", padx=10, pady=8)
        self.project = tk.StringVar()
        tk.Entry(row, textvariable=self.project, bg="#07100b", fg=GREEN, insertbackground=GREEN).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="ESCOLHER", command=self.choose_project, bg="#153c28", fg=GREEN).pack(side="left", padx=5)
        self.button(self.roblox_tab, "ANALISAR PROJETO", self.scan_project)
        self.roblox_view = tk.Text(self.roblox_tab, bg="#050806", fg=GREEN, wrap="word", state="disabled")
        self.roblox_view.pack(fill="both", expand=True, padx=10, pady=8)

    def choose_project(self):
        chosen = filedialog.askdirectory(parent=self.root)
        if chosen: self.project.set(chosen)

    def scan_project(self):
        try:
            report = inspect_roblox_project(self.project.get())
            lines = [f"Pasta: {report['root']}", f"Arquivos: {report['files_scanned']}",
                     f"Somente leitura: {report['read_only']}", f"Código executado: {report['executed_code']}",
                     f"Achados: {len(report['findings'])}", ""]
            for item in report["findings"][:1000]:
                lines.append(f"[{item['severity']}] {item['code']} — {item['file']}:{item['line']}")
                lines.append("  " + item["message"])
            lines += report["skipped"]
            if not report["findings"]: lines.append("Nenhuma regra heurística acionada; isso não garante ausência de bugs.")
            self.roblox_view.configure(state="normal"); self.roblox_view.delete("1.0","end")
            self.roblox_view.insert("end","\n".join(lines)); self.roblox_view.configure(state="disabled")
            self.log(f"Roblox Lab leu {report['files_scanned']} arquivos.")
        except (OSError, ValueError) as exc: messagebox.showerror("Roblox Lab", str(exc))

    def _build_recovery(self):
        self.label(self.recovery_tab, "Backups de arquivos com SHA-256; restauração exige confirmação. Plugins ficam apenas como metadados.")
        self.button(self.recovery_tab, "CRIAR BACKUP DE ARQUIVO", self.create_backup_ui)
        self.button(self.recovery_tab, "RESTAURAR BACKUP", self.restore_backup_ui)
        self.button(self.recovery_tab, "VALIDAR MANIFESTO DE PLUGIN", self.plugin_ui)
        self.recovery_view = tk.Text(self.recovery_tab, bg="#050806", fg=GREEN, wrap="word", state="disabled")
        self.recovery_view.pack(fill="both", expand=True, padx=10, pady=8)
        self.recovery_view.configure(state="normal")
        self.recovery_view.insert("end", "Plugins nunca são importados ou executados por esta edição.")
        self.recovery_view.configure(state="disabled")

    def create_backup_ui(self):
        source = filedialog.askopenfilename(parent=self.root)
        if not source: return
        dest = filedialog.askdirectory(parent=self.root, title="Pasta para backups")
        if not dest: return
        try:
            record = create_backup(source, dest)
            messagebox.showinfo("Backup criado", f"SHA-256: {record['sha256']}\nArquivo e metadados foram criados.")
            self.log("Backup criado: " + Path(source).name)
        except (OSError, ValueError) as exc: messagebox.showerror("Backup", str(exc))

    def restore_backup_ui(self):
        backup = filedialog.askopenfilename(parent=self.root, filetypes=[("Backup", "*.backup"), ("Todos", "*.*")])
        if not backup: return
        meta_path = Path(backup).with_suffix(".json")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if Path(meta["backup_path"]).resolve() != Path(backup).resolve(): raise ValueError("Metadados não correspondem ao backup.")
            if sha256_file(backup) != meta["sha256"]: raise ValueError("O hash não confere.")
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Backup", f"Backup/metadados inválidos: {exc}"); return
        dest = filedialog.asksaveasfilename(parent=self.root, initialfile=meta.get("source_name","restored-file"))
        if not dest: return
        if not messagebox.askyesno("Confirmar", f"Restaurar para:\n{dest}\nO destino pode ser substituído. Continuar?"): return
        try:
            restore_backup(backup, dest, meta["sha256"], confirmed=True)
            messagebox.showinfo("Backup", "Restauração concluída após verificação de integridade.")
            self.log("Backup restaurado: " + Path(dest).name)
        except (OSError, ValueError, PermissionError) as exc: messagebox.showerror("Backup", str(exc))

    def plugin_ui(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            manifest = validate_plugin_manifest(json.loads(Path(path).read_text(encoding="utf-8")))
            text = json.dumps(manifest, ensure_ascii=False, indent=2)
            self.recovery_view.configure(state="normal"); self.recovery_view.delete("1.0","end")
            self.recovery_view.insert("end", text + "\n\nValidação apenas. Nenhum plugin foi instalado ou executado.")
            self.recovery_view.configure(state="disabled")
            self.log("Manifesto validado sem execução.")
        except (OSError, ValueError, json.JSONDecodeError) as exc: messagebox.showerror("Plugin", str(exc))

    def _build_future(self):
        self.label(self.future_tab, "Status real dos sistemas: não mostrar protótipo como se fosse recurso pronto.")
        rows = [
            ("Chat IA local/HTTPS", "IMPLEMENTADO; configuração por ambiente"),
            ("Monitor CPU/RAM/rede/processos", "IMPLEMENTADO PARCIAL; psutil opcional"),
            ("GPU NVIDIA", "OPCIONAL; depende de nvidia-smi"),
            ("Roblox Lab somente leitura", "IMPLEMENTADO; análise heurística"),
            ("Backup/restauração de arquivo", "IMPLEMENTADO; confirmação + SHA-256"),
            ("Plugins", "VALIDAÇÃO DE MANIFESTO; sem execução"),
            ("Controle Windows amplo", "FUTURO; precisa de catálogo e permissões por ação"),
            ("Correção automática Roblox", "FUTURO; diff, backup, aprovação e testes obrigatórios"),
            ("Sandbox real de plugins", "FUTURO; isolamento de processo e modelo de ameaças"),
            ("Aplicativo Android e streaming de tela", "FUTURO; cliente e transporte autenticado"),
            ("Controle remoto fora de casa", "FUTURO; VPN/rede privada, TLS, pareamento e revogação"),
            ("Autostart, atualização e rollback", "FUTURO; assinatura, canal seguro e recuperação"),
            ("Memória/projetos/anexos da IA", "FUTURO; armazenamento local e política de retenção"),
        ]
        for name, status in rows:
            row = tk.Frame(self.future_tab, bg=PANEL); row.pack(fill="x", padx=10, pady=3)
            tk.Label(row, text=name, bg=PANEL, fg=GREEN, anchor="w", width=37).pack(side="left", padx=6, pady=5)
            tk.Label(row, text=status, bg=PANEL, fg=MUTED, anchor="w", wraplength=430, justify="left").pack(side="left", fill="x", expand=True)
        tk.Label(self.future_tab, text="Controle remoto fica desativado até existir transporte seguro revisado. Nunca exponha uma porta de controle à internet.",
                 bg=PANEL, fg="#ffb86b", wraplength=850, justify="left").pack(anchor="w", padx=16, pady=12)

    def _poll(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                self.busy = False
                if event == "ai_ok":
                    self.chat.append({"role":"assistant","content":value})
                    self._append_chat("IA", value); self.ai_status.set("Resposta recebida; nada foi executado.")
                    self.log("Resposta de IA recebida.")
                else:
                    self._append_chat("ERRO", value); self.ai_status.set("Falha no provedor.")
                    self.log("Falha de IA: " + value)
        except queue.Empty: pass
        if self.root.winfo_exists(): self.root.after(150, self._poll)


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--self-test", action="store_true", help="Executa testes locais sem abrir a interface.")
    args = parser.parse_args()
    if args.self_test: return run_self_tests()
    root = tk.Tk()
    BlackcoreApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
