"""WF1 defense-in-depth: TranscriptIndex.store/store_batch redact secrets at the sink."""
from pathlib import Path

from verimem.transcript_index import TranscriptIndex, Turn

_P2 = 'ghp_'
_P4 = 'AKIA'


def _turn(i, text):
    return Turn(id=i, session_id="s", ts=1.0, role="user", text=text,
                source_path="p", source_offset=0)


def test_store_redacts_secret(tmp_path):
    ti = TranscriptIndex(db_path=tmp_path / "t.db")
    ti.store(_turn("t1", "deploy token " + _P2 + "1234567890abcdefABCDEF1234567890abcd here"))
    got = ti.get("t1")
    assert got is not None and "" + _P2 + "1234567890abcdefABCDEF1234567890abcd" not in got.text


def test_store_batch_redacts_secret(tmp_path):
    ti = TranscriptIndex(db_path=tmp_path / "t.db")
    ti.store_batch([_turn("t2", "aws " + _P4 + "1234567890ABCDEF rotated"),
                    _turn("t3", "no secret here just text content")])
    g2, g3 = ti.get("t2"), ti.get("t3")
    assert "" + _P4 + "1234567890ABCDEF" not in g2.text
    assert g3.text == "no secret here just text content"   # clean text unchanged
