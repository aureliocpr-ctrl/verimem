"""WF3 capture-reliability: skip sidechain turns + subagent/journal files."""
import json
from pathlib import Path

from verimem.transcript_ingest import _is_real_session_file, find_current_session, parse_turns


def _write(p, records):
    p.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def test_parse_turns_skips_sidechain(tmp_path):
    f = tmp_path / "s.jsonl"
    _write(f, [
        {"type": "user", "uuid": "u1", "message": {"role": "user", "content": "real main turn content here that is long enough"}},
        {"type": "assistant", "uuid": "u2", "isSidechain": True, "message": {"role": "assistant", "content": "subagent sidechain content long enough to pass noise"}},
    ])
    turns = parse_turns(f)
    assert [t.id for t in turns] == ["u1"]   # sidechain dropped


def test_is_real_session_file_filters(tmp_path):
    assert _is_real_session_file(tmp_path / "1234abcd-0000-0000-0000-0000abcd.jsonl")
    assert not _is_real_session_file(tmp_path / "agent-foo.jsonl")
    assert not _is_real_session_file(tmp_path / "journal.jsonl")
    assert not _is_real_session_file(tmp_path / "subagents" / "x.jsonl")


def test_find_current_skips_transient_subagent(tmp_path):
    proj = tmp_path / "proj"; (proj / "subagents").mkdir(parents=True)
    real = proj / "aaaa-real.jsonl"; real.write_text('{"type":"user"}', encoding="utf-8")
    agent = proj / "agent-transient.jsonl"; agent.write_text('{"type":"user"}', encoding="utf-8")
    import os
    import time
    os.utime(agent, (time.time() + 100, time.time() + 100))  # agent file is NEWER
    assert find_current_session(proj) == real   # still picks the real session, not the newer agent tape
