"""TDD — recall-side denylist dei namespace di telemetria-macchina (scan 68-Opus, 2026-06-02).

Anche se un writer scrive telemetria come fact (bus/ metric/ alloc/ lock/ tx/ nego/ replay/
dialog/voice), recall() NON la deve MAI servire sul recall GENERICO (topic=None). Difesa
COMPLEMENTARE alla quarantena. ('test/' NON e' in denylist: i fixture usano topic='test/...').

AUDIT 2026-06-02 (2 agenti Opus):
 - 'emerging_skill/' RIMOSSO dalla denylist: e' conoscenza potenziale (skill auto-scoperte) ->
   gate via STATUS quarantine, non via topic.
 - asimmetria chiusa: la denylist ora vale in ENTRAMBI i path (cache fast-path E legacy SQL),
   ma SOLO per topic=None (un topic esplicito va servito).

HERMETIC: temp DB, zero side-effect sul DB reale.
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory

# NB: emerging_skill NON e' piu' qui (e' conoscenza, gestita dallo status).
_TELEMETRY_PREFIXES = ("bus/", "metric/", "alloc/", "lock/", "tx/", "nego/",
                       "replay/", "dialog/voice")

_BASE = "lezione importante sul recall semantico della memoria"
_Q = "lezione importante recall semantico memoria"


def _seed(m: SemanticMemory) -> None:
    m.store(Fact(id="real1", proposition=_BASE, topic="lessons/x", confidence=0.8))
    m.store(Fact(id="tel_bus", proposition=_BASE + " evento",
                 topic="bus/ambient_daemon/events", confidence=1.0))
    m.store(Fact(id="tel_metric", proposition=_BASE + " metrica",
                 topic="metric/event_x", confidence=1.0))
    m.store(Fact(id="tel_alloc", proposition=_BASE + " alloc",
                 topic="alloc/handle-1", confidence=1.0))


def test_recall_excludes_telemetry_cache_path(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(m)
    res = m.recall(_Q, k=10, topic=None)  # cache fast-path
    topics = [r[0].topic for r in res]
    leaked = [t for t in topics if t.startswith(_TELEMETRY_PREFIXES)]
    assert not leaked, f"telemetria servita dal cache-path: {leaked} (tutti: {topics})"
    assert "lessons/x" in topics


def test_recall_excludes_telemetry_legacy_path(tmp_path):
    # AUDIT: include_superseded=True forza il LEGACY SQL path. Prima la denylist
    # non c'era qui (asimmetria) -> la telemetria trapelava. Ora deve essere esclusa.
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(m)
    res = m.recall(_Q, k=10, topic=None, include_superseded=True)
    leaked = [r[0].topic for r in res if r[0].topic.startswith(_TELEMETRY_PREFIXES)]
    assert not leaked, f"telemetria trapelata dal LEGACY path: {leaked}"


def test_explicit_telemetry_topic_is_still_served(tmp_path):
    # Con un topic ESPLICITO la denylist NON si applica: chi chiede 'bus/...' lo vuole.
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(m)
    res = m.recall(_Q, k=10, topic="bus/ambient_daemon/events")
    topics = [r[0].topic for r in res]
    assert any(t.startswith("bus/") for t in topics), (
        f"un topic esplicito 'bus/...' deve essere servito: {topics}")


def test_emerging_skill_is_recallable(tmp_path):
    # AUDIT: emerging_skill RIMOSSO dalla denylist -> un fatto non-quarantined
    # con topic emerging_skill/ DEVE essere richiamabile (e' conoscenza).
    m = SemanticMemory(db_path=tmp_path / "s.db")
    m.store(Fact(id="real1", proposition=_BASE, topic="lessons/x", confidence=0.8))
    m.store(Fact(id="emerg1", proposition=_BASE + " skill emergente",
                 topic="emerging_skill/auto-discovered/foo", confidence=0.9))
    res = m.recall(_Q, k=10, topic=None)
    topics = [r[0].topic for r in res]
    assert any(t.startswith("emerging_skill/") for t in topics), (
        f"emerging_skill non-quarantined deve essere richiamabile: {topics}")


# --- 2026-06-13: extend the denylist with the machine-state/simulation blobs --
# EMPIRICAL trigger: a LIVE hippo_facts_recall surfaced cache/ market/ citations/
# JSON state blobs at score ~0.82, crowding out real knowledge ("serve davvero?"
# pain). The corpus histogram + per-namespace sampling (B2) confirmed these are
# serialized machine state, NOT natural-language knowledge. They must be denied
# on the generic recall exactly like bus/. ('test/', 'handoff/', 'bench/' are
# DELIBERATELY kept recallable — fixtures/mandates/benchmark knowledge.)
_MACHINE_STATE_PREFIXES = (
    "cache/", "market/", "citations/", "obs/", "signal/",
    "dispatch/", "supervisor/", "namespace/", "diary/",
)


def _seed_machine_state(m: SemanticMemory) -> None:
    m.store(Fact(id="real_k", proposition=_BASE, topic="lessons/y", confidence=0.8))
    for i, pfx in enumerate(_MACHINE_STATE_PREFIXES):
        m.store(Fact(id=f"ms_{i}", proposition=_BASE + f" stato {i}",
                     topic=pfx + "x/1779", confidence=1.0))


def test_recall_excludes_machine_state_blobs_cache_path(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed_machine_state(m)
    res = m.recall(_Q, k=20, topic=None)  # cache fast-path
    topics = [r[0].topic for r in res]
    leaked = [t for t in topics if t.startswith(_MACHINE_STATE_PREFIXES)]
    assert not leaked, f"machine-state served on generic recall (cache): {leaked}"
    assert "lessons/y" in topics, "real knowledge must still be recallable"


def test_recall_excludes_machine_state_blobs_legacy_path(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed_machine_state(m)
    res = m.recall(_Q, k=20, topic=None, include_superseded=True)  # legacy SQL path
    leaked = [r[0].topic for r in res if r[0].topic.startswith(_MACHINE_STATE_PREFIXES)]
    assert not leaked, f"machine-state leaked from legacy path: {leaked}"


def test_explicit_machine_state_topic_is_still_served(tmp_path):
    # A caller who explicitly asks for 'market/...' still gets it (generic-only denylist).
    m = SemanticMemory(db_path=tmp_path / "s.db")
    _seed_machine_state(m)
    res = m.recall(_Q, k=10, topic="market/x/1779")
    assert any(r[0].topic.startswith("market/") for r in res), (
        "an explicit machine-state topic must still be served")
