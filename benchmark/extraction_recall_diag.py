"""EXTRACTION RECALL falsificazione METRO-vs-PRODOTTO: rimisura gli stessi 2
gruppi di gold con DUE metri — token-overlap (severo, quello di ieri) E
embedding-cosine (semantico). Se il recall sale molto col semantico → il buco
0.42 era il METRO, non il prodotto. Se resta basso → gap reale di estrazione.
Salva anche i gold ancora persi col match semantico (il vero residuo)."""
import json
import os

os.environ.setdefault("ENGRAM_RECONCILE_ON_WRITE", "0")

import numpy as np

from benchmark.qa_runner import LeanClaudeCLILLM
from engram import embedding
from engram.conversation_ingest import (
    ATOMIC_EXTRACT_SYSTEM,
    CONSOLIDATE_SYSTEM,
    parse_extracted_lines,
)
from engram.truth_reconciliation import _content_overlap

p = os.path.expanduser("~/.cache/halumem/HaluMem-Medium.jsonl")
u = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()][0]
llm = LeanClaudeCLILLM(timeout_s=120, model="claude-sonnet-4-6")


def extract(dialogue):
    msgs = [{"role": t.get("role", "user"), "content": t.get("content", "")}
            for t in dialogue if (t.get("content") or "").strip()]
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
    raw = llm.complete(ATOMIC_EXTRACT_SYSTEM,
                       [{"role": "user", "content": convo}]).text
    facts = parse_extracted_lines(raw)
    cons = llm.complete(CONSOLIDATE_SYSTEM,
                        [{"role": "user", "content": "\n".join(facts)}]).text
    return parse_extracted_lines(cons) or facts


def emb(texts):
    # as_passage/as_query non necessari per la sola similarità gold<->fatto;
    # encode restituisce vettori normalizzati e5.
    return [embedding.encode(t) for t in texts]


def cos(a, b):
    return float(embedding.cosine(np.asarray(a), np.asarray(b)))


OV_THR, EMB_THR = 0.5, 0.80
cov_ov = cov_emb = tot = 0
still_missed = []
for si, s in enumerate(u["sessions"][:2]):
    dialogue = s.get("dialogue") or []
    golds = [(mp.get("memory_content") or "").strip()
             for mp in (s.get("memory_points") or []) if mp.get("memory_content")]
    if not dialogue or not golds:
        continue
    facts = extract(dialogue)
    fembs = emb(facts)
    gembs = emb(golds)
    for g, ge in zip(golds, gembs):
        tot += 1
        best_ov = max((_content_overlap(g, f) for f in facts), default=0.0)
        best_em = max((cos(ge, fe) for fe in fembs), default=0.0)
        if best_ov >= OV_THR:
            cov_ov += 1
        if best_em >= EMB_THR:
            cov_emb += 1
        else:
            still_missed.append({"session": si, "gold": g,
                                 "best_overlap": round(best_ov, 2),
                                 "best_cosine": round(best_em, 3)})
    print(f"session {si}: {len(golds)} gold, {len(facts)} extracted", flush=True)

print(f"\nRECALL token-overlap(>={OV_THR}): {cov_ov}/{tot} = {round(cov_ov/tot,3)}", flush=True)
print(f"RECALL embedding-cosine(>={EMB_THR}): {cov_emb}/{tot} = {round(cov_emb/tot,3)}", flush=True)
print(f"VERDETTO: {'METRO (semantico >> overlap = il buco era la misura)' if cov_emb > cov_ov + 3 else 'GAP REALE (anche il semantico manca gold = estrazione da arricchire)'}", flush=True)
print("GOLD ANCORA PERSI col semantico (il vero residuo):", flush=True)
for m in sorted(still_missed, key=lambda x: x["best_cosine"]):
    print(f"  [cos={m['best_cosine']}] {m['gold'][:100]}", flush=True)
import pathlib

pathlib.Path("benchmark/results/extraction_diag2.json").write_text(
    json.dumps({"recall_overlap": cov_ov/tot, "recall_embedding": cov_emb/tot,
                "total": tot, "still_missed": still_missed}, indent=2,
               ensure_ascii=False), encoding="utf-8")
print("DONE", flush=True)
