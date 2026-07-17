"""Round 6 demo — World model predicts outcome before acting.

Scenario: HippoAgent has 8 past episodes (mixed success/failure).
Agent proposes 3 candidate actions. World model predicts each
before any is executed:

  A) "exploit CVE-2023-6449 on WordPress" — past 3 successes →
     should predict ~90% success
  B) "aggressive nmap on cloudflare-protected target" — past 3
     failures → should predict failure + suggest passive enum
  C) "unknown novel action on unknown target" — no precedent →
     uncertain

Run: python scripts/world_model_demo.py
"""
from __future__ import annotations

from dataclasses import dataclass

from verimem.world_model import simulate_action


@dataclass
class Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


def build_past():
    return [
        # Success pattern: WordPress + CVE-2023-6449 RCE
        Ep("e1", "target acme.io WordPress 5.8 exploit CVE-2023-6449",
           outcome="success", final_answer="shell as www-data"),
        Ep("e2", "target widget.co WordPress 5.7 exploit CVE-2023-6449",
           outcome="success", final_answer="RCE via file_attachment"),
        Ep("e3", "target initech.com WordPress 5.9 exploit CVE-2023-6449",
           outcome="success", final_answer="foothold obtained"),

        # Failure pattern: aggressive nmap on cloudflare-protected
        Ep("e4", "target acme.io cloudflare aggressive nmap scan",
           outcome="failure", final_answer="IP banned"),
        Ep("e5", "target widget.co cloudflare aggressive nmap scan",
           outcome="failure", final_answer="WAF banned"),
        Ep("e6", "target initech.com cloudflare aggressive nmap scan",
           outcome="failure", final_answer="rate limited then banned"),

        # Success pattern alternative: passive crtsh on cloudflare
        Ep("e7", "target acme.io cloudflare passive crtsh enum",
           outcome="success", final_answer="5 subdomains found"),
        Ep("e8", "target widget.co cloudflare passive crtsh enum",
           outcome="success", final_answer="api-staging discovered"),
    ]


def main():
    print("=" * 70)
    print("Round 6 demo — World model (predict-before-act)")
    print("=" * 70)
    past = build_past()
    print(f"\nMemory: {len(past)} past episodes "
          f"({sum(1 for e in past if e.outcome == 'success')} success, "
          f"{sum(1 for e in past if e.outcome == 'failure')} failure)")

    proposals = [
        ("A — exploit (known pattern)",
         "target new.io WordPress 5.8",
         "exploit CVE-2023-6449"),
        ("B — aggressive nmap (failure pattern)",
         "target new.io cloudflare",
         "aggressive nmap scan"),
        ("C — novel territory",
         "embedded firmware ARM64",
         "fuzz with afl++"),
    ]

    for label, state, action in proposals:
        print(f"\n>> Proposal {label}")
        print(f"   state:  {state}")
        print(f"   action: {action}")
        out = simulate_action(
            state=state, action=action, past_episodes=past,
        )
        print(f"   PREDICTION: p_success={out['p_success']:.2f}  "
              f"p_failure={out['p_failure']:.2f}  "
              f"confidence={out['confidence']}")
        print(f"   evidence:    {out['n_similar']} similar episodes")
        print(f"   rationale:   {out['rationale']}")
        if out["alternative"]:
            print("   ⚠ ALTERNATIVE SUGGESTED:")
            print(f"     → {out['alternative'][:80]}")

    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print("HippoAgent no longer reacts — it *anticipates*.")
    print()
    print("Proposal A (exploit) → high p_success → execute confidently")
    print("Proposal B (nmap)    → low p_success → AGENT REROUTES to passive")
    print("Proposal C (novel)   → uncertain → escalate to human / search web")
    print()
    print("This closes the loop: trajectory → causal → world model → planning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
