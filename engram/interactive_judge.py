"""Interactive-CLI judge — Claude as the write-gate judge WITHOUT claude -p.

Why: headless subscription calls (claude -p) are moving to paid; interactive Claude
CLI sessions stay on the flat subscription. Validated empirically 2026-07-02: a GHOST
sister (hidden console window) judges grounding batches with 10/10 decision agreement
vs the claude -p judge at ~3.6-5 s/item — ai-eye's transport is AttachConsole(pid) +
WriteConsoleInputW, pure console API, no visible window or focus needed.

Pattern (filesystem handshake — long prompts never go through the console):
  1. spawn ONE sister (``clp.commands.swarm_launch_cmd`` conhost, auto-trust), find her
     console windows (incl. conhost children) and hide them (SW_HIDE) — GHOST;
  2. PROBE both pids from ``~/.clp/swarm_new_pwsh_pids.txt`` with ai-eye --read (the
     claude pid is NOT positional in that file — measured: run1 first, run2 second);
  3. write a batch .md (rubric + N items) under ~/.engram/local_gate/, inject one short
     "read that file" command, poll the JSON response file;
  4. REUSE the sister across batches; kill the whole tree (taskkill /T) on close.

This module is transport-injected (house style): unit tests use a fake transport; the
real one (GhostSisterTransport) shells out to the clp arsenal and is exercised live.
Backend selection: ``ENGRAM_GROUNDING_BACKEND=interactive`` routes
``fact_grounding_score`` here; any failure returns None and the gate falls back to the
injected llm — same fail-over contract as the local CE backend.
"""
from __future__ import annotations

import atexit
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol

from engram._proc_quiet import quiet_popen_kwargs

_RUBRIC = (
    "Sei il judge di grounding del write-gate di Engram. Per OGNI item qui sotto valuta"
    " da 0 a 100 quanto la SOURCE implica logicamente (entails) il CANDIDATE FACT:"
    " 100 = la source lo afferma o lo implica senza ambiguita'; 50 = correlato ma NON"
    " stabilito (inferenza plausibile non affermata = confabulazione); 0 = non"
    " supportato o contraddetto. Giudica il SIGNIFICATO, non la sovrapposizione di"
    " parole.")

DATA_DIR = Path.home() / ".engram" / "local_gate"


class Transport(Protocol):
    def ensure_session(self) -> str: ...
    def run_batch(self, batch_md: str, items: list[dict],
                  timeout_s: float) -> dict[str, Any] | None: ...


class InteractiveJudge:
    """Scores (source, fact) pairs through an interactive Claude CLI sister."""

    def __init__(self, transport: Transport | None = None, *,
                 timeout_s: float = 180.0):
        self._transport = transport or GhostSisterTransport()
        self.timeout_s = timeout_s

    def render_batch(self, items: list[dict]) -> str:
        resp = items[0]["response_path"] if items else ""
        lines = ["# GATE JUDGE BATCH — istruzioni", "", _RUBRIC, "",
                 f"Quando hai finito, scrivi il file {resp}",
                 'con ESATTAMENTE questo formato: {"item_1": <score>, "item_2": <score>, ...}',
                 "Nessun altro testo nel file. Poi rispondi in chat solo: COMPLETATO", ""]
        for i, it in enumerate(items, 1):
            lines += [f"## item_{i}", "SOURCE:", it["source"], "",
                      "CANDIDATE FACT:", it["fact"], ""]
        return "\n".join(lines)

    def parse_response(self, text: str, n: int) -> list[float | None] | None:
        try:
            d = json.loads(text)
        except (ValueError, TypeError):
            return None
        out: list[float | None] = []
        for i in range(1, n + 1):
            v = d.get(f"item_{i}")
            out.append(float(v) if isinstance(v, (int, float)) else None)
        return out

    def score_batch(self, pairs: list[tuple[str, str]],
                    ) -> list[float | None] | None:
        """Scores for (source, fact) pairs, order-preserving. None on ANY transport
        failure (spawn, inject, timeout) — the caller falls back, never crashes."""
        if not pairs:
            return []
        stamp = f"{int(time.time() * 1000):x}"
        resp_path = str(DATA_DIR / f"judge_{stamp}_response.json")
        items = [{"source": s, "fact": f, "response_path": resp_path}
                 for s, f in pairs]
        try:
            self._transport.ensure_session()
            raw = self._transport.run_batch(self.render_batch(items), items,
                                            self.timeout_s)
        except Exception:  # noqa: BLE001 — any transport trouble -> fall back
            return None
        if raw is None:
            return None
        return [float(raw[f"item_{i}"]) if isinstance(raw.get(f"item_{i}"),
                                                      (int, float)) else None
                for i in range(1, len(items) + 1)]

    def score(self, source: str, fact: str) -> float | None:
        r = self.score_batch([(source, fact)])
        return r[0] if r else None


