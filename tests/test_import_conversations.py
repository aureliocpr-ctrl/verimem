"""Onboarding import (roadmap #2, cold-start): parse standard chat exports
(ChatGPT / Claude / generic), LIST them so the user can consent per-conversation,
and ingest ONLY the selected ones through the gate (ingest_conversation).

Hermetic: stub LLM, tmp stores. The consent UX lives in the CLI; the API takes
an explicit selection (ids) — the caller owns consent.
"""
from __future__ import annotations

import json

from verimem.import_conversations import (
    detect_format,
    import_conversations,
    list_conversations,
    load_conversation,
)
from verimem.semantic import SemanticMemory


class _StubLLM:
    def __init__(self, text="Johnson Joseph likes tea"):
        self._text = text
        self.calls = []

    def complete(self, system, messages, **kw):
        self.calls.append({"system": system, "messages": messages})

        class R:
            text = self._text
        return R()


def _chatgpt_export(tmp_path):
    """Minimal but faithful ChatGPT conversations.json shape (mapping tree)."""
    data = [{
        "title": "Trip planning",
        "create_time": 1700000000.0,
        "update_time": 1700000500.0,
        "conversation_id": "cg-1",
        "mapping": {
            "n0": {"id": "n0", "message": None, "parent": None, "children": ["n1"]},
            "n1": {"id": "n1", "message": {
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": ["I want to visit Albi in July."]},
                "create_time": 1700000100.0}, "parent": "n0", "children": ["n2"]},
            "n2": {"id": "n2", "message": {
                "author": {"role": "assistant"},
                "content": {"content_type": "text", "parts": ["Albi is lovely in summer!"]},
                "create_time": 1700000200.0}, "parent": "n1", "children": []},
        },
    }]
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _claude_export(tmp_path):
    """Minimal claude.ai data-export conversations.json shape."""
    data = [{
        "uuid": "cl-1", "name": "Recipe ideas",
        "created_at": "2026-01-02T10:00:00Z", "updated_at": "2026-01-02T11:00:00Z",
        "chat_messages": [
            {"uuid": "m1", "sender": "human", "text": "I dislike snakes and cats.",
             "created_at": "2026-01-02T10:00:01Z"},
            {"uuid": "m2", "sender": "assistant", "text": "Noted!",
             "created_at": "2026-01-02T10:00:02Z"},
        ],
    }]
    p = tmp_path / "claude_export.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_detect_and_list_chatgpt(tmp_path) -> None:
    p = _chatgpt_export(tmp_path)
    assert detect_format(p) == "chatgpt"
    convs = list_conversations(p)
    assert len(convs) == 1
    c = convs[0]
    assert c["id"] == "cg-1" and c["title"] == "Trip planning"
    assert c["n_messages"] == 2 and c["format"] == "chatgpt"


def test_detect_and_list_claude(tmp_path) -> None:
    p = _claude_export(tmp_path)
    assert detect_format(p) == "claude"
    convs = list_conversations(p)
    assert convs[0]["id"] == "cl-1" and convs[0]["title"] == "Recipe ideas"
    assert convs[0]["n_messages"] == 2


def test_load_conversation_normalizes_messages(tmp_path) -> None:
    p = _chatgpt_export(tmp_path)
    msgs = load_conversation(p, "cg-1")
    assert msgs == [
        {"role": "user", "content": "I want to visit Albi in July."},
        {"role": "assistant", "content": "Albi is lovely in summer!"},
    ]
    q = _claude_export(tmp_path)
    msgs2 = load_conversation(q, "cl-1")
    assert msgs2[0] == {"role": "user", "content": "I dislike snakes and cats."}


def test_import_only_selected_ids_consent(tmp_path) -> None:
    """Consent: only the EXPLICITLY selected conversations are ingested."""
    p = _chatgpt_export(tmp_path)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM()
    rep = import_conversations(sm, p, llm=llm, ids=["cg-1"], embed="sync")
    assert rep["imported"] == 1 and rep["stored"] >= 1
    assert rep["skipped"] == 0

    rep2 = import_conversations(sm, p, llm=llm, ids=["nope"], embed="sync")
    assert rep2["imported"] == 0, "unselected conversations must NOT be ingested"


def test_import_passes_user_name_to_ingest(tmp_path) -> None:
    p = _claude_export(tmp_path)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    llm = _StubLLM()
    import_conversations(sm, p, llm=llm, ids=["cl-1"],
                         user_name="Johnson Joseph", embed="sync")
    assert any("Johnson Joseph" in c["system"] for c in llm.calls), \
        "identity fix must flow through the import path"


def test_generic_list_of_messages(tmp_path) -> None:
    p = tmp_path / "generic.json"
    p.write_text(json.dumps([{"role": "user", "content": "ciao"},
                             {"role": "assistant", "content": "ciao!"}]),
                 encoding="utf-8")
    assert detect_format(p) == "generic"
    convs = list_conversations(p)
    assert len(convs) == 1 and convs[0]["n_messages"] == 2
    msgs = load_conversation(p, convs[0]["id"])
    assert msgs[0]["content"] == "ciao"
