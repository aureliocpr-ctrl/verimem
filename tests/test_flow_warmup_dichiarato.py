"""Il caricamento del giudice si vede: 42 secondi non sono un vuoto.

Misurato il 2026-08-05 su store vergine: la PRIMA scrittura con `source`
impiega 42,7 secondi e sul canale flow esce questo:

    flow.entity   t+42.7s
    flow.write    t+42.7s

Nulla per quarantadue secondi, poi due eventi insieme alla fine. La Engine
Room — che deve mostrare il motore in diretta — mostra un motore FERMO
proprio mentre il prodotto fa la cosa più costosa che fa. Non è un
sottosistema muto: è un INTERVALLO che nessuno racconta.

ws4 ha isolato che quei secondi sono il moat e non l'embedder (senza fonte
2,4s, con fonte 46,4s). Il COSTO lo cura chi possiede il write path; qui si
cura il SILENZIO, che è ciò che fa sembrare bloccato un prodotto al lavoro.

⚠️ E il punto in cui emettere non è quello ovvio: `LocalGroundingJudge()`
ritorna in 0,1 ms — i 41 secondi si spendono dentro `_ensure_scorer`, alla
prima chiamata. Un `ready` emesso dal costruttore dichiarava pronto un
giudice che non aveva caricato niente: la bugia che l'osservabilità serve a
togliere. L'ultimo test qui sotto è la guardia contro quel ritorno indietro.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events, local_grounding


@pytest.fixture()
def pulito(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    local_grounding.reset_local_judge()
    yield tmp_path
    local_grounding.reset_local_judge()


def _flow(tmp_path, name="flow.warmup"):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == name]


def _giudice(monkeypatch, *, scorer=None, esplode=False):
    """Un giudice vero con il CARICAMENTO finto: è il caricamento che si
    misura, non il modello."""
    j = local_grounding.LocalGroundingJudge()

    def _fake(model_dir, max_length=None):
        if esplode:
            raise RuntimeError("modello assente")
        return scorer or (lambda coppie: [42.0 for _ in coppie])
    monkeypatch.setattr(local_grounding, "make_finetuned_scorer", _fake)
    return j


def test_il_caricamento_dichiara_inizio_e_fine(pulito, monkeypatch):
    """Due eventi, non uno: senza l'inizio, chi guarda scopre l'attesa solo
    quando è già finita — cioè quando non gli serve più saperlo."""
    j = _giudice(monkeypatch)
    j.score("una fonte qualunque", "un fatto qualunque")
    fasi = [e["payload"]["phase"] for e in _flow(pulito)]
    assert fasi == ["start", "ready"], fasi
    assert _flow(pulito)[0]["payload"]["what"] == "moat-judge"


def test_la_fine_porta_la_durata(pulito, monkeypatch):
    j = _giudice(monkeypatch)
    j.score("fonte", "fatto")
    fine = _flow(pulito)[-1]["payload"]
    assert isinstance(fine.get("elapsed_ms"), (int, float))


def test_il_secondo_giudizio_non_riemette(pulito, monkeypatch):
    """Si carica una volta: un evento per ogni giudizio sarebbe rumore su un
    giudice che sta già rispondendo."""
    j = _giudice(monkeypatch)
    j.score("fonte", "fatto")
    n = len(_flow(pulito))
    j.score("altra fonte", "altro fatto")
    assert len(_flow(pulito)) == n


def test_un_caricamento_fallito_lo_dice(pulito, monkeypatch):
    """Il caso peggiore per chi guarda è l'attesa che non finisce: se il
    caricamento salta, l'evento lo dice invece di lasciare uno `start`
    orfano per sempre."""
    j = _giudice(monkeypatch, esplode=True)
    with pytest.raises(RuntimeError):
        j.score("fonte", "fatto")
    assert [e["payload"]["phase"] for e in _flow(pulito)] == ["start", "failed"]


def test_costruire_il_giudice_NON_emette(pulito, monkeypatch):
    """La guardia contro il ritorno indietro: il costruttore non carica
    niente (0,1 ms misurati), quindi non deve dichiarare nulla. Se qualcuno
    rimette l'evento lì, l'attesa vera torna silenziosa e questo test cade."""
    local_grounding.LocalGroundingJudge()
    local_grounding.get_local_judge()
    assert _flow(pulito) == []
