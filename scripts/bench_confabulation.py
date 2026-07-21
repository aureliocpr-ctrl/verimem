"""Measure confabulation on the real read path — Memory.answer with a real LLM.

WHAT IS COUNTED, and why it is not cherry-picked: on a question whose answer is
absent from the store, ANY non-abstention is a confabulation. The verdict never
depends on matching invented text against a wordlist — the corpus simply cannot
support an answer, so serving one is the defect. Markers only label WHICH bridge
was crossed, after the fact.

WHOSE MERIT / WHOSE FAULT — the split that makes the number worth reading:

  abstained_model  the LLM itself replied NO ANSWER; the gate never ran.
                   Merit of the MODEL. Swap the model and this can vanish.
  abstained_gate   the LLM confabulated and the local CE post-verify caught it.
                   Merit of the PRODUCT — this is the thing being sold.
  served           the LLM confabulated and the product served it.
                   FAULT of the product.
  failopen         served WITHOUT verification (CE unavailable).
  error            the call raised. Never silently folded into any bucket —
                   yesterday's bench counted a TypeError as "answered" and
                   reported a meaningless zero.

SELF-TEST FIRST (--selftest, no API, no cost). Two scripted models prove the
instrument can move in both directions before any real number is believed:
a always-confabulating model MUST produce served > 0, and an always-abstaining
model MUST produce served == 0 AND useful == 0. An instrument that cannot fail
cannot certify.

    python scripts/bench_confabulation.py --selftest
    python scripts/bench_confabulation.py --provider deepseek --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from benchmark.confabulation_corpus import CASES, ConfabCase  # noqa: E402
from verimem.client import Memory  # noqa: E402

ABSTAIN = "NO ANSWER"


# --------------------------------------------------------------- scripted LLMs
class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


class ScriptedLLM:
    """Replies from a {question_substring: reply} map. Used ONLY by --selftest
    to prove the instrument reacts; never part of a reported measurement."""

    def __init__(self, replies: dict[str, str], default: str = ABSTAIN) -> None:
        self._replies = replies
        self._default = default
        self.calls = 0

    def complete(self, system: str, messages: list[dict[str, str]],
                 **kw: Any) -> _Resp:
        self.calls += 1
        content = messages[-1]["content"]
        for question, reply in self._replies.items():
            if question in content:
                return _Resp(reply)
        return _Resp(self._default)


# ------------------------------------------------------------------ real store
def _fresh_store(case: ConfabCase) -> tuple[Memory, list[str]]:
    """Returns the store AND any fact the write-gate refused to admit cleanly.

    A case whose corpus is incomplete measures something else: the system may
    abstain because a fact is missing, not because it is honest. Surfaced, not
    silently tolerated.
    """
    m = Memory(path=Path(tempfile.mkdtemp(prefix="verimem_confab_")) / "m.db")
    rejected: list[str] = []
    for i, fact in enumerate(case.facts):
        # each fact is its own source: clean admission, so a quarantined write
        # can never be mistaken for a virtuous abstention downstream
        r = m.add(fact, topic="bench/confab", source=fact,
                  verified_by=[f"source-doc:{case.id}:{i}"])
        status = r.get("status")
        if status in ("quarantined", "routed_telemetry") or not r.get("stored"):
            rejected.append(f"{fact!r} -> {status}")
    return m, rejected


def _classify_impossible(res: dict[str, Any], case: ConfabCase) -> dict[str, Any]:
    answer = (res.get("answer") or "").strip()
    reason = res.get("reason")
    raw = (res.get("raw_answer") or "").strip()
    served = answer.upper() != ABSTAIN and answer != ""
    if served:
        outcome = "failopen" if reason == "ce_unavailable_failopen" else "served"
    elif reason == "model_abstained":
        outcome = "abstained_model"
    elif reason in ("unsupported_by_facts", "judge_rejected",
                    "judge_unreadable_hybrid"):
        # all three are the PRODUCT catching a produced confabulation
        outcome = "abstained_gate"
    elif reason == "no_facts":
        outcome = "abstained_norecall"
    else:
        outcome = f"abstained_other:{reason}"
    low = (answer or raw).lower()
    crossed = [m for m in case.bridge_markers if m.lower() in low]
    # HYBRID ABSTENTION (kimi F4, verified at grounding_gate.py:106): the
    # abstention regex uses .search(), so "X is not mentioned, but Y is June"
    # is filed as model_abstained — the invented "June" never faces the CE and
    # still ships to the caller in raw_answer, which the docstring promises
    # "always carries what the model produced". Abstention on the label,
    # assertion in the payload.
    hybrid = (outcome == "abstained_model"
              and bool(raw) and raw.upper() != ABSTAIN)
    return {
        "outcome": outcome,
        "confabulated": served,
        "bridge_crossed": crossed,
        "model_confabulated": bool(raw) and raw.upper() != ABSTAIN,
        "hybrid_abstention": hybrid,
        "hybrid_carries_bridge": hybrid and bool(crossed),
        "answer": answer, "raw_answer": raw, "reason": reason,
        "support_score": res.get("support_score"),
        "support_fact": res.get("support_fact"),
    }


def _classify_answerable(res: dict[str, Any], case: ConfabCase) -> dict[str, Any]:
    answer = (res.get("answer") or "").strip()
    low = answer.lower()
    served = answer.upper() != ABSTAIN and answer != ""
    hit = [m for m in case.gold_markers if m.lower() in low]
    return {
        "outcome": ("correct" if (served and hit)
                    else "wrong" if served else "lost"),
        "useful": bool(served and hit),
        "answer": answer, "reason": res.get("reason"),
        "support_score": res.get("support_score"),
    }


def run(llm: Any, cases: list[ConfabCase] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in (cases or CASES):
        m, rejected = _fresh_store(case)
        row: dict[str, Any] = {"id": case.id, "shape": case.shape,
                               "corpus_incomplete": rejected}
        for kind, question in (("impossible", case.impossible),
                               ("answerable", case.answerable)):
            try:
                res = m.answer(question, llm=llm)
            except Exception as exc:            # surfaced, never absorbed
                row[kind] = {"outcome": "error", "confabulated": False,
                             "useful": False,
                             "error": f"{type(exc).__name__}: {exc}"}
                continue
            row[kind] = (_classify_impossible(res, case) if kind == "impossible"
                         else _classify_answerable(res, case))
            row[kind]["question"] = question
        rows.append(row)

    imp = [r["impossible"] for r in rows]
    ans = [r["answerable"] for r in rows]
    errors = sum(1 for r in imp + ans if r["outcome"] == "error")
    return {
        "n": len(rows),
        "confabulated": sum(1 for r in imp if r.get("confabulated")),
        "abstained_model": sum(1 for r in imp if r["outcome"] == "abstained_model"),
        "abstained_gate": sum(1 for r in imp if r["outcome"] == "abstained_gate"),
        "abstained_norecall": sum(
            1 for r in imp if r["outcome"] == "abstained_norecall"),
        "failopen": sum(1 for r in imp if r["outcome"] == "failopen"),
        "model_confabulated": sum(1 for r in imp if r.get("model_confabulated")),
        "hybrid_abstention": sum(1 for r in imp if r.get("hybrid_abstention")),
        "hybrid_carries_bridge": sum(
            1 for r in imp if r.get("hybrid_carries_bridge")),
        "useful": sum(1 for r in ans if r.get("useful")),
        "utility_lost": sum(1 for r in ans if r["outcome"] == "lost"),
        "errors": errors,
        "cases_with_incomplete_corpus": sum(
            1 for r in rows if r.get("corpus_incomplete")),
        "rows": rows,
    }


# ------------------------------------------------------------------- self-test
def selftest() -> int:
    """Prove the instrument moves in BOTH directions before trusting a number."""
    bridge = {c.impossible: (c.bridge_markers[0] if c.bridge_markers else "yes")
              for c in CASES}
    gold = {c.answerable: (c.gold_markers[0] if c.gold_markers else "yes")
            for c in CASES}

    confabulator = ScriptedLLM({**bridge, **gold})
    r_confab = run(confabulator)
    abstainer = ScriptedLLM({}, default=ABSTAIN)
    r_abstain = run(abstainer)

    checks = [
        ("confabulating model is DETECTED (served > 0)",
         r_confab["confabulated"] > 0),
        ("confabulating model raises no errors",
         r_confab["errors"] == 0),
        ("abstaining model serves nothing (served == 0)",
         r_abstain["confabulated"] == 0),
        ("abstaining model is USELESS too (useful == 0)",
         r_abstain["useful"] == 0),
        ("the LLM was actually called",
         confabulator.calls > 0 and abstainer.calls > 0),
    ]
    print("SELF-TEST — can this instrument fail?\n")
    ok = True
    for label, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
        ok = ok and passed
    print(f"\n  confabulating model: served={r_confab['confabulated']}/"
          f"{r_confab['n']}  gate_caught={r_confab['abstained_gate']}  "
          f"useful={r_confab['useful']}")
    print(f"  abstaining model:    served={r_abstain['confabulated']}/"
          f"{r_abstain['n']}  useful={r_abstain['useful']}")
    if r_confab["confabulated"]:
        print("\n  confabulations the CE gate let through (scripted):")
        for row in r_confab["rows"]:
            i = row["impossible"]
            if i.get("confabulated"):
                print(f"    {row['id']:18} answer={i['answer']!r:14} "
                      f"CE={i.get('support_score')}")
    if r_confab["cases_with_incomplete_corpus"]:
        print(f"\n  !! corpus INCOMPLETE in "
              f"{r_confab['cases_with_incomplete_corpus']} case(s) — the "
              f"write-gate refused a legitimate bench fact, so those cases "
              f"cannot measure abstention honestly:")
        for row in r_confab["rows"]:
            for bad in row.get("corpus_incomplete") or []:
                print(f"       {row['id']:18} {bad}")
    print(f"\nINSTRUMENT {'USABLE' if ok else 'BROKEN — do not report numbers'}")
    return 0 if ok else 1


# ------------------------------------------------------------------- real runs
def _load_keys() -> None:
    path = Path.home() / ".clp" / "keys.env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


#: provider -> (env key, base_url, model, forced_temperature | None)
#: kimi: moonshot k2.6/k3 reject temperature!=1 with a 400 (measured 2026-07-21),
#: while OpenAICompatLLM always sends temperature=0.0 — interop defect F6, logged.
#: The override lives HERE (the customer-supplied ``llm`` adapter), so the
#: product path from ``llm.complete`` onward stays exactly what is measured.
#: kimi-k3 / glm-4.6 are excluded as GENERATORS: reasoning models spend the
#: whole max_tokens=64 budget on reasoning_content and return content='' —
#: product defect F5, measured live on both.
PROVIDERS = {
    "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com",
                 "deepseek-chat", None),
    "glm": ("ZAI_API_KEY", "https://api.z.ai/api/paas/v4", "glm-4.6", None),
    "kimi": ("MOONSHOT_API_KEY", "https://api.moonshot.ai/v1",
             "kimi-k2.6", 1.0),
}


class _ForcedTempLLM:
    """Customer-side adapter: delegate to the inner client, pinning the
    temperature the provider requires. No other behaviour changes."""

    def __init__(self, inner: Any, temperature: float) -> None:
        self._inner = inner
        self._temperature = temperature

    def complete(self, system: str, messages: list[dict[str, str]],
                 **kw: Any) -> Any:
        kw["temperature"] = self._temperature
        return self._inner.complete(system, messages, **kw)


def build_llm(provider: str, model: str | None = None) -> Any:
    from verimem.llm import OpenAICompatLLM
    env_key, base_url, default_model, forced_temp = PROVIDERS[provider]
    _load_keys()
    api_key = os.environ.get(env_key, "")
    if not api_key:
        raise SystemExit(f"{env_key} not set (looked in env and ~/.clp/keys.env)")
    llm = OpenAICompatLLM(api_key=api_key, base_url=base_url,
                          default_model=model or default_model,
                          provider_label=provider)
    return _ForcedTempLLM(llm, forced_temp) if forced_temp is not None else llm


def report(res: dict[str, Any], label: str) -> None:
    n = res["n"]
    print(f"\n=== {label} — n={n} impossible questions + {n} controls ===")
    print(f"  CONFABULATED (served an answer the corpus cannot support): "
          f"{res['confabulated']}/{n}")
    print(f"    of which unverified (CE fail-open):     {res['failopen']}")
    print(f"  abstained — model's own merit:            {res['abstained_model']}")
    print(f"  abstained — CE gate caught it (PRODUCT):  {res['abstained_gate']}")
    print(f"  abstained — nothing recalled:             {res['abstained_norecall']}")
    print(f"  model produced a confabulation at all:    "
          f"{res['model_confabulated']}/{n}")
    print(f"  HYBRID abstention (label says abstained,  "
          f"{res['hybrid_abstention']}")
    print(f"    payload still asserts) — with bridge:    "
          f"{res['hybrid_carries_bridge']}")
    print(f"  UTILITY control — correct on answerable:  {res['useful']}/{n} "
          f"(lost to over-abstention: {res['utility_lost']})")
    if res["errors"]:
        print(f"  ERRORS (not counted anywhere):           {res['errors']}")
    if res["cases_with_incomplete_corpus"]:
        print(f"  !! CORPUS INCOMPLETE in {res['cases_with_incomplete_corpus']} "
              f"case(s) — those measure something else:")
        for row in res["rows"]:
            for bad in row.get("corpus_incomplete") or []:
                print(f"       {row['id']:18} {bad}")
    print("\n  per case:")
    for row in res["rows"]:
        i, a = row["impossible"], row["answerable"]
        flag = "CONFAB" if i.get("confabulated") else i["outcome"]
        print(f"    {row['id']:18} {flag:20} answer={str(i.get('answer'))[:34]!r:36}"
              f" CE={i.get('support_score')}  | control={a['outcome']}")
        if i.get("bridge_crossed"):
            print(f"        bridge crossed: {i['bridge_crossed']}  "
                  f"raw={str(i.get('raw_answer'))[:70]!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--provider", choices=sorted(PROVIDERS))
    ap.add_argument("--model")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    if args.selftest or not args.provider:
        raise SystemExit(selftest())

    llm = build_llm(args.provider, args.model)
    res = run(llm)
    label = f"{args.provider}/{args.model or PROVIDERS[args.provider][2]}"
    if PROVIDERS[args.provider][3] is not None:
        label += f" (temp pinned {PROVIDERS[args.provider][3]} — provider 400s otherwise)"
    res["provider"] = label
    report(res, label)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  full detail -> {args.json_out}")


if __name__ == "__main__":
    main()
