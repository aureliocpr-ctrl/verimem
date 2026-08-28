# -*- coding: utf-8 -*-
"""IL PUNTO 3 DELLA DIREZIONE, applicato alle MIE celle.

La DIREZIONE di `lead-audit` del 28/08 ore 20:09, punto 3 (da @ws8 e @ws7):
«misuriamo con un presidio in piu' di chi installa, e questo GONFIA I VERDI —
27 verdi del cruscotto potrebbero non reggere in regime installato».

Il censimento del cruscotto e' loro. Ma le celle che ho scritto io sono mie, e
tutte le misure di stasera le ho fatte con NOVE variabili d'ambiente nostre
attive, fra cui proprio quella che @ws8 ha nominato:

    ENGRAM_ADMISSION_GATE=1        HIPPO_ENCODE_DELEGATE_ONLY=1
    ENGRAM_DECAY_ENABLED=1         HIPPO_DATA_DIR=...
    ENGRAM_BRIEFING_MIN_MATCHED=4  ENGRAM_DATA_DIR=...
    ENGRAM_BRIEFING_THRESHOLD=0.40 ENGRAM_TELEMETRY_PREFIXES=builtin
    HIPPO_EXPOSE_TOOLS=...

Un utente che fa `pip install verimem` non ne ha nessuna.

Questo banco rifa' la misura che sta dietro la mia cella VERDE — la cifra
inventata fermata su fonti di ogni lunghezza — e va eseguito DUE volte:

    con le nostre     python <banco>
    senza le nostre   env -u ENGRAM_ADMISSION_GATE -u HIPPO_ENCODE_DELEGATE_ONLY \
                          -u ENGRAM_DECAY_ENABLED -u ENGRAM_BRIEFING_MIN_MATCHED \
                          -u ENGRAM_BRIEFING_THRESHOLD -u ENGRAM_TELEMETRY_PREFIXES \
                          -u HIPPO_EXPOSE_TOOLS python <banco>

(`HIPPO_DATA_DIR` e `ENGRAM_DATA_DIR` restano: il banco usa un database
temporaneo suo, quindi non toccano il giudizio — e toglierle misurerebbe il
percorso del datastore, non il gate.)

Il banco stampa quali delle nove sono attive nel processo che lo esegue, cosi'
il confronto fra le due esecuzioni e' leggibile senza fidarsi di chi lo lancia.

  se i verdetti coincidono nelle due esecuzioni
     -> la cella e' verde anche fuori da casa nostra
  se cambiano
     -> e' un verde-di-casa e va marcato «DA RIVERIFICARE IN REGIME INSTALLATO»

CONTROLLO CHE DEVE POTER FALLIRE: la cifra del claim non dev'essere nella fonte
a nessuna lunghezza.

    python docs/stato-reale/banchi/i-miei-verdi-sono-verdi-di-casa.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

NOSTRE = [
    "ENGRAM_ADMISSION_GATE", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_DECAY_ENABLED",
    "ENGRAM_BRIEFING_MIN_MATCHED", "ENGRAM_BRIEFING_THRESHOLD",
    "ENGRAM_TELEMETRY_PREFIXES", "HIPPO_EXPOSE_TOOLS",
]

BASE = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
CLAUSOLE = [
    "Le parti danno atto di aver preso visione integrale del presente accordo.",
    "Il foro competente e' quello della sede del committente.",
    "Le comunicazioni avvengono a mezzo di posta elettronica certificata.",
    "Il presente atto e' redatto in duplice originale.",
]
LUNGHEZZE = [0, 400, 1200, 3000]
CLAIM = "La cauzione definitiva e' pari a 99999 euro."


def _fonte(extra: int) -> str:
    if extra <= 0:
        return BASE
    pezzi, i = [], 0
    while sum(len(p) + 1 for p in pezzi) < extra:
        pezzi.append(CLAUSOLE[i % len(CLAUSOLE)])
        i += 1
    return BASE + " " + " ".join(pezzi)


def main() -> int:
    attive = [v for v in NOSTRE if v in os.environ]
    print(f"  variabili NOSTRE attive in questo processo: {len(attive)} su {len(NOSTRE)}")
    for v in attive:
        print(f"     {v}={os.environ[v][:40]}")
    if not attive:
        print("     (nessuna: questa e' l'esecuzione «da utente»)")

    for n in LUNGHEZZE:
        if "99999" in _fonte(n):
            print(f"CONTROLLO CADUTO a +{n}: la cifra e' nella fonte")
            return 1
    print(f"  CONTROLLO retto: la cifra inventata non e' in nessuna delle {len(LUNGHEZZE)} fonti\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "casa.db"))

    print(f"  {'fonte':>7}   {'esito':<13} {'ground':>7}")
    print("  " + "-" * 34)
    esiti = []
    for n in LUNGHEZZE:
        fonte = _fonte(n)
        ric = mem.add(CLAIM, topic=f"casa/{n}", source=fonte, validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        esiti.append((len(fonte), st, g))
        print(f"  {len(fonte):>7}   {st:<13} {g:7.1f}")

    fermati = sum(1 for _c, st, _g in esiti if st == "quarantined")
    print(f"\n  RIGA DA CONFRONTARE: fermati {fermati} su {len(esiti)} · "
          f"env nostre attive {len(attive)} · "
          f"ground {min(g for _c, _s, g in esiti):.1f}-{max(g for _c, _s, g in esiti):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
