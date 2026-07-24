"""Content-bound receipts (D5 / task #44) — pin WHAT was cited, not just where.

`_verify_file_ref` answers one question: does `file:<path>:<line>` resolve to a
file with at least that many lines? That is RESOLVABILITY. It says nothing
about the content, so the receipt cannot tell later whether the evidence still
says what it said — the TOCTOU Kimi-K3 raised on the P0 design (2026-07-22):
pin the hash of the matched span, not the path and line.

The pin is a signal, never a verdict: evidence that moved or changed does not
retroactively make a fact false. It makes the receipt HONEST about the fact
that what was read then is not what is there now — `stale` as an orthogonal
axis, exactly as D5 states it.

Four outcomes, and each one is a different truth:
  ok           — the cited line still reads the same
  moved        — the same text is still in the file, at another line
  changed      — that line now says something else
  unresolvable — the file (or the line) is gone; nothing can be said
"""
from __future__ import annotations

from verimem.content_pin import pin_for_ref, verify_pin

LINES = "alpha\nbeta\ngamma\ndelta\n"


def _repo(tmp_path):
    (tmp_path / "src").mkdir()
    p = tmp_path / "src" / "mod.py"
    p.write_text(LINES, encoding="utf-8")
    return tmp_path, p


# --- pinning --------------------------------------------------------------

def test_pin_is_stable_and_content_derived(tmp_path):
    root, p = _repo(tmp_path)
    a = pin_for_ref(f"file:{p}:2", repo_root=root)
    b = pin_for_ref(f"file:{p}:2", repo_root=root)
    assert a and a == b
    assert a.startswith("sha256:")
    assert pin_for_ref(f"file:{p}:3", repo_root=root) != a


def test_pin_ignores_trailing_whitespace(tmp_path):
    """Trailing spaces are not content. This is what the normalisation buys:
    an editor stripping (or adding) them must not read as a rewrite."""
    root, p = _repo(tmp_path)
    a = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_text("alpha\nbeta   \t\ngamma\ndelta\n", encoding="utf-8")
    assert pin_for_ref(f"file:{p}:2", repo_root=root) == a


def test_pin_ignores_the_line_ending(tmp_path):
    """CRLF vs LF is not a content change either — though that one comes free
    from reading in text mode (universal newlines), not from the normalisation
    above. Kept as a regression test on the READ, not on the hashing."""
    root, p = _repo(tmp_path)
    a = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_bytes(LINES.replace("\n", "\r\n").encode())
    assert pin_for_ref(f"file:{p}:2", repo_root=root) == a


def test_no_pin_for_non_file_refs(tmp_path):
    root, _ = _repo(tmp_path)
    assert pin_for_ref("commit:deadbeef", repo_root=root) is None
    assert pin_for_ref("url:arxiv.org/abs/1", repo_root=root) is None
    assert pin_for_ref("", repo_root=root) is None


