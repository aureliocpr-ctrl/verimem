"""Critic counterexample on graded admission (514cdec3c6b4b512, FAIL vote):
an UNPROVEN write must never RETIRE an admitted value.

Empirically reproduced by the critic on the working tree: with
ENGRAM_GRADED_ADMISSION=1, a sub-threshold write (score 12) that the L3 stack
also classifies as a same-source EVOLUTION flips the gate action to persist,
which flips client.add()'s _disposition to "admitted" and UNLOCKS the
supersession branch — retiring the previously admitted (grounded) value from
curated recall. Under the env OFF both values survived. Net effect: a score-12
claim evicts a score-95 one. This file pins the cure plus the two graded
branches the first test file left uncovered (critic falsification caveat 1)
and the ledger-attribution rule (caveat 4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.anti_confab_gate import run_validation_gate

OLD = "The subscription costs 100 euros per month."
NEW = "The subscription costs 150 euros per month."
WEAK_SOURCE = "Billing notes: various commercial topics were discussed."

#: ⚠️ DUE SCHERMI INDIPENDENTI, E IL BANCO DEVE PASSARE SOLO IL PRIMO.
#: Misurato il 2026-09-13 dalla porta MCP: con `WEAK_SOURCE` la scrittura non
#: arriva mai all'ammissione degradata, perche' PRIMA la ferma uno schermo
#: LESSICALE — `quarantined_by='L4.1'`, «il claim afferma un valore che la
#: fonte non contiene: 150 euro» — e la quarantena lessicale non e' quella che
#: T83 misura. Il giudice semantico e' indipendente da quello schermo: qui la
#: fonte CONTIENE il valore (L4.1 tace) ma non lo sostiene (il giudice lo
#: punteggia sotto soglia), che e' esattamente la forma per cui l'ammissione
#: degradata esiste.
FONTE_DEBOLE_COL_VALORE = (
    "Billing notes, Q3 meeting: the figure of 150 euros per month came up in "
    "passing while several commercial topics were discussed; no decision was "
    "recorded and no plan was named.")
FONTE_FORTE = (
    "Billing contract, section 2: the subscription costs 100 euros per month.")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("ENGRAM_GRADED_ADMISSION", raising=False)
    yield


def _low_score(monkeypatch, score: float = 12.0):
    """Deterministic sub-threshold CE on the REAL SDK path."""
    import verimem.grounding_gate as gg
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda llm, src, prop: (score, "local"))


def _punteggi(monkeypatch, mappa: dict[str, float], default: float = 95.0):
    """CE deterministico ma DIVERSO per proposizione, sulla stessa porta.

    Serve il caso che il docstring di questo file promette — «uno score-12
    sfratta uno score-95» — e con un punteggio unico per tutte le scritture
    quel caso non e' costruibile: il valore vecchio entrerebbe anch'esso
    sotto soglia, e un degradato che ne sfratta un altro degradato non e'
    l'invariante in discussione.
    """
    import verimem.grounding_gate as gg

    def _finto(llm, src, prop):
        for frammento, punteggio in mappa.items():
            if frammento in (prop or ""):
                return (punteggio, "local")
        return (default, "local")

    monkeypatch.setattr(gg, "fact_grounding_score_ex", _finto)


def test_graded_admit_must_not_retire_an_admitted_value(tmp_path: Path,
                                                        monkeypatch):
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r1 = m.add(OLD, topic="pricing/plan",
               verified_by=["source-doc:billing:1"], validate="full")
    assert r1.get("status") != "quarantined"
    _low_score(monkeypatch)
    r2 = m.add(NEW, topic="pricing/plan",
               verified_by=["source-doc:billing:1"], validate="full",
               source=WEAK_SOURCE, ground=True)
    # the graded write may be admitted low-conf — but the OLD value survives
    import sqlite3
    with sqlite3.connect(str(m.semantic.db_path)) as con:
        row = con.execute("SELECT superseded_by FROM facts WHERE id=?",
                          (r1["id"],)).fetchone()
    assert row and row[0] is None, \
        "an unproven (graded) write must NOT retire an admitted value"
    assert not r2.get("superseded"), \
        f"graded admission must not supersede, got {r2.get('superseded')}"


def test_graded_layers_are_never_credited_as_blockers():
    """Ledger attribution (critic caveat 4): a ``*-graded`` layer records an
    ADMISSION — it must never own a block reason nor a by_layer credit, even
    when another layer quarantines the same write."""
    from verimem.client import _blocking_layers, _is_advisory_layer
    assert _is_advisory_layer("L4-grounding-graded") is True
    assert _is_advisory_layer("L4-review-graded") is True
    ws = [{"layer": "L3", "reason": "contradiction"},
          {"layer": "L4-grounding-graded", "reason": "graded"}]
    assert _blocking_layers(ws) == ["L3"]


def _band(monkeypatch, *, score: float, escalation):
    """Force the CE band path deterministically: local judge, band enforced,
    tau_hi above the score, escalate_band stubbed."""
    import verimem.band_escalation as be
    import verimem.grounding_gate as gg
    monkeypatch.setattr(gg, "fact_grounding_score_ex",
                        lambda llm, src, prop: (score, "local"))
    monkeypatch.setattr(gg, "_ce_band_enforced", lambda: True)
    monkeypatch.setattr(gg, "_ce_band_tau_hi", lambda: 88.0)
    monkeypatch.setattr(be, "escalate_band", lambda src, prop: escalation)


def _gate_no_llm():
    return run_validation_gate(
        proposition="The maintenance window is on Saturday night.",
        verified_by=None, topic="ops/x", agent=None, validate="full",
        source=WEAK_SOURCE, grounding_llm=None, ground_write=True)


def test_band_review_graded_admits(monkeypatch):
    """Critic caveat 1a: the no-adjudicator band branch. Graded ON: the
    borderline write persists with L4-review-graded instead of being held."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _band(monkeypatch, score=60.0, escalation=None)
    res = _gate_no_llm()
    assert res.action == "persist"
    assert any(w.get("layer") == "L4-review-graded" for w in res.warnings)
    assert not any(w.get("layer") == "L4-review" for w in res.warnings)


