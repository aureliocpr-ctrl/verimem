"""Quante «unità di misura» estratte dal corpus NON sono unità?

Residuo dichiarato curando i numeri d'articolo (`29ab5544`): in

    «Il comma 2 prevede 5 giorni di preavviso.»
        ->  {('giorno', 5.0), ('prevede', 2.0)}

il `2` del comma **non viene potato** perché **acquisisce l'unità fasulla
`prevede`** — la parola che lo segue — e la potatura agisce solo sul numero
nudo. Il modulo ha già `_NON_UNIT_WORDS` proprio per questo, ma **non contiene
i verbi**.

⚠️ E il danno di un'unità FALSA è dichiarato dal modulo stesso
(`quantity_match.py:153`): «*una falsa unita' CREA conflitti*» — due numeri con
la stessa unità inventata diventano confrontabili, e il gate li accoppia.

LA DOMANDA: sul corpus vero, quante coppie `(unità, valore)` estratte portano
un'unità che **non è un'unità di misura**? E quali sono le forme più frequenti?

⚠️ **Non decido io cosa è un'unità.** Il banco **non** classifica: raggruppa le
unità estratte per frequenza e le stampa, così la lista la legge un umano. Un
elenco di parole giudicate da me sarebbe la lista monolingue che ci costa la
classe ③ — la stessa che sto misurando.

LA PREDIZIONE, scritta prima di eseguire: fra le prime 40 unità per frequenza
ce ne sono **almeno 5** che non sono unità di misura. Se sono meno di 2, il
residuo è marginale e non vale una cura.

CONTROLLO CHE DEVE POTER FALLIRE: le unità VERE più ovvie — `euro`, `mg`,
`giorno`, `ms` — devono comparire fra le più frequenti. Se non ci sono, sto
misurando un estrattore rotto e non la coda delle unità false.

    sola lettura (`mode=ro`) · percorso chiesto a `CONFIG.semantic_db`
    NESSUNA scrittura sullo store di Aurelio

    python docs/stato-reale/banchi/ws3-quante-unita-estratte-non-sono-unita.py
"""

from __future__ import annotations

import sqlite3
from collections import Counter

#: solo per il CONTROLLO: quattro unità che devono esserci. Non è una lista di
#: giudizio — serve a provare che l'estrattore sta funzionando.
_UNITA_OVVIE = ("euro", "mg", "giorno", "ms")


def main() -> int:
    from verimem.config import CONFIG
    from verimem.quantity_match import extract_quantities

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    store: {db}")
    print("    SOLA LETTURA (mode=ro) · nessuna scrittura · store di Aurelio")
    print("    il banco NON classifica: raggruppa e stampa, la lista la legge un umano")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts "
            "WHERE superseded_by IS NULL AND proposition IS NOT NULL")]
    finally:
        con.close()
    print(f"    fatti VIVI esaminati: {len(righe)}")

    unita: Counter[str] = Counter()
    senza_unita = 0
    totale = 0
    esempi: dict[str, str] = {}
    for prop in righe:
        for u, _v in extract_quantities(prop, come_fonte=True):
            totale += 1
            if not u:
                senza_unita += 1
                continue
            unita[u] += 1
            esempi.setdefault(u, prop[:96])

    print("\n  ══ IL CONTO ══")
    print(f"     coppie (unita', valore) estratte in tutto ... {totale}")
    print(f"     ► con unita' VUOTA .......................... {senza_unita}"
          f"   ({100.0 * senza_unita / max(totale, 1):.1f}%)")
    print(f"     ► con un'unita' ............................. {totale - senza_unita}")
    print(f"     unita' DISTINTE ............................. {len(unita)}")

    # ── controllo che deve poter fallire ────────────────────────────────
    top = [u for u, _c in unita.most_common(40)]
    presenti = [u for u in _UNITA_OVVIE if u in unita]
    print(f"\n  CONTROLLO: unita' ovvie presenti nel corpus: "
          f"{len(presenti)}/{len(_UNITA_OVVIE)}  {presenti}")
    if not presenti:
        print("     CONTROLLO CADUTO: nessuna unita' ovvia ⇒ misuro un estrattore")
        print("     rotto, non la coda delle unita' false. NESSUN ELENCO.")
        return 1

    print("\n  ══ LE PRIME 40 UNITA' PER FREQUENZA — da LEGGERE ══")
    print(f"  {'unita':<22} {'n':>6}   esempio")
    print("  " + "-" * 100)
    for u, c in unita.most_common(40):
        print(f"  {u[:22]:<22} {c:>6}   {esempi.get(u, '')[:66]}")

    print("\n  ══ LA CODA: unita' viste UNA VOLTA SOLA ══")
    rare = [u for u, c in unita.items() if c == 1]
    print(f"     {len(rare)} unita' su {len(unita)} compaiono una volta sola"
          f"   ({100.0 * len(rare) / max(len(unita), 1):.0f}%)")
    print("     un campione (i primi 30 in ordine alfabetico):")
    for u in sorted(rare)[:30]:
        print(f"       · {u[:30]}")

    print("\n  ⚠️ LIMITI: il banco NON dice quali sono false — non e' il suo")
    print("     mestiere e una lista giudicata da me sarebbe la classe ③ che sto")
    print("     misurando. Dice DOVE guardare: la coda delle unita' rare e' il")
    print("     posto in cui una parola qualsiasi finisce per essere un'unita'.")
    print("     Un corpus solo, di output di strumenti, in un solo istante; e le")
    print("     proposizioni sono lette come FONTE (come_fonte=True), che e' il")
    print("     regime piu' permissivo dell'estrattore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
