"""`verimem trust` su una DOMANDA non deve rispondere con una spunta verde.

TROVATO dal dogfooding in parallelo il 2026-07-30. Il comando e' un linter del
WORDING di un claim, e lo dichiara — «wording only», «the moat did NOT run»,
«this verdict is about the WORDING of the claim, not about whether it is true».
Il perimetro e' scritto e onesto.

Resta che la superficie che un utente incontra chiedendosi «posso fidarmi?»
risponde `NO FLAGS ✓` a una domanda:

    verimem trust "Quale versione di Kubernetes usa il cluster di OnlyPaws?"
    -> Anti-confab trust check   NO FLAGS ✓ (wording only — ...)

Su una domanda quel verdetto non e' impreciso, e' VACUO: non c'e' nessuna
affermazione di cui esaminare le parole. Un utente che legge la spunta e salta
il testo fine porta via «verimem dice che va bene» da una domanda che non ha
risposta nel corpus — il contrario esatto del prodotto.

CURA: riconoscere l'input interrogativo e dirlo, indirizzando allo strumento
giusto (`recall` per cercare, `ignorance` per sapere cosa manca). Non blocca e
non cambia il codice d'uscita: aggiunge la riga che manca.
"""
from __future__ import annotations

import re

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _out(*args: str) -> str:
    r = runner.invoke(app, ["trust", *args])
    return _ANSI.sub("", r.output).replace("\n", " ")


def test_una_domanda_viene_riconosciuta_come_tale():
    testo = _out("Quale versione di Kubernetes usa il cluster di OnlyPaws?")
    assert "question" in testo.lower() or "domanda" in testo.lower(), (
        f"una domanda ottiene lo stesso verdetto di un claim:\n{testo}")


def test_indirizza_allo_strumento_giusto():
    """Dire «non e' il mio mestiere» senza dire quale lo sia lascia l'utente
    dov'era."""
    testo = _out("Che tempo fa a Berlino domani?")
    assert "recall" in testo or "ignorance" in testo, testo


def test_un_claim_normale_non_cambia_comportamento():
    """La cura non deve toccare il caso per cui il comando esiste."""
    testo = _out("Il server di produzione sta a Francoforte.")
    assert "question" not in testo.lower(), testo
    assert "Anti-confab trust check" in testo


def test_un_claim_che_finisce_con_punto_interrogativo_dentro_le_virgolette():
    """Falsificazione del criterio: il riconoscimento guarda la FINE della
    frase, quindi un claim che cita una domanda non deve essere scambiato."""
    testo = _out('La domanda "che ore sono?" e\' stata posta due volte.')
    assert "question" not in testo.lower(), (
        f"un claim che CITA una domanda e' stato scambiato per una domanda:\n"
        f"{testo}")
