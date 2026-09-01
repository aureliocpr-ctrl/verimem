"""Le letture che non trovano: e' il RANKING o l'ASSENZA?

Il doc 61 ha stabilito che il difetto e' il retrieval, non la soglia: il best
separa senza sovrapposizioni, quindi l'86% di avvisi non e' rumore - le letture
non trovano davvero. Ma «non trova» ha DUE cause con cure opposte:

  RANKING  il fatto giusto E' nel corpus e viene restituito, ma oltre k
           => curabile: rerank, k piu' alto, query expansion
  ASSENZA  il fatto giusto non torna nemmeno a k molto grande
           => non curabile col ranking: e' copertura o embedding

Righello: per ogni domanda con risposta NOTA, cercare il rango reale a k=200.
Se il fatto sta fra 11 e 200, il ranking lo nasconde. Se non c'e', e' altro.

⚠️ PRESIDIO: stampo la composizione per `status` PRIMA di misurare - un fatto
quarantinato non torna per contratto e falserebbe il conto (lezione del doc 58).

SOLA LETTURA sullo store.
"""
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K_LARGO = 200

# domande col vocabolario del dominio, risposta nota (le stesse del doc 61)
NOTE = [
    ("448caf2a4196", "il journal degli eventi registra il ranking degradato o il rerank"),
    ("50364aa2d383", "quale punto che emette flow.recall non registra abstained"),
    ("19ca6c5a1078", "il degrado del ranking dipende dalla durata del processo"),
    ("4f2156999025", "la ricevuta di save avvisa quando il fatto e scritto senza embedding"),
    ("4a6e084ed45f", "quanti vettori a 768 dimensioni riporta verimem doctor"),
    ("c6666ba131b0", "una scrittura con encode daemon in funzione registra judged"),
    ("7251557d6e29", "quando viene sollevata EncodeDelegateUnavailable"),
    ("c955c33e9395", "quanto vale HIPPO_ENCODE_DELEGATE_ONLY nell ambiente"),
    ("4b0810bb9ae2", "cosa afferma verimem doctor sul primo encode senza daemon"),
    ("0ebe9e824198", "il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati"),
    ("758425daf047", "il 19 agosto 2026 quanti fatti mai giudicati"),
    ("a9186a0a3ab9", "il 30 agosto 2026 quanti fatti scritti e quanti mai giudicati"),
    ("1df6f66e68fb", "i fatti mai giudicati del 30 agosto in quanti blocchi stanno"),
    ("1e5b5528694b", "nell ora delle 21 del 30 agosto quanti fatti mai giudicati"),
    ("1fd933467e50", "il commit 2f92d9e5 e antenato di origin main"),
    ("d0ca371c09e8", "mediana di parole delle proposizioni italiane e inglesi"),
    ("b57a07b33264", "coppie di supersessione prima del 25 agosto in cui i testi parlano d altro"),
    ("216d8673e0ec", "coppie di supersessione dal 25 agosto in cui i testi parlano d altro"),
    ("a2a8acea0c70", "jaccard sotto 0.15 fra fatti dello stesso topic mai superseduti"),
    ("c40a5a447d26", "quante contraddizioni registrate e quante irrisolte nello store"),
    ("403969229a59", "numeric_clash con jaccard sotto 0.15 su un campione di coppie"),
    ("1c88e6ce600c", "fatti senza trust rank coinvolti in contraddizioni irrisolte"),
    ("4256fc4d39c1", "coppie di contraddizioni irrisolte con jaccard maggiore di 0.50"),
    ("2fe9844f1fda", "coppie di contraddizioni con jaccard alto che differiscono per pochi token"),
]

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(NOTE))
righe = dict((r[0], r[1:]) for r in con.execute(
    "SELECT id, status, superseded_by FROM facts WHERE id IN (%s)" % ph,
    tuple(i for i, _ in NOTE)).fetchall())
con.close()

# PRESIDIO
assenti = [i for i, _ in NOTE if i not in righe]
quar = [i for i, _ in NOTE if righe.get(i, ("",))[0] == "quarantined"]
sup = [i for i, _ in NOTE if righe.get(i, ("", None))[1]]
print("domande con risposta nota      : %d" % len(NOTE))
print("  fatti assenti dallo store    : %d" % len(assenti))
print("  QUARANTINATI (non tornano)   : %d" % len(quar))
print("  superseduti nel frattempo    : %d" % len(sup))
usabili = [(i, q) for i, q in NOTE
           if i in righe and righe[i][0] != "quarantined" and not righe[i][1]]
print("  usabili per questa misura    : %d" % len(usabili))

from verimem.client import Memory   # noqa: E402 - dopo la lettura

m = Memory(DB)
print("pavimento servito: %s\n" % m._auto_relevance_floor())

entro10, fra, oltre = [], [], []
for fid, q in usabili:
    try:
        res = m.recall(q, k=K_LARGO)
    except Exception:      # noqa: BLE001
        res = []
    rango = None
    for r, it in enumerate(res or [], 1):
        if isinstance(it, dict) and it.get("id") == fid:
            rango = r
            break
    if rango is None:
        oltre.append((fid, q))
    elif rango <= 10:
        entro10.append((rango, fid))
    else:
        fra.append((rango, fid, q))

n = len(usabili)
print("RANGO REALE a k=%d, su %d domande con risposta nota" % (K_LARGO, n))
print("  entro i primi 10                    : %2d  = %5.1f%%" % (len(entro10), 100.0 * len(entro10) / max(1, n)))
print("  fra 11 e %d  → IL RANKING LO NASCONDE: %2d  = %5.1f%%" % (K_LARGO, len(fra), 100.0 * len(fra) / max(1, n)))
print("  non torna affatto → ALTRO            : %2d  = %5.1f%%" % (len(oltre), 100.0 * len(oltre) / max(1, n)))

if fra:
    print("\nI CASI CURABILI COL RANKING (il fatto c'e', ma oltre k=10):")
    for rango, fid, q in sorted(fra):
        print("  rango %3d  %-14s %s" % (rango, fid, q[:58]))
if oltre:
    print("\nI CASI CHE NON TORNANO AFFATTO (copertura o embedding):")
    for fid, q in oltre:
        print("  %-14s %s" % (fid, q[:66]))

print("\nSe la riga di mezzo e' GRANDE, alzare k o rerankare cura molto.")
print("Se e' ~0 e la terza e' grande, il ranking non c'entra: e' altro.")
