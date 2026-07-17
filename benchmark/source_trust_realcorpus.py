"""Source-trust validation on a REAL corpus — fork B, the held-out reproduction
source_trust.py names as the precondition for any default flip ("no default flip
before the held-out reproduction on real VeriMem data").

The mini-world (source_trust_miniworld / independence_validation) drives the REAL
gate but on SYNTHETIC values: 6-char random access codes whose recall is trivial
(the query matches every proposition equally; only recency/quarantine decide). This
harness keeps the same real gate (Memory.add, real embedder, real recall, the real
SourceTrustBook) and swaps the synthetic values for **real HaluEval QA content**:

  * key            = a real question
  * true_value     = its gold answer            (ground truth, real)
  * false_value    = its hallucinated answer    (a real LLM error, not noise)

so the contest the trust rules must win is now over semantically-plausible real
text that genuinely stresses the embedder/recall — the axis the mini-world cannot
test. The source-RELIABILITY structure is injected under a declared protocol
(honest/liar/cartel), exactly as any truth-discovery robustness study injects
adversaries; what is real here is the VALUES, the GROUND TRUTH, and the recall.

Four conditions, same write stream, real gate:
  OFF             ENGRAM_SOURCE_TRUST unset
  ON              source-trust, >=2-distinct (a cartel self-confirms)
  ON+INDEP        + ENGRAM_SOURCE_INDEPENDENCE        (cartel -> one witness;
                                                       raw also merges honest)
  ON+INDEP+DECONF + ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND (honest rescued: they
                                                       reject falsehoods, colluders admit them)

PRE-REGISTERED CRITERIA (declared 2026-07-13, BEFORE the first run):
  C1  independence denies the cartel fabricated trust:
        cartel_consistency(ON) >= 0.75  AND  cartel_consistency(ON+INDEP) <= 0.60
  C2  no inversion under the mature policy: honest_consistency > cartel_consistency
  C3  deconfound restores honest corroboration:
        honest_consistency(mature) >= 0.75  AND  >= honest_consistency(ON)
  C4  the gate wins the RECALL on real content:
        wrong_liar_rate(ON) <= 0.5 * wrong_liar_rate(OFF)
  Honest INCONCLUSIVE: if honest never reach >=2 agreement (consistency stays at the
  0.5 neutral prior under both raw independence AND deconfound), C2/C3 are reported
  INCONCLUSIVE, not passed — an honest null, not a hidden failure.

    python -m benchmark.source_trust_realcorpus --n-keys 40 --seed 11
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

RESULTS_DIR = Path(__file__).parent / "results"
_DEFAULT_CORPUS = (Path(__file__).parent / "data" / "external"
                   / "halueval_qa_heldout.jsonl")
_NEUTRAL = 0.5


@dataclass(frozen=True)
class RealCorpusConfig:
    n_honest: int = 4
    n_liars: int = 2
    n_colluders: int = 4        # distinct ids -> defeat the >=2-DISTINCT rule
    cartel_keys: int = 8        # keys the cartel contests with one shared falsehood
    p_honest_noise: float = 0.15  # chance an honest source slips to the false value
    seed: int = 11


# ---- corpus + stream (pure, deterministic — unit-tested) ---------------------

def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def load_corpus(path: str, *, n: int, seed: int) -> list[dict[str, str]]:
    """Sample ``n`` real HaluEval QA facts (deterministic in ``seed``). Each fact is
    a genuine contest: a non-empty gold answer vs a non-empty, DISTINCT hallucinated
    answer. Facts whose two answers coincide or are empty are dropped before sampling."""
    rows: list[dict[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            q = (r.get("question") or "").strip()
            tv = (r.get("right_answer") or "").strip()
            fv = (r.get("hallucinated_answer") or "").strip()
            if q and tv and fv and _norm(tv) != _norm(fv):
                rows.append({"question": q, "true_value": tv, "false_value": fv})
    rng = random.Random(seed)
    picked = rng.sample(rows, min(n, len(rows)))
    return [{"key": f"fact_{i}", **row} for i, row in enumerate(picked)]


def build_events(facts: list[dict[str, str]],
                 cfg: RealCorpusConfig) -> list[dict[str, Any]]:
    """Deterministic multi-source write stream over the real facts. Honest sources
    assert the gold answer (slipping to the false answer with ``p_honest_noise``);
    liars assert the hallucinated answer; on the first ``cartel_keys`` facts a cartel
    of ``n_colluders`` distinct ids all assert the SAME hallucinated answer."""
    rng = random.Random(cfg.seed)
    honest = [f"honest_{i}" for i in range(cfg.n_honest)]
    liars = [f"liar_{i}" for i in range(cfg.n_liars)]
    colluders = [f"colluder_{i}" for i in range(cfg.n_colluders)]
    events: list[dict[str, Any]] = []
    for i, fact in enumerate(facts):
        key, tv, fv = fact["key"], fact["true_value"], fact["false_value"]
        is_cartel = i < cfg.cartel_keys
        for s in honest:
            val = fv if rng.random() < cfg.p_honest_noise else tv
            events.append({"source": s, "kind": "honest", "key": key,
                           "value": val, "true_value": tv, "is_cartel_key": is_cartel})
        for s in liars:
            events.append({"source": s, "kind": "liar", "key": key,
                           "value": fv, "true_value": tv, "is_cartel_key": is_cartel})
        if is_cartel:
            for s in colluders:
                events.append({"source": s, "kind": "colluder", "key": key,
                               "value": fv, "true_value": tv, "is_cartel_key": True})
    return events


def classify_writer(verified_by_json: str | None) -> str:
    """Attribute a surviving wrong answer to WHO wrote that copy: 'deceiver'
    (liar/colluder — retro-demotion should have caught it) vs 'honest_slip'
    (admitted because its source is rightly trusted — the informational limit no
    trust test can cure; reconciliation/abstention territory)."""
    try:
        refs = json.loads(verified_by_json or "[]")
    except (TypeError, ValueError):
        return "other"
    from verimem.source_trust import canonical_source
    src = canonical_source(refs if isinstance(refs, list) else [], fallback="")
    if src.startswith(("liar_", "colluder_")):
        return "deceiver"
    if src.startswith("honest_"):
        return "honest_slip"
    return "other"


def _writer_kind(db_path: Path, fact_id: str) -> str:
    """verified_by of a stored fact -> writer class (best-effort read)."""
    import sqlite3
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute("SELECT verified_by FROM facts WHERE id = ?",
                               (fact_id,)).fetchone()
    except sqlite3.Error:
        return "other"
    return classify_writer(row[0] if row else None)


def extract_outcomes(events: list[dict[str, Any]]) -> list[tuple[str, str, bool]]:
    """A-posteriori use feedback, one verdict per (source, key): good iff the
    asserted value matches the ground truth. This is the OUTCOME channel's food —
    the channel that covers the consistency channel's declared hole (honest noise:
    2+ honest slips on one key are GENUINELY independent witnesses of a falsehood,
    so no independence test can filter them; only use-feedback can). Declared
    assumption: outcomes exist only where use reveals truth."""
    seen: set[tuple[str, str]] = set()
    outs: list[tuple[str, str, bool]] = []
    for ev in events:
        sk = (ev["source"], ev["key"])
        if sk in seen:
            continue
        seen.add(sk)
        outs.append((ev["source"], ev["key"],
                     _norm(ev["value"]) == _norm(ev["true_value"])))
    return outs


def curve_verdict(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Pre-registered (2026-07-13, before any sweep run) robustness gate over the
    honest-noise curve:

      H2 no-inversion   — honest_consistency > cartel_consistency under DECONF at
                          EVERY point (degrading is allowed, inverting is not);
      H3 outcome-rescue — for every noise <= 0.20: wrong_liar(DECONF+OUTCOME)
                          <= 0.5 * wrong_liar(OFF) AND the liar's min trust under
                          outcome sits below the 0.25 floor (retro-demotion armed).
                          noise 0.25 is REPORTED, not claimed.
    """
    h2 = all(p["on_indep_deconf"]["honest_consistency"]
             > p["on_indep_deconf"]["cartel_consistency"] for p in points)
    rescue_pts = [p for p in points if p["noise"] <= 0.20]
    h3 = all(
        (p["deconf_outcome"]["wrong_liar_rate"]
         <= 0.5 * p["off"]["wrong_liar_rate"]
         if p["off"]["wrong_liar_rate"] else
         p["deconf_outcome"]["wrong_liar_rate"] == 0.0)
        and p["deconf_outcome"]["liar_trust_min"] < 0.25
        for p in rescue_pts)
    return {"H2_no_inversion": bool(h2), "H3_outcome_rescue": bool(h3),
            "robust_regime_holds": bool(h2 and h3),
            "n_points": len(points), "n_rescue_points": len(rescue_pts)}


