"""Cosa resta scollegato del sottosistema epistemico, dopo averlo collegato.

AGGIORNATO 2026-07-31. Il mandato era «collega tutto», e tre pezzi su cinque ora
lo sono (tests/test_le_etichette_epistemiche_sono_collegate.py):

    scrittura         Memory.label · hippo_fact_label · verimem facts label
    lettura per-fatto il contratto porta `epistemic` su ogni superficie
    conteggio         `verimem status`, perche' un sottosistema a zero si veda

Questo file resta perche' UNO non lo e', e cancellarlo avrebbe nascosto
proprio la parte che manca — dopo due giorni passati a scoprire meccanismi
spenti in silenzio, sarebbe stato l'errore piu' stupido possibile:

    ring di composizione `composer` e `active_probe` — gli unici che DERIVANO
                       etichette invece di riceverle — restano irraggiungibili,
                       e `compose_daemon` non e' avviato da nessuna parte

Il test qui sotto e' scritto perche' FALLISCA quando anche quello verra'
collegato: e' un promemoria che si accende da solo, non una descrizione che
invecchia.

Contesto storico, il punto di partenza. Il README le promette in 18 punti
(righe 158-162):

    «Epistemic labels — a fact can carry the KIND of guarantee behind it:
     proven (a named machine-checkable proof), unbeaten (held up to a declared
     bound), refuted (a named counterexample, absorbing). "Held to 10^6" and
     "proven" are never conflated.»
    «Derived knowledge, through the same gate — the composition ring derives...»

Sul corpus vivo del 2026-07-30: `epistemic` valorizzato in 0 fatti su 6457.
COM'ERA ALLORA, verificato modulo per modulo — la prima riga NON vale piu':

    scrittura   [SUPERATA il 31/07] Memory.add non accettava epistemic, nessun
                tool MCP lo prendeva, nessun comando CLI. `set_epistemic()`
                esisteva su SemanticMemory ed era chiamato solo da composer.py e
                active_probe.py, che nessuna superficie raggiunge.
                (Le uniche due occorrenze della PAROLA in mcp_server.py erano
                una riga di help e un commento: cercare la parola invece del
                dato faceva accendere il test sui propri commenti.)
    lettura     [SUPERATA il 31/07 per epistemic_health] non era importato ne'
                da mcp_server ne' da cli: le etichette si scrivevano e si
                leggevano per-fatto, e non si poteva chiedere al CORPUS come
                stesse messo. Ora c'e' hippo_epistemic_health. Resta
                `adaptive_ledger`.

Il sottosistema era completo e ben progettato — `make_proven` rifiuta un
riferimento vuoto perche' «a proof must be machine-checkable, not a vibe» — e
scollegato in entrambe le direzioni.

La regola che ha guidato il collegamento: NON bastava esporre la scrittura, o si
sarebbero scritte etichette che nessuno legge — una colonna riempita per poter
dire che e' piena. Percio' sono arrivate insieme scrittura, lettura per-fatto e
conteggio, e poi la lettura aggregata. Resta il ring di composizione.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
VERIMEM = RADICE / "verimem"


def _testo(nome: str) -> str:
    p = VERIMEM / nome
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def test_la_scrittura_ORA_e_collegata():
    """Il contrario di quello che questo file diceva il 30/07: da allora si
    puo' etichettare da SDK, MCP e CILI. Sta qui perche' se qualcuno la
    scollegasse, questo file — che parla di cio' che manca — se ne accorga."""
    import inspect

    from verimem.client import Memory
    assert "label" in dir(Memory)
    assert {"kind", "proof", "bound", "counterexample"} <= set(
        inspect.signature(Memory.label).parameters)
    assert '"hippo_fact_label"' in _testo("mcp_server.py")


def test_i_moduli_che_etichettano_restano_irraggiungibili():
    """`composer` e `active_probe` sono gli unici a chiamare set_epistemic."""
    mcp, cli = _testo("mcp_server.py"), _testo("cli.py")
    for modulo in ("active_probe", "compose_daemon"):
        assert modulo not in mcp and modulo not in cli, (
            f"{modulo} e' stato esposto: aggiorna questo file")


def test_nessuna_superficie_legge_le_etichette():
    mcp, cli = _testo("mcp_server.py"), _testo("cli.py")
    # `epistemic_health` E' STATO COLLEGATO il 31/07 (hippo_epistemic_health +
    # Memory.epistemic_health): resta `adaptive_ledger`.
    assert "hippo_epistemic_health" in mcp, (
        "la lettura aggregata e' stata scollegata: era il pezzo che chiudeva "
        "il cerchio fra il verdetto scritto e la salute del corpus")
    for modulo in ("adaptive_ledger",):
        assert modulo not in mcp and modulo not in cli, (
            f"{modulo} e' stato esposto: aggiorna questo file")


def test_l_api_pretende_ancora_un_riferimento_vero():
    """L'attrito e' la parte buona del sottosistema e non va persa nel
    ricollegarlo: `proven` senza una prova nominata dev'essere un errore, non
    un'etichetta vuota — altrimenti diventa l'auto-dichiarazione che questo
    prodotto esiste per impedire."""
    from verimem.epistemic import make_proven, make_refuted, make_unbeaten
    with pytest.raises(ValueError):
        make_proven("  ")
    with pytest.raises(ValueError):
        make_unbeaten(0)
    with pytest.raises(ValueError):
        make_refuted("")
    assert make_proven("pytest:test_x_PASS")["kind"] == "proven"


def test_il_readme_continua_a_prometterle():
    """Se un giorno la promessa viene tolta invece che mantenuta, questo test
    lo dice: il disallineamento fra README e prodotto non deve poter sparire
    in silenzio da nessuno dei due lati."""
    readme = (RADICE / "README.md").read_text(encoding="utf-8", errors="replace")
    assert "Epistemic labels" in readme
