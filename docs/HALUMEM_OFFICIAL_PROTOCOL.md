# HaluMem official protocol (extracted from MemTensor/HaluMem eval/ — for a leaderboard-comparable harness)

Source: github.com/MemTensor/HaluMem `eval/evaluation.py` + `eval/eval_tools.py` (read 2026-06-20).
arXiv 2511.03506. The leaderboard is **self-reported by MemTensor** (who also make MemOS, the winner)
→ conflict of interest + low ceiling (best QA ~67%). This is the spec to post an HONEST number.

## Inputs (HaluMem-Medium.jsonl / -Long.jsonl, cached ~/.cache/halumem/)
Per user: `sessions[].memory_points[]` each = {memory_content, memory_type (Persona/Event/Relationship),
memory_source ∈ {system, primary, secondary, **interference**}}; plus `questions[]` = {question, answer,
evidence, question_type}. `interference` = injected plausible distortions (the corrupted-memory the
write-gate must reject — Engram's home turf).

## The three metrics — ALL LLM-judged, semantic (no embedding threshold, no exact-match)
1. **Memory Extraction F1** = harmonic mean of:
   - **Integrity (Recall):** for each GOLD memory point, an LLM judge searches the system's EXTRACTED
     memories and scores 0/1/2 (2=fully covered/implied, 1=partial, 0=missing/wrong). "Semantic matching
     is acceptable; exact wording not required." Recall = mean(score)/2.
   - **Accuracy (Precision):** for each EXTRACTED memory, judge scores 0/1/2 whether it is supported by
     dialogue+gold ("any info not in or inferable from these two sources is unsupported"). Precision = mean/2.
   - `compute_f1(p,r) = 2*p*r/(p+r)`.
2. **Memory Updating** — when a fact changes, judge categorizes the system's stored result:
   Correct | Hallucinated-Update | Omitted-Update | Other. "Key fields (date/time/values/proper nouns)
   must match EXACTLY." Rates = count/total → C / H / O.
3. **QA (answer hallucination)** — judge compares System Response vs Reference Answer + Key Memory Points,
   using ONLY those: **Correct** (semantically equivalent, no contradiction) | **Hallucination**
   (contradicts ref or adds unsupported facts) | **Omission** (incomplete/missing). Rates → C / H / O.
   Judge model unspecified in their code → we use claude -p (method-comparable, NOT judge-identical:
   the same declared asterisk as docs/BENCHMARKS.md).

## Build plan for Engram (the #1 P0 — `benchmark/halumem_official_*.py`)
- **QA-hallucination (most moat-relevant, do first):** ingest a user's dialogue through Engram's FULL
  write pipeline (extract → anti-confab gate → store — the gate should REJECT `interference`, the moat),
  then for each question retrieve→answer (strict-answer + dates ON) → LLM-judge C/H/O. **The hypothesis:
  Engram's low Hallucination-rate (it abstains/omits rather than fabricate) is the differentiator vs
  MemOS' 67% correct.** Reuse `benchmark/halumem_interference_stage.py` loaders + `benchmark/qa_eval.py`
  answer/judge + the C/H/O classifier above.
- **Extraction F1:** run Engram extraction (narration_llm/openie) per dialogue → Integrity+Accuracy
  judges (0/1/2 prompts above) → F1. Heavier; second.
- Score with Wilson CIs; SERIAL claude -p (concurrent hangs); start with a small N (3–5 users) to
  validate the harness, then scale when the LLM window is stable (sustained runs hit the server throttle —
  the n=60 LongMemEval run had ~25% claude -p errors, so size + retry accordingly).

## Honesty guardrails
- Do NOT claim a leaderboard rank: judge ≠ their (unknown) judge; report "method-comparable".
- Report the FULL C/H/O triple, not just Correct — Engram's story is **low H** (anti-confab), possibly
  higher O (abstention), which is the CORRECT trade for a memory system.
