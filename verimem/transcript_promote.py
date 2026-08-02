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

    # IL GATE, che questo modulo prometteva e non chiamava. Il docstring dice
    # «SOTTOPOSTO al gate anti-confab di SemanticMemory.store» e «il gate gira
    # per intero (nessun bypass della provenance)», ma `store()` fa tre cose
    # diverse — redazione dei segreti, screen di sicurezza, e hard-gate su
    # `verified_by` (`verified` senza ref file/commit -> `model_claim`) — e
    # NON fa girare ne' L1 ne' il moat L4. E' un gate di SICUREZZA e
    # PROVENIENZA, e quattro moduli di questo repo lo chiamavano «il gate
    # completo» (vedi `test_store_non_e_il_gate_completo`).
    #
    # Il gemello `document_promote` e' stato curato in `8d4d393d` dopo averlo
    # MISURATO: quattro promozioni su quattro con `grounding_score=None`, e
    # fra quelle passavano una claim che la fonte CONTRADDICE e la
    # confabulazione-scuola. Qui la forma e' identica.
    #
    # LA SOURCE E' `turn.text`: quando il chiamante passa una `proposition`
    # (una distillazione del turno) il turno verbatim e' esattamente l'input
    # che L4 vuole. Quando non la passa, la proposizione E' il turno e si
    # implica da se'.
    punteggio = None
    try:
        from .anti_confab_gate import run_validation_gate
        verdetto = run_validation_gate(
            proposition=prop, verified_by=None, topic=topic,
            agent=None, writer_role=PROMOTION_WRITER_ROLE,
            source=(turn.text or "").strip() or None, ground_write=True,
        )
        punteggio = verdetto.grounding_score
        # Quarantina quando il MOAT boccia, non quando l'azione e'
        # `downgrade`: quest'ultimo copre anche il caso in cui il contenuto e'
        # implicato dalla fonte e a decadere e' solo lo STATUS — «frase grezza
        # spacciata per verificata senza prove» promossa con
        # `status="verified"` da' `downgrade` con `grounding 98.78`, e
        # `store()` la declassa gia' da sola. La differenza sta nel PUNTEGGIO
        # contro la soglia, che il verdetto porta con se'.
        _soglia = getattr(verdetto, "threshold", None)
        if verdetto.action == "reject" or (
                isinstance(punteggio, (int, float))
                and isinstance(_soglia, (int, float))
                and punteggio < _soglia):
            status = "quarantined"
    except Exception:  # noqa: BLE001 — un giudice irraggiungibile non fa passare
        # ... e non fa nemmeno cadere la promozione: resta cio' che era prima,
        # e `grounding_score=None` dice «mai giudicato», non «giudicato e
        # passato».
        punteggio = None

    fact = Fact(
        proposition=prop,
        topic=topic,
        confidence=confidence,
        status=status,
        source_episodes=[turn_provenance_ref(turn.session_id, turn.id)],
        writer_role=PROMOTION_WRITER_ROLE,
        grounding_score=punteggio,
    )
    # store() aggiunge redazione, screen di sicurezza e hard-gate sulla
    # provenienza — le tre cose che fa davvero.
    semantic_memory.store(fact)
    return fact


__all__ = ["promote_turn_to_fact", "turn_provenance_ref", "PROMOTION_WRITER_ROLE"]
