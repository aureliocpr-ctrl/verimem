"""Il limite aperto del doc 58: perche' su prosa discorsiva altrui il livello e'
56,2% invece di 91,7%?

Le due candidate erano (a) AMBIGUITA' - 105 fatti quasi identici sugli stessi
due personaggi - e (b) REGISTRO discorsivo. Il controllo col nome proprio non
discriminava, e l'avevo dichiarato.

Non serve un altro corpus: basta guardare DOVE FINISCONO i fatti non trovati.

  se la domanda restituisce ALTRI FATTI DELLO STESSO CLUSTER e il fatto atteso
  sta poco oltre k=10  ->  la domanda aggancia il posto giusto e sbaglia la
                           riga: AMBIGUITA'
  se restituisce roba SCORRELATA e il fatto atteso e' lontanissimo o assente
                       ->  la domanda non aggancia: non e' ambiguita'

Due righelli, sugli stessi 16 fatti del doc 58:
  ① il RANGO REALE con k=100 (invece di k=10)
  ② quanti dei primi 10 risultati appartengono al CLUSTER del fatto atteso
     (criterio: il nome proprio del fatto compare nel risultato)

Store di Aurelio: SOLA LETTURA.
"""
import os
import re
import sqlite3

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
K_LARGO = 100

COPPIE = [
    ("dce592fd45d5", "how did the perception of rodents change after caring for a pet", "Donna"),
    ("c312490739e8", "why did the clothing preference shift from casual to handmade sneakers", "Christopher"),
    ("17255c6cf701", "the decision to update food preferences aligns with which life goal", "Christopher"),
    ("b18c649d05d2", "the dialogue emphasized overcoming biases and embracing new experiences", "Donna"),
    ("05c1bfd1522f", "insights from a seminar on sustainable fabrics and the economic benefits of traditional materials", "Donna"),
    ("b0f04695ceb5", "incorporating insights from the fashion innovation workshop into community programs", "Christopher"),
    ("c6e6239700d3", "expanded social connections enhance the effectiveness and reach of volunteer programs", "Christopher"),
    ("688fa84c5a65", "adaptability in personal preferences as a key aspect of personal growth", "Christopher"),
    ("7e7381d1330f", "the transition to community program director is motivated by which passion", "Christopher"),
    ("d7dab32cb613", "seeking books that reflect themes of social change and personal growth", "Christopher"),
    ("4609963352d1", "the instrumental motivation driving the effort to build partnerships", "Christopher"),
    ("cf3a30fb4d75", "practical insights from music composition guides aid the soundtrack creation process", "Donna"),
    ("a9c1c7791397", "resilience and optimism maintained through the support of a social network", "Donna"),
    ("e112a72c2868", "leisure activities such as painting contributing positively to career goals", "Donna"),
    ("141df7f50277", "plans to focus solely on internal development rather than industry partnerships", "Steven"),
    ("827fb3bb620d", "python execution applied transformations catching off-by-one and wrap-around errors", "Python"),
]

con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
ph = ",".join("?" * len(COPPIE))
testi = dict(con.execute(
    "SELECT id, proposition FROM facts WHERE id IN (%s)" % ph,
    tuple(c[0] for c in COPPIE)).fetchall())
con.close()

from verimem.client import Memory   # noqa: E402 - dopo la sola lettura

m = Memory(DB)

print("%-14s %-8s %-9s %s" % ("fatto", "rango", "nel top10", "domanda"))
righe = []
for fid, q, nome in COPPIE:
    if fid not in testi:
        continue
    try:
        res = m.recall(q, k=K_LARGO)
    except Exception:
        res = []
    rango = None
    stesso = 0
    for r, it in enumerate(res or [], 1):
        if not isinstance(it, dict):
            continue
        if it.get("id") == fid and rango is None:
            rango = r
        if r <= 10 and re.search(re.escape(nome), str(it.get("text") or ""), re.I):
            stesso += 1
    righe.append((fid, rango, stesso, q))
    print("%-14s %-8s %2d/10     %s"
          % (fid, str(rango) if rango else ">%d" % K_LARGO, stesso, q[:56]))

entro10 = [r for _f, r, _s, _q in righe if r and r <= 10]
oltre10 = [r for _f, r, _s, _q in righe if r and r > 10]
mai = [1 for _f, r, _s, _q in righe if not r]
print("\nRANGO REALE con k=%d, sui %d fatti:" % (K_LARGO, len(righe)))
print("  entro i primi 10        : %d" % len(entro10))
print("  fra 11 e %d             : %d   %s"
      % (K_LARGO, len(oltre10), sorted(oltre10)))
print("  oltre %d o assente      : %d" % (K_LARGO, len(mai)))

persi = [(f, s, q) for f, r, s, q in righe if not r or r > 10]
if persi:
    med = sorted(s for _f, s, _q in persi)
    print("\nSUI %d NON TROVATI ENTRO 10 - quanti dei primi 10 risultati" % len(persi))
    print("appartengono al CLUSTER del fatto atteso (stesso nome proprio):")
    for f, s, q in persi:
        print("  %-14s %2d/10   %s" % (f, s, q[:52]))
    print("  mediana: %d su 10" % med[len(med) // 2])
    print("\n  ALTO (8-10) => la domanda aggancia il posto giusto e sbaglia la")
    print("  riga: AMBIGUITA'.  BASSO (0-3) => non aggancia il cluster: la causa")
    print("  non e' l'ambiguita' fra fatti simili.")
