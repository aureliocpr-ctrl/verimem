"""Cycle 222 (2026-05-23) — disk persistence for emergent skill drafts.

RED marker: ``from engram.skill_draft_persist import persist_drafts``
must fail on master.

Adds an audit trail: every batch of drafts produced by
cycle 217's ``draft_skill_from_community`` can be written to
``<root_dir>/<YYYYMMDD-HHMMSS>/<skill_name>.md`` so that the agent
+ user can ``ls + cat`` to see emergence evolution over time.

Each draft → two files:
  - ``<name>.md``      → human-readable Markdown body
  - ``<name>.meta.json`` → structured evidence + keywords + fact_ids

Defensive: name sanitization (no path traversal, no slashes),
existing files NOT overwritten in the same timestamp dir (rare
collision, but caller may invoke twice within 1 second).
"""
from __future__ import annotations

import json
from pathlib import Path

# RED MARKER
from engram.skill_draft_persist import persist_drafts


def _sample_draft(name: str = "emerging_skill_demo") -> dict:
    return {
        "skill_name": name,
        "draft_text": f"# {name} (DRAFT)\n\n## Evidence\n- size=4\n\nStatus: DRAFT (pending)",
        "trigger_keywords": ["foo", "bar", "baz"],
        "fact_ids": ["f1", "f2", "f3", "f4"],
        "evidence": {
            "community_id": "c0",
            "size": 4,
            "dominant_topic": "lang/demo",
            "topic_purity": 0.75,
            "cohesion": 0.88,
            "emergence_score": 2.64,
        },
    }


class TestPersistDrafts:
    def test_empty_list_creates_no_files(self, tmp_path: Path) -> None:
        out = persist_drafts([], root_dir=tmp_path)
        assert out["n_written"] == 0
        # No timestamp subdir should have been created.
        assert not any(tmp_path.iterdir())

    def test_writes_md_and_meta_for_each_draft(
        self, tmp_path: Path,
    ) -> None:
        drafts = [_sample_draft("emerging_skill_python")]
        out = persist_drafts(drafts, root_dir=tmp_path)
        assert out["n_written"] == 1
        # Exactly one timestamp dir.
        dirs = list(tmp_path.iterdir())
        assert len(dirs) == 1
        sub = dirs[0]
        assert sub.is_dir()
        md = sub / "emerging_skill_python.md"
        meta = sub / "emerging_skill_python.meta.json"
        assert md.exists()
        assert meta.exists()
        assert "# emerging_skill_python (DRAFT)" in md.read_text(
            encoding="utf-8",
        )
        loaded = json.loads(meta.read_text(encoding="utf-8"))
        assert loaded["skill_name"] == "emerging_skill_python"
        assert loaded["trigger_keywords"] == ["foo", "bar", "baz"]
        assert loaded["evidence"]["size"] == 4

    def test_multiple_drafts_same_batch(self, tmp_path: Path) -> None:
        drafts = [
            _sample_draft("emerging_skill_a"),
            _sample_draft("emerging_skill_b"),
            _sample_draft("emerging_skill_c"),
        ]
        out = persist_drafts(drafts, root_dir=tmp_path)
        assert out["n_written"] == 3
        sub = next(tmp_path.iterdir())
        assert len(list(sub.glob("*.md"))) == 3
        assert len(list(sub.glob("*.meta.json"))) == 3

    def test_name_sanitization_blocks_path_traversal(
        self, tmp_path: Path,
    ) -> None:
        """A malicious draft name with '..' or '/' must not escape
        the root_dir."""
        bad = _sample_draft("../../etc/passwd")
        out = persist_drafts([bad], root_dir=tmp_path)
        # File must be inside tmp_path or be skipped entirely.
        # If skipped, n_written=0; if sanitized, file inside tmp_path.
        if out["n_written"] > 0:
            sub = next(tmp_path.iterdir())
            for f in sub.iterdir():
                assert f.is_file()
                # Resolved path must stay under sub.
                rel = f.resolve().relative_to(sub.resolve())
                # No directory traversal in the relative path.
                assert ".." not in rel.parts

    def test_empty_skill_name_skipped(self, tmp_path: Path) -> None:
        """Drafts without a skill_name must be skipped silently."""
        d = _sample_draft("")
        out = persist_drafts([d], root_dir=tmp_path)
        assert out["n_written"] == 0

    def test_returns_timestamp_directory_path(
        self, tmp_path: Path,
    ) -> None:
        """Caller can use the timestamp dir for follow-up
        operations (logs, hippo fact ref, etc.)."""
        drafts = [_sample_draft("emerging_skill_x")]
        out = persist_drafts(drafts, root_dir=tmp_path)
        assert "batch_dir" in out
        assert Path(out["batch_dir"]).exists()
        assert Path(out["batch_dir"]).is_dir()

    def test_duplicate_skill_names_get_unique_suffix(
        self, tmp_path: Path,
    ) -> None:
        """Cycle 222.1: when two drafts share a normalised name
        (real-corpus 'emerging_skill_master-fact' produced two
        communities with same family-key), append community_id
        to disambiguate so neither overwrites the other."""
        d1 = _sample_draft("emerging_skill_master-fact")
        d1["evidence"] = dict(d1["evidence"])
        d1["evidence"]["community_id"] = "c-010"
        d2 = _sample_draft("emerging_skill_master-fact")
        d2["evidence"] = dict(d2["evidence"])
        d2["evidence"]["community_id"] = "c-011"
        out = persist_drafts([d1, d2], root_dir=tmp_path)
        assert out["n_written"] == 2
        sub = next(tmp_path.iterdir())
        md_files = sorted(p.name for p in sub.glob("*.md"))
        assert len(md_files) == 2
        # First one keeps the bare name; second one gets the suffix.
        assert "emerging_skill_master-fact.md" in md_files
        assert any("c-010" in m or "c-011" in m for m in md_files)

    def test_root_dir_created_if_missing(self, tmp_path: Path) -> None:
        """The function should ensure root_dir exists (mkdir parents)."""
        missing = tmp_path / "deeply" / "nested" / "out"
        drafts = [_sample_draft("emerging_skill_y")]
        out = persist_drafts(drafts, root_dir=missing)
        assert out["n_written"] == 1
        assert missing.exists()
