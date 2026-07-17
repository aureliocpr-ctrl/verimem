"""Deterministic, zero-API entity extractor (entity-live, step 1).

The PPR engine (entity_kg.py, 28 tests) is built-not-live: nothing
populates it from the real corpus because the only extractor
(openie.py) requires an LLM. This extractor is the LLM-free tier that
makes the graph REAL today on the actual corpus — technical facts full
of code identifiers, commit SHAs, acronyms and proper nouns.

Expectations below come from REAL corpus facts (sampled 2026-06-10),
not invented examples.
"""
from __future__ import annotations

from verimem.entity_extract_lite import extract_entities_lite


def _names(text: str) -> set[str]:
    return {e["name"] for e in extract_entities_lite(text)}


def test_real_fact_code_identifiers_and_sha():
    # Real fact 2026-06-10 (#316 closure), abridged.
    text = (
        "ENGRAM #316 CHIUSO 2026-06-10 (commit ff1bb0f pushato, critic "
        "claim_holds 2-0-1): branch causale community_detector FUNZIONA - "
        "proiezione episode->fact via source_episodes (parsing "
        "comma-separated, fanout cap 32)"
    )
    names = _names(text)
    assert "community_detector" in names, names
    assert "source_episodes" in names, names
    assert "ff1bb0f" in names, names


def test_real_fact_proper_nouns_and_tech_tokens():
    text = (
        "Bench FAIR n=120 parafrasi fluenti su LongMemEval validato con "
        "McNemar: mem0 2.0.4 converge ai numeri vanilla; engram resta "
        "davanti con il reranker guardato"
    )
    names = _names(text)
    assert "LongMemEval" in names, names
    assert "McNemar" in names, names
    assert "mem0" in names, names


def test_paths_and_dotted_modules():
    text = (
        "il fix vive in engram/semantic.py e il registry in "
        "verimem.provider_registry mentre benchmark/comparative_retrieval.py "
        "ha i 3 bracci"
    )
    names = _names(text)
    assert "engram/semantic.py" in names, names
    assert "verimem.provider_registry" in names, names
    assert "benchmark/comparative_retrieval.py" in names, names


def test_acronyms_extracted_stopwords_not():
    text = (
        "Il gate MCP usa PPR e TDD. La CI resta verde. Per questo non "
        "cambia nulla."
    )
    names = _names(text)
    assert {"MCP", "PPR", "TDD", "CI"} <= names, names
    # Italian/English stopwords and sentence-initial words must not leak.
    for bad in ("Il", "La", "Per", "The", "This"):
        assert bad not in names, names


def test_camelcase_extracted():
    names = _names(
        "SemanticMemory e EpisodicMemory condividono il pattern _connect"
    )
    assert "SemanticMemory" in names
    assert "EpisodicMemory" in names


def test_noise_resistance_numbers_and_short_tokens():
    text = "recall@5 0.790 hit@5 0.820 MRR 0.717 lat 59ms n=100 k=5 p=0.00052"
    names = _names(text)
    # Pure metrics noise: no number-only or unit tokens; MRR (acronym) ok.
    assert names <= {"MRR"}, names


def test_cap_per_text_and_shape():
    text = " ".join(f"Modulo_{i} " for i in range(40))
    out = extract_entities_lite(text)
    assert len(out) <= 16, "per-text cap must bound clique size downstream"
    for e in out:
        assert set(e) >= {"name", "type"}
        assert e["name"].strip()


def test_empty_and_none_safe():
    assert extract_entities_lite("") == []
    assert extract_entities_lite("   ") == []
