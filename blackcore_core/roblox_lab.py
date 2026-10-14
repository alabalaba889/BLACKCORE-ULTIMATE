"""Read-only Luau/Lua project inspection and patch previews; never executes project code."""
from __future__ import annotations
import difflib
import os
import re
from pathlib import Path

SUPPORTED_SUFFIXES = {".lua", ".luau"}
DEFAULT_MAX_FILES = 500
DEFAULT_MAX_FILE_BYTES = 1_000_000
_RULES = [
    ("BC001", "warning", re.compile(r"\bwait\s*\("), "wait() pode causar esperas imprecisas; avalie task.wait() conforme o contexto."),
    ("BC002", "warning", re.compile(r"\bloadstring\s*\("), "loadstring pode executar código dinâmico; confirme se é necessário e seguro."),
    ("BC003", "info", re.compile(r"\bFireServer\s*\("), "Confirme se o servidor valida os dados recebidos pelo RemoteEvent."),
    ("BC004", "info", re.compile(r"\bOnServerEvent\s*:\s*Connect\s*\("), "Verifique validação de tipos, permissões, distância e limites no handler do servidor."),
    ("BC005", "info", re.compile(r"\bGetAsync\s*\("), "Chamadas HTTP podem falhar; considere tratamento de erros e políticas de acesso."),
    ("BC006", "warning", re.compile(r"\bLocalPlayer\b"), "LocalPlayer só está disponível no contexto do cliente; confira onde o script roda."),
]

def inspect_project(root: str, *, max_files: int = DEFAULT_MAX_FILES, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> dict:
    """Read supported scripts and return findings; does not execute or modify files."""
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError("A pasta do projeto não existe ou não é uma pasta.")
    if max_files < 1 or max_file_bytes < 1:
        raise ValueError("Limites de inspeção precisam ser positivos.")
    findings, scanned, skipped = [], 0, []
    for current, dirs, files in os.walk(base, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(current) / d).is_symlink())
        for filename in sorted(files):
            path = Path(current) / filename
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if scanned >= max_files:
                skipped.append("Limite máximo de arquivos atingido.")
                break
            try:
                if path.is_symlink() or path.stat().st_size > max_file_bytes:
                    skipped.append(f"{path.relative_to(base)}: arquivo simbólico ou grande demais.")
                    continue
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                skipped.append(f"{path.relative_to(base)}: não foi possível ler.")
                continue
            scanned += 1
            relative = str(path.relative_to(base))
            for line_no, line in enumerate(content.splitlines(), start=1):
                for code, severity, pattern, explanation in _RULES:
                    if pattern.search(line):
                        findings.append({"code": code, "severity": severity, "file": relative, "line": line_no, "message": explanation})
    return {"root": str(base), "files_scanned": scanned, "findings": findings, "skipped": skipped, "read_only": True, "executed_code": False}

def preview_patch(original: str, proposed: str, *, filename: str = "script.luau") -> str:
    """Return a unified diff preview. This function never applies the patch."""
    if not isinstance(original, str) or not isinstance(proposed, str):
        raise TypeError("O texto original e a proposta precisam ser strings.")
    if not filename or Path(filename).is_absolute() or ".." in Path(filename).parts:
        raise ValueError("Nome de arquivo inválido para o diff.")
    return "".join(difflib.unified_diff(original.splitlines(keepends=True), proposed.splitlines(keepends=True),
                                        fromfile="a/" + filename, tofile="b/" + filename))
