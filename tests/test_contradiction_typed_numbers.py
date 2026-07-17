"""Cycle #123 (2026-05-17) — Type-aware number classification in _values_clash.

Aurelio direttiva: "studiamo confabulazioni come prevenirle in memoria".
Lab 2026-05-17 (subagent #2 code-review su contradiction.py): bug
verified empiricamente da analisi e linea-citation a `contradiction.py:
117-131`.

**Bug pattern**: `_values_clash` confronta numeri PER POSIZIONE senza
type classification. Conseguenza:
* "Tasso 5% nel 2024"   -> `_extract_numbers` -> [5.0, 2024.0]
* "2024 tasso 5%"       -> `_extract_numbers` -> [2024.0, 5.0]

Pairwise position 0: 5 vs 2024 -> abs(5-2024)/2024 = 0.997 > 0.05 ->
CLASH falso positive. Il contraddictor segnala un mismatch che non
esiste: i due fatti dicono LA STESSA COSA in ordine diverso.

Fix: classifica i numeri estratti per tipo (year | percent | count) via
regex contestuale. Confronto tra valori dello STESSO tipo, non per
posizione assoluta nella string.

Test plan TDD:
1. RED: "Tasso 5% nel 2024" vs "2024 tasso 5%" -> NO clash (stessa info)
2. RED: "Crescita 5% nel 2024" vs "Crescita 10% nel 2024" -> CLASH (% diverso)
3. RED: "Misura 100 nel 2024" vs "Misura 200 nel 2024" -> CLASH (count diverso)
4. GREEN dopo introdurre `_classify_numbers` + type-aware compare.
"""
from __future__ import annotations

import pytest

from verimem.contradiction import _extract_numbers, _values_clash


class TestTypedNumberClassification:
    """RED tests for cycle #123 — type-aware comparison."""

    def test_order_independence_year_percent(self) -> None:
        """Reordering year and percent must NOT produce a clash.

        BEFORE cycle #123 fix: positional compare 5 vs 2024 = clash.
        AFTER cycle #123 fix: 5% maps to %, 2024 maps to year — no
        cross-type mismatch — no clash."""
        a_vals = _extract_numbers("Tasso 5% nel 2024")
        b_vals = _extract_numbers("2024 tasso 5%")
        # Pre-fix: positional compare [5, 2024] vs [2024, 5] flags clash.
        # Post-fix: type-aware compare matches 5%↔5%, 2024↔2024.
        assert not _values_clash(
            a_vals, b_vals,
            tolerance=0.05,
            text_a="Tasso 5% nel 2024",
            text_b="2024 tasso 5%",
        ), (
            "Cycle #123: order-independent reformulation must NOT "
            "produce a clash. Pre-fix positional compare gives false "
            "positive 5 vs 2024."
        )

    def test_real_percent_clash_within_same_year(self) -> None:
        """Same year, different percent — must clash."""
        a_vals = _extract_numbers("Crescita 5% nel 2024")
        b_vals = _extract_numbers("Crescita 10% nel 2024")
        assert _values_clash(
            a_vals, b_vals,
            tolerance=0.05,
            text_a="Crescita 5% nel 2024",
            text_b="Crescita 10% nel 2024",
        ), (
            "Cycle #123: real disagreement on percent must still clash."
        )

    def test_real_count_clash_within_same_year(self) -> None:
        """Same year, different count — must clash."""
        a_vals = _extract_numbers("Misura 100 nel 2024")
        b_vals = _extract_numbers("Misura 200 nel 2024")
        assert _values_clash(
            a_vals, b_vals,
            tolerance=0.05,
            text_a="Misura 100 nel 2024",
            text_b="Misura 200 nel 2024",
        ), (
            "Cycle #123: count disagreement must clash."
        )

    def test_no_clash_when_no_numbers(self) -> None:
        """Defensive — empty number lists never clash."""
        assert not _values_clash(
            [], [], tolerance=0.05, text_a="", text_b="",
        )

    def test_backward_compat_no_kwargs(self) -> None:
        """Cycle #123 must NOT break legacy callers that pass only
        (a_vals, b_vals, tolerance=...). The new text_a/text_b kwargs
        must be optional with sane defaults."""
        # Without context (text=""), the classifier falls back to
        # positional compare. This is the pre-cycle-123 behaviour.
        a_vals = [5.0, 2024.0]
        b_vals = [10.0, 2024.0]
        assert _values_clash(a_vals, b_vals, tolerance=0.05), (
            "Backward compat: legacy positional compare must still flag "
            "[5,2024] vs [10,2024] as clash at position 0."
        )
