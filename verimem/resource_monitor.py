"""Cycle 2026-05-27 round 13 P2b — CPU/RAM throttle background monitor.

Aurelio audit gap I2: "no resource limits (Claude può consumare 100%
CPU/RAM senza throttling)".

Approach: polling-based monitor over the current process tree (configurable
PID set). Uses psutil. Two thresholds:

  cpu_pct_threshold (default 80%): trigger when CPU > N % for >= sustain_s
  ram_mb_threshold (default 4096 MB): trigger when RSS > N MB

Triggered alerts append to ~/.engram/audit/resource-YYYYMMDD.jsonl and
fire a Python callback (passed at construct time) for in-process reaction.

The monitor never kills processes — that decision belongs to the operator.
It just produces structured signal.

Config file ~/.claude/clp_throttle.json (optional):
    {
      "cpu_pct_threshold": 80,
      "ram_mb_threshold": 4096,
      "sustain_seconds": 30,
      "poll_interval_seconds": 5
    }
"""
from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "clp_throttle.json"
DEFAULT_AUDIT_ROOT = Path.home() / ".engram" / "audit"

DEFAULTS: dict = {
    "cpu_pct_threshold": 80.0,
    "ram_mb_threshold": 4096,
    "sustain_seconds": 30,
    "poll_interval_seconds": 5,
}


@dataclass(frozen=True)
class ResourceSample:
    """One sampling event."""
    ts: float
    pid: int
    cpu_pct: float
    rss_mb: float


@dataclass(frozen=True)
class ResourceAlert:
    """Sustained-breach alert."""
    kind: str  # 'cpu' | 'ram'
    pid: int
    value: float
    threshold: float
    sustained_s: float
    fired_at: float


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict:
    """Load config from JSON. Missing file -> defaults."""
    p = Path(path)
    if not p.exists():
        return dict(DEFAULTS)
    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    out.update(loaded)
    return out


def sample_process(pid: int) -> ResourceSample | None:
    """One snapshot of CPU + RAM for `pid`. None if process missing."""
    try:
        import psutil
    except ImportError:
        return None
    try:
        p = psutil.Process(pid)
        # psutil cpu_percent needs a sampling interval (warm-up).
        cpu = p.cpu_percent(interval=0.1)
        mem = p.memory_info().rss / (1024 * 1024)
        return ResourceSample(
            ts=time.time(), pid=pid, cpu_pct=cpu, rss_mb=mem,
        )
    except Exception:
        return None


@dataclass
class ResourceMonitor:
    """Background poller that fires alerts on sustained CPU/RAM breach.

    The monitor doesn't kill anything — it just structurally surfaces signal
    that the operator (or a higher-level Claude Code policy) can act on.
    """
    pids: list[int]
    config: dict = field(default_factory=lambda: dict(DEFAULTS))
    on_alert: Callable[[ResourceAlert], None] | None = None
    audit_root: Path = DEFAULT_AUDIT_ROOT
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_evt: threading.Event = field(
        default_factory=threading.Event, repr=False,
    )
    # Sustained-breach trackers per (pid, kind): epoch when breach started,
    # or None if currently under threshold.
    _breach_start: dict[tuple[int, str], float | None] = field(
        default_factory=dict, repr=False,
    )

    @property
    def audit_log_path(self) -> Path:
        return self.audit_root / f"resource-{datetime.now():%Y%m%d}.jsonl"

    def _audit(self, event: dict) -> None:
        self.audit_root.mkdir(parents=True, exist_ok=True)
        event = {"ts": time.time(), **event}
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _check_one(self, pid: int) -> ResourceAlert | None:
        sample = sample_process(pid)
        if sample is None:
            return None
        sustain_s = float(self.config.get(
            "sustain_seconds", DEFAULTS["sustain_seconds"]
        ))
        for kind, value, threshold in (
            ("cpu", sample.cpu_pct, float(self.config.get(
                "cpu_pct_threshold", DEFAULTS["cpu_pct_threshold"]
            ))),
            ("ram", sample.rss_mb, float(self.config.get(
                "ram_mb_threshold", DEFAULTS["ram_mb_threshold"]
            ))),
        ):
            key = (pid, kind)
            if value > threshold:
                started = self._breach_start.get(key)
                if started is None:
                    self._breach_start[key] = sample.ts
                elif sample.ts - started >= sustain_s:
                    alert = ResourceAlert(
                        kind=kind, pid=pid, value=value,
                        threshold=threshold,
                        sustained_s=sample.ts - started,
                        fired_at=sample.ts,
                    )
                    # Reset so a single sustained breach fires once per
                    # sustain window (not every poll).
                    self._breach_start[key] = sample.ts
                    return alert
            else:
                self._breach_start[key] = None
        return None

    def tick(self) -> list[ResourceAlert]:
        """One synchronous polling cycle. Useful for tests + manual ops."""
        alerts: list[ResourceAlert] = []
        for pid in list(self.pids):
            alert = self._check_one(pid)
            if alert is not None:
                alerts.append(alert)
                self._audit({
                    "event": "resource_alert",
                    "kind": alert.kind, "pid": alert.pid,
                    "value": alert.value, "threshold": alert.threshold,
                    "sustained_s": alert.sustained_s,
                })
                if self.on_alert:
                    try:
                        self.on_alert(alert)
                    except Exception:
                        pass
        return alerts

    def _loop(self) -> None:
        interval = float(self.config.get(
            "poll_interval_seconds",
            DEFAULTS["poll_interval_seconds"],
        ))
        while not self._stop_evt.is_set():
            self.tick()
            self._stop_evt.wait(interval)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_evt.clear()
        t = threading.Thread(target=self._loop, name="engram-resource-monitor",
                              daemon=True)
        t.start()
        self._thread = t

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_evt.set()
        t = self._thread
        if t is not None:
            t.join(timeout=timeout)
        self._thread = None


__all__ = [
    "DEFAULTS",
    "DEFAULT_AUDIT_ROOT",
    "DEFAULT_CONFIG_PATH",
    "ResourceAlert",
    "ResourceMonitor",
    "ResourceSample",
    "load_config",
    "sample_process",
]
