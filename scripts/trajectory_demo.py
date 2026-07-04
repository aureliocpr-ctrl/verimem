"""R1.6: Real-world trajectory demo.

Scenario: pentest agent recon su target hipotetico.
- Trajectory A (failure path): aggressive nmap → WAF banna → fail
- Trajectory B (success path): stealth nmap → no detect → exploit

Output:
  1. Render markdown di entrambe
  2. Diff con punto di divergenza
  3. Fork dell'A da step di divergenza → counterfactual seed
  4. Summary one-line

Run: python scripts/trajectory_demo.py
"""
from __future__ import annotations

import json
import time

from engram.trajectory import (
    TrajectoryStep,
    trajectory_to_json,
)
from engram.trajectory_diff import trajectory_diff
from engram.trajectory_fork import trajectory_fork
from engram.trajectory_render import (
    trajectory_summary_line,
    trajectory_to_markdown,
)

now = time.time()


def make_failure_trajectory() -> list[TrajectoryStep]:
    """Agent tries aggressive recon, gets WAF-banned, fails."""
    return [
        TrajectoryStep(
            step_idx=0, kind="thought", timestamp=now,
            content="Target acme.io — start recon to map attack surface",
        ),
        TrajectoryStep(
            step_idx=1, kind="action", timestamp=now + 1,
            content="Aggressive nmap full scan",
            tool_name="nmap",
            tool_args={"target": "acme.io", "flags": "-A -T4 --top-ports 1000"},
            tool_result="80/tcp open http (cloudflare-nginx)\n443/tcp open https",
        ),
        TrajectoryStep(
            step_idx=2, kind="observation", timestamp=now + 30,
            content="Cloudflare WAF detected upstream",
        ),
        TrajectoryStep(
            step_idx=3, kind="action", timestamp=now + 31,
            content="Try sqlmap direct injection on /api/v1/users",
            tool_name="sqlmap",
            tool_args={"url": "https://acme.io/api/v1/users?id=1"},
            tool_result="HTTP 403 — request blocked by Cloudflare",
        ),
        TrajectoryStep(
            step_idx=4, kind="observation", timestamp=now + 35,
            content="IP banned. Engagement compromised.",
        ),
    ]


def make_success_trajectory() -> list[TrajectoryStep]:
    """Agent uses stealth recon, finds OSS plugin vuln, succeeds."""
    return [
        TrajectoryStep(
            step_idx=0, kind="thought", timestamp=now,
            content="Target acme.io — start recon to map attack surface",
        ),
        TrajectoryStep(
            step_idx=1, kind="action", timestamp=now + 1,
            content="Passive subdomain enumeration via crt.sh",
            tool_name="crtsh",
            tool_args={"domain": "acme.io"},
            tool_result="api-staging.acme.io\ndev.acme.io\ncms.acme.io",
        ),
        TrajectoryStep(
            step_idx=2, kind="observation", timestamp=now + 10,
            content="cms.acme.io discovered — likely WordPress, no WAF",
        ),
        TrajectoryStep(
            step_idx=3, kind="action", timestamp=now + 11,
            content="Fingerprint WordPress version + plugins",
            tool_name="wpscan",
            tool_args={"url": "https://cms.acme.io"},
            tool_result="WordPress 5.8.2\nplugin: contact-form-7 5.7.3",
            branch_id="stealth-path",
        ),
        TrajectoryStep(
            step_idx=4, kind="decision", timestamp=now + 15,
            content="CF7 5.7.3 vulnerable to CVE-2023-6449 (RCE)",
            branch_id="stealth-path",
        ),
        TrajectoryStep(
            step_idx=5, kind="action", timestamp=now + 16,
            content="Exploit CVE-2023-6449",
            tool_name="exploit",
            tool_args={"cve": "CVE-2023-6449", "target": "https://cms.acme.io"},
            tool_result="Shell obtained: www-data@cms",
            branch_id="stealth-path",
        ),
        TrajectoryStep(
            step_idx=6, kind="observation", timestamp=now + 18,
            content="Foothold established. Engagement successful.",
        ),
    ]


def main():
    print("=" * 70)
    print("Round 1.6 — Trajectory real-world demo")
    print("=" * 70)

    failure = make_failure_trajectory()
    success = make_success_trajectory()

    # 1. Summary one-liner
    print("\n>> Summary lines:")
    print(f"  Failure: {trajectory_summary_line(failure)}")
    print(f"  Success: {trajectory_summary_line(success)}")

    # 2. Diff (what was the discriminating step?)
    print("\n>> Diff failure vs success:")
    diff = trajectory_diff(failure, success)
    print(f"  {diff['summary']}")
    print(f"  Divergence at step {diff['first_divergence']}")
    if diff["step_a"]:
        print(f"    FAILURE took: {diff['step_a']['content'][:80]}")
        if diff["step_a"].get("tool_name"):
            print(f"      tool: {diff['step_a']['tool_name']}")
    if diff["step_b"]:
        print(f"    SUCCESS took: {diff['step_b']['content'][:80]}")
        if diff["step_b"].get("tool_name"):
            print(f"      tool: {diff['step_b']['tool_name']}")

    # 3. Fork the failure at divergence point with success's choice
    print("\n>> Fork failure at divergence, seed with success's step:")
    cf_seed = TrajectoryStep.from_dict(diff["step_b"])
    forked = trajectory_fork(failure, from_step=diff["first_divergence"],
                             counterfactual_seed=cf_seed)
    print(f"  fork_id={forked['fork_id']}")
    print(f"  preserved {len(forked['preserved'])} steps (replay would "
          f"continue from step {forked['branch_point']} with the success path)")

    # 4. Render: print only first 20 lines of each markdown
    print("\n>> Markdown render (failure, head):")
    md_failure = trajectory_to_markdown(failure, max_tool_result_chars=80)
    for line in md_failure.splitlines()[:15]:
        print(f"  | {line}")
    print(f"  | ... ({len(md_failure.splitlines())} total lines)")

    # 5. Save JSON for re-ingestion
    out = {
        "failure": json.loads(trajectory_to_json(failure)),
        "success": json.loads(trajectory_to_json(success)),
        "diff": diff,
        "fork": {
            "fork_id": forked["fork_id"],
            "branch_point": forked["branch_point"],
            "n_preserved": len(forked["preserved"]),
        },
    }
    from pathlib import Path
    Path("trajectory_demo_report.json").write_text(
        json.dumps(out, indent=2, default=str)
    )
    print("\n>> Report saved -> trajectory_demo_report.json")

    # The KEY INSIGHT: discriminating step = causal point
    print("\n" + "=" * 70)
    print("CAUSAL INSIGHT")
    print("=" * 70)
    print("The failure diverged from success at step 1:")
    print("  → FAILURE used aggressive nmap (triggered WAF)")
    print("  → SUCCESS used passive crt.sh enumeration")
    print()
    print("This is the *causal* finding that Round 2 will use to")
    print("auto-extract a skill 'use passive recon when WAF suspected'.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
