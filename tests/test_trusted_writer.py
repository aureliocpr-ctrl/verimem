"""TDD — mattone ANTI-SPOOF (FASE 4, buco #1 della falsificazione).

Oggi il gate si fida di `writer_role in TRUSTED_HOOKS`, ma `writer_role` e'
settabile dal client MCP (esposto nello schema) -> spoofabile (dimostrato:
una confab con writer_role=trusted_hook passa da downgrade a persist).

Fix: il ruolo trusted vale SOLO se accompagnato da un token segreto server-side
(env) che il client non conosce. Primitiva PURA, fail-closed, HMAC-compare.
NON wirata nel gate (il wiring rompe il test che pinna il vecchio bypass = FORK
con ok-Aurelio). HERMETIC (monkeypatch env).
"""
from __future__ import annotations

from verimem.trusted_writer import verify_trusted_writer

ENV = "ENGRAM_HOOK_TOKEN"


def test_trusted_role_with_correct_token(monkeypatch):
    monkeypatch.setenv(ENV, "s3cret-xyz")
    assert verify_trusted_writer("trusted_hook", "s3cret-xyz") is True
    assert verify_trusted_writer("system_hook", "s3cret-xyz") is True


def test_trusted_role_with_wrong_token(monkeypatch):
    monkeypatch.setenv(ENV, "s3cret-xyz")
    assert verify_trusted_writer("trusted_hook", "guess") is False


def test_trusted_role_without_token_is_rejected(monkeypatch):
    monkeypatch.setenv(ENV, "s3cret-xyz")
    assert verify_trusted_writer("trusted_hook", None) is False
    assert verify_trusted_writer("trusted_hook", "") is False


def test_non_trusted_role_always_false(monkeypatch):
    monkeypatch.setenv(ENV, "s3cret-xyz")
    assert verify_trusted_writer("agent_inference", "s3cret-xyz") is False
    assert verify_trusted_writer("user", "s3cret-xyz") is False


def test_fail_closed_when_env_unset(monkeypatch):
    # nessun segreto configurato -> nessuno e' trusted (fail-closed)
    monkeypatch.delenv(ENV, raising=False)
    assert verify_trusted_writer("trusted_hook", "anything") is False
