"""Signed anchor receipt over BOTH audit chains (task #24, step 2).

Step 1 hash-chained each destructive mutation and each adjudication, and let the
operator archive a chain HEAD off-box; but an in-DB ``verify()`` still cannot see
a full-chain rewrite (re-hash everything to a new, internally-valid chain) or a
tail-truncate+reinsert (adversary F1/F5, deepseek 2026-07-23). And a bare-head
signature (``tamper_evidence.sign_head``) binds only the 64-hex string, so with
one operator key across two chains a signature for chain A's head is presentable
as chain B's.

This module builds a RECEIPT that closes both gaps:

* It names BOTH chains' heads AND row counts, plus a timestamp, and the ed25519
  signature covers the canonical serialization of that whole payload (via
  ``tamper_evidence.sign_receipt``). The signature therefore binds chain
  identity + counts + ts together -- domain separation the bare head lacked.
* Row counts let a later verify distinguish "no new rows" from "tail truncated
  to an older length", and the anchored head is re-checked AT the anchored row
  count, so a rewrite (same count, different head) or a truncate+reinsert (count
  restored, head differs) is caught -- what ``verify()`` alone is blind to.

Honest replay/rollback contract (documented, enforced as far as crypto can):
an OLD receipt legitimately signed an OLDER, shorter state, so it will still
verify against a chain rolled back to exactly that state -- an attacker can
present a stale receipt after truncating. Defending that is OPERATIONAL, not
cryptographic: the operator verifies against the NEWEST archived receipt (whose
``ts`` and counts are the highest). What every receipt DOES enforce is that the
current chain is an append-only EXTENSION of the state it signed -- counts may
only grow, and the anchored head must still sit at its anchored position.

GDPR posture: the receipt carries action-metadata only (hashes, counts, ts) --
never a fact, never a hash of a fact -- so it is safe to archive anywhere.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .tamper_evidence import sign_receipt, verify_receipt_signature

__all__ = [
    "ALGORITHM",
    "RECEIPT_VERSION",
    "AnchorResult",
    "ChainState",
    "build_payload",
    "sign_anchor",
    "verify_anchor",
]

RECEIPT_VERSION = 1
ALGORITHM = "ed25519"

#: The chains a receipt covers; each maps to ``<name>_head`` / ``<name>_rows``
#: fields in the payload. Ordered so failure reports read chain-1 then chain-2.
_CHAINS = ("mutations", "adjudications")


def build_payload(*, ts: float, mutations_head: str | None,
                  mutations_rows: int, adjudications_head: str | None,
                  adjudications_rows: int) -> dict:
    """The signed part of a receipt (everything EXCEPT the signature). Heads are
    the chains' current heads (``None`` when a chain is empty); rows are their
    chained-row counts -- the two together let verify tell truncation from
    stasis."""
    return {
        "version": RECEIPT_VERSION,
        "ts": float(ts),
        "algorithm": ALGORITHM,
        "mutations_head": mutations_head,
        "mutations_rows": int(mutations_rows),
        "adjudications_head": adjudications_head,
        "adjudications_rows": int(adjudications_rows),
    }


def sign_anchor(payload: dict, private_key_path) -> dict:
    """Return the full receipt: ``payload`` plus its base64 ed25519
    ``signature`` over the payload's canonical bytes."""
    return {**payload, "signature": sign_receipt(payload, private_key_path)}


@dataclass
class ChainState:
    """A chain's CURRENT state, as seen at verify time.

    ``rows`` is the current chained-row count; ``intact`` is ``verify()`` having
    returned ``None`` (no interior tamper); ``head_at(k)`` returns the stored
    ``entry_hash`` of the k-th chained row (1-indexed), or ``None`` if k is out
    of range. Reading the stored hash is sufficient BECAUSE ``intact`` separately
    proves the stored hashes recompute -- so a rewrite that changed row k shows
    up as a mismatched ``head_at(k)``, and an inconsistent rewrite shows up as
    ``intact=False``."""
    rows: int
    intact: bool
    head_at: Callable[[int], str | None]


@dataclass
class AnchorResult:
    ok: bool
    failures: list[str] = field(default_factory=list)


def verify_anchor(receipt: dict, *, key_path,
                  chains: dict[str, ChainState]) -> AnchorResult:
    """Verify a receipt against the live chains. Checks, in order:

    1. the signature is valid over the receipt payload (a forged/tampered
       receipt is game over -- no chain claim from it can be trusted);
    2. per chain: the current chain is intact, its row count has only GROWN
       (>= anchored), and the anchored head still sits at the anchored row
       count.

    Returns ``AnchorResult(ok, failures)`` -- each failure names the chain and
    the check, so a caller can print exactly what broke and exit non-zero."""
    failures: list[str] = []
    payload = {k: v for k, v in receipt.items() if k != "signature"}
    sig = receipt.get("signature")
    if not sig or not verify_receipt_signature(payload, sig, key_path):
        failures.append(
            "signature: invalid or missing — receipt was forged or tampered, "
            "or the wrong verification key was supplied")
        return AnchorResult(ok=False, failures=failures)

    for name in _CHAINS:
        st = chains.get(name)
        if st is None:
            failures.append(f"{name}: no current chain state supplied to verify")
            continue
        anchored_head = payload.get(f"{name}_head")
        anchored_rows = payload.get(f"{name}_rows")
        if anchored_rows is None:
            failures.append(f"{name}: receipt is missing {name}_rows")
            continue
        if not st.intact:
            failures.append(
                f"{name}: current chain fails verify (an edited, reordered or "
                f"interior-deleted row)")
        if st.rows < anchored_rows:
            failures.append(
                f"{name}: tail truncated — current {st.rows} chained rows < "
                f"anchored {anchored_rows}")
            continue
        if anchored_rows == 0:
            if anchored_head is not None:
                failures.append(
                    f"{name}: receipt anchors 0 rows but a non-null head")
            continue
        got = st.head_at(anchored_rows)
        if got != anchored_head:
            failures.append(
                f"{name}: head at anchored row {anchored_rows} does not match "
                f"the receipt (full-chain rewrite or truncate+reinsert)")
    return AnchorResult(ok=not failures, failures=failures)
