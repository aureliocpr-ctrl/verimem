"""Cycle #145 (2026-05-18 sera) — CLI ``engram consolidate`` cluster tests.

Aurelio direttiva cycle 144: l'orchestrator deterministico
``engram.consolidation.auto_consolidate`` esiste ma NON ha surface CLI.
L'unica via per chiamarlo è uno script Python esterno o un MCP tool
(``hippo_consolidate``). Manca il pendant operator-facing che permetta:

  engram consolidate dry-run [--min-size N] [--prefix-depth D]
      Mostra clusters detected + masters proposed. NO write.

  engram consolidate apply   [--min-size N] [--prefix-depth D]
      Esegue auto_consolidate, mostra stats finali (persist).

  engram consolidate status
      Mostra count master già esistenti (proposition LIKE
      'AUTO-CLUSTER-MASTER %').

I test usano typer.testing.CliRunner contro la app real (no mock),
con ENGRAM_DATA_DIR=tmp_path per isolamento del corpus utente. Pattern
gemello a tests/test_cli_facts.py (cycle 138-bis).

TDD strict RED→GREEN: questo file deve fallire al primo run perché il
gruppo Typer ``consolidate`` con sub-comandi ``dry-run/apply/status``
non esiste ancora in engram/cli.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from engram.cli import app
from engram.semantic import Fact, SemanticMemory

runner = CliRunner()


def _seed_cluster(sm: SemanticMemory, topic: str, n: int) -> list[str]:
    """Insert n facts under the same topic for cluster detection."""
    ids: list[str] = []
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic} — content {i}",
            topic=topic,
            confidence=0.7,
            verified_by=[f"test:seed:{topic}:{i}"],
            status="model_claim",
        )
        sm.store(f)
        ids.append(f.id)
    return ids


@pytest.fixture
def isolated_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Point engram at an empty corpus under tmp_path so CLI commands
    operate on a known-shape store, not the user's live ~/.engram.

    Seed a small cluster (≥5 facts under one depth-2 prefix) so the
    detector has something to chew on without needing the real corpus.
    """
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    # Make sure the layout matches what the CLI expects (subdir style).
    sem_dir = tmp_path / "semantic"
    sem_dir.mkdir(parents=True, exist_ok=True)
    sm = SemanticMemory(db_path=sem_dir / "semantic.db")
    # 6 facts share project/cycle145 prefix → 1 cluster at depth=2.
    _seed_cluster(sm, "project/cycle145/area-a", 6)
    return tmp_path


# ----------------------------------------------------------------------
# Help / registration — the typer group must show up
# ----------------------------------------------------------------------
class TestConsolidateHelpExposesCluster:
    """Cycle 145: 'consolidate' must register as a typer subcommand group."""

    def test_top_level_help_lists_consolidate(self) -> None:
        r = runner.invoke(app, ["--help"])
        assert r.exit_code == 0
        assert "consolidate" in r.output, (
            "cycle 145: 'consolidate' subcommand cluster must appear in "
            "engram --help. Got:\n" + r.output
        )

    def test_consolidate_help_lists_subcommands(self) -> None:
        r = runner.invoke(app, ["consolidate", "--help"])
        assert r.exit_code == 0, r.output
        for sub in ("dry-run", "apply", "status"):
            assert sub in r.output, (
                f"cycle 145: 'engram consolidate --help' must list "
                f"subcommand {sub!r}. Got output:\n{r.output}"
            )