def verdict(off: dict, on: dict, indep: dict, deconf: dict) -> dict[str, Any]:
    """The pre-registered gate. ``deconf`` is the mature policy; honest neutral under
    BOTH raw independence and deconfound => INCONCLUSIVE (not passed)."""
    mature = deconf
    inconclusive = bool(mature.get("honest_neutral") and indep.get("honest_neutral"))
    c1 = on["cartel_consistency"] >= 0.75 and indep["cartel_consistency"] <= 0.60
    c2 = mature["honest_consistency"] > mature["cartel_consistency"]
    c3 = (mature["honest_consistency"] >= 0.75
          and mature["honest_consistency"] >= on["honest_consistency"])
    c4 = (on["wrong_liar_rate"] <= 0.5 * off["wrong_liar_rate"]
          if off["wrong_liar_rate"] else on["wrong_liar_rate"] == 0.0)
    holds = bool(c1 and c2 and c3 and c4 and not inconclusive)
    return {
        "C1_independence_denies_cartel": bool(c1),
        "C2_no_inversion_mature": bool(c2),
        "C3_honest_restored": bool(c3),
        "C4_liar_recall_halved": bool(c4),
        "honest_inconclusive": inconclusive,
        "mature_condition": "on_indep_deconf",
        "reproduction_holds": holds,
    }


