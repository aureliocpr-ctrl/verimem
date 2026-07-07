"""Onboarding import — cold-start the memory from past conversations (roadmap #2).

First-run problem: a new Verimem store is empty, so the first sessions feel
valueless. Every user already HAS months of conversations in ChatGPT / Claude:
this module parses their standard data exports, lists the conversations so the
user can consent PER conversation, and ingests only the selected ones through
``ingest_conversation`` — i.e. the anti-confab gate, provenance and (optionally)
the identity fix (``user_name``) apply to imported memories exactly as to live
ones. Privacy-first by construction: nothing is imported without an explicit
selection; the API takes ``ids`` and the CLI owns the ask.

Supported formats (auto-detected):
  - ``chatgpt``: OpenAI data export ``conversations.json`` (mapping tree);
  - ``claude``:  claude.ai data export ``conversations.json`` (chat_messages);
  - ``generic``: a plain JSON list of ``{"role", "content"}`` messages, or
    ``{"messages": [...]}`` — the escape hatch for any other tool.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .conversation_ingest import ingest_conversation

__all__ = ["detect_format", "list_conversations", "load_conversation",
           "import_conversations"]


def _read_json(path: Path | str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def detect_format(path: Path | str) -> str:
    """``chatgpt`` | ``claude`` | ``generic`` — by structure, not filename."""
    data = _read_json(path)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        first = data[0]
        if "mapping" in first:
            return "chatgpt"
        if "chat_messages" in first:
            return "claude"
        if "role" in first and "content" in first:
            return "generic"
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return "generic"
    raise ValueError(f"unrecognized conversation-export format: {path}")


# --- per-format normalizers ------------------------------------------------
def _chatgpt_messages(conv: dict) -> list[dict]:
    """Linearize the mapping tree: text nodes ordered by create_time."""
    nodes = []
    for node in (conv.get("mapping") or {}).values():
        msg = (node or {}).get("message") or {}
        content = msg.get("content") or {}
        role = ((msg.get("author") or {}).get("role") or "").strip()
        if content.get("content_type") != "text" or role not in ("user", "assistant"):
            continue
        text = "\n".join(str(part) for part in (content.get("parts") or []) if part)
        if not text.strip():
            continue
        nodes.append((msg.get("create_time") or float("inf"), role, text))
    nodes.sort(key=lambda t: t[0])
    return [{"role": r, "content": c} for _, r, c in nodes]


def _claude_messages(conv: dict) -> list[dict]:
    out = []
    for m in conv.get("chat_messages") or []:
        text = (m.get("text") or "").strip()
        if not text:
            continue
        role = "user" if (m.get("sender") == "human") else "assistant"
        out.append({"role": role, "content": text})
    return out


def _generic_messages(data: Any) -> list[dict]:
    msgs = data.get("messages") if isinstance(data, dict) else data
    out = []
    for m in msgs or []:
        c = (m.get("content") or "").strip()
        if c:
            out.append({"role": m.get("role", "user"), "content": c})
    return out


# --- public API --------------------------------------------------------------
def list_conversations(path: Path | str) -> list[dict]:
    """One row per conversation — what the consent UX shows the user.

    ``{id, title, n_messages, format, updated_at}``; NO message content leaves
    this function (the user decides from metadata, content stays private until
    an explicit import).
    """
    fmt = detect_format(path)
    data = _read_json(path)
    out: list[dict] = []
    if fmt == "chatgpt":
        for conv in data:
            out.append({
                "id": str(conv.get("conversation_id") or conv.get("id") or ""),
                "title": conv.get("title") or "(untitled)",
                "n_messages": len(_chatgpt_messages(conv)),
                "format": fmt,
                "updated_at": conv.get("update_time"),
            })
    elif fmt == "claude":
        for conv in data:
            out.append({
                "id": str(conv.get("uuid") or ""),
                "title": conv.get("name") or "(untitled)",
                "n_messages": len(_claude_messages(conv)),
                "format": fmt,
                "updated_at": conv.get("updated_at"),
            })
    else:  # generic — the file IS one conversation
        msgs = _generic_messages(data)
        out.append({"id": "generic-1", "title": Path(path).name,
                    "n_messages": len(msgs), "format": fmt, "updated_at": None})
    return out


def load_conversation(path: Path | str, conv_id: str) -> list[dict]:
    """Normalized ``[{"role", "content"}]`` for one conversation by id."""
    fmt = detect_format(path)
    data = _read_json(path)
    if fmt == "generic":
        return _generic_messages(data)
    for conv in data:
        cid = str(conv.get("conversation_id") or conv.get("uuid")
                  or conv.get("id") or "")
        if cid == str(conv_id):
            return (_chatgpt_messages(conv) if fmt == "chatgpt"
                    else _claude_messages(conv))
    return []


def import_conversations(
    semantic_memory,
    path: Path | str,
    *,
    llm: Any,
    ids: list[str] | None,
    user_name: str | None = None,
    topic: str = "conversational/imported",
    consolidate: bool = True,
    embed: str | None = None,
) -> dict:
    """Ingest ONLY the selected conversations through the anti-confab gate.

    ``ids`` is the user's explicit selection (consent lives with the caller: the
    CLI asks, an app shows checkboxes). ``ids=None`` means "all listed" and is
    reserved for callers that already obtained consent for everything.
    ``user_name`` flows to the extraction identity fix. Fail-safe per
    conversation: one bad conversation never aborts the rest.
    """
    convs = list_conversations(path)
    selected = ([c for c in convs if c["id"] in set(ids)] if ids is not None
                else convs)
    rep = {"listed": len(convs), "imported": 0, "skipped": len(convs) - len(selected),
           "stored": 0, "rejected": 0, "errors": []}
    for c in selected:
        msgs = load_conversation(path, c["id"])
        if not msgs:
            rep["errors"].append(f"{c['id']}: empty/unreadable")
            continue
        res = ingest_conversation(
            semantic_memory, msgs, llm=llm,
            conversation_id=f"import:{c['format']}:{c['id']}",
            topic=topic, consolidate=consolidate, embed=embed,
            user_name=user_name)
        rep["imported"] += 1
        rep["stored"] += res.get("stored", 0)
        rep["rejected"] += res.get("rejected", 0)
        if res.get("error"):
            rep["errors"].append(f"{c['id']}: {res['error']}")
    return rep
