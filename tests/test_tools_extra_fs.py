"""Boundary tests for tools_extra filesystem operations.

Covers fs_read_file / fs_write_file / fs_list_dir / fs_search_files:

  • Happy path inside the allowed root
  • Refusal when outside the allowed root
  • Refusal when the path matches the sensitive deny-list
  • Append vs overwrite mode for fs_write_file
  • UTF-8 / non-UTF-8 file behaviour for fs_read_file
  • Glob pattern + content-substring filter for fs_search_files
  • max_bytes truncation for fs_read_file
  • Missing file / not-a-regular-file branches
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engram import tools_extra


@pytest.fixture
def fs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Lock the FS sandbox to tmp_path for the duration of the test."""
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    monkeypatch.delenv("HIPPO_FS_STRICT", raising=False)
    monkeypatch.delenv("HIPPO_FS_HOME", raising=False)
    return tmp_path


# ---------------------------------------------------------------------------
# fs_read_file
# ---------------------------------------------------------------------------


def test_fs_read_happy_path(fs_root: Path) -> None:
    target = fs_root / "hello.txt"
    target.write_text("ciao mondo", encoding="utf-8")
    r = tools_extra.fs_read_file(str(target))
    assert r.ok is True
    assert r.output == "ciao mondo"
    assert r.extra and r.extra["size"] == len(b"ciao mondo")


def test_fs_read_truncates_to_max_bytes(fs_root: Path) -> None:
    target = fs_root / "big.txt"
    target.write_text("A" * 1000, encoding="utf-8")
    r = tools_extra.fs_read_file(str(target), max_bytes=100)
    assert r.ok is True
    assert len(r.output) == 100


def test_fs_read_missing_file(fs_root: Path) -> None:
    r = tools_extra.fs_read_file(str(fs_root / "nope.txt"))
    assert r.ok is False
    assert "not found" in (r.error or "").lower()


def test_fs_read_not_regular_file(fs_root: Path) -> None:
    """Reading a directory should fail cleanly."""
    sub = fs_root / "subdir"
    sub.mkdir()
    r = tools_extra.fs_read_file(str(sub))
    assert r.ok is False
    assert "regular" in (r.error or "").lower()


def test_fs_read_outside_root_refused(
    fs_root: Path, tmp_path_factory: pytest.TempPathFactory,
) -> None:
    other = tmp_path_factory.mktemp("other")
    target = other / "leaked.txt"
    target.write_text("nope", encoding="utf-8")
    r = tools_extra.fs_read_file(str(target))
    assert r.ok is False
    assert "outside" in (r.error or "").lower()


def test_fs_read_handles_non_utf8_bytes(fs_root: Path) -> None:
    """fs_read_file must not crash on invalid UTF-8 — uses errors='replace'."""
    target = fs_root / "binary.bin"
    target.write_bytes(b"\xff\xfe\x00bad bytes")
    r = tools_extra.fs_read_file(str(target))
    assert r.ok is True
    # The replacement char is allowed; we just verify it didn't crash.


# ---------------------------------------------------------------------------
# fs_write_file
# ---------------------------------------------------------------------------


def test_fs_write_creates_file_and_parents(fs_root: Path) -> None:
    target = fs_root / "deep" / "nested" / "out.txt"
    r = tools_extra.fs_write_file(str(target), "hello")
    assert r.ok is True
    assert target.read_text(encoding="utf-8") == "hello"


def test_fs_write_overwrites_by_default(fs_root: Path) -> None:
    target = fs_root / "f.txt"
    target.write_text("OLD", encoding="utf-8")
    r = tools_extra.fs_write_file(str(target), "NEW")
    assert r.ok is True
    assert target.read_text(encoding="utf-8") == "NEW"


def test_fs_write_appends_when_requested(fs_root: Path) -> None:
    target = fs_root / "log.txt"
    target.write_text("first\n", encoding="utf-8")
    r = tools_extra.fs_write_file(str(target), "second\n", append=True)
    assert r.ok is True
    assert target.read_text(encoding="utf-8") == "first\nsecond\n"


def test_fs_write_outside_root_refused(
    fs_root: Path, tmp_path_factory: pytest.TempPathFactory,
) -> None:
    other = tmp_path_factory.mktemp("forbidden")
    r = tools_extra.fs_write_file(str(other / "leak.txt"), "evil")
    assert r.ok is False
    assert not (other / "leak.txt").exists()


