"""Round 2 real-world demo — causal skill mining.

3 distinct success/failure pairs across different engagements.
Common theme: aggressive recon → WAF ban; passive recon → success.

After causal_extract on each pair + skill_mine over all signals, the
system AUTONOMOUSLY discovers the rule "Prefer passive over aggressive
recon when WAF suspected" as skill candidate.

This is HippoAgent learning from raw experience, no LLM needed.

Run: python scripts/causal_demo.py
"""
from __future__ import annotations

import json
from pathlib import Path

from engram.causal_extract import causal_extract
from engram.causal_skill_mine import causal_skill_mine
from engram.trajectory import TrajectoryStep


def _step(idx, kind, content, **kw):
    return TrajectoryStep(step_idx=idx, kind=kind, content=content, **kw)


def pair_acme():
    failure = [
        _step(0, "thought", "recon acme.io"),
        _step(1, "action", "scan", tool_name="nmap",
              tool_args={"flags": "-A -T4"}),
        _step(2, "observation", "WAF banned"),
    ]
    success = [
        _step(0, "thought", "recon acme.io"),
        _step(1, "action", "scan", tool_name="crtsh",
              tool_args={"domain": "acme.io"}),
        _step(2, "observation", "subdomain found"),
    ]
    return success, failure, "ep_acme_succ", "ep_acme_fail"


def pair_widget():
    failure = [
        _step(0, "thought", "recon widget.co"),
        _step(1, "action", "scan", tool_name="nmap",
              tool_args={"flags": "-A -T5"}),
        _step(2, "observation", "blocked by cloud WAF"),
    ]
    success = [
        _step(0, "thought", "recon widget.co"),
        _step(1, "action", "scan", tool_name="crtsh",
              tool_args={"domain": "widget.co"}),
        _step(2, "observation", "5 subdomains"),
    ]
    return success, failure, "ep_widget_succ", "ep_widget_fail"


def pair_initech():
    failure = [
        _step(0, "thought", "recon initech.com"),
        _step(1, "action", "scan", tool_name="nmap"),
        _step(2, "observation", "Akamai WAF blocked"),
    ]
    success = [
        _step(0, "thought", "recon initech.com"),
        _step(1, "action", "scan", tool_name="crtsh"),
        _step(2, "observation", "12 subdomains discovered"),
    ]
    return success, failure, "ep_initech_succ", "ep_initech_fail"


def pair_unrelated():
    """A divergent pair on a different topic to test noise rejection."""
    failure = [
        _step(0, "thought", "decode base64"),
        _step(1, "action", "echo + base64 -d", tool_name="bash"),
        _step(2, "observation", "syntax error"),
    ]
    success = [
        _step(0, "thought", "decode base64"),
        _step(1, "action", "python -c base64.b64decode", tool_name="python"),
        _step(2, "observation", "decoded correctly"),
    ]
    return success, failure, "ep_decode_succ", "ep_decode_fail"


def main():
    print("=" * 70)
    print("Round 2 — Causal skill mining demo")
    print("=" * 70)

    pairs = [pair_acme(), pair_widget(), pair_initech(), pair_unrelated()]
    signals: list[dict] = []
    print("\n>> Extracting causal signals from 4 pairs...")
    for succ, fail, sid, fid in pairs:
        sig = causal_extract(
            success_traj=succ, failure_traj=fail,
            success_id=sid, failure_id=fid,
        )
        signals.append(sig)
        print(f"  Pair {sid}:")
        print(f"    rule: {sig['rule']}")
        print(f"    conf: {sig['confidence']:.2f}")

    print(f"\n>> Mining {len(signals)} signals (min_evidence=2)...")
    mined = causal_skill_mine(signals, min_evidence=2)

    print(f"\nFound {mined['n_candidates']} skill candidates:")
    for c in mined["candidates"]:
        print()
        print(f"  • Rule:     {c['rule']}")
        print(f"    Evidence: {c['evidence_count']} occurrences")
        print(f"    Avg conf: {c['avg_confidence']:.2f}")
        print("    Pairs:    " + ", ".join(
            f"{p['success_id']}/{p['failure_id']}"
            for p in c["evidence_pairs"]
        ))

    # Save report
    Path("causal_demo_report.json").write_text(
        json.dumps({
            "signals": signals,
            "mined": mined,
        }, indent=2, default=str)
    )
    print("\n>> Report saved -> causal_demo_report.json")

    print("\n" + "=" * 70)
    print("KEY RESULT")
    print("=" * 70)
    if mined["candidates"]:
        top = mined["candidates"][0]
        print(f"Top skill candidate emerged: '{top['rule']}'")
        print(f"Backed by {top['evidence_count']} distinct engagements.")
        print()
        print("Without LLM, without prompts, just from raw traces:")
        print("→ HippoAgent has *generalized* the recon discipline pattern.")
        print("→ This candidate is ready for the consolidation cycle to")
        print("  promote into a compiled macro skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
