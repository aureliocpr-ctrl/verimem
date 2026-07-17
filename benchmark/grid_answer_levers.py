"""GRIGLIA DI LEVE sull'answerer e2e Basic (concatenamento scientifico: screening
di TUTTE le leve, poi combinazione delle migliori). Store costruito UNA volta coi
nostri fatti estratti; poi ogni cella = (answer_mode × k contesto) sulle stesse
Basic, stesso giudice. Leve:
  answer_mode: strict | declared | verify | declared+verify (combinazione prompt)
  k (distrattori): 6 (poco contesto) | 12 (molto)
= 4×2 = 8 celle. Riporta accuracy per cella + la classifica → la ricetta migliore.
"""
import json
import os
import tempfile
from itertools import product
from pathlib import Path

os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "1"
os.environ["ENGRAM_RECONCILE_AUTO_SUPERSEDE"] = "1"
os.environ["ENGRAM_RECONCILE_NLI"] = "local"
os.environ["ENGRAM_RECONCILE_MIN_OVERLAP"] = "0.35"

from benchmark.qa_eval import (
    _ANSWER_SYSTEM_DECLARED,
    _ANSWER_SYSTEM_VERIFY,
    _JUDGE_SYSTEM_FAIR,
)
from benchmark.qa_runner import LeanClaudeCLILLM, _recall_context
from verimem.agent import wire_reconcile_judge
from verimem.conversation_ingest import ingest_conversation
from verimem.semantic import SemanticMemory

_STRICT = ("Answer from the CONTEXT only. Answer ONLY if EXPLICITLY present; do "
           "not infer or guess. When in doubt reply exactly: NO ANSWER. One "
           "short sentence.")
# combinazione: premise-check (verify) + inferenza dichiarata (declared)
_DECL_VERIFY = (
    "Answer from the CONTEXT only. First, if the question contains a claim, "
    "check it against the context; if it contradicts, answer 'No' + the correct "
    "fact. If the answer is stated, give it directly. If NOT stated but it "
    "clearly FOLLOWS from the context, infer it and DECLARE 'Inferred from: A + "
    "B' (single-step only). If the context neither states nor supports it, reply "
    "exactly: NO ANSWER. Never use outside knowledge; at most two short sentences."
)

MODES = {"strict": _STRICT, "declared": _ANSWER_SYSTEM_DECLARED,
         "verify": _ANSWER_SYSTEM_VERIFY, "declared_verify": _DECL_VERIFY}
KS = [6, 12]

p = os.path.expanduser("~/.cache/halumem/HaluMem-Medium.jsonl")
u = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()][0]
llm = LeanClaudeCLILLM(timeout_s=120, model="claude-sonnet-4-6")

N_SESS = 20
sm = SemanticMemory(db_path=Path(tempfile.mkdtemp(prefix="grid_")) / "d.db")
wire_reconcile_judge(sm, None)
for si, s in enumerate(u["sessions"][:N_SESS]):
    msgs = [{"role": t.get("role", "user"), "content": t.get("content", "")}
            for t in (s.get("dialogue") or []) if (t.get("content") or "").strip()]
    if msgs:
        ingest_conversation(sm, msgs, llm=llm, conversation_id=f"s{si}",
                            topic=f"e/{si}", consolidate=True)
print(f"ingest fatto ({N_SESS} sess)", flush=True)

# raccogli le domande Basic + il contesto per ogni k (recall UNA volta per k)
questions = []
for si, s in enumerate(u["sessions"][:N_SESS]):
    for q in (s.get("questions") or []):
        if str(q.get("question_type")) != "Basic Fact Recall":
            continue
        gold = str(q.get("answer", "")).strip()
        if not gold or gold.lower().startswith(("unknown", "this info", "not ",
                                                "no ", "n/a")):
            continue
        qq = q.get("question", "")
        ctxs = {k: "\n".join(_recall_context(sm, qq, k)) for k in KS}
        questions.append({"q": qq, "gold": gold, "ctxs": ctxs})
print(f"{len(questions)} Basic non-trappola", flush=True)


def answer(system, question, ctx):
    user = f"CONTEXT:\n{ctx}\n\nQUESTION: {question}\nANSWER:"
    return llm.complete(system, [{"role": "user", "content": user}]).text.strip()


def judge(question, gold, pred):
    if not pred or pred.upper().startswith("NO ANSWER"):
        return False
    user = f"QUESTION: {question}\nGOLD: {gold}\nPREDICTED: {pred}"
    r = llm.complete(_JUDGE_SYSTEM_FAIR, [{"role": "user", "content": user}]).text
    return "CORRECT" in r.upper() and "INCORRECT" not in r.upper()


cells = {}
for mode, k in product(MODES, KS):
    correct = 0
    for item in questions:
        a = answer(MODES[mode], item["q"], item["ctxs"][k])
        correct += judge(item["q"], item["gold"], a)
    acc = correct / len(questions) if questions else 0.0
    cells[f"{mode}@k{k}"] = round(acc, 3)
    print(f"  CELL {mode}@k{k}: {correct}/{len(questions)} = {round(acc,3)}", flush=True)

ranking = sorted(cells.items(), key=lambda x: -x[1])
print("\n=== CLASSIFICA LEVE (Basic e2e) ===", flush=True)
for name, acc in ranking:
    print(f"  {name}: {acc}", flush=True)
print(f"MIGLIORE: {ranking[0][0]} = {ranking[0][1]}", flush=True)
Path("benchmark/results/grid_answer_levers.json").write_text(
    json.dumps({"n": len(questions), "cells": cells, "best": ranking[0][0],
                "best_acc": ranking[0][1]}, indent=2, ensure_ascii=False),
    encoding="utf-8")
print("DONE", flush=True)
