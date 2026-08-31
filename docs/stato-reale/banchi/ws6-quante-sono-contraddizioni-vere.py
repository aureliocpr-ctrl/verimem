"""Chiude il limite dichiarato nel doc 42.

Il `42` finiva con: "Quello che NON ho misurato: quante delle coppie
numeric_clash con jaccard >= 0,50 siano contraddizioni VERE. Sono ~137 nel
campione." E proponeva come cura: "portare nel rilevatore di contraddizioni il
criterio di L4.2", cioe' quello che LEGA numero e grandezza.

Quel criterio esiste gia' come funzione pubblica: `numeric_conflict(a, b)` in
quantity_match.py, che ritorna (unita, valore_a, valore_b) solo se i due testi
danno un valore DIVERSO per la STESSA unita' sullo STESSO soggetto - con le
guardie che il suo docstring elenca (stesso soggetto, nessun qualificatore
contrastante, nessun identificatore diverso).

⚠️ La CHIAMO in lettura. Non tocco il gate: nessuna modifica, nessuna scrittura.

Righello: delle coppie che il rilevatore dichiara in conflitto, quante il
criterio che lega numero e grandezza conferma?

⚠️ Misuro ENTRAMBE le popolazioni: le coppie ad alto jaccard (dove il conflitto
e' plausibile) e quelle a basso jaccard (dove il `42` sosteneva che il rilevatore
sbaglia). Se il criterio confermasse la stessa quota in entrambe, non
discriminerebbe e il righello non varrebbe niente.

SOLA LETTURA sullo store.
"""
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
LIMITE = 400            # coppie per gruppo: il criterio non e' gratis


def token(t):
    return {w for w in re.findall(r"[a-z0-9]+", str(t or "").lower()) if len(w) > 2}


def jaccard(a, b):
    ta, tb = token(a), token(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)

# PRESIDIO: che cosa contiene la tabella, prima di misurare.
tabelle = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%contradic%'")]
print("tabelle delle contraddizioni:", tabelle)
if not tabelle:
    print("nessuna tabella: non misuro niente")
    raise SystemExit(0)

T = tabelle[0]
cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % T)]
print("colonne:", cols)

tot = con.execute("SELECT COUNT(*) FROM %s" % T).fetchone()[0]
print("righe totali in %s: %d" % (T, tot))

campo_kind = "kind" if "kind" in cols else ("reason" if "reason" in cols else None)
campo_a = next((c for c in ("fact_a_id", "fact_a", "a_id") if c in cols), None)
campo_b = next((c for c in ("fact_b_id", "fact_b", "b_id") if c in cols), None)
campo_stato = "resolved_at" if "resolved_at" in cols else (
    "resolved" if "resolved" in cols else None)
if not (campo_a and campo_b):
    print("non trovo le colonne delle due parti: mi fermo")
    raise SystemExit(0)

where = []
if campo_stato:
    where.append("%s IS NULL" % campo_stato
                 if campo_stato == "resolved_at"
                 else "%s = 0" % campo_stato)
if campo_kind:
    where.append("%s LIKE '%%numeric%%'" % campo_kind)
w = (" WHERE " + " AND ".join(where)) if where else ""
righe = con.execute(
    "SELECT %s, %s FROM %s%s LIMIT 20000" % (campo_a, campo_b, T, w)).fetchall()
print("coppie numeriche irrisolte lette: %d" % len(righe))

ids = {x for c in righe for x in c if x}
ph = ",".join("?" * len(ids))
testi = dict(con.execute(
    "SELECT id, proposition FROM facts WHERE id IN (%s)" % ph, tuple(ids)).fetchall())
con.close()

alto, basso = [], []
for a, b in righe:
    ta, tb = testi.get(a), testi.get(b)
    if not ta or not tb:
        continue
    (alto if jaccard(ta, tb) >= 0.50 else basso).append((ta, tb))
print("  con jaccard >= 0.50: %d      con jaccard < 0.50: %d"
      % (len(alto), len(basso)))

from verimem.quantity_match import numeric_conflict   # noqa: E402 - dopo la lettura

print("\nQUANTE IL CRITERIO CHE LEGA NUMERO E GRANDEZZA CONFERMA")
print("%-38s %8s %10s %s" % ("popolazione", "n", "confermate", "quota"))
for eti, g in (("coppie ad ALTO jaccard (>= 0.50)", alto[:LIMITE]),
               ("coppie a BASSO jaccard (< 0.50)", basso[:LIMITE])):
    n = len(g)
    if not n:
        print("%-38s  nessuna" % eti)
        continue
    k = 0
    for ta, tb in g:
        try:
            if numeric_conflict(ta, tb) is not None:
                k += 1
        except Exception:      # noqa: BLE001 - una coppia che rompe non ferma il banco
            pass
    print("%-38s %8d %10d %5.1f%%" % (eti, n, k, 100.0 * k / n))

print("\nSe la quota confermata e' ALTA in alto-jaccard e BASSA in basso-jaccard,")
print("il criterio discrimina e il rilevatore sbaglia soprattutto sulle seconde.")
print("Se e' bassa in ENTRAMBE, quasi nessuna di queste coppie e' una")
print("contraddizione vera secondo il criterio che lega numero e grandezza.")
