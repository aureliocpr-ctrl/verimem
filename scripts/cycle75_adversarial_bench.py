"""Cycle #75 - Adversarial benchmark: sfido le mie regex empiricamente.

Goal: cercare di ROMPERE syntax_pollution. Non test sintetici banali,
ma casi al limite che potrebbero confondere detection o sanitize.
Output: report con falsi-positivi, falsi-negativi, performance.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from engram.semantic import SemanticMemory
from engram.syntax_pollution import (
    PollutionError,
    detect_xml_markup,
    is_polluted,
    sanitize_proposition,
    scan_facts,
    validate_proposition,
)

print("=" * 70)
print("CYCLE #75 ADVERSARIAL BENCHMARK")
print("=" * 70)
print()

# ---------------------------------------------------------------------------
# TEST 1 — Edge cases
# ---------------------------------------------------------------------------
print("[1] EDGE CASES")
print("-" * 70)

# Mark each case as (label, input, expected_polluted, expected_sanitize_short)
LT = "<"
GT = ">"
NEWLINE = "\n"

cases = [
    # (label, input, expected_is_polluted_True, expected_clean_starts_with)
    (
        "Backtick describes </proposition>",
        "Bug: il marker `" + LT + "/proposition" + GT + "` causa truncate",
        True,  # detection TRIGGERS — and sanitize WILL truncate it
        "Bug: il marker `",
    ),
    (
        "Multiple </proposition> anchors",
        "First " + LT + "/proposition" + GT + " mid " + LT + "/proposition" + GT + " last",
        True,
        "First",
    ),
    (
        "XML attribute con > letterale",
        'fact ' + LT + 'parameter name="x" cmp=">"' + GT + ' end',
        True,
        "fact",  # the regex matches up to first > so cuts mid-tag
    ),
    (
        "Newline-anchored </invoke> mid-content",
        "Real content" + NEWLINE + LT + "/invoke" + GT + " trailing payload",
        True,
        "Real content",
    ),
    (
        "Inline </invoke> WITHOUT newline (legit backtick form)",
        "Bug `" + LT + "/invoke" + GT + "` ricorrente",
        True,  # detection triggers (it's still XML markup)
        None,  # but sanitize should NOT cut — no anchor matches inline
    ),
    (
        "Empty proposition",
        "",
        False,
        None,
    ),
    (
        "Whitespace only",
        "   \n\t  ",
        False,
        None,
    ),
    (
        "Math expression x < y (no false positive)",
        "Bench shows x < y for 90% of cases",
        False,
        None,
    ),
    (
        "Markdown arrow -> (no false positive)",
        "step1 -> step2 -> step3",
        False,
        None,
    ),
    (
        "Unicode chinese + envelope",
        "中文 fact" + LT + "/proposition" + GT + LT + "parameter" + GT,
        True,
        "中文 fact",
    ),
    (
        "Very long proposition (5000 char) clean",
        "Real content. " * 350,
        False,
        None,
    ),
    (
        "Adversarial: case mixed",
        "TEXT </PROPOSITION>",  # uppercase variant
        True,  # regex is re.IGNORECASE
        "TEXT",
    ),
    (
        "Adversarial: extra spaces",
        "TEXT <  /  proposition  > end",  # spaces inside tag
        True,
        "TEXT",
    ),
    (
        "Trick: invoke as filename in path",
        "/path/to/invoke.py is a Python module",
        False,  # no < before invoke
        None,
    ),
    (
        "Trick: <param> not <parameter>",
        "URL: <param> in HTTP",
        False,  # we don't match <param>, only <parameter
        None,
    ),
    (
        "Trick: malformed but suggestive",
        "fact " + LT + "parameter without close",
        False,  # no > closing the tag → regex requires >
        None,
    ),
    (
        "Adversarial XSS-ish",
        "fact " + LT + "script" + GT + "alert(1)" + LT + "/script" + GT,
        False,  # we don't flag script tags
        None,
    ),
]

fp_count = 0
fn_count = 0
correct = 0
edge_fails = []

for label, inp, expected_pol, expected_starts in cases:
    actual_pol = is_polluted(inp)
    actual_clean = sanitize_proposition(inp)

    pol_ok = actual_pol == expected_pol
    if not pol_ok:
        if expected_pol:
            fn_count += 1
            edge_fails.append(f"  FN [{label}]: expected pollution=True got False")
        else:
            fp_count += 1
            edge_fails.append(f"  FP [{label}]: expected clean got pollution=True (markers={detect_xml_markup(inp)})")
    else:
        correct += 1

    # Optional sanitize check
    if expected_starts is not None and actual_pol:
        if not actual_clean.startswith(expected_starts):
            edge_fails.append(
                f"  SAN [{label}]: expected starts {expected_starts!r}, "
                f"got {actual_clean[:60]!r}"
            )

print(f"Detection correct: {correct}/{len(cases)}")
print(f"  False positives: {fp_count}")
print(f"  False negatives: {fn_count}")
if edge_fails:
    print("  Failures:")
    for f in edge_fails:
        print(f)
print()


# ---------------------------------------------------------------------------
# TEST 2 — Backtick legit content (the famous case 5e527bc230f5)
# ---------------------------------------------------------------------------
print("[2] BACKTICK LEGIT CONTENT — IS IT REALLY PRESERVED?")
print("-" * 70)
mem = SemanticMemory(db_path=Path(os.path.expanduser("~/.engram/semantic/semantic.db")))
facts = mem.list_facts(limit=10000, offset=0)
target = [f for f in facts if f.id == "5e527bc230f5"]
if target:
    t = target[0]
    print(f"Fact id: {t.id}")
    print(f"Full proposition ({len(t.proposition)} chars):")
    print(f"  {t.proposition[:250]}...")
    print(f"is_polluted: {is_polluted(t.proposition)}")
    print(f"sanitize would produce: {sanitize_proposition(t.proposition)[:250]!r}")
    print(f"Lengths: orig={len(t.proposition)}, sanitized={len(sanitize_proposition(t.proposition))}")
else:
    print("Fact 5e527bc230f5 NOT FOUND in live DB")
print()


# ---------------------------------------------------------------------------
# TEST 3 — Performance: scan_facts on 801 facts
# ---------------------------------------------------------------------------
print("[3] PERFORMANCE BENCH")
print("-" * 70)
# Cold
t0 = time.perf_counter()
result = scan_facts(facts)
t_cold = (time.perf_counter() - t0) * 1000
print(f"Cold scan: {t_cold:.1f}ms for {result['n_total']} facts")
# Warm avg
t0 = time.perf_counter()
for _ in range(5):
    scan_facts(facts)
t_warm = (time.perf_counter() - t0) * 1000 / 5
print(f"Warm avg:  {t_warm:.1f}ms (5 iter)")
print(f"Per-fact:  {1000*t_warm/result['n_total']:.2f}μs")
print()


# ---------------------------------------------------------------------------
# TEST 4 — FN search: facts NOT flagged but suspicious?
# ---------------------------------------------------------------------------
print("[4] FALSE NEGATIVE SEARCH — look for suspicious patterns NOT caught")
print("-" * 70)

# Pattern di sospetto NON coperti dalla mia regex
suspicious_patterns = [
    ("html_tag_generic", re.compile(r"<\s*[a-z]+\s+[^>]*?>", re.IGNORECASE)),
    ("xml_self_close", re.compile(r"<\s*[a-z]+\s*/>", re.IGNORECASE)),
    ("json_escape_artifact", re.compile(r'\\["\\nrt]')),
    ("placeholder_TBD", re.compile(r"\bTBD\b|\bTODO\b|\bFIXME\b", re.IGNORECASE)),
    ("very_short", re.compile(r"^.{0,20}$")),
    ("stub_rationale", re.compile(r"^Stub\s+rationale", re.IGNORECASE)),
    ("test_fixture_compute", re.compile(r"^Compute\s+\d", re.IGNORECASE)),
    ("only_punct", re.compile(r"^[\W_]+$")),
]

n_clean_facts = [f for f in facts if not is_polluted(f.proposition)]
print(f"Facts that pass L1: {len(n_clean_facts)}")
for name, pat in suspicious_patterns:
    hits = [f for f in n_clean_facts if pat.search(f.proposition or "")]
    print(f"  [{name}]: {len(hits)} facts match this suspicious pattern")
    for h in hits[:2]:
        print(f"    - id={h.id[:12]} {h.proposition[:70]!r}")
print()


# ---------------------------------------------------------------------------
# TEST 5 — Validate gate stress test
# ---------------------------------------------------------------------------
print("[5] GATE STRESS — validate_proposition with attack inputs")
print("-" * 70)
attack_inputs = [
    ("", "empty"),
    ("   ", "whitespace"),
    ("clean text", "should pass"),
    (LT + "/proposition" + GT, "only anchor"),
    ("a" + LT + "/proposition" + GT + "b", "anchor inside"),
    (NEWLINE + LT + "/invoke" + GT, "envelope start"),
    ("ok" + NEWLINE + LT + "parameter name=x" + GT + "v" + LT + "/parameter" + GT, "param envelope"),
]
for inp, label in attack_inputs:
    try:
        validate_proposition(inp)
        print(f"  PASS  [{label}]: {inp[:40]!r}")
    except PollutionError as e:
        print(f"  RAISE [{label}]: {e}")
print()

print("=" * 70)
print("BENCHMARK COMPLETE")
print("=" * 70)
