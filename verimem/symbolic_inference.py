"""R8: Symbolic-neural bridge — cheap deductions on rule-shaped facts.

Some facts are *rules*: "if X then Y". HippoAgent now detects these
and chains them with state facts to deduce new propositions without
calling an LLM. Forward-chaining with depth limit (default 5).

Patterns detected:
  - "A -> B"
  - "A => B"
  - "If A then B"
  - "A implies B"
  - "When A, B"
  - "A → B"  (unicode arrow)

This is deliberately a SIMPLE module — not a Prolog interpreter. The
goal is fast common deductions (CVE chains, config invariants), not
arbitrary first-order logic. For complex inference, escalate to LLM.
"""
from __future__ import annotations

import re
from typing import Any

# Patterns ranked by specificity (try longer/more-specific first)
_RULE_PATTERNS = [
    re.compile(r"^\s*if\s+(.+?)\s+then\s+(.+)$", re.IGNORECASE),
    re.compile(r"^\s*when\s+(.+?)\s*,\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*(.+?)\s+implies\s+(.+)$", re.IGNORECASE),
    re.compile(r"^\s*(.+?)\s*=>\s*(.+)$"),
    re.compile(r"^\s*(.+?)\s*→\s*(.+)$"),
    re.compile(r"^\s*(.+?)\s*->\s*(.+)$"),
]


def parse_rule(proposition: str) -> dict[str, Any] | None:
    """Return {antecedent, consequent} if proposition is a rule."""
    if not proposition:
        return None
    for pat in _RULE_PATTERNS:
        m = pat.match(proposition.strip())
        if m:
            ant, con = m.group(1).strip(), m.group(2).strip()
            if ant and con:
                return {"antecedent": ant, "consequent": con}
    return None


# A negation token within this many chars BEFORE the antecedent match flips it.
_NEGATION_RE = re.compile(r"\b(?:not|no|non|never|without)\b[\w\s]{0,15}$")


def _antecedent_in_facts(antecedent: str, facts: list[Any]) -> Any | None:
    """Return the fact whose proposition contains the antecedent as a whole-word,
    non-negated match (case-insensitive).

    Whole-word (``\\b…\\b``) stops "cat" from matching "category"; the negation
    guard skips a match locally preceded by not/no/never/… so "service is NOT
    running" does not satisfy the antecedent "running" (both were unsound
    substring deductions before).
    """
    ant = antecedent.strip().lower()
    if not ant:
        return None
    pattern = re.compile(r"\b" + re.escape(ant) + r"\b")
    for f in facts:
        prop = (getattr(f, "proposition", "") or "").lower()
        for m in pattern.finditer(prop):
            if _NEGATION_RE.search(prop[: m.start()]):
                continue  # antecedent is locally negated -> not satisfied
            return f
    return None


def forward_chain(
    *,
    rules: list[Any],
    state_facts: list[Any],
    max_depth: int = 5,
) -> dict[str, Any]:
    """Forward-chain rules against state facts up to max_depth layers."""
    # Pre-parse rules
    parsed_rules: list[tuple[Any, dict[str, str]]] = []
    for r in rules:
        prop = getattr(r, "proposition", "") or ""
        parsed = parse_rule(prop)
        if parsed:
            parsed_rules.append((r, parsed))

    deductions: list[dict[str, Any]] = []
    # Build a "known" pool starting from state_facts. Deduced propositions
    # also added so multi-step chains can fire.
    known_pool: list[Any] = list(state_facts)
    fired_rules: set[str] = set()  # avoid re-firing same rule
    max_reached = 0

    for depth in range(1, max_depth + 1):
        new_deduced = False
        for rule, parts in parsed_rules:
            rule_id = getattr(rule, "id", "") or f"_anon_{id(rule)}"
            if rule_id in fired_rules:
                continue
            match = _antecedent_in_facts(parts["antecedent"], known_pool)
            if match is None:
                continue
            # New deduction
            deduction = {
                "proposition": parts["consequent"],
                "rule_id": rule_id,
                "depth": depth,
                "evidence_id": getattr(match, "id", ""),
            }
            deductions.append(deduction)
            fired_rules.add(rule_id)
            # Add as known for next-layer chaining

            class _Inferred:
                def __init__(self, prop, rid):
                    self.id = f"inferred_{rid}"
                    self.proposition = prop
                    self.topic = "inferred"
                    self.confidence = 0.8

            known_pool.append(_Inferred(parts["consequent"], rule_id))
            new_deduced = True
            max_reached = max(max_reached, depth)
        if not new_deduced:
            break

    return {
        "deductions": deductions,
        "n_rules": len(rules),
        "n_state": len(state_facts),
        "max_depth_reached": max_reached,
    }


__all__ = ["parse_rule", "forward_chain"]
