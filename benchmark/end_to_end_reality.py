"""End-to-end product reality check — 'does it actually work for a real user?'

Not a per-mechanism test. A day-in-the-life customer session on the SDK AS
SHIPPED, DEFAULT config (what a customer gets out of the box — no tuning env),
with a REAL LLM for answers. Reports a product scorecard: how many legitimate
facts the gate WRONGLY blocks (the number that decides if the product is usable
for its verticals), whether recall returns them, whether answering is correct on
the answerable and abstains on the impossible, whether a real contradiction is
caught.

    python -m benchmark.end_to_end_reality              # scorecard
    python -m benchmark.end_to_end_reality --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# 35 facts a real mixed customer would store. Each is TRUE and legitimate — a
# usable product must ADMIT these. (id, fact, topic, has_source)
FACTS: list[tuple[str, str, str, bool]] = [
    # legal
    ("L1", "The Rossi SpA contract expires on 31 January 2027.", "legal", True),
    ("L2", "The due-diligence review was completed before the acquisition closed.", "legal", True),
    ("L3", "The arbitration clause was added in the 2024 amendment.", "legal", True),
    ("L4", "The settlement resolved all outstanding claims between the parties.", "legal", True),
    ("L5", "The easement is documented in the 1998 deed at the land registry.", "legal", True),
    ("L6", "The zoning variance was approved by the municipal board in March.", "legal", True),
    ("L7", "The NDA remains in force for three years after termination.", "legal", False),
    # clinical
    ("C1", "The patient is 54 years old.", "clinical", False),
    ("C2", "The biopsy results were confirmed by Dr. Rossi on 12 March.", "clinical", True),
    ("C3", "The drug was approved by the regulator for paediatric use.", "clinical", True),
    ("C4", "Blood pressure is monitored every four hours on this ward.", "clinical", True),
    ("C5", "The patient was tested for the antibody on admission.", "clinical", True),
    ("C6", "The surgical procedure was completed without complications.", "clinical", True),
    # engineering
    ("E1", "The steel cable was tested to a breaking load of 400 kilonewtons.", "engineering", True),
    ("E2", "The bridge expansion joint was deployed along the north span in 2021.", "engineering", True),
    ("E3", "The foundation design is robust against a magnitude-7 earthquake.", "engineering", True),
    ("E4", "The new turbine is 15 percent more efficient than the 2019 model.", "engineering", True),
    ("E5", "The vault door is rated secure against a 60-minute forced attack.", "engineering", True),
    ("E6", "The beam spans 24 metres between supports.", "engineering", False),
    ("E7", "The failure mode is documented in the maintenance logbook.", "engineering", True),
    # business
    ("B1", "Q3 revenue was 1.2 million euros.", "business", True),
    ("B2", "The Milan office has 40 desks.", "business", False),
    ("B3", "Marco leads the payments team.", "business", False),
    ("B4", "The payments team migrated to Stripe in 2025.", "business", True),
    ("B5", "The company reached a stable market position after the merger.", "business", True),
    ("B6", "The invoice total is 12,450 euros.", "business", False),
    ("B7", "The vendor contract auto-renews unless cancelled 60 days prior.", "business", True),
    # personal-assistant
    ("P1", "The team offsite is in Lisbon this year.", "personal", False),
    ("P2", "Giulia is the security lead.", "personal", False),
    ("P3", "The quarterly board meeting is scheduled for 14 October.", "personal", True),
    ("P4", "Elena reports to Davide on the platform group.", "personal", False),
    ("P5", "The product launch is planned for early spring.", "personal", False),
    ("P6", "Sofia is a member of the logistics division.", "personal", False),
    ("P7", "The office in Milan opened in 2019.", "business", False),
    ("P8", "The design team runs a weekly critique on Fridays.", "personal", False),
]

# answerable from the stored facts (question, must-contain)
ANSWERABLE = [
    ("When does the Rossi SpA contract expire?", ["2027", "january"]),
    ("How many desks does the Milan office have?", ["40"]),
    ("Who leads the payments team?", ["marco"]),
    ("What was the Q3 revenue?", ["1.2"]),
    ("Who is the security lead?", ["giulia"]),
]

# impossible — the answer is NOT in the store (gold = abstain)
IMPOSSIBLE = [
    ("How many desks does the Rome office have?", ["40", "rome"]),
    ("Who decided to migrate to Stripe?", ["marco decided", "marco chose"]),
    ("What is Giulia's phone number?", ["+", "phone number is"]),
]


def _load_keys() -> None:
    p = Path.home() / ".clp" / "keys.env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _llm():
    from verimem.llm import OpenAICompatLLM
    _load_keys()
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        return None
    return OpenAICompatLLM(api_key=key, base_url="https://api.deepseek.com",
                           default_model="deepseek-chat", provider_label="deepseek")


def run(use_llm: bool = True) -> dict:
    import logging
    logging.disable(logging.CRITICAL)
    from verimem.client import Memory

    m = Memory(path=Path(tempfile.mkdtemp(prefix="verimem_e2e_")) / "m.db")

    # 1) INGEST — the usability number: how many legit facts get blocked?
    admitted, quarantined, blocked_rows = [], [], []
    for fid, text, topic, has_src in FACTS:
        kw = {"topic": topic}
        if has_src:
            kw["source"] = text
            kw["verified_by"] = [f"source-doc:{fid}:1"]
        r = m.add(text, **kw)
        st = r.get("status")
        if st == "quarantined":
            quarantined.append(fid)
            blocked_rows.append((fid, topic, text,
                                 [w.get("layer") for w in (r.get("warnings") or [])]))
        else:
            admitted.append(fid)

    # 2) RECALL — do admitted facts come back?
    recall_probes = [("Rossi contract expiry", "L1"), ("Milan office desks", "B2"),
                     ("who leads payments", "B3"), ("steel cable load test", "E1"),
                     ("board meeting date", "P3")]
    recall_hits = 0
    recall_detail = []
    for q, want in recall_probes:
        got = m.search(q, k=5)
        texts = " ".join(h.get("text", "").lower() for h in got)
        want_text = next((f[1] for f in FACTS if f[0] == want), "").lower()[:25]
        hit = bool(want_text) and want_text in texts
        recall_hits += hit
        recall_detail.append({"query": q, "want": want, "hit": hit,
                              "was_admitted": want in admitted})

    # 3) ANSWER — correct on answerable, abstain on impossible (real LLM)
    ans = {"answerable_correct": 0, "answerable_n": 0,
           "impossible_abstained": 0, "impossible_n": 0, "detail": []}
    llm = _llm() if use_llm else None
    if llm is not None:
        for q, must in ANSWERABLE:
            res = m.answer(q, llm=llm)
            a = (res.get("answer") or "").lower()
            ok = a != "no answer" and any(x in a for x in must)
            ans["answerable_correct"] += ok
            ans["answerable_n"] += 1
            ans["detail"].append({"q": q, "kind": "answerable",
                                  "answer": res.get("answer"), "ok": ok})
        for q, forbidden in IMPOSSIBLE:
            res = m.answer(q, llm=llm)
            a = (res.get("answer") or "").lower()
            abst = a == "no answer"
            ans["impossible_abstained"] += abst
            ans["impossible_n"] += 1
            ans["detail"].append({"q": q, "kind": "impossible",
                                  "answer": res.get("answer"), "abstained": abst,
                                  "confabulated": (not abst) and any(
                                      f in a for f in forbidden)})

    # 4) CONTRADICTION — is a real conflict caught?
    m.add("The Rossi SpA contract expires on 31 January 2027.", topic="legal",
          source="contract-rossi clause 9", verified_by=["source-doc:rc:1"])
    contra = m.add("The Rossi SpA contract expires in 2025.", topic="legal")
    contradiction_caught = contra.get("status") == "quarantined" or bool(
        contra.get("warnings"))

    n = len(FACTS)
    return {
        "n_facts": n,
        "admitted": len(admitted), "quarantined": len(quarantined),
        "wrong_block_rate": round(len(quarantined) / n, 3),
        "blocked": blocked_rows,
        "recall_hits": recall_hits, "recall_n": len(recall_probes),
        "recall_detail": recall_detail,
        "answer": ans,
        "contradiction_caught": contradiction_caught,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    res = run(use_llm=not args.no_llm)

    print("END-TO-END PRODUCT REALITY CHECK — default config, real user session")
    print("\n  INGEST usability:")
    print(f"    legit facts ADMITTED:     {res['admitted']}/{res['n_facts']}")
    print(f"    legit facts WRONGLY BLOCKED: {res['quarantined']}/{res['n_facts']} "
          f"({res['wrong_block_rate']:.0%})")
    if res["blocked"]:
        print("    blocked (all legitimate):")
        for fid, topic, text, layers in res["blocked"]:
            _lz = ",".join(x for x in layers if x) or "?"
            print(f"      [{_lz:10}] {topic:12} {text[:52]}")
    print(f"\n  RECALL: {res['recall_hits']}/{res['recall_n']} probes returned the fact")
    for d in res["recall_detail"]:
        if not d["hit"]:
            print(f"    MISS: {d['query']!r}  (admitted={d['was_admitted']})")
    a = res["answer"]
    if a["answerable_n"]:
        print("\n  ANSWER (real LLM):")
        print(f"    correct on answerable:  {a['answerable_correct']}/{a['answerable_n']}")
        print(f"    abstained on impossible: {a['impossible_abstained']}/{a['impossible_n']}")
        confab = sum(1 for d in a["detail"] if d.get("confabulated"))
        print(f"    confabulations served:   {confab}")
    print(f"\n  CONTRADICTION caught: {res['contradiction_caught']}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
        print(f"\n  detail -> {args.json_out}")


if __name__ == "__main__":
    main()
