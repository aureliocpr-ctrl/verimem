"""T2.2, passo zero — IL RAMO BM25 SI ATTIVA MAI? Prima di ablare una fusione, verificare che esista.

    python scripts/banco_ramo_bm25_si_attiva.py

La ricerca esterna propone un'ablation «solo-BM25 / solo-dense / RRF / somma normalizzata»
con la predizione «sulle query EN il solo-dense batte l'ibrido di >=15 punti di recall@10,
perche' oggi il ramo BM25 annega il segnale semantico».
⚠️ LEGGENDO IL CODICE quell'architettura non sembra essere questa:
  semantic.py:4055  q_emb = _encode_prepared_within_budget(...)
  semantic.py:4062  if q_emb is None:            <- SOLO QUI parte il ramo keyword
  semantic.py:4109      from .bm25_rank import bm25_fact_ids   <- BM25 ri-ordina i keyword
Il commento accanto dice che il BM25 «approssima la rilevanza che il warm path ottiene dal
cosine»: cioe' e' un SURROGATO del denso quando l'encode non c'e', non un ramo fuso in
parallelo. Se e' cosi', «ibrido» e «solo-dense» non sono due configurazioni: in condizioni
normali il prodotto E' GIA' solo-dense, e T2.2 misurerebbe una differenza che non esiste.

⚠️ MA LA LETTURA NON BASTA (A2): questo banco lo MISURA, con il contatore che il prodotto
tiene da solo — `SemanticMemory._recall_degraded_count`, incrementato SOLO nel ramo keyword
(semantic.py:4121). Se dopo N query vale 0, il ramo BM25 non si e' mai attivato.

PREDIZIONE SCRITTA PRIMA (02/09 12:48):
  store piccolo, 24 query: degradi 0  (l'encode di una query e' veloce e sta nel budget)
  store vivo,    24 query: degradi 0 dopo la prima; al piu' 1 sulla PRIMA query a freddo
CONDIZIONE D'USCITA:
  degradi == 0            -> il ramo BM25 NON partecipa al percorso normale: T2.2 come
                             formulata NON e' eseguibile, e va detto prima che qualcuno
                             ci spenda un giorno
  degradi > 0 e stabili   -> il ramo esiste davvero nel percorso normale: T2.2 ha senso, e
                             questo banco ne da' la frequenza
"""
import os
import sys
import tempfile
from pathlib import Path

for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

QUERY = [
    "Quando viene svuotata la cache?", "Cosa fa il server di posta?",
    "Quale penale prevede il contratto?", "Quanto dura il corso?",
    "Quale carico sopporta il ponte?", "Quante persone accoglie la sala?",
    "When is the cache emptied?", "What does the mail server do?",
    "What penalty does the contract provide?", "How long does the course last?",
    "What load does the bridge support?", "How many people does the hall seat?",
]


def conta(mem, nome, queries):
    sm = mem.semantic
    prima = getattr(sm, "_recall_degraded_count", 0)
    for q in queries:
        mem.search(q, k=10)
    dopo = getattr(sm, "_recall_degraded_count", 0)
    print(f"  {nome:<34} query {len(queries):>3} | degradi {dopo - prima} "
          f"(contatore {prima} -> {dopo})", flush=True)
    return dopo - prima


def main():
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__}", flush=True)
    tot = QUERY * 2  # 24 query

    d = tempfile.mkdtemp()
    piccolo = Memory(Path(d) / "s.db")
    for i, q in enumerate(QUERY):
        piccolo.add(f"Fatto numero {i}: {q.rstrip('?')} e la risposta e {40 + i}.",
                    topic="t2/ramo")
    a = conta(piccolo, "store PICCOLO (12 fatti)", tot)

    vivo = Memory(CONFIG.semantic_db)
    b = conta(vivo, "store VIVO (sola lettura)", tot)

    print("\n" + "=" * 74, flush=True)
    print(f"  degradi su store piccolo: {a}/{len(tot)}", flush=True)
    print(f"  degradi su store vivo:    {b}/{len(tot)}", flush=True)
    if a == 0 and b == 0:
        print("  => il ramo BM25 NON si e' attivato nemmeno una volta: nel percorso normale\n"
              "     il prodotto e' gia' solo-dense, e l'ablation «ibrido vs solo-dense»\n"
              "     NON ha due configurazioni da confrontare.", flush=True)
    else:
        print("  => il ramo si attiva: T2.2 ha senso, e questa e' la sua frequenza.",
              flush=True)
    print("=" * 74, flush=True)
    print("PREDIZIONE (scritta prima): 0 sul piccolo, 0-1 sul vivo.", flush=True)


if __name__ == "__main__":
    main()
