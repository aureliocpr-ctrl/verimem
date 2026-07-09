"""UX import: filtri per titolo/data/progetto — la selezione diventa umana.

Il consent-first esiste già (lista-e-basta senza selezione); il gap è la
SELEZIONE: con centinaia di conversazioni scegliere per uuid esatto è
inutilizzabile. Filtri componibili: ``--match`` (titolo, case-insensitive),
``--since`` (updated_at >= data), ``--project`` (l'export claude.ai porta il
progetto della conversazione quando esiste — parsing DIFENSIVO: campo assente
-> None, mai un crash). ``--all-matching`` importa l'intero sottoinsieme
filtrato: il filtro esplicito È il consenso.
"""
from __future__ import annotations

import json

import pytest

from engram.import_conversations import filter_conversations, list_conversations

_CLAUDE_EXPORT = [
    {"uuid": "aaa", "name": "Verimem gateway design",
     "updated_at": "2026-07-01T10:00:00Z",
     "project": {"uuid": "p1", "name": "verimem"},
     "chat_messages": [{"sender": "human", "text": "hi"},
                       {"sender": "assistant", "text": "hello"}]},
    {"uuid": "bbb", "name": "Ricette della nonna",
     "updated_at": "2026-01-15T10:00:00Z",
     "chat_messages": [{"sender": "human", "text": "lasagna?"}]},
    {"uuid": "ccc", "name": "Verimem multilingual bug",
     "updated_at": "2026-07-09T09:00:00Z",
     "project": {"uuid": "p1", "name": "verimem"},
     "chat_messages": [{"sender": "human", "text": "8/10 languages"}]},
    {"uuid": "ddd", "name": "Piano viaggio Dolomiti",
     "updated_at": "2026-06-20T10:00:00Z",
     "project": {"uuid": "p2", "name": "personale"},
     "chat_messages": [{"sender": "human", "text": "agosto"}]},
]


@pytest.fixture()
def export_file(tmp_path):
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(_CLAUDE_EXPORT), encoding="utf-8")
    return p


def test_list_exposes_project_when_present(export_file):
    convs = list_conversations(export_file)
    by_id = {c["id"]: c for c in convs}
    assert by_id["aaa"]["project"] == "verimem"
    assert by_id["bbb"]["project"] is None, "campo assente -> None, mai KeyError"
    assert by_id["ddd"]["project"] == "personale"


def test_filter_by_title_match(export_file):
    convs = list_conversations(export_file)
    hit = filter_conversations(convs, match="verimem")
    assert {c["id"] for c in hit} == {"aaa", "ccc"}, "match titolo case-insensitive"


def test_filter_by_since(export_file):
    convs = list_conversations(export_file)
    hit = filter_conversations(convs, since="2026-06-01")
    assert {c["id"] for c in hit} == {"aaa", "ccc", "ddd"}


def test_filter_by_project(export_file):
    convs = list_conversations(export_file)
    hit = filter_conversations(convs, project="verimem")
    assert {c["id"] for c in hit} == {"aaa", "ccc"}


def test_filters_compose(export_file):
    convs = list_conversations(export_file)
    hit = filter_conversations(convs, project="verimem", since="2026-07-05")
    assert {c["id"] for c in hit} == {"ccc"}


def test_no_filters_returns_everything(export_file):
    convs = list_conversations(export_file)
    assert filter_conversations(convs) == convs


def test_filter_handles_missing_updated_at():
    """Conversazioni senza data: escluse da --since (non si può affermare che
    siano recenti), MAI un crash."""
    convs = [{"id": "x", "title": "t", "project": None, "updated_at": None,
              "n_messages": 1, "format": "claude"}]
    assert filter_conversations(convs, since="2026-01-01") == []
    assert filter_conversations(convs, match="t") == convs


def test_chatgpt_rows_have_project_none(tmp_path):
    """Formato chatgpt: il campo project esiste nella riga (None) — le UI a
    valle iterano chiavi uniformi, mai KeyError cross-formato."""
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps([{
        "conversation_id": "c1", "title": "GPT chat", "update_time": 1750000000,
        "mapping": {"n1": {"message": {
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["hello"]},
            "create_time": 1750000000}}},
    }]), encoding="utf-8")
    convs = list_conversations(p)
    assert convs[0]["project"] is None
