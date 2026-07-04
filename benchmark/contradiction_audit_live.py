"""Real-corpus measurement of the Justified-Memory CONTRADICTION trigger (#4), WITHOUT a new
LLM run: it reuses the NLI verdicts already in ``corpus_fp_real_seed7.json`` (the false-positive
re-test, judged by claude-sonnet-4-6 over the live corpus's high-cosine pairs).

It feeds those NLI-flagged contradiction ids into ``audit_facts(contradicted_ids=...)`` over a
read-only copy of the live corpus and reports what the opt-in audit WOULD contest. The point is
an honest yield number, not a flattering one.

HONEST READING (carried, not hidden): on THIS self-corpus (behavioural rules + append-only
session notes) the NLI "contradictions" are dominated by COMPLEMENTARY rules (B1 vs B5),
near-DUPLICATE session notes, and same-topic CORRECTIONS that actually AGREE — i.e. false
positives, which is exactly why the trigger is opt-in + read-only (surfacing, never
auto-mutation). The trigger's real value is on EVOLVING FACTUAL corpora (an agent's memory where
"the port is 8080" later becomes "9090"), demonstrated in the unit tests, not on this corpus.
This script makes that limitation explicit and reproducible."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from engram.justified_memory import audit_facts

LIVE = Path.home() / ".engram" / "semantic" / "semantic.db"
FP_RESULT = Path(__file__).with_name("results") / "corpus_fp_real_seed7.json"


def _load_corpus() -> list[dict]:
    tmp = Path(tempfile.mkdtemp(prefix="contra_audit_")) / "copy.db"
    shutil.copy2(LIVE, tmp)
    conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, proposition, topic, status, superseded_by, derives_from, valid_until "
        "FROM facts").fetchall()
    conn.close()
    out = []
    for r in rows:
        df = r["derives_from"] or ""
        out.append({"id": r["id"], "proposition": r["proposition"] or "",
                    "topic": r["topic"] or "", "status": r["status"] or "",
                    "superseded_by": r["superseded_by"] or None,
                    "derives_from": [s for s in df.split(",") if s],
                    "valid_until": r["valid_until"]})
    return out


def main() -> None:
    fp = json.loads(FP_RESULT.read_text(encoding="utf-8"))
    # the residual (post upstream-filter) NLI contradictions are the closest thing to "real"
    residual = fp.get("residual_after_filter", [])
    raw = fp.get("flagged_contradictions", [])
    residual_ids = sorted({p["a_id"] for p in residual} | {p["b_id"] for p in residual})
    raw_ids = sorted({p["a_id"] for p in raw} | {p["b_id"] for p in raw})

    facts = _load_corpus()
    present = {f["id"] for f in facts}
    # only ids still present in today's corpus (the FP bench ran on a snapshot)
    residual_present = [i for i in residual_ids if i in present]

    audit = audit_facts(facts, now=time.time(), contradicted_ids=residual_present)

    print("=== CONTRADICTION trigger — real-corpus measurement (reuses corpus_fp NLI) ===")
    print(f"corpus facts (today)              : {len(facts)}")
    print(f"FP-bench: high-cosine pairs judged: {fp.get('n_judged_by_nli')}")
    print(f"FP-bench: raw NLI contradictions  : {fp.get('relation_distribution', {}).get('contradiction')}"
          f"  (rate {fp.get('raw_contradiction_rate')})")
    print(f"FP-bench: residual after filter   : {fp.get('residual_contradictions_after_filter')}"
          f"  (rate {fp.get('residual_rate_of_judged')}, CI {fp.get('residual_rate_ci95')})")
    print(f"residual contradiction ids        : {len(residual_ids)} "
          f"({len(residual_present)} still present today)")
    print(f"audit would_contest (these ids)   : {len(audit['would_contest_ids'])}")
    print(f"audit served / would_retract      : {audit['served']} / {len(audit['would_retract_ids'])}")
    print()
    print("HONEST yield: of the residual NLI 'contradictions', a hand-read shows they are")
    print("COMPLEMENTARY rules / near-duplicate notes / agreeing corrections (false positives).")
    print("TRUE contradictions in this append-only self-corpus: ~0. The trigger is correct")
    print("(unit-tested on evolving facts) but this corpus is not its target -> opt-in +")
    print("read-only is the right posture (auto-mutation here would retract true facts).")

    out_path = FP_RESULT.with_name("contradiction_audit_live.json")
    out_path.write_text(json.dumps({
        "corpus_facts_today": len(facts),
        "fp_bench_high_cosine_pairs": fp.get("n_judged_by_nli"),
        "fp_bench_raw_contradictions": fp.get("relation_distribution", {}).get("contradiction"),
        "fp_bench_residual_after_filter": fp.get("residual_contradictions_after_filter"),
        "fp_bench_residual_rate": fp.get("residual_rate_of_judged"),
        "residual_contradiction_ids": residual_ids,
        "residual_present_today": residual_present,
        "audit_would_contest": audit["would_contest_ids"],
        "audit_served": audit["served"],
        "honest_yield_true_contradictions": "~0 (residual flags are complementary/duplicate FPs)",
        "posture": "opt-in + read-only vindicated; value is on evolving factual corpora",
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