class GhostSisterTransport:
    """The real thing: one TRUE-ghost interactive Claude CLI, reused across batches.

    Ghost = hidden FROM BIRTH: spawn claude.exe directly with CREATE_NEW_CONSOLE +
    STARTUPINFO(SW_HIDE). The console exists (so ai-eye's AttachConsole + read/inject
    work) but its window is never shown — no spawn-then-hide race, no visible frame.
    Verified 2026-07-02: visible_windows(pid) == 0 at 5/10/18 s, ai-eye read OK.
    ``claude.exe`` owns the console here (not a pwsh child), so ai-eye attaches to it
    directly."""

    CREATE_NEW_CONSOLE = 0x00000010
    STARTF_USESHOWWINDOW = 0x00000001
    SW_HIDE = 0

    def __init__(self, boot_timeout_s: float = 45.0):
        self._claude_pid: int | None = None
        self._proc = None
        self.boot_timeout_s = boot_timeout_s

    # -- session ------------------------------------------------------------
    def ensure_session(self) -> str:
        if self._claude_pid and self._pid_alive(self._claude_pid):
            return f"sister-{self._claude_pid}"
        self._spawn()
        return f"sister-{self._claude_pid}"

    def _pid_alive(self, pid: int) -> bool:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"[bool](Get-Process -Id {pid} -ErrorAction SilentlyContinue)"],
                           capture_output=True, text=True, timeout=15, **quiet_popen_kwargs())
        return "True" in r.stdout

    @staticmethod
    def _claude_exe() -> str:
        p = Path.home() / ".local" / "bin" / "claude.exe"
        return str(p) if p.exists() else "claude"

    def _popen_ghost(self):
        """Spawn claude.exe hidden from birth; returns the Popen handle.
        Split out of _spawn so the boot/ready logic is testable without a
        real spawn (and without STARTUPINFO on non-Windows CI)."""
        si = subprocess.STARTUPINFO()
        si.dwFlags |= self.STARTF_USESHOWWINDOW
        si.wShowWindow = self.SW_HIDE
        return subprocess.Popen(
            [self._claude_exe(), "--dangerously-skip-permissions"],
            creationflags=self.CREATE_NEW_CONSOLE, startupinfo=si,
            cwd=str(Path.home()))

    def _spawn(self) -> None:
        self._proc = self._popen_ghost()
        pid = self._proc.pid
        deadline = time.time() + self.boot_timeout_s
        trusted = False
        while time.time() < deadline:
            tail = self._read_tail(pid, 12).lower()
            if not trusted and ("trust this folder" in tail or "trust the files" in tail):
                # confirm the folder-trust dialog (default is "Yes") with one Enter
                self._inject_enter(pid)
                trusted = True
                time.sleep(3)
                continue
            if "bypass permissions" in tail or "❯" in tail:
                self._claude_pid = pid
                return
            time.sleep(3)
        # last chance: some builds settle without the marker in the tail window
        if "claude" in self._read_tail(pid, 20).lower():
            self._claude_pid = pid
            return
        # HARDENING (critic follow-up 2026-07-02): the sister exists but
        # never became ready — kill her NOW. Without this, _claude_pid stays
        # None, close() skips her, and an invisible claude.exe leaks.
        self._kill_tree(pid)
        self._proc = None
        raise RuntimeError(f"ghost claude {pid} did not become ready")

    def _read_tail(self, pid: int, n: int) -> str:
        r = subprocess.run(["clp", "ai-eye", "--pid", str(pid), "--read",
                            "--tail", str(n)],
                           capture_output=True, text=True, timeout=30, shell=True,
                           **quiet_popen_kwargs())
        return r.stdout or ""

    def _inject_enter(self, pid: int) -> None:
        subprocess.run(["clp", "ai-eye", "--pid", str(pid), "--inject", "",
                        "--newline"], capture_output=True, text=True, timeout=30,
                       shell=True, **quiet_popen_kwargs())

    def _kill_tree(self, pid: int) -> None:
        subprocess.run(["cmd", "/c", f"taskkill /PID {pid} /T /F"],
                       capture_output=True, timeout=20, **quiet_popen_kwargs())

    def close(self) -> None:
        # Reach the sister through EITHER handle: _claude_pid (ready) or
        # _proc (spawned but never ready). Idempotent.
        pid = self._claude_pid or (self._proc.pid if self._proc else None)
        if pid:
            self._kill_tree(pid)
        self._claude_pid = None
        self._proc = None

    # -- batch --------------------------------------------------------------
    def run_batch(self, batch_md: str, items: list[dict],
                  timeout_s: float) -> dict[str, Any] | None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        resp = Path(items[0]["response_path"])
        stamp = resp.stem.replace("_response", "")
        batch_path = DATA_DIR / f"{stamp}.md"
        batch_path.write_text(batch_md, encoding="utf-8")
        marker = f"GATE-{stamp}"
        posix = str(batch_path).replace("\\", "/")
        inj = subprocess.run(
            ["clp", "ai-eye", "--pid", str(self._claude_pid), "--inject",
             f"Leggi il file {posix} e segui le sue istruzioni alla lettera. [{marker}]",
             "--verify", marker, "--newline"],
            capture_output=True, text=True, timeout=60, shell=True,
            **quiet_popen_kwargs())
        if '"ok": true' not in (inj.stdout or "").lower():
            return None
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if resp.exists():
                try:
                    return json.loads(resp.read_text(encoding="utf-8"))
                except ValueError:
                    time.sleep(2)  # partially written — retry once the write settles
            time.sleep(3)
        return None


