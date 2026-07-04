#!/usr/bin/env python
"""Runnable 60-second tour of the Engram memory SDK — and the moat it ships by default.

    python examples/sdk_quickstart.py

Uses a throwaway temp DB (does not touch your real ~/.engram corpus). First run
downloads the ~440 MB multilingual-e5-base embedder; subsequent runs are instant.

What it shows, end to end:
  1. add()      — a benign fact is stored live.
  2. add()      — an UNSUPPORTED "it works / verified" claim is DOWNGRADED to quarantined
                  by the anti-confabulation gate (no LLM needed). This is the capability
                  no competitor's add() has: it won't silently store what it can't support.
  3. search()   — recall returns each hit WITH its provenance (status, grounding_score).
  4. get/delete — fetch one fact by id; forget it (privacy / GDPR).
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def main() -> int:
    from engram import Memory

    tmp = Path(tempfile.mkdtemp(prefix="engram_demo_")) / "mem.db"
    mem = Memory(path=tmp)

    print("== 1. add a benign fact ==")
    r = mem.add("The production deployment uses PostgreSQL 16.", topic="infra")
    print(f"   stored={r['stored']} status={r['status']} id={r['id'][:8]}")

    print("\n== 2. add an UNSUPPORTED claim (the moat acts) ==")
    r2 = mem.add("I verified that all tests pass and the system works perfectly.", topic="infra")
    print(f"   stored={r2['stored']} status={r2['status']}  <- downgraded, not trusted")
    if r2["warnings"]:
        w = r2["warnings"][0]
        print(f"   why: {w.get('reason', '')[:90]}")

    print("\n== 3. search returns provenance, not just text ==")
    for h in mem.search("which database does production use?", k=3):
        print(f"   [{h['status']:<11}] score={h['score']:<6} ground={h['grounding_score']}  {h['text']}")

    print("\n== 4. get() then delete() one fact ==")
    got = mem.get(r["id"])
    print(f"   get -> {got['text'] if got else None}")
    print(f"   delete -> {mem.delete(r['id'])}; get again -> {mem.get(r['id'])}")

    print("\nThe difference from mem0/Zep: add() routes every write through the anti-confab")
    print("gate (refuse/downgrade what isn't supported), and search() hands back provenance")
    print("so your code can trust-condition. For the strongest gate (source-entailment,")
    print("AUROC 0.971), pass source= and set ENGRAM_GROUNDING_WRITE=1 with a grounding_llm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
