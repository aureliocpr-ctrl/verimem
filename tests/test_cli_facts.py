"""Cycle #138-bis (2026-05-18) — CLI ``engram facts`` cluster tests.

Aurelio gap identificato 2026-05-18: ``engram facts --help`` ritorna
"No such command 'facts'". L'unica via per ispezionare/manipolare la
memoria semantica via CLI è ``engram introspect`` (read-only) o lanciare
direttamente Python. Manca il pendant CLI delle 60+ tool MCP
``mcp__hippoagent__hippo_facts_*``.

Cycle 138-bis aggiunge un cluster typer ``engram facts`` con 8
sotto-comandi che coprono i casi d'uso operativi quotidiani:

  engram facts list            elenca fact recenti (table)
  engram facts recall QUERY    semantic recall su cosine
  engram facts search QUERY    keyword/substring search SQL
  engram facts get FACT_ID     dettaglio singolo fact
  engram facts forget FACT_ID  delete privacy/GDPR
  engram facts stats           conteggi per status
  engram facts anti-confab-scan   L2 scan_orphaned_facts report
  engram facts anti-confab-apply  L2 mark_orphaned (dry-run safe)

I test usano typer.testing.CliRunner contro la app real (no mock),
con un ENGRAM_DATA_DIR=tmp_path per isolamento del corpus utente.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engram.cli import app
from engram.semantic import Fact, SemanticMemory

runner = CliRunner()


@pytest.fixture
def isolated_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Point engram at an empty corpus under tmp_path so CLI commands
    operate on a known-shape store, not the user's live ~/.engram."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    # Seed a small fact set covering the status enum we care about.
    sem_dir = tmp_path / "semantic"
    sem_dir.mkdir(parents=True, exist_ok=True)
    sm = SemanticMemory(db_path=sem_dir / "semantic.db")
    sm.store(Fact(
        id="fact-alpha", proposition="Aurelio prefers Italian responses",
        topic="preferences/aurelio", confidence=0.95,
        verified_by=["url:transcript:2026-05-14"], status="verified",
    ))
    sm.store(Fact(
        id="fact-beta", proposition="Cycle 999 SHIPPED to main",
        topic="lab/cli138bis", confidence=0.9,
        verified_by=["commit:abc1234"], status="model_claim",
    ))
    sm.store(Fact(
        id="fact-quar", proposition="Cycle 888 SHIPPED to main",
        topic="lab/cli138bis", confidence=0.9,
        verified_by=[], status="quarantined",
    ))
    sm.store(Fact(
        id="fact-orph", proposition="Bug #44 DIAGNOSED as memory leak",
        topic="lab/cli138bis", confidence=0.9,
        verified_by=[], status="orphaned",
    ))
    return tmp_path


class TestFactsListCommand:
    """`engram facts list` exposes the recent corpus as a table."""

    def test_list_shows_facts(self, isolated_corpus: Path) -> None:
        r = runner.invoke(app, ["facts", "list", "--limit", "10"])
        assert r.exit_code == 0, r.output
        # Default view should expose the visible facts (verified +
        # model_claim) and hide orphaned + quarantined like recall does.
        assert "fact-alp" in r.output or "alpha" in r.output, r.output
        assert "fact-bet" in r.output or "beta" in r.output, r.output
        # Hidden by default — auditable via --include-hidden.
        assert "fact-quar"[:8] not in r.output, (
            "list default must hide quarantined (parity with recall)"
        )
        assert "fact-orph"[:8] not in r.output, (
            "list default must hide orphaned"
        )

    def test_list_include_hidden_flag(self, isolated_corpus: Path) -> None:
        r = runner.invoke(
            app, ["facts", "list", "--include-hidden", "--limit", "10"],
        )
        assert r.exit_code == 0, r.output
        # With the flag, quarantined + orphaned must appear.
        assert "quarantin" in r.output.lower() or "fact-qua" in r.output
        assert "orphan" in r.output.lower() or "fact-orp" in r.output


class TestFactsRecallCommand:
    def test_recall_finds_seeded_fact(self, isolated_corpus: Path) -> None:
        r = runner.invoke(
            app, ["facts", "recall", "Aurelio prefers Italian", "--k", "3"],
        )
        assert r.exit_code == 0, r.output
        assert "alpha" in r.output or "Italian" in r.output, r.output

    def test_recall_excludes_quarantined_by_default(
        self, isolated_corpus: Path,
    ) -> None:
        r = runner.invoke(
            app, ["facts", "recall", "Cycle 888 SHIPPED", "--k", "5"],
        )
        assert r.exit_code == 0
        # fact-quar (the SHIPPED one with status=quarantined) must NOT
        # be in the default recall — cycle 138 invariant.
        assert "fact-qua" not in r.output, (
            "cycle 138-bis: recall CLI must hide quarantined by default"
        )


class TestFactsSearchCommand:
    def test_search_keyword_matches(self, isolated_corpus: Path) -> None:
        r = runner.invoke(app, ["facts", "search", "Italian"])
        assert r.exit_code == 0, r.output
        assert "alpha" in r.output or "Italian" in r.output


class TestFactsGetCommand:
    def test_get_by_full_id(self, isolated_corpus: Path) -> None:
        r = runner.invoke(app, ["facts", "get", "fact-alpha"])
        assert r.exit_code == 0, r.output
        assert "Aurelio" in r.output or "Italian" in r.output
        # Provenance fields visible in detail view.
        assert "verified" in r.output.lower() or "verified_by" in r.output

    def test_get_missing_id_exits_nonzero(
        self, isolated_corpus: Path,
    ) -> None:
        r = runner.invoke(app, ["facts", "get", "nonexistent"])
        assert r.exit_code != 0
        assert "not found" in r.output.lower() or "no fact" in r.output.lower()


class TestFactsForgetCommand:
    def test_forget_deletes_fact(self, isolated_corpus: Path) -> None:
        r = runner.invoke(app, ["facts", "forget", "fact-beta", "--yes"])
        assert r.exit_code == 0, r.output
        # Verify on disk
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        assert sm.get("fact-beta") is None, (
            "cycle 138-bis: forget must delete the row on disk"
        )

    def test_forget_requires_confirmation_by_default(
        self, isolated_corpus: Path,
    ) -> None:
        # No --yes → must prompt and exit non-zero on empty stdin.
        r = runner.invoke(app, ["facts", "forget", "fact-alpha"], input="")
        # Either typer.Confirm reads empty and treats as "no", or we
        # explicitly require --yes. Either way: alpha must STILL exist.
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        assert sm.get("fact-alpha") is not None, (
            "cycle 138-bis: forget without --yes must not delete"
        )


class TestFactsStatsCommand:
    def test_stats_shows_counts_by_status(
        self, isolated_corpus: Path,
    ) -> None:
        r = runner.invoke(app, ["facts", "stats"])
        assert r.exit_code == 0, r.output
        # 4 facts seeded: 1 verified, 1 model_claim, 1 quarantined, 1 orphaned
        # The output must surface all four buckets (status enum coverage).
        for status in ("verified", "model_claim", "quarantined", "orphaned"):
            assert status in r.output, (
                f"cycle 138-bis: stats must list status={status!r}, "
                f"got output:\n{r.output}"
            )


class TestFactsAntiConfabScanCommand:
    def test_scan_reports_categories(self, isolated_corpus: Path) -> None:
        # Seed an L1-orphan fact (SHIPPED keyword, empty verified_by)
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        sm.store(Fact(
            id="fact-l1scan",
            proposition="Cycle 555 SHIPPED to main",
            topic="lab/cli138bis", confidence=0.9,
            verified_by=[], status="model_claim",
        ))
        r = runner.invoke(app, ["facts", "anti-confab-scan"])
        assert r.exit_code == 0, r.output
        # Output must mention the shipped category and the fact id (or
        # at least its prefix).
        assert "shipped" in r.output.lower()
        assert "fact-l1s" in r.output or "555 SHIPPED" in r.output


class TestFactsAntiConfabApplyCommand:
    def test_apply_dry_run_default_no_mutation(
        self, isolated_corpus: Path,
    ) -> None:
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        sm.store(Fact(
            id="fact-apply",
            proposition="Cycle 777 SHIPPED to main",
            topic="lab/cli138bis", confidence=0.9,
            verified_by=[], status="model_claim",
        ))
        # Default = dry-run (safety). No mutation expected.
        r = runner.invoke(app, ["facts", "anti-confab-apply"])
        assert r.exit_code == 0, r.output
        assert "dry" in r.output.lower() or "would" in r.output.lower(), (
            "cycle 138-bis: anti-confab-apply default must be dry-run "
            "and surface that in the output."
        )
        # Verify nothing moved on disk.
        sm2 = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        f = sm2.get("fact-apply")
        assert f is not None and f.status == "model_claim"

    def test_apply_no_dry_run_mutates(
        self, isolated_corpus: Path,
    ) -> None:
        sm = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        sm.store(Fact(
            id="fact-apply2",
            proposition="Cycle 333 SHIPPED to main",
            topic="lab/cli138bis", confidence=0.9,
            verified_by=[], status="model_claim",
        ))
        r = runner.invoke(
            app,
            ["facts", "anti-confab-apply", "--no-dry-run", "--yes"],
        )
        assert r.exit_code == 0, r.output
        # Verify the flip happened on disk.
        sm2 = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        f = sm2.get("fact-apply2")
        assert f is not None and f.status == "orphaned", (
            "cycle 138-bis: --no-dry-run must call mark_orphaned and "
            f"flip status. Got status={f.status!r}"
        )


class TestFactsHelpExposesCluster:
    """Cycle 138-bis must register 'facts' as a typer subcommand group."""

    def test_top_level_help_lists_facts(self) -> None:
        r = runner.invoke(app, ["--help"])
        assert r.exit_code == 0
        assert "facts" in r.output, (
            "cycle 138-bis: 'facts' subcommand cluster must appear in "
            "engram --help. Got:\n" + r.output
        )

    def test_facts_help_lists_subcommands(self) -> None:
        r = runner.invoke(app, ["facts", "--help"])
        assert r.exit_code == 0, r.output
        for sub in (
            "list", "recall", "search", "get", "forget", "stats",
            "anti-confab-scan", "anti-confab-apply",
        ):
            assert sub in r.output, (
                f"cycle 138-bis: 'engram facts --help' must list "
                f"subcommand {sub!r}. Got output:\n{r.output}"
            )
