"""BLACKCORE Workbench: optional AI chat, read-only Roblox inspection, plugins and backups."""
from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from .ai_provider import AIClient, AIProviderError
from .plugin_manager import PluginRegistry
from .performance import nvidia_gpu_status, process_snapshot
from .roblox_lab import inspect_project
from .versioned_backups import create_versioned_backup, restore_versioned_backup

BG, PANEL, GREEN, MUTED = "#080d0b", "#101a15", "#39ff88", "#8eb9a0"


class Workbench:
    """A Tkinter Toplevel. Network requests run in a worker; file scans remain read-only."""

    def __init__(self, parent, logger=None):
        self.parent = parent
        self.logger = logger or (lambda _message: None)
        self.window = tk.Toplevel(parent)
        self.window.title("BLACKCORE // AI + ROBLOX WORKBENCH")
        self.window.geometry("900x680")
        self.window.minsize(720, 520)
        self.window.configure(bg=BG)
        self.events = queue.Queue()
        self.chat_messages = []
        self.chat_busy = False
        self.registry = PluginRegistry(str(Path.home() / ".blackcore" / "plugins.json"))
        self._build()
        self.window.after(100, self._poll_events)

    def _build(self):
        heading = tk.Label(self.window, text="AI / ROBLOX / RECOVERY WORKBENCH",
                           font=("Consolas", 16, "bold"), fg=GREEN, bg=BG)
        heading.pack(anchor="w", padx=16, pady=(14, 8))
        self.tabs = ttk.Notebook(self.window)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.ai_tab = tk.Frame(self.tabs, bg=PANEL)
        self.roblox_tab = tk.Frame(self.tabs, bg=PANEL)
        self.recovery_tab = tk.Frame(self.tabs, bg=PANEL)
        self.performance_tab = tk.Frame(self.tabs, bg=PANEL)
        self.tabs.add(self.ai_tab, text="IA")
        self.tabs.add(self.roblox_tab, text="Roblox Studio Lab")
        self.tabs.add(self.recovery_tab, text="Plugins e backups")
        self.tabs.add(self.performance_tab, text="Desempenho")
        self._build_ai()
        self._build_roblox()
        self._build_recovery()
        self._build_performance()

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=("Consolas", 9)).pack(
            anchor="w", padx=12, pady=(8, 3))

    def _build_ai(self):
        self._label(self.ai_tab, "Chat de texto. A IA não executa comandos nem altera arquivos.")
        self.chat_view = tk.Text(self.ai_tab, bg="#050806", fg=GREEN, insertbackground=GREEN,
                                 font=("Consolas", 10), wrap="word", state="disabled")
        self.chat_view.pack(fill="both", expand=True, padx=12, pady=6)
        self.prompt = tk.Text(self.ai_tab, height=4, bg="#07100b", fg=GREEN,
                              insertbackground=GREEN, font=("Consolas", 10), wrap="word")
        self.prompt.pack(fill="x", padx=12, pady=6)
        row = tk.Frame(self.ai_tab, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(0, 10))
        self.ai_status = tk.StringVar(value="Provedor configurado por variáveis de ambiente.")
        tk.Label(row, textvariable=self.ai_status, bg=PANEL, fg=MUTED).pack(side="left")
        tk.Button(row, text="ENVIAR", command=self.send_chat, bg="#153c28", fg=GREEN,
                  relief="flat", padx=18, pady=7).pack(side="right")

    def _chat_append(self, role, text):
        self.chat_view.configure(state="normal")
        self.chat_view.insert("end", f"{role}: {text}\n\n")
        self.chat_view.see("end")
        self.chat_view.configure(state="disabled")

    def send_chat(self):
        if self.chat_busy:
            return
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            return
        if len(prompt) > 20000:
            messagebox.showerror("BLACKCORE", "A mensagem ultrapassa 20.000 caracteres.")
            return
        self.prompt.delete("1.0", "end")
        self.chat_messages.append({"role": "user", "content": prompt})
        self._chat_append("VOCÊ", prompt)
        self.chat_busy = True
        self.ai_status.set("Conectando à IA…")
        self._chat_append("BLACKCORE", "Pedido enviado. Aguarde a resposta.")
        def worker():
            try:
                client = AIClient()
                # Keep a bounded recent context, but always include the latest user prompt.
                answer = client.chat(self.chat_messages[-20:])
                self.events.put(("ai_ok", answer))
            except (ValueError, AIProviderError) as exc:
                self.events.put(("ai_error", str(exc)))
            except Exception:
                self.events.put(("ai_error", "Falha inesperada no provedor; detalhes foram ocultados."))
        threading.Thread(target=worker, daemon=True).start()

    def _build_roblox(self):
        self._label(self.roblox_tab, "Inspeção somente leitura de scripts .lua/.luau; nenhum script é executado.")
        row = tk.Frame(self.roblox_tab, bg=PANEL)
        row.pack(fill="x", padx=12, pady=8)
        self.project_path = tk.StringVar()
        tk.Entry(row, textvariable=self.project_path, bg="#07100b", fg=GREEN,
                 insertbackground=GREEN).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(row, text="ESCOLHER PASTA", command=self.choose_project,
                  bg="#153c28", fg=GREEN, relief="flat").pack(side="right")
        tk.Button(self.roblox_tab, text="ANALISAR PROJETO (SOMENTE LEITURA)",
                  command=self.scan_project, bg="#153c28", fg=GREEN, relief="flat",
                  padx=12, pady=8).pack(anchor="w", padx=12, pady=4)
        self.roblox_report = tk.Text(self.roblox_tab, bg="#050806", fg=GREEN,
                                     font=("Consolas", 9), wrap="word", state="disabled")
        self.roblox_report.pack(fill="both", expand=True, padx=12, pady=8)

    def choose_project(self):
        selected = filedialog.askdirectory(parent=self.window, title="Escolha a pasta do projeto Roblox")
        if selected:
            self.project_path.set(selected)

    def scan_project(self):
        root = self.project_path.get().strip()
        if not root:
            messagebox.showinfo("BLACKCORE", "Escolha primeiro a pasta do projeto.")
            return
        try:
            report = inspect_project(root)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Roblox Studio Lab", str(exc))
            return
        lines = [f"Pasta: {report['root']}", f"Arquivos analisados: {report['files_scanned']}",
                 f"Somente leitura: {report['read_only']}", f"Código executado: {report['executed_code']}",
                 f"Ocorrências: {len(report['findings'])}", ""]
        for item in report["findings"][:1000]:
            lines.append(f"[{item['severity'].upper()}] {item['code']} — {item['file']}:{item['line']}")
            lines.append(f"  {item['message']}")
        if report["skipped"]:
            lines.extend(["", "Arquivos ignorados:"] + report["skipped"][:100])
        if not report["findings"]:
            lines.append("Nenhuma ocorrência das regras heurísticas atuais. Isto não garante ausência de bugs.")
        self.roblox_report.configure(state="normal")
        self.roblox_report.delete("1.0", "end")
        self.roblox_report.insert("end", "\n".join(lines))
        self.roblox_report.configure(state="disabled")
        self.logger(f"Roblox Lab: {report['files_scanned']} arquivo(s) analisado(s), somente leitura.")

    def _build_recovery(self):
        self._label(self.recovery_tab, "Backups de arquivos e cadastro de plugins. Plugins não são executados.")
        row = tk.Frame(self.recovery_tab, bg=PANEL)
        row.pack(fill="x", padx=12, pady=6)
        tk.Button(row, text="CRIAR BACKUP DE ARQUIVO", command=self.create_backup,
                  bg="#153c28", fg=GREEN, relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 6))
        tk.Button(row, text="RESTAURAR BACKUP", command=self.restore_backup,
                  bg="#3a1b20", fg="#ff9aa5", relief="flat", padx=10, pady=8).pack(side="left")
        tk.Button(row, text="CADASTRAR PLUGIN (JSON)", command=self.register_plugin,
                  bg="#153c28", fg=GREEN, relief="flat", padx=10, pady=8).pack(side="left", padx=6)
        self.registry_view = tk.Text(self.recovery_tab, bg="#050806", fg=GREEN,
                                     font=("Consolas", 9), wrap="word", state="disabled")
        self.registry_view.pack(fill="both", expand=True, padx=12, pady=8)
        self.refresh_plugins()

    def refresh_plugins(self):
        try:
            plugins = self.registry.list_plugins()
            content = json.dumps(plugins, ensure_ascii=False, indent=2) if plugins else "Nenhum plugin cadastrado."
        except ValueError as exc:
            content = f"Registro não foi carregado para evitar sobrescrever dados inválidos: {exc}"
        self.registry_view.configure(state="normal")
        self.registry_view.delete("1.0", "end")
        self.registry_view.insert("end", content)
        self.registry_view.configure(state="disabled")

    def create_backup(self):
        source = filedialog.askopenfilename(parent=self.window, title="Escolha o arquivo para fazer backup")
        if not source:
            return
        root = filedialog.askdirectory(parent=self.window, title="Escolha a pasta de destino dos backups")
        if not root:
            return
        try:
            record = create_versioned_backup(source, root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Backup", str(exc))
            return
        messagebox.showinfo("Backup criado", f"Backup criado.\nSHA-256: {record['sha256']}\n\nGuarde a pasta do backup em local seguro.")
        self.logger(f"Backup criado para {Path(source).name}.")

    def restore_backup(self):
        backup = filedialog.askopenfilename(parent=self.window, title="Escolha um arquivo .backup",
                                             filetypes=[("BLACKCORE backups", "*.backup"), ("Todos os arquivos", "*.*")])
        if not backup:
            return
        metadata_path = str(Path(backup).with_suffix(".json"))
        try:
            metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
            expected = metadata["sha256"]
            if Path(backup).resolve() != Path(metadata["backup_path"]).resolve():
                raise ValueError("O metadado não corresponde ao arquivo de backup selecionado.")
        except (OSError, KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
            messagebox.showerror("Restauração", f"Metadados do backup inválidos: {exc}")
            return
        destination = filedialog.asksaveasfilename(parent=self.window, title="Escolha o destino da restauração",
                                                    initialfile=metadata.get("source_name", "restored-file"))
        if not destination:
            return
        if not messagebox.askyesno("Confirmar restauração",
                                  f"O arquivo de destino será substituído:\n{destination}\n\nO hash será verificado antes. Continuar?"):
            return
        try:
            restore_versioned_backup(backup, destination, expected, confirmed=True)
        except (OSError, ValueError, PermissionError) as exc:
            messagebox.showerror("Restauração", str(exc))
            return
        messagebox.showinfo("Restauração", "Arquivo restaurado após verificação do SHA-256.")
        self.logger(f"Backup restaurado para {destination}.")

    def register_plugin(self):
        filename = filedialog.askopenfilename(parent=self.window, title="Escolha um manifesto JSON",
                                              filetypes=[("JSON", "*.json")])
        if not filename:
            return
        try:
            manifest = json.loads(Path(filename).read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("O manifesto deve ser um objeto JSON.")
            requested = manifest.get("permissions", [])
            if not isinstance(requested, list):
                raise ValueError("permissions deve ser uma lista.")
            answer = messagebox.askyesno(
                "Aprovar plugin",
                "Cadastro de metadados apenas; nenhum código será executado.\n"
                f"Plugin: {manifest.get('name', '(sem nome)')}\n"
                f"Permissões solicitadas: {', '.join(map(str, requested)) or 'nenhuma'}\n\n"
                "Cadastrar com zero permissões concedidas?"
            )
            if not answer:
                return
            self.registry.register(manifest, approved_permissions=[], user_approved=True)
        except (OSError, json.JSONDecodeError, ValueError, PermissionError) as exc:
            messagebox.showerror("Plugin", str(exc))
            return
        self.refresh_plugins()
        self.logger("Manifesto de plugin cadastrado sem executar código.")
        messagebox.showinfo("Plugin", "Plugin cadastrado desativado, sem permissões concedidas e sem execução.")

    def _build_performance(self):
        self._label(self.performance_tab, "Leitura pontual. Métricas dependem de permissões, hardware e drivers; nenhum processo é encerrado.")
        tk.Button(self.performance_tab, text="ATUALIZAR MÉTRICAS", command=self.refresh_performance,
                  bg="#153c28", fg=GREEN, relief="flat", padx=12, pady=8).pack(anchor="w", padx=12, pady=6)
        self.performance_view = tk.Text(self.performance_tab, bg="#050806", fg=GREEN,
                                        font=("Consolas", 10), wrap="word", state="disabled")
        self.performance_view.pack(fill="both", expand=True, padx=12, pady=8)
        self.refresh_performance()

    def refresh_performance(self):
        lines = ["MÉTRICAS DE PROCESSOS (somente leitura)"]
        try:
            result = process_snapshot(limit=12)
            if not result["available"]:
                lines.append(result["reason"])
            elif not result["processes"]:
                lines.append("Nenhum processo pôde ser listado.")
            else:
                for item in result["processes"]:
                    lines.append(f"PID {item['pid']:>6} | {item['memory_bytes'] / (1024 ** 2):>8.1f} MB | {item['name']}")
        except (OSError, ValueError) as exc:
            lines.append(f"Lista de processos indisponível: {exc}")
        lines.extend(["", "GPU NVIDIA (nvidia-smi, se instalado):"])
        try:
            gpu = nvidia_gpu_status()
            if not gpu["available"]:
                lines.append(gpu["reason"])
            else:
                for item in gpu["gpus"]:
                    lines.append(f"{item['name']} | uso {item['utilization_percent']}% | "
                                 f"VRAM {item['memory_used_mb']}/{item['memory_total_mb']} MB")
        except (OSError, ValueError) as exc:
            lines.append(f"Telemetria GPU indisponível: {exc}")
        lines.extend(["", "A leitura não encerra processos, não instala drivers e não altera configurações."])
        self.performance_view.configure(state="normal")
        self.performance_view.delete("1.0", "end")
        self.performance_view.insert("end", "\\n".join(lines))
        self.performance_view.configure(state="disabled")

    def _poll_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "ai_ok":
                    self.chat_messages.append({"role": "assistant", "content": value})
                    self._chat_append("IA", value)
                    self.ai_status.set("Resposta recebida.")
                else:
                    self._chat_append("ERRO", value)
                    self.ai_status.set("Falha na chamada da IA.")
                self.chat_busy = False
        except queue.Empty:
            pass
        if self.window.winfo_exists():
            self.window.after(100, self._poll_events)
