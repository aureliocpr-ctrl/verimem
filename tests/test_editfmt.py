"""Tests for the SEARCH/REPLACE edit format parser + applier."""
from __future__ import annotations

from engram.editfmt import (
    EditBlock,
    apply_block,
    apply_blocks,
    make_diff,
    parse_edits,
)

# --- parse_edits ----------------------------------------------------------


def test_parse_single_block():
    text = """\
src/foo.py
<<<<<<< SEARCH
old line
=======
new line
>>>>>>> REPLACE
"""
    blocks = parse_edits(text)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.path == "src/foo.py"
    assert b.search == "old line"
    assert b.replace == "new line"


def test_parse_multiple_blocks():
    text = """
Some explanation.

a.py
<<<<<<< SEARCH
A
=======
B
>>>>>>> REPLACE

More explanation.

b.py
<<<<<<< SEARCH
C
=======
D
>>>>>>> REPLACE
"""
    blocks = parse_edits(text)
    assert [b.path for b in blocks] == ["a.py", "b.py"]
    assert [b.search for b in blocks] == ["A", "C"]
    assert [b.replace for b in blocks] == ["B", "D"]


def test_parse_handles_crlf():
    text = "x.py\r\n<<<<<<< SEARCH\r\nold\r\n=======\r\nnew\r\n>>>>>>> REPLACE"
    blocks = parse_edits(text)
    assert len(blocks) == 1
    assert blocks[0].search == "old"
    assert blocks[0].replace == "new"


def test_parse_handles_fences_around_block():
    text = """
```python
foo.py
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE
```
"""
    blocks = parse_edits(text)
    assert len(blocks) == 1
    assert blocks[0].path == "foo.py"


def test_parse_empty_search_for_new_file():
    text = """\
new_file.txt
<<<<<<< SEARCH
=======
hello world
>>>>>>> REPLACE
"""
    blocks = parse_edits(text)
    assert len(blocks) == 1
    assert blocks[0].search == ""
    assert blocks[0].replace == "hello world"


def test_parse_no_blocks_in_plain_text():
    assert parse_edits("just an explanation, no edits here") == []


def test_parse_preserves_multiline_body():
    text = """\
m.py
<<<<<<< SEARCH
def f():
    return 1
=======
def f():
    return 2
>>>>>>> REPLACE
"""
    b = parse_edits(text)[0]
    assert b.search == "def f():\n    return 1"
    assert b.replace == "def f():\n    return 2"


# --- apply_block ----------------------------------------------------------


def test_apply_modifies_existing_file(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("def hello():\n    return 'old'\n", encoding="utf-8")
    b = EditBlock(path="x.py", search="return 'old'", replace="return 'new'")
    r = apply_block(b, tmp_path)
    assert r.ok
    assert "return 'new'" in f.read_text()
    assert "-    return 'old'" in r.diff
    assert "+    return 'new'" in r.diff


def test_apply_creates_new_file_with_empty_search(tmp_path):
    b = EditBlock(path="newdir/new.py", search="", replace="print('hi')\n")
    r = apply_block(b, tmp_path)
    assert r.ok
    assert (tmp_path / "newdir" / "new.py").read_text() == "print('hi')\n"


def test_apply_refuses_path_traversal(tmp_path):
    b = EditBlock(path="../escape.txt", search="", replace="evil")
    r = apply_block(b, tmp_path)
    assert not r.ok
    assert "escape" in r.reason.lower()


def test_apply_refuses_search_not_found(tmp_path):
    f = tmp_path / "y.py"
    f.write_text("def f(): pass\n", encoding="utf-8")
    b = EditBlock(path="y.py", search="does not exist", replace="x")
    r = apply_block(b, tmp_path)
    assert not r.ok
    assert "not found" in r.reason.lower()


def test_apply_refuses_ambiguous_search(tmp_path):
    f = tmp_path / "z.py"
    f.write_text("x = 1\nx = 1\n", encoding="utf-8")  # "x = 1" appears twice
    b = EditBlock(path="z.py", search="x = 1", replace="x = 2")
    r = apply_block(b, tmp_path)
    assert not r.ok
    assert "matches 2 times" in r.reason


def test_apply_missing_file(tmp_path):
    b = EditBlock(path="ghost.py", search="anything", replace="x")
    r = apply_block(b, tmp_path)
    assert not r.ok
    assert "does not exist" in r.reason.lower()


def test_apply_blocks_reports_independently(tmp_path):
    """One bad block shouldn't roll back a good one in the same call."""
    f = tmp_path / "a.py"
    f.write_text("aaa\n", encoding="utf-8")
    blocks = [
        EditBlock(path="a.py", search="aaa", replace="bbb"),  # good
        EditBlock(path="missing.py", search="x", replace="y"),  # bad
    ]
    results = apply_blocks(blocks, tmp_path)
    assert results[0].ok
    assert not results[1].ok
    assert (tmp_path / "a.py").read_text() == "bbb\n"


# --- make_diff ------------------------------------------------------------


def test_make_diff_format():
    diff = make_diff("foo.py", "old\n", "new\n")
    assert "--- a/foo.py" in diff
    assert "+++ b/foo.py" in diff
    assert "-old" in diff
    assert "+new" in diff