# ----------------------------------------------------------------------
# dry-run: detection, no write
# ----------------------------------------------------------------------
class TestConsolidateDryRunCommand:
    """`engram consolidate dry-run` reports detected clusters, no persist."""

    def test_dry_run_reports_cluster_count(
        self, isolated_corpus: Path,
    ) -> None:
        r = runner.invoke(
            app, ["consolidate", "dry-run", "--min-size", "5"],
        )
        assert r.exit_code == 0, r.output
        # Must surface either the count or the prefix in the output.
        assert (
            "1" in r.output
            or "project/cycle145" in r.output
            or "cluster" in r.output.lower()
        ), (
            f"cycle 145: dry-run must surface ≥1 cluster detected for "
            f"the seeded corpus. Got:\n{r.output}"
        )

    def test_dry_run_does_not_persist_master(
        self, isolated_corpus: Path,
    ) -> None:
        # Sanity: count facts before
        sm_before = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        n_before = sm_before.count()
        r = runner.invoke(
            app, ["consolidate", "dry-run", "--min-size", "5"],
        )
        assert r.exit_code == 0, r.output
        # No new fact may appear — dry-run is read-only.
        sm_after = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        n_after = sm_after.count()
        assert n_after == n_before, (
            f"cycle 145: dry-run must not persist (facts {n_before}→"
            f"{n_after}). Output:\n{r.output}"
        )


# ----------------------------------------------------------------------
# apply: run full auto_consolidate, persist masters
# ----------------------------------------------------------------------
class TestConsolidateApplyCommand:
    """`engram consolidate apply` actually persists master Episode+Fact+edges."""

    def test_apply_creates_master_fact(
        self, isolated_corpus: Path,
    ) -> None:
        sm_before = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        n_before = sm_before.count()
        r = runner.invoke(
            app, ["consolidate", "apply", "--min-size", "5"],
        )
        assert r.exit_code == 0, r.output
        # Master fact count must grow by ≥1
        sm_after = SemanticMemory(
            db_path=isolated_corpus / "semantic" / "semantic.db",
        )
        n_after = sm_after.count()
        assert n_after >= n_before + 1, (
            f"cycle 145: apply must persist ≥1 new master fact "
            f"({n_before}→{n_after}). Output:\n{r.output}"
        )

    def test_apply_output_shows_stats(
        self, isolated_corpus: Path,
    ) -> None:
        r = runner.invoke(
            app, ["consolidate", "apply", "--min-size", "5"],
        )
        assert r.exit_code == 0, r.output
        # Must surface the aggregate stats keys from auto_consolidate.
        # We tolerate either snake_case or pretty-printed variants.
        text = r.output.lower()
        for marker in ("master", "cluster"):
            assert marker in text, (
                f"cycle 145: apply output must mention {marker!r}. "
                f"Got:\n{r.output}"
            )


# ----------------------------------------------------------------------
# status: count existing AUTO-CLUSTER-MASTER facts
# ----------------------------------------------------------------------
class TestConsolidateStatusCommand:
    """`engram consolidate status` reports how many master facts exist."""

    def test_status_zero_on_empty_corpus(
        self, isolated_corpus: Path,
    ) -> None:
        # Before any apply, status must report 0 masters.
        r = runner.invoke(app, ["consolidate", "status"])
        assert r.exit_code == 0, r.output
        assert "0" in r.output, (
            f"cycle 145: status on un-consolidated corpus must show 0 "
            f"masters. Got:\n{r.output}"
        )

    def test_status_grows_after_apply(
        self, isolated_corpus: Path,
    ) -> None:
        # First apply, then verify status counts the new master.
        ra = runner.invoke(
            app, ["consolidate", "apply", "--min-size", "5"],
        )
        assert ra.exit_code == 0, ra.output
        rs = runner.invoke(app, ["consolidate", "status"])
        assert rs.exit_code == 0, rs.output
        # ≥1 master must be reported now.
        text = rs.output.lower()
        # The number 1 (or more) should appear; "0" alone would be wrong.
        assert "0 master" not in text and "0\n" != text.split("master")[0][-3:], (
            f"cycle 145: status after apply must show ≥1 master. Got:\n{rs.output}"
        )
        # Stronger assertion: the prefix or master marker should leak.
        assert (
            "master" in text or "AUTO-CLUSTER" in rs.output
            or "1" in rs.output or "2" in rs.output
        ), (
            f"cycle 145: status must mention master count or marker. "
            f"Got:\n{rs.output}"
        )
