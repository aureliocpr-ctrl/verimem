"""I 13 candidati CONTRADDICE, separati fra chi AFFERMA e chi RACCONTA.

Il primo che ho letto a mano — GRAVITA-DIFETTI.md — nominava un test cancellato
e diceva, nella riga sopra, «rimosso dal revert». Non contraddice il codice: lo
racconta, ed e' pure preciso. Se avessi classificato dall'indizio avrei
diffamato un documento corretto.

Quindi: per ogni path che non esiste, guardo le due righe attorno alla menzione
e cerco le parole con cui un documento DICHIARA che quel file non c'e' piu'.
Chi le ha va letto lo stesso, ma parte da «probabile racconto»; chi non le ha
parte da «probabile affermazione». Il verdetto resta mio, questo ordina la coda.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

R = Path(sys.argv[1]).resolve()
INDIZI = Path(sys.argv[2])

RACCONTA = re.compile(
    r"rimoss|cancellat|elimina|revert|non esiste|piu'|più|prima di|era |allora|"
    r"recuperat|ripristinat|storic|archivi|superat|obsolet|"
    r"removed|deleted|no longer|used to|former",
    re.IGNORECASE)
PATH_RE = re.compile(r"\b((?:verimem|tests|scripts|benchmark)/[A-Za-z0-9_./-]+\.py)\b")

righe = INDIZI.read_text(encoding="utf-8").splitlines()[1:]
n_aff = n_rac = 0
print("  verdetto-di-partenza  documento                                    path mancante")
print("  " + "-" * 100)
for r in righe:
    c = r.split("\t")
    if len(c) < 3 or c[2] == "-":
        continue
    doc = R / c[0]
    testo = doc.read_text(encoding="utf-8", errors="replace").splitlines()
    for mancante in c[2].split(";"):
        for i, riga in enumerate(testo):
            if mancante in riga:
                ctx = " ".join(testo[max(0, i - 2): i + 3])
                racconta = bool(RACCONTA.search(ctx))
                if racconta: n_rac += 1
                else: n_aff += 1
                v = "racconta?" if racconta else "AFFERMA?"
                print(f"  {v:<21} {c[0][:44]:<44}  {mancante[:34]}")
                break
print("  " + "-" * 100)
print(f"  probabile racconto: {n_rac}   ·   probabile affermazione (da leggere per primi): {n_aff}")
