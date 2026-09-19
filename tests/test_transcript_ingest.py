"""Ingest dei transcript .jsonl di Claude Code nel Tier C (verimem.transcript_ingest).

Invarianti:
  - parse_turns estrae SOLO testo conversazionale (user/assistant), salta
    queue-operation/system, rumore hook (<...>, system-reminder), turni corti.
  - id del turno = uuid del record (ID stabile) -> ingest IDEMPOTENTE: ri-ingest
    della stessa sessione NON duplica (added=0 al secondo giro). È il requisito
    di scala anti-inquinamento.
  - ts dal campo timestamp ISO (per ordinamento/retention).
  - blocchi non-text (tool_use) ignorati nell'estrazione del verbatim.

Hermetic: .jsonl sintetico in tmp_path, DB Tier C temporaneo.
"""
from __future__ import annotations

import json

from verimem.transcript_index import TranscriptIndex
from verimem.transcript_ingest import ingest_dir, ingest_session, parse_turns

_RECS = [
    {"type": "queue-operation", "uuid": "q0"},  # skip
    {"type": "system", "uuid": "s0",
     "message": {"role": "system", "content": "boot"}},  # skip (type)
    {"type": "user", "uuid": "u1", "sessionId": "S",
     "timestamp": "2026-05-13T07:55:31.076Z",
     "message": {"role": "user",
                 "content": "Questo e un messaggio utente abbastanza lungo da superare la soglia minima."}},
    {"type": "assistant", "uuid": "a1", "sessionId": "S",
     "timestamp": "2026-05-13T07:55:39.523Z",
     "message": {"role": "assistant",
                 "content": [
                     {"type": "text",
                      "text": "Risposta assistant con testo sufficiente per non essere scartata dal filtro."},
                     {"type": "tool_use", "name": "x", "input": {}},
                 ]}},
    {"type": "user", "uuid": "u2", "sessionId": "S",
     "message": {"role": "user",
                 "content": "<system-reminder>rumore hook</system-reminder> roba che non e conversazione"}},  # noise (<)
    {"type": "user", "uuid": "u3", "sessionId": "S",
     "message": {"role": "user", "content": "corto"}},  # too short
]


def _write_jsonl(path, recs):
    path.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")


def test_parse_turns_filters_and_uses_uuid(tmp_path):
    f = tmp_path / "S.jsonl"
    _write_jsonl(f, _RECS)
    turns = parse_turns(f)
    assert [t.id for t in turns] == ["u1", "a1"], "solo i 2 turni reali, id=uuid"
    assert turns[0].session_id == "S"
    assert turns[0].ts > 0, "timestamp ISO parsato a epoch"
    # blocco tool_use ignorato: resta solo il testo
    assert "Risposta assistant" in turns[1].text
    assert "tool_use" not in turns[1].text


def test_ingest_session_is_idempotent(tmp_path):
    f = tmp_path / "S.jsonl"
    _write_jsonl(f, _RECS)
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    r1 = ingest_session(f, idx)
    assert r1["added"] == 2 and r1["total"] == 2
    r2 = ingest_session(f, idx)  # re-ingest stessa sessione
    assert r2["added"] == 0, "re-ingest NON deve duplicare (id stabile=uuid)"
    assert r2["total"] == 2, "totale invariato"


def test_ingest_dir_walks_multiple_sessions(tmp_path):
    _write_jsonl(tmp_path / "A.jsonl", _RECS)
    _write_jsonl(tmp_path / "B.jsonl", [
        {**r, "uuid": r["uuid"] + "_b", "sessionId": "B"} for r in _RECS
    ])
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    summary = ingest_dir(projects_dir=tmp_path, index=idx, glob_pat="*.jsonl")
    assert summary["sessions"] == 2
    assert summary["total"] == 4, "2 turni reali per sessione x 2 sessioni"


def test_parse_fallback_id_is_content_stable_without_uuid(tmp_path):
    """Record SENZA uuid: il fallback id deve essere CONTENT-based (sessionId+text),
    NON posizionale -> stesso contenuto a offset/file diversi = stesso id, così
    l'idempotenza anti-pollution regge anche se il .jsonl viene riscritto/prependato."""
    rec = {"type": "user", "sessionId": "S",
           "message": {"role": "user",
                       "content": "contenuto identico abbastanza lungo per superare il filtro"}}
    f1 = tmp_path / "a.jsonl"
    _write_jsonl(f1, [rec])
    f2 = tmp_path / "b.jsonl"
    _write_jsonl(f2, [{"type": "system", "uuid": "sys0"}, rec])  # stesso rec, offset 1
    id1 = parse_turns(f1)[0].id
    id2 = parse_turns(f2)[0].id
    assert id1 == id2, "fallback id deve essere content-stable, non posizionale"
    assert id1.startswith("h:"), "fallback id e' un content-hash"


def test_parse_redacts_secrets(tmp_path):
    """L'ingest maschera i segreti incollati in chat PRIMA di persistere (finding HIGH)."""
    rec = {"type": "user", "uuid": "sek", "sessionId": "S",
           "message": {"role": "user",
                       "content": "la mia chiave api e' sk-abc123DEF456ghi789jkl012mno usala per il deploy"}}
    f = tmp_path / "S.jsonl"
    _write_jsonl(f, [rec])
    turns = parse_turns(f)
    assert turns, "il turno (dopo redaction resta lungo) deve restare"
    assert "sk-abc123DEF456ghi789jkl012mno" not in turns[0].text
    assert "REDACTED" in turns[0].text
