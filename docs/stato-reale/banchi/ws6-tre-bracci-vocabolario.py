"""Tre bracci sullo STESSO fatto: quanto conta il vocabolario, quanto la forma.

Il primo banco (24 domande con sinonimi lontani) dava 20,8%: rischio di aver
riformulato TROPPO, che sarebbe l'errore speculare del banco "troppo facile".
Qui aggiungo il braccio che mancava.

  A  SINONIMI LONTANI  - "liti" per contraddizioni, "ricordi" per fatti
  B  VOCABOLARIO DEL DOMINIO, frase diversa - come chiede chi conosce il tema
     ma non ricorda la frase esatta
  C  FRAMMENTO del fatto (il controllo alto: gia' misurato 100% nel doc 54)

Un solo fatto per riga, tutti e tre i bracci sullo stesso: il confronto e'
appaiato, quindi le differenze non dipendono da quali fatti ho scelto.
Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id, A sinonimi lontani, B vocabolario del dominio con frase diversa)
TRIPLE = [
    ("448caf2a4196",
     "il diario delle operazioni dice mai quando la qualita della risposta peggiora",
     "il journal degli eventi registra il ranking degradato o il rerank"),
    ("50364aa2d383",
     "ce un punto del codice che scrive nel diario ma dimentica di dire se ha rinunciato",
     "quale punto che emette flow.recall non registra abstained"),
    ("19ca6c5a1078",
     "il peggioramento dipende da quanto tempo e acceso il servizio",
     "il degrado del ranking dipende dalla durata del processo"),
    ("4f2156999025",
     "quando salvo qualcosa mi viene detto se manca il vettore",
     "la ricevuta di save avvisa quando il fatto e scritto senza embedding"),
    ("4a6e084ed45f",
     "quanti numeri per ogni ricordo usa il motore adesso",
     "quanti vettori a 768 dimensioni riporta verimem doctor"),
    ("c6666ba131b0",
     "se il servizio di codifica e acceso il controllo di veridicita viene eseguito",
     "una scrittura con encode daemon in funzione registra judged"),
    ("7251557d6e29",
     "cosa succede se il servizio non risponde e il caricamento locale e vietato",
     "quando viene sollevata EncodeDelegateUnavailable"),
    ("c955c33e9395",
     "come e impostata la variabile che vieta il caricamento dentro al processo",
     "quanto vale HIPPO_ENCODE_DELEGATE_ONLY nell ambiente"),
    ("4b0810bb9ae2",
     "la diagnostica cosa sostiene del primo utilizzo quando manca il servizio",
     "cosa afferma verimem doctor sul primo encode senza daemon"),
    ("0ebe9e824198",
     "a meta luglio quanti ricordi sono rimasti senza controllo",
     "il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati"),
    ("758425daf047",
     "il diciannove del mese scorso ci sono stati ricordi senza controllo",
     "il 19 agosto 2026 quanti fatti mai giudicati"),
    ("a9186a0a3ab9",
     "l ultimo giorno del mese quanti ne sono sfuggiti al controllo",
     "il 30 agosto 2026 quanti fatti scritti e quanti mai giudicati"),
    ("1df6f66e68fb",
     "i ricordi sfuggiti sono sparsi o raggruppati in intervalli di tempo",
     "i fatti mai giudicati del 30 agosto in quanti blocchi stanno"),
    ("1e5b5528694b",
     "nella serata tardi ci sono stati ammanchi",
     "nell ora delle 21 del 30 agosto quanti fatti mai giudicati"),
    ("1fd933467e50",
     "il file con le domande di prova e finito nel ramo principale",
     "il commit 2f92d9e5 e antenato di origin main"),
    ("d0ca371c09e8",
     "le frasi in italiano sono piu lunghe di quelle inglesi",
     "mediana di parole delle proposizioni italiane e inglesi"),
    ("b57a07b33264",
     "prima di ferragosto quante sostituzioni cancellavano roba che diceva altro",
     "coppie di supersessione prima del 25 agosto in cui i testi parlano d altro"),
    ("216d8673e0ec",
     "e dopo ferragosto quante sostituzioni cancellavano roba che diceva altro",
     "coppie di supersessione dal 25 agosto in cui i testi parlano d altro"),
    ("a2a8acea0c70",
     "quanto si somigliano i ricordi dello stesso argomento mai sostituiti",
     "jaccard sotto 0.15 fra fatti dello stesso topic mai superseduti"),
    ("c40a5a447d26",
     "quante incoerenze sono registrate e quante restano ancora aperte",
     "quante contraddizioni registrate e quante irrisolte nello store"),
    ("403969229a59",
     "gli scontri fra cifre riguardano testi che si somigliano poco",
     "numeric_clash con jaccard sotto 0.15 su un campione di coppie"),
    ("1c88e6ce600c",
     "quanti elementi senza punteggio di fiducia finiscono in liti aperte",
     "fatti senza trust rank coinvolti in contraddizioni irrisolte"),
    ("4256fc4d39c1",
     "quante liti aperte riguardano testi molto somiglianti",
     "coppie di contraddizioni irrisolte con jaccard maggiore di 0.50"),
    ("2fe9844f1fda",
     "le liti fra testi somiglianti differiscono per poche parole",
     "coppie di contraddizioni con jaccard alto che differiscono per pochi token"),
]


def parole(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2}


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(TRIPLE))
testi = dict(con.execute(
    "SELECT id, proposition FROM facts WHERE id IN (%s)" % ph,
    tuple(t[0] for t in TRIPLE)).fetchall())
con.close()

from verimem.client import Memory   # noqa: E402 - dopo la sola lettura

m = Memory(DB)


def prova(domanda, fid):
    try:
        res = m.recall(domanda, k=K)
    except Exception:
        return False, None
    for r, it in enumerate(res or [], 1):
        if isinstance(it, dict) and it.get("id") == fid:
            return True, r
    return False, None


ris = {"A": [], "B": [], "C": []}
for fid, qa, qb in TRIPLE:
    prop = testi.get(fid)
    if prop is None:
        continue
    pp = parole(prop)
    qc = " ".join(str(prop).split()[:7])
    for eti, q in (("A", qa), ("B", qb), ("C", qc)):
        pd = parole(q)
        sovr = len(pd & pp) / max(1, len(pd))
        ok, rango = prova(q, fid)
        ris[eti].append((sovr, ok, rango))

print("fatti nel confronto appaiato: %d\n" % len(ris["A"]))
print("%-3s %-42s %-12s %-10s %s"
      % ("", "come e' costruita la domanda", "ritrovati", "al 1o posto", "sovrapp."))
for eti, testo in (("A", "SINONIMI LONTANI (liti, ricordi, diario)"),
                   ("B", "VOCABOLARIO DEL DOMINIO, frase diversa"),
                   ("C", "FRAMMENTO di 7 parole del fatto")):
    g = ris[eti]
    n = len(g)
    t = sum(1 for x in g if x[1])
    p = sum(1 for x in g if x[2] == 1)
    s = sum(x[0] for x in g) / max(1, n)
    print("%-3s %-42s %2d/%-2d = %5.1f%%  %2d = %5.1f%%   %5.1f%%"
          % (eti, testo, t, n, 100.0 * t / n, p, 100.0 * p / n, 100 * s))
