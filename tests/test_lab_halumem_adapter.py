"""Cycle 173 (2026-05-22) — integration test for scripts/lab_halumem_adapter.py.

Validates the HaluMem adapter pipeline end-to-end on the built-in
6-record synthetic sample. Does NOT download the real HaluMem dataset
(network-gated); a separate manual run with ``--jsonl <path>`` covers
that case.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lab_halumem_adapter import (  # noqa: E402
    _SAMPLE,
    AdapterRecord,
    expected_gate_action,
    load_jsonl,
    normalize,
    score,
)


class TestNormalize:
    def test_canonical_record_passes(self):
        rec = normalize({
            "proposition": "x",
            "verified_by": ["a"],
            "topic": "t",
            "memory_source": "primary",
        })
        assert rec is not None
        assert rec.proposition == "x"
        assert rec.verified_by == ["a"]
        assert rec.topic == "t"
        assert rec.label == "primary"

    def test_alternate_keys_accepted(self):
        # HaluMem may emit "content" or "text" instead of "proposition";
        # "evidence" instead of "verified_by"; "source" instead of label.
        rec = normalize({
            "content": "y",
            "evidence": "single-ref",
            "category": "topic-cat",
            "source": "interference",
        })
        assert rec is not None
        assert rec.proposition == "y"
        assert rec.verified_by == ["single-ref"]
        assert rec.topic == "topic-cat"
        assert rec.label == "interference"

    def test_missing_proposition_returns_none(self):
        assert normalize({"memory_source": "primary"}) is None

    def test_missing_label_returns_none(self):
        assert normalize({"proposition": "x"}) is None

    def test_unknown_label_returns_none(self):
        assert normalize({
            "proposition": "x", "memory_source": "bogus_class",
        }) is None

    def test_label_lowercased(self):
        rec = normalize({"proposition": "x", "memory_source": "PRIMARY"})
        assert rec is not None and rec.label == "primary"


class TestExpectedGateAction:
    def test_interference_is_gate_positive(self):
        assert expected_gate_action("interference") == "downgrade"

    def test_other_classes_are_gate_negative(self):
        for lbl in ("primary", "secondary", "system"):
            assert expected_gate_action(lbl) == "persist"


class TestLoadJsonl:
    def test_round_trip(self, tmp_path: Path):
        p = tmp_path / "halumem.jsonl"
        rows = [
            {"proposition": "a", "memory_source": "primary"},
            {"proposition": "b", "memory_source": "interference"},
        ]
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        out = load_jsonl(p)
        assert out == rows

    def test_skips_blank_and_malformed(self, tmp_path: Path):
        p = tmp_path / "halumem.jsonl"
        p.write_text(
            '{"proposition": "ok", "memory_source": "primary"}\n'
            "\n"
            "{not valid json\n"
            '{"proposition": "ok2", "memory_source": "system"}\n',
            encoding="utf-8",
        )
        out = load_jsonl(p)
        assert len(out) == 2
        assert {r["proposition"] for r in out} == {"ok", "ok2"}


class TestScoreOnSyntheticSample:
    def test_built_in_sample_scores_100_pct(self):
        """The synthetic _SAMPLE is engineered so every label class is
        present and the gate's L1/L1.5 keyword heuristics agree with
        the expected_gate_action contract. This test is the smoke
        signal that the pipeline is wired end-to-end. It is NOT a
        paper-citable claim about HaluMem real numbers."""
        records = [r for r in (normalize(x) for x in _SAMPLE) if r is not None]
        assert len(records) == 6
        outcomes, summary = score(records, validate="fast",
                                    gate_mode="downgrade")
        assert summary["n"] == 6
        assert summary["accuracy"] == 1.0
        assert summary["confusion"] == {"tp": 2, "fn": 0, "fp": 0, "tn": 4}
        assert summary["tpr"] == 1.0
        assert summary["fpr"] == 0.0
        # Latency sanity — all records sub-millisecond on fast tier.
        assert summary["p50_ms"] < 5.0

    def test_interference_records_carry_warnings(self):
        records = [r for r in (normalize(x) for x in _SAMPLE) if r is not None]
        outcomes, _ = score(records, validate="fast", gate_mode="downgrade")
        interference = [o for o in outcomes if o.label == "interference"]
        assert len(interference) == 2
        for o in interference:
            assert o.actual == "downgrade"
            assert len(o.warnings) >= 1, (
                f"interference record should carry ≥1 warning, "
                f"got {o.warnings}"
            )

    def test_anchored_shipped_claim_persists(self):
        """A SHIPPED claim WITH a commit/PR anchor in verified_by must
        NOT be downgraded by L1 — exactly the contract paper §2.1."""
        records = [r for r in (normalize(x) for x in _SAMPLE) if r is not None]
        anchored = [r for r in records if "commit:" in " ".join(r.verified_by)]
        assert len(anchored) == 1
        outcomes, _ = score(anchored, validate="fast",
                              gate_mode="downgrade")
        assert outcomes[0].actual == "persist"
        assert outcomes[0].label == "primary"
