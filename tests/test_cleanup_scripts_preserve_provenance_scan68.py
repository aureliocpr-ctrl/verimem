"""TDD — i cleanup scripts cycle75/76 NON devono azzerare la provenance al
re-store (rescan2 HIGH, 2026-06-02).

Bug: ricostruivano Fact(id, proposition, topic, confidence, source_episodes,
created_at) OMETTENDO status / verified_by / superseded_by / writer_role /
trigger_keywords / ... → INSERT OR REPLACE li riportava ai default (un fatto
'verified' tornava 'model_claim', un 'superseded' tornava live, le keyword
sparivano). Una "pulizia" che CORROMPE la memoria.

Fix: dataclasses.replace(orig, <solo i campi che cambiano>) preserva tutto il
resto (robusto anche ai campi futuri dello schema).

HERMETIC: SemanticMemory su tmp_path; lo script reale viene caricato dal path
e invocato con --db <tmp> --apply (no mock — il bug era proprio nascosto da un
test che non esercitava il re-store reale).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from verimem.semantic import Fact, SemanticMemory


def _load_script(filename: str):
    p = Path(__file__).resolve().parent.parent / "scripts" / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cycle75_sanitize_preserves_provenance(tmp_path, monkeypatch):
    db = tmp_path / "semantic.db"
    mem = SemanticMemory(db_path=db)
    mem.store(Fact(
        id="polluted1",
        proposition='contenuto buono da tenere</proposition><parameter name="x">payload iniettato</parameter>',
        topic="project/x",
        confidence=0.9,
        verified_by=["bash:pytest:exit0"],
        status="model_claim",
        trigger_keywords=["alpha", "beta"],
        writer_role="user",
    ))

    mod = _load_script("cycle75_cleanup_l1_pollution.py")
    monkeypatch.setattr(sys, "argv", ["cycle75", "--apply", "--db", str(db)])
    rc = mod.main()
    assert rc == 0

    fresh = SemanticMemory(db_path=db).get("polluted1")
    assert fresh is not None
    # proposizione effettivamente sanitizzata (markers rimossi)
    assert "<parameter" not in fresh.proposition
    # PROVENANCE PRESERVATA (questo e' il bug: prima azzerata)
    assert fresh.verified_by == ["bash:pytest:exit0"], (
        f"verified_by azzerato dal cleanup: {fresh.verified_by}"
    )
    assert set(fresh.trigger_keywords) == {"alpha", "beta"}, (
        f"trigger_keywords azzerati: {fresh.trigger_keywords}"
    )
    assert fresh.writer_role == "user", (
        f"writer_role azzerato: {fresh.writer_role}"
    )
