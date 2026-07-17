"""End-to-end CLI smoke tests via typer.testing.CliRunner.

Verifies that:
  • the top-level `hippo --help` works (catches import-time crashes)
  • subcommand --help all work (no missing imports, no broken signatures)
  • providers list / active produce output and exit 0
  • skills list / episodes list run against an empty store and exit 0

These tests do not exercise actual LLM calls — they exit 0 the moment Typer
prints help, or after listing an empty in-memory store.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect every storage CONFIG.* path so CLI tests don't pollute prod data.

    `Config` is a frozen dataclass — we replace the module-level CONFIG with
    a mutable namespace that mirrors the same attributes. This avoids
    FrozenInstanceError while still being a per-test override.
    """
    from types import SimpleNamespace

    from verimem import config as cfg
    new = tmp_path / "data"
    (new / "episodes").mkdir(parents=True)
    (new / "skills").mkdir(parents=True)
    (new / "semantic").mkdir(parents=True)
    (new / "reports").mkdir(parents=True)
    (new / "runs").mkdir(parents=True)
    # Build a snapshot of every attribute on the original CONFIG, then
    # override the storage-related paths.
    snapshot = {
        attr: getattr(cfg.CONFIG, attr) for attr in dir(cfg.CONFIG)
        if not attr.startswith("_") and not callable(getattr(cfg.CONFIG, attr))
    }
    snapshot.update({
        "data_dir": new,
        "episodes_db": new / "episodes" / "episodes.db",
        "skills_dir": new / "skills",
        "skills_db": new / "skills" / "skills_index.db",
        "semantic_db": new / "semantic" / "semantic.db",
        "reports_dir": new / "reports",
        "runs_dir": new / "runs",
    })

    fake = SimpleNamespace(**snapshot)
    fake.ensure_dirs = lambda: None  # already created above
    monkeypatch.setattr(cfg, "CONFIG", fake)


# ---------------------------------------------------------------------------
# Top-level + subcommand --help (catches import errors)
# ---------------------------------------------------------------------------


def test_root_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Engram CLI" in result.output


@pytest.mark.parametrize("subcommand", [
    "wake", "sleep", "benchmark", "tui", "mcp", "chat", "reset",
    "metrics", "dashboard", "code", "run",
    # audit#2 C-3 (health alias) + A-9 (backup-all): both must be registered.
    "health", "backup-all",
])
def test_subcommand_help(runner: CliRunner, subcommand: str) -> None:
    """Each subcommand must have a --help that prints and exits 0."""
    result = runner.invoke(app, [subcommand, "--help"])
    assert result.exit_code == 0, \
        f"hippo {subcommand} --help failed: {result.output}"


@pytest.mark.parametrize("group_args", [
    ["providers", "--help"],
    ["providers", "list", "--help"],
    ["providers", "active", "--help"],
    ["providers", "scan", "--help"],
    ["providers", "models", "--help"],
    ["skills", "--help"],
    ["skills", "list", "--help"],
    ["skills", "show", "--help"],
    ["episodes", "--help"],
    ["episodes", "list", "--help"],
    ["episodes", "show", "--help"],
])
def test_subgroup_help(runner: CliRunner, group_args: list[str]) -> None:
    result = runner.invoke(app, group_args)
    assert result.exit_code == 0, \
        f"hippo {' '.join(group_args)} failed: {result.output}"


# ---------------------------------------------------------------------------
# providers list / active — should run with no providers configured
# ---------------------------------------------------------------------------


def test_providers_list(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure nothing is "configured" so we test the unconfigured branch too.
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    # The table title should mention "providers".
    assert "providers" in result.output.lower()


def test_providers_active(runner: CliRunner) -> None:
    result = runner.invoke(app, ["providers", "active"])
    assert result.exit_code == 0
    # Output should include the word "provider" somewhere.
    assert "provider" in result.output.lower()


# ---------------------------------------------------------------------------
# skills list / episodes list — exit 0 on empty store
# ---------------------------------------------------------------------------


def test_skills_list_empty_store(runner: CliRunner) -> None:
    result = runner.invoke(app, ["skills", "list"])
    assert result.exit_code == 0
    # Either "no skills" or a header — both are acceptable.
    out_lower = result.output.lower()
    assert "no skills" in out_lower or "skills" in out_lower


def test_episodes_list_empty_store(runner: CliRunner) -> None:
    result = runner.invoke(app, ["episodes", "list"])
    assert result.exit_code == 0
    assert "episodes" in result.output.lower()


# ---------------------------------------------------------------------------
# Critical safety check: dashboard refuses non-loopback bind
# ---------------------------------------------------------------------------


def test_dashboard_refuses_non_loopback_without_trust(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`hippo dashboard --host 0.0.0.0` without HIPPO_TRUSTED_NETWORK must
    exit non-zero (bind safety, CVE-008)."""
    monkeypatch.delenv("HIPPO_TRUSTED_NETWORK", raising=False)
    result = runner.invoke(app, ["dashboard", "--host", "0.0.0.0"])
    assert result.exit_code != 0
    assert "REFUSED" in result.output or "loopback" in result.output.lower()
