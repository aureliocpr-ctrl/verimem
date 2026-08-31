"""Il punteggio migliore predice la BONTA' della risposta?

Domanda posta al canale e non ancora risposta: l'avviso `sotto_il_pavimento` si
accende sull'86,3% del traffico col pavimento attuale e sul ~50% con la banda
proposta da @ws2. Ma se le risposte con best basso fossero DAVVERO cattive,
l'avviso avrebbe ragione e il problema sarebbe il retrieval, non la soglia.

Serve un righello della bonta' CHE NON SIA IL PUNTEGGIO. Ne ho uno: nei miei
banchi so QUALE fatto la query deve trovare. "Il fatto atteso e' fra i
risultati" e' una nozione di bonta' indipendente dal punteggio.

Tre popolazioni:
  A  query con risposta nota, fatto atteso TROVATO      -> risposta buona
  B  query con risposta nota, fatto atteso NON trovato  -> risposta mancata
  C  query FUORI DOMINIO, nessuna risposta in memoria   -> non deve trovare

Se il best separa A da B e da C, e' un buon predittore e l'avviso ha ragione.
Se non separa, stiamo tarando la soglia sbagliata.

⚠️ La bonta' qui e' STRETTA: un solo fatto e' quello giusto. Una risposta
diversa ma utile conta come mancata. E' un limite, non un difetto del righello:
lo rende PESSIMISTA su A, non ottimista.

SOLA LETTURA sullo store.
"""
import os
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id atteso, domanda col vocabolario del dominio) — le stesse del banco 55/57
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

FUORI = [
    "come si pota un ulivo in primavera",
    "qual e la ricetta della carbonara romana",
    "chi ha vinto il campionato di calcio nel millenovecentottantadue",
    "quanto costa un biglietto del treno per Vienna",
    "come si accorda una chitarra classica",
    "quali sono i sintomi dell intolleranza al lattosio",
    "come si calcola l area di un trapezio isoscele",
    "che differenza c e fra un violino e una viola",
    "quando fiorisce il glicine nel nord Italia",
    "come si cambia una gomma bucata in bicicletta",
]

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(NOTE))
stato = dict(con.execute(
    "SELECT id, status FROM facts WHERE id IN (%s)" % ph,
    tuple(i for i, _ in NOTE)).fetchall())
con.close()

# PRESIDIO: la composizione per status, prima di misurare.
quar = [i for i, _ in NOTE if stato.get(i) == "quarantined"]
print("query con risposta nota: %d   di cui il fatto atteso e' QUARANTINATO: %d"
      % (len(NOTE), len(quar)))
if quar:
    print("  -> escluse: per contratto non tornano dal recall")
NOTE = [(i, q) for i, q in NOTE if stato.get(i) and stato.get(i) != "quarantined"]
print("query usate: %d" % len(NOTE))

from verimem.client import Memory   # noqa: E402 - dopo la sola lettura

m = Memory(DB)
pav = m._auto_relevance_floor()
print("pavimento servito ora: %s\n" % pav)


def misura(q, atteso=None):
    try:
        r = m.recall(q, k=K)
    except Exception:
        return None, False
    best = max((float(i.get("score") or 0.0) for i in r), default=0.0)
    trovato = any(i.get("id") == atteso for i in r) if atteso else False
    return best, trovato


A, B, C = [], [], []
for fid, q in NOTE:
    best, trovato = misura(q, fid)
    if best is None:
        continue
    (A if trovato else B).append(best)
for q in FUORI:
    best, _t = misura(q)
    if best is not None:
        C.append(best)


def riga(eti, g):
    if not g:
        print("%-44s  nessun caso" % eti)
        return
    g = sorted(g)
    n = len(g)
    sotto = sum(1 for x in g if pav and x < float(pav))
    print("%-44s n=%2d  min %.4f  mediana %.4f  max %.4f   avvisati %d = %.0f%%"
          % (eti, n, g[0], g[n // 2], g[-1], sotto, 100.0 * sotto / n))


print("%-44s %s" % ("popolazione", "punteggio migliore"))
riga("A  risposta nota, fatto atteso TROVATO", A)
riga("B  risposta nota, fatto atteso MANCATO", B)
riga("C  fuori dominio (non deve trovare)", C)

if A and C:
    sovr = sum(1 for x in C if x >= min(A))
    print("\nSEPARAZIONE fra A (buone) e C (fuori dominio):")
    print("  minimo di A          %.4f" % min(A))
    print("  massimo di C         %.4f" % max(C))
    print("  query fuori dominio che superano il minimo delle buone: %d su %d"
          % (sovr, len(C)))
    print("  => se e' 0, il best separa; se e' alto, il best NON separa e la")
    print("     soglia non puo' distinguere le due popolazioni.")
