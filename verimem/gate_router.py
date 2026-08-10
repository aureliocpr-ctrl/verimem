"""Gate router — separate write-path gates by claim provenance (task #25).

Mandato 2026-07-10: i gate devono essere separati, e quando uno non passa
deve poter chiedere agli altri se la competenza è sua o loro. F1 (virgin-corpus validation, docs/F1_VIRGIN_CORPUS_FINDINGS.md)
root-caused the falls C2/C4 to a single axis: every gate was calibrated for
AGENT work-memory (short, ASCII, self-asserted status claims) and misfires
on externally-ingested document content.

This module answers the ownership question — WHOSE claim is this? — so each
gate can route on it instead of applying one blind policy:

======================  =============================  =====================
provenance              what it is                     gate consequences
======================  =============================  =====================
``agent_claim``         the agent's own assertion      L1.x anti-confab APPLY
                        (default writer_role)          (SHIPPED w/o commit =
                                                       confabulation signal)
``external_content``    ingested document/paragraph    L1.x SKIP (a book
                        (writer_role or source refs)   saying "merged" is not
                                                       the agent claiming a
                                                       merge). Injection /
                                                       content attacks still
                                                       quarantine — documents
                                                       ARE the poisoning
                                                       vector.
``user_input``          the user's own words           L1.x SKIP, same logic.
``trusted_hook``        system/trusted hooks           unchanged (they have
                                                       their own token-gated
                                                       bypass in store()).
======================  =============================  =====================

Security invariant: provenance NEVER weakens the injection defense — it only
routes the anti-confab heuristics (which are warning-only semantics about the
AGENT's honesty, meaningless for third-party text) and enriches gate events
with the attribution, so the ledger carries the "whose is this?" question
instead of silently deciding (the mandate's "backpropagation chiedendo").

NOTE writer_role is client-spoofable (see trusted_writer.py): that is safe
here BECAUSE the only privilege external_content grants is skipping a
warning-only heuristic that does not apply to it anyway; everything
security-relevant (injection screen, admission gate, refs hard-gate,
source-trust) runs identically for every provenance.
"""
from __future__ import annotations

from collections.abc import Iterable

AGENT_CLAIM = "agent_claim"
EXTERNAL_CONTENT = "external_content"
USER_INPUT = "user_input"
TRUSTED_HOOK = "trusted_hook"

# writer_role values that mean "this text was ingested, not asserted".
_EXTERNAL_ROLES = frozenset({"external_content", "document", "document_ingest"})
_TRUSTED_ROLES = frozenset({"system_hook", "trusted_hook"})

# verified_by prefixes that anchor the text to an external source. commit:/
# pytest:/file: refs anchor an AGENT claim and stay agent_claim on purpose.
_EXTERNAL_REF_PREFIXES = (
    "source-doc:", "doc:", "document:", "url:", "http://", "https://",
)


def classify_provenance(
    writer_role: str | None,
    verified_by: Iterable[str] | None = None,
) -> str:
    """WHOSE claim is this? Pure function of the fact's declared provenance."""
    role = (writer_role or "agent_inference").strip().lower()
    if role in _TRUSTED_ROLES:
        return TRUSTED_HOOK
    if role == "user":
        return USER_INPUT
    if role in _EXTERNAL_ROLES:
        return EXTERNAL_CONTENT
    # ⛔ `verified_by` NON decide piu' la provenienza, ed e' una cura di
    # SICUREZZA. Qui c'era un ciclo che rendeva `external_content` qualunque
    # claim portasse un ref con prefisso `url:`/`doc:`/`http://`… — e
    # `verified_by` arriva dal BODY della richiesta sul gateway HTTP.
    # Verificato end-to-end, ricostruito riga per riga:
    #     verified_by ['commit:abc123']   quarantined  L1=['L1.10','L1.15']
    #     verified_by ['url:https://…']   **model_claim  L1=NESSUNO**
    #     verified_by ['doc:inventato']   **model_claim  L1=NESSUNO**
    # cioe' un'auto-attestazione («ho verificato che funziona») entrava
    # SERVIBILE dichiarando una URL inventata.
    #
    # 🔑 QUARTA ISTANZA DI «spoofabile ma sicuro», e la terza l'ho curata IERI
    # io in questo stesso file: allora scrissi che il privilegio non puo'
    # pendere da `writer_role`, perche' sul canale di rete e' un argomento del
    # client, e lo feci pendere da `provenance_trusted`. Non ho applicato lo
    # stesso ragionamento a `verified_by`: il presidio copriva UN campo mentre
    # questa funzione ne legge DUE.
    #
    # LA REGOLA, e vale oltre questo caso: **`writer_role` e' una DICHIARAZIONE
    # di chi chiama, `verified_by` e' un DATO.** Un dato non decide i privilegi
    # di chi lo porta — stesso principio per cui il contenuto di un documento
    # non e' un'istruzione. Chi ingerisce davvero un documento ha la strada
    # esplicita e raggiungibile: `writer_role='external_content'`.
    return AGENT_CLAIM


def l1x_applies(provenance: str) -> bool:
    """L1/L1.5/L1.7 anti-confabulation detectors grade the AGENT's own
    status claims ("SHIPPED without a commit ref"). Third-party text is not
    the agent speaking — running them there is a category error (F1 C2)."""
    return provenance not in (EXTERNAL_CONTENT, USER_INPUT)


def attribution_question(provenance: str) -> str:
    """The one-line ownership answer a firing gate attaches to its event —
    the mandate's "backpropagation": the ledger asks/answers WHOSE claim it
    is instead of deciding silently."""
    if provenance == EXTERNAL_CONTENT:
        return (
            "attribution=external_content — ingested source content, not an "
            "agent claim; document policies apply")
    if provenance == USER_INPUT:
        return (
            "attribution=user_input — the user's own words, not an agent "
            "claim")
    if provenance == TRUSTED_HOOK:
        return "attribution=trusted_hook — system-hook provenance"
    return (
        "attribution=agent_claim — reads as the agent's own assertion; if "
        "this text was ingested from a document or user, set "
        "writer_role='external_content' to route it to the document policy")


__all__ = [
    "AGENT_CLAIM",
    "EXTERNAL_CONTENT",
    "USER_INPUT",
    "TRUSTED_HOOK",
    "classify_provenance",
    "l1x_applies",
    "attribution_question",
]
