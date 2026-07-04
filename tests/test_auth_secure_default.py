"""Cycle #124 (2026-05-17) — Auth secure-by-default + warning when disabled.

Lab 2026-05-17 subagent #3 (Security Architect) ha identificato risk
HIGH-severity con linea citation `engram/dashboard_routes/auth.py:75-78`:

> ``auth_disabled()`` default-True. ``HIPPO_DASHBOARD_AUTH_DISABLED`` ha
> default ``"1"`` (fail-open). Operator che binda 0.0.0.0 senza leggere
> docstring espone POST/PUT/DELETE senza auth. Antipattern
> insecure-by-default (OWASP ASVS V1.14.4).

Cycle #124 chiude il gap:
1. Default flip: ``"1"`` (auth disabled) → ``"0"`` (auth required).
2. Emit ``dashboard_auth_disabled`` warning event when auth is bypassed
   (regardless of why) so the operator sees it in observability.
3. Backward compat: explicit ``HIPPO_DASHBOARD_AUTH_DISABLED=1`` still
   works for dev/local deployments.

Test plan TDD:
* RED: default `auth_disabled()` returns False (currently True).
* RED: when env var unset, no skip happens during verify.
* GREEN: explicit opt-out still works for backward compat.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture
def clean_env() -> Iterator[None]:
    """Remove HIPPO_DASHBOARD_AUTH_DISABLED, restore prior state after.

    Cycle 167 fix: the original ``finally`` branch only restored when
    ``prior is not None`` — but two tests in this module set the env
    var *inside* the test body (``os.environ[...] = value``) and rely
    on this fixture to clean up afterwards. When the prior value was
    ``None`` (the normal case in a clean shell), the body-set value
    leaked into subsequent tests, breaking
    ``tests/test_dashboard_api.py::test_auth_info_default_is_enabled``
    under CI's alphabetical collection order. Now: always pop first,
    restore only if there was a prior value.
    """
    prior = os.environ.pop("HIPPO_DASHBOARD_AUTH_DISABLED", None)
    try:
        yield
    finally:
        os.environ.pop("HIPPO_DASHBOARD_AUTH_DISABLED", None)
        if prior is not None:
            os.environ["HIPPO_DASHBOARD_AUTH_DISABLED"] = prior


class TestSecureDefaultAuth:
    """Cycle #124 fix: default is secure (auth required)."""

    def test_default_no_env_var_auth_required(
        self, clean_env: None,
    ) -> None:
        """With no env var set, auth_disabled() must return False
        (auth is REQUIRED by default — secure-by-default)."""
        from engram.dashboard_routes.auth import auth_disabled
        assert auth_disabled() is False, (
            "Cycle #124 (lab finding agent #3 HIGH risk): default "
            "must be secure. HIPPO_DASHBOARD_AUTH_DISABLED unset must "
            "REQUIRE auth (return False)."
        )


class TestBackwardCompatExplicitOptOut:
    """Explicit opt-out via env var still works for dev/local."""

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE"])
    def test_explicit_opt_out_disables_auth(
        self, clean_env: None, value: str,
    ) -> None:
        os.environ["HIPPO_DASHBOARD_AUTH_DISABLED"] = value
        from engram.dashboard_routes.auth import auth_disabled
        assert auth_disabled() is True, (
            f"Explicit opt-out '{value}' must disable auth "
            f"(backward compat for dev/local)."
        )

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_explicit_enable_requires_auth(
        self, clean_env: None, value: str,
    ) -> None:
        os.environ["HIPPO_DASHBOARD_AUTH_DISABLED"] = value
        from engram.dashboard_routes.auth import auth_disabled
        assert auth_disabled() is False, (
            f"Explicit '{value}' must enforce auth."
        )
