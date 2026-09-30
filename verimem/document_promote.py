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
    #: 1b.3 — CHI sta scrivendo, dichiarato dal chiamante. La porta MCP passa
    #: il suo `_MCP_PRINCIPAL`: senza, una promozione entrata da un agente
    #: resta indistinguibile da una scrittura interna, ed e' proprio la
    #: distinzione per cui quel timbro esiste. `None` lascia ad `add()` il suo
    #: default, cosi' i chiamanti che non lo passano si comportano come prima.
    principal: str | None = None,
) -> dict:
    """Store ``hit`` (a DocumentIndex search result) as a gated Fact.

    Returns ``{"stored": bool, "fact_id": str | None, "citation": str,
    "error": str | None}``. Fail-safe: a gate rejection reports, never raises.
    """
    from .redaction import redact_secrets

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
    # T192 — IL GIUDICE GIRA UNA VOLTA SOLA, E GIRA DENTRO `add()`.
    #
    # Qui c'erano ~170 righe che chiamavano `run_validation_gate` e ne
    # rileggevano il verdetto con una politica scritta a mano: quali L1
    # contano, quali `*-observe` no, quali layer numerici valgono il giudice,
    # dove sta la soglia. Poi `Memory.add()` — che questa via chiama subito
    # dopo — rifaceva tutto con la PROPRIA politica e SOVRASCRIVEVA il
    # risultato. Due giudici sulla stessa scrittura, e il secondo vinceva
    # sempre: il verdetto calcolato qui non veniva letto da nessuno.
    #
    # Misurato il 21/09 sul ramo che aveva introdotto il secondo passaggio:
    #     3 failed, 7 passed in 32.95s   (ramo)
    #     10 passed in 35.16s            (main pulito, stesso comando)
    # e i tre rossi dicevano esattamente questo — `'quarantined' ==
    # 'model_claim'` su un L1 tenuto advisory, su un `L4.1-ambiguo`, e sul
    # chunk grezzo. Non erano tre difetti: era un disaccordo fra due copie
    # della stessa regola.
    #
    # ⚠️ E LA POLITICA NON SI PERDE, perche' DUE TERZI NON ERANO MAI STATI
    # DI QUESTA VIA. Il gate li ha gia' dentro, e sono le stesse righe:
    #     anti_confab_gate.py:230   LAYER_NUMERICI_COME_IL_GIUDICE
    #     anti_confab_gate.py:3249  has_grounding_fail = any(... in quelli)
    #     anti_confab_gate.py:237   _is_advisory_layer  (un `*-observe` non
    #                               e' un layer in piu')
    # Copiarli qui voleva dire mantenerne due versioni e scoprire che
    # divergevano da un rosso. Restava DAVVERO di questa via una cosa sola:
    # **di chi e' la proposizione**, ed e' quella che si dichiara qui sotto.
    #
    # SENZA `claim` LA PROPOSIZIONE E' IL CHUNK, cioe' testo di un documento,
    # e i detector L1.x gradano la sincerita' dell'AGENTE: applicarli li' e'
    # l'errore di categoria che `gate_router` esiste per evitare. CON un
    # `claim` chi promuove sta DISTILLANDO un'affermazione e se ne fa carico,
    # quindi L1 ha giurisdizione — ed e' il caso del vanto, presidiato da
    # `test_il_vanto_entrava_dalla_porta_dei_documenti.py`.
    #
    # Il timbro NON cambia: `writer_role` resta `document_promote` perche' un
    # banco lo pretende con la sua ragione (`test_document_promote.py:51`,
    # «no trusted-hook bypass»). Cambia solo cio' che il gate sente dire, e
    # per questo `add()` ha ora due ingressi invece di uno.
    from .client import Memory
    from .gate_router import EXTERNAL_CONTENT

    # ⚠️ LA `Memory` SI COSTRUISCE DAL FILE CHE QUESTO STORE HA GIA' APERTO.
    # `Memory(path)` vuole il FILE del database: passargli una cartella alza
    # `OperationalError`, e passargli un percorso sbagliato NON fallisce —
    # apre un secondo store vuoto, e le scritture finiscono dove nessuno
    # guarda. `semantic_memory.db_path` e' l'unico percorso che non puo'
    # divergere da quello che il chiamante sta gia' usando. Due connessioni
    # allo stesso file convivono (WAL + `busy_timeout`, gia' impostati da
    # `_connect`); due FILE diversi no, ed e' cio' che la prima cella del
    # banco misura.
    _autoreferenziale = prop.split() == chunk_text.split()

    # UN PUNTEGGIO TAUTOLOGICO NON E' UN VERDETTO. Senza `claim` la
    # proposizione E' il chunk, quindi il moat verificherebbe «X implica X» e
    # risponderebbe ~100 per costruzione. Misurato il 2026-08-04 su tre
    # documenti senza niente in comune: 99.95, 99.96, 99.98 — mentre le stesse
    # tre fonti con una claim che NON dicono danno 0.00, 0.23, 0.00. Il gate
    # funziona; e' la domanda a non esserci. Pubblicare quel numero sarebbe
    # peggio che tacerlo, perche' il prodotto insegna a leggerlo come «the
    # moat's verdict on that fact» e la promozione mette in `verified_by` la
    # citazione esatta del file: il fatto uscirebbe col punteggio piu' alto
    # del corpus E una provenienza puntuale, mentre nessuno ha verificato
    # niente. `ground=False` dice al motore di non fare quella domanda, e
    # `None` e' la descrizione esatta del risultato — «null means NEVER
    # JUDGED, not judged and failed», che e' quanto il prodotto gia' insegna.
    # Confronto sulle parole, non sui caratteri, perche' la redazione dei
    # segreti puo' aver riscritto `prop`.
    nota_punteggio = (
        "no grounding verdict: the proposition IS the source chunk, so the "
        "moat would only confirm that the text says what it says. Pass a "
        "distilled `claim` to get a real entailment check against the chunk."
    ) if _autoreferenziale else None
    try:
        _ricevuta = Memory(getattr(semantic_memory, "db_path", None)).add(
            prop,
            topic=topic,
            source=chunk_text,
            ground=not _autoreferenziale,
            confidence=confidence,
            verified_by=[citation],        # the checkable file citation
            source_episodes=(
                [citation] + ([f"doc_version:{version}"] if version else [])),
            writer_role=PROMOTE_WRITER_ROLE,
            # T192 — L'UNICA DECISIONE DI DOMINIO CHE RESTA A QUESTA VIA.
            # Il timbro sopra dice CHI scrive; questo dice al gate DI CHI e'
            # il testo. Senza `claim` la proposizione e' il chunk, cioe' un
            # documento, e L1.x non ha giurisdizione; con un `claim` chi
            # promuove ha distillato una frase e se ne fa carico, quindi L1
            # torna a valere e il moat la giudica contro il chunk.
            gate_writer_role=None if claim is not None else EXTERNAL_CONTENT,
            principal=principal,
        )
    except Exception as exc:  # noqa: BLE001 — gate rejection is a result, not a crash
        return {"stored": False, "fact_id": None, "citation": citation,
                "error": f"gate rejected: {exc!s:.120}"}
    if not _ricevuta.get("stored"):
        return {"stored": False, "fact_id": None, "citation": citation,
                "error": f"gate rejected: {_ricevuta.get('advice') or ''!s:.120}"}
    # SI LEGGE LA RICEVUTA, non si rilegge il fatto e non si ricalcola niente.
    # `add()` ha gia' deciso, gia' scritto e gia' compilato `quarantined_by`
    # nella colonna che le tre porte del write path riempiono con lo stesso
    # vocabolario (`chi_ha_quarantinato`: moat / L1 / il layer che ha agito).
    # Qui c'era una `persisti_chi_ha_quarantinato` che rifaceva quel lavoro
    # con il verdetto della copia locale: una seconda scrittura per dire una
    # cosa che era gia' scritta, e che poteva dirla DIVERSA.
    stato = str(_ricevuta.get("status") or "model_claim")
    # QUALE LAYER, non quale famiglia — ed e' una distinzione che la ricevuta
    # fa gia', in due campi diversi. Misurato sul vanto distillato:
    #     fermato_da     = 'L1'        quarantined_by = 'L1'
    #     livelli        = [{'nome': 'L1.15', …}, {'nome': 'L1.20', …}]
    # `fermato_da` dice la FAMIGLIA, che e' il vocabolario con cui le tre
    # porte riempiono la colonna; `livelli` dice i NOMI. Chi promuove ha
    # bisogno dei nomi: «L1» non gli dice se e' stato il rilevatore del
    # «testato» o quello della frase-vetrina, e leggere «L1» dove prima
    # c'era «L1.15» e' la stessa perdita curata in T77, quando una porta
    # scriveva «gate» al posto del layer. Il banco lo pretende in entrambi i
    # modi: nome nella ricevuta, famiglia nella colonna.
    # Vuoto quando non ha fermato nessuno: un elenco di avvisi su un fatto
    # ammesso direbbe «trattenuto da» di qualcosa che e' passato.
    _trattenuto_da = ",".join(
        str(_l.get("nome")) for _l in (_ricevuta.get("livelli") or [])
        if isinstance(_l, dict) and _l.get("nome")) if stato == "quarantined" else ""
    # `None` quando non e' stato giudicato — e con `ground=False`, cioe' sul
    # chunk grezzo, e' esattamente il caso: mai giudicato, non giudicato e
    # passato.
    punteggio = _ricevuta.get("grounding_score")
    return {"stored": True, "fact_id": _ricevuta.get("id"), "citation": citation,
            "error": None, "grounding_note": nota_punteggio,
            # Il punteggio del giudice esce anche in ricevuta: prima andava
            # riletto dal fatto (None = mai giudicato, come sempre).
            "grounding_score": punteggio,
            # Vuoto quando non e' stato L1: cosi' la ricevuta distingue «il
            # moat ha bocciato» da «il documento lo dice ma e' un vanto», che
            # con il solo punteggio erano indistinguibili — 99.98 in ENTRAMBI
            # i casi, perche' la fonte contiene davvero la frase.
            "trattenuto_da": _trattenuto_da,
            "status": stato,
            # 1b.3 — LE CHIAVI DEL NUCLEO, che `add()` rende gia': qui si
            # smette di buttarle via. L'unione mette le nuove SOPRA le
            # vecchie, e le vecchie restano finche' dura il debito, cosi' i
            # lettori di `stored`/`status`/`citation` continuano a funzionare.
            # Non c'e' una seconda traduzione: quella la fa `add()`, una
            # volta, per tutte le porte — che e' il senso della fetta.
            **{k: v for k, v in _ricevuta.items()
               if k not in ("stored", "status", "grounding_score")}}
