"""Cycle #150 (2026-05-19) — ``engram teams`` Typer subapp.

Due comandi:

* ``engram teams watch [--team-dir <p>] [--refresh-sec N] [--max-sec M]``
  — Tail dei messaggi inter-agent in tempo reale. Default è polling
  della directory standard ``~/.claude/teams/<team>/inboxes/``. La
  visualizzazione è semplice (echo per riga) — per una vista Rich Live
  full-screen color-coded esiste già ``engram lab live <topic>`` che
  legge SemanticMemory (richiede attivo il bridge ``mirror_message``).

* ``engram teams send --to <name> --as <human> --message "…"
  [--team-dir <p>]`` — Inietta un messaggio nell'inbox di un teammate
  scrivendo direttamente il file JSON. Permette a un operatore umano
  di partecipare alla chat agent-teams da una CLI esterna senza
  possedere una sessione Claude Code attiva.

Anti-pattern: NON ricostruiamo SendMessage qui — quello è il tool nativo
agent-teams disponibile a chi ha una sessione Claude Code lead/teammate.
``engram teams send`` è il "back-door umano": Aurelio appende al file
JSON, il supervisor Claude consegna il messaggio al destinatario alla
prossima delivery.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape as rich_escape

from .harness import CollabHarness
from .inbox import InboxWatcher
from .protocol import CHARTER_TEMPLATE

# Cycle 159.4 patch (alice+bob sonnet duo convergence) — colorize live
# messages by leading protocol tag, plus a voters-progress bar. The tag→
# color map covers both the cycle-159 charter tags and a handful of
# adjacent ones (DONE, CONCERN) the duo asked for during the dibattito;
# unknown tags fall through to ``white`` and untagged prose to ``dim``.
_console = Console()
_TAG_COLORS = {
    "CLAIM": "blue",
    "BLOCK": "red",
    "BLOCKED": "red",
    "VOTE-CONVERGED": "green",
    "QUESTION": "yellow",
    "DONE": "green",
    "CONCERN": "magenta",
    "REFER": "cyan",
}
_TAG_RE = re.compile(
    r"\[(CLAIM|BLOCK(?:ED)?|VOTE-CONVERGED|QUESTION|DONE|CONCERN|REFER)\]",
    re.IGNORECASE,
)


def _msg_color(text: str) -> str:
    """Return the rich color associated with the FIRST protocol tag in
    ``text``, or ``"dim"`` if no tag is found.

    Searches the entire text (not a truncated prefix) so a tag deep in
    a long message still drives the color — bug bob caught at round 2.
    """
    m = _TAG_RE.search(text)
    if not m:
        return "dim"
    return _TAG_COLORS.get(m.group(1).upper(), "white")

teams_app = typer.Typer(
    help="Agent-teams Mailbox bridge: watch + send messages + collab-test",
    no_args_is_help=True,
)


def _now_iso() -> str:
    """Return the current UTC time in the same ISO8601 ms format Anthropic uses."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# === Inbox read-modify-write: atomic + lock-guarded (cycle 2026-06-05) ======
# `engram teams send` appends to <team_dir>/inboxes/<to>.json. The original
# code did read_json -> append -> write_json with NO serialization: two
# concurrent sends to the SAME teammate (the normal swarm case — many teammates
# messaging one coordinator) both read the same array, each appended its own
# message, and the LAST write overwrote the other = a silently LOST message. A
# torn read (a reader hitting a half-written file) also silently reset the inbox
# to []. Fix: serialize the read-modify-write with a BOUNDED cross-platform file
# lock, and make the write atomic (temp + os.replace) so a concurrent reader
# never sees a partial file.
_INBOX_LOCK_TIMEOUT_S = 5.0   # max wait for the lock — BOUNDED (no-hang posture)
_INBOX_LOCK_STALE_S = 30.0    # steal a lock file older than this (crashed holder)


