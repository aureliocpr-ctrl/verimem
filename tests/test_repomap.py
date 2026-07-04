"""Tests for the repo-map scanner + ranker."""
from __future__ import annotations

from pathlib import Path

from engram.repomap import (
    build_repomap,
    rank_files,
    render_repomap,
    scan_repo,
)


def _seed(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def hello():\n    return 1\n\nclass Foo:\n    def bar(self): pass\n",
        encoding="utf-8",
    )
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "util.js").write_text(
        "export function add(a, b) { return a + b; }\n"
        "export class Helper {}\n"
        "const X = 1;\n",
        encoding="utf-8",
    )
    # An ignored dir — must be filtered out
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ghost.js").write_text("function evil() {}\n",
                                                          encoding="utf-8")
    # A binary-ish file we don't recognise
    (tmp_path / "image.bin").write_bytes(b"\x00\x01\x02\x03")


def test_scan_extracts_python_symbols(tmp_path):
    _seed(tmp_path)
    entries = scan_repo(tmp_path)
    py = next(e for e in entries if e.path == "main.py")
    assert py.lang == "python"
    names = [s.name for s in py.symbols]
    assert {"hello", "Foo", "bar"} <= set(names)


def test_scan_extracts_js_symbols(tmp_path):
    _seed(tmp_path)
    entries = scan_repo(tmp_path)
    js = next(e for e in entries if e.path == "lib/util.js")
    names = {s.name for s in js.symbols}
    assert {"add", "Helper", "X"} <= names


def test_scan_skips_ignored_dirs(tmp_path):
    _seed(tmp_path)
    paths = [e.path for e in scan_repo(tmp_path)]
    assert not any(p.startswith("node_modules") for p in paths)


def test_scan_skips_binary_unknown(tmp_path):
    _seed(tmp_path)
    paths = [e.path for e in scan_repo(tmp_path)]
    assert "image.bin" not in paths


def test_rank_orders_richer_files_higher(tmp_path):
    _seed(tmp_path)
    entries = scan_repo(tmp_path)
    ranked = rank_files(entries)
    # main.py has 3 symbols, util.js has 3 — tie depends on path depth.
    # Top-level main.py should come before nested lib/util.js
    top_paths = [e.path for e in ranked]
    assert top_paths.index("main.py") < top_paths.index("lib/util.js")


def test_render_respects_char_budget(tmp_path):
    _seed(tmp_path)
    entries = rank_files(scan_repo(tmp_path))
    rendered = render_repomap(entries, max_chars=300)
    assert len(rendered) <= 300


def test_build_repomap_one_shot(tmp_path):
    _seed(tmp_path)
    text = build_repomap(tmp_path, max_files=10, max_chars=2000)
    assert "REPO MAP" in text
    assert "main.py" in text
    assert "hello" in text
    assert "node_modules" not in text


def test_recent_skill_paths_boost(tmp_path):
    _seed(tmp_path)
    entries = scan_repo(tmp_path)
    # No boost: top-level main.py wins by depth
    plain = rank_files(list(entries))
    # Boost lib/util.js
    boosted = rank_files(list(entries), recent_skill_paths={"lib/util.js"})
    plain_top = plain[0].path
    boosted_top = boosted[0].path
    # Boost should at least pull lib/util.js to the top, OR keep both relative
    # ordering reasonable. Strict assert: boost moves util.js above main.py.
    assert boosted_top == "lib/util.js"
    assert plain_top != boosted_top  # ranking actually changed
