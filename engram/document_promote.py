"""doc -> Fact GATED promotion — the last brick of the document RAG (roadmap #1).

A retrieved chunk (``DocumentIndex.search`` hit) can be PROMOTED into the recall
corpus as a Fact — but through the same anti-confab discipline as everything
else, never around it:

  * status stays ``model_claim`` (a document says it; that does not make it
    verified truth — evidence elevates status later, not the promotion);
  * ``writer_role="document_promote"`` — a dedicated, non-trusted writer, so the
    full admission gate runs;
  * the EXACT citation ``file:<source_id>:<start>-<end>`` goes into
    ``verified_by`` AND ``source_episodes``: any reader can open the file at the
    exact offsets and check. This is the provenance moat carried into the
    corpus — the answer to "memoria documentale che non allucina e cita sempre".

The caller may pass a distilled ``claim`` (one clean sentence) instead of the
raw chunk text; the citation still anchors it to the file position it came from.
"""
from __future__ import annotations

__all__ = ["promote_chunk_to_fact", "chunk_citation", "PROMOTE_WRITER_ROLE"]

#: writer_role of promoted facts: NOT a trusted hook -> the full gate runs.
PROMOTE_WRITER_ROLE = "document_promote"


def chunk_citation(hit: dict) -> str:
    """The exact, checkable citation of a chunk: ``file:<source_id>:<start>-<end>``."""
    return f"file:{hit.get('source_id', '?')}:{hit.get('start', 0)}-{hit.get('end', 0)}"


def promote_chunk_to_fact(
    semantic_memory,
    hit: dict,
    *,
    claim: str | None = None,
    topic: str = "documents/promoted",
    confidence: float = 0.5,
    embed: str | None = None,
) -> dict:
    """Store ``hit`` (a DocumentIndex search result) as a gated Fact.

    Returns ``{"stored": bool, "fact_id": str | None, "citation": str,
    "error": str | None}``. Fail-safe: a gate rejection reports, never raises.
    """
    from .redaction import redact_secrets
    from .semantic import Fact

    text = (claim if claim is not None else str(hit.get("text", ""))).strip()
    citation = chunk_citation(hit)
    if not text:
        return {"stored": False, "fact_id": None, "citation": citation,
                "error": "empty chunk/claim — nothing to promote"}
    prop, _ = redact_secrets(text)
    version = hit.get("version")
    fact = Fact(
        proposition=prop,
        topic=topic,
        confidence=confidence,
        status="model_claim",              # a claim, never laundered truth
        verified_by=[citation],            # the checkable file citation
        source_episodes=[citation] + ([f"doc_version:{version}"] if version else []),
        writer_role=PROMOTE_WRITER_ROLE,
    )
    try:
        if embed is not None:
            semantic_memory.store(fact, embed=embed)
        else:
            semantic_memory.store(fact)
    except Exception as exc:  # noqa: BLE001 — gate rejection is a result, not a crash
        return {"stored": False, "fact_id": None, "citation": citation,
                "error": f"gate rejected: {exc!s:.120}"}
    return {"stored": True, "fact_id": fact.id, "citation": citation,
            "error": None}
