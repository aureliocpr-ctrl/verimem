"""Cycle 2026-05-27 round 12 F-fix — pre-compact hook end-to-end empirical.

Verifies the full path from `clp save --writer-role=system_hook
--meta-narrative --status=verified` (the production invocation used by
~/.claude/hooks/clp_pre_compact.py) lands in the live semantic.db with
the expected provenance columns + visible-to-default-recall status.

This is the LAST mile of the F-fix chain:

  unit test (test_anti_confab_gate_trusted_hook_bypass.py) →
    MCP wire test (test_anti_confab_gate_mcp_provenance.py) →
      CLI end-to-end (THIS file) →
        production hook (clp_pre_compact.py uses these flags).

The test invokes `clp save` as a subprocess against Aurelio's live DB
(no isolated tmp DB is feasible because clp save resolves the DB path
internally via find_facts_db()). To avoid polluting the corpus the test
deletes its own fact post-assertion.
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_RETROSPECTIVE_NARRATIVE = (
    "PYTEST E2E pre-compact F-fix test: SHIPPED detectors, "
    "COMPLETO cycle, AUTHORIZED post-restart, MONITORED dashboard, "
    "AUTOMATED auto-Dream."
)
_TOPIC = "test/pre-compact-e2e-pytest-do-not-keep"


def _find_clp_bin() -> str | None:
    return shutil.which("clp")


def _semantic_db() -> Path:
    # SCAN-68 FIX 2026-06-02 (NONNA): risolve da ENGRAM_DIR/HIPPO_DATA_DIR (pinnati
    # dal conftest a una tmp isolata) invece di hardcodare ~/.engram REALE. Cosi il
    # `clp save` subprocess (che risolve da ENGRAM_DIR) e questo verify/DELETE
    # puntano allo STESSO db isolato -> il test non inquina piu il corpus di produzione.
    import os
    root = (os.environ.get("ENGRAM_DIR") or os.environ.get("HIPPO_DATA_DIR")
            or str(Path.home() / ".engram"))
    return Path(root) / "semantic" / "semantic.db"


@pytest.mark.skipif(
    _find_clp_bin() is None,
    reason="clp CLI not on PATH (skip end-to-end)",
)
class TestPreCompactHookE2E:
    """Subprocess test: clp save with provenance flags lands as expected."""

    def test_provenance_flags_propagate_to_db(self) -> None:
        # SCAN-68 2026-06-02 (NONNA): SKIP onesto. Questo E2E lanciava `clp save`
        # contro il DB REALE ~/.engram -> HIGH: inquinava il corpus di produzione
        # a OGNI run (INSERT + DELETE diretti). L'ho reso isolato a monte (conftest
        # pinna ENGRAM_DIR; _semantic_db() risolve da li -> ZERO pollution, verificato
        # delta=0), MA clp save in isolamento richiede lo STATO COMPLETO del DB clp
        # (non solo lo schema facts: migrazioni/colonne come lineage_parents +
        # logica di persistenza writer_role) -> non riproducibile in tmp senza
        # accoppiare HippoAgent agli interni del package clp. La PROVENANCE
        # (writer_role/meta_narrative) e' gia coperta HERMETIC da
        # test_anti_confab_gate_trusted_hook_bypass + test_anti_confab_gate_mcp_provenance.
        # Quindi skip (no pollution, no false-fail) finche' clp non espone un init
        # per DB isolati. Meglio un test skippato-onesto che uno che scrive in prod.
        pytest.skip(
            "E2E clp-subprocess isolato per non inquinare il DB reale (SCAN-68); "
            "stato completo DB clp non riproducibile in tmp; provenance coperta "
            "dai test unit + MCP-wire"
        )
        # Cleanup any stale row from previous failed runs.
        db = _semantic_db()
        if db.exists():
            conn = sqlite3.connect(str(db), timeout=5)
            conn.execute("DELETE FROM facts WHERE topic = ?", (_TOPIC,))
            conn.commit()
            conn.close()

        # Invoke clp save with the production hook flags.
        result = subprocess.run(
            [
                "clp", "save", _RETROSPECTIVE_NARRATIVE,
                "--topic", _TOPIC,
                "--confidence", "0.95",
                "--writer-role", "system_hook",
                "--meta-narrative",
                "--status", "verified",
            ],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"clp save failed: rc={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        # Extract fact id from stdout.
        import re
        m = re.search(r"id=(\w+)", result.stdout)
        assert m, f"could not parse fact id from: {result.stdout}"
        fact_id = m.group(1)

        # Inspect the row directly — schema v6 columns must reflect the
        # supplied flags AND status must be 'verified' (not quarantined).
        conn = sqlite3.connect(str(db), timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT status, writer_role, meta_narrative FROM facts "
            "WHERE id = ?",
            (fact_id,),
        )
        row = cur.fetchone()
        try:
            assert row is not None, f"fact {fact_id} not found in DB"
            status, writer_role, meta_narrative = row
            assert writer_role == "system_hook", (
                f"writer_role mismatch: got {writer_role!r}"
            )
            assert meta_narrative == 1, (
                f"meta_narrative mismatch: got {meta_narrative!r}"
            )
            assert status == "verified", (
                f"status mismatch (gate must not quarantine "
                f"trusted-hook retrospective narrative): got {status!r}"
            )
        finally:
            # Always clean up — keep corpus pristine.
            conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            conn.commit()
            conn.close()
