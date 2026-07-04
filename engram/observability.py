"""Observability: structured logging, event bus, metrics registry.

The HippoAgent emits a structured event for every meaningful action
(episode_started, skill_retrieved, dream_synthesized, fitness_updated, ...).
Subscribers can react in real time (dashboard, metrics, persistence).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

# ---- Structured logging ----------------------------------------------------

# When `HIPPO_LOG_STDERR=1` is set BEFORE this module is imported, every log
# line is routed to stderr and colors are disabled. The MCP stdio server
# requires this — its protocol owns stdout and any extra byte breaks JSON-RPC
# framing. Other entry points (CLI, dashboard, tests) keep the default
# stdout + colored output.
_log_to_stderr = os.environ.get("HIPPO_LOG_STDERR", "").strip() == "1"
_log_factory = (
    structlog.PrintLoggerFactory(file=sys.stderr) if _log_to_stderr else None
)
_console_renderer = structlog.dev.ConsoleRenderer(
    colors=not _log_to_stderr,
)

_configure_kwargs: dict[str, Any] = dict(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        _console_renderer,
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    cache_logger_on_first_use=True,
)
if _log_factory is not None:
    _configure_kwargs["logger_factory"] = _log_factory
structlog.configure(**_configure_kwargs)

log = structlog.get_logger("hippo")


def route_logs_to_stderr() -> None:
    """Re-route every structlog line to stderr (colors off), for entry points
    whose stdout is a PROTOCOL channel (the MCP stdio server: any extra byte
    on stdout breaks JSON-RPC framing).

    Needed because `HIPPO_LOG_STDERR=1` only works when set BEFORE this module
    is first imported — engram/cli.py imports observability at module top, so
    the env-var set later inside mcp_server.py comes too late on the
    `engram mcp` CLI path (G2 install smoke, 2026-07-04). Call this before the
    server starts; loggers already bound to stdout by earlier use keep their
    factory (cache_logger_on_first_use), so call it before any logging."""
    os.environ["HIPPO_LOG_STDERR"] = "1"
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


# ---- Event bus -------------------------------------------------------------


@dataclass
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({"name": self.name, "payload": self.payload, "ts": self.ts})


Subscriber = Callable[[Event], None]


class EventBus:
    """Synchronous pub/sub. Thread-safe. Keeps a ring buffer of recent events."""

    def __init__(self, history_size: int = 1024) -> None:
        self._subs: dict[str, list[Subscriber]] = defaultdict(list)
        self._wildcards: list[Subscriber] = []
        self._lock = threading.RLock()
        self._history: deque[Event] = deque(maxlen=history_size)

    def subscribe(self, event_name: str, fn: Subscriber) -> None:
        with self._lock:
            if event_name == "*":
                self._wildcards.append(fn)
            else:
                self._subs[event_name].append(fn)

    def unsubscribe(self, event_name: str, fn: Subscriber) -> None:
        """Remove a previously-registered subscriber. No-op if absent.

        Tolerant of double-unsubscribe and of a never-subscribed ``fn`` so a
        caller's teardown path (e.g. the SSE generator's ``finally``) can invoke
        it unconditionally without guarding. Without this, every wildcard
        ``subscribe`` leaked — each ``emit()`` iterates ``_wildcards`` /
        ``_subs[name]`` so a growing list slows all event emission process-wide
        and pins the captured closures. See
        ``tests/test_eventbus_unsubscribe_leak.py``.
        """
        with self._lock:
            target = (
                self._wildcards if event_name == "*" else self._subs.get(event_name)
            )
            if not target:
                return
            try:
                target.remove(fn)
            except ValueError:
                pass

    def emit(self, name: str, **payload: Any) -> Event:
        evt = Event(name=name, payload=payload)
        with self._lock:
            self._history.append(evt)
            subs = list(self._subs.get(name, [])) + list(self._wildcards)
        for fn in subs:
            try:
                fn(evt)
            except Exception:
                # ``event`` would collide with structlog's positional `event`
                # (the message), surfacing as ``TypeError: exception() got
                # multiple values for argument 'event'`` and propagating out
                # of BUS.emit. Rename the field — drive-by fix discovered
                # while bootstrapping the memory-map dashboard.
                log.exception(
                    "event_subscriber_failed", failing_event=name
                )
        return evt

    def history(self, event_name: str | None = None, limit: int = 100) -> list[Event]:
        with self._lock:
            items = list(self._history)
        if event_name:
            items = [e for e in items if e.name == event_name]
        return items[-limit:]


BUS = EventBus()


# ---- Metrics registry ------------------------------------------------------


class MetricsRegistry:
    """Lightweight in-memory metrics: counters + histograms."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}
        self._lock = threading.RLock()

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(value)

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            hist_summary = {}
            for k, v in self._histograms.items():
                if not v:
                    continue
                arr = sorted(v)
                hist_summary[k] = {
                    "count": len(arr),
                    "mean": sum(arr) / len(arr),
                    "min": arr[0],
                    "max": arr[-1],
                    "p50": arr[len(arr) // 2],
                    "p95": arr[min(len(arr) - 1, int(len(arr) * 0.95))],
                }
            return {
                "counters": dict(self._counters),
                "histograms": hist_summary,
                "gauges": dict(self._gauges),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


METRICS = MetricsRegistry()


# ---- Bridge: events → metrics + logs --------------------------------------

def _on_any_event(evt: Event) -> None:
    METRICS.inc(f"events.{evt.name}")


def _on_episode_completed(evt: Event) -> None:
    p = evt.payload
    METRICS.inc(f"episodes.{p.get('outcome', 'unknown')}")
    if "tokens_used" in p:
        METRICS.observe("episode.tokens", float(p["tokens_used"]))
    if "steps" in p:
        METRICS.observe("episode.steps", float(p["steps"]))


def _on_skill_synthesized(evt: Event) -> None:
    METRICS.inc("skills.synthesized")


def _on_skill_promoted(evt: Event) -> None:
    METRICS.inc("skills.promoted")


def _on_skill_retired(evt: Event) -> None:
    METRICS.inc("skills.retired")


BUS.subscribe("*", _on_any_event)
BUS.subscribe("episode_completed", _on_episode_completed)
BUS.subscribe("skill_synthesized", _on_skill_synthesized)
BUS.subscribe("skill_promoted", _on_skill_promoted)
BUS.subscribe("skill_retired", _on_skill_retired)


def get_log() -> structlog.BoundLogger:
    return log


def emit(name: str, **payload: Any) -> None:
    BUS.emit(name, **payload)
    log.info(name, **payload)
    # Cross-process fan-out: la memory-map live dashboard fa tail del JSONL
    # per mostrare attività di altre istanze HippoAgent. Late import per
    # evitare cicli e best-effort: errori inghiottiti dentro append_event.
    try:
        from . import event_jsonl_log
        event_jsonl_log.append_event(name, dict(payload))
    except Exception:
        pass
