"""The data that trains the v3 judge does not copy the sentences of the gate that judges it.

The v3 judge is chosen and checked on the 112 matrix and on the G0 probes: a judge trained on those
sentences would pass them from memory. The plan wants the D1 templates disjoint from them, and a
declaration is not a proof. This file builds the D1 rows of every builder and asks
`d1_disgiunti.in_comune()` for the word 4-grams they share with every string literal of the gate
benches (`benchmark/moat_multilingual_matrix.py` and `docs/stato-reale/banchi/`, a superset of the G0
probes). No model and no store: the builders are templates, and the reference is read with `ast`.

A second builder joins with one line in BUILDERS, and is checked by the same function.

The dialogue builder runs at 600 dialogues per language, not at the 60 of the published file: the
number of distinct claims stops growing there (measured on 2026-09-29: 1019-1863 per language), so the
combinations of template and filler are covered, not just a sample of them.

The positive control: a row that repeats a 4-gram of the matrix must light the check up, otherwise an
empty answer would say nothing, because a blind instrument answers empty too.

    python -m pytest tests/test_i_dati_del_giudice_non_copiano_il_cancello.py -q -p no:randomly
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

JUDGE_V3 = Path(__file__).resolve().parents[1] / "benchmark" / "judge_v3"
sys.path.insert(0, str(JUDGE_V3))
import d1_dialoghi  # noqa: E402
import d1_disgiunti  # noqa: E402

SEME = 20260930
BUILDERS = {
    "dialoghi": lambda: d1_dialoghi.genera(600, SEME),
}


@pytest.fixture(scope="module")
def riferimento() -> dict:
    dove, stringhe = d1_disgiunti.riferimento(4)
    # an empty reference would make every builder disjoint: the benches must have been read
    assert stringhe > 10_000, stringhe
    assert any("moat_multilingual_matrix.py" in file for file in dove.values()), "the 112 matrix was not read"
    return dove


def test_una_riga_che_copia_il_cancello_accende_il_controllo(riferimento) -> None:
    della_matrice = sorted(g for g, file in riferimento.items() if "moat_multilingual_matrix.py" in file)
    copia = " ".join(della_matrice[0])
    riga = {"fonte": "", "memoria": "", "claim": f"Lena said that {copia} yesterday."}
    trovati = d1_disgiunti.in_comune([riga], 4, riferimento)
    assert della_matrice[0] in [g for g, _, _ in trovati], (della_matrice[0], trovati)


@pytest.mark.parametrize("builder", sorted(BUILDERS))
def test_i_dati_di_d1_non_copiano_il_cancello(riferimento, builder) -> None:
    righe = BUILDERS[builder]()
    assert righe, f"the builder {builder} wrote no rows"
    comuni = d1_disgiunti.in_comune(righe, 4, riferimento)
    assert not comuni, (f"{builder}: {len(comuni)} 4-grams shared with the gate benches, first ones: "
                        + "; ".join(f"{' '.join(g)!r} x{volte} {file[:2]}" for g, volte, file in comuni[:5]))
