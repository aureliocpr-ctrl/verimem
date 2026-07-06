"""LOCALIZZA il collo e2e Basic: retrieval o answerer? Per le domande Basic di
1-2 sessioni HaluMem, costruisci lo store coi NOSTRI fatti estratti (pipeline
reale), poi per ogni domanda misura DUE cose senza LLM di risposta:
  (A) RETRIEVAL-HIT: il fatto-gold è nel contesto top-k recuperato? (embedding
      cosine gold<->miglior-fatto-recuperato >= 0.80)
Se retrieval-hit è ALTO sulle domande, il collo è l'ANSWERER (recupera ma non
aggancia). Se è BASSO, il collo è il RETRIEVAL (i nostri fatti, in prosa, non
matchano il fraseggio della domanda). Diagnosi pura, claude-p solo per estrarre.
"""
import json
import os
import tempfile
from pathlib import Path

os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "1"
os.environ["ENGRAM_RECONCILE_AUTO_SUPERSEDE"] = "1"
os.environ["ENGRAM_RECONCILE_NLI"] = "local"
os.environ["ENGRAM_RECONCILE_MIN_OVERLAP"] = "0.35"

import numpy as np

from benchmark.qa_runner import LeanClaudeCLILLM
from engram import embedding
from engram.agent import wire_reconcile_judge
from engram.conversation_ingest import ingest_conversation
from engram.semantic import SemanticMemory

p = os.path.expanduser("~/.cache/halumem/HaluMem-Medium.jsonl")
u = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()][0]
llm = LeanClaudeCLILLM(timeout_s=120, model="claude-sonnet-4-6")


def cos(a, b):
    return float(embedding.cosine(np.asarray(a), np.asarray(b)))


N_SESS = 10
sm = SemanticMemory(db_path=Path(tempfile.mkdtemp(prefix="loc_")) / "d.db")
wire_reconcile_judge(sm, None)
# store GOLD parallelo (i memory_points), per il confronto retrieval nostri-vs-gold
smg = SemanticMemory(db_path=Path(tempfile.mkdtemp(prefix="locg_")) / "g.db")
from engram.semantic import Fact

for si, s in enumerate(u["sessions"][:N_SESS]):
    msgs = [{"role": t.get("role", "user"), "content": t.get("content", "")}
            for t in (s.get("dialogue") or []) if (t.get("content") or "").strip()]
    if msgs:
        ingest_conversation(sm, msgs, llm=llm, conversation_id=f"s{si}",
                            topic=f"e/{si}", consolidate=True)
    for mp in (s.get("memory_points") or []):
        c = (mp.get("memory_content") or "").strip()
        if c:
            smg.store(Fact(proposition=c, topic=f"g/{si}"), embed="sync")
    print(f"ingest sess {si}", flush=True)
print("ingest fatto (nostri fatti estratti + store gold parallelo)", flush=True)


def retrieval_hit(store, question, gold_emb, k=12):
    hits = store.recall(question, k=k)
    return max((cos(gold_emb, embedding.encode(f.proposition)) for f, *_ in hits),
               default=0.0)


K = 12
hit_ours = hit_gold = tot = 0
misses = []
for si, s in enumerate(u["sessions"][:N_SESS]):
    for q in (s.get("questions") or []):
        if str(q.get("question_type")) != "Basic Fact Recall":
            continue
        gold = str(q.get("answer", "")).strip()
        if not gold or gold.lower().startswith(("unknown", "this info", "not ",
                                                "no ", "n/a")):
            continue
        tot += 1
        ge = embedding.encode(gold)
        bo = retrieval_hit(sm, q.get("question", ""), ge, K)
        bg = retrieval_hit(smg, q.get("question", ""), ge, K)
        if bo >= 0.80:
            hit_ours += 1
        if bg >= 0.80:
            hit_gold += 1
        if bo < 0.80:
            misses.append({"q": q.get("question", "")[:75], "gold": gold[:50],
                           "ours_cos": round(bo, 3), "gold_cos": round(bg, 3)})

ro = hit_ours / tot if tot else 0.0
rg = hit_gold / tot if tot else 0.0
print(f"\nRETRIEVAL-HIT Basic (n={tot}, cos>=0.80, top-{K}):", flush=True)
print(f"  NOSTRI fatti estratti: {hit_ours}/{tot} = {round(ro,3)}", flush=True)
print(f"  fatti GOLD (read-path): {hit_gold}/{tot} = {round(rg,3)}", flush=True)
if rg - ro >= 0.15:
    verdict = "FRASEGGIO estrazione (gold recuperato, i nostri fatti no) — leva: allineare/multi-form l'estrazione"
elif ro >= 0.7:
    verdict = "ANSWERER (retrieval ok anche coi nostri fatti, il collo è la risposta)"
else:
    verdict = "RETRIEVAL generale (nemmeno il gold si recupera bene per la domanda)"
print(f"VERDETTO: {verdict}", flush=True)
for m in sorted(misses, key=lambda x: x["ours_cos"])[:12]:
    print(f"  MISS ours={m['ours_cos']} gold={m['gold_cos']} | {m['q']} -> {m['gold']}",
          flush=True)
Path("benchmark/results/localize_bottleneck.json").write_text(
    json.dumps({"retrieval_hit_ours": ro, "retrieval_hit_gold": rg, "n": tot,
                "verdict": verdict, "misses": misses}, indent=2,
               ensure_ascii=False), encoding="utf-8")
print("DONE", flush=True)
