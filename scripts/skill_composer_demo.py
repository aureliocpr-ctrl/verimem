"""Round 10 demo — Skill Composer auto-generates attack chain.

Library of 6 pentest skills with parent_skills dependencies.
Input: new task "WordPress contact-form-7 RCE acme.io".
Output: full ordered attack chain auto-planned.

Run: python scripts/skill_composer_demo.py
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engram.skill_composer import compose_plan


@dataclass
class Skill:
    id: str
    trigger: str
    body: str = ""
    parent_skills: list[str] = field(default_factory=list)
    status: str = "promoted"
    fitness_mean: float = 0.85
    trials: int = 10


def build_library():
    """Realistic pentest skill library with deps."""
    return [
        Skill("passive-recon",
              "passive subdomain enumeration target domain",
              body="crtsh + dnsdumpster + waybackurls"),
        Skill("wp-fingerprint",
              "WordPress version plugin detection",
              body="wpscan --enumerate vp",
              parent_skills=["passive-recon"]),
        Skill("cf7-vuln-check",
              "contact-form-7 plugin vulnerability check",
              body="check plugin version vs CVE list",
              parent_skills=["wp-fingerprint"]),
        Skill("cf7-rce-exploit",
              "contact-form-7 CVE-2023-6449 RCE exploit",
              body="POST malicious file_attachment",
              parent_skills=["cf7-vuln-check"]),
        Skill("post-exploit-setup",
              "post-exploitation foothold reverse shell",
              body="upload webshell + callback",
              parent_skills=["cf7-rce-exploit"]),
        # Distractors
        Skill("nmap-scan",
              "active port scan with nmap",
              body="nmap -sS -p- target"),
        Skill("sqlmap-test",
              "SQL injection automation",
              body="sqlmap on params"),
        Skill("retired-old",
              "WordPress old plugin",
              body="legacy",
              status="retired"),
    ]


def main():
    print("=" * 70)
    print("Round 10 — Skill Composer: auto-plan attack chain")
    print("=" * 70)

    library = build_library()
    print(f"\nLibrary: {len(library)} skills "
          f"({sum(1 for s in library if s.status == 'promoted')} promoted, "
          f"{sum(1 for s in library if s.status == 'retired')} retired)")

    tasks = [
        "WordPress contact-form-7 RCE on acme.io target",
        "SQL injection assessment on /api/v1/users",
        "Embedded firmware buffer overflow on STM32",
    ]

    for task in tasks:
        print(f"\n>> Task: '{task}'")
        out = compose_plan(task=task, skills=library)
        print(f"   {out['n_skills_matched']} matched, "
              f"coverage={out['coverage']:.2f}, plan {len(out['plan'])} steps")
        if not out["plan"]:
            print("   (no skills matched — task is novel)")
            continue
        for i, step in enumerate(out["plan"], 1):
            marker = "▶" if step["role"] == "matched" else "│"
            score = (f"[score={step['match_score']:.2f}]"
                     if step["role"] == "matched"
                     else "[parent]")
            print(f"   {i}. {marker} {step['skill_id']:<22s} "
                  f"{score:<18s} {step['trigger'][:50]}")

    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print("Given a new task, HippoAgent now auto-generates an execution plan")
    print("by chaining skills along their parent dependencies.")
    print()
    print("Task 1 → 5-step chain (recon → fingerprint → vuln → exploit → post)")
    print("Task 2 → 1 standalone skill (sqlmap)")
    print("Task 3 → empty (novel: escalate to LLM or human)")
    print()
    print("Combined with R6 world model: agent can simulate EACH step")
    print("of the proposed plan BEFORE executing → safer engagements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
