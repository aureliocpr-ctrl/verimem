"""Cycle #110.E (2026-05-16) — daemon spawner tests.

Auto-Dream pattern generalizzato per spawn detached background CLI:
  - env-gate (opt-in default)
  - cooldown per-daemon via state file
  - injected spawn_callable (no real subprocess in tests)
  - returns structured dict, never raises to caller
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from verimem.daemon_runner import (
    DEFAULT_DAEMONS,
    DaemonSpec,
    maybe_spawn_all_default_daemons,
    maybe_spawn_daemon,
)


def _make_spec(
    *, name: str = "contradiction_scan", env_gate: str = "ENGRAM_T_X",
    cooldown_seconds: float = 21600.0, default_enabled: bool = False,
) -> DaemonSpec:
    return DaemonSpec(
        name=name,
        script_path=f"scripts/{name}.py",
        env_gate=env_gate,
        cooldown_seconds=cooldown_seconds,
        extra_args=["--json"],
        default_enabled=default_enabled,
    )


class _SpawnRecorder:
    def __init__(self, raises: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raises = raises

    def __call__(self, *, script_path: str, extra_args: list[str]) -> dict[str, Any]:
        self.calls.append({"script_path": script_path, "extra_args": extra_args})
        if self.raises is not None:
            raise self.raises
        return {"pid": 42}


class TestMaybeSpawnDaemon:

    def test_disabled_by_default_returns_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ENGRAM_T_X", raising=False)
        spec = _make_spec(default_enabled=False)
        rec = _SpawnRecorder()
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=time.time(), spawn_callable=rec,
        )
        assert out["spawned"] is False
        assert out["reason"] == "disabled"
        assert rec.calls == []

    def test_enabled_via_env_first_run_spawns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False)
        rec = _SpawnRecorder()
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1_000_000.0, spawn_callable=rec,
        )
        assert out["spawned"] is True
        assert out["reason"] == "fired"
        assert len(rec.calls) == 1
        assert rec.calls[0]["script_path"].endswith("contradiction_scan.py")
        assert rec.calls[0]["extra_args"] == ["--json"]
        state_file = tmp_path / "daemon_contradiction_scan_last.txt"
        assert state_file.exists()
        assert abs(float(state_file.read_text().strip()) - 1_000_000.0) < 0.001

    def test_default_enabled_no_env_spawns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("ENGRAM_T_X", raising=False)
        spec = _make_spec(default_enabled=True)
        rec = _SpawnRecorder()
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=2_000_000.0, spawn_callable=rec,
        )
        assert out["spawned"] is True

    @pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "banana"])
    def test_explicit_non_truthy_disables_even_when_default_on(
        self, val: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", val)
        spec = _make_spec(default_enabled=True)
        rec = _SpawnRecorder()
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1.0, spawn_callable=rec,
        )
        assert out["spawned"] is False
        assert out["reason"] == "disabled"
        assert rec.calls == []

    def test_cooldown_blocks_second_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False, cooldown_seconds=3600.0)
        rec = _SpawnRecorder()
        # First call fires.
        maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1000.0, spawn_callable=rec,
        )
        # 30 min later → still under 1h cooldown.
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1000.0 + 1800.0, spawn_callable=rec,
        )
        assert out["spawned"] is False
        assert out["reason"] == "cooldown"
        assert "elapsed_s" in out
        assert len(rec.calls) == 1

    def test_cooldown_passes_after_expiry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False, cooldown_seconds=3600.0)
        rec = _SpawnRecorder()
        maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1000.0, spawn_callable=rec,
        )
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1000.0 + 3700.0, spawn_callable=rec,
        )
        assert out["spawned"] is True
        assert len(rec.calls) == 2

    def test_corrupt_state_self_heals(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False)
        rec = _SpawnRecorder()
        state_file = tmp_path / "daemon_contradiction_scan_last.txt"
        state_file.write_text("definitely not a float", encoding="utf-8")
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1.0, spawn_callable=rec,
        )
        assert out["spawned"] is True

    def test_future_timestamp_self_heals(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # State says last run was at t=10_000_000, but we ask at t=1000.
        # Treat as corrupt (clock-skew defence, mirrors Auto-Dream cycle #69).
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False)
        rec = _SpawnRecorder()
        state_file = tmp_path / "daemon_contradiction_scan_last.txt"
        state_file.write_text("10000000.0\n", encoding="utf-8")
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1000.0, spawn_callable=rec,
        )
        assert out["spawned"] is True

    def test_spawn_exception_caught_no_state_burn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_T_X", "1")
        spec = _make_spec(default_enabled=False)
        rec = _SpawnRecorder(raises=RuntimeError("boom"))
        out = maybe_spawn_daemon(
            spec, state_dir=tmp_path, now=1.0, spawn_callable=rec,
        )
        assert out["spawned"] is False
        assert out["reason"] == "error"
        assert "boom" in out["error"]
        # Failure must NOT burn the cooldown: state file should not exist.
        state_file = tmp_path / "daemon_contradiction_scan_last.txt"
        assert not state_file.exists()


class TestMaybeSpawnAllDefaultDaemons:

    def test_returns_status_per_daemon(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Disable both via their env gates (default_enabled=False means
        # delenv keeps them off).
        for spec in DEFAULT_DAEMONS:
            monkeypatch.delenv(spec.env_gate, raising=False)
        rec = _SpawnRecorder()
        out = maybe_spawn_all_default_daemons(
            state_dir=tmp_path, now=1.0, spawn_callable=rec,
        )
        # One key per default daemon.
        assert set(out.keys()) == {spec.name for spec in DEFAULT_DAEMONS}
        # All disabled → all skipped.
        for status in out.values():
            assert status["spawned"] is False

    def test_subset_enabled_fires_only_that(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        for spec in DEFAULT_DAEMONS:
            monkeypatch.delenv(spec.env_gate, raising=False)
        # Enable just the first one.
        target = DEFAULT_DAEMONS[0]
        monkeypatch.setenv(target.env_gate, "1")
        rec = _SpawnRecorder()
        out = maybe_spawn_all_default_daemons(
            state_dir=tmp_path, now=1.0, spawn_callable=rec,
        )
        assert out[target.name]["spawned"] is True
        for spec in DEFAULT_DAEMONS[1:]:
            assert out[spec.name]["spawned"] is False
        assert len(rec.calls) == 1


class TestDefaultDaemonsRegistry:

    def test_registry_includes_contradiction_and_decay(self) -> None:
        names = {spec.name for spec in DEFAULT_DAEMONS}
        assert "contradiction_scan" in names
        assert "decay_run" in names

    def test_registry_scripts_exist_in_repo(self) -> None:
        # Sanity: the registry must point at files that actually exist
        # in scripts/. If a daemon's CLI is missing, the spawn would fail
        # in production silently.
        repo_root = Path(__file__).resolve().parent.parent
        for spec in DEFAULT_DAEMONS:
            target = repo_root / spec.script_path
            assert target.exists(), f"missing CLI for {spec.name}: {target}"

    def test_registry_default_enabled_is_opt_in(self) -> None:
        # Cycle #110.E ships daemons OFF by default. Aurelio can flip
        # them ON via env var; a future cycle can change the default.
        for spec in DEFAULT_DAEMONS:
            assert spec.default_enabled is False, (
                f"{spec.name} should default OFF in cycle 110.E"
            )
