"""L4.2 e' un cattivo criterio, o e' un buon criterio FUORI DAL SUO DOMINIO?

Sui casi puliti di prosa e' 4/4 preso e 2/2 taciuto. Sul nostro corpus spara sul
47% dei fatti sani. La differenza candidata e' la FORMA DELLA FONTE: prosa
contro output di strumento (tabelle, log, chiave=valore).

Si separa il corpus nelle due forme e si rifa' il conto su ENTRAMBE le
popolazioni. Se il tasso di falsi allarmi crolla sulla prosa, il criterio e'
sano e il nostro corpus e' il caso anomalo — e la conclusione da consegnare e'
l'opposto di «L4.2 e' rotto».
"""
import re
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from verimem.config import CONFIG  # noqa: E402
from verimem.vicinato_del_valore import (  # noqa: E402
    valori_riusati_da_altro_contesto as l42,
)

# una fonte e' «output di strumento» se porta i segni tipici: colonne, exit
# code, percentuali fra parentesi, chiave=valore, righe che iniziano con spazi
_SEGNI = (
    re.compile(r"EXIT\s*=|exit code|\bpassed\b|\bfailed\b|\bxfailed\b"),
    re.compile(r"^\s{2,}\S", re.MULTILINE),
    re.compile(r"\w+=\S"),
    re.compile(r"\(\d+%\)"),
    re.compile(r"\|\s|\t"),
)


def e_un_referto(source: str) -> bool:
    s = source or ""
    if s.count("\n") >= 2:
        return True
    return sum(1 for r in _SEGNI if r.search(s)) >= 1


def taratura():
    """Il banco non misura se non ritrova il caso noto del docstring."""
    preso = l42("Il magazzino contiene 14 valvole.", "Il turno impiega 14 operai.")
    taciuto = l42("Il magazzino contiene 14 valvole.",
                  "Nel magazzino ci sono 14 valvole.")
    print("taratura: caso vero -> %s · riformulazione -> %s" % (
        "PRESO" if preso else "PERSO", "tace" if not taciuto else "AVVISA"))
    if not preso or taciuto:
        print("RIGHELLO ROTTO. Non misuro.")
        raise SystemExit(1)
    print()


con = sqlite3.connect(str(CONFIG.semantic_db))
con.row_factory = sqlite3.Row
taratura()

POP = [
    ("QUARANTINATI g>=90", "status='quarantined'"),
    ("AMMESSI      g>=90", "status='model_claim'"),
]

tab = {}
for et, dove in POP:
    righe = con.execute(f"""SELECT proposition, grounding_span FROM facts
        WHERE {dove} AND superseded_by IS NULL AND grounding_score >= 90
          AND grounding_span IS NOT NULL AND TRIM(grounding_span) <> ''
        ORDER BY created_at DESC LIMIT 400""").fetchall()
    for forma in ("prosa", "referto"):
        sel = [r for r in righe
               if e_un_referto(r["grounding_span"]) == (forma == "referto")]
        n = len(sel)
        avvisa = 0
        for r in sel:
            try:
                if l42(r["proposition"] or "", r["grounding_span"] or ""):
                    avvisa += 1
            except Exception:  # noqa: BLE001
                pass
        tab[(et, forma)] = (n, avvisa)

print("%-20s %-9s %6s %8s" % ("popolazione", "fonte", "n", "L4.2"))
print("-" * 48)
for (et, forma), (n, a) in tab.items():
    print("%-20s %-9s %6d %6.0f%%" % (et, forma, n, 100.0 * a / max(1, n)))
print()

for forma in ("prosa", "referto"):
    nq, aq = tab[("QUARANTINATI g>=90", forma)]
    na, aa = tab[("AMMESSI      g>=90", forma)]
    pq, pa = aq / max(1, nq), aa / max(1, na)
    sep = (pq / pa) if pa else float("inf")
    print("su fonte %-8s  falsi allarmi %3.0f%% (n=%d)   separazione %.1fx" % (
        forma, 100 * pa, na, sep))
print()
print("Se sulla PROSA i falsi allarmi crollano, il criterio e' sano e il nostro")
print("corpus e' il caso anomalo.")
