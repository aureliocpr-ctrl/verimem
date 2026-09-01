"""Il filone «le letture non trovano»: quante letture mute adesso PARLANO.

Un case-study vale se porta un numero che prima non c'era. Il filone ha prodotto
tre documenti di diagnosi (61, 67, 69) e tre commit nel prodotto; questo banco
misura la cosa che l'utente vede davvero cambiata.

PRIMA (documentato nel `67` §⑥, misurato il 2026-09-01 alle 20:37 col controllo
positivo acceso nella stessa esecuzione):

    A. il filtro TEMPORALE ha scartato tutto   n=0  AVVISO: NESSUNO
    C. la SOGLIA ha tagliato tutto             n=0  AVVISO: tagliati=6 …

cioe' su una risposta svuotata dal routing temporale il chiamante riceveva il
vuoto e NON aveva modo di sapere perche'.

DOPO: `letto_al_passato` (5f84f8a5) piu' la correzione del fuso (6d79f676).

RIGHELLO: prendere le domande che il `67` ha misurato come SPENTE dal routing —
quelle costruite dal testo di fatti RETROSPETTIVI, cioe' scritti dopo la data che
nominano — e contare quante, oggi, ricevono una DICHIARAZIONE invece del
silenzio. E, per non misurare una sola meta', contare anche quante volte la
dichiarazione esce dove NON serve.

⚠️ PRESIDIO: solo fatti vivi e non quarantinati (doc 58).
⚠️ Questo NON misura quante letture reali siano state salvate: il journal non
registra il testo delle query (67 §⑦). Misura la copertura della dichiarazione
sulla popolazione dove il difetto accade.

SOLA LETTURA sullo store.
"""
import datetime as dt
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K = 10

MESI = "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
NUM = dict((m, i + 1) for i, m in enumerate(MESI.split("|")))
RE_DATA = re.compile(r"\b(\d{1,2})\s+(%s)\s+(\d{4})\b" % MESI, re.I)


def retrospettivo(prop, created_at):
    mm = RE_DATA.search(prop or "")
    if not mm:
        return None
    try:
        quando = dt.datetime(int(mm.group(3)), NUM[mm.group(2).lower()],
                             int(mm.group(1)), 23, 59, 59,
                             tzinfo=dt.timezone.utc).timestamp()
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

retro = [(i, p) for i, p, c in righe if retrospettivo(p, c) is True]
contemp = [(i, p) for i, p, c in righe if retrospettivo(p, c) is False]
print("fatti vivi non quarantinati con una data nel testo : %d" % len(righe))
print("  RETROSPETTIVI (dove il difetto accade)           : %d" % len(retro))
print("  contemporanei (dove non puo' accadere)           : %d" % len(contemp))
print()

from verimem.client import Memory   # noqa: E402 — dopo la lettura

m = Memory(DB)


def esamina(coppie, etichetta):
    vuote = dichiarate = servite = dich_inutili = 0
    for _fid, prop in coppie:
        dom = " ".join((prop or "").split()[:12])
        try:
            r = m.recall(dom, k=K)
        except Exception:      # noqa: BLE001
            continue
        avviso = getattr(r, "letto_al_passato", None)
        if not (r or []):
            vuote += 1
            if avviso:
                dichiarate += 1
        else:
            servite += 1
            if avviso:
                dich_inutili += 1
    print("%s (n=%d)" % (etichetta, len(coppie)))
    print("  risposte VUOTE                       : %2d" % vuote)
    print("    di cui DICHIARATE (letto_al_passato): %2d  <- prima erano 0" % dichiarate)
    print("  risposte servite                     : %2d" % servite)
    print("    con dichiarazione dove NON serve    : %2d  <- rumore" % dich_inutili)
    print()
    return vuote, dichiarate, dich_inutili


v1, d1, r1 = esamina(retro, "RETROSPETTIVI — la popolazione dove il difetto accade")
v2, d2, r2 = esamina(contemp, "CONTEMPORANEI — l'altra popolazione (controllo)")

print("=" * 66)
if v1:
    print("COPERTURA sulla popolazione colpita : %d/%d = %.1f%%"
          % (d1, v1, 100.0 * d1 / v1))
else:
    print("COPERTURA: nessuna risposta vuota nel campione — niente da dichiarare.")
print("RUMORE (dichiarazione dove i risultati ci sono): %d + %d" % (r1, r2))
print()
print("Il PRIMA non e' rieseguibile: il codice e' cambiato. Vale 0 per")
print("costruzione — la condizione dell'avviso richiedeva risultati trovati")
print("prima del taglio, e qui il filtro temporale li aveva gia' scartati tutti.")
