"""Cycle 368 (2026-05-23) — CAPABILITY TOKENS for engram syscall bridge.

Cross-instance fine-grained authorization: a central authority
(supervisor / OS-AI kernel) issues HMAC-signed tokens scoped to
(peer_id, op_name, expiry). engram_invoke verifies the token before
executing the op. Tokens are unforgeable without the shared secret
and naturally expire.

B4 concatenazione → STATO SUPERIORE engram completo:
  clp.agentos.syscall typed boundary (LOOP 361)
  + manifest validator anti-hallucination (LOOP 359-360)
  + verimem.op_supervisor circuit breaker (cycle 365)
  + verimem.syscall_bridge audit + rate-limit (cycle 364)
  + HMAC capability token (this module)
  ⇒ Engram operations now have AuthZ + AuthN equivalent via shared
    secret + token, layered over the existing safety stack.

A3 honest: NOT singolarità. Pattern from JWT / Macaroons / Erlang
cookie auth (predates 2010). Novel only the composition with engram
op manifest + supervisor.

Threat model:
  - Tokens HMAC-SHA256 over canonical body (peer_id || op || expiry).
  - Secret shared between issuer (supervisor) and verifier
    (engram_invoke). Stored in ~/.clp/a2a-secret.bin (reuses A2A
    bus secret per A6 lentezza, no key proliferation).
  - Receiver discards tokens with invalid HMAC or expired ts.
  - Tokens are bearer tokens — caller proves possession, no
    challenge-response. Suitable for trusted-cluster federation,
    NOT untrusted internet.

API:
  issue_token(peer_id, op, ttl_sec=300, scope=None) -> str
    Returns hex-encoded token of canonical body + HMAC.

  verify_token(token, expected_op, peer_id_required=None,
               now=None) -> {ok, peer_id, op, expires_at,
                              blocked_by, reason}

  decode_token_unsafe(token) -> dict (NO verification, diagnostic only).

Falsifiable contract (cycle 368):
  (a) issue_token + verify_token same secret + before expiry → ok=True
  (b) verify_token wrong op → ok=False, blocked_by='op_mismatch'
  (c) verify_token expired → ok=False, blocked_by='expired'
  (d) verify_token tampered HMAC → ok=False, blocked_by='hmac_invalid'
  (e) verify_token wrong peer (when peer_id_required) → ok=False,
       blocked_by='peer_mismatch'
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import struct
import time
from pathlib import Path

# Reuse A2A secret (same security domain) per A6 lentezza
A2A_SECRET_PATH = Path.home() / ".clp" / "a2a-secret.bin"
GHOST_SECRET_PATH = Path.home() / ".clp" / "ghost-secret.bin"
DEDICATED_SECRET_PATH = Path.home() / ".clp" / "engram-token-secret.bin"


def _load_secret() -> bytes:
    """Load HMAC secret. Prefer A2A bus secret, then ghost, then dedicated."""
    for p in (A2A_SECRET_PATH, GHOST_SECRET_PATH, DEDICATED_SECRET_PATH):
        if p.exists():
            return p.read_bytes()
    # Generate dedicated if none exists
    DEDICATED_SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    import secrets as _secrets
    s = _secrets.token_bytes(32)
    DEDICATED_SECRET_PATH.write_bytes(s)
    return s


def _canonical_body(peer_id: str, op: str, expires_at: float,
                     scope: str = "") -> bytes:
    """Order-sensitive canonical body for HMAC.

    Format (binary):
      "engram-token-v1\\x00" ||
      peer_id_utf8 || \\x00 ||
      op_utf8 || \\x00 ||
      struct.pack('<d', expires_at) ||
      scope_utf8 || \\x00
    """
    return b"".join([
        b"engram-token-v1\x00",
        peer_id.encode("utf-8"), b"\x00",
        op.encode("utf-8"), b"\x00",
        struct.pack("<d", expires_at),
        (scope or "").encode("utf-8"), b"\x00",
    ])


def _compute_hmac(body: bytes) -> bytes:
    """HMAC-SHA256 (32 bytes)."""
    return _hmac.new(_load_secret(), body, hashlib.sha256).digest()


def issue_token(
    peer_id: str,
    op: str,
    ttl_sec: float = 300.0,
    scope: str | None = None,
) -> str:
    """Issue a capability token for (peer_id, op) with TTL.

    Returns a base64-encoded token string. The token encodes:
      version | peer_id | op | expires_at | scope | hmac

    Args:
        peer_id: identity of the peer authorized to invoke op.
        op: operation name (must match engram_invoke op).
        ttl_sec: time-to-live in seconds from now.
        scope: optional fine-grain capability scope tag.

    Raises:
        ValueError on empty peer_id/op or non-positive ttl.
    """
    if not peer_id or not isinstance(peer_id, str):
        raise ValueError("peer_id (non-empty str) required")
    if not op or not isinstance(op, str):
        raise ValueError("op (non-empty str) required")
    if ttl_sec <= 0:
        raise ValueError("ttl_sec must be > 0")
    expires_at = time.time() + ttl_sec
    body = _canonical_body(peer_id, op, expires_at, scope or "")
    digest = _compute_hmac(body)
    # Wire format: base64(body) + ':' + hex(digest)
    return (
        base64.urlsafe_b64encode(body).decode("ascii")
        + ":"
        + digest.hex()
    )


def decode_token_unsafe(token: str) -> dict:
    """Decode token WITHOUT verification (diagnostic only).

    Returns {peer_id, op, expires_at, scope, hmac_hex} or {error}.
    """
    try:
        b64, hmac_hex = token.split(":", 1)
        body = base64.urlsafe_b64decode(b64.encode("ascii"))
        # Parse: skip version prefix
        if not body.startswith(b"engram-token-v1\x00"):
            return {"error": "bad_version"}
        rest = body[len(b"engram-token-v1\x00"):]
        peer_id_end = rest.find(b"\x00")
        peer_id = rest[:peer_id_end].decode("utf-8")
        rest = rest[peer_id_end + 1:]
        op_end = rest.find(b"\x00")
        op = rest[:op_end].decode("utf-8")
        rest = rest[op_end + 1:]
        expires_at = struct.unpack("<d", rest[:8])[0]
        rest = rest[8:]
        scope_end = rest.find(b"\x00")
        scope = rest[:scope_end].decode("utf-8")
        return {
            "peer_id": peer_id, "op": op,
            "expires_at": expires_at, "scope": scope,
            "hmac_hex": hmac_hex,
        }
    except (ValueError, struct.error, UnicodeDecodeError) as e:
        return {"error": f"malformed: {type(e).__name__}"}


def verify_token(
    token: str,
    expected_op: str,
    peer_id_required: str | None = None,
    now: float | None = None,
) -> dict:
    """Verify a capability token.

    Returns:
        {
          "ok": bool,
          "peer_id": str | None,
          "op": str | None,
          "expires_at": float | None,
          "scope": str | None,
          "blocked_by": str | None,
          "reason": str | None,
        }

    Falsifiable contract:
      (a) Valid token + correct op + before expiry → ok=True
      (b) op mismatch → ok=False blocked_by='op_mismatch'
      (c) expired → ok=False blocked_by='expired'
      (d) tampered hmac → ok=False blocked_by='hmac_invalid'
      (e) peer mismatch (when required) → ok=False blocked_by='peer_mismatch'
    """
    now = time.time() if now is None else now
    base = {"ok": False, "peer_id": None, "op": None,
            "expires_at": None, "scope": None,
            "blocked_by": None, "reason": None}

    if not isinstance(token, str) or ":" not in token:
        return {**base, "blocked_by": "malformed_token",
                "reason": "missing separator"}

    try:
        b64, hmac_hex = token.rsplit(":", 1)
        body = base64.urlsafe_b64decode(b64.encode("ascii"))
        provided_hmac = bytes.fromhex(hmac_hex)
    except (ValueError, base64.binascii.Error) as e:
        return {**base, "blocked_by": "malformed_token",
                "reason": f"decode error: {type(e).__name__}"}

    # HMAC verification FIRST (timing-safe via hmac.compare_digest)
    expected_hmac = _compute_hmac(body)
    if not _hmac.compare_digest(provided_hmac, expected_hmac):
        return {**base, "blocked_by": "hmac_invalid",
                "reason": "HMAC mismatch (tampered or wrong secret)"}

    # Parse body (we know it's intact now)
    decoded = decode_token_unsafe(token)
    if "error" in decoded:
        return {**base, "blocked_by": "malformed_token",
                "reason": decoded["error"]}

    peer_id = decoded["peer_id"]
    op = decoded["op"]
    expires_at = decoded["expires_at"]
    scope = decoded["scope"]

    # Op match
    if op != expected_op:
        return {**base,
                "peer_id": peer_id, "op": op,
                "expires_at": expires_at, "scope": scope,
                "blocked_by": "op_mismatch",
                "reason": f"token op '{op}' != expected '{expected_op}'"}

    # Expiry
    if expires_at < now:
        return {**base,
                "peer_id": peer_id, "op": op,
                "expires_at": expires_at, "scope": scope,
                "blocked_by": "expired",
                "reason": f"expired at {expires_at:.0f}, now {now:.0f}"}

    # Peer match (if required)
    if peer_id_required and peer_id != peer_id_required:
        return {**base,
                "peer_id": peer_id, "op": op,
                "expires_at": expires_at, "scope": scope,
                "blocked_by": "peer_mismatch",
                "reason": (
                    f"token peer '{peer_id}' != required "
                    f"'{peer_id_required}'"
                )}

    return {
        "ok": True,
        "peer_id": peer_id, "op": op,
        "expires_at": expires_at, "scope": scope,
        "blocked_by": None, "reason": None,
    }
