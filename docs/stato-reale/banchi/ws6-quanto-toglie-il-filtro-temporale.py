"""Quanto materiale toglie il filtro temporale, quando si attiva.

Il doc `70` ha misurato la COPERTURA della dichiarazione (0/3 → 3/3). Questo
banco misura la GRANDEZZA del fenomeno che dichiara: **quanti risultati il
filtro esclude** su una domanda che contiene una data.

Il caso che ha fatto nascere la domanda: `0ebe9e824198` serviva **2** fatti
scartandone **58**. Se fosse tipico, il filtro non è un dettaglio del ranking:
è la potatura più grossa che una lettura subisca.

⚠️ E la parte che interessa di più non sono i casi già noti come rotti, ma
quelli che sembrano **sani**: quando il fatto giusto TORNA lo stesso, quanti ne
sono stati scartati? Un filtro che toglie molto e per caso lascia dentro la
risposta è un rischio latente, non un successo.

⚠️ `scartati` è un «ALMENO»: `recall_as_of` smette di esaminare gli hit appena
ne ha `k` validi. Il vero numero di esclusi può essere più alto, mai più basso.

⚠️ PRESIDIO: solo fatti vivi e non quarantinati (doc 58).

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

casi = [(i, p, retrospettivo(p, c)) for i, p, c in righe
        if retrospettivo(p, c) is not None]
print("fatti vivi non quarantinati con una data «D mese AAAA»: %d" % len(casi))
print("  retrospettivi %d · contemporanei %d\n"
      % (sum(1 for _, _, r in casi if r), sum(1 for _, _, r in casi if not r)))

from verimem.client import Memory   # noqa: E402 — dopo la lettura

m = Memory(DB)

sani, rotti = [], []
for fid, prop, _retro in casi:
    dom = " ".join((prop or "").split()[:12])
    try:
        res = m.recall(dom, k=K)
    except Exception:      # noqa: BLE001
        continue
    av = getattr(res, "letto_al_passato", None)
    if av is None:
        continue                      # il filtro non si è attivato o non ha tolto
    scartati = int(av.get("scartati") or 0)
    torna = any(isinstance(i, dict) and i.get("id") == fid for i in (res or []))
    (sani if torna else rotti).append((scartati, len(res or []), fid))


def riassumi(gruppo, etichetta):
    if not gruppo:
        print("%s: nessun caso\n" % etichetta)
        return
    sc = sorted(s for s, _, _ in gruppo)
    tot_serviti = sum(n for _, n, _ in gruppo)
    tot_scartati = sum(sc)
    print("%s (n=%d)" % (etichetta, len(gruppo)))
    print("  scartati: min %d · mediana %d · max %d"
          % (sc[0], sc[len(sc) // 2], sc[-1]))
    print("  totale   : %d serviti contro %d scartati" % (tot_serviti, tot_scartati))
    if tot_serviti + tot_scartati:
        print("  il filtro toglie il %.1f%% di cio' che aveva in mano"
              % (100.0 * tot_scartati / (tot_serviti + tot_scartati)))
    print()


riassumi(rotti, "CASI ROTTI — il fatto che risponde e' stato ESCLUSO")
riassumi(sani, "CASI SANI — il fatto torna lo stesso (rischio latente)")

tutti = sani + rotti
if tutti:
    print("=" * 62)
    print("Su %d letture in cui il filtro temporale ha tolto qualcosa," % len(tutti))
    print("il fatto che risponde e' stato escluso in %d." % len(rotti))
    print()
    print("⚠️ `scartati` e' un ALMENO: il vero numero puo' essere piu' alto.")
