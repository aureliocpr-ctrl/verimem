"""La soglia del rerank e' in PAROLE (10) e il corpus e' multilingue: a parita'
di lunghezza in CARATTERI, l'italiano supera la soglia piu' spesso dell'inglese?

Usa `_query_word_count` DEL PRODOTTO, non una reimplementazione.
SOLA LETTURA sullo store.  PROXY DICHIARATO: le proposizioni non sono query.
"""
import os
import sqlite3
import statistics

from verimem.semantic import _query_word_count, _rerank_auto_max_words

SOGLIA = _rerank_auto_max_words()
print("soglia del rerank (parole): %d" % SOGLIA)

# euristica di lingua: parole funzionali che non si sovrappongono fra IT e EN
IT = {"il", "lo", "la", "i", "gli", "le", "di", "del", "della", "dei", "delle",
      "che", "non", "per", "con", "sono", "e", "un", "una", "nel", "nella",
      "quando", "piu", "anche", "come", "alla", "dal", "sul"}
EN = {"the", "of", "and", "to", "in", "is", "that", "for", "with", "are",
      "not", "when", "this", "from", "it", "on", "as", "was", "by", "an"}

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
con = sqlite3.connect("file:%s?mode=ro" % DB.replace(os.sep, "/"), uri=True)
c = con.cursor()

dati = {"it": [], "en": []}
for (p,) in c.execute(
        "SELECT proposition FROM facts "
        "WHERE proposition IS NOT NULL AND topic NOT LIKE '%/auto-MASTER'"):
    tk = [w.strip(".,;:()[]\"'").lower() for w in str(p).split()]
    n_it = sum(1 for w in tk if w in IT)
    n_en = sum(1 for w in tk if w in EN)
    if n_it >= 3 and n_it > 2 * n_en:
        lg = "it"
    elif n_en >= 3 and n_en > 2 * n_it:
        lg = "en"
    else:
        continue
    dati[lg].append((_query_word_count(p), len(p)))
con.close()

print("\n%-4s %7s %10s %10s %12s %14s"
      % ("ling", "n", "parole~", "caratteri~", "par/1000ch", "sopra soglia"))
for lg in ("it", "en"):
    v = dati[lg]
    if not v:
        continue
    par = [a for a, _ in v]
    ch = [b for _, b in v]
    sopra = sum(1 for a, _ in v if a > SOGLIA)
    dens = 1000.0 * sum(par) / max(1, sum(ch))
    print("%-4s %7d %10.1f %10.1f %12.1f %10d = %4.1f%%"
          % (lg, len(v), statistics.median(par), statistics.median(ch),
             dens, sopra, 100.0 * sopra / len(v)))

print("\n== isolando la variabile: SOLO le proposizioni fra 100 e 200 caratteri ==")
print("%-4s %7s %10s %14s" % ("ling", "n", "parole~", "sopra soglia"))
for lg in ("it", "en"):
    v = [(a, b) for a, b in dati[lg] if 100 <= b <= 200]
    if not v:
        continue
    sopra = sum(1 for a, _ in v if a > SOGLIA)
    print("%-4s %7d %10.1f %10d = %4.1f%%"
          % (lg, len(v), statistics.median([a for a, _ in v]),
             sopra, 100.0 * sopra / len(v)))
