"""M2 residuo — IL SALTO LESSICALE sul corpus reale, e l'ANCORAGGIO come confondente.

    python scripts/banco_sinonimo_e_ancoraggio.py it-en
    python scripts/banco_sinonimo_e_ancoraggio.py en-it

⚠️ RERANK SPENTO in entrambi i bracci (`ENGRAM_RECALL_RERANK=0`): e' il regime che il
02/09 alle 19:31 ha dato ripetizioni IDENTICHE su due ordini. Ogni esecuzione e' un
processo nuovo (il breaker e' per-processo).

DUE MISURE IN UNA SOLA ESECUZIONE.

(1) SALTO LESSICALE. Per ogni fatto la query e' la stessa del banco stabile — i 6 token
piu' lunghi — e poi la stessa query con UN token sostituito dal suo SINONIMO, quando il
token e' in un dizionario scritto a mano. ⚠️ Il dizionario copre PAROLE COMUNI: i fatti
reali sono pieni di identificatori (`hippo_facts_recall`, `2026-05-11`, `pqc-audit-italia`)
che un sinonimo non ce l'hanno. I fatti senza alcun token sostituibile sono ESCLUSI e il
loro numero e' dichiarato: misurare «sinonimo» su una query che non e' cambiata sarebbe
misurare due volte lo stesso braccio.

(2) ANCORAGGIO — il confondente visto guardando il materiale prima di scrivere il banco:
nelle query italiane il 10% dei token distinti ha cifre/underscore/MAIUSCOLE, nelle inglesi
il 29%. Se le ancore uniche (date, sigle, nomi di repo) portano il recall, allora il divario
IT/EN misurato il 02/09 (60-80% contro 93-100%) NON e' la lingua ma quanto le query sono
ancorate. Qui si misura il recall separando le query CON e SENZA ancora, dentro ogni lingua.

PREDIZIONE SCRITTA PRIMA (02/09 19:56):
  (1) il sinonimo fa scendere recall@10 sotto il 60% in entrambe le lingue
      (riferimento con la parola del fatto: IT 13/15 = 86,7%, EN 15/15 = 100%)
  (2) dentro OGNI lingua, le query CON ancora superano quelle SENZA di >= 20 punti
CONDIZIONE D'USCITA:
  (1) sinonimo >= 80% -> il salto lessicale NON esiste sul corpus reale e M2 si chiude
      sinonimo <  60% -> il salto esiste e va quantificato
  (2) divario con/senza ancora >= 20 punti -> l'ancoraggio e' un confondente del divario
      IT/EN e va dichiarato accanto a ogni numero per lingua
"""
import os
import re
import sqlite3
import sys
from pathlib import Path

_ORDINE = (sys.argv[1] if len(sys.argv) > 1 else "it-en").lower()
for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
os.environ["ENGRAM_RECALL_RERANK"] = "0"          # regime ripetibile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

K = 10
N_PER_LINGUA = 40

_IT_STOP = {"il", "lo", "la", "i", "gli", "le", "di", "che", "non", "per", "con", "sono",
            "della", "dei", "alla", "una", "un", "nel", "sulla", "come"}
_EN_STOP = {"the", "of", "and", "is", "are", "to", "with", "that", "for", "not", "this",
            "from", "was", "were", "has", "have", "in", "on", "by", "as"}

#: Sinonimi di PAROLE COMUNI, scritti a mano guardando i token che ricorrono davvero nelle
#: query derivate. Non coprono gli identificatori: quelli non hanno sinonimo.
SIN = {
    "progetto": "iniziativa", "numero": "cifra", "documentazione": "manuale",
    "pubblico": "aperto", "semplificato": "snellito", "voglio": "desidero",
    "servirebbe": "occorrerebbe", "memoria": "archivio", "fatto": "dato",
    "misura": "rilevazione", "banco": "prova", "errore": "difetto", "cura": "rimedio",
    "prodotto": "applicativo", "riga": "linea", "campo": "attributo",
    "sessione": "seduta", "comando": "istruzione", "modello": "schema",
    "risposta": "replica", "domanda": "quesito", "conteggio": "computo",
    "episodes": "sessions", "succeeded": "worked", "extraction": "retrieval",
    "commit": "revision", "dependencies": "requirements", "intermediate": "middle",
    "sequences": "series", "memory": "storage", "fact": "datum", "measure": "reading",
    "bench": "testbed", "error": "defect", "product": "application", "row": "line",
    "field": "attribute", "session": "sitting", "command": "instruction",
    "model": "schema", "answer": "reply", "question": "query", "count": "tally",
}


