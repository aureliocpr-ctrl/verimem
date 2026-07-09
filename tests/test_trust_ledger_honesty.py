"""Fix-pack onestà del trust ledger (adversarial review 2026-07-09).

La review ha trovato che l'odometro poteva CONTARE MALE — l'opposto del suo
contratto: (1) "admitted" registrato PRIMA di semantic.store(), ma gli screen
dentro store (injection screen: default ON) possono ribaltare lo status a
quarantined → admitted sovracontava; (2) il path conversation-ingest non era
contato affatto, ma i suoi fatti compaiono nello store → ledger e store si
contraddicevano nella stessa risposta /v1/stats; (3) by_layer contava anche i
layer ADVISORY (warning con persist) come se avessero agito.

Contratto post-fix: il ledger conta lo STATUS FINALE del fatto (dopo ogni
screen), copre anche l'ingest conversazionale, attribuisce i layer solo alle
azioni reali, ed espone i write-failure del ledger stesso (fail-open ma non
più invisibile).
"""
from __future__ import annotations

import pytest

from engram.client import Memory


def test_store_screen_flip_counts_as_quarantined_not_admitted(tmp_path, monkeypatch):
    """Il gate dice persist ma lo screen dentro store() quarantena (es.
    injection screen): l'odometro deve dire QUARANTINED — conta ciò che è
    successo davvero, non l'intenzione del gate."""
    import engram.semantic as semantic_mod

    m = Memory(tmp_path / "m.db")

    real_store = semantic_mod.SemanticMemory.store

    def screening_store(self, fact, *a, **kw):
        fact.status = "quarantined"  # come fa lo screen injection reale
        return real_store(self, fact, *a, **kw)

    monkeypatch.setattr(semantic_mod.SemanticMemory, "store", screening_store)
    r = m.add("perfectly clean fact", verified_by=["doc:1"])
    assert r["stored"] is True
    s = m.trust_stats()
    assert s["ledger"]["quarantined"] == 1, "lo screen ha agito: va contato"
    assert s["ledger"]["admitted"] == 0, "admitted non deve sovracontare"


def test_conversation_ingest_is_ledgered(tmp_path):
    """add(messages) passa dall'ingest: i fatti estratti DEVONO comparire
    nell'odometro — un intero path primario non può essere invisibile."""

    class _StubLLM:
        def complete(self, system, messages, **kw):
            class R:
                text = ("- Alice moved to Berlin in March 2024\n"
                        "- Alice works at a fintech startup")
                total_tokens = 10
            return R()

    m = Memory(tmp_path / "m.db", llm=_StubLLM())
    res = m.add([{"role": "user", "content": "I am Alice, I moved to Berlin "
                                             "in March 2024 for a fintech job."}])
    assert res.get("stored", 0) >= 1, f"precondizione ingest: {res}"
    s = m.trust_stats()
    counted = (s["ledger"]["admitted"] + s["ledger"]["quarantined"]
               + s["ledger"]["rejected"])
    assert counted >= res["stored"], (
        f"l'ingest ha memorizzato {res['stored']} fatti ma l'odometro ne "
        f"conta {counted} — path invisibile")


def test_advisory_layers_not_in_by_layer(tmp_path):
    """Un layer che ha SOLO avvisato (warning ma fatto ammesso pulito) non
    va in by_layer: quella vista risponde a 'quale layer ti ha protetto',
    non 'quale layer ha parlato'."""
    m = Memory(tmp_path / "m.db")
    # fatto personale: L1 scatta su 'scheduled' ma il contesto personale lo
    # sopprime -> persist con warning advisory
    r = m.add("My dentist appointment is scheduled for Monday afternoon")
    s = m.trust_stats()
    if r["status"] not in ("quarantined",):  # ammesso: nessun layer ha AGITO
        assert s["by_layer"] == {}, (
            f"layer advisory contati come protettivi: {s['by_layer']}")


def test_ledger_write_failures_are_visible(tmp_path, monkeypatch):
    """Fail-open resta (mai rompere una scrittura) ma non più invisibile:
    i drop del ledger sono contati ed esposti in trust_stats."""
    from engram import trust_ledger as tl

    m = Memory(tmp_path / "m.db")

    def boom(self, *a, **kw):
        raise RuntimeError("ledger table locked")

    monkeypatch.setattr(tl.TrustLedger, "_connect", boom)
    r = m.add("fact survives", verified_by=["doc:1"])
    assert r["stored"] is True, "fail-open: la scrittura non muore"
    s = m.trust_stats()
    assert s.get("ledger_write_failures", 0) >= 1, (
        "un odometro che perde eventi deve DIRLO, non mostrare zeri")
