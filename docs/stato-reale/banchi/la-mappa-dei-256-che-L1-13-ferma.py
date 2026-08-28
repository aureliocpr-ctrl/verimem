"""LA MAPPA DEI 256 CHE `L1.13` FERMA — descrittiva, non normativa.

W7-33 ha misurato che `L1.13` ferma **256 dei 1074** quarantinati vivi, e il
campione di sei righe suggeriva che fossero TITOLI di referto («*Test fatto del
Round 5*», «*Threat Model COMPLETATO*»). ⚠️ **Sei righe non sono una classe**:
una regolarita' vista su due o tre casi non sopravvive quasi mai a dieci.

Quindi qui NON invento un criterio: misuro la distribuzione e la consegno. Chi
cura sapra' dove sta il peso invece di dedurlo da un campione che ho scelto io.

Tre domande, tutte descrittive:
  ① QUALI parole scattano, e con che frequenza? (dove sta il peso)
  ② Il participio e' scritto TUTTO MAIUSCOLO? (marcatore tipografico di titolo)
  ③ Il participio compare NELLA PRIMA META' della proposizione? (in un titolo
     sta presto; in un'affermazione «il lavoro e' stato completato» sta in fondo)

⚠️ Il ② e il ③ sono INDIZI, non definizioni: la memoria del progetto registra
gia' che «la quota di maiuscole e' scartata, servirebbe un dizionario». Li
misuro perche' un numero su 256 vale piu' di un'impressione su 6, e li
consegno come tali.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se una sola parola copre quasi tutto, la «classe» e' un caso singolo e la
     dico cosi'.
 (2) le due popolazioni: misuro gli indizi ② e ③ ANCHE sui claim che L1.13
     ferma e che NON sono titoli — cioe' sui self-claim veri del mio banco. Se
     un indizio non separa le due popolazioni, non e' un indizio.

    python -u docs/stato-reale/banchi/la-mappa-dei-256-che-L1-13-ferma.py
"""

from __future__ import annotations

import collections
import sqlite3
import sys

# I self-claim VERI: la popolazione opposta, quella che L1.13 deve fermare.
SELFCLAIM = [
    "La migrazione e' completata e tutti i test passano.",
    "The migration is complete and all tests pass.",
    "Il lavoro e' stato completato.",
    "The task is done.",
    "Il refactoring e' finito e la suite e' verde.",
    "The cleanup is done and the branch is closed.",
]


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT proposition FROM facts "
        "WHERE status='quarantined' AND superseded_by IS NULL"))
    print(f"  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {len(righe)}")

    def analizza(prop):
        w = detect_unsupported_completion_claim(proposition=prop or "",
                                                verified_by=[])
        if w is None:
            return None
        mt = w.matched_text
        pos = (prop or "").find(mt)
        meta = len(prop or "") / 2.0
        return {
            "parola": mt.casefold(),
            "urlata": mt.isupper() and len(mt) > 1,
            "presto": 0 <= pos < meta,
        }

    fermati = [a for a in (analizza(r[0]) for r in righe) if a]
    n = len(fermati)
    print(f"  fermati da L1.13: {n}")
    if not n:
        print("  NON RIUSCITO: zero fermati, non ho misurato niente.")
        return 1

    print("\n  == ① QUALI PAROLE, e con che peso")
    dist = collections.Counter(a["parola"] for a in fermati)
    for parola, quante in dist.most_common(12):
        print(f"     {quante:>4}  ({100.0 * quante / n:>4.1f}%)  {parola}")
    prima = dist.most_common(1)[0]
    print(f"     [parole distinte: {len(dist)}]")

    urlate = sum(1 for a in fermati if a["urlata"])
    presto = sum(1 for a in fermati if a["presto"])
    print("\n  == ② e ③ GLI INDIZI, sui 256")
    print(f"     participio TUTTO MAIUSCOLO     : {urlate} su {n}"
          f"   ({100.0 * urlate / n:.1f}%)")
    print(f"     participio nella PRIMA META'   : {presto} su {n}"
          f"   ({100.0 * presto / n:.1f}%)")

    print("\n  == LA POPOLAZIONE OPPOSTA: gli stessi indizi sui self-claim veri")
    op = [a for a in (analizza(s) for s in SELFCLAIM) if a]
    if not op:
        print("     CADUTO - il detector non ferma nemmeno i self-claim: non")
        print("     posso confrontare le due popolazioni.")
        return 1
    op_url = sum(1 for a in op if a["urlata"])
    op_pre = sum(1 for a in op if a["presto"])
    print(f"     participio TUTTO MAIUSCOLO     : {op_url} su {len(op)}")
    print(f"     participio nella PRIMA META'   : {op_pre} su {len(op)}")

    print("\n  -- CONTROLLO (1): e' una classe o un caso singolo?")
    if prima[1] > 0.7 * n:
        print(f"     UN CASO SINGOLO - «{prima[0]}» da sola copre {prima[1]} su"
              f" {n}: non e' una classe, e' una parola.")
    else:
        print(f"     una CLASSE - la parola piu' frequente («{prima[0]}»,"
              f" {prima[1]}) copre il {100.0 * prima[1] / n:.0f}%,")
        print(f"     e le parole distinte sono {len(dist)}.")

    print("\n  -- CONTROLLO (2): gli indizi separano? COPERTURA e PRECISIONE")
    # ⚠️ LA PRIMA VERSIONE DI QUESTO CONTROLLO ERA SBAGLIATA, e l'errore vale
    # piu' del risultato: chiedevo `copertura - falsi >= 0.30`, cioe' una
    # soglia di COPERTURA. Ma un indizio che serve ad ASSOLVERE («questo e' un
    # titolo, non fermarlo») si giudica sulla PRECISIONE: se nessun self-claim
    # lo mostra, l'indizio e' affidabile su cio' che copre, anche se copre
    # poco. Le due grandezze vanno lette separate, mai sommate in un verdetto.
    q_url, q_pre = urlate / n, presto / n
    o_url, o_pre = op_url / len(op), op_pre / len(op)
    for nome, cop, falsi, nfalsi in (
            ("TUTTO MAIUSCOLO", q_url, o_url, op_url),
            ("PRIMA META'", q_pre, o_pre, op_pre)):
        print(f"     {nome}")
        print(f"        COPERTURA sui 256      : {cop:.1%}")
        print(f"        FALSI sui self-claim   : {nfalsi} su {len(op)}"
              f"  ({falsi:.0%})")
        if nfalsi == 0 and cop > 0:
            print("        ⇒ PRECISO ma PARZIALE: assolve solo cio' che copre,"
                  " e li' non sbaglia.")
        elif falsi >= cop - 0.10:
            print("        ⇒ RUMORE: mostra la stessa quota nelle due"
                  " popolazioni, non porta informazione.")
        else:
            print("        ⇒ parziale: guarda i due numeri prima di citarlo.")
    print(f"\n     ⚠️ La popolazione opposta e' di SOLI {len(op)} casi: una")
    print("     precisione su sei non e' una precisione, e' un'assenza di")
    print("     controesempi. Va allargata prima di appoggiarci una cura.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
