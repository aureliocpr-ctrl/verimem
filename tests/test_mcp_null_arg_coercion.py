"""Audit#2 2026-06-08 A10: ~236 MCP arg sites do `int(arguments.get("k", 5))`.
When a client sends `{"k": null}` the key EXISTS, so `.get` returns None (NOT
the default), and int(None)/float(None) raised TypeError — a tool crash on a
benign null. The dispatcher now drops None-valued keys before validation so
every get(key, default) falls back correctly; a null for a REQUIRED field still
fails validation cleanly. The risk is over-dropping falsy-but-valid values, so
this pins that 0 / 0.0 / False / "" / [] are KEPT.
"""
from __future__ import annotations

from verimem import mcp_server


def test_drop_none_args_removes_only_none():
    out = mcp_server._drop_none_args({"k": None, "q": "x", "limit": 5})
    assert out == {"q": "x", "limit": 5}


def test_drop_none_args_keeps_falsy_but_valid():
    # The dangerous failure mode would be dropping a legitimate 0/False/""/[]
    # and silently reverting to a different default — these MUST survive.
    args = {"k": 0, "ratio": 0.0, "flag": False, "s": "", "xs": [], "n": 7}
    assert mcp_server._drop_none_args(args) == args


def test_drop_none_args_empty_and_allnone():
    assert mcp_server._drop_none_args({}) == {}
    assert mcp_server._drop_none_args({"a": None, "b": None}) == {}