_judge: InteractiveJudge | None = None


def get_interactive_judge() -> InteractiveJudge:
    global _judge
    if _judge is None:
        _judge = InteractiveJudge()
    return _judge


def set_interactive_judge(judge: InteractiveJudge | None) -> None:
    global _judge
    _judge = judge


def reset_interactive_judge() -> None:
    set_interactive_judge(None)


def _close_singleton_at_exit() -> None:
    """atexit sweep: a process dying with a live judge must not leak its
    hidden sister. Best-effort — never raises during interpreter teardown."""
    j = _judge
    transport = getattr(j, "_transport", None) if j is not None else None
    close = getattr(transport, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # noqa: BLE001 — teardown must not explode
            pass


atexit.register(_close_singleton_at_exit)


def try_interactive_score(source: str, fact: str, *,
                          focus_budget: int | None = None) -> float | None:
    """Gate hook: span-select like the other backends, judge via the ghost sister;
    None when unavailable (caller falls back to the injected llm). Same claude 0-100
    scale as the -p judge — the claude-scale threshold applies."""
    from engram.grounding_gate import select_relevant_span
    budget = int(focus_budget) if focus_budget else 1500
    span = select_relevant_span(source or "", fact or "", budget=budget)
    try:
        return get_interactive_judge().score(span, fact or "")
    except Exception:  # noqa: BLE001
        return None


_ = re  # keep import surface stable for future marker parsing

__all__ = ["InteractiveJudge", "GhostSisterTransport", "get_interactive_judge",
           "set_interactive_judge", "reset_interactive_judge",
           "try_interactive_score"]
