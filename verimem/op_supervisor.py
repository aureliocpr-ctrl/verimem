"""Cycle 365 (2026-05-23) — OPERATION SUPERVISOR for engram syscall bridge.

Aurelio mandate "stato superiore engram, meta-regole sempre". Pattern
OTP/Erlang-inspired operation-level supervisor con circuit-breaker:
quando una memory op fails N volte consecutive entro window, circuit
"opens" → subsequent calls bloccate finché reset_window scaduto.

B4 concatenazione → STATO SUPERIORE engineering:
  clp.agentos.supervisor (process-level Erlang supervisor, LOOP 342)
  + verimem.syscall_bridge (typed boundary cycle 364)
  + circuit-breaker pattern (Hystrix/Polly)
  ⇒ OS-native memory layer ora ha FAULT-ISOLATION at operation level.

DIFFERENZA con clp supervisor:
  - clp supervisor: process-level (start/stop/restart subprocess)
  - engram op_supervisor: in-process operation-level
    (failure counting, circuit-breaker, reset_window)
  - complementare: clp restart il servizio, engram bloccca op singola.

A3 honest scope: NOT singolarità. Engineering pattern (Hystrix predates
2012). Novel solo la composizione con syscall_bridge anti-hallucination
manifest + engram memory ops + per-op state.

API:
  CircuitState: enum {closed, open, half_open}
  OpSupervisor: in-process state per op
    record_success(op) -> reset failure counter
    record_failure(op, reason) -> increment, maybe open circuit
    check(op) -> {allowed: bool, blocked_by: str | None, state: dict}
  reset_all() -> clean slate for testing

  Configurazione default:
    max_failures = 3 consecutive
    failure_window_sec = 30.0
    reset_window_sec = 60.0 (half-open after this)
    half_open_probe_count = 1 (test 1 call when half-open)

Falsifiable contract (cycle 365):
  (a) 3 consecutive failures su op X → circuit X opens
  (b) Call X dopo open → blocked_by='circuit_breaker_open'
  (c) Successo Y other op → Y state independent (per-op isolation)
  (d) reset_window scaduto → circuit half_open + permette 1 probe
"""
from __future__ import annotations