@contextlib.contextmanager
def _inbox_lock(inbox: Path):
    """BOUNDED cross-platform exclusive lock on one inbox file.

    Uses an O_CREAT|O_EXCL lock file (atomic create on Windows + POSIX). Waits
    at most _INBOX_LOCK_TIMEOUT_S, then proceeds WITHOUT the lock rather than
    blocking forever — a rare lost update beats a hung `send` (same posture as
    the embedding model-lock timeout). A lock file older than _INBOX_LOCK_STALE_S
    (a crashed holder) is stolen.
    """
    lock_path = inbox.with_name(inbox.name + ".lock")
    fd: int | None = None
    start = time.monotonic()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except (FileExistsError, PermissionError):
            # FileExistsError = lock held (POSIX + Windows). On Windows a held or
            # pending-delete lock file surfaces as PermissionError (sharing
            # violation) instead — treat both as "contended": stale-break by age,
            # else bounded wait.
            try:
                age = time.time() - os.path.getmtime(lock_path)
            except OSError:
                age = 0.0
            if age > _INBOX_LOCK_STALE_S:
                with contextlib.suppress(OSError):
                    os.unlink(lock_path)
                continue
            if time.monotonic() - start >= _INBOX_LOCK_TIMEOUT_S:
                break  # bounded: proceed unlocked rather than hang
            time.sleep(0.02)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
            with contextlib.suppress(OSError):
                os.unlink(lock_path)


def _read_inbox(inbox: Path) -> list[dict]:
    """Read the inbox JSON array; [] if absent / empty / corrupt."""
    if not inbox.is_file():
        return []
    try:
        raw = inbox.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return []
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _atomic_write_json(path: Path, data: list[dict]) -> None:
    """Write ``data`` to ``path`` atomically (unique temp file + os.replace).

    The temp file is created via ``tempfile.mkstemp`` in the destination dir so
    it is unique per writer (a per-pid name collides across threads of one
    process). Retries os.replace on PermissionError: on Windows replace fails
    while a reader (e.g. the inbox watcher) momentarily holds the destination
    open — bounded (~0.5s) then a final attempt that surfaces a real failure.
    """
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2))
        for _ in range(50):
            try:
                os.replace(tmp_name, str(path))
                return
            except PermissionError:
                time.sleep(0.01)
        os.replace(tmp_name, str(path))  # final attempt — raise if truly stuck
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def append_to_inbox(team_dir: Path, to: str, as_: str, message: str) -> Path:
    """Append one message to ``<team_dir>/inboxes/<to>.json`` as an atomic,
    lock-guarded read-modify-write. Returns the inbox path.

    Concurrency-safe (the swarm coordinator case): the lock serializes the
    read+append+write and the write is atomic, so no message is lost and no
    reader observes a torn file.
    """
    inbox = team_dir / "inboxes" / f"{to}.json"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    with _inbox_lock(inbox):
        existing = _read_inbox(inbox)
        existing.append({
            "from": as_,
            "text": message,
            "timestamp": _now_iso(),
            "read": False,
        })
        _atomic_write_json(inbox, existing)
    return inbox


@teams_app.command("send")
def send_cmd(
    team_dir: Path = typer.Option(  # noqa: B008 — typer convention
        ..., "--team-dir",
        help="Team directory (typically ~/.claude/teams/<name>).",
    ),
    to: str = typer.Option(
        ..., "--to",
        help="Recipient teammate name (filename in inboxes/, no .json).",
    ),
    as_: str = typer.Option(
        ..., "--as",
        help="Sender display name (free-form, e.g. 'aurelio').",
    ),
    message: str = typer.Option(
        ..., "--message",
        help="Message text. Use a heredoc for multi-line input.",
    ),
) -> None:
    """Append one message to the recipient inbox JSON file."""
    inbox = append_to_inbox(team_dir, to, as_, message)
    typer.echo(f"sent {len(message)} chars to {to} ({inbox})")


