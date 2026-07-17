"""Cycle #139 (2026-05-18) — secure session token write (no TOCTOU race).

Aurelio sfida 2026-05-18 'fai una ricerca approfondita': delle 3
pendenze 'security' che avevo identificato, 2 erano confabulazioni
(CVE-009 default fixato in cycle 124, trust_signals MCP wire fixato in
cycle 121). La TERZA è genuina:

    engram/dashboard_routes/auth.py:50-53 — POSIX TOCTOU race
    ─────────────────────────────────────────────────────────
    path.write_text(token, encoding="utf-8")       # ← creates with umask (typically 0o644)
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)                  # ← fixes permission AFTER

A local attacker on the same POSIX box can ``stat`` or ``open(path)``
during the microsecond window between ``write_text`` and ``os.chmod``
and read the dashboard session token. Severity: LOW (local-only,
microsecond window) but trivially preventable by writing the file
with mode 0o600 from the start via ``os.open(... mode=0o600)``.

Cycle 139 fix: replace the two-step pattern with a single
``os.open(path, O_CREAT|O_WRONLY|O_TRUNC, mode=0o600)`` followed by
``os.write`` + ``os.close``. On Windows the legacy ``write_text``
path is preserved because the file mode is governed by ACLs inherited
from the user profile directory, which is already private — no TOCTOU
analog applies.

The RED test below patches ``os.chmod`` to a no-op so any TOCTOU-style
implementation that depends on a post-write chmod fails to land on
0o600. The atomic O_CREAT path passes regardless.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

# POSIX-only: Windows uses ACLs, the test concept doesn't translate.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="TOCTOU race is POSIX-specific; Windows uses ACL inheritance.",
)


def _read_session_module():
    """Late import so the env override below takes effect at module init."""
    from verimem.dashboard_routes import auth as _auth
    return _auth


class TestSessionTokenIsCreatedWithSecureMode:
    """The session token file must be 0o600 IMMEDIATELY after creation,
    independently of any subsequent ``chmod`` call.

    Implementation contract: cycle 139 uses ``os.open(O_CREAT,
    mode=0o600)`` so the file never exists with broader permissions.
    """

    def test_file_mode_is_0600_even_when_chmod_is_a_noop(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Route the engram data dir to tmp_path so the session token
        # lands somewhere we can stat without touching the real corpus.
        monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
        # Make sure we don't pick up an explicit override token from env.
        monkeypatch.delenv("HIPPO_DASHBOARD_TOKEN", raising=False)

        # Patch os.chmod to NO-OP. Pre-fix _generate_session_token leans
        # on os.chmod to tighten the mode AFTER write_text; with chmod
        # neutered, the resulting file is 0o644 (umask default) and the
        # assertion below fails. Post-fix, the file is opened with
        # mode=0o600 atomically so chmod is irrelevant.
        chmod_calls: list[tuple[str, int]] = []
        original_chmod = os.chmod

        def _noop_chmod(p, mode):  # noqa: ANN001 — match signature
            chmod_calls.append((str(p), int(mode)))
            return None  # explicitly do nothing

        monkeypatch.setattr(os, "chmod", _noop_chmod)

        auth = _read_session_module()
        auth.reset_session_token()  # ensure a fresh _generate_session_token call

        token = auth._generate_session_token()  # noqa: SLF001 — test
        assert isinstance(token, str) and len(token) > 0

        path = auth.session_token_path()
        assert path.exists(), "session token file must be written"

        # Use original_chmod-bypassing stat so we read the real mode.
        st = path.stat()
        mode = stat.S_IMODE(st.st_mode)
        assert mode == 0o600, (
            "cycle 139: session token file must be created with mode "
            f"0o600 atomically (got 0o{mode:o}). chmod_calls={chmod_calls!r} "
            "— if these calls were the ONLY thing tightening the mode, the "
            "TOCTOU race is still present."
        )

    def test_token_content_round_trips(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The atomic write must not lose data."""
        monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("HIPPO_DASHBOARD_TOKEN", raising=False)
        auth = _read_session_module()
        auth.reset_session_token()
        token = auth._generate_session_token()  # noqa: SLF001
        path = auth.session_token_path()
        on_disk = path.read_text(encoding="utf-8")
        assert on_disk == token, (
            "cycle 139: secure write must produce the same bytes the caller "
            "received from _generate_session_token."
        )
