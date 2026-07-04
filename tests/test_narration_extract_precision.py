"""Precision fixes (2026-06-19) to extract_atomic_candidates: no UUIDs/headings/fragments."""
from engram.narration import extract_atomic_candidates as ext


def test_rejects_raw_uuid_session_id():
    assert ext("originSessionId: 82f5aa75-856d-440a-855a-fa94384ef520") == []


def test_strips_markdown_emphasis_and_heading():
    got = ext("**L4-grounding** wired into anti_confab_gate.py")
    assert got == ["L4-grounding wired into anti_confab_gate.py"]


def test_rejects_bare_heading_fragment():
    assert ext("**R8 sopravvive**:") == []          # no anchor + heading noise


def test_keeps_real_atom_with_file_anchor():
    got = ext("Fixed the recall hang in semantic.py:165 under contention")
    assert any("semantic.py:165" in c and "*" not in c for c in got)


def test_keeps_real_atom_with_sha():
    got = ext("Shipped grounding_gate.py at origin/main 42266a0 with AUROC numbers")
    assert got and all("**" not in c for c in got)