@teams_app.command("watch")
def watch_cmd(
    team_dir: Path = typer.Option(  # noqa: B008 — typer convention
        ..., "--team-dir",
        help="Team directory (typically ~/.claude/teams/<name>).",
    ),
    refresh_sec: float = typer.Option(
        0.5, "--refresh-sec",
        help="Polling interval seconds (default 0.5).",
    ),
    max_sec: float = typer.Option(
        0.0, "--max-sec",
        help="Auto-exit after N seconds (0 = run until Ctrl-C).",
    ),
    include_idle: bool = typer.Option(
        False, "--include-idle/--no-include-idle",
        help="Show idle_notification system messages (default: hide).",
    ),
    mirror_to_memory: bool = typer.Option(
        False, "--mirror-to-memory/--no-mirror-to-memory",
        help="Mirror new messages to HippoAgent Fact "
             "(topic 'lab/teams/<team_dir.name>'). Closes the cycle 150 "
             "gap — without this flag messages are volatile.",
    ),
    mirror_include_idle: bool = typer.Option(
        False, "--mirror-include-idle/--no-mirror-include-idle",
        help="When mirroring, also persist idle_notification (default: skip).",
    ),
) -> None:
    """Tail teammates' inboxes. New messages printed one per line."""
    watcher = InboxWatcher(team_dir=team_dir)
    deadline = time.time() + max_sec if max_sec > 0 else None

    # Banner: rende ovvio che il watcher è partito e sta pollando, anche
    # quando ``inboxes/`` non esiste ancora (tipico al momento della
    # creazione del team — la cartella nasce al primo SendMessage).
    inbox_dir = team_dir / "inboxes"
    inbox_status = (
        "exists"
        if inbox_dir.is_dir()
        else "NOT yet created — apparirà al primo messaggio"
    )
    typer.echo(f"[watch] team_dir = {team_dir}")
    typer.echo(f"[watch] inboxes dir: {inbox_status}")
    typer.echo(
        f"[watch] polling every {refresh_sec}s, "
        f"include_idle={include_idle}. Ctrl-C per uscire.",
    )

    # Lazy-import the bridge — only pay the SemanticMemory cost when the
    # operator actually asks for persistence. Keeps ``watch`` cheap for
    # simple terminal tailing.
    sm = None
    team_name = team_dir.name
    if mirror_to_memory:
        from ..semantic import SemanticMemory
        from .bridge import mirror_message as _mirror
        sm = SemanticMemory()
        typer.echo(
            f"[watch] mirror_to_memory ENABLED — "
            f"topic 'lab/teams/{team_name}', include_idle={mirror_include_idle}",
        )

    typer.echo("[watch] --- waiting for messages ---")

    last_heartbeat = time.time()
    heartbeat_interval = 5.0

    while True:
        if deadline is not None and time.time() >= deadline:
            typer.echo("[watch] deadline raggiunto, exit.")
            return
        try:
            new_msgs = watcher.poll(include_idle=include_idle)
        except Exception as exc:  # noqa: BLE001 — defensive: never die mid-tail
            typer.echo(f"[watch error] {exc}")
            new_msgs = []
        for m in new_msgs:
            tag = "[IDLE]" if m.is_idle_notification else ""
            snippet = m.text.replace("\n", " ")[:200]
            typer.echo(f"{tag}[{m.sender} -> {m.recipient}] {snippet}")
            if mirror_to_memory and sm is not None:
                try:
                    _mirror(
                        m, sm=sm, team_name=team_name,
                        include_idle=mirror_include_idle,
                    )
                except Exception as exc:  # noqa: BLE001 — never die mid-tail
                    typer.echo(f"[mirror error] {exc}")
        # Heartbeat dot ogni ``heartbeat_interval`` secondi quando la
        # chat è silenziosa, così il watcher sembra vivo all'utente.
        if not new_msgs and (time.time() - last_heartbeat) >= heartbeat_interval:
            typer.echo(
                f"[watch] ... {time.strftime('%H:%M:%S')} (still polling)",
            )
            last_heartbeat = time.time()
        time.sleep(refresh_sec)


@teams_app.command("charter")
def charter_cmd() -> None:
    """Print the Real-Collaboration Charter (cycle 159).

    Paste it verbatim into a teammate's system-prompt / role to enable
    the [CLAIM]/[QUESTION]/[VOTE-CONVERGED] tag protocol that
    ``engram teams collab-test`` measures.
    """
    typer.echo(CHARTER_TEMPLATE)


