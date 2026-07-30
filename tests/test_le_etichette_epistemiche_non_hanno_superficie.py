"""Le etichette epistemiche sono documentate e non hanno nessuna superficie.

Il README le promette in 18 punti (righe 158-162):

    «Epistemic labels — a fact can carry the KIND of guarantee behind it:
     proven (a named machine-checkable proof), unbeaten (held up to a declared
     bound), refuted (a named counterexample, absorbing). "Held to 10^6" and
     "proven" are never conflated.»
    «Derived knowledge, through the same gate — the composition ring derives...»

Sul corpus vivo del 2026-07-30: `epistemic` valorizzato in 0 fatti su 6457.
Verificato il perche', modulo per modulo:

    scrittura   Memory.add non accetta epistemic; nessun tool MCP lo prende o
                lo restituisce come dato; nessun comando CLI. `set_epistemic()`
                esiste su SemanticMemory ed e' chiamato solo da composer.py e
                active_probe.py, che nessuna superficie raggiunge —
                compose_daemon non e' avviato da nessuna parte.
                (Le uniche due occorrenze della PAROLA in mcp_server.py sono
                una riga di help e un commento: cercare la parola invece del
                dato faceva accendere il test sui propri commenti.)
    lettura     epistemic_health, adaptive_ledger e grounding_gate non sono
                importati ne' da mcp_server ne' da cli; l'SDK client.py nomina
                epistemic solo in un commento.

Il sottosistema e' completo e ben progettato — `make_proven` rifiuta un
riferimento vuoto perche' «a proof must be machine-checkable, not a vibe» — ed
e' scollegato dal prodotto in entrambe le direzioni.

NON si cura esponendo la sola scrittura: si scriverebbero etichette che nessuno
legge, cioe' si riempirebbe una colonna per poter dire che e' piena. Ricollegarlo
vuol dire scrittura + lettura + il ring di composizione, ed e' una decisione di
prodotto, non una patch.

Questo file tiene la misura attaccata al codice: quando il collegamento
arrivera', questi test falliranno e obbligheranno a riscrivere cosa e' cambiato.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
VERIMEM = RADICE / "verimem"


def _testo(nome: str) -> str:
    p = VERIMEM / nome
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def test_nessuna_superficie_permette_di_etichettare():
    import inspect

    from verimem.client import Memory
    firma = str(inspect.signature(Memory.add))
    assert "epistemic" not in firma, (
        "l'SDK ora accetta epistemic: il sottosistema si sta ricollegando, "
        "aggiorna questo file e il README")
    # Il criterio e' il DATO, non la parola. La prima versione cercava
    # «epistemic» nel sorgente e trovava due cose che non c'entrano: una riga
    # di help di hippo_justified_audit e un commento che avevo scritto io
    # stesso quella mattina. Un test che si accende sui propri commenti misura
    # se stesso.
    mcp = _testo("mcp_server.py")
    assert '"epistemic"' not in mcp and "epistemic=" not in mcp, (
        "un tool MCP ora accetta o restituisce l'etichetta come dato: "
        "il sottosistema si sta ricollegando, aggiorna questo file")


def test_i_moduli_che_etichettano_restano_irraggiungibili():
    """`composer` e `active_probe` sono gli unici a chiamare set_epistemic."""
    mcp, cli = _testo("mcp_server.py"), _testo("cli.py")
    for modulo in ("active_probe", "compose_daemon"):
        assert modulo not in mcp and modulo not in cli, (
            f"{modulo} e' stato esposto: aggiorna questo file")


def test_nessuna_superficie_legge_le_etichette():
    mcp, cli = _testo("mcp_server.py"), _testo("cli.py")
    for modulo in ("epistemic_health", "adaptive_ledger"):
        assert modulo not in mcp and modulo not in cli, (
            f"{modulo} e' stato esposto: ora le etichette si possono leggere, "
            f"aggiorna questo file")


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
