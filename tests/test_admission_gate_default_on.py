"""0.7.0 flip: the admission gate is ON out of the box.

Decision record (2026-07-20, adversarial review GLM-5.2 + Kimi-K3, both
independent, convergent):
  - The measured pre-gate corpus trajectory (75% quarantined, 94% of it
    machine exhaust) is what any unprotected deployment drifts toward; a
    "verified memory" that admits machine exhaust as curated facts by
    default is a false claim. Hence default ON.
  - The flip must not be silent ("memory that decides for you without
    telling you is the opposite of verified memory" — Kimi): the first
    routed write in a process where the operator made NO explicit choice
    emits a one-time migration warning naming the opt-out.
  - An explicit choice (env set to any recognized value) means no
    migration warning: the operator already decided.
  - Content-based classification (JSON-shape sniffing) was REJECTED by
    both reviewers (false positives without undo, e.g. a calendar entry
    {"event_type": "dentist", ...}); routing stays topic-prefix only.
"""
from __future__ import annotations

import sqlite3
import warnings

import pytest

from verimem.semantic import Fact, SemanticMemory


def _count(db, sql):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def _no_explicit_choice(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)


def test_gate_on_by_default(monkeypatch, tmp_path):
    _no_explicit_choice(monkeypatch)
    import dataclasses

    import verimem.config as cfg
    monkeypatch.setattr(
        cfg, "CONFIG", dataclasses.replace(cfg.CONFIG, data_dir=str(tmp_path)))
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


@pytest.mark.parametrize("off", ["0", "off", "false", "no"])
def test_gate_explicit_off_wins(monkeypatch, off):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", off)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is False


@pytest.mark.parametrize("on", ["1", "on", "true", "strict"])
def test_gate_explicit_on_still_on(monkeypatch, on):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", on)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


def test_store_routes_telemetry_by_default(tmp_path, monkeypatch):
    _no_explicit_choice(monkeypatch)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired", topic="bus/ambient"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 1


def test_store_legacy_behavior_with_explicit_optout(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired", topic="bus/ambient"))
    assert _count(
        tmp_path / "s.db",
        "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 1


def test_first_route_without_explicit_choice_warns_once(tmp_path, monkeypatch):
    _no_explicit_choice(monkeypatch)
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick 1", topic="metric/cpu"))
        sm.store(Fact(proposition="tick 2", topic="metric/cpu2"))
    migration = [w for w in caught
                 if "ENGRAM_ADMISSION_GATE" in str(w.message)]
    assert len(migration) == 1, (
        "exactly one migration warning for the whole process, naming the "
        f"opt-out env var; got {len(migration)}")
    assert "telemetry" in str(migration[0].message).lower()


def test_no_migration_warning_when_choice_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick", topic="metric/cpu"))
    assert not [w for w in caught
                if "ENGRAM_ADMISSION_GATE" in str(w.message)]


@pytest.mark.parametrize("junk", ["maybe", "2", "yes-ish"])
def test_unrecognized_env_value_means_on(monkeypatch, junk):
    # Documented in the CHANGELOG: anything that is not an explicit OFF is ON.
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", junk)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


def test_unrecognized_env_value_gets_dedicated_warning(tmp_path, monkeypatch):
    # Round-2 review, both reviewers: ENGRAM_ADMISSION_GATE=disabled is the
    # intuitive first attempt at switching off — silent-ON would let the
    # operator believe they disabled it. They get told, once.
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "disabled")
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick", topic="metric/cpu"))
    hits = [w for w in caught if "not a recognized value" in str(w.message)]
    assert len(hits) == 1
    assert "'disabled'" in str(hits[0].message)
    # and the write WAS routed (unrecognized means ON)
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1


def test_public_receipt_tells_the_truth_about_routing(tmp_path, monkeypatch):
    # Found by the fresh-install product probe (2026-07-20): a routed write
    # returned {'stored': True, 'disposition': 'admitted', 'status':
    # 'model_claim'} — a receipt that lies about where the write went. The
    # public receipt must report what HAPPENED: the fact never entered the
    # curated corpus, it was routed.
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r = m.add("ambient daemon event fired at tick 42", topic="bus/probe")
    assert r["stored"] is True
    assert r["status"] == "routed_telemetry"
    assert r["routed_to"] == "telemetry"
    assert r["adjudication"]["disposition"] == "routed_telemetry"
    assert "routed" in r["adjudication"]["reason"]  # not the generic "rejected"
    # a real fact keeps the normal receipt
    r2 = m.add("our staging deploys run from the ci pipeline",
               topic="lessons/deploy")
    assert r2["status"] != "routed_telemetry"
    assert "routed_to" not in r2


def test_migration_message_names_the_route_table(monkeypatch):
    # Round-2 review, GLM: the episode path stores in episode_telemetry —
    # a hardcoded 'telemetry' query hint would be wrong there.
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ag.warn_default_on_migration_once(table="episode_telemetry")
    assert caught and "episode_telemetry" in str(caught[0].message)


def test_route_survives_warnings_promoted_to_errors(tmp_path, monkeypatch):
    # Review round 2, Kimi #9: under `python -W error` warnings.warn raises —
    # a migration courtesy must never break (or degrade) the write it
    # narrates. The route must complete; the courtesy is simply lost.
    _no_explicit_choice(monkeypatch)
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_MIGRATION_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sm.store(Fact(proposition="tick", topic="metric/cpu"))  # must not raise
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1
