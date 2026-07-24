"""P0 evidence-before-belief, ciclo 2a — is the cited evidence INDEPENDENT?

Ciclo 1 stamped identity on both sides of the question (`writer_principal` on
facts, `meta.indexed_by` on document snapshots). This module answers it, and
nothing else: no gate wiring, no write path, no I/O beyond one read of the
document store.

The rule (adversarial design review 2026-07-22, glm-5.2 + kimi-k3 convergent
2/2 — the OR formulation was rejected because a hash proves INTEGRITY, never
PROVENANCE):

    independent  ⟺  author is known  AND  author != claimant
                    AND  the AUTHOR's channel is trusted

Each conjunct earns its place:

* **author known** — an unsigned exogenous document never earns advisory.
  Absence stays absence; a default would read as a vouch nobody made.
* **author != claimant** — self-citation IS the laundering move (write the
  poison, then cite yourself). Time-ordering does not discriminate here and
  tenant-scoping does not either: one poisons inside one's own tenant.
* **the AUTHOR's channel, not the claimant's** — the conjunct that survives
  falsification. Were it the claimant's, poison indexed over the
  unauthenticated MCP surface (`mcp:unbound`) and cited by any SDK-side
  writer would satisfy the rule: two principals, different, attack through.
  Trust attaches to how the EVIDENCE got in.

Contested provenance is not independence: when the versions of one source_id
disagree about who stamped them (or some are unstamped), the author is
unknown. Re-ingest is precisely how one would try to relabel a document's
voucher. Pinning the exact cited version is the next increment (content-bound
receipts, D5/#44); until then "contested → not independent" is the safe answer.

Never raises: an unreadable store degrades to "not independent" — it must not
fail a write, and it must not claim an independence it could not verify.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "IndependenceVerdict",
    "LazyDocumentStore",
    "author_principal_of_ref",
    "channel_of",
    "independence_verdict",
    "is_trusted_channel",
]

#: An identity the surface could not bind to anyone (the MCP server stamps
#: ``mcp:unbound`` exactly because an MCP client is not authenticated).
_UNBOUND = "unbound"


class LazyDocumentStore:
    """A document store that opens only if the rule actually asks something.

    Every write path can hand one of these to the gate unconditionally: most
    writes never reach the independence question (no L1 escalation, or no
    document ref among their evidence), and those must not pay for a sqlite
    connection. A store that cannot be opened answers "nothing known" — the
    rule then declines to claim independence, which is the safe direction.
    """

    __slots__ = ("_factory", "_store", "_tried")

    def __init__(self, factory: Any = None) -> None:
        self._factory = factory
        self._store: Any = None
        self._tried = False

    def _resolve(self) -> Any:
        if not self._tried:
            self._tried = True
            try:
                if self._factory is not None:
                    self._store = self._factory()
                else:
                    from .documents import DocumentStore
                    self._store = DocumentStore()
            except Exception:
                self._store = None
        return self._store

    def list_versions(self, source_id: str) -> list:
        store = self._resolve()
        if store is None:
            return []
        try:
            return store.list_versions(source_id)
        except Exception:
            return []


def channel_of(principal: str | None) -> str | None:
    """``"gw:team-alpha"`` → ``"gw"``; ``None`` when there is no channel part.

    An operator-declared in-process identity (``"ops-1"``) has no channel —
    only a caller already inside the process could set it.
    """
    if not isinstance(principal, str):
        return None
    head, sep, _rest = principal.strip().partition(":")
    return head if (sep and head) else None


def is_trusted_channel(principal: str | None) -> bool:
    """True unless the identity is absent or explicitly unbound.

    Trusted: ``sdk:*`` / ``cli:*`` (in-process — the caller could open the
    SQLite file anyway), ``gw:<tenant>`` (the gateway authenticated a tenant
    key), and bare operator-declared identities. Untrusted: nothing at all,
    and any ``*:unbound`` — an unauthenticated surface vouching for itself.
    """
    if not isinstance(principal, str) or not principal.strip():
        return False
    _head, sep, identity = principal.strip().partition(":")
    return not (sep and identity.strip().lower() == _UNBOUND)


def _source_id_of_ref(ref: str) -> str | None:
    """``doc:<source_id>`` / ``file:<path>[:<line>]`` → the source_id used at
    ingest time. Any other ref shape (``commit:``, ``url:``, free text) has no
    document behind it."""
    if not isinstance(ref, str):
        return None
    r = ref.strip()
    low = r.lower()
    if low.startswith("doc:"):
        return r[4:].strip() or None
    if low.startswith("file:"):
        path = r[5:].strip()
        # `file:<path>:<lineno>` — drop the trailing line number only when it
        # IS one (a Windows drive letter also carries a colon: C:\x\spec.md).
        head, sep, tail = path.rpartition(":")
        if sep and tail.isdigit() and head:
            path = head
        return path or None
    return None


def _stamps_for_source(store: Any, source_id: str) -> list[str | None]:
    """One entry per stored version: its ``indexed_by``, or None if unstamped."""
    versions = store.list_versions(source_id)
    return [(getattr(doc, "meta", None) or {}).get("indexed_by")
            for doc in versions]


def author_principal_of_ref(ref: str, store: Any) -> str | None:
    """Who vouched for the document behind ``ref`` — or None.

    None when: the ref is not a document ref, the document is unknown, it was
    ingested without a principal, or its versions disagree about the stamper
    (contested provenance is not authorship).
    """
    source_id = _source_id_of_ref(ref)
    if not source_id:
        return None
    try:
        stamps = _stamps_for_source(store, source_id)
        if not stamps:
            # Fall back to a normalised path (a `file:` ref and the stored
            # source_id can spell the same path differently).
            alt = os.path.normpath(source_id)
            if alt != source_id:
                stamps = _stamps_for_source(store, alt)
    except Exception:
        return None            # unreadable store: no claim either way
    if not stamps:
        return None
    distinct = set(stamps)
    if len(distinct) != 1:
        return None            # contested (or partly unstamped) provenance
    only = distinct.pop()
    return only if isinstance(only, str) and only.strip() else None


@dataclass(frozen=True)
class IndependenceVerdict:
    """The AND rule's answer, with the reason it reached it."""

    independent: bool
    author: str | None = None
    ref: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"independent": self.independent, "author": self.author,
                "ref": self.ref, "reason": self.reason}


