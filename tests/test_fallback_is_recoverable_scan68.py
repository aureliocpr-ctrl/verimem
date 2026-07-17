"""TDD — FallbackLLM._is_recoverable non deve trattare i context/token-length
limit come recuperabili (rescan2 MEDIUM llm.py:1320-1326, 2026-06-02).

Il match substring includeva 'limit', che cattura anche 'context length limit'
/ 'token limit': errori che falliscono IDENTICI su ogni provider (il prompt e'
troppo lungo) -> ritentare la catena di fallback e' inutile e spreca i provider.

Fix aggiusta-non-rovina: una denylist di pattern non-recuperabili (context/token
length) con precedenza; i rate-limit veri restano recuperabili. Funzione pura.
"""
from __future__ import annotations

from verimem.llm import FallbackLLM


def _rec(msg: str) -> bool:
    return FallbackLLM._is_recoverable(Exception(msg))


# --- recuperabili: cambiare provider PUO aiutare (devono restare True) -------
def test_rate_limit_recoverable():
    assert _rec("Rate limit exceeded (429)") is True


def test_503_recoverable():
    assert _rec("503 Service Unavailable") is True


def test_connection_timeout_recoverable():
    assert _rec("Connection timeout after 30s") is True


def test_overloaded_recoverable():
    assert _rec("server overloaded, please retry") is True


# --- NON recuperabili: falliscono identici ovunque (devono diventare False) --
def test_context_length_limit_not_recoverable():
    assert _rec("context length limit exceeded") is False


def test_token_limit_not_recoverable():
    assert _rec("token limit reached for this request") is False


def test_maximum_context_not_recoverable():
    assert _rec("This model's maximum context length is 8192 tokens") is False


def test_auth_error_not_recoverable():
    assert _rec("Invalid API key provided") is False
