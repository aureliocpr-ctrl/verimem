"""CVE-005 — Python executor backend isolation contract.

Backend selection is driven by HIPPO_PYTHON_EXEC_BACKEND. The default
'subprocess' backend remains unchanged; the 'docker' backend is opt-in
and falls back transparently when Docker is unavailable.

The container backend MUST:
  • disable network egress (--network=none)
  • drop all caps (--cap-drop=ALL)
  • mount /work read-write but NOTHING ELSE
  • bound memory + pids
  • not leak filesystem state outside the mount

These tests do NOT require Docker to run — when Docker is missing they
exercise the fallback path. When Docker IS present they assert real
isolation by attempting to write outside /work.
"""
from __future__ import annotations

import os

import pytest

from verimem.tools import (
    DockerPythonExecutor,
    PythonExecutor,
    make_python_executor,
)


class TestFactoryBackendSelection:
    """make_python_executor honours HIPPO_PYTHON_EXEC_BACKEND."""

    def test_default_is_subprocess(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HIPPO_PYTHON_EXEC_BACKEND", raising=False)
        ex = make_python_executor()
        assert isinstance(ex, PythonExecutor)

    def test_explicit_subprocess(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HIPPO_PYTHON_EXEC_BACKEND", "subprocess")
        ex = make_python_executor()
        assert isinstance(ex, PythonExecutor)

    def test_docker_falls_back_when_unavailable(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If 'docker' requested but SDK/daemon missing, fall back to subprocess."""
        monkeypatch.setenv("HIPPO_PYTHON_EXEC_BACKEND", "docker")

        # Force the docker SDK probe to fail
        import builtins
        real_import = builtins.__import__

        def _fake_import(name, *a, **kw):
            if name == "docker":
                raise ImportError("simulated: docker SDK absent")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        ex = make_python_executor()
        assert isinstance(ex, PythonExecutor)


class TestDockerExecutorContract:
    """Skip when Docker isn't usable — these test real isolation when it is."""

    def _docker_available(self) -> bool:
        try:
            import docker  # type: ignore
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def test_init_unavailable_marks_executor(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When docker SDK can't import, the executor reports unavailable."""
        import builtins
        real_import = builtins.__import__

        def _fake_import(name, *a, **kw):
            if name == "docker":
                raise ImportError("simulated")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        ex = DockerPythonExecutor()
        assert ex.available is False
        # run() returns a clean error, doesn't crash
        result = ex.run("print('hi')")
        assert result.ok is False
        assert "docker" in result.error.lower()

    @pytest.mark.skipif(
        os.environ.get("HIPPO_TEST_DOCKER", "0") != "1",
        reason="set HIPPO_TEST_DOCKER=1 to run live Docker tests",
    )
    def test_basic_execution(self) -> None:
        ex = DockerPythonExecutor()
        if not ex.available:
            pytest.skip("docker not available")
        result = ex.run("print('hello from container')")
        assert result.ok is True
        assert "hello from container" in result.output
        assert (result.extra or {}).get("backend") == "docker"

    @pytest.mark.skipif(
        os.environ.get("HIPPO_TEST_DOCKER", "0") != "1",
        reason="set HIPPO_TEST_DOCKER=1 to run live Docker tests",
    )
    def test_cannot_write_outside_mount(self) -> None:
        """Read-only root FS prevents writes outside the /work mount."""
        ex = DockerPythonExecutor()
        if not ex.available:
            pytest.skip("docker not available")
        code = (
            "import sys\n"
            "try:\n"
            "    open('/etc/passwd_compromised', 'w').write('pwned')\n"
            "    print('LEAK')\n"
            "except OSError as e:\n"
            "    print('ISOLATED:', e)\n"
        )
        result = ex.run(code)
        # Either the run failed, or the script printed ISOLATED.
        assert "LEAK" not in result.output

    @pytest.mark.skipif(
        os.environ.get("HIPPO_TEST_DOCKER", "0") != "1",
        reason="set HIPPO_TEST_DOCKER=1 to run live Docker tests",
    )
    def test_no_network_egress(self) -> None:
        """--network=none must block outbound requests."""
        ex = DockerPythonExecutor()
        if not ex.available:
            pytest.skip("docker not available")
        code = (
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 80), timeout=3)\n"
            "    print('NETWORK_OK')\n"
            "except OSError as e:\n"
            "    print('NETWORK_BLOCKED:', e)\n"
        )
        result = ex.run(code)
        assert "NETWORK_OK" not in result.output


class TestSubprocessBackendUnchanged:
    """Sanity: the existing subprocess backend keeps working as it did."""

    def test_print_works(self) -> None:
        ex = PythonExecutor()
        result = ex.run("print(2 + 3)")
        assert result.ok is True
        assert "5" in result.output
