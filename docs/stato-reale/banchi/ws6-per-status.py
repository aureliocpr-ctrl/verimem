"""Rilettura del banco del doc 58, separando i fatti per STATUS.

Il doc 58 riportava 56,2% (EN) e 50,0% (IT) su 16 fatti inglesi, e dichiarava
di non aver isolato la causa del livello basso. La causa c'era: SETTE dei
sedici fatti erano QUARANTINATI, e il prodotto li tiene FUORI dal recall di
default - e' il suo contratto, non un difetto.

Il campione era viziato sulla dimensione che il decisore usa: avevo filtrato
superseded_by IS NULL e NON lo status.

Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3
import unicodedata

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

COPPIE = [
    ("dce592fd45d5", "how did the perception of rodents change after caring for a pet",
     "come e cambiata la percezione dei roditori dopo aver curato un animale"),
    ("c312490739e8", "why did the clothing preference shift from casual to handmade sneakers",
     "perche la preferenza di abbigliamento e passata dalle scarpe casual a quelle fatte a mano"),
    ("17255c6cf701", "the decision to update food preferences aligns with which life goal",
     "la decisione di aggiornare le preferenze alimentari si allinea a quale obiettivo di vita"),
    ("b18c649d05d2", "the dialogue emphasized overcoming biases and embracing new experiences",
     "il dialogo ha sottolineato il superamento dei pregiudizi e l apertura a nuove esperienze"),
    ("05c1bfd1522f", "insights from a seminar on sustainable fabrics and the economic benefits of traditional materials",
     "spunti da un seminario sui tessuti sostenibili e i benefici economici dei materiali tradizionali"),
    ("b0f04695ceb5", "incorporating insights from the fashion innovation workshop into community programs",
     "portare gli spunti del laboratorio di innovazione della moda nei programmi di comunita"),
    ("c6e6239700d3", "expanded social connections enhance the effectiveness and reach of volunteer programs",
     "connessioni sociali piu ampie migliorano l efficacia e la portata dei programmi di volontariato"),
    ("688fa84c5a65", "adaptability in personal preferences as a key aspect of personal growth",
     "l adattabilita nelle preferenze personali come aspetto chiave della crescita personale"),
    ("7e7381d1330f", "the transition to community program director is motivated by which passion",
     "la transizione a direttore dei programmi di comunita e motivata da quale passione"),
    ("d7dab32cb613", "seeking books that reflect themes of social change and personal growth",
     "cercare libri che riflettano temi di cambiamento sociale e crescita personale"),
    ("4609963352d1", "the instrumental motivation driving the effort to build partnerships",
     "la motivazione strumentale che guida lo sforzo di costruire partnership"),
    ("cf3a30fb4d75", "practical insights from music composition guides aid the soundtrack creation process",
     "gli spunti pratici dalle guide di composizione musicale aiutano il processo di creazione della colonna sonora"),
    ("a9c1c7791397", "resilience and optimism maintained through the support of a social network",
     "resilienza e ottimismo mantenuti grazie al sostegno di una rete sociale"),
    ("e112a72c2868", "leisure activities such as painting contributing positively to career goals",
     "attivita del tempo libero come la pittura che contribuiscono positivamente agli obiettivi di carriera"),
    ("141df7f50277", "plans to focus solely on internal development rather than industry partnerships",
     "piani per concentrarsi solo sullo sviluppo interno invece che sulle partnership di settore"),
    ("827fb3bb620d", "python execution applied transformations catching off-by-one and wrap-around errors",
     "l esecuzione python ha applicato trasformazioni intercettando errori di off-by-one e di avvolgimento"),
]


def parole(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 2}


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(COPPIE))
db = con.execute("SELECT id, proposition, status FROM facts WHERE id IN (%s)" % ph,
                 tuple(c[0] for c in COPPIE)).fetchall()
con.close()
testi = {r[0]: r[1] for r in db}
stato = {r[0]: r[2] for r in db}

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


gruppi = {}
for lg in ("EN", "IT"):
    for st in ("servibile", "quarantined"):
        gruppi[(lg, st)] = []

for fid, qen, qit in COPPIE:
    if fid not in testi:
        continue
    pp = parole(testi[fid])
    st = "quarantined" if stato.get(fid) == "quarantined" else "servibile"
    for lg, q in (("EN", qen), ("IT", qit)):
        sovr = len(parole(q) & pp) / max(1, len(parole(q)))
        ok, rango = prova(q, fid)
        gruppi[(lg, st)].append((sovr, ok, rango))

print("Il campione del doc 58, separato per STATUS")
print("(i quarantinati stanno FUORI dal recall di default: contratto del")
print(" prodotto, non un difetto. Il doc 58 li mescolava ai servibili.)\n")
print("%-36s %-14s %-10s %s" % ("", "ritrovati", "al 1o posto", "sovrapp."))
for (lg, st), eti in (
        (("EN", "servibile"), "SERVIBILI     domanda in INGLESE"),
        (("IT", "servibile"), "SERVIBILI     la STESSA in ITALIANO"),
        (("EN", "quarantined"), "QUARANTINATI  domanda in INGLESE"),
        (("IT", "quarantined"), "QUARANTINATI  la STESSA in ITALIANO")):
    g = gruppi[(lg, st)]
    n = len(g)
    if not n:
        print("%-36s  nessun caso" % eti)
        continue
    t = sum(1 for x in g if x[1])
    pr = sum(1 for x in g if x[2] == 1)
    sv = sum(x[0] for x in g) / n
    print("%-36s %2d/%-2d = %5.1f%%  %2d = %5.1f%%   %5.1f%%"
          % (eti, t, n, 100.0 * t / n, pr, 100.0 * pr / n, 100 * sv))