def test_no_pin_outside_the_repo_root(tmp_path):
    """Same containment rule as the verifier: no root, no read (CodeQL
    2026-07-18 — an absolute ref must not probe arbitrary server files)."""
    root, p = _repo(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    assert pin_for_ref(f"file:{outside}:1", repo_root=root) is None
    assert pin_for_ref(f"file:{p}:1", repo_root=None) is None


def test_no_pin_past_the_end_of_file(tmp_path):
    root, p = _repo(tmp_path)
    assert pin_for_ref(f"file:{p}:99", repo_root=root) is None


# --- verifying ------------------------------------------------------------

def test_unchanged_evidence_verifies_ok(tmp_path):
    root, p = _repo(tmp_path)
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "ok"


def test_edited_line_is_changed(tmp_path):
    root, p = _repo(tmp_path)
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_text("alpha\nBETA-EDITED\ngamma\ndelta\n", encoding="utf-8")
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "changed"


def test_a_shifted_but_trivial_line_is_changed(tmp_path):
    """An insertion above the citation is the common case, and reporting it as
    a content change would make the signal useless within a day — which is why
    `moved` exists. But it only applies above the distinctiveness floor: for a
    line like `beta` there is no way to tell a survived citation from a
    coincidence, and claiming otherwise would be the reassurance the
    adversarial review objected to. See the two tests below for both sides of
    the floor."""
    root, p = _repo(tmp_path)
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_text("header\nalpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "changed"


def test_a_trivial_line_is_never_reported_as_moved(tmp_path):
    """Adversarial review 2026-07-25 (glm-5.2 + deepseek-v4-pro, convergent
    2/2): `pass` — or `OK`, or `}` — occurs everywhere. Rewrite the file
    completely and the pinned text is still SOMEWHERE, so "moved" reads as
    reassurance while nothing of the citation survived. A line that carries
    no information cannot testify to its own survival: below the
    distinctiveness floor the honest answer is `changed`.
    """
    root = tmp_path
    p = tmp_path / "u.py"
    p.write_text("def f():\n    pass\n", encoding="utf-8")
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_text("def totally_different(x):\n    return x * 2\n\n"
                 "def g():\n    pass\n", encoding="utf-8")
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "changed"


def test_a_distinctive_line_still_reports_moved(tmp_path):
    """The floor must not eat the case `moved` exists for."""
    root, p = _repo(tmp_path)
    p.write_text("alpha\nthe parser rejects malformed headers\ngamma\n",
                 encoding="utf-8")
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.write_text("header\nalpha\nthe parser rejects malformed headers\ngamma\n",
                 encoding="utf-8")
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "moved"


def test_deleted_file_is_unresolvable(tmp_path):
    root, p = _repo(tmp_path)
    pin = pin_for_ref(f"file:{p}:2", repo_root=root)
    p.unlink()
    assert verify_pin(f"file:{p}:2", pin, repo_root=root) == "unresolvable"


def test_truncated_file_is_unresolvable(tmp_path):
    root, p = _repo(tmp_path)
    pin = pin_for_ref(f"file:{p}:4", repo_root=root)
    p.write_text("alpha\n", encoding="utf-8")
    assert verify_pin(f"file:{p}:4", pin, repo_root=root) == "unresolvable"


def test_the_unresolved_marker_verifies_as_unresolvable(tmp_path):
    """The marker records that nothing was ever pinned. Comparing it against
    today's file and calling the difference `changed` would invent a history
    that never existed."""
    root, p = _repo(tmp_path)
    assert verify_pin(f"file:{p}:2", "unresolved", repo_root=root) == "unresolvable"


def test_missing_pin_is_unresolvable_not_ok(tmp_path):
    """A receipt written before pinning existed must never read as verified."""
    root, p = _repo(tmp_path)
    assert verify_pin(f"file:{p}:2", None, repo_root=root) == "unresolvable"
    assert verify_pin(f"file:{p}:2", "", repo_root=root) == "unresolvable"


# --- end to end, on the real receipt --------------------------------------

def test_write_receipt_pins_what_it_cited(tmp_path, monkeypatch):
    """The whole point, end to end: cite a line, edit the file, and the
    RECEIPT can now tell that the evidence no longer says what it said."""
    from verimem.client import Memory

    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    root, p = _repo(tmp_path)
    m = Memory(path=tmp_path / "m.db", repo_root=root)
    ref = f"file:{p}:2"
    r = m.add("The parser reads beta on the second line.", topic="t",
              verified_by=[ref])
    assert r.get("stored"), r

    row = m.audit_log(limit=1)[0]
    assert row["pins"].get(ref, "").startswith("sha256:")
    assert verify_pin(ref, row["pins"][ref], repo_root=root) == "ok"

    p.write_text("alpha\nBETA-EDITED\ngamma\ndelta\n", encoding="utf-8")
    assert verify_pin(ref, row["pins"][ref], repo_root=root) == "changed"
    assert m.audit_verify() is None, "pinning must not break the chain"


def test_an_unresolvable_file_ref_is_recorded_as_such(tmp_path, monkeypatch):
    """Adversarial review 2026-07-25 (glm-5.2, Q6.5): a row with no pins was
    ambiguous — pre-feature row, or post-feature row whose ref did not
    resolve? Citing a non-existent file:line produced silence indistinguishable
    from legacy, so the absence of a pin proved nothing. Now an unresolvable
    `file:` ref is recorded EXPLICITLY, and only refs that were never
    pinnable at all (commit:, url:) stay silent."""
    from verimem.client import Memory

    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    root, _p = _repo(tmp_path)
    m = Memory(path=tmp_path / "m.db", repo_root=root)
    ghost = f"file:{root / 'src' / 'gone.py'}:3"
    m.add("The parser reads beta on the second line.", topic="t",
          verified_by=[ghost])
    assert m.audit_log(limit=1)[0]["pins"] == {ghost: "unresolved"}


def test_receipt_without_file_refs_records_no_pins(tmp_path, monkeypatch):
    """Nothing to pin → empty map → the chained payload stays v1-identical."""
    from verimem.client import Memory

    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    root, _p = _repo(tmp_path)
    m = Memory(path=tmp_path / "m.db", repo_root=root)
    m.add("The office is on the second floor.", topic="t",
          verified_by=["commit:deadbeef"])
    assert m.audit_log(limit=1)[0]["pins"] == {}
