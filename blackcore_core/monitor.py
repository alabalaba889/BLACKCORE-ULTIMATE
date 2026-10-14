"""Safe, read-only system metrics using the Python standard library."""
from __future__ import annotations
import os
import shutil
import time
from typing import Optional


def disk_stats(path: str = os.path.abspath(os.sep)) -> dict:
    """Return total/used/free disk bytes for the drive containing path."""
    usage = shutil.disk_usage(path)
    return {"total_bytes": usage.total, "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": round(usage.used * 100 / usage.total, 1) if usage.total else 0.0}


def network_counters() -> dict:
    """Return cumulative network byte counters when psutil is installed; otherwise report unavailable."""
    try:
        import psutil  # optional dependency; never required to launch the app
        counters = psutil.net_io_counters()
        return {"available": True, "bytes_sent": counters.bytes_sent,
                "bytes_received": counters.bytes_recv}
    except (ImportError, AttributeError, OSError):
        return {"available": False, "bytes_sent": None, "bytes_received": None}


def gpu_status() -> dict:
    """Best-effort GPU status. Does not install drivers or execute vendor tools."""
    return {"available": False, "detail": "GPU metrics require a future, explicitly configured provider."}


def format_bytes(value: Optional[int]) -> str:
    if value is None:
        return "indisponível"
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"
