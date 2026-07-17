"""R9: Hierarchical schema abstraction — find cross-domain patterns.

When multiple skills across different domains follow the same RULE
TEMPLATE, HippoAgent abstracts them into a single "schema" — a
generalisable pattern transferable to new domains.

Approach: word-level template extraction. Find substrings that are
constant across multiple skill bodies; the variable parts become
slots.

Example inputs:
  "Prefer `crtsh` over `nmap` in this context"
  "Prefer `tsc-strict` over `tsc-loose` in this context"
  "Prefer `snapshot-svc` over `event-log` in this context"

Extracted template:
  "Prefer `<slot1>` over `<slot2>` in this context"

This realises the "schema" stage of skills (skill.stage="schema")
that has been a placeholder until now.
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+|[`\"'\[\]\(\)]+|\W")


def _tokenize(s: str) -> list[str]:
    """Tokenize keeping all characters including punctuation."""
    return s.split()


def _common_template(strings: list[str]) -> str | None:
    """Find a word-level template common to all input strings.

    Strategy: position-aligned (assumes similar word count). For each
    word position, if all strings have the same token → keep it;
    else → replace with `<slotN>`. If less than 50% positions match,
    return None.
    """
    if not strings or len(strings) < 2:
        return None
    tokenised = [_tokenize(s) for s in strings]
    min_len = min(len(t) for t in tokenised)
    if min_len < 2:
        return None
    template_tokens: list[str] = []
    n_match = 0
    slot_idx = 0
    for i in range(min_len):
        toks = {t[i] for t in tokenised}
        if len(toks) == 1:
            template_tokens.append(next(iter(toks)))
            n_match += 1
        else:
            slot_idx += 1
            template_tokens.append(f"<slot{slot_idx}>")
    # Require at least 40% positions to match
    if n_match / min_len < 0.4:
        return None
    if slot_idx == 0:
        return None  # all identical → not really a template
    return " ".join(template_tokens)


def extract_template(rules: list[str]) -> dict[str, Any] | None:
    """Try to extract a common template from a list of rule strings."""
    if not rules or len(rules) < 2:
        return None
    template = _common_template(rules)
    if template is None:
        return None
    return {
        "template": template,
        "instances": list(rules),
        "n_instances": len(rules),
    }


def find_cross_domain_schemas(
    skills: list[Any],
    *,
    min_instances: int = 2,
    top_k: int = 30,
) -> dict[str, Any]:
    """Cluster skill bodies by shared template, return schemas."""
    # Group skills by first-token bucket (proxy for shared rule pattern)
    bodies = [
        (getattr(s, "id", ""), getattr(s, "body", "") or "")
        for s in skills
        if getattr(s, "body", "")
    ]
    if not bodies:
        return {"schemas": [], "n_schemas": 0, "n_skills_scanned": len(skills)}

    # Bucket by first word + total token count (signature for pattern)
    buckets: dict[str, list[tuple[str, str]]] = {}
    for sid, body in bodies:
        toks = _tokenize(body)
        if len(toks) < 2:
            continue
        # First word + length bucket → groups same-shaped sentences
        key = f"{toks[0].lower()}_len{len(toks)}"
        buckets.setdefault(key, []).append((sid, body))

    schemas: list[dict[str, Any]] = []
    for key, group in buckets.items():
        if len(group) < min_instances:
            continue
        rule_strings = [g[1] for g in group]
        tpl = extract_template(rule_strings)
        if tpl is None:
            continue
        schemas.append({
            "template": tpl["template"],
            "n_instances": tpl["n_instances"],
            "instance_skill_ids": [g[0] for g in group],
            "example_instances": rule_strings[:3],
        })

    schemas.sort(key=lambda s: -s["n_instances"])

    return {
        "schemas": schemas[:top_k],
        "n_schemas": len(schemas),
        "n_skills_scanned": len(skills),
    }


__all__ = ["extract_template", "find_cross_domain_schemas"]
