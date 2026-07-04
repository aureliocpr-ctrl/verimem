"""Cycle 159 (2026-05-19 05:18 Roma) — protocol+harness RED tests.

OBJECTIVE cycle 159: portare i team agent-teams da "broadcast log" a
**vera collaborazione misurabile**. Definiamo un protocollo testuale
minimale (tag-based) che ogni teammate include nei suoi messaggi, e un
``CollabHarness`` che classifica i messaggi in flight, rileva convergence,
deadlock e produce un report empirico.

Tag convention (cycle 159 charter)::

    [CLAIM] <asserzione fattuale, deve essere verificabile>
    [QUESTION] <dissenso o richiesta chiarimento ad altro teammate>
    [VOTE-CONVERGED] <reasoning breve di chi vota convergence>
    [BLOCKED] <ragione blocco>
    [REFER] <fact_id|episode_id> <topic> — link a memoria HippoAgent

I tag sono case-insensitive, multi-line, e possono comparire più volte
nello stesso messaggio. Il parser è permissivo (no schema rigido) per
non spezzare quando il modello varia spacing/punctuation.

Convergence rule cycle 159 §3:
  Un team è "converged" quando ``≥ ceil(N/2)+1`` membri (maggioranza
  semplice) hanno emesso almeno un [VOTE-CONVERGED] nella finestra
  corrente, dove N = len(members) attivi.

Deadlock rule cycle 159 §4:
  Un team è "deadlocked" quando zero messaggi non-idle entrano nel
  watcher per ``deadlock_after_sec`` (default 120). Diverso da
  converged: deadlock = stuck, converged = chiusura sana.

Test sotto sono RED finché ``engram/teams/protocol.py`` +
``engram/teams/harness.py`` non esistono o non implementano l'API.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

# -----------------------------------------------------------------------
# parse_protocol_tags
# -----------------------------------------------------------------------


def test_parse_protocol_tags_extracts_claim() -> None:
    from engram.teams.protocol import parse_protocol_tags
    tags = parse_protocol_tags(
        "[CLAIM] _persist_master at consolidation.py:240 takes 3 args.",
    )
    assert "claim" in tags
    assert any("_persist_master" in c for c in tags["claim"]), tags


def test_parse_protocol_tags_extracts_multiple() -> None:
    from engram.teams.protocol import parse_protocol_tags
    msg = (
        "[CLAIM] bug A at line 50.\n"
        "[QUESTION] @bob, agree on the lock placement?\n"
        "[REFER] fact_id=abc123 topic=lessons/lock-pattern\n"
        "[VOTE-CONVERGED] CLAIM verified empirically; closing.\n"
    )
    tags = parse_protocol_tags(msg)
    assert len(tags["claim"]) == 1
    assert len(tags["question"]) == 1
    assert len(tags["refer"]) == 1
    assert len(tags["vote-converged"]) == 1


def test_parse_protocol_tags_case_insensitive() -> None:
    from engram.teams.protocol import parse_protocol_tags
    tags = parse_protocol_tags("[claim] lower works\n[Question] mixed works")
    assert tags["claim"] and tags["question"]


def test_parse_protocol_tags_empty_when_no_tags() -> None:
    from engram.teams.protocol import parse_protocol_tags
    tags = parse_protocol_tags("just regular prose, no tags at all")
    # Returned dict exists but all categories are empty lists.
    for v in tags.values():
        assert v == [], tags


def test_charter_template_mentions_anticonfab_and_hippo() -> None:
    """Charter content gate: must instruct anti-confab + HippoAgent consult."""
    from engram.teams.protocol import CHARTER_TEMPLATE
    s = CHARTER_TEMPLATE.lower()
    assert "anti-confab" in s or "anti-confabul" in s, s[:200]
    assert "hippo" in s, s[:200]
    assert "[claim]" in s
    assert "[vote-converged]" in s


# -----------------------------------------------------------------------
# CollabHarness fixture helpers
# -----------------------------------------------------------------------


def _seed_inbox(team_dir: Path, recipient: str, msgs: list[dict]) -> None:
    inboxes = team_dir / "inboxes"
    inboxes.mkdir(parents=True, exist_ok=True)
    (inboxes / f"{recipient}.json").write_text(
        json.dumps(msgs, indent=2), encoding="utf-8",
    )


def _msg(sender: str, text: str, ts_offset: float = 0.0) -> dict:
    return {
        "from": sender,
        "text": text,
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%S.000Z",
            time.gmtime(time.time() + ts_offset),
        ),
        "read": False,
    }


# -----------------------------------------------------------------------
# CollabHarness
# -----------------------------------------------------------------------


def test_harness_classifies_messages_by_tag(tmp_path: Path) -> None:
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-team"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[CLAIM] line 50 is buggy"),
        _msg("bob", "[QUESTION] @alice agree?"),
    ])
    _seed_inbox(team_dir, "bob", [
        _msg("alice", "[CLAIM] empirically verified"),
        _msg("alice", "[VOTE-CONVERGED] all checks pass"),
    ])

    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    r = h.report()
    assert r["total_msgs"] == 4
    assert r["claims"] == 2
    assert r["questions"] == 1
    assert r["votes_converged"] == 1
    assert r["senders"] == {"alice": 2, "bob": 2}


def test_harness_converged_majority_rule(tmp_path: Path) -> None:
    """≥ ceil(N/2)+1 distinct senders must emit [VOTE-CONVERGED]."""
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-converge"
    # 3-member team, need ceil(3/2)+1 = 2+1 = 3 votes (full consensus).
    # Wait — ceil(3/2) = 2; +1 = 3. So with 3 members, need 3.
    # Reformulate to "strictly more than half": (N//2)+1. For N=3 → 2.
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[VOTE-CONVERGED] done"),
        _msg("carol", "[VOTE-CONVERGED] agree"),
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob", "carol"])
    h.poll()
    assert h.converged is True, h.report()


def test_harness_not_converged_when_only_one_voter(tmp_path: Path) -> None:
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-no-converge"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[VOTE-CONVERGED] solo vote"),
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob", "carol"])
    h.poll()
    assert h.converged is False, h.report()


def test_harness_deadlock_after_silence(tmp_path: Path) -> None:
    """Deadlock = no new messages for ``deadlock_after_sec``."""
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-deadlock"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[CLAIM] something", ts_offset=-300),
    ])
    h = CollabHarness(
        team_dir=team_dir,
        members=["alice", "bob"],
        deadlock_after_sec=60.0,
    )
    h.poll()
    # First poll: we have 1 message, last activity = now. Not deadlocked yet.
    # Simulate elapsed time by injecting an explicit "now".
    assert h.is_deadlocked(now=time.time()) is False
    # Now jump 120s into the future with no new messages.
    assert h.is_deadlocked(now=time.time() + 120) is True


def test_harness_report_shape(tmp_path: Path) -> None:
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-report"
    _seed_inbox(team_dir, "alice", [_msg("bob", "[CLAIM] x")])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    r = h.report()
    for k in ("total_msgs", "claims", "questions", "votes_converged",
              "blocked", "refers", "senders", "converged", "deadlocked",
              "elapsed_sec"):
        assert k in r, f"missing key {k!r} in report: {r}"


def test_harness_idle_notifications_dont_inflate_counts(tmp_path: Path) -> None:
    """idle_notification JSON envelopes are not real claims/questions."""
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-idle"
    idle_envelope = json.dumps({
        "type": "idle_notification",
        "from": "bob",
        "timestamp": "2026-05-19T05:00:00.000Z",
        "idleReason": "available",
    })
    _seed_inbox(team_dir, "alice", [
        _msg("bob", idle_envelope),
        _msg("bob", "[CLAIM] real claim"),
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    r = h.report()
    assert r["total_msgs"] == 1, r  # idle filtered out
    assert r["claims"] == 1, r


def test_harness_refer_links_collected(tmp_path: Path) -> None:
    """[REFER] entries pointing to HippoAgent fact/episode are collected."""
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "harness-refer"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[REFER] fact_id=abc123 topic=lessons/lock-pattern"),
        _msg("bob", "[REFER] episode_id=ep999 topic=project/x"),
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    r = h.report()
    assert r["refers"] == 2, r


# -----------------------------------------------------------------------
# CLI smoke
# -----------------------------------------------------------------------


def test_cli_charter_prints_template() -> None:
    from typer.testing import CliRunner

    from engram.teams.cli import teams_app
    res = CliRunner().invoke(teams_app, ["charter"])
    assert res.exit_code == 0
    assert "[CLAIM]" in res.stdout
    assert "[VOTE-CONVERGED]" in res.stdout


def test_cli_collab_test_converged_exit_0(tmp_path: Path) -> None:
    """CLI exits 0 when the team already converged on first poll."""
    from typer.testing import CliRunner

    from engram.teams.cli import teams_app

    team_dir = tmp_path / "cli-team"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[VOTE-CONVERGED] all done"),
        _msg("carol", "[VOTE-CONVERGED] confirmed"),
    ])

    res = CliRunner().invoke(
        teams_app,
        [
            "collab-test",
            "--team-dir", str(team_dir),
            "--members", "alice,bob,carol",
            "--max-min", "0.05",  # 3s upper bound
            "--refresh-sec", "0.1",
            "--report-every-sec", "60",
            "--deadlock-after-sec", "60",
        ],
    )
    # Strict-majority: 3 members → need 2 votes. We have 2 distinct.
    assert res.exit_code == 0, (res.exit_code, res.stdout)
    assert "CONVERGED" in res.stdout


def test_cli_collab_test_timeout_exit_3(tmp_path: Path) -> None:
    """CLI exits 3 on hard timeout when nobody speaks."""
    from typer.testing import CliRunner

    from engram.teams.cli import teams_app

    team_dir = tmp_path / "cli-team-timeout"
    # No inbox files at all → harness polls forever.
    (team_dir).mkdir(parents=True, exist_ok=True)
    res = CliRunner().invoke(
        teams_app,
        [
            "collab-test",
            "--team-dir", str(team_dir),
            "--members", "alice,bob",
            "--max-min", "0.02",  # ~1.2s
            "--refresh-sec", "0.1",
            "--report-every-sec", "60",
            "--deadlock-after-sec", "9999",  # avoid deadlock branch
        ],
    )
    assert res.exit_code == 3, (res.exit_code, res.stdout)
    assert "TIMEOUT" in res.stdout


# -----------------------------------------------------------------------
# Cycle 159.4 patch — _msg_color (alice+bob sonnet duo convergence)
# -----------------------------------------------------------------------


def test_msg_color_red_for_block() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("[BLOCK] cannot proceed without X") == "red"
    assert _msg_color("[BLOCKED] need clarification") == "red"


def test_msg_color_green_for_vote_converged() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("[VOTE-CONVERGED] all checks pass") == "green"


def test_msg_color_blue_for_claim() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("[CLAIM] verified at file:line") == "blue"


def test_msg_color_yellow_for_question() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("[QUESTION] @alice agree on X?") == "yellow"


def test_msg_color_dim_when_no_tag() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("plain prose without any tag") == "dim"
    assert _msg_color("") == "dim"


def test_msg_color_finds_tag_deep_in_text() -> None:
    """Bug bob caught in round 2: tag may appear AFTER the [:200] cutoff."""
    from engram.teams.cli import _msg_color
    deep_text = ("x" * 250) + "\n[BLOCK] late but real"
    assert _msg_color(deep_text) == "red"


def test_msg_color_case_insensitive_tag() -> None:
    from engram.teams.cli import _msg_color
    assert _msg_color("[claim] lowercase still classifies") == "blue"
    assert _msg_color("[Vote-Converged] mixed case ok") == "green"


# -----------------------------------------------------------------------
# Cycle 159.5 opus-review fixes — stall detection + outsider guard
# -----------------------------------------------------------------------


def test_outsider_vote_does_not_drive_convergence(tmp_path: Path) -> None:
    """Opus-review #3c: a sender not in `members` cannot count toward
    convergence even when they emit [VOTE-CONVERGED].
    """
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "outsider-team"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[VOTE-CONVERGED] legit"),
        _msg("eve", "[VOTE-CONVERGED] spoof"),  # eve NOT in members
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    # Need both alice+bob (N=2 → threshold (N//2)+1 = 2). bob is in,
    # eve is out. So converged must be False because we only have 1
    # legit voter (bob).
    assert h.converged is False, h.report()
    r = h.report()
    assert "bob" in r["voters"]
    assert "eve" not in r["voters"]
    assert r["outsider_voters"] == ["eve"]


def test_outsider_vote_still_recorded_in_report(tmp_path: Path) -> None:
    """Outsiders are tracked separately so the operator can see spoof
    attempts without polluting the convergence count.
    """
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "outsider-trace"
    _seed_inbox(team_dir, "alice", [
        _msg("eve", "[VOTE-CONVERGED] off-team"),
    ])
    h = CollabHarness(team_dir=team_dir, members=["alice", "bob"])
    h.poll()
    assert h.report()["outsider_voters"] == ["eve"]


def test_stalled_members_lists_silent_teammates(tmp_path: Path) -> None:
    """Opus-review #3a: ``stalled_members(thr)`` exposes who hasn't
    spoken in ``thr`` seconds. With default thr = deadlock_after_sec/2.
    """
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "stall-team"
    # bob talks, alice doesn't.
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[CLAIM] something"),
    ])
    h = CollabHarness(
        team_dir=team_dir, members=["alice", "bob"],
        deadlock_after_sec=10.0,
    )
    # Force-rewind harness `_started_at` 1h into the past so that alice
    # (who has no `_last_seen` entry) appears stalled even with a small
    # positive threshold. Doing this *before* poll() also keeps bob's
    # stamp fresh (`time.time()` post-poll).
    h._started_at = time.time() - 3600.0  # noqa: SLF001 — test surgery
    h.poll()
    # threshold=10s: alice last seen = _started_at (1h ago) → stalled.
    # bob last seen ≈ now (just polled) → not stalled.
    stalled_now = h.stalled_members(threshold_sec=10.0)
    assert "alice" in stalled_now, stalled_now
    assert "bob" not in stalled_now, stalled_now


def test_stalled_members_empty_when_everyone_recent(tmp_path: Path) -> None:
    from engram.teams.harness import CollabHarness
    team_dir = tmp_path / "stall-fresh"
    _seed_inbox(team_dir, "alice", [
        _msg("bob", "[CLAIM] hi"),
    ])
    _seed_inbox(team_dir, "bob", [
        _msg("alice", "[CLAIM] hi back"),
    ])
    h = CollabHarness(
        team_dir=team_dir, members=["alice", "bob"],
        deadlock_after_sec=600.0,
    )
    h.poll()
    # Both spoke, threshold is large → nobody stalled.
    assert h.stalled_members() == [], h.report()
