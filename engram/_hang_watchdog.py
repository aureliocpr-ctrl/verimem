"""Hang watchdog — make intermittent multi-minute MCP hangs DIAGNOSABLE.

When a tool call exceeds a wall-clock budget, dump ALL thread stacks to
``~/.engram/hang-traces/`` so the exact blocking frame is captured in the act
(``_MODEL_LOCK.acquire`` / socket ``recv`` / sqlite lock / a stale-code path).
Without this, a hang that only reproduces in a user's specific session is a
black box.

CONTRACT — observability ONLY:
  * never changes dispatch behaviour (the call runs exactly as before),
  * never raises (a broken trace dir must not break the tool),
  * never cancels/returns the call (it only LOGS; fixing is a separate concern),
  * a fast call leaves NO file (the header-only file is cleaned up).

faulthandler's timer is process-global, so only ONE call is watched at a time
(a non-blocking lock); concurrent calls run unwatched rather than clobbering the
timer. With the synchronous MCP dispatch (one tool body on the loop at a time)
this watches effectively every call.
"""
from __future__ import annotations

import faulthandler
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_TRACE_DIR = Path(
    os.environ.get("HIPPO_HANG_TRACE_DIR")
    or (Path.home() / ".engram" / "hang-traces")
)
# Below this many bytes the file is header-only (nothing was dumped) → delete.
_HEADER_MAX_BYTES = 300
_ARMED = threading.Lock()


@contextmanager
def hang_trace(label: str, budget_s: float):
    """Wrap a tool call. If it runs longer than ``budget_s`` seconds, append a
    full all-thread stack dump to a per-call file under ``_TRACE_DIR``."""
    if not budget_s or budget_s <= 0:
        yield
        return
    # Process-global faulthandler timer → only one watcher at a time.
    if not _ARMED.acquire(blocking=False):
        yield
        return
    f = None
    path = None
    armed = False
    try:
        _TRACE_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(label))[:40]
        path = _TRACE_DIR / f"hang-{int(time.time())}-{os.getpid()}-{safe}.txt"
        f = open(path, "w", encoding="utf-8")
        f.write(
            f"HANG WATCHDOG  tool={label}  pid={os.getpid()}  budget={budget_s}s\n"
            "the stacks below were dumped because the call exceeded the budget:\n"
        )
        f.flush()
        faulthandler.dump_traceback_later(budget_s, repeat=True, file=f)
        armed = True
    except Exception:  # noqa: BLE001 — tracing is best-effort, never break the call
        if f is not None:
            try:
                f.close()
            except Exception:  # noqa: BLE001
                pass
            f = None
    try:
        yield
    finally:
        if armed:
            try:
                faulthandler.cancel_dump_traceback_later()
            except Exception:  # noqa: BLE001
                pass
        if f is not None:
            try:
                size = f.tell()
                f.close()
                if size <= _HEADER_MAX_BYTES and path is not None:
                    path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        _ARMED.release()
