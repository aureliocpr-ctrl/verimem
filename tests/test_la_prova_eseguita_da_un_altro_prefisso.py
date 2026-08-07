"""`bash:pytest tests/x.py:exit0` È pytest, e il detector «testato» lo rifiuta.

TROVATO CERCANDOLO, non per caso. Il 2026-08-04 la forma «due esiti dove ne
servono tre» è uscita tre volte da punti indipendenti — il giudice di
supersessione (manca il `neutral`), il detector L1 (manca il mondo
scientifico), gli esiti di scrittura (manca «ammetti entrambi»). Tre
occorrenze non sono una coincidenza, così l'ho cercata apposta censendo le
funzioni che rispondono `bool` a una domanda di classificazione. La famiglia
`_has_*_evidence` è saltata fuori subito, e la misura conferma:

    claim                       prova                              esito
    «è sicuro contro SQLi»      pytest:test_no_sql_injection_PASS  quarantined
    «funziona in produzione»    audit:2026-08-04:clean             quarantined
    «è stata testata»           bash:pytest tests/test_parsing:exit0  quarantined

Le cinque famiglie di prefissi sono quasi disgiunte (tested∩security = 0,
works∩security = 0, security∩quantitative = 0), quindi una prova vale per una
famiglia sola. La domanda «c'è la prova?» ha due risposte e ne servirebbero
tre: *del tipo giusto* / **di un altro tipo** / *nessuna*, e il caso di mezzo
viene schiacciato su «nessuna».

⚠️ NON SI CURANO TUTTI E TRE, E LA DIFFERENZA È IL PUNTO. `bandit:clean` per
«il modulo funziona» va rifiutato davvero: uno scanner statico non prova il
funzionamento a runtime, e unire le liste renderebbe ogni prova buona per ogni
claim — che è il modo di spegnere il detector fingendo di ripararlo.

Qui si cura il solo caso INEQUIVOCABILE: una prova che dichiara
un'ESECUZIONE (`bash:`, `cmd:`) e il cui comando invoca un RUNNER DI TEST è
una prova di test, comunque la si sia scritta. Non è il prefisso a dirlo — è
il comando, che è lì e si legge. Il claim «è stata testata» sostenuto da
`bash:pytest ...:exit0` porta esattamente l'evidenza che il detector chiede.
"""
from __future__ import annotations

import pytest

from verimem.l1_tested_detector import _has_tested_evidence

#: Prove che dichiarano un'esecuzione E invocano un runner di test.
ESECUZIONI_DI_TEST = [
    ["bash:pytest tests/test_parsing.py:exit0"],
    ["bash:python -m pytest tests/ -q:exit0"],
    ["cmd:pytest tests/test_gate.py::test_uno:exit0"],
    ["bash:npm test:exit0"],
    ["bash:cargo test --all:exit0"],
    ["bash:go test ./...:exit0"],
]

#: Prove di esecuzione che NON sono test: devono continuare a non bastare,
#: altrimenti la cura spegne il detector invece di correggerlo.
ESECUZIONI_QUALSIASI = [
    ["bash:ls -la:exit0"],
    ["bash:python -m export --check:exit0"],
    ["cmd:git status:exit0"],
    ["bash:curl https://example.com:exit0"],
]

#: Prove di ALTRE famiglie: restano fuori. Uno scanner statico non prova che
#: una cosa sia stata testata.
ALTRE_FAMIGLIE = [
    ["bandit:clean"],
    ["audit:2026-08-04:clean"],
    ["docs:testing.md"],
    ["semgrep:no-findings"],
]


@pytest.mark.parametrize("vb", ESECUZIONI_DI_TEST)
def test_un_runner_di_test_dentro_bash_e_una_prova_di_test(vb):
    """Il cuore: il comando dice `pytest`, l'exit code c'è. Rifiutarlo perché
    il prefisso è `bash:` invece di `pytest:` chiede all'utente di riscrivere
    la stessa prova in un altro formato."""
    assert _has_tested_evidence(vb), (
        f"«{vb[0]}» invoca un runner di test e riporta l'esito, e non viene "
        f"riconosciuta come prova di test")


@pytest.mark.parametrize("vb", ESECUZIONI_QUALSIASI)
def test_un_comando_qualsiasi_NON_basta(vb):
    """IL VERSO CHE RENDE LA CURA SICURA. Se bastasse `bash:` con un exit
    code, qualunque comando eseguito proverebbe qualunque cosa — e il
    detector sarebbe spento, non riparato."""
    assert not _has_tested_evidence(vb), (
        f"«{vb[0]}» non è un test e viene accettata come prova di test")


@pytest.mark.parametrize("vb", ALTRE_FAMIGLIE)
def test_le_altre_famiglie_di_prova_restano_fuori(vb):
    """L'altra metà del presidio: le cinque famiglie sono quasi disgiunte per
    una ragione. Uno scanner statico, un audit o un file di documentazione non
    provano che qualcosa sia stato ESEGUITO."""
    assert not _has_tested_evidence(vb), (
        f"«{vb[0]}» appartiene a un'altra famiglia e viene accettata")


def test_la_prova_canonica_continua_a_valere():
    """Il comportamento originale non si muove."""
    assert _has_tested_evidence(["pytest:test_parsing_PASS"])
    assert not _has_tested_evidence([])
    assert not _has_tested_evidence(None)
