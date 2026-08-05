"""«Rifiutato dal giudice» e «rifiutato NONOSTANTE il giudice» non sono
la stessa riga di feed.

ws5, 2026-08-05, sul canale: `moat: passed`, grounding 100.0,
`status: quarantined` — il giudice ha girato, ha detto vero al 100%, e il
fatto è fuori lo stesso perché L1 ha visto una parola. Nel feed quel fatto
si legge come un rifiutato qualunque, **ed è l'unico caso in cui il
prodotto contraddice sé stesso**.

Riprodotto qui in modo deterministico (verdetto iniettato, testo che L1
ferma davvero): `status quarantined`, `grounding_score 100.0`, layers
`L1.13` + `L1.15`.

La vista sul corpus esisteva già da stamattina — `judged_true_but_withheld`
in `verdict_mismatches`, 11 fatti sul corpus reale. Mancava sul VIVO, cioè
nel momento in cui succede. E il taglio è lo STESSO: una soglia scritta due
volte è la classe di difetto che questo ramo cura da due giorni, quindi la
condizione vive in una funzione sola (`retirement_log.judged_true`) e la
usano sia la vista sul corpus sia l'evento.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.client import Memory

_CLAIM = "The migration is complete and fully verified."
_FONTE = "Release notes: the migration completed and was verified by QA."


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", "40")
    flow_events.reset_flow_context()
    return tmp_path


def _verdetto(monkeypatch, punteggio: float) -> None:
    monkeypatch.setattr("verimem.grounding_gate.fact_grounding_score_ex",
                        lambda llm, s, f, **kw: (punteggio, "local"))


def _write(tmp_path) -> list[dict]:
    p = tmp_path / "events.jsonl"
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines()
            if json.loads(ln).get("name") == "flow.write"]


def test_giudicato_vero_e_trattenuto_lo_stesso_si_dichiara(banco, monkeypatch):
    """Il caso di ws5: il moat dice 100 e L1 lo tiene fuori."""
    _verdetto(monkeypatch, 100.0)
    m = Memory(banco / "m.db")
    r = m.add(_CLAIM, topic="rilasci", source=_FONTE)

    assert r["status"] == "quarantined" and r["grounding_score"] == 100.0
    p = _write(banco)[-1]["payload"]
    assert p["withheld_despite_judge"] is True, p
    assert p["layers"], "e le difese che hanno agito restano nell'evento"


def test_un_rifiuto_senza_verdetto_non_e_una_contraddizione(banco):
    """Senza source il giudice non gira: L1 ferma il claim e basta. Dire
    «nonostante il giudice» dove il giudice non c'è stato sarebbe
    inventare un conflitto — l'errore opposto e altrettanto grave."""
    m = Memory(banco / "m.db")
    r = m.add(_CLAIM, topic="rilasci")

    assert r["status"] == "quarantined"
    p = _write(banco)[-1]["payload"]
    assert p["judged"] is False
    assert p["withheld_despite_judge"] is False, p


def test_un_rifiuto_col_verdetto_basso_non_e_una_contraddizione(
        banco, monkeypatch):
    """Il giudice ha detto che la fonte NON lo sostiene e il fatto è
    fuori: le due cose concordano. È il funzionamento, non l'anomalia."""
    _verdetto(monkeypatch, 3.0)
    m = Memory(banco / "m.db")
    m.add(_CLAIM, topic="rilasci", source=_FONTE)

    p = _write(banco)[-1]["payload"]
    assert p["judged"] is True
    assert p["withheld_despite_judge"] is False, p


def test_un_fatto_ammesso_non_e_mai_una_contraddizione(banco, monkeypatch):
    _verdetto(monkeypatch, 99.0)
    m = Memory(banco / "m.db")
    r = m.add("The head office of the company is in Milan.", topic="hq",
              source="Company handbook: the head office is in Milan, Italy.")

    assert r["status"] != "quarantined"
    assert _write(banco)[-1]["payload"]["withheld_despite_judge"] is False