def independence_verdict(*, verified_by: Iterable[str] | None,
                         claimant: str | None,
                         store: Any) -> IndependenceVerdict:
    """Evaluate the AND rule over the refs a claim cites.

    A claim is independent if ANY cited ref is: one genuine outside witness is
    enough, and the others are not evidence against it. The reported reason
    describes the first ref that HAD an author — the informative near-miss —
    rather than the last unrelated ``commit:`` ref in the list.
    """
    refs = [r for r in (verified_by or []) if isinstance(r, str) and r.strip()]
    if not refs:
        return IndependenceVerdict(False, reason="no refs cited")
    if not isinstance(claimant, str) or not claimant.strip():
        # A pre-P0 row has no identity to be independent OF.
        return IndependenceVerdict(False, reason="claimant identity unknown")
    claimant = claimant.strip()

    near_miss: IndependenceVerdict | None = None
    for ref in refs:
        author = author_principal_of_ref(ref, store)
        if author is None:
            continue
        if author == claimant:
            near_miss = near_miss or IndependenceVerdict(
                False, author=author, ref=ref,
                reason=f"self-citation: '{ref}' was indexed by the claimant "
                       f"({claimant})")
            continue
        if not is_trusted_channel(author):
            near_miss = near_miss or IndependenceVerdict(
                False, author=author, ref=ref,
                reason=f"'{ref}' entered over an untrusted channel "
                       f"({author}) — an unauthenticated surface cannot "
                       f"vouch for evidence")
            continue
        return IndependenceVerdict(
            True, author=author, ref=ref,
            reason=f"'{ref}' was indexed by {author}, independent of the "
                   f"claimant ({claimant})")
    return near_miss or IndependenceVerdict(
        False, reason="no cited ref resolves to a signed document")
