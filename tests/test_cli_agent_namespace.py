"""Product-CLI slimming (VERIMEM-MAP.md 1b): agent-runtime commands live under
`verimem agent <cmd>`; the memory product keeps the top level. Old top-level
spellings still WORK (the product is public — 0.5.x scripts must not break),
they are just hidden from --help.
"""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


def test_agent_namespace_lists_the_runtime_commands():
    res = runner.invoke(app, ["agent", "--help"])
    assert res.exit_code == 0, res.output
    for cmd in ("chat", "code", "run", "benchmark", "sleep", "swarm", "teams"):
        assert cmd in res.output, f"`verimem agent` missing {cmd!r}: {res.output}"


def test_top_level_help_no_longer_shows_runtime_commands():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0, res.output
    for cmd in ("chat", "swarm", "teams", "wake", "sleep-now"):
        assert f" {cmd} " not in res.output, f"{cmd!r} still visible in top-level --help"
    # the product core is still there
    for cmd in ("mcp", "trust", "index", "console", "agent-guide"):
        assert cmd in res.output, f"product command {cmd!r} missing from --help"


def test_old_toplevel_spellings_still_work_hidden():
    # public product: a 0.5.x script calling `verimem chat --help` must not break
    for argv in (["chat", "--help"], ["sleep-now", "--help"], ["swarm", "--help"]):
        res = runner.invoke(app, argv)
        assert res.exit_code == 0, f"hidden alias {argv} broke: {res.output}"


def test_new_agent_spellings_work():
    for argv in (["agent", "chat", "--help"], ["agent", "swarm", "--help"],
                 ["agent", "sleep-now", "--help"]):
        res = runner.invoke(app, argv)
        assert res.exit_code == 0, f"{argv} failed: {res.output}"
