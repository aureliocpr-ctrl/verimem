"""TDD for precision-first derivation auto-detection (R27 step 2).

The tests that matter are the PRECISION ones: a paraphrase, a short coincidental overlap, a
superseded parent, or a partial quote must NOT create an edge (a false edge = false cascade).
"""
from __future__ import annotations

from verimem.derivation_detect import detect_derivations


def _f(i, prop, superseded_by=None):
    return {"id": i, "proposition": prop, "superseded_by": superseded_by}


_LONG = "the rerank stage caps the per-query wait to forty milliseconds on cpu"  # 67 chars
CORPUS = [
    _f("aaaaaaaaaaaa", _LONG),
    _f("bbbbbbbbbbbb", "short fact"),                       # < 40 chars
    _f("cccccccccccc", "an unrelated belief about caches"),
]


def test_links_on_explicit_id_mention() -> None:
    src = "Derived from prior finding bbbbbbbbbbbb about the store."
    assert detect_derivations(src, CORPUS) == ["bbbbbbbbbbbb"]


def test_containment_off_by_default() -> None:
    # R27 step2: containment over-links 38% on the real corpus -> OFF unless opted in.
    src = f"Building on the fact that {_LONG}, we conclude the cold path is fixed."
    assert detect_derivations(src, CORPUS) == []                          # default: no link
    assert detect_derivations(src, CORPUS, use_containment=True) == ["aaaaaaaaaaaa"]


def test_does_not_link_on_paraphrase() -> None:
    # semantically identical, lexically different -> MUST NOT link (no fuzzy matching)
    src = "The reranking step limits each query's delay to 40 ms on the processor."
    assert detect_derivations(src, CORPUS, use_containment=True) == []


def test_does_not_link_on_short_coincidental_overlap() -> None:
    src = "this is a short fact and nothing more"   # contains 'short fact' but < 40 chars
    assert detect_derivations(src, CORPUS, use_containment=True) == []


def test_does_not_link_on_partial_quote() -> None:
    # only a PREFIX of the long proposition appears -> not a full restatement -> no link
    src = "the rerank stage caps the per-query wait to ... (truncated)"
    assert detect_derivations(src, CORPUS, use_containment=True) == []


def test_excludes_superseded_parent() -> None:
    corpus = [_f("dddddddddddd", _LONG, superseded_by="eeeeeeeeeeee")]
    src = f"based on {_LONG}"
    assert detect_derivations(src, corpus, use_containment=True) == []


def test_excludes_self_id() -> None:
    src = "self-reference aaaaaaaaaaaa should be ignored"
    assert detect_derivations(src, CORPUS, exclude_id="aaaaaaaaaaaa") == []


def test_empty_source_links_nothing() -> None:
    assert detect_derivations("", CORPUS) == []
    assert detect_derivations(None, CORPUS) == []  # type: ignore[arg-type]


def test_normalisation_tolerates_whitespace_and_case() -> None:
    src = f"BUILDING ON: {_LONG.upper().replace(' ', '   ')} -- done"
    assert detect_derivations(src, CORPUS, use_containment=True) == ["aaaaaaaaaaaa"]
