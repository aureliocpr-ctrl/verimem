"""D1 for the v3 judge, the NON-dialogue half: sources are documents (contracts, records, sheets, logs).

The cells:
1. the rows pass the same field check as the dialogue half (`d1_campi.controlla`);
2. every language has every pair type, and both whole and split memories;
3. the labels hold by construction on single-unit rows: the changed value, the swapped entity and the
   added detail are NOT in the source, the supported value IS;
4. deterministic with the seed.

That the rows do not copy the gate benches is checked for every builder in ONE place,
`tests/test_i_dati_del_giudice_non_copiano_il_cancello.py`, where this builder is a line of BUILDERS.

No model: `decomponi()` is pure.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

CARTELLA = Path(__file__).resolve().parents[1] / "benchmark" / "judge_v3"
sys.path.insert(0, str(CARTELLA))

LINGUE = {"en", "it", "fr", "es"}
TIPI_SOSTENUTI = {"sostenuta", "parafrasi"}
TIPI_NEGATIVI = {"valore", "entita", "negazione", "portata", "tempo", "omissione"}


def _righe(seme: int = 20260930, per_lingua: int = 6) -> list[dict]:
    import d1_fonti

    return d1_fonti.genera(seme=seme, per_lingua=per_lingua)


def test_the_rows_pass_the_field_check_of_every_d1_builder() -> None:
    import d1_campi

    righe = _righe()
    # POSITIVE CONTROL: an empty list would pass the check without checking anything
    assert len(righe) >= 100, len(righe)
    d1_campi.controlla(righe)


def test_every_language_has_every_pair_type_and_both_memory_shapes() -> None:
    righe = _righe()
    for lingua in LINGUE:
        sue = [r for r in righe if r["lingua"] == lingua]
        tipi = {r["tipo"] for r in sue}
        assert TIPI_SOSTENUTI | TIPI_NEGATIVI <= tipi, (lingua, sorted(tipi))
        forme = Counter(r["unita_nella_memoria"] > 1 for r in sue)
        assert forme[True] and forme[False], (lingua, forme)
    for r in righe:
        atteso = 1 if r["tipo"] in TIPI_SOSTENUTI else 0
        assert r["etichetta"] == atteso, (r["id"], r["tipo"], r["etichetta"])


def test_the_labels_hold_by_construction_on_single_unit_rows() -> None:
    righe = [r for r in _righe() if r["unita_nella_memoria"] == 1]
    assert righe
    for r in righe:
        segno, fonte = r["segno"].lower(), r["fonte"].lower()
        # the mark is always IN the claim: a mark that is not there proves nothing about the label
        assert segno in r["claim"].lower(), (r["id"], r["segno"], r["claim"])
        if r["tipo"] in TIPI_SOSTENUTI:
            assert segno in fonte, (r["id"], "a supported value missing from the source")
        else:
            assert segno not in fonte, (r["id"], r["tipo"], "the negative's mark is in the source")


def test_the_same_seed_gives_the_same_rows_and_another_seed_does_not() -> None:
    a, b, c = _righe(seme=7), _righe(seme=7), _righe(seme=8)
    assert json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
    assert json.dumps(a, ensure_ascii=False) != json.dumps(c, ensure_ascii=False)


def test_every_source_claim_pair_is_written_once() -> None:
    # the judge reads (source, claim): a pair written twice weighs twice and bends the proportions
    # we declare. Found by Nadia on 2026-09-30 (960 repeated pairs out of 4320 rows in d1_fonti@1)
    righe = _righe(per_lingua=60)
    conta = Counter((r["fonte"], r["claim"]) for r in righe)
    ripetute = {k: v for k, v in conta.items() if v > 1}
    assert not ripetute, (len(ripetute), sum(v - 1 for v in ripetute.values()), next(iter(ripetute)))


def test_the_sources_read_as_their_language() -> None:
    # found by reading the sample (Nadia, 2026-09-30): «1 months», «1 meses», «a Anna»
    fonti = {r["fonte"] for r in _righe(per_lingua=60)}
    sbagliate = [f for f in fonti if re.search(r"\b1 months\b|\b1 meses\b|\ba A", f)]
    assert not sbagliate, (len(sbagliate), sbagliate[:3])
