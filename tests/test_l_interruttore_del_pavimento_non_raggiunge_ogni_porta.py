"""`ENGRAM_MIN_RELEVANCE` cambia due porte MCP su tre, e lo schema non lo diceva.

MISURATO ALLE PORTE il 2026-08-31 alle 00:04, un fatto nello store, giudice
locale assente per costruzione::

    regime                      porta                pavimento riportato   n
    ambiente NON impostato      hippo_facts_recall   None                  1
    ambiente NON impostato      hippo_trust_report   0.0                   1
    ENGRAM_MIN_RELEVANCE=0.99   hippo_facts_recall   0.99                  0
    ENGRAM_MIN_RELEVANCE=0.99   hippo_trust_report   0.0                   1

⇒ **L'interruttore non raggiunge `hippo_trust_report`** — la porta che la guida
degli agenti addita *per* sapere se lo store possa rispondere.

DOVE STA, letto prima di misurare::

    hippo_facts_recall     (:13803)  _mr = args.get(...) or env_floor_if_set()
    hippo_recall_history   (:8145)   _mrh = args.get(...) or env_floor_if_set()
    hippo_trust_report     (:8183)   float(arguments.get("min_relevance", 0.0))

E `trust_report.py` non legge l'ambiente per suo conto (`min_relevance: float =
0.0` nella firma): il controllo di lettura non e' caduto.

⚖️ COSA QUESTO TEST **NON** AFFERMA — ed e' la meta' che tiene onesta l'altra:
che la porta non si astenga. Si astiene per un'ALTRA via, `ce_gate`, accesa di
default. La divergenza e' sul PAVIMENTO, e la conseguenza e' per l'OPERATORE:
alza la variabile, ne cambia due su tre, e nessuna superficie glielo diceva.

📌 IL CAMBIO DI COMPORTAMENTO NON E' QUI. Far leggere l'ambiente anche a questa
porta e' una decisione collegiale (cambia cosa la porta RESTITUISCE a chi ha la
variabile impostata) e sta al voto sul canale. Questo presidio tiene ferma la
sola cosa che la misura autorizza da sola: che lo schema lo DICA.

🪞 IL BANCO SI E' FERMATO SULLA SUA STESSA POPOLAZIONE OPPOSTA alla prima
esecuzione, leggendo `None` (facts_recall) contro `0.0` (trust_report) come una
divergenza: sono lo stesso significato scritto in due modi, e il difetto era nel
criterio del misuratore. Corretto li'; il reperto minore — le due porte scrivono
«nessun pavimento» in due modi — resta scritto nel banco e non e' curato qui.

Banco: ``docs/stato-reale/banchi/ws3-l-interruttore-dell-astensione-e-la-porta-del-dossier.py``
"""

from __future__ import annotations

import asyncio

import pytest

from verimem import mcp_server


@pytest.fixture(scope="module")
def schema_trust_report() -> dict:
    """Lo schema che il server LISTA davvero, non una costante del test."""
    strumenti = asyncio.run(mcp_server.list_tools())
    for t in strumenti:
        if t.name == "hippo_trust_report":
            return t.inputSchema
    pytest.fail("hippo_trust_report non e' fra gli strumenti listati: "
                f"{[t.name for t in strumenti][:20]}")


def _descrizione(schema: dict) -> str:
    prop = (schema.get("properties") or {}).get("min_relevance") or {}
    assert prop, f"min_relevance sparito dallo schema: {list(schema.get('properties') or {})}"
    return str(prop.get("description", ""))


def test_lo_schema_dice_che_l_ambiente_non_raggiunge_questa_porta(
        schema_trust_report):
    """IL CUORE: la descrizione nomina la variabile e dice che NON arriva."""
    d = _descrizione(schema_trust_report)
    assert "ENGRAM_MIN_RELEVANCE" in d, d
    assert "does NOT" in d or "does not" in d, d


def test_lo_schema_porta_la_misura_e_non_solo_l_affermazione(
        schema_trust_report):
    """Un'affermazione senza il numero e' una promessa come le altre."""
    d = _descrizione(schema_trust_report)
    assert "0.99" in d, d


def test_lo_schema_non_lascia_credere_che_la_porta_sia_permissiva(
        schema_trust_report):
    """⚠️ LA POPOLAZIONE OPPOSTA, presidiata: dire «l'interruttore non arriva»
    e fermarsi li' fa concludere che la porta non si astenga mai. Si astiene per
    `ce_gate`, e lo schema deve dirlo nella stessa frase."""
    d = _descrizione(schema_trust_report)
    assert "ce_gate" in d, d


def test_le_porte_del_recall_continuano_a_leggere_l_ambiente():
    """⚠️ L'ALTRA POPOLAZIONE: se domani qualcuno «uniformasse» togliendo la
    lettura dell'ambiente dalle porte che ce l'hanno, la divergenza sparirebbe
    e questo presidio resterebbe verde mentendo. Qui si legge il sorgente
    dell'handler, che e' cio' che la misura ha osservato."""
    import inspect
    sorgente = inspect.getsource(mcp_server._call_tool_impl)
    assert sorgente.count("env_floor_if_set") >= 2, (
        "le porte del recall non leggono piu' l'ambiente: la premessa della "
        "misura del 2026-08-31 non vale piu', rimisurare prima di fidarsi "
        "dello schema")
