"""Promozione Tier C → corpus accettato (il ponte ESPLICITO e gated).

Prende un turno verbatim del transcript grezzo (Tier C, confidence~0, isolato) e
crea un ``Fact`` nel corpus accettato (``semantic.db``) con PROVENANCE che punta
al turno. È l'unico cammino per cui qualcosa di detto-in-chat diventa
conoscenza: deliberato, tracciabile, e SOTTOPOSTO al gate anti-confab di
``SemanticMemory.store`` (che NON promuove a ``verified`` senza evidenza reale —
``status='verified'`` senza ref file/commit viene demoto a ``model_claim``).

Default ``status='model_claim'``: il grezzo entra come *claim* a bassa fiducia,
non come verità. Sta poi al normale flusso di verifica elevarne lo status con
evidenza (ref file:line / commit). Niente laundering della conversazione.
"""
from __future__ import annotations

from .transcript_index import TranscriptIndex

#: writer_role della promozione: NON è un trusted-hook → il gate gira per intero
#: (nessun bypass della provenance). Marca l'origine conversazionale.
PROMOTION_WRITER_ROLE = "conversational_promotion"


def turn_provenance_ref(session_id: str, turn_id: str) -> str:
    """Ref di provenance stabile e namespaced verso il turno verbatim."""
    return f"transcript:{session_id}:{turn_id}"


def promote_turn_to_fact(
    index: TranscriptIndex,
    turn_id: str,
    semantic_memory,
    *,
    topic: str = "conversational/promoted",
    proposition: str | None = None,
    confidence: float = 0.5,
    status: str = "model_claim",
):
    """Promuovi un turno del Tier C a ``Fact`` nel corpus, con provenance.

    Args:
        index: il TranscriptIndex (Tier C) da cui leggere il turno.
        turn_id: id del turno (== uuid del record di sessione).
        semantic_memory: istanza ``SemanticMemory`` di destinazione.
        topic: topic del fatto promosso.
        proposition: override del testo; default = testo verbatim del turno.
        confidence: fiducia iniziale (il gate può comunque declassare lo status).
        status: status richiesto; ``verified`` senza ref reali → demoto dal gate.

    Returns:
        Il ``Fact`` come persistito (``fact.status`` riflette il post-gate).

    Raises:
        ValueError: turn_id sconosciuto nel Tier C.
    """
    from .redaction import redact_secrets
    from .semantic import Fact

    turn = index.get(turn_id)
    if turn is None:
        raise ValueError(f"unknown turn_id {turn_id!r} nel Tier C")

    # Maschera segreti/credenziali PRIMA di immettere nel corpus accettato:
    # promuovere e' un ponte verso recall+banner, quindi il grezzo (anche un
    # override `proposition` libero) non deve laundering-are una API key/token.
    prop = proposition if proposition is not None else turn.text
    prop, _ = redact_secrets(prop)

    fact = Fact(
        proposition=prop,
        topic=topic,
        confidence=confidence,
        status=status,
        source_episodes=[turn_provenance_ref(turn.session_id, turn.id)],
        writer_role=PROMOTION_WRITER_ROLE,
    )
    # store() applica il gate anti-confab: verified senza evidenza → model_claim.
    semantic_memory.store(fact)
    return fact


__all__ = ["promote_turn_to_fact", "turn_provenance_ref", "PROMOTION_WRITER_ROLE"]
