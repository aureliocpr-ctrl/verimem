"""T2.1 — L'EFFETTO LINGUA SUL CORPUS REALE, non su un banco fabbricato.

    python scripts/banco_lingua_store_vivo.py

PERCHE' NON UN TERZO BANCO FABBRICATO. I miei due precedenti sono finiti agli estremi
opposti, entrambi per come li avevo costruiti IO:
  12 fatti a domini disgiunti  -> SOFFITTO: 12/12 IT e 12/12 EN (anello ①)
  100 fatti della stessa forma -> PAVIMENTO:  6/50 IT e  6/50 EN (anello ③, banco rotto)
In tutti e due l'effetto lingua era |IT-EN| = 0, ma nessuno dei due e' il corpus di un
utente. Lo store vivo invece ha ENTRAMBE le lingue nello STESSO indice (misurato il 02/09:
75,8% IT, 14,0% EN, 10,2% non classificabile su 17 149 proposizioni) — quindi l'effetto
lingua si misura a parita' di indice, di fusione e di embedder: l'unica variabile e' la
lingua del fatto.

DISEGNO. Per ogni fatto campionato costruisco la query in modo DETERMINISTICO dal fatto
stesso — i suoi 6 token piu' lunghi, in ordine di apparizione — cosi' la domanda non e' una
mia invenzione e il metodo e' identico nelle due lingue. E' il LIMITE SUPERIORE del recall
(«cercando un fatto con le sue stesse parole chiave, lo ritrovo?»): se anche qui le due
lingue divergono, il divario e' reale; se non divergono, la lingua non e' la variabile.
⚠️ SOLA LETTURA sullo store vivo. Nessuna scrittura. Solo embedder, nessun giudice.

PREDIZIONE SCRITTA PRIMA (02/09 19:10):
    IT al primo posto >= 80%   ·   EN al primo posto >= 80%   ·   |IT - EN| <= 5 punti
(coerente con i due banchi precedenti, dove |IT-EN| era 0 in entrambi i regimi)
CONDIZIONE D'USCITA:
    |IT - EN| >= 15 punti -> il divario di lingua ESISTE sul corpus reale: T2.1 ha una
                             baseline e il confronto fra embedder ha senso
    |IT - EN| <= 5 punti  -> TERZO punto indipendente che dice che la lingua non e' la
                             variabile del recall: T2.1 perde la sua premessa
    fra 5 e 15            -> intermedio, lo dichiaro senza chiamarlo effetto
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

K = 10
N_PER_LINGUA = 40

IT = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
      "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
EN = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
      "from", "was", "were", "has", "have", "in", "on", "by", "as"}


def lingua(testo):
    p = set(re.findall(r"[a-zà-ù']+", testo.lower()))
    a, b = len(p & IT), len(p & EN)
    return "it" if a > b else ("en" if b > a else "?")


def query_da_fatto(testo, n=6):
    """Deterministica: i `n` token piu' lunghi, in ordine di apparizione.

    Nessuna domanda inventata da me, e lo stesso identico metodo nelle due lingue.
    """
    tok = re.findall(r"[\w\-.]{3,}", testo)
    if not tok:
        return testo[:60]
    scelti = sorted(sorted(set(tok), key=tok.index), key=len, reverse=True)[:n]
    return " ".join(sorted(scelti, key=tok.index))


def campiona():
    con = sqlite3.connect(f"file:{CONFIG.semantic_db}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT proposition FROM facts WHERE proposition IS NOT NULL "
        "AND length(proposition) BETWEEN 60 AND 300"
    ).fetchall()
    con.close()
    it, en = [], []
    for (p,) in righe:
        p = str(p)
        lg = lingua(p)
        if lg == "it" and len(it) < N_PER_LINGUA:
            it.append(p)
        elif lg == "en" and len(en) < N_PER_LINGUA:
            en.append(p)
        if len(it) >= N_PER_LINGUA and len(en) >= N_PER_LINGUA:
            break
    return it, en


def misura(mem, fatti, nome):
    primo = entro = 0
    persi = []
    for f in fatti:
        q = query_da_fatto(f)
        r = mem.search(q, k=K)
        pos = -1
        for j, x in enumerate(r):
            if (x.get("text") or "")[:60].strip() == f[:60].strip():
                pos = j + 1
                break
        if pos == 1:
            primo += 1
        if pos > 0:
            entro += 1
        else:
            persi.append((q[:48], f[:48]))
    n = len(fatti) or 1
    print(f"  {nome:<22} primo posto {primo:>2}/{n} ({primo / n * 100:5.1f}%) | "
          f"entro k={K} {entro:>2}/{n}", flush=True)
    for q, f in persi[:3]:
        print(f"      perso — query «{q}» | fatto «{f}»", flush=True)
    return primo, n


def main():
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | store VIVO in sola lettura: {CONFIG.semantic_db}",
          flush=True)
    it, en = campiona()
    print(f"campionati {len(it)} fatti italiani e {len(en)} inglesi "
          f"(60-300 caratteri, euristica di parole funzionali)", flush=True)
    mem = Memory(CONFIG.semantic_db)
    # CONFONDENTE misurato il 02/09 19:09: il breaker del rerank e' scattato FRA i due
    # bracci ("5 of the last 7 reranks overran their budget -> CE rerank disabled for
    # this process"), quindi il primo braccio girava col rerank e il secondo senza: la
    # lingua era confusa con lo stato del rerank. `--ordine en-it` inverte i bracci: se
    # il divario si inverte era il rerank, se resta e' la lingua.
    inverti = "en-it" in sys.argv
    if inverti:
        print("  [ordine INVERTITO: prima INGLESE, poi ITALIANO]", flush=True)
        b, nb = misura(mem, en, "INGLESE")
        a, na = misura(mem, it, "ITALIANO")
    else:
        a, na = misura(mem, it, "ITALIANO")
        b, nb = misura(mem, en, "INGLESE")

    pit, pen = a / (na or 1) * 100, b / (nb or 1) * 100
    print("\n" + "=" * 74, flush=True)
    print(f"  ITALIANO al primo posto {pit:5.1f}%   INGLESE {pen:5.1f}%   "
          f"divario {abs(pit - pen):5.1f} punti", flush=True)
    if abs(pit - pen) >= 15:
        print("  => il divario di lingua ESISTE sul corpus reale: T2.1 ha una baseline.",
              flush=True)
    elif abs(pit - pen) <= 5:
        print("  => TERZO punto indipendente: la lingua NON e' la variabile del recall,\n"
              "     e T2.1 perde la sua premessa anche sul corpus vero.", flush=True)
    else:
        print("  => intermedio: lo dichiaro senza chiamarlo effetto.", flush=True)
    print("=" * 74, flush=True)
    print("PREDIZIONE (scritta prima): IT >=80% · EN >=80% · divario <=5 punti.", flush=True)


if __name__ == "__main__":
    main()
