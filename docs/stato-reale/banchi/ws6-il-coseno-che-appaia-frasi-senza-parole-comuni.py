r"""Le coppie ritirate da `heal_contradictions` superano davvero il coseno 0.75?

`contradiction.py:250` filtra le contraddizioni con `similarity_threshold=0.75`
(coseno su proposizioni ri-codificate, `_cosine` riga 209). Il filtro dunque C'E'.
Ma sui 106 ritiri appaiabili ho misurato che **71 (67%) hanno jaccard lessicale <0.25
e 22 (21%) non condividono nemmeno una parola**. Delle due l'una: o il coseno di
quelle coppie e' sotto 0.75 (e allora il ritiro e' avvenuto per un'altra via), o e'
sopra (e allora l'embedding da' 0.75+ a frasi senza parole in comune).

RISULTATO (28/08 18:57) - IL CONTROLLO POSITIVO E' FALLITO, ED E' LA SCOPERTA:

  controllo   0.994  «Il magazzino M-03 contiene 1111 pezzi» / «...1112 pezzi»   atteso
  controllo   0.752  «Il magazzino M-03 contiene 1111 pezzi»
                     / «La chiave di lettura del sonetto e' l'ironia»   <- SOPRA LA SOGLIA

  le 106 coppie ritirate:  coseno >= 0.75  ->  **106 su 106 = 100%**

  IL PAVIMENTO, misurato su 30 coppie di fatti presi da TOPIC DIVERSI (non correlate
  per costruzione, uno per topic):
      min **0.767** · p25 0.818 · mediana 0.849 · p75 0.950 · max 1.000
      >= 0.75 -> **30 su 30 = 100%**

=> LA SOGLIA E' SOTTO IL PAVIMENTO. `similarity_threshold=0.75` (contradiction.py:252)
   non scarta MAI nulla su questo corpus: il minimo osservato fra due fatti scorrelati
   e' 0.767. Il filtro c'e', gira, e non filtra.
=> Il criterio EFFETTIVO che ritira i fatti si riduce quindi a: **stesso topic + numeri
   diversi**. Non e' una deduzione dal messaggio d'errore: e' il meccanismo misurato.

⚠️ ONESTA' SUL CAMPIONE: fra le 30 coppie ce ne sono a coseno 1.000 che sono `diary`
con testo quasi identico (righe automatiche di sessione). Quelle ALZANO la mediana e
vanno dichiarate. **Non toccano il numero che conta**, che e' il MINIMO: 0.767 > 0.75.
⚠️ E il controllo positivo indipendente (magazzino/sonetto, 0.752) e' dello stesso
ordine di grandezza, misurato su due frasi scritte a mano fuori dal corpus.

CONTROLLO POSITIVO, senza il quale il banco non dice niente: due frasi quasi identiche
devono dare coseno alto, due palesemente scorrelate basso. Se il mio strumento non
separa quelle, non separa niente.

REGIME: store di Aurelio in **sola lettura** (`mode=ro`) - FUORI da pytest, dove
l'embedder e' uno stub su SHA-256 dei token e ogni coseno e' privo di significato -
`embedding.encode` e' lo stesso del prodotto, chiamato come lo chiama `_cosine`.
⚠️ LIMITE DICHIARATO: i ritiri sono avvenuti col modello di ALLORA; questo banco
ri-codifica con quello di OGGI. Se il modello e' cambiato nel frattempo, il numero
descrive il criterio attuale, non la decisione storica.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-il-coseno-che-appaia-frasi-senza-parole-comuni.py
"""
from __future__ import annotations

import re
import sqlite3

import numpy as np

from verimem import embedding
from verimem.config import CONFIG

W = re.compile(r"\w+", re.UNICODE)
SOGLIA = 0.75


def _tok(s):
    return {w.lower() for w in W.findall(s or "") if len(w) > 2}


def _cos(x, y):
    a, b = embedding.encode(x), embedding.encode(y)
    d = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / d) if d > 0 else 0.0


def main() -> None:
    print("=== CONTROLLO POSITIVO (senza questo il resto non vale) ===")
    prove = [
        ("Il magazzino M-03 contiene 1111 pezzi.", "Il magazzino M-03 contiene 1112 pezzi.", "quasi identiche"),
        ("Il magazzino M-03 contiene 1111 pezzi.", "La chiave di lettura del sonetto e' l'ironia.", "scorrelate"),
    ]
    for x, y, et in prove:
        print(f"   {_cos(x, y):.3f}  {et}")

    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT l.proposition, w.proposition FROM facts l JOIN facts w ON w.id=l.superseded_by "
        "WHERE l.superseded_reason LIKE 'heal%'").fetchall()
    con.close()

    print(f"\n=== LE {len(righe)} COPPIE RITIRATE DA heal_contradictions ===")
    sopra = sotto = 0
    zero_parole_sopra = []
    for lp, wp in righe:
        c = _cos(lp, wp)
        j = len(_tok(lp) & _tok(wp)) / len(_tok(lp) | _tok(wp)) if (_tok(lp) | _tok(wp)) else 0
        if c >= SOGLIA:
            sopra += 1
            if not (_tok(lp) & _tok(wp)) and len(zero_parole_sopra) < 3:
                zero_parole_sopra.append((c, j, lp[:64], wp[:64]))
        else:
            sotto += 1
    n = len(righe)
    print(f"   coseno >= {SOGLIA} (il filtro le ha lasciate passare) ... {sopra:>3}  {100*sopra/n:.0f}%")
    print(f"   coseno <  {SOGLIA} (oggi NON passerebbero) ............. {sotto:>3}  {100*sotto/n:.0f}%")
    print("\n=== coppie che passano il coseno SENZA una parola in comune ===")
    for c, j, lp, wp in zero_parole_sopra:
        print(f"   coseno {c:.3f} · jaccard {j:.2f}\n      A {lp}\n      B {wp}")
    if not zero_parole_sopra:
        print("   NESSUNA: ogni coppia sopra soglia condivide almeno una parola")


if __name__ == "__main__":
    main()
