"""RIGA 5 — i numeri in vetrina sono veri.

LA PROMESSA. Lista chiusa della 0.7.7, riga 5 (21/09 21:5x). La pagina che l'utente legge
prima di installare e' la pagina di PyPI, cioe' la descrizione che il wheel porta nei suoi
metadati (`pyproject.toml`: `readme = "README.md"`). Ogni numero misurato che vi compare
deve essere RIPRODUCIBILE: generato da un banco, con sha, data e comando, non scritto a
mano. La regola e' quella della RICERCA del 21/09 §5: «un test in CI fallisce se nel
README compare un numero con `%` o `/` fuori dai marcatori».

COSA VEDE L'UTENTE. Oggi un numero scritto a mano che invecchia: il 21/09 16 dei 48
numeri in vetrina erano stantii (rimisura del 21/09), e il banco della matrice dichiarava
nel docstring 100/25 ed eseguiva 112/28 (T187).

LA PROVA. Si legge la descrizione DAL WHEEL INSTALLATO (`importlib.metadata`), non dal
repo. Ogni numero con `%` o nella forma `x/y` che la pagina MOSTRA deve stare fra i due
marcatori del registro G4, che lo rende dal banco (`--render`) e lo controlla
(`--check-docs`):

    <!-- g4:<id> -->0.87<!-- /g4 -->

Una convenzione sola, definita in un punto solo: il marcatore si legge da
`benchmark/repro_all.py` (`_MARKER`), non si ricopia qui. I commenti HTML PyPI non li
mostra, quindi non contano; un commento finisce al primo `-->`, come nel browser.
Controllo positivo: la pagina deve contenere almeno un numero di quella forma, altrimenti
la prova non vede niente.

CHI LA CHIUDE: T218 (la vetrina generata dai banchi), T187; i numeri scritti a mano uno
per uno, registrati e marcati o tolti con la ragione (decisione del lead, 30/09). Oggi:
ROSSA finche' ne resta uno fuori dai marcatori.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

CODICE = r'''
import json
from importlib.metadata import metadata
md = metadata("verimem")
testo = md.get_payload() if hasattr(md, "get_payload") else md.get("Description")
print("ESITO " + json.dumps({"testo": testo or ""}))
'''

#: un numero con il segno di percentuale, o due numeri separati da una sbarra
NUMERO_DI_VETRINA = re.compile(r"\d+(?:[.,]\d+)?\s?%|(?<![\w/])\d+\s?/\s?\d+(?![\w/])")
#: un commento HTML, anche su piu' righe; finisce al primo `-->`
COMMENTO = re.compile(r"<!--.*?-->", re.S)


def _marcatore_g4() -> re.Pattern[str]:
    """Il marcatore del registro G4, letto dal registro stesso (solo libreria standard)."""
    percorso = Path(__file__).resolve().parents[1] / "benchmark" / "repro_all.py"
    spec = importlib.util.spec_from_file_location("repro_all_per_la_riga_5", percorso)
    registro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registro)
    return registro._MARKER


def numeri_scritti_a_mano(pagina: str) -> tuple[list[str], list[str]]:
    """(tutti, fuori): i numeri con % o x/y che la pagina mostra, e quelli fuori dai marcatori g4.

    Si toglie ogni commento (anche i due del marcatore) e si tiene, per ogni carattere
    rimasto, dove stava nel sorgente: un numero e' generato se comincia dentro il testo di
    un marcatore.
    """
    generati = [m.span("text") for m in _marcatore_g4().finditer(pagina)]
    pezzi, origine, pos = [], [], 0
    for m in COMMENTO.finditer(pagina):
        pezzi.append(pagina[pos:m.start()])
        origine.extend(range(pos, m.start()))
        pos = m.end()
    pezzi.append(pagina[pos:])
    origine.extend(range(pos, len(pagina)))
    tutti, fuori = [], []
    for m in NUMERO_DI_VETRINA.finditer("".join(pezzi)):
        tutti.append(m.group(0))
        if not any(a <= origine[m.start()] < b for a, b in generati):
            fuori.append(m.group(0))
    return tutti, fuori


def test_riga_5_ogni_numero_della_pagina_di_pypi_e_generato(utente):
    uscita = utente.python(CODICE)
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, f"metadati del wheel non letti: {uscita.stderr[-600:]}"
    pagina = json.loads(righe[-1][len("ESITO "):])["testo"]

    tutti, fuori = numeri_scritti_a_mano(pagina)
    assert tutti, "CONTROLLO POSITIVO SPENTO: nessun numero con % o x/y nella pagina"
    assert not fuori, (
        f"{len(fuori)} numeri su {len(tutti)} nella pagina di PyPI sono scritti a mano, "
        f"fuori da un blocco generato: {fuori[:15]}")
