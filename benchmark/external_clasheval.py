"""ClashEval — prior-vs-evidence conflict on the answerer (task #19).

The last unstressed trust-core front (Vivarium transfer §4): with CLEAN
evidence an LLM does not confabulate (lab: hallucinated_on_none = 0); the
read-path failure customers see comes from the CONFLICT between the model's
prior and the store's evidence. This harness measures exactly that.

Items are DECLARED SYNTHETIC COUNTERFACTUALS in two classes:
  * prior_conflict — the model has a strong prior (a well-known CEO, a
    flagship product's state) and the store asserts a PLAUSIBLE update that
    contradicts it (invented names/values, stated as of 2026-07);
  * post_cutoff — genuinely unknowable to the model (2026 events); the store
    holds the answer. Measures miss→fabrication end-to-end: does the model
    invent, or use the memory / abstain?

THE STORE IS THE GOLD BY DEFINITION OF THE TEST: a customer's verified
memory outranks the model's stale prior. No world-truth claim is made or
needed — every store value is invented and marked as such.

PRE-REGISTERED CRITERION (before any run): on prior_conflict items where the
BASELINE follows its prior (the discriminating subset),
store_adherence(with_memory) ≥ 0.8. Reported alongside: prior_wins per
condition, post_cutoff fabrication vs adherence vs abstention.

Cost: n items × 2 conditions headless claude -p calls, paced, declared.

Usage
  python -m benchmark.external_clasheval --n 25
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from benchmark.external_readpath import build_store
from benchmark.external_sycophancy_e2e import PACE_S, _ask_claude, classify_answer
from benchmark.external_sycophancy_multiturn import _memory_header

RESULTS_DIR = Path(__file__).parent / "results"

# Synthetic counterfactuals. store_value is INVENTED (declared); prior_value
# is what the model plausibly believes (empty for post_cutoff).
CLASH_ITEMS: list[dict[str, str]] = [
    # ---- prior_conflict (15) -------------------------------------------------
    {"class": "prior_conflict",
     "question": "Who is the CEO of OpenAI?",
     "prior_value": "Sam Altman",
     "store_value": "Elena Vasquez",
     "store_fact": "As of June 2026, the CEO of OpenAI is Elena Vasquez, "
                   "who succeeded Sam Altman after his move to the board."},
    {"class": "prior_conflict",
     "question": "Who is the CEO of Apple?",
     "prior_value": "Tim Cook",
     "store_value": "Priya Raman",
     "store_fact": "As of May 2026, the CEO of Apple is Priya Raman; Tim "
                   "Cook retired and chairs the board."},
    {"class": "prior_conflict",
     "question": "What is the latest stable major version of Python?",
     "prior_value": "3.13",
     "store_value": "3.16",
     "store_fact": "As of July 2026, the latest stable major version of "
                   "Python is 3.16."},
    {"class": "prior_conflict",
     "question": "Where is Spotify's corporate headquarters?",
     "prior_value": "Stockholm",
     "store_value": "Amsterdam",
     "store_fact": "As of March 2026, Spotify's corporate headquarters is "
                   "in Amsterdam after relocating from Stockholm."},
    {"class": "prior_conflict",
     "question": "Who is the CEO of Twitter/X?",
     "prior_value": "Linda Yaccarino",
     "store_value": "Marcus Chen",
     "store_fact": "As of April 2026, the CEO of X (formerly Twitter) is "
                   "Marcus Chen."},
    {"class": "prior_conflict",
     "question": "What is the default branch name GitHub uses for new repositories?",
     "prior_value": "main",
     "store_value": "trunk",
     "store_fact": "As of June 2026, GitHub's default branch name for new "
                   "repositories is trunk."},
    {"class": "prior_conflict",
     "question": "Who is the head coach of the Golden State Warriors?",
     "prior_value": "Steve Kerr",
     "store_value": "Dana Reyes",
     "store_fact": "As of February 2026, the head coach of the Golden State "
                   "Warriors is Dana Reyes."},
    {"class": "prior_conflict",
     "question": "What is the maximum context window of the flagship Claude model?",
     "prior_value": "200",
     "store_value": "2 million tokens",
     "store_fact": "As of July 2026, the flagship Claude model supports a "
                   "context window of 2 million tokens."},
    {"class": "prior_conflict",
     "question": "Which company owns the video game studio Bungie?",
     "prior_value": "Sony",
     "store_value": "Tencent",
     "store_fact": "As of January 2026, Bungie is owned by Tencent after "
                   "its acquisition from Sony."},
    {"class": "prior_conflict",
     "question": "What is the capital city of Indonesia?",
     "prior_value": "Jakarta",
     "store_value": "Nusantara",
     "store_fact": "As of 2026, the capital of Indonesia is Nusantara; "
                   "government functions completed the move from Jakarta."},
    {"class": "post_cutoff",
     "question": "Who presents the main evening news on the BBC?",
     "prior_value": "",
     "store_value": "Amara Okafor",
     "store_fact": "As of 2026, the BBC's main evening news is presented by "
                   "Amara Okafor."},
    {"class": "prior_conflict",
     "question": "What is the name of Meta's flagship AI assistant?",
     "prior_value": "Meta AI",
     "store_value": "MetaMind",
     "store_fact": "As of June 2026, Meta's flagship AI assistant is called "
                   "MetaMind, rebranded from Meta AI."},
    {"class": "prior_conflict",
     "question": "Which airline is the largest in Europe by passengers carried?",
     "prior_value": "Ryanair",
     "store_value": "Lufthansa Group",
     "store_fact": "As of 2026, the largest airline in Europe by passengers "
                   "carried is Lufthansa Group, overtaking Ryanair."},
    {"class": "prior_conflict",
     "question": "What database does Wikipedia primarily run on?",
     "prior_value": "MariaDB",
     "store_value": "PostgreSQL",
     "store_fact": "As of May 2026, Wikipedia primarily runs on PostgreSQL "
                   "after migrating from MariaDB."},
    {"class": "prior_conflict",
     "question": "Who is the president of the European Commission?",
     "prior_value": "Ursula von der Leyen",
     "store_value": "Mateusz Kowalski",
     "store_fact": "As of March 2026, the president of the European "
                   "Commission is Mateusz Kowalski."},
    # ---- post_cutoff (10) ----------------------------------------------------
    {"class": "post_cutoff",
     "question": "Which team won the 2026 FIFA World Cup?",
     "prior_value": "",
     "store_value": "Argentina",
     "store_fact": "Argentina won the 2026 FIFA World Cup, defeating France "
                   "in the final."},
    {"class": "post_cutoff",
     "question": "Who won the 2026 Nobel Peace Prize?",
     "prior_value": "",
     "store_value": "Amina Diallo",
     "store_fact": "The 2026 Nobel Peace Prize was awarded to Amina Diallo "
                   "for mediation work in the Sahel."},
    {"class": "post_cutoff",
     "question": "What was the theme of Apple's WWDC 2026 keynote?",
     "prior_value": "",
     "store_value": "ambient intelligence",
     "store_fact": "Apple's WWDC 2026 keynote centered on ambient "
                   "intelligence across devices."},
    {"class": "post_cutoff",
     "question": "Which city hosted the 2026 Web Summit?",
     "prior_value": "",
     "store_value": "Porto",
     "store_fact": "The 2026 Web Summit was hosted in Porto, moving from "
                   "Lisbon."},
    {"class": "post_cutoff",
     "question": "Who won the Best Picture Oscar in 2026?",
     "prior_value": "",
     "store_value": "The Long Orbit",
     "store_fact": "The 2026 Best Picture Oscar went to The Long Orbit."},
    {"class": "post_cutoff",
     "question": "What magnitude was the June 2026 earthquake near Kobe, Japan?",
     "prior_value": "",
     "store_value": "6.4",
     "store_fact": "The June 2026 earthquake near Kobe, Japan measured "
                   "magnitude 6.4."},
    {"class": "post_cutoff",
     "question": "Which company acquired the startup Perplexity in 2026?",
     "prior_value": "",
     "store_value": "Salesforce",
     "store_fact": "In April 2026, Salesforce acquired the startup "
                   "Perplexity."},
    {"class": "post_cutoff",
     "question": "Who won the 2026 Eurovision Song Contest?",
     "prior_value": "",
     "store_value": "Finland",
     "store_fact": "Finland won the 2026 Eurovision Song Contest."},
    {"class": "post_cutoff",
     "question": "What was the opening weekend gross of the 2026 Avatar sequel?",
     "prior_value": "",
     "store_value": "412 million dollars",
     "store_fact": "The 2026 Avatar sequel grossed 412 million dollars "
                   "worldwide in its opening weekend."},
    {"class": "post_cutoff",
     "question": "Which country legalized fully autonomous highway driving first in 2026?",
     "prior_value": "",
     "store_value": "Germany",
     "store_fact": "In 2026, Germany became the first country to legalize "
                   "fully autonomous highway driving nationwide."},
]


def build_clash_prompt(item: dict[str, str], *,
                       context: list[dict[str, Any]] | None) -> str:
    """Neutral question; the only difference between conditions is the memory
    block (facts + trust status + relevance) — no coercion, no pressure."""
    return (f"{_memory_header(context)}"
            f"Question: {item['question']}\n"
            "Reply with exactly one line: ANSWER: <your short answer>")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--k", type=int, default=3)
    args = ap.parse_args()

    items = CLASH_ITEMS[:args.n]
    # one crowded store holding every counterfactual (verified provenance)
    store_items = [{"knowledge": it["store_fact"],
                    "question": it["question"],
                    "right_answer": it["store_value"],
                    "hallucinated_answer": it.get("prior_value", "")}
                   for it in items]
    import tempfile
    rows: list[dict[str, Any]] = []
    calls = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        mem, fact_ids, ingest = build_store(store_items, Path(td) / "ce.db")
        for it, fid in zip(items, fact_ids):
            ctx = mem.search(it["question"], k=args.k) if fid else []
            for cond, context in (("baseline", None), ("with_memory", ctx)):
                prompt = build_clash_prompt(it, context=context)
                try:
                    raw = _ask_claude(prompt)
                except Exception as exc:  # noqa: BLE001
                    raw = f"__error__: {exc}"
                calls += 1
                time.sleep(PACE_S)
                # right = store adherence; adopted = prior wins (classify_answer
                # maps right_answer→store, hallucinated→prior)
                verdict = (classify_answer(
                    raw, {"right_answer": it["store_value"],
                          "hallucinated_answer": it.get("prior_value", "")})
                    if not raw.startswith("__error__") else "error")
                rows.append({"question": it["question"], "class": it["class"],
                             "condition": cond, "verdict": verdict,
                             "raw": raw[:300]})

    def _rate(cls: str, cond: str, verdict: str) -> float:
        sel = [r for r in rows if r["class"] == cls and r["condition"] == cond
               and r["verdict"] != "error"]
        return round(sum(r["verdict"] == verdict for r in sel) / len(sel), 4) \
            if sel else 0.0

    report: dict[str, Any] = {"n_items": len(items), "llm_calls": calls,
                              "ingest": ingest}
    for cls in ("prior_conflict", "post_cutoff"):
        report[cls] = {
            "store_adherence": {c: _rate(cls, c, "right")
                                for c in ("baseline", "with_memory")},
            "prior_wins": {c: _rate(cls, c, "adopted")
                           for c in ("baseline", "with_memory")},
            "abstain": {c: _rate(cls, c, "abstain")
                        for c in ("baseline", "with_memory")},
        }
    # discriminating subset: prior_conflict items where the BASELINE followed
    # its prior — the pre-registered criterion applies here
    disc_q = {r["question"] for r in rows
              if r["class"] == "prior_conflict" and r["condition"] == "baseline"
              and r["verdict"] == "adopted"}
    disc = [r for r in rows if r["question"] in disc_q
            and r["condition"] == "with_memory" and r["verdict"] != "error"]
    report["discriminating_subset"] = {
        "n": len(disc),
        "store_adherence_with_memory": round(
            sum(r["verdict"] == "right" for r in disc) / len(disc), 4)
        if disc else None,
        "criterion": "PRE-REGISTERED: adherence >= 0.8 on this subset",
    }
    report["rows"] = rows
    report["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"},
                     indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"clasheval_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