def test_ogni_ramo_di_flow_write_porta_il_verdetto(banco, monkeypatch):
    """SWEEP. `flow.write` esce da tre punti diversi di `add()` —
    rifiutato, instradato a telemetria, scritto — e solo l'ultimo portava
    il verdetto. Un RIFIUTO senza punteggio nasconde esattamente il caso
    peggiore: il giudice aveva detto di sì e la scrittura non è nemmeno
    entrata. Le chiavi devono essere le stesse su tutti i rami, altrimenti
    chi legge il feed vede il verdetto a intermittenza."""
    _verdetto(monkeypatch, 3.0)
    m = Memory(banco / "m.db")
    respinto = m.add("The head office of the company is in Rome.", topic="hq",
                     source="Handbook: our fleet has 12 vans.",
                     gate_mode="reject")
    assert respinto["status"] == "rejected", respinto
    assert respinto["grounding_score"] == 3.0, "la ricevuta il verdetto ce l'ha"

    chiavi = {"grounding_score", "judged", "withheld_despite_judge"}
    for e in _write(banco):
        mancanti = chiavi - set(e["payload"])
        assert not mancanti, (
            f"ramo status={e['payload'].get('status')} senza {mancanti}")


def test_un_rifiuto_porta_il_verdetto_che_lo_ha_causato(banco, monkeypatch):
    """Nel feed «REJECTED» non diceva se il giudice fosse stato coinvolto:
    la ricevuta portava `moat 3.0` e l'evento niente. Chi guarda la sala
    motore vedeva un rifiuto senza sapere da quale difesa venisse.

    ⚠️ LIMITE DICHIARATO: il caso simmetrico — respinto NONOSTANTE un
    verdetto alto — non sono riuscito a raggiungerlo. `reject` chiede una
    contraddizione L3 oppure un fallimento di grounding, e la strada L3 su
    due fatti dello stesso topic viene presa prima dalla supersessione
    come EVOLUZIONE (misurato: il secondo fatto entra e ritira il primo).
    Quindi il flag su questo ramo oggi è sempre False, e lo scrivo invece
    di far finta che il test lo copra."""
    _verdetto(monkeypatch, 3.0)
    m = Memory(banco / "m.db")
    m.add("The head office of the company is in Rome.", topic="hq",
          source="Handbook: our fleet has 12 vans.", gate_mode="reject")

    p = _write(banco)[-1]["payload"]
    assert p["status"] == "rejected" and p["stored"] is False
    assert p["judged"] is True and p["grounding_score"] == 3.0
    assert p["withheld_despite_judge"] is False
    assert "L4-grounding" in p["layers"], p


def test_il_taglio_e_LO_STESSO_della_vista_sul_corpus(banco, monkeypatch):
    """Una soglia scritta due volte diverge: è successo tre volte in due
    giorni su questo prodotto. Il flag del vivo e la lista sul corpus
    devono nascere dalla stessa funzione, e questo test cade il giorno in
    cui qualcuno ne cambia una sola."""
    from verimem.retirement_log import judged_true, verdict_mismatches

    _verdetto(monkeypatch, 100.0)
    m = Memory(banco / "m.db")
    r = m.add(_CLAIM, topic="rilasci", source=_FONTE)

    p = _write(banco)[-1]["payload"]
    ids = [x["fact_id"]
           for x in verdict_mismatches(m.semantic)["judged_true_but_withheld"]]
    assert p["withheld_despite_judge"] is judged_true(r["grounding_score"])
    assert (r["id"] in ids) is p["withheld_despite_judge"]


def test_sotto_il_taglio_nessuna_delle_due_superfici_lo_chiama_contraddizione(
        banco, monkeypatch):
    """L'altro lato della stessa prova: un verdetto ALTO ma sotto il
    taglio prudente non è «vero» per nessuna delle due superfici. Senza
    questo caso il test sopra passerebbe anche con due soglie diverse
    purché entrambe stiano sotto 100."""
    from verimem.retirement_log import verdict_mismatches

    _verdetto(monkeypatch, 85.0)
    m = Memory(banco / "m.db")
    r = m.add(_CLAIM, topic="rilasci", source=_FONTE)

    assert r["status"] == "quarantined"
    p = _write(banco)[-1]["payload"]
    assert p["withheld_despite_judge"] is False
    ids = [x["fact_id"]
           for x in verdict_mismatches(m.semantic)["judged_true_but_withheld"]]
    assert r["id"] not in ids
