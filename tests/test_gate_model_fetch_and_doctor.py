"""The fresh-machine gap (demonstrated 2026-07-18) and its remedies.

On a machine without ``~/.engram/models/local_gate_ce_v2`` the README moat
quickstart's ``assert status == "quarantined"`` FAILED: the fine-tuned gate CE
exists only where it was trained — nothing downloaded it. Remedies pinned here:

* ``ensure_gate_model`` — the download path (`verimem warmup` calls it); honest
  "not yet published / not configured" message instead of a crash;
* ``verimem doctor`` — diagnoses the missing judge (and the rest of the install)
  in seconds, with the concrete fix per check;
* the fresh-machine write behavior stays HONEST: admitted WITH an L4-skipped
  advisory, never silently.
"""
from __future__ import annotations

import verimem.local_grounding as lg
from verimem.doctor import FAIL, OK, WARN, run_doctor, worst_status

# --- ensure_gate_model --------------------------------------------------------

def test_present_model_is_reported_present(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    ok, msg = lg.ensure_gate_model(tmp_path)
    assert ok and "present" in msg


def test_unconfigured_hub_reports_honestly_never_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("VERIMEM_GATE_MODEL_HUB_ID", raising=False)
    monkeypatch.setattr(lg, "DEFAULT_GATE_MODEL_HUB_ID", None)
    ok, msg = lg.ensure_gate_model(tmp_path / "missing")
    assert not ok
    assert "VERIMEM_GATE_MODEL_HUB_ID" in msg and "not yet published" in msg


def test_configured_hub_downloads_via_injected_downloader(tmp_path, monkeypatch):
    monkeypatch.setenv("VERIMEM_GATE_MODEL_HUB_ID", "acme/gate-model")
    calls = {}

    def fake_dl(repo_id, local_dir):
        calls["repo"] = repo_id
        (tmp_path / "dl" / "config.json").write_text("{}")

    ok, msg = lg.ensure_gate_model(tmp_path / "dl", download=fake_dl)
    assert ok and calls["repo"] == "acme/gate-model" and "downloaded" in msg


# --- doctor -------------------------------------------------------------------

def _by_name(checks):
    return {c["name"]: c for c in checks}

EXPECTED = {"version", "data-dir", "daemon", "moat-judge", "offline", "llm",
            "gateway"}


def test_doctor_runs_all_checks_with_valid_statuses(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "d"))
    checks = run_doctor()
    got = _by_name(checks)
    assert EXPECTED <= set(got), f"missing checks: {EXPECTED - set(got)}"
    assert all(c["status"] in (OK, WARN, FAIL) for c in checks)


def test_doctor_flags_the_fresh_machine_no_judge_case(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: False)
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: "mock")
    got = _by_name(run_doctor())
    mj = got["moat-judge"]
    assert mj["status"] == FAIL, mj
    assert "L4-skipped" in mj["detail"] and mj.get("fix")


def test_doctor_moat_ok_when_ce_present(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: True)
    got = _by_name(run_doctor())
    assert got["moat-judge"]["status"] == OK


def test_worst_status_ordering():
    assert worst_status([{"status": OK}, {"status": WARN}]) == WARN
    assert worst_status([{"status": WARN}, {"status": FAIL}]) == FAIL
    assert worst_status([{"status": OK}]) == OK


def test_cli_doctor_command_runs_and_exits_scriptably(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "d"))
    res = CliRunner().invoke(app, ["doctor", "--json"])
    assert res.exit_code in (0, 1, 2), res.output
    assert "moat-judge" in res.output
