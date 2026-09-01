"""La data nella domanda spegne la risposta.

Chiedendo «il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati» il
prodotto restituisce ZERO risultati. Senza la data restituisce 6, con best
0.8790 - SOPRA il pavimento 0.8781, quindi sarebbe una lettura buona.

La catena, letta nel codice:
  client.py:1117   as_of == "auto"  ->  extract_as_of(query)
  temporal_context.py:132  estrae «18 luglio 2026» -> epoch di fine giornata
  client.py:1128   recall_as_of(..., when=<18 luglio>)
  temporal_context.py:218  recall(k*6, include_superseded=True) e POI scarta
                           chi ha `born > when`

⚠️ Il filtro e' POST-RETRIEVAL su un pool oversampled ×6. Se i k*6 fatti piu'
simili sono TUTTI stati scritti dopo la data, non ne resta nessuno. Il docstring
di recall_as_of dice «oversampled so the as-of filter doesn't starve top-k»: e'
esattamente cio' che non regge.

RIGHELLO: per ogni fatto vivo il cui TESTO contiene una data italiana, costruire
la domanda dal suo stesso testo e misurare A/B NELLA STESSA ESECUZIONE:
    as_of="auto"  (come lo chiama il prodotto)   vs   as_of=None
Il fatto e' la risposta giusta per costruzione: se torna senza routing e non
torna con, il routing temporale ha spento una lettura che funzionava.

⚠️ PRESIDIO: solo fatti VIVI e non quarantinati (un quarantinato non torna per
contratto e falserebbe il conto - lezione del doc 58).

SOLA LETTURA sullo store.
"""
import os
import random
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10
SEME = 20260901

MESI = "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
NUM_MESE = dict((m, i + 1) for i, m in enumerate(MESI.split("|")))
RE_DATA = re.compile(r"\b(\d{1,2})\s+(%s)\s+(\d{4})\b" % MESI, re.I)


def e_retrospettivo(prop, created_at):
    """Il fatto e' stato SCRITTO DOPO la data che nomina?

    ⚠️ E' il DENOMINATORE VERO. Il filtro di `recall_as_of` scarta chi ha
    `born > when`: un fatto scritto NEL giorno che nomina non puo' essere
    colpito, quindi contarlo nel denominatore diluisce il tasso e lo fa
    sembrare piu' raro di quanto sia (la lezione del doc 66, pagata il 31/08).
    """
    import datetime as _dt
    mm = RE_DATA.search(prop or "")
    if not mm:
        return None
    try:
        quando = _dt.datetime(int(mm.group(3)), NUM_MESE[mm.group(2).lower()],
                              int(mm.group(1)), 23, 59, 59,
                              tzinfo=_dt.timezone.utc).timestamp()
    except (ValueError, KeyError, OverflowError):
        return None
    return float(created_at or 0.0) > quando

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
righe = con.execute("""
 SELECT id, proposition, created_at FROM facts
 WHERE superseded_by IS NULL AND status != 'quarantined'
   AND (proposition LIKE '%luglio 2026%'  OR proposition LIKE '%agosto 2026%'
     OR proposition LIKE '%giugno 2026%'  OR proposition LIKE '%maggio 2026%'
     OR proposition LIKE '%aprile 2026%'  OR proposition LIKE '%settembre 2026%')
""").fetchall()
con.close()

candidati = [(i, p, c) for i, p, c in righe if RE_DATA.search(p or "")]
print("fatti VIVI e non quarantinati con una data italiana nel testo : %d" % len(righe))
print("  di cui con la data in forma «D mese AAAA» (quella estratta)  : %d" % len(candidati))

random.seed(SEME)
camp = random.sample(candidati, min(40, len(candidati)))
print("  campione (seme %d)                                          : %d\n" % (SEME, len(camp)))

from verimem.client import Memory   # noqa: E402 - dopo la lettura

m = Memory(DB)
print("pavimento servito: %s\n" % m._auto_relevance_floor())


