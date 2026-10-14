"""Optional, read-only performance helpers for the BLACKCORE dashboard."""
from __future__ import annotations

import subprocess
import time
from typing import Callable

from .monitor import network_counters


class NetworkRateSampler:
    """Calculate network throughput from cumulative counters without assuming a fixed timer."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._previous: tuple[float, int, int] | None = None

    def sample(self) -> dict:
        counters = network_counters()
        now = self._clock()
        if not counters["available"]:
            self._previous = None
            return {"available": False, "sent_bytes_per_sec": None,
                    "received_bytes_per_sec": None}
        sent, received = counters["bytes_sent"], counters["bytes_received"]
        previous = self._previous
        self._previous = (now, sent, received)
        if previous is None or now <= previous[0]:
            return {"available": True, "sent_bytes_per_sec": None,
                    "received_bytes_per_sec": None}
        elapsed = now - previous[0]
        # Counter resets (e.g. adapter restart) should not yield negative rates.
        sent_delta, received_delta = sent - previous[1], received - previous[2]
        if sent_delta < 0 or received_delta < 0:
            return {"available": True, "sent_bytes_per_sec": None,
                    "received_bytes_per_sec": None}
        return {"available": True, "sent_bytes_per_sec": sent_delta / elapsed,
                "received_bytes_per_sec": received_delta / elapsed}


def process_snapshot(limit: int = 8) -> dict:
    """Return a small best-effort process list when psutil is installed; never terminates processes."""
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("limit deve estar entre 1 e 50.")
    try:
        import psutil
        rows = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = proc.info
                rows.append({"pid": int(info["pid"]), "name": str(info.get("name") or "processo")[:120],
                             "memory_bytes": int(info["memory_info"].rss) if info.get("memory_info") else 0})
            except (psutil.Error, OSError, TypeError, ValueError):
                continue
        rows.sort(key=lambda row: row["memory_bytes"], reverse=True)
        return {"available": True, "processes": rows[:limit], "reason": ""}
    except (ImportError, OSError):
        return {"available": False, "processes": [],
                "reason": "Instale psutil para habilitar a lista opcional de processos."}


def nvidia_gpu_status(*, timeout: float = 1.5) -> dict:
    """Read NVIDIA telemetry via nvidia-smi if already installed; do not install or change anything."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=max(0.2, min(float(timeout), 3.0)),
            check=False, shell=False,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"available": False, "gpus": [],
                "reason": "nvidia-smi indisponível; GPU não identificada por este provedor."}
    if result.returncode != 0:
        return {"available": False, "gpus": [],
                "reason": "O provedor NVIDIA não retornou métricas válidas."}
    gpus = []
    for line in result.stdout.splitlines()[:8]:
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 4:
            continue
        try:
            gpus.append({"name": fields[0][:120], "utilization_percent": int(fields[1]),
                         "memory_used_mb": int(fields[2]), "memory_total_mb": int(fields[3])})
        except ValueError:
            continue
    return {"available": bool(gpus), "gpus": gpus,
            "reason": "" if gpus else "Nenhuma GPU NVIDIA compatível foi reportada."}
