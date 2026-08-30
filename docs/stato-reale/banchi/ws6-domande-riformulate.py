"""Il caso dell'UTENTE VERO: domande con parole DIVERSE da quelle del fatto.

Il doc 54 dichiara questo limite: le query del banco usavano le parole del
fatto (frammento o frase intera), che e' il caso favorevole. Qui le domande le
ho scritte io in italiano naturale, cercando sinonimi - diario per giornale,
ricordi per fatti, liti per contraddizioni, servizio per daemon.

Il giudizio su "quanto sono diverse" NON e' mio: il banco misura la
sovrapposizione lessicale fra domanda e fatto e riporta il ritrovamento in
funzione di quella. Cosi' il verdetto non dipende da quanto mi sento bravo a
riformulare.

Store di Aurelio: SOLA LETTURA (la recall e' una lettura).
"""
import os
import re
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id atteso, domanda riformulata)
COPPIE = [
    ("448caf2a4196", "il diario delle operazioni dice mai quando la qualita della risposta peggiora"),
    ("50364aa2d383", "ce un punto del codice che scrive nel diario ma dimentica di dire se ha rinunciato a rispondere"),
    ("19ca6c5a1078", "il peggioramento dipende da quanto tempo e acceso il servizio"),
    ("4f2156999025", "quando salvo qualcosa mi viene detto se manca il vettore"),
    ("4a6e084ed45f", "quanti numeri per ogni ricordo usa il motore adesso"),
    ("c6666ba131b0", "se il servizio di codifica e acceso il controllo di veridicita viene eseguito"),
    ("7251557d6e29", "cosa succede se il servizio non risponde e il caricamento locale e vietato"),
    ("c955c33e9395", "come e impostata la variabile che vieta il caricamento dentro al processo"),
    ("4b0810bb9ae2", "la diagnostica cosa sostiene del primo utilizzo quando manca il servizio"),
    ("0ebe9e824198", "a meta luglio quanti ricordi sono rimasti senza controllo"),
    ("758425daf047", "il diciannove del mese scorso ci sono stati ricordi senza controllo"),
    ("a9186a0a3ab9", "l ultimo giorno del mese quanti ne sono sfuggiti al controllo"),
    ("1df6f66e68fb", "i ricordi sfuggiti sono sparsi o raggruppati in intervalli di tempo"),
    ("1e5b5528694b", "nella serata tardi ci sono stati ammanchi"),
    ("1fd933467e50", "il file con le domande di prova e finito nel ramo principale"),
    ("d0ca371c09e8", "le frasi in italiano sono piu lunghe di quelle inglesi"),
    ("b57a07b33264", "prima di ferragosto quante sostituzioni cancellavano roba che diceva altro"),
    ("216d8673e0ec", "e dopo ferragosto quante sostituzioni cancellavano roba che diceva altro"),
    ("a2a8acea0c70", "quanto si somigliano i ricordi dello stesso argomento mai sostituiti"),
    ("c40a5a447d26", "quante incoerenze sono registrate e quante restano ancora aperte"),
    ("403969229a59", "gli scontri fra cifre riguardano testi che si somigliano poco"),
    ("1c88e6ce600c", "quanti elementi senza punteggio di fiducia finiscono in liti aperte"),
    ("4256fc4d39c1", "quante liti aperte riguardano testi molto somiglianti"),
    ("2fe9844f1fda", "le liti fra testi somiglianti differiscono per poche parole"),
]


def parole(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2}


import sqlite3   # noqa: E402 - dopo le utility, prima della sola lettura

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(COPPIE))
testi = dict(con.execute(
    "SELECT id, proposition FROM facts WHERE id IN (%s)" % ph,
    tuple(i for i, _ in COPPIE)).fetchall())
con.close()

from verimem.client import Memory   # noqa: E402 - dopo la sola lettura

m = Memory(DB)

esiti = []
for fid, domanda in COPPIE:
    prop = testi.get(fid)
    if prop is None:
        continue
    pd, pp = parole(domanda), parole(prop)
    sovr = len(pd & pp) / max(1, len(pd))
    trovato, rango = False, None
    try:
        res = m.recall(domanda, k=K)
    except Exception:
        res = []
    for r, it in enumerate(res or [], 1):
        ident = it.get("id") if isinstance(it, dict) else None
        if ident == fid:
            trovato, rango = True, r
            break
    esiti.append((sovr, trovato, rango, domanda[:52]))

n = len(esiti)
tro = sum(1 for e in esiti if e[1])
pri = sum(1 for e in esiti if e[2] == 1)
print("domande riformulate: %d" % n)
print("  ritrovate entro k=%d : %d = %.1f%%" % (K, tro, 100.0 * tro / max(1, n)))
print("  al PRIMO posto       : %d = %.1f%%" % (pri, 100.0 * pri / max(1, n)))
sovr_media = sum(e[0] for e in esiti) / max(1, n)
print("  sovrapposizione lessicale media domanda/fatto: %.1f%%" % (100 * sovr_media))

print("\nritrovamento IN FUNZIONE della sovrapposizione (il giudizio non e' mio):")
for lo, hi, eti in ((0.0, 0.20, "quasi nulla  <20%"),
                    (0.20, 0.35, "bassa     20-35%"),
                    (0.35, 1.01, "alta        >35%")):
    g = [e for e in esiti if lo <= e[0] < hi]
    if not g:
        print("  %-18s  nessun caso" % eti)
        continue
    t = sum(1 for e in g if e[1])
    p = sum(1 for e in g if e[2] == 1)
    print("  %-18s  n=%2d   trovati %2d = %5.1f%%   primi %2d" % (eti, len(g), t, 100.0 * t / len(g), p))

print("\nle domande NON ritrovate:")
for sovr, trovato, _r, d in esiti:
    if not trovato:
        print("  sovr %4.1f%%  %s" % (100 * sovr, d))
