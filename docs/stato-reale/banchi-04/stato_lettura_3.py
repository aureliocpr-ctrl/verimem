# -*- coding: utf-8 -*-
"""FETTA ④ — banco 3: la QUINTA porta, `search-docs` (i documenti), su questo SHA.

Ieri avevo misurato che il tier documenti **dichiara da solo** di non astenersi e
suggerisce `--min-score`. Rifaccio su 544d27bd, perche' una misura vale sullo SHA
in cui e' stata presa.
Copro: cosa restituisce · se si astiene · se il consiglio del prodotto funziona ·
e il ciclo completo (chunk -> `trust`), che e' l'unico modo documentato per avere
un verdetto su una risposta presa da un documento.
Store ISOLATO.
"""
import os, sys, io, contextlib, tempfile, shutil, re

SCRATCH = os.path.dirname(os.path.abspath(__file__))
BASE = tempfile.mkdtemp(prefix="stato4c_")
os.environ["HIPPO_DATA_DIR"] = BASE
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.cli import app as cli_app

MANUALE = """Manuale operativo Sud S.r.l. — edizione 2026

1. Magazzino
Il magazzino centrale di Verona contiene 2700 unita su 22 pallet.
Il turno di notte inizia alle 22 e termina alle 6.

2. Condizioni di pagamento
Il pagamento delle fatture e fissato a 60 giorni.
Gli interessi di mora sono pari al 4 per cento annuo.

3. Qualita
La responsabile della qualita e Anna Ferri, presso la sede di Perugia.
"""

def cli(argv):
    b = io.StringIO()
    try:
        with contextlib.redirect_stdout(b), contextlib.redirect_stderr(b):
            cli_app(argv, standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:
        b.write("[EXC %s: %s]" % (type(e).__name__, e))
    return b.getvalue()

p = os.path.join(SCRATCH, "manuale_stato.txt")
open(p, "w", encoding="utf-8").write(MANUALE)
out_index = cli(["index", p])

print("=" * 100)
print("  A. `index` — cosa dice quando ingerisce un documento")
print("=" * 100)
for l in out_index.splitlines():
    if "indexed" in l or "chunks" in l:
        print("   ", l.strip()[:96])

def cerca(q, extra=None):
    out = cli(["search-docs", q] + (extra or []))
    m = re.search(r"\(([\d.]+)\)", out)
    return (float(m.group(1)) if m else None), out

print()
print("=" * 100)
print("  B. `search-docs` — si astiene quando la risposta NON c'e'?")
print("=" * 100)
print("  {:<3} {:<50} {:>10}  {}".format("tipo", "domanda", "punteggio", "esito"))
print("  " + "-" * 92)
DOM = [
 ("A", "Quante unita contiene il magazzino centrale?"),
 ("A", "Chi e la responsabile della qualita?"),
 ("B", "Qual e il fatturato consolidato del 2025?"),
 ("B", "Quanti dipendenti ha l azienda?"),
 ("C", "Quante unita contiene il magazzino di Trento?"),
]
for tipo, q in DOM:
    pt, out = cerca(q)
    print("  {:<3}  {:<50} {:>10}  {}".format(
        tipo, q[:48], pt if pt is not None else "-",
        "risponde" if pt is not None else "SI ASTIENE"))

print("\n  la riga che il prodotto stampa DA SOLO in fondo a ogni risposta:")
_, out = cerca("Quante unita contiene il magazzino centrale?")
coda = [l.strip() for l in out.splitlines() if l.strip()][-3:]
for l in coda:
    print("     ", l[:92])

print()
print("=" * 100)
print("  C. IL CONSIGLIO DEL PRODOTTO — `--min-score`. Funziona su questo SHA?")
print("=" * 100)
IMP = "Qual e il fatturato consolidato del 2025?"
VER = "Quante unita contiene il magazzino centrale?"
pi, _ = cerca(IMP)
pv, _ = cerca(VER)
print("    senza soglia   domanda SENZA risposta -> {}   domanda VERA -> {}".format(pi, pv))
for s in ("0.75", "0.80", "0.85"):
    a, _ = cerca(IMP, ["--min-score", s])
    b_, _ = cerca(VER, ["--min-score", s])
    print("    --min-score {}  senza risposta: {:<22} vera: {}".format(
        s, "SI ASTIENE" if a is None else "risponde (%s)" % a,
        "persa anche lei" if b_ is None else "risponde (%s)" % b_))

print()
print("=" * 100)
print("  D. IL CICLO DOCUMENTATO — prendo il chunk e chiedo `trust` se posso fidarmi")
print("=" * 100)
_, out = cerca(VER)
righe = [l.strip() for l in out.splitlines() if l.strip()]
chunk = " ".join(l for l in righe
                 if not l.startswith(("1.", "2.", "3.", "file:", "top-1", "tagliare", "risposta")))[:600]
CASI = [
 ("VERA (dal documento)",      "Il magazzino centrale di Verona contiene 2700 unita."),
 ("INVENTATA verosimile",      "Il magazzino centrale di Verona contiene 2700 unita su 30 pallet."),
 ("INVENTATA grossolana",      "Il magazzino centrale di Livorno contiene 9900 unita."),
]
print("  {:<26} {:>8}  {}".format("affermazione", "moat", "verdetto"))
print("  " + "-" * 60)
for et, aff in CASI:
    o = cli(["trust", aff, "--source", chunk])
    v = "SEGNALATO" if "FLAGGED" in o else ("fidato" if "TRUSTED" in o else "?")
    mm = re.search(r"judged the source at ([\d.]+)", o)
    print("  {:<26} {:>8}  {}".format(et, mm.group(1) if mm else "-", v))

try:
    os.unlink(p)
except OSError:
    pass
shutil.rmtree(BASE, ignore_errors=True)
