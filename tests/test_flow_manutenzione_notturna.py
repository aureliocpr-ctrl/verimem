"""La manutenzione automatica ritira fatti, e non lo diceva a nessuno.

`auto_dream_worker.run_maintenance` gira **da sola ogni 4 ore** e fa tre
cose che cambiano il corpus: `cycle_light` (promuove/ritira),
`auto_consolidate` (nodi master), e `scan_corpus` + `heal_contradictions`,
che **supersede il lato debole di un conflitto**, fino a 100 per passata.

Misurato sul corpus di casa il 2026-08-05 alle 23:07 — venti minuti prima
di scrivere questo file:

    scan:    scanned_facts 6476 · new_detected 31 · kinds {numeric_clash: 2526}
    healed:  healed_superseded 5 · resolved 5 · skipped_equal_trust 95

Cinque fatti ritirati da un processo che nessuno stava guardando. Le
singole supersessioni un evento ce l'hanno (`flow.supersession`, da
questo ramo); la PASSATA no — e nemmeno i suoi fallimenti, perché ogni
passo è avvolto in un `try` («a step failure never crashes the worker»)
e l'errore finisce in `consolidate_last.json`, un file che non legge
nessuno.

Il fail-open è la scelta giusta: un worker che muore su un passo è
peggio. Ma un fail-open **invisibile** è un difetto, ed è la terza volta
che lo curo su questo ramo.

⚠️ Qui non si cambia cosa fa la manutenzione — perimetro di altri. Si
emette cosa ha fatto.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events


@pytest.fixture()
def canale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    monkeypatch.setenv("ENGRAM_CONSOLIDATE_COOLDOWN_S", "0")
    flow_events.reset_flow_context()
    return tmp_path


def _flow(tmp_path, name="flow.dream"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


class _SleepFinto:
    def __init__(self, **kw) -> None:
        pass

    def cycle_light(self):
        class _R:
            promoted = ["a"]
            retired = []
        return _R()


def _prepara(monkeypatch, *, heal=None, rompi=None):
    """Sostituisce i tre passi con versioni deterministiche."""
    import verimem.sleep as _sleep
    monkeypatch.setattr(_sleep, "SleepEngine", _SleepFinto)

    import verimem.consolidation as _cons
    monkeypatch.setattr(_cons, "auto_consolidate",
                        lambda *a, **k: {"clusters_detected": 3,
                                         "masters_persisted": 1})

    import verimem.contradiction as _con
    if rompi == "scan":
        def _boom(*a, **k):
            raise RuntimeError("indice illeggibile")
        monkeypatch.setattr(_con, "scan_corpus", _boom)
    else:
        monkeypatch.setattr(_con, "scan_corpus",
                            lambda *a, **k: {"scanned_facts": 10,
                                             "new_detected": 2})
    monkeypatch.setattr(_con, "heal_contradictions",
                        lambda *a, **k: (heal if heal is not None
                                         else {"healed_superseded": ["x", "y"],
                                               "resolved": ["x", "y"]}))


def _esegui(tmp_path, monkeypatch, **kw):
    from verimem.auto_dream_worker import run_maintenance
    _prepara(monkeypatch, **kw)

    class _Finto:
        pass
    return run_maintenance(tmp_path, sm=_Finto(), mem=_Finto())


def test_una_passata_che_gira_esce_sul_canale(canale, monkeypatch):
    out = _esegui(canale, monkeypatch)
    assert out["ran"] is True

    evts = _flow(canale)
    assert len(evts) == 1, "la manutenzione automatica non puo' essere muta"
    p = evts[0]["payload"]
    assert p["retired"] == 2, p
    assert p["clusters_detected"] == 3
    assert p["steps_failed"] == []


def test_i_passi_falliti_ESCONO_invece_di_finire_in_un_file(canale,
                                                            monkeypatch):
    """Il fail-open resta — il worker non muore — ma smette di essere
    invisibile: oggi l'errore va in `consolidate_last.json` e nessuno lo
    apre. Un passo che fallisce in silenzio ogni 4 ore per settimane e'
    esattamente quello che non si scopre.

    ⚠️ Il nome che esce è `heal` anche quando a cadere è lo scan: i due
    stanno nello stesso `try`, quindi il prodotto NON sa distinguerli e
    l'evento non lo inventa. Separarli cambierebbe il comportamento — con
    il try unico, uno scan fallito salta anche l'heal — ed è una
    decisione di chi possiede il worker, non mia.
    """
    _esegui(canale, monkeypatch, rompi="scan")

    p = _flow(canale)[-1]["payload"]
    assert "heal" in p["steps_failed"], p
    assert p["ran"] is True, "il fallimento di un passo non ferma la passata"


def test_la_passata_in_cooldown_non_emette(canale, monkeypatch):
    """Il worker si sveglia molto piu' spesso di quanto lavori: un evento
    per ogni risveglio a vuoto e' rumore, e seppellisce quelli veri."""
    monkeypatch.setenv("ENGRAM_CONSOLIDATE_COOLDOWN_S", "99999")
    _esegui(canale, monkeypatch)          # scrive il marker
    flow_events.reset_flow_context()
    prima = len(_flow(canale))
    out = _esegui(canale, monkeypatch)    # secondo giro: cooldown

    assert out["ran"] is False and out["reason"] == "cooldown"
    assert len(_flow(canale)) == prima


def test_l_evento_non_porta_il_testo_dei_fatti(canale, monkeypatch):
    """Come ogni altro evento di questo ramo: metadati, mai proposizioni.
    Il feed viaggia in rete e finisce su una pagina."""
    _esegui(canale, monkeypatch,
            heal={"healed_superseded": ["id1"], "resolved": ["id1"]})
    testo = json.dumps(_flow(canale)[-1]["payload"])
    assert "proposition" not in testo and "office" not in testo
