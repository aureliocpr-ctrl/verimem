"""0.7.0 admission-gate defaults — the contract after the external bench.

Decision record, three rounds (2026-07-20):
  R1 (design): flip everything ON — GLM-5.2 + Kimi-K3 demanded observability
     and rejected content-based classification.
  R2 (diff): latch/thread/table fixes.
  R3 (external bench, scripts/bench_admission_external_corpora.py): on TWO
     foreign-domain corpora the prefix routing scored ~10% knowledge false
     positives (cache/ricette, metric/kpi-churn, ...) with telemetry recall
     0.0 — Kimi's structural argument: for anyone who is not us the prefix
     list can only hurt (cost > 0, benefit = 0 by construction). Both
     reviewers independently converged on caller-declared intent.

Contract shipped here:
  - INTEGRITY screening (markup / injection / low-provenance / duplicate)
    stays ON by default (ENGRAM_ADMISSION_GATE, 0 turns everything off).
    Content FP measured 0/500 on TruthfulQA+HaluEval — an upper-bound-free
    claim is NOT made: hostile-shaped-legitimate bench is roadmap.
  - TELEMETRY ROUTING is opt-in and declarative:
      * env ENGRAM_TELEMETRY_PREFIXES — unset: NO routing (public default);
        comma-separated, case-insensitive startswith; the keyword `builtin`
        expands to our own stack's list and composes ("builtin,mqtt/").
      * add(purpose="telemetry") — the writer declares intent; routes
        regardless of topic. Default None = knowledge = never routed by
        name. (GLM origin-tag + Kimi channel-tag, made non-breaking.)
  - The first ACTUAL route in a process still warns once, naming the table.
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


def _clean(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    monkeypatch.delenv("ENGRAM_TELEMETRY_PREFIXES", raising=False)


# ---------- gate (integrity) default ------------------------------------


def test_gate_on_by_default(monkeypatch, tmp_path):
    _clean(monkeypatch)
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


@pytest.mark.parametrize("junk", ["maybe", "2", "yes-ish"])
def test_unrecognized_env_value_means_on(monkeypatch, junk):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", junk)
    from verimem.admission_gate import gate_enabled
    assert gate_enabled() is True


# ---------- routing is declarative --------------------------------------


def test_no_route_without_declared_prefixes(tmp_path, monkeypatch):
    # The public default: a bus/ topic is a NAME, not a verdict. External
    # bench: on foreign corpora the builtin list only made false positives.
    _clean(monkeypatch)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="orario del bus 12 per il centro alle 7:40",
                  topic="bus/orari"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic='bus/orari'") == 1
    try:
        n = _count(db, "SELECT COUNT(*) FROM telemetry")
    except sqlite3.OperationalError:
        n = 0
    assert n == 0


def test_builtin_prefixes_route(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="ambient daemon event fired", topic="bus/ambient"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic LIKE 'bus/%'") == 0
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 1


def test_custom_prefixes_compose_with_builtin(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin, mqtt/")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="mqtt broker heartbeat", topic="mqtt/broker1"))
    sm.store(Fact(proposition="bus event tick", topic="bus/x"))
    sm.store(Fact(proposition="preferenza utente: caffe' senza zucchero",
                  topic="preferences/coffee"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 2
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic='preferences/coffee'") == 1


def test_custom_only_prefixes_do_not_include_builtin(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "mqtt/")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="bus event tick", topic="bus/x"))
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic='bus/x'") == 1


def test_prefix_match_is_case_insensitive(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "MQTT/")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="mqtt heartbeat", topic="mqtt/b"))
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1


# ---------- origin-tag: the writer declares intent ----------------------


def test_purpose_telemetry_routes_regardless_of_topic(tmp_path, monkeypatch):
    _clean(monkeypatch)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition='{"event_type":"tick","ts":1}',
                  topic="anything/at-all"), purpose="telemetry")
    db = tmp_path / "s.db"
    assert _count(db, "SELECT COUNT(*) FROM telemetry") == 1
    assert _count(db, "SELECT COUNT(*) FROM facts WHERE topic='anything/at-all'") == 0


def test_purpose_default_is_knowledge_even_on_trap_topics(tmp_path, monkeypatch):
    _clean(monkeypatch)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="raccolta: ricetta della carbonara di nonna",
                  topic="cache/ricette"))
    assert _count(tmp_path / "s.db",
                  "SELECT COUNT(*) FROM facts WHERE topic='cache/ricette'") == 1


def test_gate_off_disables_routing_too(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "0")
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="bus tick", topic="bus/x"))
    assert _count(tmp_path / "s.db",
                  "SELECT COUNT(*) FROM facts WHERE topic='bus/x'") == 1


# ---------- first-route warning -----------------------------------------


def test_first_route_warns_once(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin")
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_ROUTE_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sm.store(Fact(proposition="tick 1", topic="metric/cpu"))
        sm.store(Fact(proposition="tick 2", topic="metric/cpu2"))
    hits = [w for w in caught if "telemetry" in str(w.message).lower()
            and "routed" in str(w.message).lower()]
    assert len(hits) == 1
    assert "SELECT * FROM telemetry" in str(hits[0].message)


def test_route_survives_warnings_promoted_to_errors(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin")
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_ROUTE_WARNED", False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sm.store(Fact(proposition="tick", topic="metric/cpu"))  # must not raise
    assert _count(tmp_path / "s.db", "SELECT COUNT(*) FROM telemetry") == 1


def test_route_message_names_the_route_table(monkeypatch):
    _clean(monkeypatch)
    import verimem.admission_gate as ag
    monkeypatch.setattr(ag, "_ROUTE_WARNED", False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ag.warn_first_route_once(table="episode_telemetry")
    assert caught and "episode_telemetry" in str(caught[0].message)


# ---------- public receipt ----------------------------------------------


def test_public_receipt_tells_the_truth_about_routing(tmp_path, monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("ENGRAM_TELEMETRY_PREFIXES", "builtin")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r = m.add("ambient daemon event fired at tick 42", topic="bus/probe")
    assert r["stored"] is True
    assert r["status"] == "routed_telemetry"
    assert r["routed_to"] == "telemetry"
    assert r["adjudication"]["disposition"] == "routed_telemetry"
    assert "routed" in r["adjudication"]["reason"]
    r2 = m.add("our staging deploys run from the ci pipeline",
               topic="lessons/deploy")
    assert r2["status"] != "routed_telemetry"
    assert "routed_to" not in r2


def test_client_add_purpose_telemetry(tmp_path, monkeypatch):
    _clean(monkeypatch)
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r = m.add('{"event_type":"sync","ts":9}', topic="calendar/sync-log",
              purpose="telemetry")
    assert r["status"] == "routed_telemetry"
    assert _count(tmp_path / "m.db", "SELECT COUNT(*) FROM telemetry") == 1