def test_band_review_off_still_holds(monkeypatch):
    _band(monkeypatch, score=60.0, escalation=None)
    res = _gate_no_llm()
    assert res.action in ("downgrade", "reject")
    assert any(w.get("layer") == "L4-review" for w in res.warnings)


def test_band_escalated_subthreshold_graded_admits(monkeypatch):
    """Critic caveat 1b: the escalated-judge branch. The llm adjudicates below
    the claude-scale cut; graded ON admits with L4-grounding-graded."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _band(monkeypatch, score=60.0, escalation=(20.0, "claude-band"))
    res = _gate_no_llm()
    assert res.action == "persist"
    assert any(w.get("layer") == "L4-grounding-graded" for w in res.warnings)


def test_band_escalated_subthreshold_off_blocks(monkeypatch):
    _band(monkeypatch, score=60.0, escalation=(20.0, "claude-band"))
    res = _gate_no_llm()
    assert res.action in ("downgrade", "reject")
    assert any(w.get("layer") == "L4-grounding" for w in res.warnings)


# ═══════════════════════════════════════════════════════════════════════════
# T83 (2026-09-13) — LA STESSA REGOLA, SULLA SECONDA PORTA.
#
# La regola di questo file — «an UNPROVEN write must never RETIRE an admitted
# value» — nasce da un controesempio di un critic ed e' presidiata sopra, con
# `Memory.add`: l'SDK. Ma un agente non scrive dall'SDK: scrive dal server di
# strumenti, e li' la guardia non c'e'.
#
#   SDK   client.py   `_graded_admit = any(layer.endswith("-graded") …)`
#                     e la supersessione si sblocca solo se NON e' graded
#   MCP   mcp_server.py   `if (not _deferred and status != "quarantined")`
#                          ← due condizioni, e la graded non e' fra queste
#
# Chi ha fatto la cura di T56 lo ha scritto per iscritto invece di nasconderlo,
# nel docstring di `supersession_policy.applica_verdetto`: «l'SDK non ritira
# quando la scrittura e' stata ammessa in forma DEGRADATA, il server di
# strumenti quella guardia non ce l'aveva. La differenza NON viene unificata
# qui … e' una DECISIONE DI PRODOTTO». La decisione e' stata presa il
# 2026-09-13: vale la regola dell'SDK, su tutte e tre le porte.
#
# ⚠️ PERCHE' LE CELLE SONO DUE. La prima pretende che il vecchio NON sia
# ritirato — e un test cosi' passa anche quando non c'era NIENTE da ritirare:
# se la coppia non viene classificata come evoluzione della stessa fonte, o se
# la seconda scrittura non entra affatto, il risultato e' identico e il
# presidio non misura niente. La seconda cella e' il controllo positivo: con
# un'ammissione PIENA la stessa porta DEVE ritirare. Senza, il giorno in cui
# la supersessione si rompe del tutto la prima diventa verde e nessuno lo vede.
#
# Judge stubbato: costa millisecondi, non i ~29 s di caricamento del CE.
# ═══════════════════════════════════════════════════════════════════════════

async def _scrivi_dalla_porta_mcp(monkeypatch, tmp_path, coppie):
    """Scrive dal server di strumenti e torna (ricevute, semantic).

    `coppie` e' la lista degli `arguments` di `hippo_remember`, in ordine.
    L'agente e' finto ma lo store e' vero: la supersessione va osservata nel
    database, non in cio' che la porta dichiara.
    """
    import json
    import types

    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _Giudice:
        def __init__(self):
            self.calls = 0

        def complete(self, *a, **k):
            self.calls += 1
            return "YES"

    class _A:
        def __init__(self):
            self.semantic = sm
            self.wake = types.SimpleNamespace(llm=_Giudice())

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())
    handler = mcp_server.server.request_handlers[CallToolRequest]

    ricevute = []
    for argomenti in coppie:
        risultato = await handler(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="hippo_remember",
                                         arguments=argomenti)))
        corpo = risultato.root if hasattr(risultato, "root") else risultato
        ricevute.append(json.loads(
            next(c.text for c in corpo.content if hasattr(c, "text"))))
    return ricevute, sm


def _superseduto_da(sm, fact_id):
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as con:
        riga = con.execute("SELECT superseded_by FROM facts WHERE id=?",
                           (fact_id,)).fetchone()
    return riga[0] if riga else "ASSENTE"


_ARG_VECCHIO = {"proposition": OLD, "topic": "pricing/plan",
                "verified_by": ["source-doc:billing:1"], "validate": "full"}

#: Il valore che deve NON essere sfrattato entra con la sua fonte e col suo
#: punteggio pieno: senza fonte sarebbe un `model_claim` mai giudicato, e
#: «un claim non provato ne sfratta un altro non provato» non e' l'invariante.
_ARG_VECCHIO_PROVATO = {**_ARG_VECCHIO, "source": FONTE_FORTE}


@pytest.mark.asyncio
async def test_la_porta_MCP_non_ritira_su_un_ammissione_DEGRADATA(
        tmp_path: Path, monkeypatch):
    """Il difetto: dal server di strumenti uno score-12 sfratta uno score-95."""
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _punteggi(monkeypatch, {"150 euros": 12.0})     # il vecchio resta a 95

    ricevute, sm = await _scrivi_dalla_porta_mcp(monkeypatch, tmp_path, [
        _ARG_VECCHIO_PROVATO,
        {"proposition": NEW, "topic": "pricing/plan",
         "verified_by": ["source-doc:billing:1"], "validate": "full",
         "source": FONTE_DEBOLE_COL_VALORE},
    ])
    vecchio, nuovo = ricevute

    id_vecchio = vecchio.get("id") or vecchio.get("fact_id")
    assert id_vecchio, (
        "CONTROLLO POSITIVO SPENTO: la prima scrittura non ha reso un id, "
        f"quindi non c'e' niente che possa essere ritirato. ricevuta={vecchio}")
    assert vecchio.get("status") != "quarantined", (
        f"CONTROLLO POSITIVO SPENTO: il vecchio e' entrato come "
        f"{vecchio.get('status')!r}: un fatto gia' fermato non prova niente.")

    #: ⚠️ LA PRECONDIZIONE SI ASSERISCE, NON SI SPERA. Questa cella misura cosa
    #: fa la porta con un'ammissione DEGRADATA: se la scrittura nuova non e'
    #: arrivata in quello stato, l'assert finale passa per la ragione
    #: sbagliata — la guardia che la porta ha GIA' (`status != quarantined`) la
    #: ferma prima che quella MANCANTE possa contare, e il verde direbbe «il
    #: difetto non c'e'» quando vuol dire «non ci sono arrivato».
    #:
    #: Misurato il 2026-09-13: al primo giro la scrittura nuova e' uscita
    #: `quarantined` e le due celle passavano tutt'e due. Senza questa riga
    #: avrei consegnato un RED verde, cioe' un presidio che non presidia.
    _stato_nuovo = nuovo.get("status")
    #: ⚠️ LA STESSA LISTA HA DUE NOMI ALLE DUE PORTE. L'SDK la rende come
    #: `warnings` (client.py, `_graded_admit` la legge cosi'); questa porta la
    #: rende come `anti_confab_warnings`. Chiedendo solo il nome dell'SDK la
    #: lista tornava VUOTA — e una lista vuota si legge «nessuno schermo ha
    #: parlato», che il 2026-09-13 era falso: ne avevano parlato due.
    _campi = [c for c in ("anti_confab_warnings", "warnings") if c in nuovo]
    assert _campi, (
        "BANCO CIECO: la ricevuta della porta non porta ne' "
        "`anti_confab_warnings` ne' `warnings`, quindi da qui nessun layer e' "
        f"osservabile e ogni verdetto su di essi sarebbe inventato. chiavi="
        f"{sorted(nuovo)}")
    _strati = [w.get("layer") for c in _campi for w in (nuovo.get(c) or [])]
    assert _stato_nuovo != "quarantined", (
        f"PRECONDIZIONE NON RAGGIUNTA, e questo NON e' un verdetto sul "
        f"prodotto: la scrittura nuova e' entrata come {_stato_nuovo!r} invece "
        f"che ammessa in forma degradata, quindi questa cella non ha misurato "
        f"la guardia che le interessa. Guarda i layer per capire chi ha "
        f"deciso: {_strati}. Il ramo del punteggio in `anti_confab_gate` "
        f"chiede `source and _ground_on and _have_judge`: se uno dei tre e' "
        f"falso il punteggio non viene mai calcolato e l'ammissione degradata "
        f"non e' raggiungibile da questa porta — che sarebbe un risultato, non "
        f"un errore, e andrebbe scritto nel ticket invece che aggirato qui. "
        f"ricevuta={nuovo}")
    assert any(str(s).endswith("-graded") for s in _strati), (
        f"PRECONDIZIONE NON RAGGIUNTA: la scrittura e' stata ammessa ma "
        f"NESSUN layer `*-graded` compare fra {_strati}. L'ammissione non e' "
        f"degradata, quindi il caso di T83 non e' sul tavolo: l'assert qui "
        f"sotto passerebbe anche a difetto presente. ricevuta={nuovo}")

    assert _superseduto_da(sm, id_vecchio) is None, (
        "dalla porta MCP una scrittura ammessa in forma DEGRADATA ha RITIRATO "
        "un valore ammesso sulle proprie prove. L'SDK non lo fa "
        "(client.py, `_graded_admit`), la riga di comando nemmeno: e' la "
        "stessa regola su una porta che non la applica. Un claim score-12 "
        "sfratta uno score-95 dal recall curato, ed e' la perdita netta che "
        "la quarantena dura impediva. "
        f"nuovo={nuovo.get('id') or nuovo.get('fact_id')} "
        f"status={nuovo.get('status')!r}")


@pytest.mark.asyncio
async def test_CONTROLLO_la_porta_MCP_ritira_su_un_ammissione_PIENA(
        tmp_path: Path, monkeypatch):
    """Il controllo positivo: senza, la cella qui sopra passa per il silenzio.

    Stessa porta, stessa coppia, **una sola variabile diversa**: il punteggio
    non e' sotto soglia e l'ammissione non e' degradata. Qui la supersessione
    DEVE avvenire — se non avviene, non e' la guardia sulla degradata a
    mancare: e' la supersessione a non funzionare affatto, e la cella
    precedente starebbe misurando il nulla.
    """
    #: ⚠️ L'INTERRUTTORE RESTA ACCESO ANCHE QUI. Al primo giro questa cella
    #: spegneva `ENGRAM_GRADED_ADMISSION` mentre l'altra lo accendeva: due
    #: variabili diverse fra le due, e un confronto con due variabili non dice
    #: quale delle due ha prodotto la differenza. Qui cambia SOLO il punteggio
    #: del nuovo (95 invece di 12), cioe' solo la cosa di cui T83 parla.
    monkeypatch.setenv("ENGRAM_GRADED_ADMISSION", "1")
    _punteggi(monkeypatch, {})                      # tutto a 95: piena

    ricevute, sm = await _scrivi_dalla_porta_mcp(monkeypatch, tmp_path, [
        _ARG_VECCHIO_PROVATO,
        {"proposition": NEW, "topic": "pricing/plan",
         "verified_by": ["source-doc:billing:1"], "validate": "full",
         "source": FONTE_DEBOLE_COL_VALORE},
    ])
    vecchio, nuovo = ricevute

    id_vecchio = vecchio.get("id") or vecchio.get("fact_id")
    id_nuovo = nuovo.get("id") or nuovo.get("fact_id")
    assert id_vecchio and id_nuovo, (
        f"le due scritture non hanno reso due id: {vecchio} / {nuovo}")

    #: Il controllo positivo deve misurare un'ammissione PIENA: se il nuovo
    #: entrasse qui in forma degradata e la porta ritirasse lo stesso, questa
    #: cella verde direbbe «la supersessione funziona» mentre starebbe
    #: mostrando proprio il difetto dell'altra — e lo attribuirebbe al
    #: contrario.
    _strati_c = [w.get("layer")
                 for c in ("anti_confab_warnings", "warnings")
                 for w in (nuovo.get(c) or [])]
    assert not any(str(s).endswith("-graded") for s in _strati_c), (
        f"CONTROLLO POSITIVO SPENTO: il nuovo e' entrato DEGRADATO ({_strati_c}), "
        "quindi questa cella non misura l'ammissione piena che dice di misurare.")

    assert _superseduto_da(sm, id_vecchio) == id_nuovo, (
        "CONTROLLO POSITIVO SPENTO: con un'ammissione PIENA la porta MCP non "
        "ritira il valore vecchio, quindi la cella sulla degradata non "
        "distingue «non ha ritirato perche' degradata» da «non ritira mai». "
        "Non rilassare questo assert: senza di esso l'altro presidio e' un "
        f"sensore scollegato. superseded_by={_superseduto_da(sm, id_vecchio)!r} "
        f"atteso={id_nuovo!r}")