import time
from collections import defaultdict
from enum import Enum
from threading import Lock
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class OpSupervisor:
    """In-process per-op circuit breaker supervisor.

    Thread-safe (uses RLock). Each operation has its own state.
    """

    def __init__(
        self,
        max_failures: int = 3,
        failure_window_sec: float = 30.0,
        reset_window_sec: float = 60.0,
        half_open_probe_count: int = 1,
    ) -> None:
        self.max_failures = max_failures
        self.failure_window_sec = failure_window_sec
        self.reset_window_sec = reset_window_sec
        self.half_open_probe_count = half_open_probe_count
        # Per-op state
        self._state: dict[str, dict[str, Any]] = defaultdict(self._initial_state)
        self._lock = Lock()

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "circuit": CircuitState.CLOSED,
            "n_consecutive_failures": 0,
            "failure_timestamps": [],  # recent failures within window
            "last_open_at": None,
            "half_open_probes_remaining": 0,
            "n_total_failures": 0,
            "n_total_successes": 0,
            "last_failure_reason": None,
        }

    def _trim_window(self, st: dict, now: float) -> None:
        cutoff = now - self.failure_window_sec
        st["failure_timestamps"] = [t for t in st["failure_timestamps"]
                                     if t >= cutoff]

    def check(self, op: str) -> dict:
        """Return current allowance + state for op.

        Returns: {allowed: bool, blocked_by: str | None, state: dict}
        """
        now = time.time()
        with self._lock:
            st = self._state[op]
            self._trim_window(st, now)

            # CLOSED: always allowed
            if st["circuit"] == CircuitState.CLOSED:
                return {"allowed": True, "blocked_by": None,
                        "state": self._snapshot(op, st)}

            # OPEN: check if reset_window elapsed
            if st["circuit"] == CircuitState.OPEN:
                if (st["last_open_at"] is not None and
                        now - st["last_open_at"] >= self.reset_window_sec):
                    # Transition to HALF_OPEN + consume 1 probe for THIS check
                    st["circuit"] = CircuitState.HALF_OPEN
                    st["half_open_probes_remaining"] = (
                        self.half_open_probe_count - 1
                    )
                    return {"allowed": True, "blocked_by": None,
                            "state": self._snapshot(op, st)}
                return {"allowed": False,
                        "blocked_by": "circuit_breaker_open",
                        "state": self._snapshot(op, st)}

            # HALF_OPEN: allow up to half_open_probe_count probes
            if st["circuit"] == CircuitState.HALF_OPEN:
                if st["half_open_probes_remaining"] > 0:
                    st["half_open_probes_remaining"] -= 1
                    return {"allowed": True, "blocked_by": None,
                            "state": self._snapshot(op, st)}
                # No probes left: stay half_open, block
                return {"allowed": False,
                        "blocked_by": "circuit_breaker_half_open_exhausted",
                        "state": self._snapshot(op, st)}
            # Defensive: unknown state → block
            return {"allowed": False, "blocked_by": "unknown_state",
                    "state": self._snapshot(op, st)}

    def record_success(self, op: str) -> dict:
        """Record successful op call. Resets consecutive failure counter.

        HALF_OPEN + success → close circuit.
        """
        time.time()
        with self._lock:
            st = self._state[op]
            st["n_consecutive_failures"] = 0
            st["n_total_successes"] += 1
            if st["circuit"] == CircuitState.HALF_OPEN:
                # Successful probe → close circuit
                st["circuit"] = CircuitState.CLOSED
                st["last_open_at"] = None
                st["failure_timestamps"] = []
            return self._snapshot(op, st)

    def record_failure(self, op: str, reason: str = "unknown") -> dict:
        """Record failure. If threshold reached → open circuit.

        HALF_OPEN + failure → re-open circuit (no leniency).
        """
        now = time.time()
        with self._lock:
            st = self._state[op]
            self._trim_window(st, now)
            st["n_consecutive_failures"] += 1
            st["n_total_failures"] += 1
            st["failure_timestamps"].append(now)
            st["last_failure_reason"] = reason

            if st["circuit"] == CircuitState.HALF_OPEN:
                # Probe failed → re-open
                st["circuit"] = CircuitState.OPEN
                st["last_open_at"] = now
                st["half_open_probes_remaining"] = 0
            elif (st["circuit"] == CircuitState.CLOSED and
                    len(st["failure_timestamps"]) >= self.max_failures):
                st["circuit"] = CircuitState.OPEN
                st["last_open_at"] = now
            return self._snapshot(op, st)

    def reset_all(self) -> None:
        """Reset all per-op state. For tests + admin."""
        with self._lock:
            self._state.clear()

    def reset_op(self, op: str) -> None:
        """Manually reset a single op's circuit."""
        with self._lock:
            if op in self._state:
                self._state[op] = self._initial_state()

    def escalate_open_circuits(
        self,
        min_open_sec: float = 60.0,
        alert_channel: str = "os/alerts",
        sender: str = "engram_supervisor",
    ) -> list[dict]:
        """Cycle 377: publish vec_bus alert for circuits open beyond
        a threshold. Idempotent: should be called periodically (e.g.
        every 30s by an ambient daemon).

        Returns list of {op, alert_msg_id, open_duration_sec}.
        """
        now = time.time()
        escalated: list[dict] = []
        snapshot = self.snapshot_all()
        for op, snap in snapshot.items():
            if snap["circuit"] != "open":
                continue
            last_open = snap.get("last_open_at")
            if last_open is None:
                continue
            open_dur = now - last_open
            if open_dur < min_open_sec:
                continue
            # Build alert payload
            alert_text = (
                f"engram circuit OPEN op={op} duration={open_dur:.1f}s "
                f"failures={snap['n_total_failures']} "
                f"last_reason={snap.get('last_failure_reason')!r}"
            )
            try:
                from clp.agentos import vec_bus
                r = vec_bus.vec_send(
                    alert_channel, alert_text, sender=sender,
                    origin_hint=f"circuit-open:{op}",
                    intent_tag="engram-alert-circuit-open",
                )
                if r.get("ok"):
                    escalated.append({
                        "op": op,
                        "alert_msg_id": r["msg_id"],
                        "open_duration_sec": open_dur,
                    })
            except (ImportError, Exception):  # noqa: BLE001
                # Best-effort: vec_bus may be unavailable
                pass
        return escalated

    def snapshot_all(self) -> dict[str, dict[str, Any]]:
        """Return current state for all tracked ops (diagnostic)."""
        with self._lock:
            return {op: self._snapshot(op, st)
                    for op, st in self._state.items()}

    def _snapshot(self, op: str, st: dict) -> dict:
        return {
            "op": op,
            "circuit": (
                st["circuit"].value if isinstance(st["circuit"], CircuitState)
                else st["circuit"]
            ),
            "n_consecutive_failures": st["n_consecutive_failures"],
            "n_failures_in_window": len(st["failure_timestamps"]),
            "n_total_failures": st["n_total_failures"],
            "n_total_successes": st["n_total_successes"],
            "last_failure_reason": st["last_failure_reason"],
            "last_open_at": st["last_open_at"],
            "half_open_probes_remaining": st["half_open_probes_remaining"],
        }


# Module-level default supervisor (singleton convenience)
_DEFAULT_SUPERVISOR: OpSupervisor | None = None


def get_default_supervisor() -> OpSupervisor:
    """Get/create the process-level default supervisor."""
    global _DEFAULT_SUPERVISOR
    if _DEFAULT_SUPERVISOR is None:
        _DEFAULT_SUPERVISOR = OpSupervisor()
    return _DEFAULT_SUPERVISOR


def reset_default() -> None:
    """Reset the default supervisor (test fixture)."""
    global _DEFAULT_SUPERVISOR
    _DEFAULT_SUPERVISOR = None
