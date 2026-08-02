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

    # IL GATE, che questo modulo prometteva e non chiamava. Il docstring dice
    # «through the same anti-confab discipline as everything else, NEVER
    # AROUND IT» e «the full admission gate runs», ma `semantic.store()` non
    # ha un parametro `source` e non importa mai `anti_confab_gate`: misurato
    # eseguendo, quattro promozioni su quattro uscivano con
    # `grounding_score=None`, e fra quelle passavano «Il piano annuale costa
    # 500 euro» — che il chunk CONTRADDICE — e la confabulazione-scuola che
    # ogni altro canale quarantina.
    #
    # E pesa piu' di una scrittura qualunque: la promozione mette la citazione
    # esatta del file in `verified_by`, quindi il fatto esce con l'aria di
    # essere verificato DAL DOCUMENTO mentre il documento puo' dire il
    # contrario. La provenienza diventa una decorazione.
    #
    # LA SOURCE C'ERA GIA' E VENIVA BUTTATA: `hit["text"]` e' il chunk, e
    # quando il chiamante passa un `claim` distillato quel testo e' esattamente
    # l'input che L4 vuole — source = il chunk, claim = la frase. Il caso d'uso
    # principale del modulo E' il caso d'uso principale del moat.
    chunk_text = str(hit.get("text", "") or "").strip()
    stato = "model_claim"                  # a claim, never laundered truth
    punteggio = None
    try:
        from .anti_confab_gate import run_validation_gate
        verdetto = run_validation_gate(
            proposition=prop, verified_by=[citation], topic=topic,
            agent=None, writer_role=PROMOTE_WRITER_ROLE,
            source=chunk_text or None, ground_write=True,
        )
        punteggio = verdetto.grounding_score
        # QUARANTINA QUANDO IL MOAT BOCCIA, non quando l'azione e'
        # `downgrade`. La prima versione di questa riga guardava
        # `action in ("reject","downgrade")` ed era SBAGLIATA: `downgrade`
        # copre due situazioni diverse, e un test gia' in repo l'ha presa —
        # «frase grezza spacciata per verificata senza prove» promossa con
        # `status="verified"` da' `action=downgrade` con `grounding 98.78`,
        # cioe' il contenuto e' implicato dalla fonte e a decadere e' solo lo
        # STATUS. Trattarlo come una quarantena avrebbe nascosto un fatto
        # buono per un difetto di provenienza, che `store()` gia' corregge da
        # solo. Misurato: contraddetta 0.44 e confabulazione 0.38 sono
        # `downgrade` quanto quella, e vanno trattenute — la differenza sta
        # nel PUNTEGGIO, non nell'azione, e il verdetto porta la sua soglia.
        _soglia = getattr(verdetto, "threshold", None)
        if verdetto.action == "reject" or (
                isinstance(punteggio, (int, float))
                and isinstance(_soglia, (int, float))
                and punteggio < _soglia):
            stato = "quarantined"
    except Exception:  # noqa: BLE001 — un gate irraggiungibile non fa passare
        # ... e non fa nemmeno cadere la promozione: resta un `model_claim`
        # senza verdetto, che e' cio' che era prima e che il lettore riconosce
        # da `grounding_score=None` («mai giudicato», non «giudicato e
        # passato»).
        punteggio = None

    fact = Fact(
        proposition=prop,
        topic=topic,
        confidence=confidence,
        status=stato,
        verified_by=[citation],            # the checkable file citation
        source_episodes=[citation] + ([f"doc_version:{version}"] if version else []),
        writer_role=PROMOTE_WRITER_ROLE,
        grounding_score=punteggio,
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
