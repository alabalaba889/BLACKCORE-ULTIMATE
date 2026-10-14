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


def sparkline(values: list, width: int = 20) -> str:
    """Render recent numeric samples as a compact text chart; missing samples show a dot."""
    if width < 1:
        raise ValueError("width must be positive")
    samples = list(values)[-width:]
    if not samples:
        return "—"
    glyphs = "▁▂▃▄▅▆▇█"
    numeric = [float(v) for v in samples if v is not None]
    if not numeric:
        return "·" * len(samples)
    low, high = min(numeric), max(numeric)
    out = []
    for value in samples:
        if value is None:
            out.append("·")
        elif high == low:
            out.append("▄")
        else:
            index = int((float(value) - low) / (high - low) * (len(glyphs) - 1))
            out.append(glyphs[index])
    return "".join(out)


def append_history(history: list, value, limit: int = 40) -> list:
    """Return a bounded copy of history with one sample appended."""
    if limit < 1:
        raise ValueError("limit must be positive")
    result = list(history)
    result.append(value)
    return result[-limit:]
