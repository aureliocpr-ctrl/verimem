"""Security regression (opus CodeQL triage 2026-07-18, alerts [26] & [29]).

Two regexes ran on ``fact.proposition`` FULL-LENGTH (documented up to 64KB, NOT
capped by the L1 8192 gate), both with super-linear backtracking:

* [26] ``quantity_match._QUANT_RE`` — two adjacent ``\\s*`` → quadratic on a
  number followed by a long run of spaces. Measured 27.9s on 40k spaces.
* [29] ``entity_extract_lite._is_sentence_initial`` — ``.search(text[:start])``
  re-scanned the whole growing prefix for every entity match → O(n²).

A hostile multi-tenant caller could stall the server per fact. The fixes bound
the work; these tests fail (time out) on the pre-fix code and pass after.
"""
import time

from verimem.entity_extract_lite import extract_entities_lite
from verimem.quantity_match import extract_quantities

_BUDGET_S = 1.0  # generous: fixed forms run in single-digit ms


def test_quantity_extract_is_redos_safe() -> None:
    patho = "5" + " " * 60000 + "!"
    t0 = time.perf_counter()
    extract_quantities(patho)
    dt = time.perf_counter() - t0
    assert dt < _BUDGET_S, f"quantity ReDoS not fixed: {dt:.2f}s on 60k spaces"


def test_quantity_extract_correctness_preserved() -> None:
    q = extract_quantities("peso 5 kg, distanza 10-km, prezzo 5 - kg")
    assert ("kg", 5.0) in q
    assert ("km", 10.0) in q


def test_entity_extract_is_redos_safe() -> None:
    patho = "\n" * 40000 + " Roma Milano"
    t0 = time.perf_counter()
    extract_entities_lite(patho)
    dt = time.perf_counter() - t0
    assert dt < _BUDGET_S, f"entity ReDoS not fixed: {dt:.2f}s on 40k newlines"


def test_entity_extract_correctness_preserved() -> None:
    names = [x["name"] for x in extract_entities_lite("Mario Rossi lavora a Milano.")]
    assert "Mario Rossi" in names
    assert "Milano" in names
