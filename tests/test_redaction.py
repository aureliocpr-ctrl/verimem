"""Redaction di segreti/PII (engram.redaction.redact_secrets).

Finding HIGH del workflow di review: il path Tier C (ingest + promote) salvava
testo conversazionale VERBATIM, inclusi eventuali segreti incollati in chat
(API key, token, private key). redact_secrets maschera i pattern di segreto
PRIMA della persistenza, preservando il contenuto legittimo (zero falsi
positivi su testo normale).
"""
from __future__ import annotations

from engram.redaction import redact_secrets


def test_redacts_openai_style_key():
    out, n = redact_secrets("la chiave e' sk-abc123DEF456ghi789jkl012mno ok")
    assert "sk-abc123DEF456ghi789jkl012mno" not in out
    assert n >= 1 and "REDACTED" in out


def test_redacts_github_and_aws():
    out, n = redact_secrets("tok ghp_ABCDEFGHIJ1234567890abcdefXY e AKIAIOSFODNN7EXAMPLE qui")
    assert "ghp_ABCDEFGHIJ1234567890abcdefXY" not in out
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert n >= 2


def test_redacts_private_key_block():
    t = "ecco:\n-----BEGIN RSA PRIVATE KEY-----\nMIIabc123secret\n-----END RSA PRIVATE KEY-----\nfine"
    out, n = redact_secrets(t)
    assert "MIIabc123secret" not in out and n >= 1


def test_redacts_assigned_secret_keeps_key_name():
    out, n = redact_secrets('config: password = "hunter2supersecretvalue"')
    assert "hunter2supersecretvalue" not in out
    assert "password" in out  # il nome della chiave resta, solo il valore mascherato
    assert n >= 1


def test_redacts_bearer_token():
    out, n = redact_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abc")
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abc" not in out and n >= 1


def test_preserves_legit_content_zero_false_positive():
    t = "Abbiamo deciso di usare e5-base per il recall; MRR 0.84, R@10 0.88."
    out, n = redact_secrets(t)
    assert out == t and n == 0


def test_empty_and_none_safe():
    assert redact_secrets("") == ("", 0)
    assert redact_secrets(None) == (None, 0)


# --- Gap-closure 2026-06-03 (MISS trovati dall'audit indipendente 4-sorelle) ---

def test_redacts_naked_jwt():
    """JWT verbatim SENZA header Bearer (eyJ.eyJ.sig) — l'audit lo trovava slippare."""
    jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
           "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
    out, n = redact_secrets(f"il token e' {jwt} ormai scaduto")
    assert jwt not in out and n >= 1 and "REDACTED" in out


def test_redacts_db_url_password():
    """Password in connection-string (postgres/mysql/...) — MISS dell'audit."""
    out, n = redact_secrets("DSN=postgres://app_user:s3cr3tP4ssw0rd@db.internal:5432/main")
    assert "s3cr3tP4ssw0rd" not in out and n >= 1
    # struttura preservata (debuggabile): solo la password e' mascherata
    assert "app_user" in out and "db.internal" in out


def test_redacts_aws_secret_access_key_in_context():
    """AWS SECRET access key (40 char base64) in contesto var-name — MISS dell'audit.
    (La AKIA... era gia' coperta; la SECRET key nuda no.)"""
    out, n = redact_secrets('aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"')
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in out and n >= 1


def test_service_account_private_key_already_covered():
    """Il private_key di un service-account JSON e' coperto dal blocco PEM (conferma)."""
    sa = ('{"type":"service_account","private_key":"-----BEGIN PRIVATE KEY-----\\n'
          'MIIEvQISUPERSECRETkeymaterial\\n-----END PRIVATE KEY-----\\n"}')
    out, n = redact_secrets(sa)
    assert "MIIEvQISUPERSECRETkeymaterial" not in out and n >= 1


def test_no_false_positive_on_plain_url_hash_base64():
    """URL senza credenziali, hash SHA-256 e blob base64 NON sono segreti -> zero redaction.
    (Difende il recall legittimo: la redaction non deve inquinare il contenuto vero.)"""
    samples = [
        "endpoint https://api.example.com:8443/v1/recall?k=10",
        "commit sha256 a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
        "payload base64 TWFuIGlzIGRpc3Rpbmd1aXNoZWQgbm90IG9ubHkgYnkgcmVhc29u",
    ]
    for s in samples:
        out, n = redact_secrets(s)
        assert out == s and n == 0, f"falso positivo su: {s!r}"


# --- Gap-closure 2026-06-04 (hunt findings [01] @ in pwd, [09] stripe/slack-app) ---

def test_redacts_db_url_password_with_at_sign():
    """Password CON '@' (reale): l'intero frammento va mascherato, host preservato."""
    out, n = redact_secrets("DSN=postgres://user:p@ssw0rd@db.internal:5432/main")
    assert "ssw0rd" not in out and "p@ss" not in out and n >= 1
    assert "db.internal" in out  # host preservato
    out2, n2 = redact_secrets("uri mongodb://admin:Pa$ot@w0rd@cluster.mongodb.net/test ok")
    assert "w0rd" not in out2 and n2 >= 1
    assert "cluster.mongodb.net" in out2


def test_redacts_stripe_and_slack_app_tokens():
    out, n = redact_secrets("stripe REDACTED_FAKE_TEST_KEY e slack xapp-1-A0B1-123456-abcdef")
    assert "REDACTED_FAKE_TEST_KEY" not in out
    assert "xapp-1-A0B1-123456-abcdef" not in out
    assert n >= 2