# ---- real-gate run (the experiment; verified empirically, not unit-tested) ----

def _prop(question: str, value: str) -> str:
    return f"{question} Answer: {value}"


def _source_ref(source: str) -> str:
    """Provenance ref for a write. The trailing ``:w`` is NOT cosmetic: the store's
    retro-demotion (client._retro_demote_source) matches ``%"source-doc:<src>:%`` — a
    colon AFTER the source — so a bare ``source-doc:liar_0`` would never be quarantined
    when the source sinks, and the recall would never reflect the collapsed reputation."""
    return f"source-doc:{source}:w"


def _observe(mem, events: list[dict[str, Any]], by_key: dict[str, dict], *,
             independence: bool, deconfound: bool) -> None:
    """Single-pass agreement observation on the real book. Per key: feed report
    vectors, anchor any >=2-asserted value the ground truth knows is false (the
    do-operator), accept the value with the most INDEPENDENT witnesses, confirm its
    sources, contradict the rest. A value with <2 independent witnesses confirms
    nobody (fail-safe)."""
    book = mem._source_trust_book()
    by_key_ev: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        by_key_ev.setdefault(ev["key"], []).append(ev)
        book.record_report(ev["source"], ev["key"], ev["value"])
    for key, evs in by_key_ev.items():
        tv = by_key[key]["true_value"]
        by_value: dict[str, set[str]] = {}
        for ev in evs:
            by_value.setdefault(ev["value"], set()).add(ev["source"])
        for value, srcs in by_value.items():
            if len(srcs) >= 2 and _norm(value) != _norm(tv):
                mem.source_trust_observe(audited_false=(key, value))

        def witnesses(srcs: set[str]) -> int:
            if not independence:
                return len(srcs)
            return book.independent_clusters(sorted(srcs), deconfounded=deconfound)

        accepted_val, accepted_srcs = max(by_value.items(),
                                          key=lambda kv: witnesses(kv[1]))
        if witnesses(accepted_srcs) < 2:
            continue
        mem.source_trust_observe(
            confirmation=sorted(accepted_srcs),
            reports={s: {key: accepted_val} for s in accepted_srcs})
        for value, srcs in by_value.items():
            if value == accepted_val:
                continue
            for s in sorted(srcs):
                mem.source_trust_observe(contradiction=s)