def lingua(testo):
    p = set(re.findall(r"[a-zà-ù']+", testo.lower()))
    a, b = len(p & _IT_STOP), len(p & _EN_STOP)
    return "it" if a > b else ("en" if b > a else "?")


def token6(testo):
    tok = re.findall(r"[\w\-.]{3,}", testo)
    if not tok:
        return []
    return sorted(sorted(set(tok), key=tok.index), key=len, reverse=True)[:6]


def ha_ancora(tokens):
    """Una query e' ANCORATA se almeno un token porta cifre, underscore o MAIUSCOLE."""
    return any(re.search(r"[_0-9]|[A-Z]{2,}", t) for t in tokens)


def con_sinonimo(tokens):
    """Sostituisce il PRIMO token che ha un sinonimo. None se nessuno ne ha."""
    fuori, cambiato = [], False
    for t in tokens:
        s = SIN.get(t.lower())
        if s and not cambiato:
            fuori.append(s)
            cambiato = True
        else:
            fuori.append(t)
    return (" ".join(fuori) if cambiato else None)


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


def trovato(mem, query, atteso):
    for x in mem.search(query, k=K):
        if (x.get("text") or "")[:60].strip() == atteso[:60].strip():
            return True
    return False


def misura(mem, fatti, nome):
    base_ok = sin_ok = sin_n = 0
    anc_ok = anc_n = noanc_ok = noanc_n = 0
    for f in fatti:
        tk = token6(f)
        if not tk:
            continue
        ok = trovato(mem, " ".join(tk), f)
        base_ok += ok
        if ha_ancora(tk):
            anc_n += 1
            anc_ok += ok
        else:
            noanc_n += 1
            noanc_ok += ok
        qs = con_sinonimo(tk)
        if qs is not None:
            sin_n += 1
            sin_ok += trovato(mem, qs, f)
    n = len(fatti)
    print(f"  {nome}", flush=True)
    print(f"    parola del fatto   recall@{K} {base_ok:>2}/{n} ({base_ok / n * 100:5.1f}%)",
          flush=True)
    if sin_n:
        print(f"    con SINONIMO       recall@{K} {sin_ok:>2}/{sin_n} "
              f"({sin_ok / sin_n * 100:5.1f}%)   [{sin_n}/{n} fatti avevano un token "
              f"sostituibile]", flush=True)
    else:
        print("    con SINONIMO       nessun fatto aveva un token sostituibile", flush=True)
    if anc_n:
        print(f"    query CON ancora   recall@{K} {anc_ok:>2}/{anc_n} "
              f"({anc_ok / anc_n * 100:5.1f}%)", flush=True)
    if noanc_n:
        print(f"    query SENZA ancora recall@{K} {noanc_ok:>2}/{noanc_n} "
              f"({noanc_ok / noanc_n * 100:5.1f}%)", flush=True)
    return {"base": (base_ok, n), "sin": (sin_ok, sin_n), "anc": (anc_ok, anc_n),
            "noanc": (noanc_ok, noanc_n)}


def main():
    print(f"verimem {verimem.__version__} | rerank=OFF | ordine={_ORDINE} | "
          f"{N_PER_LINGUA} fatti per lingua | k={K}", flush=True)
    it, en = campiona()
    mem = Memory(CONFIG.semantic_db)
    if _ORDINE == "en-it":
        b = misura(mem, en, "INGLESE")
        a = misura(mem, it, "ITALIANO")
    else:
        a = misura(mem, it, "ITALIANO")
        b = misura(mem, en, "INGLESE")
    print(f"RIGA ordine={_ORDINE} it_base={a['base']} it_sin={a['sin']} it_anc={a['anc']} "
          f"it_noanc={a['noanc']} en_base={b['base']} en_sin={b['sin']} en_anc={b['anc']} "
          f"en_noanc={b['noanc']}", flush=True)
    print("PREDIZIONE (scritta prima): sinonimo sotto il 60% in entrambe · "
          "con-ancora batte senza-ancora di >=20 punti dentro ogni lingua.", flush=True)


if __name__ == "__main__":
    main()
