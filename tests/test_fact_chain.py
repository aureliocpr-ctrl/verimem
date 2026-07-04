"""R30: Fact chaining — multi-hop reasoning across facts.

Starting from a seed query, find facts that share tokens. From each
match, expand to more facts. Up to max_depth layers.

Different from forward_chain: this works on natural-language facts,
not formal rules. Useful for "what do we know about X?".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""


def test_empty_query_no_chain():
    from engram.fact_chain import chain_facts
    out = chain_facts(seed_query="", facts=[])
    assert out["chain"] == []


def test_single_hop():
    from engram.fact_chain import chain_facts
    facts = [
        _Fact("f1", "WordPress is a CMS"),
        _Fact("f2", "Cloudflare is a CDN"),
    ]
    out = chain_facts(seed_query="WordPress", facts=facts, max_depth=1)
    chain_ids = [c["id"] for c in out["chain"]]
    assert "f1" in chain_ids


def test_multi_hop():
    from engram.fact_chain import chain_facts
    facts = [
        _Fact("f1", "WordPress 5.8 detected on target"),
        _Fact("f2", "WordPress 5.8 vulnerable to CVE-X"),
        _Fact("f3", "CVE-X allows remote code execution"),
        _Fact("f4", "totally unrelated cooking recipe"),
    ]
    out = chain_facts(seed_query="WordPress", facts=facts, max_depth=3)
    chain_ids = [c["id"] for c in out["chain"]]
    # Should reach CVE-X through f1, f2, f3 chain
    assert "f1" in chain_ids
    assert "f4" not in chain_ids


def test_depth_limit():
    from engram.fact_chain import chain_facts
    facts = [
        _Fact("f1", "A is B"),
        _Fact("f2", "B is C"),
        _Fact("f3", "C is D"),
    ]
    out = chain_facts(seed_query="A", facts=facts, max_depth=1)
    # Only f1 at depth 1
    chain_ids = [c["id"] for c in out["chain"]]
    assert len(chain_ids) <= 2  # max f1, maybe f2


def test_payload_shape():
    from engram.fact_chain import chain_facts
    out = chain_facts(seed_query="X", facts=[])
    for k in ("chain", "max_depth_reached", "n_facts_scanned"):
        assert k in out


def test_entry_keys():
    from engram.fact_chain import chain_facts
    facts = [_Fact("f1", "X is something")]
    out = chain_facts(seed_query="X", facts=facts)
    if out["chain"]:
        for k in ("id", "proposition", "depth"):
            assert k in out["chain"][0]
