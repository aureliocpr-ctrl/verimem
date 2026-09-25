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
repo. Ogni numero con `%` o nella forma `x/y` deve stare dentro un blocco generato:

    <!-- vetrina:inizio <nome> -->   ...   <!-- vetrina:fine -->

La convenzione dei marcatori e' quella che questa prova richiede; la cura (T218) la
adotta o la cambia QUI, nello stesso commit. Controllo positivo: la pagina deve contenere
almeno un numero di quella forma, altrimenti la prova non vede niente.

CHI LA CHIUDE: T218 (la vetrina generata dai banchi), T187. Oggi: ROSSA (predizione).
"""
from __future__ import annotations

import json
import re

CODICE = r'''
import json
from importlib.metadata import metadata
md = metadata("verimem")
testo = md.get_payload() if hasattr(md, "get_payload") else md.get("Description")
print("ESITO " + json.dumps({"testo": testo or ""}))
'''

#: un numero con il segno di percentuale, o due numeri separati da una sbarra
NUMERO_DI_VETRINA = re.compile(r"\d+(?:[.,]\d+)?\s?%|(?<![\w/])\d+\s?/\s?\d+(?![\w/])")
BLOCCO = re.compile(r"<!--\s*vetrina:inizio\b.*?<!--\s*vetrina:fine\s*-->", re.S)


def test_riga_5_ogni_numero_della_pagina_di_pypi_e_generato(utente):
    uscita = utente.python(CODICE)
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, f"metadati del wheel non letti: {uscita.stderr[-600:]}"
    pagina = json.loads(righe[-1][len("ESITO "):])["testo"]

    tutti = [m.group(0) for m in NUMERO_DI_VETRINA.finditer(pagina)]
    assert tutti, "CONTROLLO POSITIVO SPENTO: nessun numero con % o x/y nella pagina"

    fuori = NUMERO_DI_VETRINA.findall(BLOCCO.sub("", pagina))
    assert not fuori, (
        f"{len(fuori)} numeri su {len(tutti)} nella pagina di PyPI sono scritti a mano, "
        f"fuori da un blocco generato: {fuori[:15]}")
