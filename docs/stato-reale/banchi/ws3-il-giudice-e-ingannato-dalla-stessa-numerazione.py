"""Anche il GIUDICE è ingannato dalla numerazione degli articoli?

Curando l'estrattore (`29ab5544`) avevo dichiarato che **due difese erano
cadute per ragioni diverse** e che ne avevo rialzata **una sola**::

    claim «Il numero di rate previste dal contratto e' 3.»  (INVENTATO: il
    contratto non parla di rate)
        prima della cura:  AMMESSO, grounding 100.0, L4.1 muto
        dopo   la cura:    quarantinato da L4.1 — ma grounding ANCORA 100.0

⇒ `L4.1` è stato rialzato. **Il giudice no**: continua a dare **100.0** a un
claim che la fonte non sostiene. Questo banco chiede **perché**.

L'IPOTESI, e viene da un meccanismo che ho già documentato: lo span passato al
giudice è scelto da `select_relevant_span`, che ordina i pezzi della fonte per
**sovrapposizione di token col claim**. Il claim inventato condivide con la
fonte `contratto` e **`3`** — e quel `3` nella fonte è **il numero
dell'articolo**. ⇒ **la stessa identica caratteristica testuale che ingannava
l'estrattore inganna anche il giudice**, su un layer diverso.

A/B A VARIABILE SINGOLA: **stesso claim**, e la fonte cambia **solo** per la
presenza della numerazione. Il testo delle clausole è **identico parola per
parola**.

    fonte A   «Art. 3 - La penale ...  Art. 6 - Il termine ...»
    fonte B   «La penale ...  Il termine ...»          (senza numerazione)

LA PREDIZIONE, scritta prima di eseguire: **il grounding scende da A a B** in
modo netto (>20 punti). Se resta uguale, la numerazione non c'entra e
**l'ipotesi va ritirata**.

CONDIZIONE DI FALSIFICAZIONE: `|grounding(A) - grounding(B)| <= 20` sui claim
coperti ⇒ ipotesi caduta.

DUE CONTROLLI CHE DEVONO POTER FALLIRE:
  (a) un claim **VERO** deve restare alto in ENTRAMBE le fonti: se crollasse
      anche lui, starei misurando «togliere testo abbassa tutto», non la
      numerazione;
  (b) un claim inventato con una cifra **estranea** (91) deve restare basso in
      entrambe: è la popolazione di controllo che dice che il giudice
      distingue qualcosa.

REGIME: un processo, store temporaneo vuoto, porta SDK, `validate="full"`, IT.
⚠️ Si guarda il `grounding_score`, NON l'esito: l'esito lo decide anche `L4.1`,
che ora ferma questi casi. La domanda è **cosa pensa il giudice**.

    python docs/stato-reale/banchi/ws3-il-giudice-e-ingannato-dalla-stessa-numerazione.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

#: identiche parola per parola: cambia SOLO «Art. N - » in testa alle clausole
FONTE_A = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al due per cento "
    "dell'importo contrattuale. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato dallo statuto. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro."
)
FONTE_B = (
    "La penale per il ritardo nella consegna e' pari al due per cento "
    "dell'importo contrattuale. "
    "Il termine per la contestazione dei vizi e' fissato dallo statuto. "
    "L'importo contrattuale e' di 148000 euro."
)

#: (etichetta, claim, la cifra coincide con un numero d'articolo di A?)
CASI = [
    ("INVENTATO  3 ", "Il numero di rate previste dal contratto e' 3.", True),
    ("INVENTATO  6 ", "Il numero di rate previste dal contratto e' 6.", True),
    ("INVENTATO  7 ", "Il numero di rate previste dal contratto e' 7.", True),
    ("controllo 91 ", "Il numero di rate previste dal contratto e' 91.", False),
    ("controllo 43 ", "Il numero di rate previste dal contratto e' 43.", False),
    ("VERO         ", "L'importo contrattuale e' di 148000 euro.", False),
]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print("    store TEMPORANEO vuoto · un processo · porta SDK · "
          "validate='full' · IT")
    print("    si guarda il GROUNDING, non l'esito: l'esito lo decide anche L4.1")
    print(f"    fonte A {len(FONTE_A)} char · fonte B {len(FONTE_B)} char "
          f"(differenza: solo «Art. N - »)")

    mem = Memory(str(Path(tempfile.mkdtemp()) / "giud.db"))

    print(f"\n  {'caso':<15} {'A con numeri':>13} {'B senza':>13} {'delta':>9}")
    print("  " + "-" * 54)
    righe = []
    for i, (et, claim, coperto) in enumerate(CASI):
        ga = mem.add(claim, topic=f"g/a/{i}", source=FONTE_A,
                     validate="full").get("grounding_score")
        gb = mem.add(claim, topic=f"g/b/{i}", source=FONTE_B,
                     validate="full").get("grounding_score")
        fa = float(ga) if ga is not None else -1.0
        fb = float(gb) if gb is not None else -1.0
        righe.append((et, coperto, fa, fb))
        print(f"  {et:<15} {fa:13.1f} {fb:13.1f} {fa - fb:+9.1f}")

    if any(fa < 0 or fb < 0 for _e, _c, fa, fb in righe):
        print("\n     CONTROLLO CADUTO: un grounding e' None ⇒ il giudice non ha")
        print("     girato su tutte le celle. NESSUN VERDETTO.")
        return 1

    vero = [r for r in righe if r[0].startswith("VERO")][0]
    print(f"\n  CONTROLLO (a): il VERO resta alto in entrambe? "
          f"A={vero[2]:.1f} B={vero[3]:.1f}")
    if vero[2] < 80 or vero[3] < 80:
        print("     CONTROLLO CADUTO: il claim VERO non e' alto in entrambe ⇒")
        print("     misuro «togliere testo abbassa tutto», non la numerazione.")
        return 1

    ctrl = [r for r in righe if r[0].startswith("controllo")]
    print(f"  CONTROLLO (b): i controlli con cifra estranea, in A: "
          f"{[round(r[2], 1) for r in ctrl]}")

    coperti = [r for r in righe if r[1]]
    delta_medio = sum(r[2] - r[3] for r in coperti) / max(len(coperti), 1)
    print("\n  ══ I COPERTI (cifra = numero d'articolo di A) ══")
    print(f"     grounding medio con la numerazione ... {sum(r[2] for r in coperti) / len(coperti):.1f}")
    print(f"     grounding medio SENZA ................ {sum(r[3] for r in coperti) / len(coperti):.1f}")
    print(f"     DELTA MEDIO .......................... {delta_medio:+.1f}")

    print("\n  ══ VERDETTO ══")
    if delta_medio > 20:
        print("     IPOTESI RETTA: togliere la sola numerazione fa CROLLARE il")
        print("     grounding sui claim inventati la cui cifra coincideva con un")
        print("     numero d'articolo. ⇒ LA STESSA CARATTERISTICA TESTUALE INGANNA")
        print("     ENTRAMBE LE DIFESE: l'estrattore (curato in 29ab5544) e il")
        print("     GIUDICE, che non e' curato.")
    elif abs(delta_medio) <= 20:
        print("     IPOTESI FALSIFICATA: il grounding non cambia togliendo la")
        print("     numerazione ⇒ il giudice e' ingannato da qualcos'ALTRO, e")
        print("     l'ipotesi che avevo pubblicato va ritirata. La domanda «perche'")
        print("     il giudice da' 100.0» resta APERTA.")
    else:
        print("     RISULTATO INVERSO: senza la numerazione il grounding SALE.")
        print("     Da spiegare, non da archiviare.")

    print("\n  ⚠️ LIMITI: una fonte sola in due varianti, sei claim, italiano, un")
    print("     solo modello di frase. Il grounding e' del giudice LOCALE (CE):")
    print("     con un provider llm diverso il numero puo' cambiare. E tolgo la")
    print("     numerazione dall'INTERA fonte: non isolo QUALE articolo pesa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
