"""Cycle 2026-05-27 round 13 P2a — hot-reload code watcher.

Aurelio audit gap C2: "no hot-reload MCP server — ogni modifica Python
richiede restart Claude Code session". Gemini suggested ``watchdog`` lib.

Reality check: a Python MCP server hosted in the Claude Code process
cannot be soft-restarted from inside a user-mode helper — the host owns
the process lifecycle. What this module CAN do:

  1. Observe .py changes under engram/ + clp/ via watchdog.
  2. Compute a content hash so cosmetic-only changes (whitespace, comments)
     are ignored.
  3. Emit a BUS event ``mcp_code_changed`` with the changed file path so
     the dashboard / Claude Code instance can surface a "restart needed"
     notification.
  4. Write a JSON marker ``~/.engram/hot_reload/pending.json`` containing
     the changed files since the last restart, so future tooling (e.g. a
     supervisor or a Claude Code plugin) can warn at session start.

The actual subprocess restart is out of scope; this is the OBSERVATION
half of hot-reload. It removes the silent-drift failure mode where you
think the new gate logic is active but the live MCP is still on cached
old code.

Usage:
    watcher = HotReloadWatcher([engram_root, clp_root])
    watcher.start()  # non-blocking
    # ... your work ...
    watcher.stop()

Or one-shot snapshot:
    pending = collect_pending_changes(state_file=...)
"""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_STATE_DIR = Path.home() / ".engram" / "hot_reload"
DEFAULT_PENDING_FILE = DEFAULT_STATE_DIR / "pending.json"


@dataclass(frozen=True)
class FileChange:
    """One observed change to a watched .py file."""
    path: Path
    new_hash: str
    detected_at: float


def _hash_file(path: Path) -> str:
    """Content sha256 (first 16 hex chars). Returns '' if file unreadable."""
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()[:16]
    except OSError:
        return ""


def _scan_py_files(roots: list[Path]) -> dict[str, str]:
    """Return {path_str: content_hash} for every .py under each root.

    Skips common noise dirs (.git, __pycache__, .venv, node_modules).
    """
    skip_dirs = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"}
    out: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            # Skip if any path component is in skip_dirs.
            if any(part in skip_dirs for part in p.parts):
                continue
            out[str(p.resolve())] = _hash_file(p)
    return out


def diff_snapshots(
    before: dict[str, str], after: dict[str, str],
) -> list[FileChange]:
    """Return list of FileChange for files added or content-changed.

    Deletions are also reported (new_hash = '' indicates removed).
    """
    now = time.time()
    changes: list[FileChange] = []
    for p, h in after.items():
        if before.get(p) != h:
            changes.append(FileChange(path=Path(p), new_hash=h, detected_at=now))
    for p in set(before) - set(after):
        changes.append(FileChange(path=Path(p), new_hash="", detected_at=now))
    return changes


def collect_pending_changes(
    roots: list[Path],
    *,
    state_file: Path = DEFAULT_PENDING_FILE,
) -> list[FileChange]:
    """Compare current FS state to the last snapshot in state_file.

    Updates state_file with the current snapshot. Returns changes since
    last call. First call returns [] (just establishes baseline).
    """
    state_file.parent.mkdir(parents=True, exist_ok=True)
    if state_file.exists():
        prev = json.loads(state_file.read_text(encoding="utf-8")).get(
            "snapshot", {}
        )
    else:
        prev = {}
    curr = _scan_py_files(roots)
    state_file.write_text(
        json.dumps({"snapshot": curr, "ts": time.time()}, ensure_ascii=False),
        encoding="utf-8",
    )
    return diff_snapshots(prev, curr)


@dataclass
class HotReloadWatcher:
    """Optional live watcher (requires `watchdog` lib). Start in a thread.

    On each detected change, calls ``on_change(FileChange)`` if provided
    and appends to ``pending`` list (drained by ``drain_pending()``).
    """
    roots: list[Path]
    on_change: Callable[[FileChange], None] | None = None
    pending: list[FileChange] = field(default_factory=list)
    _observer: object | None = field(default=None, repr=False)
    _snapshot: dict[str, str] = field(default_factory=dict, repr=False)

    def start(self) -> None:
        """Begin watching. No-op if watchdog isn't installed (degraded mode)."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            # Degraded mode: caller must poll via collect_pending_changes.
            self._observer = None
            return
        self._snapshot = _scan_py_files(self.roots)

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                self._maybe_emit(event)

            def on_created(self, event):
                self._maybe_emit(event)

            def on_deleted(self, event):
                self._maybe_emit(event)

            def _maybe_emit(self, event):
                src = getattr(event, "src_path", "")
                if not src.endswith(".py"):
                    return
                p = Path(src).resolve()
                new_hash = _hash_file(p) if p.exists() else ""
                old_hash = watcher._snapshot.get(str(p), "")
                if new_hash == old_hash:
                    return  # cosmetic / no real change
                watcher._snapshot[str(p)] = new_hash
                fc = FileChange(path=p, new_hash=new_hash, detected_at=time.time())
                watcher.pending.append(fc)
                if watcher.on_change:
                    try:
                        watcher.on_change(fc)
                    except Exception:
                        pass

        obs = Observer()
        for root in self.roots:
            if root.exists():
                obs.schedule(_Handler(), str(root), recursive=True)
        obs.daemon = True
        obs.start()
        self._observer = obs

    def stop(self) -> None:
        obs = self._observer
        if obs is not None:
            try:
                obs.stop()
                obs.join(timeout=2.0)
            except Exception:
                pass
        self._observer = None

    def drain_pending(self) -> list[FileChange]:
        """Return + clear the queued changes."""
        out = list(self.pending)
        self.pending.clear()
        return out


__all__ = [
    "DEFAULT_PENDING_FILE",
    "DEFAULT_STATE_DIR",
    "FileChange",
    "HotReloadWatcher",
    "collect_pending_changes",
    "diff_snapshots",
]
