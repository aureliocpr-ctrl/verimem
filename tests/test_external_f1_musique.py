"""Pure-function tests for the MuSiQue F1 harness (task #22).

Only the judge-free/model-free logic: gold extraction, hop counting, the
multi-hop-honest all_hops@k metric, and stratified sampling. The end-to-end
ingest+recall path is verified empirically by the sanity run (it needs the
embedding model, out of scope for a unit test).
"""
from __future__ import annotations

from benchmark.external_f1_musique import (
    all_hops_at_k,
    gold_idxs,
    load_musique,
    n_hops,
    paragraph_to_text,
)


def _item(ident="2hop__1_2", supporting=(1, 2), n_para=5, decomp=2):
    paras = [{"idx": i, "title": f"T{i}", "paragraph_text": f"body {i}",
              "is_supporting": i in supporting} for i in range(n_para)]
    return {"id": ident, "paragraphs": paras,
            "question": "q?", "answer": "a",
            "question_decomposition": [{}] * decomp}


def test_gold_idxs_are_supporting_only_as_str():
    assert gold_idxs(_item(supporting=(1, 3))) == ["1", "3"]


def test_gold_idxs_empty_when_none_supporting():
    assert gold_idxs(_item(supporting=())) == []


def test_n_hops_from_id_prefix():
    assert n_hops(_item(ident="3hop__9_8_7")) == 3
    assert n_hops(_item(ident="4hop__a_b_c_d")) == 4


def test_n_hops_falls_back_to_decomposition():
    assert n_hops({"id": "weird", "question_decomposition": [{}, {}, {}]}) == 3


def test_all_hops_requires_every_gold():
    # gold {1,2}: both present -> 1.0
    assert all_hops_at_k(["1", "2", "9"], ["1", "2"], k=3) == 1.0
    # only one hop present -> 0.0 (the multi-hop-honest part)
    assert all_hops_at_k(["1", "9", "8"], ["1", "2"], k=3) == 0.0
    # both present but the second is beyond k -> 0.0
    assert all_hops_at_k(["1", "9", "2"], ["1", "2"], k=2) == 0.0


def test_all_hops_none_when_no_gold():
    assert all_hops_at_k(["1"], [], k=3) is None


def test_paragraph_to_text_keeps_title():
    p = {"title": "Green", "paragraph_text": "is an album."}
    assert paragraph_to_text(p) == "Green. is an album."
    assert paragraph_to_text({"title": "", "paragraph_text": "x"}) == "x"


def test_load_musique_stratifies_by_hop(tmp_path):
    import json
    items = ([_item(ident="2hop__a", decomp=2)] * 10
             + [_item(ident="3hop__b", decomp=3)] * 4
             + [_item(ident="4hop__c", decomp=4)] * 2)
    p = tmp_path / "d.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in items), encoding="utf-8")
    picked = load_musique(p, sample=6, seed=1)
    hops = {n_hops(x) for x in picked}
    # all three strata represented despite 2-hop being the majority
    assert hops == {2, 3, 4}
    assert len(picked) <= 6


def test_load_musique_returns_all_when_sample_none(tmp_path):
    import json
    items = [_item(ident="2hop__a")] * 3
    p = tmp_path / "d.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in items), encoding="utf-8")
    assert len(load_musique(p, sample=None)) == 3
