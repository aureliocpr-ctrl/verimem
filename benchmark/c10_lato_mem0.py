r"""C10, LATO CONCORRENTE — mem0 sulla STESSA popolazione e con la STESSA query.

Gira in `.venv-mem0bench`, che NON ha `verimem` installato: per questo e' un file
separato dal lato nostro. Nessuna chiave, nessuna rete verso terzi — embedder e5
locale (lo stesso modello che usiamo noi) e `infer=False`, quindi l'LLM di mem0
non viene mai chiamato.

    /c/Users/aurel/Code/HippoAgent/.venv-mem0bench/Scripts/python.exe \
        benchmark/c10_lato_mem0.py --n 60

⚠️ IL NODO METODOLOGICO, ed e' la ragione per cui questo file esiste.

Il primo protocollo che avevo scritto misurava la nostra AMMISSIONE (quanti
falsi passano il gate) e l'avrebbe confrontata col RETRIEVAL di mem0 (cosa torna
a una query). **Sono due livelli diversi**, e mem0 non ha affatto un gate: con
`infer=False` scrive quello che riceve. Confrontare cosi' avrebbe dato un
vantaggio automatico a noi — ed e' esattamente il difetto che passiamo la
giornata a smontare negli altri: *il livello a cui misuri decide il verdetto*.

⇒ **Protocollo simmetrico, unico livello: la QUERY.**

      entrambi ricevono   120 claim (60 veri + 60 falsi, HaluEval QA heldout)
      entrambi ricevono   le stesse 60 domande
      si conta            nel primo risultato c'e' il VERO o il FALSO?

  Cosi' la grandezza e' la stessa per tutti e due: **di cio' che il sistema
  RESTITUISCE a chi lo interroga, che frazione e' falsa.** E' la cosa che
  l'utente subisce, non un dettaglio della nostra architettura.

FAIR PLAY, dichiarato. Interrogo `vector_store.search` direttamente invece di
`Memory.search`: il runner di `competitor_probe_mem0.py` documenta un bug di
ranking in `Memory.search`, e passare da li' **handicapperebbe il concorrente**.
Il numero deve reggere anche se lo legge chi fa mem0.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
DATI = RADICE / "benchmark" / "data" / "external" / "halueval_qa_heldout.jsonl"


def build_memory(workdir: str, collection: str):
    """Copiata verbatim da `competitor_probe_mem0.py` — stesso identico
    apparecchio, cosi' il confronto non dipende da come l'ho montato io."""
    from mem0 import Memory
    config = {
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "intfloat/multilingual-e5-base"}},
        "vector_store": {"provider": "chroma",
                         "config": {"collection_name": collection, "path": workdir}},
    }
    return Memory.from_config(config)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--out", default="benchmark/results/c10_lato_mem0.json")
    a = ap.parse_args()

    with open(DATI, encoding="utf-8") as f:
        item = [json.loads(r) for r in f if r.strip()][:a.n]

    mem = build_memory(tempfile.mkdtemp(prefix="ws7_c10_mem0_"), "c10")

    #: SCRITTURA — i 120 claim, senza far girare l'LLM (infer=False).
    #: Tengo la mappa claim -> etichetta per poter leggere il retrieval dopo.
    etichetta_di: dict[str, str] = {}
    for i, it in enumerate(item):
        for et, claim in (("vero", it["right_answer"]),
                          ("falso", it["hallucinated_answer"])):
            etichetta_di[claim.strip()] = et
            mem.add(claim, user_id="c10", infer=False)
        if (i + 1) % 10 == 0:
            print(f"    scritti …{2 * (i + 1)}/{2 * len(item)} claim", flush=True)

    #: QUERY — la stessa domanda che porremo a noi, e si guarda il PRIMO risultato.
    primo_falso = primo_vero = primo_altro = 0
    for i, it in enumerate(item):
        #: firma e prefisso copiati da `competitor_probe_mem0.py:52-55`: e5
        #: vuole `query: ` davanti alla domanda e `passage: ` davanti al testo,
        #: e chiamarlo senza il prefisso giusto handicapperebbe il concorrente
        #: su una convenzione del MODELLO, non su una sua debolezza.
        qv = mem.embedding_model.embed(f"query: {it['question']}", "search")
        hit = mem.vector_store.search(query=f"query: {it['question']}",
                                      vectors=qv, top_k=1,
                                      filters={"user_id": "c10"})
        testo = ""
        if hit:
            h = hit[0]
            p = getattr(h, "payload", None) or (h.get("payload") if isinstance(h, dict) else {}) or {}
            testo = (p.get("data") or p.get("memory") or "").strip()
        et = etichetta_di.get(testo)
        if et == "falso":
            primo_falso += 1
        elif et == "vero":
            primo_vero += 1
        else:
            primo_altro += 1

    tot = len(item)
    print(f"\n  === mem0 2.0.4 su HaluEval QA heldout — {tot} domande ===")
    print(f"  primo risultato FALSO:  {primo_falso:4}/{tot} = {100 * primo_falso / max(1, tot):5.1f}%"
          f"   <- la sua «figura di merda»")
    print(f"  primo risultato VERO:   {primo_vero:4}/{tot} = {100 * primo_vero / max(1, tot):5.1f}%")
    print(f"  non riconosciuto:       {primo_altro:4}/{tot} = {100 * primo_altro / max(1, tot):5.1f}%"
          f"   (testo che non combacia con nessuno dei due)")

    corpo = {"sistema": "mem0 2.0.4 (e5 locale, infer=False, zero-API)",
             "popolazione": "halueval_qa_heldout.jsonl (RUCAIBox, MIT)",
             "domande": tot, "claim_scritti": 2 * tot,
             "primo_falso": primo_falso, "primo_vero": primo_vero,
             "primo_non_riconosciuto": primo_altro,
             "query": "vector_store.search diretto (Memory.search ha un bug di ranking documentato)"}
    out = RADICE / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpo, indent=2), encoding="utf-8")
    print(f"\n  scritto {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
