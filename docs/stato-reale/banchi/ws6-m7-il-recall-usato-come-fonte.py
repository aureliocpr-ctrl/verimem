# -*- coding: utf-8 -*-
"""M7 — quanti fatti hanno come PROVA un output della memoria stessa?

    python docs/stato-reale/banchi/ws6-m7-il-recall-usato-come-fonte.py

IL MURO, dall'audit pubblico su mem0 (808 copie di un fatto inventato): un fatto
ri-estratto da un **recall** è sostenuto dalla propria origine — la source *è* il
recall — quindi il gate lo ammette, e a ogni giro se ne fa un'altra copia. La
memoria smette di misurare il mondo e comincia a misurare se stessa.

⚠️ QUI NON BASTA UN CRITERIO SOLO, perché «la source contiene un fatto» copre due
cose diversissime: un'OSSERVAZIONE SUL CORPUS («il fatto X dice Y», del tutto
legittima, ed è metà del lavoro di questo gruppo) e un ANELLO CHIUSO (il fatto
nuovo *è* il fatto citato). Tre criteri, dal più largo al più stretto:

  C2  la source ha il FORMATO di un output di recall
      (marcatori: `score=`, `grounding=`, `topic=`, `fact_id`, o >= 3 id
       esadecimali da 12 caratteri, che è la forma con cui la memoria stampa)

  C1  la source CONTIENE la proposizione di un ALTRO fatto dello store
      (match esatto dei primi 60 caratteri, che è come un recall la stampa)

  C3  ANELLO CHIUSO = C1 **e** la proposizione del fatto nuovo somiglia a quella
      citata per >= 80% (SequenceMatcher). È il feedback loop vero: il fatto si
      sostiene da sé.

╔═ PREDIZIONE, scritta PRIMA (fatto in verimem, 02/09 19:06) ═══════════════════╗
║  C2 fra 0 e 5 · C1 fra 20 e 80 · C3 fra 0 e 3                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

⛔ SOLA LETTURA. Nessuna scrittura, nessun modello caricato: è tutto SQL e testo.
"""
import datetime as _dt
import difflib
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
CHIAVE = 60          # quanti caratteri di proposizione usare come impronta
SIMILE = 0.80        # soglia di somiglianza per dire «è lo stesso fatto»

RE_ID = re.compile(r"\b[0-9a-f]{12}\b")
MARCATORI = ("score=", "grounding=", "topic=", "fact_id", "facts_search",
             "hippo_recall", "verimem recall", "[recall]")

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
righe = con.execute(
    "SELECT id, proposition, grounding_span, topic, created_at FROM facts "
    "WHERE proposition IS NOT NULL").fetchall()
con.close()

ora = _dt.datetime.now()
tot = len(righe)
con_span = [r for r in righe if r[2]]
print("M7 — LA MEMORIA USATA COME PROVA DI SE STESSA")
print("letto il %s · corpus %d fatti · con una prova conservata %d\n"
      % (ora.strftime("%Y-%m-%d %H:%M:%S"), tot, len(con_span)))

# impronta -> (id, proposizione) di OGNI fatto: è il dizionario in cui cercare
impronte = {}
for fid, prop, _s, _t, _c in righe:
    p = " ".join((prop or "").split())
    if len(p) >= CHIAVE:
        impronte.setdefault(p[:CHIAVE], (fid, p))

c2, c1, c3 = [], [], []
for fid, prop, span, topic, creato in con_span:
    s = " ".join(str(span).split())
    if any(m in s for m in MARCATORI) or len(set(RE_ID.findall(s))) >= 3:
        c2.append((fid, topic, prop))
    # C1: scorro lo span cercando l'impronta di una proposizione ALTRUI
    for i in range(0, max(1, len(s) - CHIAVE + 1)):
        trovato = impronte.get(s[i:i + CHIAVE])
        if trovato and trovato[0] != fid:
            c1.append((fid, trovato[0], prop, trovato[1]))
            mio = " ".join((prop or "").split())
            if difflib.SequenceMatcher(None, mio, trovato[1]).ratio() >= SIMILE:
                c3.append((fid, trovato[0], mio, trovato[1]))
            break

print("  C2  source col FORMATO di un recall                     %5d" % len(c2))
print("  C1  source che CONTIENE la proposizione di un altro     %5d" % len(c1))
print("  C3  ANELLO CHIUSO (C1 + somiglianza >= %.0f%%)            %5d"
      % (SIMILE * 100, len(c3)))
print("\n  la PREDIZIONE era: C2 fra 0 e 5 · C1 fra 20 e 80 · C3 fra 0 e 3")

if c2:
    print("\nC2 — i primi, da leggere (il formato non prova l'anello):")
    for fid, topic, prop in c2[:5]:
        print("  %-14s %-26s %s" % (fid, str(topic)[:26], (prop or "")[:44]))
if c3:
    print("\nC3 — GLI ANELLI CHIUSI, uno per uno:")
    for fid, altro, mio, suo in c3[:8]:
        print("  %s  <-  %s" % (fid, altro))
        print("      nuovo:  %s" % mio[:78])
        print("      citato: %s" % suo[:78])
elif c1:
    print("\nC1 senza C3 — i primi, per mostrare che sono OSSERVAZIONI e non copie:")
    for fid, altro, prop, suo in c1[:4]:
        print("  %s cita %s" % (fid, altro))
        print("      nuovo:  %s" % (prop or "")[:78])
        print("      citato: %s" % suo[:78])
