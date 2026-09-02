"""Non «parafrasi sì o no»: quanto lontano dal lessico prima che il fatto sparisca?

Il banco `ws6-parafrasi-a-k-grande` ha lasciato un'ipotesi dichiarata e non
provata: i due casi persi erano le parafrasi **più astratte**, quelle che non
condividevano nulla col fatto. ⇒ forse non è un interruttore ma un **gradiente**.

Tre livelli sullo STESSO fatto, bersaglio unico, match per `id`, `k=200`:

    L1  FRAMMENTO   le parole del fatto (il caso favorevole, già misurato altrove)
    L2  VICINA      il concetto con QUALCHE termine tecnico conservato
    L3  ASTRATTA    il concetto con ZERO termini del fatto

Se il rango peggiora **per gradi** da L1 a L3, la distanza lessicale è una
variabile continua e la domanda «entra nel pool?» ha una risposta che dipende da
**quanto** ci si allontana. Se invece L2 e L3 collassano insieme, la soglia è
netta e sta fra il lessico e tutto il resto.

⚠️ LE TRE VARIANTI SONO MIE, scritte prima di eseguire. Quattro fatti per tre
livelli sono **dodici misure**: una direzione, non un tasso.

SOLA LETTURA sullo store.
"""
import os

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))

# id → (L1 frammento, L2 vicina, L3 astratta)
CASI = {
    "9678aab2ccf2": (
        "Con 11 righe extra il falso ha grounding 16.04",
        "con qualche riga in piu' il grounding del falso sale molto",
        "aggiungendo due righe al testo di partenza un'affermazione sbagliata "
        "passa da poco credibile a molto credibile",
    ),
    "05ee15f036ca": (
        "Sulla fonte lunga tabellare il vero ha grounding 93.46",
        "su una fonte lunga a tabella il grounding del falso supera quello del vero",
        "quando il testo di partenza e' una tabella lunga l'affermazione falsa "
        "risulta piu' convincente di quella giusta",
    ),
    "f9f86a1d5923": (
        "Nel GateResult il campo threshold vale 40.0",
        "nel risultato del gate la threshold e' 40 e il judge e' local",
        "quale valore di sbarramento e quale valutatore compaiono nell'esito "
        "del controllo",
    ),
    "17eab2845513": (
        "Con la parola nota davanti al numero nudo la fonte da set vuoto",
        "se davanti al numero c'e' la parola nota il gate fa downgrade con L4.1",
        "se davanti alla cifra c'e' una parola generica il controllo non trova "
        "riscontro e declassa",
    ),
    # ⚠️ I DUE CASI CHE NELLA PRIMA STESURA AVEVO ESCLUSO, e sono esattamente i
    # due che nel banco precedente fallivano a k=200. Sceglierne quattro su sei
    # lasciando fuori i difficili e' un campione RITAGLIATO: il 4/4 della prima
    # esecuzione lo diceva senza che me ne accorgessi.
    "64e259c420f4": (
        "Con il soggetto di 6 parole action e persist",
        "con un soggetto di sei parole l'action e' persist, con sette e' downgrade",
        "allungando di una parola la descrizione dell'oggetto il verdetto cambia "
        "da conservare a declassare",
    ),
    "60540fcd8859": (
        "Con il soggetto povero action e persist",
        "col soggetto povero l'action e' persist e col soggetto ricco e' downgrade",
        "se la descrizione dell'oggetto e' piu' dettagliata il verdetto peggiora",
    ),
}

from verimem.client import Memory   # noqa: E402

m = Memory(DB)

print("GRADIENTE LESSICALE — stesso fatto, tre distanze, k=200, match per ID\n")
print("  %-14s %-10s %-10s %-10s" % ("fatto", "L1 frammento", "L2 vicina", "L3 astratta"))

somma = {0: [], 1: [], 2: []}
for fid, varianti in CASI.items():
    ranghi = []
    for liv, q in enumerate(varianti):
        res = m.recall(q, k=200, as_of=None)
        r = None
        for i, it in enumerate(res or [], 1):
            if isinstance(it, dict) and it.get("id") == fid:
                r = i
                break
        ranghi.append(r)
        if r is not None:
            somma[liv].append(r)
    print("  %-14s %-10s %-10s %-10s" % (
        fid, *[("MAI" if r is None else str(r)) for r in ranghi]))

print()
for liv, nome in ((0, "L1 frammento"), (1, "L2 vicina"), (2, "L3 astratta")):
    v = somma[liv]
    trovati = len(v)
    if v:
        v_ord = sorted(v)
        print("  %-14s trovati %d/%d   rango mediano %d   peggiore %d"
              % (nome, trovati, len(CASI), v_ord[len(v_ord) // 2], v_ord[-1]))
    else:
        print("  %-14s trovati 0/%d" % (nome, len(CASI)))

print()
print("Se il rango peggiora per gradi, la distanza lessicale e' continua.")
print("Se L2 e L3 collassano, la soglia sta fra il lessico e tutto il resto.")