@teams_app.command("collab-test")
def collab_test_cmd(
    team_dir: Path = typer.Option(  # noqa: B008 — typer convention
        ..., "--team-dir",
        help="Team directory (typically ~/.claude/teams/<name>).",
    ),
    members: str = typer.Option(
        ..., "--members",
        help="Comma-separated teammate names (filename stems under inboxes/).",
    ),
    max_min: float = typer.Option(
        10.0, "--max-min",
        help="Hard upper bound on the test in minutes. Default 10.",
    ),
    refresh_sec: float = typer.Option(
        0.5, "--refresh-sec",
        help="Polling interval seconds.",
    ),
    report_every_sec: float = typer.Option(
        15.0, "--report-every-sec",
        help="Emit a partial report every N seconds.",
    ),
    deadlock_after_sec: float = typer.Option(
        120.0, "--deadlock-after-sec",
        help="Declare deadlock after N seconds of silence.",
    ),
) -> None:
    """Cycle 159: empirical-collaboration test.

    Watches a team's inboxes, classifies every message via the cycle-159
    tag protocol, and prints a compact running report. Exits when the
    team converges, deadlocks, or the wall-clock budget is exhausted.

    The exit code is the kind of result:
      0 — converged (success)
      2 — deadlocked
      3 — timeout (max_min hit before convergence/deadlock)
    """
    member_list = [m.strip() for m in members.split(",") if m.strip()]
    if not member_list:
        typer.echo("[collab-test] no members parsed — pass --members alice,bob")
        raise typer.Exit(code=64)

    h = CollabHarness(
        team_dir=team_dir,
        members=member_list,
        deadlock_after_sec=deadlock_after_sec,
    )
    deadline = time.time() + max_min * 60.0
    next_report = time.time() + report_every_sec

    typer.echo(
        f"[collab-test] team_dir={team_dir} members={member_list} "
        f"max_min={max_min} report_every_sec={report_every_sec}",
    )
    typer.echo("[collab-test] tail starts — Ctrl-C to abort early.")

    while True:
        if time.time() >= deadline:
            r = h.report()
            typer.echo(f"[collab-test] TIMEOUT — final report: {json.dumps(r)}")
            raise typer.Exit(code=3)

        try:
            new_msgs = h.poll()
        except Exception as exc:  # noqa: BLE001 — never die mid-poll
            typer.echo(f"[collab-test error] {exc}")
            new_msgs = []
        for m in new_msgs:
            # Cycle 159.4: colorize by leading protocol tag. rich.markup.escape
            # on sender/recipient prevents a literal '[' in a teammate name
            # (e.g. 'alice[bot]') from crashing the markup parser — fix
            # bob caught during round-2 dibattito.
            color = _msg_color(m.text)
            snippet = m.text.replace("\n", " ")[:200]
            _console.print(
                f"  [{color}]\\[{rich_escape(m.sender)} -> "
                f"{rich_escape(m.recipient)}][/] {snippet}",
            )

        if h.converged:
            r = h.report()
            typer.echo(f"[collab-test] CONVERGED — final report: {json.dumps(r)}")
            raise typer.Exit(code=0)

        if h.is_deadlocked():
            r = h.report()
            typer.echo(f"[collab-test] DEADLOCK — final report: {json.dumps(r)}")
            raise typer.Exit(code=2)

        if time.time() >= next_report:
            r = h.report()
            # Cycle 159.4 progress bar: distinct VOTERS (not raw vote count) —
            # this matches CollabHarness.converged which is len(voters) ≥
            # (N//2)+1. Using ``votes_converged`` (raw tag count) would
            # over-inflate when a teammate emits multiple VOTE tags. This
            # semantic correction overrides alice+bob's numerator choice;
            # surfaced when applying the patch to the real harness API.
            voters_n = len(r["voters"])
            total_n = max(1, len(member_list))
            filled = "█" * voters_n
            empty = "░" * max(0, total_n - voters_n)
            pct = int(voters_n / total_n * 100)
            blocked_flag = " [red]BLOCKED[/]" if r["blocked"] > 0 else ""
            _console.print(
                f"  [{filled}{empty}] {voters_n}/{total_n} converged ({pct}%)"
                f"  msgs={r['total_msgs']} claims={r['claims']} "
                f"q={r['questions']} refers={r['refers']}{blocked_flag}",
            )
            next_report = time.time() + report_every_sec

        time.sleep(refresh_sec)
