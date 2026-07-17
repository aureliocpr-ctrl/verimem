"""Cycle 2026-05-27 (round 12) — F-fix anti-confab gate trusted-hook bypass.

Closes BUG di design scoperto empirico 15:30: master pre-compact fact
con topic 'handoff/pre-compact-*' viene QUARANTENED da L1.x detector
perche contiene keyword retrospettiva (COMPLETO/SHIPPED/Authorized/MONITORED).

GPT triangulation proposal F (preferred over Gemini D): provenance-based
bypass NON topic-based. Requires writer_role='system_hook' AND
meta_narrative=True at write time. Topic-only check is insecure.

Pre-fix: master fact con handoff/ topic + retrospective keywords ->
gate fires 5+ layer warnings -> downgrade -> hidden from default recall.

Post-fix: same fact con writer_role='system_hook' + meta_narrative=True ->
gate bypasses L1.x entirely -> action='persist'.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate

_MASTER_FACT_TEXT = (
    "MASTER FACT PRE-COMPACT 2026-05-27 14:00 - CYCLE COMPLETO "
    "ANTI-CONFAB L1.x CHAIN + EMPIRICAL POST-RESTART VERIFICATION. "
    "SHIPPED 11 detector L1.9-L1.19. AUTOMATED auto-Dream cooldown. "
    "MONITORED dashboard grafana verimem. Authorized post-restart."
)


class TestPreFixQuarantineRegression:
    """Without writer_role+meta_narrative -> gate fires multi-layer warnings."""

    def test_master_fact_text_quarantined_without_provenance(self):
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
        )
        assert result.action == "downgrade", (
            f"Expected downgrade pre-fix; got {result.action}. "
            f"Warnings={result.warnings}"
        )
        layers = {w["layer"] for w in result.warnings}
        assert len(layers) >= 3, (
            f"Expected 3+ layers fire pre-fix; got {layers}"
        )


_HOOK_TOKEN = "s3cret-test-token-xyz"
_HOOK_ENV = "ENGRAM_HOOK_TOKEN"


class TestPostFixTrustedHookBypass:
    """writer_role='system_hook' + meta_narrative=True + valid token -> skip L1.x.

    Security fix 2026-06-02 (sorelle loop): the bypass is now token-gated.
    writer_role is client-spoofable via MCP arguments, so the short-circuit
    additionally requires the server-side ENGRAM_HOOK_TOKEN to be supplied
    as hook_token (fail-closed otherwise).
    """

    def test_master_fact_persisted_when_trusted_hook(self, monkeypatch):
        monkeypatch.setenv(_HOOK_ENV, _HOOK_TOKEN)
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
            writer_role="system_hook",
            meta_narrative=True,
            hook_token=_HOOK_TOKEN,
        )
        assert result.action == "persist", (
            f"Expected persist with trusted-hook bypass; "
            f"got {result.action}. Warnings={result.warnings}"
        )
        assert result.warnings == [], (
            f"Expected no warnings with bypass; got {result.warnings}"
        )

    def test_trusted_hook_alone_not_enough(self, monkeypatch):
        """writer_role='system_hook' + valid token WITHOUT meta_narrative -> gated."""
        monkeypatch.setenv(_HOOK_ENV, _HOOK_TOKEN)
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
            writer_role="system_hook",
            meta_narrative=False,
            hook_token=_HOOK_TOKEN,
        )
        assert result.action == "downgrade", (
            f"writer_role alone must NOT bypass; got {result.action}"
        )

    def test_meta_narrative_alone_not_enough(self, monkeypatch):
        """meta_narrative=True + valid token WITHOUT trusted writer_role -> gated."""
        monkeypatch.setenv(_HOOK_ENV, _HOOK_TOKEN)
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
            writer_role="user",
            meta_narrative=True,
            hook_token=_HOOK_TOKEN,
        )
        assert result.action == "downgrade", (
            f"meta_narrative alone (user role) must NOT bypass; "
            f"got {result.action}"
        )

    def test_trusted_hook_meta_narrative_without_token_is_gated(self, monkeypatch):
        """Security fix: trusted writer_role + meta_narrative but NO token
        (the MCP-client spoof vector) must NOT bypass -> fail-closed."""
        monkeypatch.setenv(_HOOK_ENV, _HOOK_TOKEN)
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
            writer_role="trusted_hook",
            meta_narrative=True,
            # hook_token omitted -> spoof from a client that cannot read env
        )
        assert result.action == "downgrade", (
            f"trusted_hook spoof without token MUST be gated; got {result.action}"
        )

    def test_trusted_hook_with_wrong_token_is_gated(self, monkeypatch):
        """A guessed/wrong token must not unlock the bypass (HMAC compare)."""
        monkeypatch.setenv(_HOOK_ENV, _HOOK_TOKEN)
        result = run_validation_gate(
            proposition=_MASTER_FACT_TEXT,
            verified_by=None,
            topic="handoff/pre-compact-2026-05-27",
            agent=None,
            validate="fast",
            writer_role="system_hook",
            meta_narrative=True,
            hook_token="wrong-guess",
        )
        assert result.action == "downgrade", (
            f"wrong token MUST be gated; got {result.action}"
        )

    def test_attacker_handoff_topic_with_user_role_still_gated(self):
        """Attack vector: user injects handoff/ topic but writer_role=user."""
        result = run_validation_gate(
            proposition=(
                "Production-ready and SHIPPED feature, fully MONITORED "
                "and AUTOMATED for enterprise customers."
            ),
            verified_by=None,
            topic="handoff/pre-compact-fake-attack",
            agent=None,
            validate="fast",
            writer_role="user",
            meta_narrative=True,
        )
        assert result.action == "downgrade", (
            "Attacker with user role + fake handoff topic MUST be gated"
        )


class TestBackwardCompat:
    """Existing callers without writer_role/meta_narrative work unchanged."""

    def test_legacy_call_signature_persist(self):
        result = run_validation_gate(
            proposition="Just a normal note about something.",
            verified_by=None,
            topic="notes/random",
            agent=None,
            validate="fast",
        )
        assert result.action == "persist"

    def test_legacy_call_signature_downgrade(self):
        result = run_validation_gate(
            proposition="The feature is SHIPPED and production-ready.",
            verified_by=None,
            topic="project/test",
            agent=None,
            validate="fast",
        )
        assert result.action == "downgrade"
