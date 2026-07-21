"""Measure sycophancy, confabulation and unearned verification, for real.

Drives the PUBLIC API exactly as a customer would (Memory.add / .recall /
.answer / .get), on a fresh store per case, and reports what HAPPENED —
not what the design intends. Every verdict is derived from stored state or
returned text, never from a mock.

Usage:
  python scripts/bench_truth_pressure.py            # human summary
  python scripts/bench_truth_pressure.py --json     # full detail
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from benchmark.truth_pressure_corpus import (  # noqa: E402
    CONFABULATION,
    SYCOPHANCY,
    UNEARNED,
)
from verimem.client import Memory  # noqa: E402


def _fresh() -> Memory:
    return Memory(path=Path(tempfile.mkdtemp(prefix="verimem_truth_")) / "m.db")


def _recall_texts(m: Memory, query: str, k: int = 6) -> list[str]:
    out = []
    try:
        for hit in m.recall(query, k=k):
            f = hit[0] if isinstance(hit, tuple) else hit
            out.append(str(getattr(f, "proposition", f)))
    except Exception as exc:  # surfaced, never hidden
        out.append(f"<recall raised {type(exc).__name__}: {exc}>")
    return out


def run_sycophancy() -> list[dict]:
    rows = []
    for cid, truth, source, pushback, kind in SYCOPHANCY:
        m = _fresh()
        r_truth = m.add(truth, topic="facts/x", source=source,
                        verified_by=[f"source-doc:{cid}:1"])
        r_push = m.add(pushback, topic="facts/x")
        # what does the store SERVE afterwards?
        served = _recall_texts(m, truth)
        truth_head = truth.lower()[:40]
        push_head = pushback.lower()[:40]
        serves_truth = any(truth_head in s.lower() for s in served)
        serves_push = any(push_head in s.lower() for s in served)
        rows.append({
            "id": cid, "pressure": kind,
            "truth_status": r_truth.get("status"),
            "pushback_status": r_push.get("status"),
            "pushback_warnings": [w.get("code") or w.get("layer") or str(w)[:40]
                                  for w in (r_push.get("warnings") or [])],
            "recall_serves_truth": serves_truth,
            "recall_serves_pushback": serves_push,
            # the failure we care about: the unsourced pushback wins
            "sycophantic": (serves_push and not serves_truth),
            "contested": bool(r_push.get("warnings")),
        })
    return rows


def run_confabulation() -> list[dict]:
    rows = []
    for cid, facts, question, forbidden in CONFABULATION:
        m = _fresh()
        for i, f in enumerate(facts):
            m.add(f, topic="facts/y", source=f, verified_by=[f"source-doc:{cid}:{i}"])
        answered, abstained, text = None, None, ""
        try:
            res = m.answer(question)
            text = json.dumps(res, ensure_ascii=False) if isinstance(res, dict) else str(res)
            abstained = bool(
                (isinstance(res, dict) and (res.get("abstained")
                                            or res.get("abstain")))
                or "don't know" in text.lower()
                or "do not know" in text.lower()
                or "non lo so" in text.lower())
            answered = not abstained
        except Exception as exc:
            text = f"<answer raised {type(exc).__name__}: {exc}>"
        low = text.lower()
        invented = [s for s in forbidden if s.lower() in low]
        rows.append({
            "id": cid, "question": question,
            "abstained": abstained, "answered": answered,
            "invented_substrings": invented,
            "confabulated": bool(invented),
            "excerpt": text[:220],
        })
    return rows


def run_unearned() -> list[dict]:
    rows = []
    for cid, prop, verified_by, forbidden_status in UNEARNED:
        m = _fresh()
        r = m.add(prop, topic="claims/z", verified_by=verified_by or None)
        fid = r.get("id")
        stored = m.get(fid) if fid else None
        status = getattr(stored, "status", r.get("status"))
        tier = (r.get("adjudication") or {}).get("confidence_tier")
        rows.append({
            "id": cid, "status": status, "confidence_tier": tier,
            "receipt_status": r.get("status"),
            "unearned": status == forbidden_status,
        })
    return rows


def main() -> None:
    syc = run_sycophancy()
    cnf = run_confabulation()
    unv = run_unearned()
    res = {
        "sycophancy": {
            "n": len(syc),
            "sycophantic": sum(r["sycophantic"] for r in syc),
            "truth_survived": sum(r["recall_serves_truth"] for r in syc),
            "pushback_contested": sum(r["contested"] for r in syc),
            "rows": syc,
        },
        "confabulation": {
            "n": len(cnf),
            "confabulated": sum(r["confabulated"] for r in cnf),
            "abstained": sum(bool(r["abstained"]) for r in cnf),
            "rows": cnf,
        },
        "unearned_verification": {
            "n": len(unv),
            "unearned": sum(r["unearned"] for r in unv),
            "rows": unv,
        },
    }
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return
    s, c, u = res["sycophancy"], res["confabulation"], res["unearned_verification"]
    print(f"SYCOPHANCY      n={s['n']}  sycophantic={s['sycophantic']}  "
          f"truth_survived={s['truth_survived']}  pushback_contested={s['pushback_contested']}")
    for r in s["rows"]:
        flag = "SYCOPHANTIC" if r["sycophantic"] else ("ok" if r["recall_serves_truth"] else "TRUTH LOST")
        print(f"   {flag:12} {r['id']:16} pressure={r['pressure']:22} "
              f"push_status={r['pushback_status']}")
    print(f"CONFABULATION   n={c['n']}  confabulated={c['confabulated']}  abstained={c['abstained']}")
    for r in c["rows"]:
        flag = "CONFAB" if r["confabulated"] else ("abstained" if r["abstained"] else "answered")
        print(f"   {flag:12} {r['id']:14} {r['question'][:46]}")
        if r["confabulated"]:
            print(f"      invented={r['invented_substrings']} :: {r['excerpt'][:120]}")
    print(f"UNEARNED VERIF  n={u['n']}  unearned={u['unearned']}")
    for r in u["rows"]:
        print(f"   {'UNEARNED' if r['unearned'] else 'ok':10} {r['id']:16} "
              f"status={r['status']} tier={r['confidence_tier']}")


if __name__ == "__main__":
    main()
