"""Cycle 227 (2026-05-23) — list persisted skill drafts.

RED marker: ``from verimem.skill_drafts_list import list_persisted_drafts``
must fail on master.

Reads the disk layout produced by cycle 222 ``persist_drafts``::

    <root>/<YYYYMMDD-HHMMSS>/<skill_name>.md
    <root>/<YYYYMMDD-HHMMSS>/<skill_name>.meta.json

and returns a structured listing sorted by batch timestamp (newest
first). Used by the cycle 228 MCP tool ``hippo_skill_drafts_list``
to surface the audit trail to MCP clients.
"""
from __future__ import annotations

import json
from pathlib import Path

# RED MARKER
from verimem.skill_drafts_list import list_persisted_drafts


def _write_batch(
    root: Path, batch_name: str, names: list[str],
) -> None:
    sub = root / batch_name
    sub.mkdir(parents=True, exist_ok=True)
    for n in names:
        (sub / f"{n}.md").write_text(
            f"# {n} (DRAFT)\n", encoding="utf-8",
        )
        meta = {
            "skill_name": n,
            "trigger_keywords": ["foo", "bar"],
            "fact_ids": ["f1", "f2"],
            "evidence": {"size": 4, "topic_purity": 0.5,
                          "cohesion": 0.7, "community_id": "c0"},
        }
        (sub / f"{n}.meta.json").write_text(
            json.dumps(meta), encoding="utf-8",
        )


class TestListPersistedDrafts:
    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        out = list_persisted_drafts(tmp_path / "nope")
        assert out["n_batches"] == 0
        assert out["batches"] == []

    def test_empty_root_returns_empty(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        out = list_persisted_drafts(tmp_path)
        assert out["n_batches"] == 0
        assert out["batches"] == []

    def test_lists_batches_newest_first(self, tmp_path: Path) -> None:
        # Timestamp names sort lexicographically (YYYYMMDD-HHMMSS).
        _write_batch(tmp_path, "20260522-020000", ["s_alpha"])
        _write_batch(tmp_path, "20260522-030000", ["s_beta"])
        _write_batch(tmp_path, "20260522-040000", ["s_gamma"])
        out = list_persisted_drafts(tmp_path)
        assert out["n_batches"] == 3
        batch_ids = [b["batch_id"] for b in out["batches"]]
        assert batch_ids == [
            "20260522-040000", "20260522-030000", "20260522-020000",
        ]

    def test_each_batch_lists_drafts_with_meta(
        self, tmp_path: Path,
    ) -> None:
        _write_batch(
            tmp_path, "20260522-040000",
            ["emerging_skill_a", "emerging_skill_b"],
        )
        out = list_persisted_drafts(tmp_path)
        batch = out["batches"][0]
        assert "drafts" in batch
        assert len(batch["drafts"]) == 2
        names = {d["skill_name"] for d in batch["drafts"]}
        assert names == {"emerging_skill_a", "emerging_skill_b"}
        for d in batch["drafts"]:
            assert "trigger_keywords" in d
            assert "evidence" in d

    def test_max_batches_caps(self, tmp_path: Path) -> None:
        for i in range(5):
            _write_batch(
                tmp_path, f"20260522-0{i}0000", [f"s_{i}"],
            )
        out = list_persisted_drafts(tmp_path, max_batches=2)
        assert out["n_batches"] == 2

    def test_corrupt_meta_handled_gracefully(
        self, tmp_path: Path,
    ) -> None:
        sub = tmp_path / "20260522-050000"
        sub.mkdir(parents=True)
        (sub / "s_x.md").write_text("body", encoding="utf-8")
        (sub / "s_x.meta.json").write_text(
            "{NOT VALID JSON", encoding="utf-8",
        )
        out = list_persisted_drafts(tmp_path)
        # Either the corrupt entry is skipped or it surfaces with
        # evidence={}; in both cases the function must NOT raise.
        assert out["n_batches"] == 1
        batch = out["batches"][0]
        # Either 0 drafts (skipped) or 1 with evidence={} (defensive).
        if batch["drafts"]:
            assert batch["drafts"][0]["skill_name"] == "s_x"
            assert batch["drafts"][0]["evidence"] == {}

    def test_orphan_md_without_meta_handled(
        self, tmp_path: Path,
    ) -> None:
        """A .md file with no matching .meta.json is included with
        empty metadata."""
        sub = tmp_path / "20260522-060000"
        sub.mkdir(parents=True)
        (sub / "orphan.md").write_text("body", encoding="utf-8")
        out = list_persisted_drafts(tmp_path)
        assert out["n_batches"] == 1
        # 0 or 1 drafts; if 1, evidence must be an empty dict.
        batch = out["batches"][0]
        if batch["drafts"]:
            assert batch["drafts"][0]["evidence"] == {}
