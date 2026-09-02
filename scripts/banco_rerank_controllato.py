"""Il rerank come VARIABILE CONTROLLATA — e la ripetibilita' come criterio di validita'.

    python scripts/banco_rerank_controllato.py off it-en
    python scripts/banco_rerank_controllato.py off en-it
    python scripts/banco_rerank_controllato.py on  it-en
    python scripts/banco_rerank_controllato.py on  en-it

⚠️ OGNI BRACCIO IN UN PROCESSO NUOVO: il breaker del rerank e' disabilitato «for this
process», quindi due bracci nello stesso processo non sono indipendenti.

PERCHE'. Il 02/09 alle 19:09-19:13 lo stesso banco ha dato ITALIANO 20,0% e poi 60,0% al
primo posto, cambiando SOLO l'ordine dei due bracci: in mezzo il prodotto stampava
«rerank breaker TRIPPED — CE rerank disabled for this process». La lingua era confusa con
lo stato del rerank.
⚠️ E NON E' UN REPERTO NUOVO: il 26/07 avevo gia' salvato
`lessons/errors/varianza-latenza-era-il-cross-encoder` — «la varianza delle mie misure di
latenza e' il cross-encoder, non la macchina: la stessa configurazione dava 493 e 610 ms».
Stessa causa, altra grandezza. L'avevo scritta io e non l'ho applicata al recall.

GLI INTERRUTTORI, letti nel codice (non inventati):
    ENGRAM_RECALL_RERANK=0            semantic.py:1706  «byte-identical legacy ranking»
    HIPPO_RECALL_RERANK_BUDGET_S=0    semantic.py:126   «0 disables the bound»
    ENGRAM_RERANK_BREAKER_N=99999     semantic.py:2104  il breaker non scatta

CRITERIO DI VALIDITA' (dal mandato): la misura vale SOLO se le due ripetizioni con ordine
invertito coincidono. Se non coincidono, la varianza ha un'altra fonte e il numero non si
consegna.

PREDIZIONE SCRITTA PRIMA (02/09 19:18):
    rerank OFF  -> le due ripetizioni coincidono entro 1 su 15 per lingua (misura VALIDA)
    rerank ON   -> le due ripetizioni coincidono entro 2 su 15 (il budget illimitato toglie
                   la causa nota della varianza)
    divario IT/EN in entrambi i regimi: sotto i 15 punti percentuali
CONDIZIONE D'USCITA:
    ripetizioni coincidenti in entrambi i regimi -> misura stabile: T2.1 puo' partire
    ripetizioni ancora divergenti                -> la varianza NON e' (solo) il rerank, e
                                                    va cercata altrove prima di misurare
                                                    qualunque embedder
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

_MODO = (sys.argv[1] if len(sys.argv) > 1 else "off").lower()
_ORDINE = (sys.argv[2] if len(sys.argv) > 2 else "it-en").lower()

for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
if _MODO == "off":
    os.environ["ENGRAM_RECALL_RERANK"] = "0"
else:
    os.environ["ENGRAM_RECALL_RERANK"] = "1"
    os.environ["HIPPO_RECALL_RERANK_BUDGET_S"] = "0"      # nessun bound
    os.environ["ENGRAM_RERANK_BREAKER_N"] = "99999"       # il breaker non scatta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

K = 10
N_PER_LINGUA = 15

IT = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
      "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
EN = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
      "from", "was", "were", "has", "have", "in", "on", "by", "as"}


def lingua(testo):
    p = set(re.findall(r"[a-zà-ù']+", testo.lower()))
    a, b = len(p & IT), len(p & EN)
    return "it" if a > b else ("en" if b > a else "?")


def query_da_fatto(testo, n=6):
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
    for f in fatti:
        r = mem.search(query_da_fatto(f), k=K)
        for j, x in enumerate(r):
            if (x.get("text") or "")[:60].strip() == f[:60].strip():
                if j == 0:
                    primo += 1
                entro += 1
                break
    n = len(fatti) or 1
    print(f"  {nome:<10} primo posto {primo:>2}/{n} | entro k={K} {entro:>2}/{n}", flush=True)
    return primo, entro


def main():
    print(f"verimem {verimem.__version__} | rerank={_MODO.upper()} | ordine={_ORDINE} | "
          f"{N_PER_LINGUA} fatti per lingua, k={K}", flush=True)
    it, en = campiona()
    mem = Memory(CONFIG.semantic_db)
    if _ORDINE == "en-it":
        b = misura(mem, en, "INGLESE")
        a = misura(mem, it, "ITALIANO")
    else:
        a = misura(mem, it, "ITALIANO")
        b = misura(mem, en, "INGLESE")
    print(f"RIGA rerank={_MODO} ordine={_ORDINE} it_primo={a[0]} it_k={a[1]} "
          f"en_primo={b[0]} en_k={b[1]} su={N_PER_LINGUA}", flush=True)


if __name__ == "__main__":
    main()
