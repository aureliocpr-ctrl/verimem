"""CLI entrypoint dell'ingest Tier C (engram.transcript_ingest.main).

Abilita l'auto-cattura (un SessionEnd hook chiamerà questo entrypoint), ma
restando in-repo e testabile: NON installa alcun hook standing.

Invarianti:
  - find_current_session restituisce la sessione .jsonl piu' recente (mtime).
  - main(--session) ingesta un singolo file nel Tier C (onora HIPPO_TRANSCRIPT_DB).
  - main(--current --projects-dir DIR) ingesta la sessione piu' recente di DIR.

Hermetic: file .jsonl sintetici + DB Tier C temporaneo via env.
"""
from __future__ import annotations

import json
import os

from engram.transcript_index import TranscriptIndex
from engram.transcript_ingest import find_current_session, main

_REC = [{
    "type": "user", "uuid": "x1", "sessionId": "S",
    "timestamp": "2026-05-13T07:55:31.076Z",
    "message": {"role": "user",
                "content": "un messaggio utente abbastanza lungo per superare il filtro minimo"},
}]


def _wj(path, recs):
    path.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")


def test_find_current_session_picks_newest(tmp_path):
    a, b = tmp_path / "A.jsonl", tmp_path / "B.jsonl"
    _wj(a, _REC)
    _wj(b, _REC)
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))  # b piu' recente
    assert find_current_session(tmp_path) == b


def test_find_current_session_none_when_empty(tmp_path):
    assert find_current_session(tmp_path) is None


def test_cli_ingest_single_session(tmp_path, monkeypatch):
    f = tmp_path / "S.jsonl"
    _wj(f, _REC)
    monkeypatch.setenv("HIPPO_TRANSCRIPT_DB", str(tmp_path / "tc.db"))
    rc = main(["--session", str(f)])
    assert rc == 0
    assert TranscriptIndex().count() == 1


def test_cli_current_default_uses_newest(tmp_path, monkeypatch):
    f = tmp_path / "S.jsonl"
    _wj(f, _REC)
    monkeypatch.setenv("HIPPO_TRANSCRIPT_DB", str(tmp_path / "tc.db"))
    rc = main(["--current", "--projects-dir", str(tmp_path)])
    assert rc == 0
    assert TranscriptIndex().count() == 1
