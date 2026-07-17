"""search_facts must treat the query as a LITERAL substring, not a SQL LIKE
glob (correctness-hunt #3, HIGH-3).

The proposition match builds `LOWER(proposition) LIKE ?` with the parameter
`%{term}%` but — unlike the sibling `topic LIKE ? ESCAPE '\\'` clause — never
escapes the LIKE wildcards `%` and `_` in the user term. So a search for
`node_engine` silently became `%node_engine%`, where `_` is a single-char
glob that also matches `nodeXengine`, `node-engine`, … ; a search for `50%`
became `%50%%` and matched `5000`. The keyword search over-returned unrelated
facts whenever the query contained `_` or `%` — common in code identifiers.

RED markers: pre-fix the `_`/`%` in the query act as globs and surface a
fact that does NOT contain the literal term.
"""
from __future__ import annotations

import time
from pathlib import Path

from verimem.semantic import Fact, SemanticMemory


def _ids(facts) -> set[str]:
    return {f.id for f in facts}


def _store(sm: SemanticMemory, fid: str, prop: str) -> None:
    now = time.time()
    sm.store(Fact(id=fid, proposition=prop, topic="cap/x",
                  created_at=now, last_verified_at=now), embed="defer")


def test_underscore_is_literal_not_single_char_glob(tmp_path: Path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _store(sm, "lit", "the node_engine module boots the worker")
    _store(sm, "glob", "the nodeXengine module boots the worker")
    got = _ids(sm.search_facts("node_engine", limit=10))
    assert "lit" in got, "the literal node_engine fact must match"
    assert "glob" not in got, (
        "'_' must be a literal, not a single-char LIKE glob matching nodeXengine"
    )


def test_percent_is_literal_not_multi_char_glob(tmp_path: Path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _store(sm, "lit", "apply a 50% discount at checkout")
    _store(sm, "glob", "apply a 5000 discount at checkout")
    got = _ids(sm.search_facts("50%", limit=10))
    assert "lit" in got, "the literal 50% fact must match"
    assert "glob" not in got, "'%' must be a literal, not a multi-char LIKE glob"


def test_underscore_literal_in_AND_token_mode(tmp_path: Path) -> None:
    """The multi-token AND branch (require_all_tokens) escapes too."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _store(sm, "lit", "node_engine boots fine")
    _store(sm, "glob", "nodeXengine boots fine")
    got = _ids(sm.search_facts("node_engine boots",
                               limit=10, require_all_tokens=True))
    assert "lit" in got
    assert "glob" not in got, "'_' must stay literal in the AND token branch"


def test_plain_substring_still_matches(tmp_path: Path) -> None:
    """Control: a wildcard-free query keeps matching every superstring —
    the escape must not over-restrict ordinary searches."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _store(sm, "a", "apply a 50% discount at checkout")
    _store(sm, "b", "apply a 5000 discount at checkout")
    got = _ids(sm.search_facts("discount", limit=10))
    assert got == {"a", "b"}, "a plain substring must still match both facts"
