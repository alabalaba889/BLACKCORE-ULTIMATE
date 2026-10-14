"""Plugin manifest validation only; this module intentionally does not execute plugins."""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_PERMISSIONS = {"read_metrics", "read_project_files", "write_project_files", "launch_apps"}


def validate_manifest(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Manifesto precisa ser um objeto.")
    name = data.get("name")
    version = data.get("version")
    permissions = data.get("permissions", [])
    entrypoint = data.get("entrypoint", "")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Nome do plugin obrigatório.")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Versão do plugin obrigatória.")
    if not isinstance(permissions, list) or any(p not in ALLOWED_PERMISSIONS for p in permissions):
        raise ValueError("O plugin solicitou permissões desconhecidas.")
    if not isinstance(entrypoint, str) or Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts:
        raise ValueError("Caminho de entrada inválido.")
    return {"name": name.strip(), "version": version.strip(),
            "permissions": sorted(set(permissions)), "entrypoint": entrypoint}


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return validate_manifest(json.load(f))
