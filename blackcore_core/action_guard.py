"""Guardrails for actions that affect the user's computer."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

@dataclass(frozen=True)
class ActionRequest:
    name: str
    description: str
    requires_confirmation: bool = True
    destructive: bool = False

@dataclass(frozen=True)
class ActionResult:
    allowed: bool
    action: str
    timestamp_utc: str
    reason: str


def authorize(request: ActionRequest, confirm: Callable[[ActionRequest], bool]) -> ActionResult:
    """Authorize only after an explicit confirmation callback approves the exact action."""
    if not request.name.strip():
        return ActionResult(False, request.name, datetime.now(timezone.utc).isoformat(), "Nome de ação vazio.")
    if not request.requires_confirmation:
        return ActionResult(True, request.name, datetime.now(timezone.utc).isoformat(), "Ação não sensível.")
    approved = bool(confirm(request))
    return ActionResult(approved, request.name, datetime.now(timezone.utc).isoformat(),
                        "Confirmada pelo usuário." if approved else "Cancelada ou não confirmada.")
