"""Cycle #110.E — production spawn_callable tests.

The library `engram.daemon_runner` takes an injected `spawn_callable`.
Production wiring uses `engram.daemon_spawn.production_spawn` which
fires a real detached subprocess (Popen) with stdin/stdout/stderr =
DEVNULL so the parent process (a SessionStart hook) doesn't block
on the child's output.

These tests use a real subprocess (a tiny `python -c "pass"` no-op)
to verify the spawn returns a PID dict and exits cleanly. No mocks
where mocks would hide bugs (per A2 — empirical verification).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from engram.daemon_spawn import production_spawn


class TestProductionSpawn:

    def test_spawn_python_noop_returns_pid(
        self, tmp_path: Path,
    ) -> None:
        # We pass the python interpreter as the "script" and `-c "pass"`
        # as the only arg. production_spawn must:
        #  1. Find the interpreter (it uses sys.executable internally),
        #  2. Return a dict with a numeric pid,
        #  3. Not block on the child.
        script = tmp_path / "noop.py"
        script.write_text("import sys; sys.exit(0)\n", encoding="utf-8")
        out = production_spawn(
            script_path=str(script),
            extra_args=[],
        )
        assert "pid" in out
        assert isinstance(out["pid"], int)
        assert out["pid"] > 0
        # Give the child a moment to actually finish — we don't wait
        # because production_spawn doesn't either; we just confirm the
        # call returned quickly.
        time.sleep(0.5)

    def test_spawn_with_extra_args_passes_them(
        self, tmp_path: Path,
    ) -> None:
        # Write a script that writes its argv to a file. We can then
        # read the file to confirm the args reached the child.
        marker = tmp_path / "argv.txt"
        script = tmp_path / "echo_argv.py"
        script.write_text(
            "import sys\n"
            f"open(r'{marker}', 'w').write('|'.join(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        production_spawn(
            script_path=str(script),
            extra_args=["--foo", "bar", "--baz"],
        )
        # Wait up to 3s for the child to write.
        for _ in range(30):
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists(), "child did not run / did not write marker"
        argv = marker.read_text().strip()
        assert argv == "--foo|bar|--baz"

    def test_spawn_missing_script_raises_or_signals(
        self, tmp_path: Path,
    ) -> None:
        # production_spawn returns a dict with the pid even for a missing
        # script (subprocess.Popen succeeds, the child fails its own
        # exec) OR raises FileNotFoundError. Both are acceptable safe
        # behaviour. What MUST hold: we do NOT silently return {} and
        # we do NOT block the parent.
        nonexistent = tmp_path / "does_not_exist.py"
        try:
            out = production_spawn(
                script_path=str(nonexistent),
                extra_args=[],
            )
        except FileNotFoundError:
            return  # acceptable
        # If it returned, pid must still be present (child crashes itself).
        assert "pid" in out

    def test_spawn_uses_current_python_interpreter(
        self, tmp_path: Path,
    ) -> None:
        # Script that writes sys.executable to a marker.
        marker = tmp_path / "interp.txt"
        script = tmp_path / "which_python.py"
        script.write_text(
            "import sys\n"
            f"open(r'{marker}', 'w').write(sys.executable)\n",
            encoding="utf-8",
        )
        production_spawn(script_path=str(script), extra_args=[])
        for _ in range(30):
            if marker.exists():
                break
            time.sleep(0.1)
        assert marker.exists()
        # The child's sys.executable must equal the parent's — this
        # avoids accidentally launching a different Python (e.g. a
        # global one) than the one running our test suite.
        assert marker.read_text().strip() == sys.executable


class TestSpawnRelativePathFromArbitraryCwd:
    """Cycle 110.E counterexample worker findings (2026-05-16):

    The SessionStart hook is invoked by Claude Code with cwd = user's
    workspace, NOT the HippoAgent repo. DEFAULT_DAEMONS uses relative
    script_path ("scripts/contradiction_scan.py"). Without explicit
    resolution, production_spawn would silently launch a child that
    fails (FileNotFoundError) while the parent burns the cooldown.

    These tests reproduce the failure mode and pin the fix.
    """

    def test_relative_script_path_resolves_against_repo_root(
        self, tmp_path: Path,
    ) -> None:
        # Reproduce the bug: chdir to an arbitrary directory (NOT the
        # repo root) and try to spawn one of the real DEFAULT_DAEMONS.
        # After the fix, the child must successfully launch — proven
        # by reading the cooldown state file the daemon would not
        # write if it crashed instantly.
        from engram.daemon_runner import DEFAULT_DAEMONS

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)  # cwd is now NOT the repo
            spec = DEFAULT_DAEMONS[0]  # contradiction_scan
            # production_spawn must return without raising — and the
            # child must actually find and start the script.
            out = production_spawn(
                script_path=spec.script_path,
                extra_args=spec.extra_args,
            )
            assert "pid" in out
            # The child should NOT instantly crash with FileNotFound.
            # We can't poll the child's exit code (it's detached), but
            # we CAN check the script file existed at the resolved
            # path. After the fix, production_spawn must resolve the
            # relative path against the repo root.
            #
            # Cheapest signal: production_spawn must surface either the
            # resolved absolute path OR raise FileNotFoundError early
            # so the cooldown caller can SKIP burning state.
            # We do NOT want silent-success on a missing script.
            resolved = out.get("resolved_script_path")
            assert resolved is not None, (
                "production_spawn must report the resolved absolute path"
            )
            assert Path(resolved).exists(), (
                f"resolved path {resolved} should exist"
            )
        finally:
            os.chdir(original_cwd)

    def test_missing_relative_script_returns_error_signal(
        self, tmp_path: Path,
    ) -> None:
        # A relative path that resolves to nothing (because there's no
        # repo anchor under cwd or the file is genuinely missing) must
        # NOT silently succeed. Two acceptable behaviours:
        #   (a) FileNotFoundError raised early — daemon_runner catches
        #       this and does NOT burn cooldown,
        #   (b) returned dict carries an "error" key so daemon_runner
        #       can treat it as a non-fire outcome.
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            try:
                out = production_spawn(
                    script_path="scripts/does_not_exist_anywhere.py",
                    extra_args=[],
                )
            except FileNotFoundError:
                return  # acceptable: caller skips cooldown burn
            # If it returned, must signal the failure to the caller.
            assert "error" in out or out.get("resolved_script_path") is None
        finally:
            os.chdir(original_cwd)
