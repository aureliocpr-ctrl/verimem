"""Chiude DUE limiti dichiarati nei doc 55 e 57 con un banco solo.

  57: "i fatti sono TUTTI in italiano; la direzione opposta - domande italiane
       su fatti INGLESI - non l'ho misurata, e il corpus ne contiene"
  55: "i fatti sono I MIEI, densi di numeri e nomi propri. Su un corpus di
       testo piu' discorsivo il pavimento puo' stare altrove"

I fatti inglesi del corpus sono in maggioranza PROSA DISCORSIVA di un banco
(personaggi sintetici), quindi la stessa popolazione chiude entrambi: altra
lingua E altro registro, scritta da altri.

DISEGNO: stesso fatto, stessa domanda, cambia solo la lingua. Le domande NON
contengono i nomi propri (Christopher, Donna), che sopravviverebbero alla
traduzione e mi farebbero misurare un token identico invece della lingua.

⚠️ Rischio noto e gestito dal disegno: senza il nome, in un corpus con ~105
fatti simili, la domanda puo' essere poco distintiva. Se lo e', CADE ANCHE IL
BRACCIO INGLESE - ed e' quello il riferimento, non un valore assoluto atteso.

Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

# (id, domanda EN — la lingua del fatto, la STESSA domanda in IT)
COPPIE = [
    ("dce592fd45d5",
     "how did the perception of rodents change after caring for a pet",
     "come e cambiata la percezione dei roditori dopo aver curato un animale"),
    ("c312490739e8",
     "why did the clothing preference shift from casual to handmade sneakers",
     "perche la preferenza di abbigliamento e passata dalle scarpe casual a quelle fatte a mano"),
    ("17255c6cf701",
     "the decision to update food preferences aligns with which life goal",
     "la decisione di aggiornare le preferenze alimentari si allinea a quale obiettivo di vita"),
    ("b18c649d05d2",
     "the dialogue emphasized overcoming biases and embracing new experiences",
     "il dialogo ha sottolineato il superamento dei pregiudizi e l apertura a nuove esperienze"),
    ("05c1bfd1522f",
     "insights from a seminar on sustainable fabrics and the economic benefits of traditional materials",
     "spunti da un seminario sui tessuti sostenibili e i benefici economici dei materiali tradizionali"),
    ("b0f04695ceb5",
     "incorporating insights from the fashion innovation workshop into community programs",
     "portare gli spunti del laboratorio di innovazione della moda nei programmi di comunita"),
    ("c6e6239700d3",
     "expanded social connections enhance the effectiveness and reach of volunteer programs",
     "connessioni sociali piu ampie migliorano l efficacia e la portata dei programmi di volontariato"),
    ("688fa84c5a65",
     "adaptability in personal preferences as a key aspect of personal growth",
     "l adattabilita nelle preferenze personali come aspetto chiave della crescita personale"),
    ("7e7381d1330f",
     "the transition to community program director is motivated by which passion",
     "la transizione a direttore dei programmi di comunita e motivata da quale passione"),
    ("d7dab32cb613",
     "seeking books that reflect themes of social change and personal growth",
     "cercare libri che riflettano temi di cambiamento sociale e crescita personale"),
    ("4609963352d1",
     "the instrumental motivation driving the effort to build partnerships",
     "la motivazione strumentale che guida lo sforzo di costruire partnership"),
    ("cf3a30fb4d75",
     "practical insights from music composition guides aid the soundtrack creation process",
     "gli spunti pratici dalle guide di composizione musicale aiutano il processo di creazione della colonna sonora"),
    ("a9c1c7791397",
     "resilience and optimism maintained through the support of a social network",
     "resilienza e ottimismo mantenuti grazie al sostegno di una rete sociale"),
    ("e112a72c2868",
     "leisure activities such as painting contributing positively to career goals",
     "attivita del tempo libero come la pittura che contribuiscono positivamente agli obiettivi di carriera"),
    ("141df7f50277",
     "plans to focus solely on internal development rather than industry partnerships",
     "piani per concentrarsi solo sullo sviluppo interno invece che sulle partnership di settore"),
    ("827fb3bb620d",
     "python execution applied transformations catching off-by-one and wrap-around errors",
     "l esecuzione python ha applicato trasformazioni intercettando errori di off-by-one e di avvolgimento"),
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
print("fatti INGLESI nel banco: %d (di %d chiesti)" % (len(testi), len(COPPIE)))

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


NOMI = {
    "dce592fd45d5": "Donna", "c312490739e8": "Christopher",
    "17255c6cf701": "Christopher", "b18c649d05d2": "Donna",
    "05c1bfd1522f": "Donna", "b0f04695ceb5": "Christopher",
    "c6e6239700d3": "Christopher", "688fa84c5a65": "Christopher",
    "7e7381d1330f": "Christopher Anderson", "d7dab32cb613": "Christopher Anderson",
    "4609963352d1": "Christopher Anderson", "cf3a30fb4d75": "Donna Gonzalez",
    "a9c1c7791397": "Donna Gonzalez", "e112a72c2868": "Donna Gonzalez",
    "141df7f50277": "Steven Miller", "827fb3bb620d": "Python",
}
dati = {"EN": [], "IT": [], "EN+nome": []}
for fid, qen, qit in COPPIE:
    prop = testi.get(fid)
    if prop is None:
        continue
    pp = parole(prop)
    qn = "%s %s" % (NOMI.get(fid, ""), qen)
    for lingua, q in (("EN", qen), ("IT", qit), ("EN+nome", qn)):
        sovr = len(parole(q) & pp) / max(1, len(parole(q)))
        ok, rango = prova(q, fid)
        dati[lingua].append((sovr, ok, rango))

print("\nFATTI IN INGLESE, prosa discorsiva, scritti da altri")
for lingua, eti in (("EN", "domanda in INGLESE (la lingua del fatto)"),
                    ("IT", "la STESSA domanda in ITALIANO"),
                    ("EN+nome", "in INGLESE col NOME PROPRIO (controllo)")):
    g = dati[lingua]
    n = len(g)
    if not n:
        continue
    t = sum(1 for x in g if x[1])
    p = sum(1 for x in g if x[2] == 1)
    s = sum(x[0] for x in g) / n
    print("  %-42s n=%2d  trovati %2d = %5.1f%%  primi %2d = %5.1f%%  sovr %5.1f%%"
          % (eti, n, t, 100.0 * t / n, p, 100.0 * p / n, 100 * s))