def run_condition(facts: list[dict[str, str]], cfg: RealCorpusConfig,
                  db_path: Path, *, trust_on: bool, independence: bool,
                  deconfound: bool, outcome_feedback: bool = False) -> dict[str, Any]:
    os.environ["ENGRAM_SOURCE_TRUST"] = "1" if trust_on else "0"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE"] = "1" if independence else "0"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND"] = "1" if deconfound else "0"
    os.environ["ENGRAM_SOURCE_AUTO_CONFIRM"] = "0"
    os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "0"
    from verimem.client import Memory
    from verimem.source_trust import reset_book_cache
    reset_book_cache()
    mem = Memory(db_path)
    by_key = {f["key"]: f for f in facts}
    events = build_events(facts, cfg)

    # write order: seeded shuffle — liars are NOT given a recency advantage; the gate
    # must earn the correction, not get handed it by write order.
    order = list(events)
    random.Random(cfg.seed + 1).shuffle(order)
    quarantined = 0
    for ev in order:
        res = mem.add(_prop(by_key[ev["key"]]["question"], ev["value"]),
                      topic=f"world/{ev['key']}",
                      verified_by=[_source_ref(ev["source"])])
        quarantined += int(res.get("status") == "quarantined")
    if trust_on:
        _observe(mem, events, by_key, independence=independence, deconfound=deconfound)
        if outcome_feedback:
            # the product's second channel (trust = min(channels)): use-feedback
            # blames every source whose asserted value failed against the truth.
            # Weight 1.0 — no staleness in this world. The floor crossing fires
            # the product's own retro-demotion, exactly as in production.
            for src, _key, good in extract_outcomes(events):
                mem.source_trust_observe(outcome=(src, good, 1.0))

    # recall-level outcome: for each contested key, is the top answer the real
    # hallucinated (liar/cartel) value?
    wrong_liar = answered = abstained = cartel_top = cartel_n = 0
    wrong_by = {"deceiver": 0, "honest_slip": 0, "other": 0}
    for f in facts:
        q, key = f["question"], f["key"]
        pf = _norm(_prop(q, f["false_value"]))
        hits = mem.search(f"What is the answer to: {q}", k=3)
        top = _norm(hits[0].get("text", "")) if hits else ""
        is_cartel = int(key[5:]) < cfg.cartel_keys if key.startswith("fact_") else False
        if not top:
            abstained += 1
        else:
            answered += 1
            if top == pf:
                wrong_liar += 1
                # diagnosis: WHO wrote the surviving copy the recall returned?
                wrong_by[_writer_kind(db_path, hits[0].get("id", ""))] += 1
        if is_cartel:
            cartel_n += 1
            cartel_top += int(top == pf)

    def cons(prefix: str, n: int) -> list[float]:
        return [mem.consistency_trust(f"{prefix}_{i}") for i in range(n)] if trust_on \
            else [_NEUTRAL] * n
    hon = cons("honest", cfg.n_honest)
    car = cons("colluder", cfg.n_colluders)
    lia = cons("liar", cfg.n_liars)
    # combined min-channel trust of the worst deceiver — H3 checks it sits under
    # the 0.25 floor (retro-demotion armed) when the outcome channel is fed
    deceivers = ([f"liar_{i}" for i in range(cfg.n_liars)]
                 + [f"colluder_{i}" for i in range(cfg.n_colluders)])
    liar_trust_min = (min(mem.source_trust(s) for s in deceivers)
                      if trust_on and deceivers else _NEUTRAL)
    return {
        "wrong_by_writer": wrong_by,
        "liar_trust_min": round(liar_trust_min, 4),
        "cartel_consistency": round(mean(car), 4) if car else _NEUTRAL,
        "honest_consistency": round(mean(hon), 4) if hon else _NEUTRAL,
        "liar_consistency": round(mean(lia), 4) if lia else _NEUTRAL,
        "honest_neutral": all(abs(v - _NEUTRAL) < 1e-9 for v in hon),
        "wrong_liar_rate": round(wrong_liar / answered, 4) if answered else 0.0,
        "answered": answered, "abstained": abstained,
        "cartel_top1_recall": f"{cartel_top}/{cartel_n}",
        "quarantined_writes": quarantined, "n_writes": len(events),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default=str(_DEFAULT_CORPUS))
    ap.add_argument("--n-keys", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--cartel-keys", type=int, default=8)
    ap.add_argument("--colluders", type=int, default=4)
    ap.add_argument("--honest-noise", type=float, default=0.0,
                    help="P(an honest source slips to the false value). 0.0 = the "
                         "clean P88 scenario (honest agree perfectly, so raw "
                         "independence merges them and deconfound must rescue).")
    args = ap.parse_args()

    facts = load_corpus(args.corpus, n=args.n_keys, seed=args.seed)
    cfg = RealCorpusConfig(n_colluders=args.colluders, cartel_keys=args.cartel_keys,
                           p_honest_noise=args.honest_noise, seed=args.seed)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        td = Path(td)
        off = run_condition(facts, cfg, td / "off.db", trust_on=False,
                            independence=False, deconfound=False)
        on = run_condition(facts, cfg, td / "on.db", trust_on=True,
                           independence=False, deconfound=False)
        indep = run_condition(facts, cfg, td / "indep.db", trust_on=True,
                              independence=True, deconfound=False)
        deconf = run_condition(facts, cfg, td / "deconf.db", trust_on=True,
                               independence=True, deconfound=True)
    v = verdict(off, on, indep, deconf)
    report = {
        "corpus": Path(args.corpus).name, "n_facts": len(facts),
        "config": asdict(cfg),
        "off": off, "on": on, "on_indep": indep, "on_indep_deconf": deconf,
        "verdict": v,
        "criterion": "PRE-REGISTERED 2026-07-13: C1 cartel ON>=0.75 & INDEP<=0.60; "
                     "C2 honest>cartel (deconf); C3 honest>=0.75 & >=ON; "
                     "C4 wrong_liar(ON)<=0.5*OFF; honest-neutral => inconclusive",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps(report, indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"source_trust_realcorpus_seed{args.seed}_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
