"""doc -> Fact GATED promotion — the last brick of the document RAG (roadmap #1).

A retrieved chunk (``DocumentIndex.search`` hit) can be PROMOTED into the recall
corpus as a Fact — but through the same anti-confab discipline as everything
else, never around it:

  * status stays ``model_claim`` (a document says it; that does not make it
    verified truth — evidence elevates status later, not the promotion);
  * ``writer_role="document_promote"`` — a dedicated, non-trusted writer, so the
    full admission gate runs;
  * the citation ``file:<source_id>:<start>-<end>`` goes into ``verified_by``
    AND ``source_episodes``. The offsets are exact ON THE INDEXED TEXT
    (``indexed_text[start:end] == chunk``) and the chunk text is stored with
    them, so the claim is always checkable against what was indexed. They are
    NOT a promise that the original file still opens: the path is recorded as
    given and never resolved, so a moved, deleted or relative one stops
    resolving — measured 2026-08-12 on the real corpus, 538 of 634 chunks
    (84.9%) pointed at files that no longer existed, with the chunk text
    present for 100% of them. ⚠️ This matters more here than elsewhere because
    the citation lands in ``verified_by``, the provenance field: it certifies
    WHAT WAS INDEXED, not that a reader can re-open the source today.

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
    _trattenuto_da = ""                    # quale layer L1, se e' stato L1
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
        # ...MA UN LAYER L1 NON E' UNA QUESTIONE DI PUNTEGGIO, e il criterio
        # qui sopra non poteva vederlo. Misurato sul percorso reale (lo si e'
        # isolato, io l'ho riprodotto):
        #     «Ho verificato che la funzione ora funziona»   add() quarantined
        #                                          promote() model_claim 99.9572
        #     «Il modulo e' stato testato ed e' pronto»      99.9825
        #     «Il bug e' stato risolto e il sistema e' stabile»  99.9840
        #     quarantinati da add() 3/3  ·  SERVIBILI via promozione 3/3
        # E il punteggio non e' un errore del moat: e' il piu' alto del corpus
        # perche' la frase sta LETTERALMENTE dentro il documento, quindi la
        # fonte la implica davvero.
        # 🔑 La distinzione che mancava non e' fra punteggi: e' fra «il
        # documento RIPORTA X» e «X e' vero». Per un dato oggettivo («il
        # magazzino contiene 300 pallet») coincidono; per un'auto-attestazione
        # no — il moat conferma la CITAZIONE, non il fatto.
        # ⚠️ Non tocca la scelta documentata qui sopra, perche' non guarda
        # l'azione: guarda DA QUALE LAYER viene il downgrade. Un `downgrade`
        # da L4/provenienza resta ammesso (contenuto implicato, decade solo lo
        # status); L1.x significa auto-attestazione senza prova, ed e' cio' che
        # `facts add` cestina dall'altra porta. Presidi in
        # test_il_vanto_entrava_dalla_porta_dei_documenti.py: i tre dati
        # oggettivi dello stesso documento continuano a promuoversi.
        # ⚠️ SOLO CON UN `claim` ESPLICITO, e la distinzione l'ha insegnata un
        # test che veniva da main (test_il_chunk_grezzo_CONTINUA_a_passare):
        # senza `claim` la proposizione E' IL CHUNK, cioe' il documento stesso,
        # e un documento che contiene «la migrazione e' completa» non e'
        # l'agente che rivendica un merito — e' un testo che riporta una frase.
        # Applicarci L1 era lo stesso errore di categoria che ho curato ieri
        # sul router di provenienza (F1 C2), rifatto da un'altra porta.
        # Con `claim`, invece, chi promuove sta DISTILLANDO un'affermazione e se
        # ne fa carico: li' L1 ha giurisdizione, ed e' il caso del vanto.
        _l1 = [str(w.get("layer")) for w in (verdetto.warnings or [])
               if claim is not None
               and str(w.get("layer", "")).startswith("L1")]
        if verdetto.action == "reject" or _l1 or (
                isinstance(punteggio, (int, float))
                and isinstance(_soglia, (int, float))
                and punteggio < _soglia):
            stato = "quarantined"
            if _l1:
                # Chi promuove deve sapere che e' stato L1 e non il moat: il
                # punteggio dira' 99.9 e senza il layer la ricevuta sembrerebbe
                # contraddirsi da sola.
                _trattenuto_da = ",".join(sorted(set(_l1)))
    except Exception:  # noqa: BLE001 — un gate irraggiungibile non fa passare
        # ... e non fa nemmeno cadere la promozione: resta un `model_claim`
        # senza verdetto, che e' cio' che era prima e che il lettore riconosce
        # da `grounding_score=None` («mai giudicato», non «giudicato e
        # passato»).
        punteggio = None

    # UN PUNTEGGIO TAUTOLOGICO NON E' UN VERDETTO. Senza `claim` la
    # proposizione E' il chunk, quindi il moat verifica «X implica X» e
    # risponde ~100 per costruzione. Misurato il 2026-08-04 su tre documenti
    # senza niente in comune: 99.95, 99.96, 99.98 — mentre le stesse tre fonti
    # con una claim che NON dicono danno 0.00, 0.23, 0.00. Il gate funziona; e'
    # la domanda a non esserci.
    #
    # Pubblicarlo sarebbe peggio che tacerlo: il prodotto insegna a leggere
    # quel numero come «the moat's verdict on that fact» e a trust-condizionare
    # su di esso, e la promozione mette in `verified_by` la citazione esatta del
    # file. Il fatto uscirebbe con il punteggio piu' alto del corpus E una
    # provenienza puntuale, mentre nessuno ha verificato niente — il documento
    # puo' dire qualunque cosa. Lo stesso testo che `facts add` quarantina
    # entrava da qui come model_claim con 99.97.
    #
    # `None` e' la descrizione esatta di questo caso ed e' quella che il
    # prodotto gia' insegna: «null means NEVER JUDGED, not judged and failed».
    # Il chunk grezzo continua a passare: cambia solo che non porta piu' un
    # verdetto che non ha. Confronto sulle parole, non sui caratteri, perche' la
    # redazione dei segreti puo' aver riscritto `prop`.
    nota_punteggio = None
    if punteggio is not None and prop.split() == chunk_text.split():
        nota_punteggio = (
            "no grounding verdict: the proposition IS the source chunk, so the "
            "moat would only confirm that the text says what it says. Pass a "
            "distilled `claim` to get a real entailment check against the chunk."
        )
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
            "error": None, "grounding_note": nota_punteggio,
            # Vuoto quando non e' stato L1: cosi' la ricevuta distingue «il
            # moat ha bocciato» da «il documento lo dice ma e' un vanto», che
            # con il solo punteggio erano indistinguibili — 99.98 in ENTRAMBI
            # i casi, perche' la fonte contiene davvero la frase.
            "trattenuto_da": _trattenuto_da,
            "status": stato}
