"""Il secondo cancello del rilascio si chiude da solo, e nessuno se ne accorge.

`scripts/controlla_registro.py` è il **veto** di `publish.yml` (riga 203: «`return
1` -> esce non-zero e FERMA il job»): impedisce che gli identificativi delle
sessioni di lavoro escano col pacchetto — finirebbero su PyPI e, per le
``description`` dei tool MCP, verrebbero letti a runtime dall'agente dell'utente.

STORIA, letta da `git log`: quel veto è stato riaperto **almeno sei volte**::

    4a2be695  registro: un mio commento di ieri fermava il veto del publish
    397c6375  registro: l'ultima riga che il veto del publish trattiene
    1681a4b9  registro: il docstring di _proposizione_di portava identificativi
    2b621050  pkg: il wheel 0.7.6 portava fuori sette identificativi, adesso zero
    e799293a  compat: un identificativo interno era finito nel pacchetto e
              bloccava il rilascio
    7e3b8b28  scripts: il controllo del registro non boccia più il collaudo

Il 2026-08-26 si è richiuso **due volte in tre ore**. Non è disattenzione: è
strutturale. Scriviamo commenti densi mentre lavoriamo (lo prevede il commento
di `publish.yml`: «il debito cresce perché scriviamo referti e commenti»), e i
banchi si chiamano `wsN-...` per costruzione — 29 file in
`docs/stato-reale/banchi/`. Ogni citazione di un banco dentro `verimem/` chiude
il cancello.

⚠️ IL BUCO CHE QUESTO FILE CHIUDE, e non è il veto: è la sua VISIBILITÀ.
Esistono già due presidi e nessuno dei due guarda lo stato del pacchetto:

    test_controlla_registro_distingue_prosa_da_codice   lo STRUMENTO funziona?
    test_la_pubblicazione_ha_un_cancello                la STRUTTURA del workflow
                                                        (ws8, 2026-08-15)

Verificano che il misuratore sia buono e che il cancello esista. **Nessuno
verifica che il pacchetto sia pulito ADESSO** — e quel veto non compare in
nessun run di `ci`, perché vive dentro `publish.yml`, che parte al tag. ⇒ Il
cancello si chiude in silenzio e lo si scopre quando si prova a rilasciare.

⚖️ Questo presidio NON aggiunge un blocco: rende visibile un blocco che esiste
già. Se il package porta un identificativo, il rilascio è fermo comunque —
cambia solo che lo si sa al push invece che al tag.

📏 PERIMETRO, dichiarato perché non coincide con quello del veto: qui si guarda
la cartella `verimem/`, il veto guarda l'ARTEFATTO. Sono vicini ma non uguali
(l'artefatto del 26/08 conteneva 422 file .py). Un identificativo nel package
compare in entrambi; uno in `tests/` o `benchmark/` in nessuno dei due. Chi
volesse la misura esatta deve costruire il wheel, che è lento e finirebbe fuori
da `ci` — e un presidio che non gira è un presidio che non esiste.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
PRESIDIO = RADICE / "scripts" / "controlla_registro.py"
PACKAGE = RADICE / "verimem"


def _esegui(cartella: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PRESIDIO), str(cartella)],
                          capture_output=True, text=True, errors="replace",
                          timeout=300)


# CHIUSO. Qui stava un `xfail(strict=True)` intestato a @ws3: il package portava
# fuori il nome di un banco di sessione, citato da `anti_confab_gate.py`. Il
# difetto e' stato curato da `fa850457` (29/08, Agent: TARA) — i riferimenti ai
# banchi sono resi navigabili per argomento invece che per nome di file.
# Verificato il 30/08: `git grep -E "ws[0-9]-[a-z]" -- verimem/*.py` -> zero
# occorrenze, e il presidio passa da se'. Il marcatore e' tolto perche' la sua
# stessa `reason` lo prescriveva: «diventa XPASS(strict) da se' quando il package
# torna pulito, e allora questa riga va TOLTA».
def test_il_package_non_porta_identificativi_di_sessione():
    """Il cuore: lo stato del pacchetto ORA, non la bontà dello strumento."""
    esito = _esegui(PACKAGE)
    assert esito.returncode == 0, (
        "il veto di `publish.yml` è CHIUSO: il pacchetto porterebbe fuori "
        "identificativi interni, e il rilascio si fermerebbe al tag senza che "
        "nessun run di `ci` lo abbia detto.\n"
        f"{esito.stdout[-900:]}")


def test_CONTROLLO_lo_strumento_TROVA_quando_c_e_qualcosa(tmp_path):
    """La difesa, e senza di lei il test sopra è inutile.

    Un presidio che passa perché lo strumento è rotto — script mancante, uscita
    sempre zero, cartella sbagliata — si legge esattamente come un pacchetto
    pulito. È la classe «una misura che non c'è si legge come una misura
    perfetta», che in questa casa è già costata. Quindi si verifica che su una
    cartella con un identificativo lo strumento lo TROVI davvero.
    """
    finta = tmp_path / "verimem"
    finta.mkdir()
    (finta / "modulo.py").write_text(
        '"""Un modulo di prova.\n\n'
        'Questa riga porta un identificativo di sessione: misurato da @ws4.\n'
        '"""\n', encoding="utf-8")
    esito = _esegui(finta)
    assert esito.returncode != 0, (
        "lo strumento NON ha trovato un identificativo che c'è: allora il test "
        f"qui sopra non sta misurando niente.\n{esito.stdout[-600:]}")
    assert "identificativo" in esito.stdout.lower(), esito.stdout[-600:]


def test_CONTROLLO_una_cartella_pulita_passa(tmp_path):
    """L'altra metà: se lo strumento bocciasse sempre, il test principale
    sarebbe rosso per sempre e verrebbe disattivato — che è il modo in cui un
    veto muore. Su codice senza identificativi deve tacere."""
    pulita = tmp_path / "verimem"
    pulita.mkdir()
    (pulita / "modulo.py").write_text(
        '"""Un modulo di prova, senza attribuzioni interne."""\n\n'
        'def somma(a, b):\n    return a + b\n', encoding="utf-8")
    esito = _esegui(pulita)
    assert esito.returncode == 0, (
        "lo strumento boccia una cartella pulita: un veto che blocca sempre "
        f"viene disattivato, ed è il suo stesso docstring a dirlo.\n{esito.stdout[-600:]}")