def rango(res, fid):
    for r, it in enumerate(res or [], 1):
        if isinstance(it, dict) and it.get("id") == fid:
            return r
    return None


# ⚠️ QUATTRO stati, non tre: senza il quarto («lo ACCENDE il routing») un
# caso a favore della funzione finirebbe fra i persi - e sarebbe il mio
# misuratore a mentire, non il prodotto.
spenti, accesi, gia_persi, ok, vuote_con, vuote_senza = [], [], [], [], 0, 0
n_retro = n_contemp = 0
spenti_retro = 0
for fid, prop, cre in camp:
    dom = " ".join((prop or "").split()[:12])      # frammento: il vocabolario del dominio
    retro = e_retrospettivo(prop, cre)
    if retro: n_retro += 1
    else: n_contemp += 1
    try:
        con_routing = m.recall(dom, k=K)            # come lo chiama il prodotto
        senza = m.recall(dom, k=K, as_of=None)      # stesso istante, stesso corpus
    except Exception:                               # noqa: BLE001
        continue
    if not (con_routing or []):
        vuote_con += 1
    if not (senza or []):
        vuote_senza += 1
    r_con, r_senza = rango(con_routing, fid), rango(senza, fid)
    if r_senza is not None and r_con is None:
        spenti.append((fid, r_senza, dom))
        if retro: spenti_retro += 1
    elif r_con is not None and r_senza is None:
        accesi.append((fid, r_con, dom))          # a FAVORE della funzione
    elif r_senza is None:
        gia_persi.append((fid, dom))
    else:
        ok.append(fid)

n = len(spenti) + len(accesi) + len(gia_persi) + len(ok)
print("A/B NELLA STESSA ESECUZIONE, su %d domande costruite dal testo del fatto" % n)
print("  il fatto torna in ENTRAMBI i casi                : %2d = %5.1f%%" % (len(ok), 100.0 * len(ok) / max(1, n)))
print("  TORNA SENZA ROUTING E NON CON  -> LO SPEGNE LUI  : %2d = %5.1f%%" % (len(spenti), 100.0 * len(spenti) / max(1, n)))
print("  torna SOLO col routing -> LO ACCENDE (a favore)  : %2d = %5.1f%%" % (len(accesi), 100.0 * len(accesi) / max(1, n)))
print("  non torna in nessuno dei due (altra causa)       : %2d = %5.1f%%" % (len(gia_persi), 100.0 * len(gia_persi) / max(1, n)))
print()
print("  risposte COMPLETAMENTE VUOTE col routing         : %2d = %5.1f%%" % (vuote_con, 100.0 * vuote_con / max(1, n)))
print("  risposte completamente vuote SENZA routing       : %2d = %5.1f%%" % (vuote_senza, 100.0 * vuote_senza / max(1, n)))

print()
print("IL DENOMINATORE VERO — solo un RETROSPETTIVO puo' essere colpito")
print("  retrospettivi nel campione (scritti DOPO la data che nominano) : %2d" % n_retro)
print("  contemporanei  (scritti nel giorno che nominano, o prima)      : %2d" % n_contemp)
print("  spenti fra i RETROSPETTIVI      : %2d/%d = %5.1f%%" % (spenti_retro, n_retro, 100.0 * spenti_retro / max(1, n_retro)))
print("  spenti fra i CONTEMPORANEI      : %2d/%d = %5.1f%%   <- l'altra popolazione: conferma il meccanismo"
      % (len(spenti) - spenti_retro, n_contemp, 100.0 * (len(spenti) - spenti_retro) / max(1, n_contemp)))

if spenti:
    print("\nLE LETTURE CHE IL ROUTING TEMPORALE SPEGNE (rango che avrebbero avuto):")
    for fid, r, dom in sorted(spenti, key=lambda x: x[1]):
        print("  rango %2d senza routing, ASSENTE con  %-14s %s" % (r, fid, dom[:52]))
