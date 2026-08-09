"""Tre rami della stessa funzione, due contratti.

ws2, grep indipendente del 2026-08-07 — cercata con chiavi diverse dalle
mie (`grounding_score`/`writer_principal` fuori da `fact_contract`, e i
letterali `{id: f.id, …}`), che è il motivo per cui ha trovato quello che
il mio criterio aveva mancato.

`Memory.ask` instrada su tre rami e ne serve due in modo diverso.
Riprodotto qui prima di toccare:

    «elenca tutti i depot»  -> list_all   3 chiavi: id, text, topic
    «list all depot»        -> list_all   3 chiavi
    «tutto tranne yard»     -> exclude    3 chiavi
    (find)                  -> find      15 chiavi, via `_fact_view`

⇒ Chi chiede «elencami tutto su X» riceve fatti in cui **un model_claim e
uno verificato sono indistinguibili**: niente `status`, niente
`grounding_score`, niente provenienza. La stessa domanda posta in un'altra
forma li distingue.

La cura è la stessa di `history()` un'ora fa e usa la superficie che già
esiste — `_fact_view`, «the SAME provenance surface everywhere» — invece
di aggiungere un terzo modo di scrivere un fatto.

⚠️ `score` NON viene inventato per i due rami: appartiene alla query e
questi non ordinano niente. Metterlo a zero direbbe «rilevanza nulla», che
è un'affermazione; ometterlo dice «questo elenco non ordina», che è la
verità.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

_CHIAVI_MINIME = {"id", "text", "topic", "status", "grounding_score",
                  "verified_by", "created_at", "superseded_by"}


@pytest.fixture()
def mem(tmp_path):
    m = Memory(tmp_path / "m.db")
    m.add("the depot holds 10 crates", topic="log/a")
    m.add("the depot holds 20 crates", topic="log/b")
    m.add("the yard holds 5 pallets", topic="log/c")
    return m


def test_il_ramo_LIST_ALL_porta_il_verdetto(mem):
    out = mem.ask("elenca tutti i depot")
    assert out["intent"] == "list_all", out["intent"]
    assert out["results"], "il banco deve trovare qualcosa"
    for r in out["results"]:
        assert _CHIAVI_MINIME <= set(r), sorted(set(r))


def test_il_ramo_EXCLUDE_porta_il_verdetto(mem):
    out = mem.ask("tutto tranne yard")
    assert out["intent"] == "exclude", out["intent"]
    assert out["results"]
    for r in out["results"]:
        assert _CHIAVI_MINIME <= set(r), sorted(set(r))


def test_i_TRE_RAMI_concordano_sulle_chiavi_del_fatto(mem):
    """L'invariante vera: non «ci sono i campi che ho elencato» ma «i rami
    della stessa funzione descrivono un fatto allo stesso modo». Questo
    test non invecchia quando la vista cresce."""
    trovato = mem.ask("depot")
    elenco = mem.ask("elenca tutti i depot")
    escluso = mem.ask("tutto tranne yard")

    k_find = set(trovato["results"][0]) - {"score", "confidence_tier"}
    for altro in (elenco, escluso):
        k = set(altro["results"][0])
        mancanti = k_find - k
        assert not mancanti, f"{altro['intent']} perde {sorted(mancanti)}"


def test_lo_score_NON_si_inventa_dove_non_si_ordina(mem):
    """`score` appartiene alla query: in un elenco non c'e' un
    ordinamento, e uno zero direbbe «rilevanza nulla» — un'affermazione.
    Assente dice «questo elenco non ordina», che e' la verita'."""
    for q in ("elenca tutti i depot", "tutto tranne yard"):
        for r in mem.ask(q)["results"]:
            assert "score" not in r, (q, sorted(r))


def test_il_nome_storico_text_resta(mem):
    """Chi legge `ask` usa `text` da sempre: la cura non lo tocca."""
    r = mem.ask("elenca tutti i depot")["results"][0]
    assert r["text"] and isinstance(r["text"], str)


def test_un_quarantinato_e_ora_RICONOSCIBILE_in_questi_rami(mem):
    """Il danno concreto misurato da ws2: un claim respinto dal gate usciva
    da questi rami indistinguibile da un fatto ammesso. Non lo filtro —
    filtrare e' una decisione di prodotto — ma ora chi legge PUO' vederlo."""
    fid = mem.add("the depot holds 30 crates", topic="log/d")["id"]
    mem.semantic.quarantine_fact(fid, reason="banco")

    righe = {r["id"]: r for r in mem.ask("elenca tutti i depot")["results"]}
    if fid in righe:
        assert righe[fid]["status"] == "quarantined", righe[fid]
