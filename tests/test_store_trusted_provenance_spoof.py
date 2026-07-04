"""FALSIFICAZIONE store-level (Popper) del provenance-skip composto — 2026-06-02.

Scoperta del loop NONNA+sorelle: il bypass anti-confab e' duplicato in DUE siti
sullo STESSO predicato (writer_role IN TRUSTED + meta_narrative), entrambi senza
token:
  - anti_confab_gate.py:507   (salta i detector L1.x)            <- gia coperto da
                                test_engram_gate_falsification.py::test_spoofed_...
  - semantic.py:627-633       (salta validate_verified_refs)     <- COPERTO QUI

I tre input (status, writer_role, meta_narrative) sono caller-controlled al
boundary MCP (mcp_server.py:10223 / :10242 / :10245). Quindi un client puo
scrivere un fact FABBRICATO come status='verified' (rank max) con verified_by
vuoto, saltando la verifica empirica delle prove.

Hermetic: SemanticMemory su DB temporaneo, repo_root=None (default paranoico).
Zero side-effect sul DB reale ~/.engram.
"""
from __future__ import annotations

import pytest

from engram.semantic import Fact, SemanticMemory

_CONFAB = "SHIPPED il modulo auth, completato e verificato in produzione, tutti i test passano"


def test_unspoofed_verified_without_valid_refs_is_demoted(tmp_path):
    """CONTROL (verde oggi): un verified senza ref verificabili degrada a model_claim.

    Isola lo spoof come unica causa del bypass: il path di demote FUNZIONA quando
    writer_role non e' privilegiato.
    """
    m = SemanticMemory(db_path=tmp_path / "s.db")  # repo_root=None -> nessun ref verifica
    f = Fact(
        id="ctrl1", proposition=_CONFAB, topic="handoff/x", confidence=0.9,
        status="verified", verified_by=[],
        writer_role="agent_inference", meta_narrative=False,
    )
    m.store(f)
    assert f.status == "model_claim", (
        f"verified senza ref validi deve degradare a model_claim, e' {f.status!r}"
    )


def test_store_trusted_hook_spoof_must_not_skip_provenance(tmp_path):
    """RED (fallisce oggi): writer_role=trusted_hook + meta_narrative spoofati dal
    client saltano validate_verified_refs (semantic.py:633 `and not _trusted_provenance`).

    Stesso identico fact del control ma con i due campi privilegiati settati:
    oggi resta status='verified' con verified_by vuoto -> fact fabbricato fidato.
    Dopo il fix (token-gate del predicato), senza token valido deve degradare.
    """
    m = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(
        id="spoof1", proposition=_CONFAB, topic="handoff/x", confidence=0.9,
        status="verified", verified_by=[],
        writer_role="trusted_hook", meta_narrative=True,
    )
    m.store(f)
    assert f.status != "verified", (
        "SPOOF: writer_role=trusted_hook+meta_narrative (caller-controlled via MCP) "
        "salta il provenance-check e fa persistere un fact fabbricato come verified"
    )
