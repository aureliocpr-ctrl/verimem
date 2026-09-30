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
    memoria=None,
) -> dict:
    """Promuovi un turno del Tier C a fatto nel corpus, con provenance.

    Dal 30/09 (1b.3, P3) il fatto lo scrive il MOTORE, `Memory.add()`, come
    ogni altra scrittura: il cancello gira UNA volta, con il turno verbatim
    come fonte, e la scrittura lascia la sua traccia (evento, registro della
    fiducia, audit). Prima questo modulo chiamava il cancello da una COPIA sua
    della decisione e salvava con `store()`, che non e' la scrittura del
    prodotto.

    Args:
        index: il TranscriptIndex (Tier C) da cui leggere il turno.
        turn_id: id del turno (== uuid del record di sessione).
        semantic_memory: istanza ``SemanticMemory`` di destinazione.
        topic: topic del fatto promosso.
        proposition: override del testo; default = testo verbatim del turno.
        confidence: fiducia iniziale (il gate può comunque declassare lo status).
        status: status richiesto; ``verified`` senza ref reali → demoto dal gate.
        memoria: il motore con cui scrivere, quando la porta ne ha uno suo (il
            server MCP passa il proprio, col suo profilo); altrimenti
            ``Memory(semantic=semantic_memory)``.

    Returns:
        La RICEVUTA del motore, come per ogni scrittura (``id``, ``status``,
        ``stored``, ...), con in piu' ``provenance``: il riferimento al turno.

    Raises:
        ValueError: turn_id sconosciuto nel Tier C.
    """
    from .client import Memory
    from .redaction import redact_secrets

    turn = index.get(turn_id)
    if turn is None:
        raise ValueError(f"unknown turn_id {turn_id!r} nel Tier C")

    # Maschera segreti/credenziali PRIMA di immettere nel corpus accettato:
    # promuovere e' un ponte verso recall+banner, quindi il grezzo (anche un
    # override `proposition` libero) non deve laundering-are una API key/token.
    prop = proposition if proposition is not None else turn.text
    prop, _ = redact_secrets(prop)

    # LA SOURCE E' `turn.text`: quando il chiamante passa una `proposition`
    # (una distillazione del turno) il turno verbatim e' esattamente l'input
    # che L4 vuole. Quando non la passa, la proposizione E' il turno e si
    # implica da se'. `ground=True` come prima: senza, una porta che non
    # prende il default dal preset lascerebbe il moat alla variabile
    # d'ambiente.
    riferimento = turn_provenance_ref(turn.session_id, turn.id)
    motore = memoria if memoria is not None else Memory(semantic=semantic_memory)
    ricevuta = motore.add(
        prop, topic=topic, source=(turn.text or "").strip() or None,
        ground=True, confidence=confidence, status=status,
        writer_role=PROMOTION_WRITER_ROLE, source_episodes=[riferimento])
    ricevuta["provenance"] = [riferimento]
    return ricevuta


__all__ = ["promote_turn_to_fact", "turn_provenance_ref", "PROMOTION_WRITER_ROLE"]