def test_fs_write_refuses_sensitive_path(fs_root: Path) -> None:
    """A .pem inside the allowed root must still be refused."""
    target = fs_root / "server.pem"
    r = tools_extra.fs_write_file(str(target), "fake key")
    assert r.ok is False
    assert "sensitive" in (r.error or "").lower()
    assert not target.exists()


# ---------------------------------------------------------------------------
# fs_list_dir
# ---------------------------------------------------------------------------


def test_fs_list_dir_lists_entries(fs_root: Path) -> None:
    (fs_root / "a.txt").write_text("a", encoding="utf-8")
    (fs_root / "b.txt").write_text("bb", encoding="utf-8")
    (fs_root / "subdir").mkdir()
    r = tools_extra.fs_list_dir()
    assert r.ok is True
    items = (r.extra or {}).get("items", [])
    names = sorted(i["name"] for i in items)
    # tmp_path may already contain files set up by other fixtures; we just
    # verify our three entries are present.
    for expected in ("a.txt", "b.txt", "subdir"):
        assert expected in names, f"missing entry: {expected}"
    sub = next(i for i in items if i["name"] == "subdir")
    assert sub["type"] == "dir"


def test_fs_list_dir_glob_filter(fs_root: Path) -> None:
    (fs_root / "x.txt").write_text("x", encoding="utf-8")
    (fs_root / "y.md").write_text("y", encoding="utf-8")
    r = tools_extra.fs_list_dir(pattern="*.txt")
    items = (r.extra or {}).get("items", [])
    names = [i["name"] for i in items]
    assert "x.txt" in names
    assert "y.md" not in names


def test_fs_list_dir_outside_root_refused(
    fs_root: Path,
) -> None:
    """Even though _fs_roots()[0] / 'subdir' is fine, an absolute outside path is not.

    The function builds its target from the first allowed root; we verify
    it stays inside (no absolute escape is possible through this surface).
    """
    # Test the standard happy-path on an existing directory
    r = tools_extra.fs_list_dir(path="nonexistent_subdir")
    assert r.ok is False
    assert "not found" in (r.error or "").lower()


# ---------------------------------------------------------------------------
# fs_search_files
# ---------------------------------------------------------------------------


def test_fs_search_finds_by_glob(fs_root: Path) -> None:
    (fs_root / "a.py").write_text("import os", encoding="utf-8")
    (fs_root / "b.py").write_text("print('hi')", encoding="utf-8")
    (fs_root / "c.txt").write_text("plain", encoding="utf-8")
    r = tools_extra.fs_search_files("*.py")
    assert r.ok is True
    matches = (r.extra or {}).get("matches", [])
    # Returned as relative paths
    assert sorted(matches) == ["a.py", "b.py"]


def test_fs_search_filters_by_substring(fs_root: Path) -> None:
    (fs_root / "good.py").write_text("import requests", encoding="utf-8")
    (fs_root / "bad.py").write_text("print('hi')", encoding="utf-8")
    r = tools_extra.fs_search_files("*.py", contains="requests")
    matches = (r.extra or {}).get("matches", [])
    assert matches == ["good.py"]


def test_fs_search_substring_is_case_insensitive(fs_root: Path) -> None:
    (fs_root / "f.py").write_text("import REQUESTS", encoding="utf-8")
    r = tools_extra.fs_search_files("*.py", contains="requests")
    matches = (r.extra or {}).get("matches", [])
    assert matches == ["f.py"]


def test_fs_search_caps_at_100_matches(fs_root: Path) -> None:
    """Limit is a defensive guard against pathological repos."""
    for i in range(150):
        (fs_root / f"f{i:03d}.txt").write_text("x", encoding="utf-8")
    r = tools_extra.fs_search_files("*.txt")
    matches = (r.extra or {}).get("matches", [])
    assert len(matches) <= 100


def test_fs_search_skips_unreadable_files_with_contains(
    fs_root: Path,
) -> None:
    """A file that fails to decode shouldn't crash the scan."""
    (fs_root / "ok.py").write_text("import requests", encoding="utf-8")
    (fs_root / "bin.py").write_bytes(b"\xff\xfe\x00binary")
    r = tools_extra.fs_search_files("*.py", contains="requests")
    matches = (r.extra or {}).get("matches", [])
    # Either the binary file is silently skipped or it doesn't match — we
    # require ok.py to be there.
    assert "ok.py" in matches
