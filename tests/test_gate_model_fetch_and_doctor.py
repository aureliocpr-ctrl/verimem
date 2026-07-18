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


def test_model_is_published_with_a_public_url_and_checksum():
    # the moat's out-of-box claim depends on this: the gate model is downloadable
    # by anyone, no account. A public release URL + a pinned sha256.
    assert lg.DEFAULT_GATE_MODEL_URL.startswith("https://github.com/")
    assert lg.DEFAULT_GATE_MODEL_URL.endswith(".tar.gz")
    assert len(lg.DEFAULT_GATE_MODEL_SHA256) == 64


def test_default_download_installs_via_injected_downloader(tmp_path):
    # no url/hub env set -> falls through to the built-in public release; the
    # injected downloader receives that URL and populates the dir.
    seen = {}

    def fake_dl(source, dest):
        seen["source"] = source
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "config.json").write_text("{}")

    ok, msg = lg.ensure_gate_model(tmp_path / "dl", download=fake_dl)
    assert ok and seen["source"] == lg.DEFAULT_GATE_MODEL_URL and "installed" in msg


def test_explicit_url_overrides_default(tmp_path, monkeypatch):
    monkeypatch.setenv("VERIMEM_GATE_MODEL_URL", "https://example.com/x.tar.gz")
    seen = {}

    def fake_dl(source, dest):
        seen["source"] = source
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "config.json").write_text("{}")

    lg.ensure_gate_model(tmp_path / "dl", download=fake_dl)
    assert seen["source"] == "https://example.com/x.tar.gz"


def test_sha256_mismatch_is_refused(tmp_path):
    # integrity gate: a tampered/truncated download must NOT be installed.
    import io

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.close()

    def opener(url):
        return _Resp(b"not the real model bytes")

    import pytest
    with pytest.raises(ValueError, match="sha256 mismatch"):
        lg._download_and_extract_tar(
            "https://x/y.tar.gz", tmp_path / "d",
            sha256="0" * 64, opener=opener)


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
