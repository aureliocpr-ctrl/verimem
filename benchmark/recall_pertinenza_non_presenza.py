"""Il recall separa «fuori tema» da «in tema». NON separa «c'è» da «non c'è».

Misura la distanza fra tre popolazioni di domande, sul corpus che gli passi, in
SOLA LETTURA. La terza è quella che conta e di solito manca dai banchi:

  NOTE    quasi copie di proposizioni reali        -> il corpus SA la risposta
  VICINE  le stesse frasi con UN identificatore
          cambiato, o un attributo che non esiste  -> il corpus NON la sa
  IGNOTE  domini del tutto estranei                -> il corpus non c'entra nulla

Misurato 2026-08-26 su un corpus da 14k fatti (n=40/40/42), DUE esecuzioni a
tre minuti di distanza — e i numeri non coincidono, mentre la conclusione si':

                      col rerank              col rerank ANDATO IN TIMEOUT
                      (min/mediana/max)       («exceeded 3.0s budget ->
                                                keeping bi-encoder order»)
    NOTE              0.856/0.921/0.957       0.838/0.908/0.961
    VICINE            0.867/0.909/0.949       0.841/0.900/0.944
    IGNOTE            0.768/0.804/0.842       0.759/0.796/0.835
    soglia migliore   0.849                   0.837
    NOTE sopra        40/40                   40/40
    IGNOTE sotto      42/42                   42/42
    VICINE sopra      40/40                   40/40   <- il dato non c'e' e passano TUTTE
    min VICINE > min NOTE?   0.867 > 0.856    0.841 > 0.838

⇒ I VALORI si muovono col regime e col corpus (qui ci scrivono in otto). LA
RELAZIONE no: in entrambi i regimi il minimo delle VICINE resta sopra il minimo
delle NOTE, e le VICINE passano tutte la soglia migliore possibile. Per questo
il banco STAMPA i suoi numeri a ogni esecuzione invece di asserirli: la cosa da
leggere e' il confronto fra le tre righe, non la terza cifra decimale.

Il minimo delle VICINE (0.867) sta SOPRA il minimo delle NOTE (0.856): nessuna
soglia può separarle, e non è un problema di taratura — l'informazione non è nel
punteggio. Da qui la riga che tiene insieme diversi difetti già misurati
altrove (identificatore scambiato servito ad alta relevance; falsità per
omissione ammesse dal gate; un claim non sostenuto che torna primo sul fatto che
lo smentisce): **il prodotto misura la PERTINENZA, non la PRESENZA**.

⚠️ PERCHE' LA TERZA POPOLAZIONE NON E' UN DETTAGLIO. Con NOTE e IGNOTE soltanto,
questo banco dice «separazione perfetta» e la conclusione è vera e inutile: sono
quasi-copie contro domini alieni, un compito che nessun agente incontra. La
prima versione, con n=4 per popolazione, diceva l'OPPOSTO («si sovrappongono»).
Tre esiti diversi dallo stesso codice, al variare di come sono costruite le
popolazioni. ⇒ **Allargare la popolazione non basta se allargando si semplifica
il compito**: il numero grande dà la risposta sbagliata con più cifre decimali.

Run:  python -m benchmark.recall_pertinenza_non_presenza [percorso/del/semantic.db]
      (senza argomento usa CONFIG.semantic_db — sempre in sola lettura)
Exit: 0 se il banco ha potuto misurare (tre popolazioni non vuote e il controllo
      di separabilità NOTE/IGNOTE eseguito); 2 se una popolazione è vuota,
      perché allora i numeri non sono leggibili.
"""
from __future__ import annotations

import pathlib
import random
import re
import sqlite3
import statistics
import sys

SEME = 20260826
#: sei domini deliberatamente lontani da un corpus tecnico
SEMI_IGNOTI = [
    "ricetta della {} alla romana",
    "chi ha vinto il torneo di {} nel 1998",
    "qual e il punto di ebollizione del {}",
    "quale compagnia vola a {}",
    "come si pota un albero di {}",
    "quanti abitanti ha la citta di {}",
]
PAROLE = ["carbonara", "paella", "ramen", "borscht", "tiramisu"]


def _proposizioni(db_path: str, quante: int) -> list[str]:
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in c.execute(
            "SELECT proposition FROM facts WHERE status != 'quarantined' "
            "AND superseded_by IS NULL AND length(proposition) BETWEEN 40 AND 160 "
            "ORDER BY created_at DESC LIMIT 400")]
    finally:
        c.close()
    return random.Random(SEME).sample(rows, min(quante, len(rows)))


def _vicina(domanda: str) -> str:
    """Stessa domanda, ma sul dato che il corpus NON ha: un identificatore
    diverso, o un attributo che non è mai stato scritto."""
    cambiata = re.sub(r"\b\d+\b", lambda m: str(int(m.group(0)) + 7717), domanda, count=1)
    return cambiata if cambiata != domanda else domanda + " e il suo colore di targa"


def main(db_path: str | None = None) -> int:
    from verimem.config import CONFIG
    from verimem.semantic import SemanticMemory

    db = db_path or str(CONFIG.semantic_db)
    print(f"  corpus (SOLA LETTURA): {db}")          # il percorso PRIMA dei numeri
    campione = _proposizioni(db, 40)
    note = [" ".join(p.split()[:9]) for p in campione]
    vicine = [_vicina(d) for d in note]
    rnd = random.Random(SEME)
    ignote = [s.format(rnd.choice(PAROLE)) for s in SEMI_IGNOTI for _ in range(7)]

    #: SemanticMemory vuole un Path: una str passa i controlli e cade a runtime
    sm = SemanticMemory(db_path=pathlib.Path(db))

    def top1(domande: list[str]) -> list[float]:
        out = []
        for q in domande:
            hits = sm.recall(q, k=3)
            if not hits:
                continue
            s = hits[0][1] if isinstance(hits[0], (list, tuple)) and len(hits[0]) > 1 else None
            if isinstance(s, (int, float)):
                out.append(float(s))
        return out

    tn, tv, ti = top1(note), top1(vicine), top1(ignote)
    if not (tn and tv and ti):
        print("  una popolazione e' VUOTA: i numeri sotto non sarebbero leggibili.")
        return 2

    print(f"  {'popolazione':<32} {'n':>3}   min / mediana / max del top-1")
    for etichetta, t in (("NOTE   (quasi copie dal corpus)", tn),
                         ("VICINE (in tema, dato ASSENTE)", tv),
                         ("IGNOTE (sei domini alieni)", ti)):
        print(f"  {etichetta:<32} {len(t):>3}   "
              f"{min(t):.3f} / {statistics.median(t):.3f} / {max(t):.3f}")

    soglia = (max(ti) + min(tn)) / 2
    print()
    print(f"  una soglia a {soglia:.3f} — la migliore possibile fra NOTE e IGNOTE:")
    print(f"    NOTE sopra   {sum(1 for x in tn if x >= soglia)}/{len(tn)}"
          f"      IGNOTE sotto {sum(1 for x in ti if x < soglia)}/{len(ti)}")
    passano = sum(1 for x in tv if x >= soglia)
    print(f"    VICINE sopra {passano}/{len(tv)}"
          f"   <- il dato NON c'e' e passano lo stesso")
    print()
    print(f"  minimo VICINE {min(tv):.3f}  contro  minimo NOTE {min(tn):.3f}"
          f"  ->  {'nessuna soglia le separa' if min(tv) >= min(tn) else 'separabili'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
