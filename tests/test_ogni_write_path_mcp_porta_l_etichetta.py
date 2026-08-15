"""Ogni percorso con cui MCP scrive un fatto deve attaccargli l'etichetta del gate.

PERCHÉ QUESTO FILE ESISTE. Misurato sul corpus il 2026-08-15, contando i fatti
per famiglia di ``writer_principal``::

    cli:*    4011 fatti  ->     0 senza confidence_tier
    sdk:*       7 fatti  ->     0 senza
    mcp:*     145 fatti  ->   145 senza          <- tutti e soli

Non era un ramo che sbagliava il calcolo. ``mcp_server._build_fact`` costruisce
il ``Fact`` **dentro il server**, non passa da ``client.add()``, e ``mcp_server``
non importava nemmeno la funzione che l'etichetta la calcola: il campo restava
``None`` **per costruzione**. I due esemplari che l'hanno fatta notare avevano
punteggi agli antipodi — **0,19** e **99,95** — e lo stesso esito, che è la prova
che l'etichetta non dipendeva dalla qualità del fatto ma dalla PORTA da cui
entrava. Con la cura quegli stessi punteggi danno ``low`` e ``high``:
l'informazione c'era già e veniva buttata via.

⚠️ E IL PRECEDENTE È NELLO STESSO PUNTO DEL FILE. Sopra la prima delle due
chiamate c'è un commento che dice *«key_facts is a SECOND MCP write path — stamp
it like hippo_remember»*: qualcuno aveva già fatto questo identico ragionamento
per ``writer_principal`` e aveva curato **entrambi** i chiamanti. **L'etichetta è
stata dimenticata esattamente dove il principal era stato ricordato** — ed è la
ragione per cui il presidio qui sotto NON verifica il comportamento di una
chiamata sola, ma **conta le chiamate**: la prossima persona che aggiunge un
terzo percorso di scrittura non deve dipendere dall'aver letto questo file.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1] / "verimem" / "mcp_server.py"


def _chiamate_a_build_fact() -> list[ast.Call]:
    albero = ast.parse(SERVER.read_text(encoding="utf-8", errors="replace"))
    return [
        n for n in ast.walk(albero)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_build_fact"
    ]


def test_il_costruttore_accetta_l_etichetta_e_la_propaga() -> None:
    """Il kwarg esiste e arriva al Fact."""
    from verimem.mcp_server import _build_fact

    f = _build_fact("prova", topic="t/presidio", confidence_tier="high")
    assert getattr(f, "confidence_tier", None) == "high", (
        "il kwarg confidence_tier non arriva al Fact: la cura è nella firma ma "
        "non nel costruttore"
    )


def test_senza_il_kwarg_il_comportamento_resta_quello_di_prima() -> None:
    """Non-regressione: il default è None, chi non lo passa non cambia.

    È la ragione per cui questa cura è a rischio basso, e va provata: se il
    default diventasse un valore, ogni chiamante che non lo passa comincerebbe
    a scrivere un'etichetta che nessun gate ha prodotto — un dato inventato con
    l'aria di un verdetto.
    """
    from verimem.mcp_server import _build_fact

    f = _build_fact("prova", topic="t/presidio")
    assert getattr(f, "confidence_tier", "NON-ESISTE") is None, (
        "senza il kwarg il campo deve restare None: un default diverso "
        "fabbricherebbe un verdetto che nessun giudice ha dato"
    )


def test_la_funzione_che_calcola_l_etichetta_e_raggiungibile_dal_server() -> None:
    """Il server non deve dipendere da `client` per una funzione del gate.

    L'import è da ``grounding_gate``: ``client._confidence_tier`` è solo un
    wrapper su quella, e farci dipendere il server significherebbe legare la
    porta MCP al modulo del client per tre righe di calcolo.
    """
    from verimem.mcp_server import _calcola_tier

    assert _calcola_tier(99.9, "llm", 70) == "high"
    assert _calcola_tier(None, None, None) == "unverified", (
        "senza punteggio l'etichetta deve dire «non verificato», non tacere: "
        "è la differenza fra «giudicato male» e «mai giudicato»"
    )


@pytest.mark.parametrize("indice", range(len(_chiamate_a_build_fact())))
def test_ogni_chiamata_del_server_passa_l_etichetta(indice: int) -> None:
    """IL presidio: ogni percorso di scrittura, non uno solo.

    Un caso per chiamata, generato dal sorgente: se qualcuno aggiunge un terzo
    percorso MCP e dimentica l'etichetta, **nasce un caso nuovo e nasce rosso**,
    senza che nessuno debba ricordarsi di questo file. È esattamente ciò che è
    successo con ``writer_principal``, curato su entrambi i chiamanti, e con
    l'etichetta, dimenticata sugli stessi due.
    """
    chiamate = _chiamate_a_build_fact()
    assert chiamate, (
        "nessuna chiamata a _build_fact trovata in mcp_server.py: se la funzione "
        "è stata rinominata o rimossa, questo file va aggiornato con lei invece "
        "di restare verde per assenza"
    )
    call = chiamate[indice]
    passati = {kw.arg for kw in call.keywords}
    assert "confidence_tier" in passati, (
        f"la chiamata a _build_fact di riga {call.lineno} non passa "
        f"confidence_tier: quel fatto entrerà nello store senza etichetta, come "
        f"i 145 misurati il 2026-08-15. Se il gate non è disponibile in quel "
        f"punto, passa esplicitamente None e scrivi perché"
    )
