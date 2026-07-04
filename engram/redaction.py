"""Redaction di segreti/PII per il Tier C (ingest + promote).

Maschera pattern di SEGRETO ad alta confidenza (API key, token, private key,
header Authorization, assegnazioni `secret=...`) PRIMA che il testo
conversazionale venga persistito nello store grezzo o promosso nel corpus.

Scelta deliberata: NON si mascherano email/PII generici (troppi falsi positivi
che distruggerebbero il recall legittimo) — solo credenziali. I pattern sono
ancorati e con lunghezza minima per evitare falsi positivi su testo normale e
catastrophic backtracking (ReDoS). Tutto locale, zero rete.
"""
from __future__ import annotations

import re

_REDACT = "[REDACTED]"


def _assigned_repl(m: re.Match) -> str:
    # preserva il NOME della chiave, maschera solo il valore
    return f"{m.group(1)}={_REDACT}:secret"


def _dburl_repl(m: re.Match) -> str:
    # connection-string: preserva scheme://user e host, maschera SOLO la password
    return f"{m.group(1)}:{_REDACT}@"


def _aws_secret_repl(m: re.Match) -> str:
    # AWS secret access key: preserva il nome della var, maschera il valore 40-char
    return m.group(0).replace(m.group(2), f"{_REDACT}:aws_secret")


# (label, compiled_pattern, replacement). replacement = str o callable.
_RULES: list[tuple[str, re.Pattern, object]] = [
    ("private_key", re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.DOTALL), f"{_REDACT}:private_key"),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), f"{_REDACT}:anthropic_key"),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), f"{_REDACT}:api_key"),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"), f"{_REDACT}:github_token"),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), f"{_REDACT}:github_pat"),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), f"{_REDACT}:aws_key"),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), f"{_REDACT}:google_key"),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), f"{_REDACT}:slack_token"),
    ("slack_app_token", re.compile(r"\bxapp-[A-Za-z0-9-]{10,}"), f"{_REDACT}:slack_token"),
    ("stripe_key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"), f"{_REDACT}:stripe_key"),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"), f"Bearer {_REDACT}"),
    # JWT verbatim (anche senza header Bearer): tre segmenti base64url, header eyJ
    # (= base64url di '{"'). Estremamente specifico -> niente falsi positivi.
    ("jwt", re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        f"{_REDACT}:jwt"),
    # Password in connection-string (postgres://user:pass@host, mysql, mongodb, ...).
    # Match SOLO se c'e' userinfo 'user:pass@' -> niente match su URL normali con :porta/.
    ("db_url_password", re.compile(
        # password segment is [^\s/]+ (tolerates embedded '@', e.g. p@ssw0rd):
        # greedy + lookahead for a host token after the LAST '@' so the WHOLE
        # password is masked, not just the head (hunt finding [01]).
        r"(?i)\b([a-z][a-z0-9+.-]*://[^\s:/@]+):[^\s/]+@(?=[^\s/@:])"), _dburl_repl),
    # AWS SECRET access key (40 char base64) in contesto var-name. La AKIA... (access
    # key ID) era gia' coperta sopra; questa e' la SECRET nuda, che slippava.
    ("aws_secret_key", re.compile(
        r"(?i)(aws[_-]?secret[_-]?access[_-]?key|aws[_-]?sak)\b\s*[=:]\s*"
        r"[\"']?([A-Za-z0-9/+]{40})[\"']?"), _aws_secret_repl),
    # --- Cloud-provider credentials (audit A3 2026-06-08). Anchored + length-
    # bounded so normal prose / code (e.g. "1//0", "AccountName=") never matches.
    ("azure_storage_key", re.compile(
        r"(?i)\bAccountKey=[A-Za-z0-9+/]{40,}={0,2}"),
        f"AccountKey={_REDACT}:azure_key"),
    ("gcp_refresh_token", re.compile(r"\b1//0[A-Za-z0-9_-]{30,}"), f"{_REDACT}:gcp_refresh"),
    ("sendgrid_key", re.compile(
        r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"), f"{_REDACT}:sendgrid_key"),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), f"{_REDACT}:npm_token"),
    ("slack_webhook", re.compile(
        r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]{16,}"),
        f"{_REDACT}:slack_webhook"),
    ("twilio_sid", re.compile(r"\bAC[0-9a-fA-F]{32}\b"), f"{_REDACT}:twilio_sid"),
    # A-1 (audit#2 2026-06-08): allow an OPTIONAL snake/kebab prefix segment so
    # compound keys match (db_password, app_secret, access_token, MYAPP_API_KEY,
    # service_account_key). The bare leading \b used to require a boundary that
    # '_' suppresses, so every snake_case secret was stored verbatim. The full
    # key (prefix included) is captured in group(1) so _assigned_repl preserves
    # the key name and masks only the value.
    # FIX 2026-06-09 (audit#3-r3 R1+R9): the value used to be
    # [A-Za-z0-9._/+=~-]{12,}, which EXCLUDES common credential symbols
    # (@ $ ! : space) — any such char dropped the run below the floor and the
    # whole secret stored verbatim; quoted multi-word passphrases leaked too.
    # Value is now a quote-delimited span (any inner chars, incl. spaces) OR a
    # whitespace/quote/separator-terminated run (captures @ $ ! etc.). The
    # secret-keyword key gate (group 1) keeps false positives near zero.
    ("assigned_secret", re.compile(
        r"(?i)\b((?:[a-z0-9]+[_-])?(?:api[_-]?key|secret|token|access[_-]?key|"
        r"access[_-]?token|auth[_-]?token|password|passwd|passphrase|pwd|"
        r"account[_-]?key|private[_-]?key(?:[_-]?id)?|client[_-]?secret|"
        r"refresh[_-]?token|sas[_-]?token))\b"
        r"\s*[=:]\s*(?:[\"'][^\"']{4,}[\"']|[^\s\"';,]{8,})"),
        _assigned_repl),
]


def redact_secrets(text):
    """Maschera i segreti in ``text``. Ritorna ``(text_redatto, n_redazioni)``.

    None / stringa vuota -> invariata, count 0. Idempotente sul testo già pulito.
    """
    if not text:
        return text, 0
    total = 0
    for _label, pat, repl in _RULES:
        text, n = pat.subn(repl, text)
        total += n
    return text, total


__all__ = ["redact_secrets"]
