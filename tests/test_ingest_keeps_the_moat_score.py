"""The ingest path judges every extracted fact and throws the verdict away.

`conversation_ingest._grounds` runs the CE over (dialogue, extracted fact) and
returns a bool: the score decides quarantine and is then discarded. So a fact
extracted from a conversation — where the source exists BY CONSTRUCTION, it is
the dialogue it came from — is stored with grounding_score NULL, identical to a
fact nobody ever checked.

Seen live 2026-07-29 importing a two-message conversation:

    [model_claim moat=--] The user's production billing service runs on port 8443
    [model_claim moat=--] The user's production database is PostgreSQL 16

Both were judged, both passed, and the store cannot say so. That matters most on
exactly this path: import is the cold-start story, so it is where a new user's
corpus comes from, and it would arrive looking entirely unverified.

Same defect the read surfaces had this morning (ca85cb0a) — the verdict is
computed and dropped on the way out.
"""
from __future__ import annotations

import pytest

DIALOGO = (
    "human: Su quale porta gira il servizio di fatturazione in produzione?\n"
    "assistant: Il servizio di fatturazione ascolta sulla porta 8443 in "
    "produzione, dietro il reverse proxy nginx."
)


def _ce_or_skip():
    from verimem import local_grounding
    if not local_grounding.local_ce_available():
        pytest.skip("local CE model not installed")


def test_grounds_reports_the_score_it_used():
    """The number exists; the signature has to carry it out."""
    _ce_or_skip()
    from verimem.conversation_ingest import _grounds
    ok, score = _grounds(DIALOGO, "The billing service listens on port 8443.")
    assert ok is True
    assert isinstance(score, float), f"no score returned: {score!r}"
    assert 0.0 <= score <= 100.0


def test_a_fact_the_dialogue_does_not_carry_is_scored_too():
    """A quarantine decision is also a verdict, and worth recording — otherwise
    a held-back fact and an unchecked one look the same in the store."""
    _ce_or_skip()
    from verimem.conversation_ingest import _grounds
    ok, score = _grounds(DIALOGO, "The billing service was migrated to Kubernetes.")
    assert isinstance(score, float)
    assert ok is False or score < 100.0


def test_no_judge_means_no_score_not_a_zero(monkeypatch):
    """Fail-open must stay fail-open: without a CE the ingest admits, and the
    fact is recorded as NEVER JUDGED rather than judged-and-failed."""
    from verimem import conversation_ingest as ci
    monkeypatch.setattr("verimem.local_grounding.try_local_score",
                        lambda *_a, **_k: None)
    ok, score = ci._grounds(DIALOGO, "qualunque cosa")
    assert ok is True
    assert score is None


def test_imported_facts_carry_the_verdict(tmp_path):
    """End to end: the number reaches the stored row.

    The extraction llm is a stub returning one known fact — what is under test
    is the PATH the verdict takes to the database, not how well a model reads a
    dialogue. The CE is the real one, so the score is a real score.
    """
    _ce_or_skip()
    import sqlite3
    import types

    from verimem.conversation_ingest import ingest_conversation
    from verimem.semantic import SemanticMemory

    class _Extractor:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(
                text="The billing service listens on port 8443.")

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = ingest_conversation(
        sm,
        [{"role": "user", "content": "Su quale porta gira il servizio di "
                                     "fatturazione in produzione?"},
         {"role": "assistant", "content": "Il servizio di fatturazione ascolta "
                                          "sulla porta 8443 in produzione."}],
        llm=_Extractor(), conversation_id="conv-test", topic="test/ingest",
        ground=True,
    )
    assert res.get("stored"), f"nothing stored: {res}"

    con = sqlite3.connect(str(sm.db_path))
    rows = con.execute("SELECT proposition, grounding_score FROM facts").fetchall()
    con.close()
    assert rows, "nothing stored"
    judged = [r for r in rows if r[1] is not None]
    assert judged, (
        "every imported fact was checked against its own dialogue and none "
        f"carries the score: {rows}"
    )


def test_the_import_command_asks_for_the_moat(tmp_path):
    """`verimem import` is the cold-start path and it did not run the check.

    `ingest_conversation(..., ground=False)` is the default, and
    import_conversations never passed the argument — while the SDK's `balanced`
    preset passes ground=True, so `Memory.add(messages)` judged and the CLI
    import did not. Same split as the write moat on the MCP channel this
    morning (7b8af116), one channel over.

    It matters most here: import is where a new user's corpus comes from, and
    the source is free — the dialogue the fact was extracted from.
    """
    _ce_or_skip()
    import json
    import sqlite3
    import types

    from verimem.import_conversations import import_conversations
    from verimem.semantic import SemanticMemory

    class _Extractor:
        def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
            return types.SimpleNamespace(
                text="The billing service listens on port 8443.")

    export = tmp_path / "export.json"
    export.write_text(json.dumps([{
        "uuid": "c1", "name": "Produzione",
        "updated_at": "2026-07-20T10:00:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Su quale porta gira il servizio di "
                                        "fatturazione?"},
            {"sender": "assistant", "text": "Il servizio di fatturazione "
                                            "ascolta sulla porta 8443."},
        ],
    }]), encoding="utf-8")

    sm = SemanticMemory(db_path=tmp_path / "s.db")
    rep = import_conversations(sm, str(export), llm=_Extractor(), ids=["c1"])
    assert rep.get("stored"), f"nothing imported: {rep}"

    con = sqlite3.connect(str(sm.db_path))
    rows = con.execute("SELECT proposition, grounding_score FROM facts").fetchall()
    con.close()
    assert [r for r in rows if r[1] is not None], (
        f"imported against its own dialogue and never judged: {rows}"
    )
