"""CYCLE #26 — audit log tail reader (pure-function).

Pre-fix: mcp_server.py importava `from verimem.audit_tail import audit_tail`
ma il modulo NON ESISTEVA. ImportError catturato da try/except in
`hippo_introspect_state` → recent_audit=[] silenziosamente. Tool funzionava
ma sempre con dati vuoti, masking del bug.

Questo modulo centralizza la logica di lettura tail già presente inline
nel handler hippo_audit_tail (mcp_server.py:4400-4425) e la espone come
pure-function utilizzabile da introspect_state + future caller.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _audit_log_path() -> Path:
    """Resolve audit log path. Honour HIPPO_MCP_AUDIT_LOG env override."""
    custom = os.environ.get("HIPPO_MCP_AUDIT_LOG", "").strip()
    if custom:
        return Path(custom)
    from .config import CONFIG
    return CONFIG.data_dir / "mcp_audit.log"


def audit_tail(*, n: int = 50, path: Path | None = None) -> dict[str, Any]:
    """Read last N entries from the MCP audit log (JSONL).

    Args:
        n: number of entries from the tail (clamped to [1, 10000]).
        path: optional override for testability. None → use env/CONFIG default.

    Returns:
        {
          "path": str,                     # absolute path read
          "entries": list[dict],           # parsed JSON records, newest last
          "n_requested": int,
          "n_returned": int,
          "exists": bool,                  # False se file mancante (no entries)
        }

    Entries malformati (JSON parse error) sono raccolti come `{"_raw": ...}`
    invece di causare fallimento. Errore di I/O ritorna entries vuoto + exists=False
    (best-effort, audit deve essere non-blocking).
    """
    n_eff = max(1, min(int(n), 10_000))
    log_path = path or _audit_log_path()
    entries: list[dict[str, Any]] = []
    exists = False
    try:
        if log_path.exists():
            exists = True
            with open(log_path, encoding="utf-8") as f:
                all_lines = f.readlines()
            for line in all_lines[-n_eff:]:
                s = line.strip()
                if not s:
                    continue
                try:
                    entries.append(json.loads(s))
                except json.JSONDecodeError:
                    entries.append({"_raw": s[:500]})
    except OSError:
        # Audit deve essere non-blocking. Restituisce entries parziali (se any).
        pass
    return {
        "path": str(log_path),
        "entries": entries,
        "n_requested": n_eff,
        "n_returned": len(entries),
        "exists": exists,
    }


__all__ = ["audit_tail"]
