"""FORGIA pezzo #227 — Wave 26: corpus disk-size report.

Pure filesystem inspection. Returns bytes used by each memory tier.
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def test_payload_shape_complete():
    from engram.corpus_size import corpus_size_report

    with tempfile.TemporaryDirectory() as tmp:
        out = corpus_size_report(data_dir=Path(tmp))
    for k in ("data_dir", "episodes_bytes", "semantic_bytes",
                "skills_bytes", "total_bytes", "total_mb",
                "n_skill_files"):
        assert k in out


def test_missing_dirs_yields_zeros():
    from engram.corpus_size import corpus_size_report

    out = corpus_size_report(data_dir=Path("/does/not/exist/anywhere"))
    assert out["episodes_bytes"] == 0
    assert out["semantic_bytes"] == 0
    assert out["skills_bytes"] == 0
    assert out["total_bytes"] == 0


def test_total_equals_sum_of_parts():
    from engram.corpus_size import corpus_size_report

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "episodes").mkdir()
        (d / "episodes" / "episodes.db").write_bytes(b"x" * 100)
        (d / "semantic").mkdir()
        (d / "semantic" / "semantic.db").write_bytes(b"y" * 200)
        (d / "skills").mkdir()
        (d / "skills" / "s1.json").write_bytes(b"z" * 50)
        (d / "skills" / "s2.json").write_bytes(b"z" * 50)
        out = corpus_size_report(data_dir=d)
    assert out["episodes_bytes"] == 100
    assert out["semantic_bytes"] == 200
    assert out["skills_bytes"] == 100
    assert out["total_bytes"] == 400
    assert abs(out["total_mb"] - 400 / (1024 * 1024)) < 1e-9
    assert out["n_skill_files"] == 2


def test_legacy_semantic_db_path():
    """Old layout: data/semantic.db (not in subdir)."""
    from engram.corpus_size import corpus_size_report

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "semantic.db").write_bytes(b"x" * 80)
        out = corpus_size_report(data_dir=d)
    assert out["semantic_bytes"] == 80


def test_data_dir_string_returned():
    from engram.corpus_size import corpus_size_report

    with tempfile.TemporaryDirectory() as tmp:
        out = corpus_size_report(data_dir=Path(tmp))
    assert isinstance(out["data_dir"], str)
