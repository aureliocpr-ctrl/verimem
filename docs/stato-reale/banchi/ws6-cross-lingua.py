"""Il limite del doc 55: l'INGLESE, su un corpus misto.

Se il richiamo e' lessicale (misurato: sinonimi lontani 20,8% contro
vocabolario del dominio 91,7%), una domanda in inglese su fatti italiani
potrebbe non vederli: sarebbe meta' memoria invisibile all'altra meta'.
Ma l'encoder e' multilingual-e5-base, che dovrebbe attraversare le lingue.
Due evidenze in tensione => esperimento.

DISEGNO, migliore di quello del 55: stesso fatto, STESSA domanda, cambia SOLO
la lingua. Un fattore solo, confronto appaiato.

PREDIZIONE registrata prima di eseguire:
  se il modello e' davvero multilingue -> EN vicino a IT (~90%)
  se domina il lessico di superficie   -> EN vicino al braccio sinonimi (~20%)

Gli identificatori (EncodeDelegateUnavailable, HIPPO_ENCODE_DELEGATE_ONLY,
flow.recall, 2f92d9e5, min_relevance) sopravvivono alla traduzione: il banco
separa le domande CHE NE CONTENGONO da quelle che non ne contengono, altrimenti
misurerei la presenza di un token identico invece della lingua.

Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id, domanda IT del braccio B, la STESSA domanda in EN)
COPPIE = [
    ("448caf2a4196",
     "il journal degli eventi registra il ranking degradato o il rerank",
     "does the event journal record the degraded ranking or the rerank"),
    ("50364aa2d383",
     "quale punto che emette flow.recall non registra abstained",
     "which flow.recall emission point does not record abstained"),
    ("19ca6c5a1078",
     "il degrado del ranking dipende dalla durata del processo",
     "does the ranking degradation depend on the process lifetime"),
    ("4f2156999025",
     "la ricevuta di save avvisa quando il fatto e scritto senza embedding",
     "does the save receipt warn when the fact is written without embedding"),
    ("4a6e084ed45f",
     "quanti vettori a 768 dimensioni riporta verimem doctor",
     "how many 768-dimensional vectors does verimem doctor report"),
    ("c6666ba131b0",
     "una scrittura con encode daemon in funzione registra judged",
     "a write with the encode daemon running records judged"),
    ("7251557d6e29",
     "quando viene sollevata EncodeDelegateUnavailable",
     "when is EncodeDelegateUnavailable raised"),
    ("c955c33e9395",
     "quanto vale HIPPO_ENCODE_DELEGATE_ONLY nell ambiente",
     "what is the value of HIPPO_ENCODE_DELEGATE_ONLY in the environment"),
    ("4b0810bb9ae2",
     "cosa afferma verimem doctor sul primo encode senza daemon",
     "what does verimem doctor claim about the first encode without the daemon"),
    ("0ebe9e824198",
     "il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati",
     "on 18 july 2026 how many facts written and how many never judged"),
    ("758425daf047",
     "il 19 agosto 2026 quanti fatti mai giudicati",
     "on 19 august 2026 how many facts were never judged"),
    ("a9186a0a3ab9",
     "il 30 agosto 2026 quanti fatti scritti e quanti mai giudicati",
     "on 30 august 2026 how many facts written and how many never judged"),
    ("1df6f66e68fb",
     "i fatti mai giudicati del 30 agosto in quanti blocchi stanno",
     "in how many blocks are the never judged facts of 30 august"),
    ("1e5b5528694b",
     "nell ora delle 21 del 30 agosto quanti fatti mai giudicati",
     "in the 21 hour of 30 august how many facts were never judged"),
    ("1fd933467e50",
     "il commit 2f92d9e5 e antenato di origin main",
     "is commit 2f92d9e5 an ancestor of origin main"),
    ("d0ca371c09e8",
     "mediana di parole delle proposizioni italiane e inglesi",
     "median word count of italian and english propositions"),
    ("b57a07b33264",
     "coppie di supersessione prima del 25 agosto in cui i testi parlano d altro",
     "supersession pairs before 25 august where the texts are about something else"),
    ("216d8673e0ec",
     "coppie di supersessione dal 25 agosto in cui i testi parlano d altro",
     "supersession pairs from 25 august where the texts are about something else"),
    ("a2a8acea0c70",
     "jaccard sotto 0.15 fra fatti dello stesso topic mai superseduti",
     "jaccard below 0.15 between never superseded facts of the same topic"),
    ("c40a5a447d26",
     "quante contraddizioni registrate e quante irrisolte nello store",
     "how many contradictions recorded and how many unresolved in the store"),
    ("403969229a59",
     "numeric_clash con jaccard sotto 0.15 su un campione di coppie",
     "numeric_clash with jaccard below 0.15 on a sample of pairs"),
    ("1c88e6ce600c",
     "fatti senza trust rank coinvolti in contraddizioni irrisolte",
     "facts without trust rank involved in unresolved contradictions"),
    ("4256fc4d39c1",
     "coppie di contraddizioni irrisolte con jaccard maggiore di 0.50",
     "unresolved contradiction pairs with jaccard above 0.50"),
    ("2fe9844f1fda",
     "coppie di contraddizioni con jaccard alto che differiscono per pochi token",
     "contradiction pairs with high jaccard differing by few tokens"),
]

# identificatori che sopravvivono alla traduzione
IDENT = re.compile(
    r"flow\.recall|EncodeDelegateUnavailable|HIPPO_ENCODE_DELEGATE_ONLY|"
    r"2f92d9e5|numeric_clash|jaccard|verimem|min_relevance|768")


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


gruppi = {("IT", True): [], ("IT", False): [], ("EN", True): [], ("EN", False): []}
for fid, qit, qen in COPPIE:
    prop = testi.get(fid)
    if prop is None:
        continue
    pp = parole(prop)
    con_ident = bool(IDENT.search(qen))
    for lingua, q in (("IT", qit), ("EN", qen)):
        sovr = len(parole(q) & pp) / max(1, len(parole(q)))
        ok, rango = prova(q, fid)
        gruppi[(lingua, con_ident)].append((sovr, ok, rango))


def riga(eti, dati):
    n = len(dati)
    if not n:
        print("%-44s  nessun caso" % eti)
        return
    t = sum(1 for x in dati if x[1])
    p = sum(1 for x in dati if x[2] == 1)
    s = sum(x[0] for x in dati) / n
    print("%-44s n=%2d   trovati %2d = %5.1f%%   primi %2d = %5.1f%%   sovr %5.1f%%"
          % (eti, n, t, 100.0 * t / n, p, 100.0 * p / n, 100 * s))


print("fatti (tutti in ITALIANO nel corpus): %d\n" % len(COPPIE))
print("TUTTE LE DOMANDE")
riga("  domanda in ITALIANO", gruppi[("IT", True)] + gruppi[("IT", False)])
riga("  la STESSA domanda in INGLESE", gruppi[("EN", True)] + gruppi[("EN", False)])

print("\nSEPARANDO le domande che contengono IDENTIFICATORI")
print("(nomi che sopravvivono alla traduzione: senza questa separazione")
print(" misurerei la presenza di un token identico, non la lingua)")
riga("  CON identificatori — italiano", gruppi[("IT", True)])
riga("  CON identificatori — inglese", gruppi[("EN", True)])
riga("  SENZA identificatori — italiano", gruppi[("IT", False)])
riga("  SENZA identificatori — inglese", gruppi[("EN", False)])
