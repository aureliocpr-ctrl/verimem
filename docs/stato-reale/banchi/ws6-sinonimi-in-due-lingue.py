"""L'esperimento decisivo: sinonimi lontani IN INGLESE.

Stato: sugli stessi 24 fatti italiani
  domanda IT, vocabolario del dominio   91,7%  (sovrapposizione 85,9%)
  la STESSA domanda in EN               87,5%  (sovrapposizione 22,7%)
  domanda IT con SINONIMI LONTANI       20,8%  (sovrapposizione 16,1%)
=> a sovrapposizione quasi uguale (22,7 contro 16,1) i risultati sono opposti:
   NON e' la sovrapposizione lessicale a decidere.

IPOTESI: l'encoder (multilingual-e5-base) allinea le TRADUZIONI, che ha visto
in addestramento, e non le PARAFRASI con sinonimi lontani, che non ha visto.

PREDIZIONE, registrata prima di eseguire:
  se l'ipotesi regge -> i sinonimi lontani IN INGLESE crollano come quelli
     italiani (~20%), perche' il problema e' la parafrasi, non la lingua
  se invece reggono (~85%) -> l'ipotesi cade e il problema e' altrove

Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id, sinonimi lontani IT, gli STESSI sinonimi lontani in EN)
COPPIE = [
    ("448caf2a4196",
     "il diario delle operazioni dice mai quando la qualita della risposta peggiora",
     "does the operations diary ever say when the answer quality gets worse"),
    ("19ca6c5a1078",
     "il peggioramento dipende da quanto tempo e acceso il servizio",
     "does the worsening depend on how long the service has been switched on"),
    ("4f2156999025",
     "quando salvo qualcosa mi viene detto se manca il vettore",
     "when i store something am i told whether the vector is missing"),
    ("4a6e084ed45f",
     "quanti numeri per ogni ricordo usa il motore adesso",
     "how many numbers per memory does the engine use now"),
    ("c6666ba131b0",
     "se il servizio di codifica e acceso il controllo di veridicita viene eseguito",
     "if the coding service is on is the truthfulness check carried out"),
    ("7251557d6e29",
     "cosa succede se il servizio non risponde e il caricamento locale e vietato",
     "what happens if the service does not answer and local loading is forbidden"),
    ("0ebe9e824198",
     "a meta luglio quanti ricordi sono rimasti senza controllo",
     "in mid july how many memories were left unchecked"),
    ("a9186a0a3ab9",
     "l ultimo giorno del mese quanti ne sono sfuggiti al controllo",
     "on the last day of the month how many escaped the check"),
    ("1df6f66e68fb",
     "i ricordi sfuggiti sono sparsi o raggruppati in intervalli di tempo",
     "are the escaped memories scattered or grouped into time intervals"),
    ("1fd933467e50",
     "il file con le domande di prova e finito nel ramo principale",
     "did the file with the test questions end up in the main branch"),
    ("b57a07b33264",
     "prima di ferragosto quante sostituzioni cancellavano roba che diceva altro",
     "before mid august how many replacements erased stuff that said something else"),
    ("a2a8acea0c70",
     "quanto si somigliano i ricordi dello stesso argomento mai sostituiti",
     "how alike are the memories on the same subject that were never replaced"),
    ("c40a5a447d26",
     "quante incoerenze sono registrate e quante restano ancora aperte",
     "how many inconsistencies are recorded and how many are still open"),
    ("1c88e6ce600c",
     "quanti elementi senza punteggio di fiducia finiscono in liti aperte",
     "how many items without a trust score end up in open disputes"),
    ("4256fc4d39c1",
     "quante liti aperte riguardano testi molto somiglianti",
     "how many open disputes involve very similar texts"),
    ("2fe9844f1fda",
     "le liti fra testi somiglianti differiscono per poche parole",
     "do disputes between similar texts differ by only a few words"),
]


def parole(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2}


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(COPPIE))
testi = dict(con.execute(
    "SELECT id, proposition FROM facts WHERE id IN (%s)" % ph,
    tuple(c[0] for c in COPPIE)).fetchall())
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


dati = {"IT": [], "EN": []}
for fid, qit, qen in COPPIE:
    prop = testi.get(fid)
    if prop is None:
        continue
    pp = parole(prop)
    for lingua, q in (("IT", qit), ("EN", qen)):
        sovr = len(parole(q) & pp) / max(1, len(parole(q)))
        ok, rango = prova(q, fid)
        dati[lingua].append((sovr, ok, rango))

print("fatti (in italiano nel corpus): %d\n" % len(dati["IT"]))
print("SINONIMI LONTANI, nelle due lingue")
for lingua, eti in (("IT", "sinonimi lontani in ITALIANO"),
                    ("EN", "gli STESSI sinonimi in INGLESE")):
    g = dati[lingua]
    n = len(g)
    t = sum(1 for x in g if x[1])
    p = sum(1 for x in g if x[2] == 1)
    s = sum(x[0] for x in g) / max(1, n)
    print("  %-34s n=%2d   trovati %2d = %5.1f%%   primi %2d   sovr %5.1f%%"
          % (eti, n, t, 100.0 * t / n, p, 100 * s))
