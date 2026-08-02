"""DocumentIndex — semantic search over whole files with exact citation (roadmap #1).

The missing middle of the document RAG pipeline:

    file --extract_text--> text --chunk_text--> chunks --embed--> THIS INDEX
    search(query) -> chunks with (source_id, version, start, end) = exact citation

Design:
  - Versioning is delegated to the Documents tier (``DocumentStore``: snapshot
    per content-hash, idempotent re-ingest). Same content -> no re-chunking.
  - Only the LATEST version of each source is searched — an updated document
    supersedes its older chunks (no stale citations).
  - The embedder is INJECTED (any object with ``encode(list[str]) -> vectors``);
    default lazily adapts ``verimem.embedding.encode`` (the shared model/service).
    Tests run hermetic with a fake — no model load.
  - Provenance invariant inherited from ``chunking``: ``original[start:end] ==
    chunk text`` exactly, so every search hit can cite file + offsets. This is
    the provenance moat applied to documents (legal cases, books, code).

Isolated store (own SQLite), like the Documents tier: NOT wired into
``SemanticMemory.recall`` — document chunks are cited context, not accepted facts.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np

from .chunking import chunk_text
from .documents import DocumentStore
from .file_extract import extract_text
from .prompt_injection import detect_injection, sanitize_dangerous_unicode


def _row_get(row, column: str):
    """A column that may not exist on a row from a pre-migration DB read by an
    old connection. Missing → None, which is exactly "unsigned"."""
    try:
        return row[column]
    except (IndexError, KeyError):
        return None


#: Parole troppo comuni per dire qualcosa sulla pertinenza di un chunk: se la
#: query e' «come funziona l'admission gate», sono `admission` e `gate` a
#: contare. Deliberatamente corta e solo funzionale — non e' una lista di
#: stopword linguistica, e un termine di troppo qui costa al massimo un
#: conteggio piu' prudente.
_PAROLE_VUOTE = frozenset("""
come cosa quale quali quando dove perche perché chi che cui
del della dello dei delle degli di da in su per con tra fra
il lo la le un uno una gli
e ed o od ma se non piu più meno molto tutto tutti
essere sono era stato stata usa usare usano fa fare ha hanno
funziona funzionano serve servono significa vuol dire
the a an of to in on for with and or is are was were be been
what which who where when why how does do did use uses using
""".split())

_TERMINE_RE = re.compile(r"[\w'’-]{3,}", re.UNICODE)


def _termini_di_ricerca(query: str) -> list[str]:
    """I termini della query che possono dire qualcosa, minuscoli.

    L'elisione si scarta: «l'admission» vale `admission`. Senza questo passo il
    token resterebbe `l'admission`, che non e' nelle parole vuote e non compare
    in nessun testo scritto senza apostrofo — cioe' un termine che non puo' mai
    corrispondere, e un conteggio sistematicamente piu' basso del vero.
    """
    fuori = []
    for grezzo in _TERMINE_RE.findall((query or "").lower()):
        t = grezzo
        for apostrofo in ("'", "’"):
            testa, sep, coda = t.partition(apostrofo)
            if sep and len(testa) <= 2 and len(coda) >= 3:
                t = coda          # l'admission, dell'ufficio, un'ora
        if len(t) >= 3 and t not in _PAROLE_VUOTE:
            fuori.append(t)
    return fuori


_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    version    INTEGER NOT NULL,
    idx        INTEGER NOT NULL,
    start      INTEGER NOT NULL,
    end        INTEGER NOT NULL,
    text       TEXT NOT NULL,
    uri        TEXT DEFAULT '',
    vec        BLOB NOT NULL,
    flagged    INTEGER NOT NULL DEFAULT 0,
    -- P0 ciclo 2: WHO indexed this chunk (server-stamped, mirrors the
    -- snapshot's meta.indexed_by). NULL = unsigned ingest — absence stays
    -- absence, never a default that could read as a vouch nobody made.
    indexed_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id, version);
"""


class _DefaultEmbedder:
    """Adapter over the shared ``verimem.embedding.encode`` (model or service)."""

    def encode(self, texts: list[str]) -> np.ndarray:
        from .embedding import encode

        return np.asarray(encode(list(texts)), dtype=np.float32)


#: Quanto testo del chunk va al cross-encoder. I chunk sono ~1000 char, la
#: finestra del modello e' piu' corta: tagliare qui e' esplicito invece che
#: lasciarlo fare al tokenizer in silenzio.
_RERANK_MAX_CHARS = 2000


def _pool_rerank(indice, k: int) -> int:
    """Quanti candidati recuperare PRIMA del riordino.

    Senza rerank e' `k` e nulla cambia. Con il rerank si recupera largo e si
    taglia dopo: un riordino puo' solo mettere in fila cio' che riceve, e con
    `k=2` il cross-encoder ordinava due chunk sbagliati fra loro. Stessa
    funzione del percorso fatti, non una costante nuova."""
    k = max(1, int(k))
    try:
        if not indice._rerank_attivo():
            return k
        from .semantic import _rerank_topn
        return max(k, _rerank_topn())
    except Exception:  # noqa: BLE001 — in dubbio, il comportamento di prima
        return k


def _rerank_pairs(pairs, **kw):
    """I punteggi del cross-encoder, o ``None`` per degradare.

    Delega al daemon condiviso che il percorso FATTI usa dal 2026-06-13, senza
    ricopiarne la logica: budget, discovery e fallback stanno tutti la'."""
    from .semantic import _rerank_via_daemon
    return _rerank_via_daemon(pairs, **kw)


def _applica_rerank(indice, query: str, hits: list[dict]) -> list[dict]:
    """Riordina i chunk col cross-encoder. STADIO IN PIU', MAI UNA DIPENDENZA.

    PERCHE'. Il coseno del bi-encoder non separa i chunk pertinenti dai non
    pertinenti. Misurato il 2026-08-02 su un documento vero (10383 byte, 18
    chunk), tre domande a cui risponde e tre a cui no:

        [SI] quante skill hanno due status diversi   0.8272     3.1453
        [SI] cosa faceva il campo moat sui respinti  0.8120     2.0328
        [SI] quale commit ha curato il caveat        0.8292    -0.2292
        [NO] quale database usa il cluster           0.8149    -5.4931
        [NO] come si configura il proxy aziendale    0.8128    -6.6794
        [NO] qual e la ricetta della carbonara       0.7984    -5.5207

        bi-encoder   dentro min 0.8120  fuori max 0.8149  margine -0.0029
        reranker CE  dentro min -0.2292 fuori max -5.4931 margine +5.2639

    Una domanda FUORI TEMA prendeva piu' di una che il documento contiene, e
    tutti i punteggi stavano fra 0.79 e 0.83. Il commento sopra `search`
    racconta la soglia provata e buttata il 31/07 su questa stessa banda: il
    problema non era la soglia, era lo STADIO MANCANTE. Il reranker esisteva
    gia' — cablato ai fatti, non ai documenti.

    IL BI-ENCODER RESTA LEGGIBILE. `score` non viene sovrascritto e il
    punteggio del CE esce come `rerank_score`: sono due misure diverse, e chi
    consuma deve poter dire se un ordine e' stato tenuto in piedi dal solo
    coseno — la stessa onesta' che `ranking` porta sul percorso fatti.

    DEGRADA SEMPRE. Daemon assente, budget scaduto, eccezione: si torna
    all'ordine del bi-encoder, senza errori e senza attese. Spegnibile con
    ENGRAM_DOC_RERANK=0."""
    if len(hits) < 2 or not query.strip():
        return hits
    try:
        if not indice._rerank_attivo():
            return hits
        # LA GUARDIA SULLA LUNGHEZZA, la stessa del percorso fatti. Il CE
        # mmarco tronca a 512 token: su testi piu' lunghi della sua finestra
        # legge solo la testa e RIMESCOLA un ordine gia' buono (misurato
        # 2026-06-10, recall@5 0.723 contro 0.800 di base sui documenti
        # lunghi). I chunk stanno a ~1000 char e passano; un indice con
        # chunk_size alzato no, ed e' giusto cosi'.
        from .semantic import _rerank_max_doc_chars
        limite = _rerank_max_doc_chars()
        if limite:
            lunghezze = sorted(len(h.get("text") or "") for h in hits)
            mediana = lunghezze[len(lunghezze) // 2]
            if mediana > limite:
                return hits
        punteggi = _rerank_pairs(
            [(query, (h.get("text") or "")[:_RERANK_MAX_CHARS]) for h in hits])
    except Exception:  # noqa: BLE001 — mai una dipendenza, sempre un'aggiunta
        return hits
    if not punteggi or len(punteggi) != len(hits):
        return hits
    for h, p in zip(hits, punteggi, strict=True):
        h["rerank_score"] = round(float(p), 4)
    # `sorted` e non `sort`: stabile, quindi a parita' di punteggio l'ordine
    # del bi-encoder sopravvive invece di essere rimescolato.
    return sorted(hits, key=lambda h: -float(h.get("rerank_score") or 0.0))


class DocumentIndex:
    """Chunk-level semantic index with exact provenance over the Documents tier."""

    def __init__(self, db_path: Path | str | None = None, embedder=None,
                 chunk_size: int = 1000, overlap: int = 150,
                 document_store: DocumentStore | None = None) -> None:
        import os
        env = os.environ.get("HIPPO_DOCINDEX_DB", "").strip()
        self.db_path = Path(db_path) if db_path else (
            Path(env) if env
            else Path(DocumentStore().db_path).parent / "document_index.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or _DefaultEmbedder()
        self.chunk_size = int(chunk_size)
        self.overlap = int(overlap)
        # Snapshot/versioning tier lives NEXT TO the index db by default so a
        # tmp-dir test stays fully isolated from the user's real Documents tier.
        self.docs = document_store or DocumentStore(
            db_path=self.db_path.parent / "documents.db")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            # migrate pre-screen DBs: add the injection-flag column if absent
            try:
                conn.execute("ALTER TABLE chunks ADD COLUMN flagged "
                             "INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # column already present
            # migrate pre-provenance DBs (P0 ciclo 2): same additive shape.
            # Existing chunks stay NULL = unsigned, which is the truth about
            # them — they were indexed before anyone recorded who was asking.
            try:
                conn.execute("ALTER TABLE chunks ADD COLUMN indexed_by TEXT")
            except sqlite3.OperationalError:
                pass  # column already present
            conn.commit()
        finally:
            conn.close()

    # --- write ----------------------------------------------------------
    def index_document(self, source_id: str, content: str, uri: str = "",
                       meta: dict | None = None,
                       principal: str | None = None) -> dict:
        """Snapshot + chunk + embed ``content``. Idempotent per content-hash.

        Returns ``{source_id, doc_id, version, is_new, chunks_indexed}``.
        Same content re-indexed -> ``chunks_indexed == 0`` (no duplicate work).

        ``principal`` (P0 ciclo 2) is the SERVER-stamped identity of whoever
        asked for the ingest. It reaches the snapshot (``meta.indexed_by``) and
        every chunk, because a chunk is what search returns and what promotion
        turns into a fact — provenance a join away is provenance missing at the
        moment a citation is made. Absent by default: an unsigned ingest
        records nothing rather than a comfortable-looking default.
        """
        snap = self.docs.ingest(source_id, content, uri=uri, meta=meta,
                                principal=principal)
        if not snap["is_new"]:
            return {"source_id": source_id, "doc_id": snap["id"],
                    "version": snap["version"], "is_new": False,
                    "chunks_indexed": 0}
        chunks = chunk_text(content, chunk_size=self.chunk_size,
                            overlap=self.overlap)
        n_flagged = 0
        if chunks:
            vecs = np.asarray(self.embedder.encode([c.text for c in chunks]),
                              dtype=np.float32)
            # Security screen (roadmap #4, audit E3 2026-07-11): il tier
            # documenti ingerisce contenuto ESTERNO untrusted. Un chunk con un
            # payload di injection, restituito verbatim dal search nel contesto
            # dell'agente, lo dirotta (indirect prompt injection). Sanitize-then-
            # scan come nel write-gate dei fatti: si RILEVA sul testo ripulito dai
            # caratteri invisibili, si CONSERVA il testo originale (invariante di
            # citazione original[start:end]==text), si marca `flagged` e lo si
            # nasconde dal recall di default — non-lossy, audit via include_flagged.
            rows = []
            for i, c in enumerate(chunks):
                clean, _ = sanitize_dangerous_unicode(c.text)
                flagged = 1 if detect_injection(clean).is_injection else 0
                n_flagged += flagged
                rows.append((snap["id"], source_id, snap["version"], c.index,
                             c.start, c.end, c.text, uri, vecs[i].tobytes(),
                             flagged, principal))
            conn = self._connect()
            try:
                conn.executemany(
                    "INSERT INTO chunks(doc_id, source_id, version, idx, start, "
                    "end, text, uri, vec, flagged, indexed_by) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    rows,
                )
                conn.commit()
            finally:
                conn.close()
            if n_flagged:
                import logging
                logging.getLogger(__name__).warning(
                    "document %s: %d/%d chunk(s) flagged for injection signals "
                    "— hidden from default search (audit via include_flagged)",
                    source_id, n_flagged, len(chunks))
        return {"source_id": source_id, "doc_id": snap["id"],
                "version": snap["version"], "is_new": True,
                "chunks_indexed": len(chunks), "chunks_flagged": n_flagged}

    def index_file(self, path: Path | str, source_id: str | None = None,
                   meta: dict | None = None,
                   principal: str | None = None) -> dict:
        """Extract text from a real file (pdf/docx/html/txt) and index it."""
        p = Path(path)
        text = extract_text(p)
        m = dict(meta or {})
        m.setdefault("filename", p.name)
        return self.index_document(source_id if source_id is not None else str(p),
                                   text, uri=f"file://{p}", meta=m,
                                   principal=principal)

    # --- read -----------------------------------------------------------
    def search(self, query: str, k: int = 5, *,
               include_flagged: bool = False) -> list[dict]:
        """Cosine top-k over the LATEST version of every source.

        Each hit carries the exact citation: ``{text, score, source_id, version,
        start, end, uri, doc_id, flagged}`` with ``original[start:end] == text``.

        Chunks flagged for injection signals at index time (audit E3) are HIDDEN
        by default — a poisoned document must not feed the agent's context via a
        citation. ``include_flagged=True`` surfaces them for audit.
        """
        q = (query or "").strip()
        if not q:
            return []
        where = "" if include_flagged else "WHERE c.flagged = 0"
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT c.* FROM chunks c JOIN (SELECT source_id, MAX(version) AS mv "
                "FROM chunks GROUP BY source_id) m "
                "ON c.source_id = m.source_id AND c.version = m.mv "
                f"{where}",  # noqa: S608 — `where` is a constant, not user input
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            return []
        qv = np.asarray(self.embedder.encode([q]), dtype=np.float32)[0]
        qn = float(np.linalg.norm(qv)) or 1.0
        scored = []
        for r in rows:
            v = np.frombuffer(r["vec"], dtype=np.float32)
            vn = float(np.linalg.norm(v)) or 1.0
            score = float(np.dot(qv, v) / (qn * vn))
            scored.append((score, r))
        scored.sort(key=lambda t: (-t[0], t[1]["source_id"], t[1]["idx"]))
        termini = _termini_di_ricerca(q)
        hits = [{"text": r["text"], "score": round(s, 6),
                 "source_id": r["source_id"], "version": r["version"],
                 "start": r["start"], "end": r["end"], "uri": r["uri"] or "",
                 "doc_id": r["doc_id"], "flagged": bool(r["flagged"]),
                 # who vouched for this chunk (None = unsigned ingest): a
                 # citation must carry it, not require a join to find it.
                 "indexed_by": _row_get(r, "indexed_by")}
                # OVERSAMPLING per il rerank. Un riordino puo' solo mettere in
                # fila cio' che il recupero gli consegna: con k=2 il cross
                # encoder riceveva due chunk sbagliati e li ordinava fra loro.
                # Misurato dal vivo il 2026-08-02: il rerank scattava e il
                # risultato non migliorava, perche' il chunk giusto non era
                # nei candidati. Stessa forma del percorso fatti
                # (`_pool_n = max(k, _rerank_topn())`), stessa funzione: si
                # recupera largo, si riordina, si taglia a k DOPO.
                for s, r in scored[:_pool_rerank(self, int(k))]]
        # QUANTE parole della query compaiono nel testo citato.
        #
        # Misurato il 2026-07-31 sul README (47 chunk): «ricetta della carbonara
        # con guanciale» prende 0.754 e torna con la citazione ESATTA — file,
        # versione, offset di carattere. Per un umano e' un risultato strano;
        # per un agente, che e' il consumatore vero di questo tool, e' una fonte
        # con provenienza, e la citazione precisa da' autorevolezza proprio a
        # cio' che non c'entra.
        #
        # NON una soglia sul punteggio. Provata e BUTTATA lo stesso giorno: il
        # rumore stimato dell'indice (il quantile dei massimi di sonde
        # scramblate, la misura che il prodotto usa sui fatti) viene 0.8706,
        # piu' alto di TUTTE le query — comprese quelle con risposta, che stanno
        # a 0.810-0.830. Marcava tutto, cioe' niente. E' lo stesso errore
        # commesso e ritirato dodici ore prima sulla mappa dell'ignoranza: quel
        # numero e' alto per costruzione, non e' «il livello sotto cui non c'e'
        # informazione». Le due popolazioni sul coseno si sovrappongono e nessun
        # taglio le separa.
        #
        # Il conteggio lessicale invece separa (stessa prova):
        #     con risposta   copertura 0.33 - 1.00
        #     estranee       copertura 0.00 su tre casi su quattro
        #
        # E qui non si giudica: si CONTA. Zero termini in comune e' un fatto
        # verificabile da chi legge, non un verdetto con una soglia inventata
        # dentro. Chi consuma decide cosa farne.
        for h in hits:
            h["query_terms"] = len(termini)
            h["query_terms_matched"] = sum(
                1 for t in termini if t in h["text"].lower())
        return _applica_rerank(self, q, hits)[:max(1, int(k))]

    # --- rerank ---------------------------------------------------------
    def _rerank_attivo(self) -> bool:
        import os
        return os.environ.get(
            "ENGRAM_DOC_RERANK", "1").strip().lower() not in (
                "0", "false", "no", "off")

    # --- discovery ------------------------------------------------------
    def stats(self) -> dict:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n, COUNT(DISTINCT source_id) AS sources "
                "FROM chunks").fetchone()
            return {"chunks": int(row["n"]), "sources": int(row["sources"]),
                    "db_path": str(self.db_path)}
        finally:
            conn.close()


__all__ = ["DocumentIndex"]


def _self_check() -> dict:  # pragma: no cover - manual smoke helper
    """Quick manual smoke: python -c "from verimem.document_index import _self_check; print(_self_check())" """
    import tempfile

    class _E:
        def encode(self, texts):
            import hashlib
            out = []
            for t in texts:
                h = hashlib.sha256((t or "").encode()).digest()
                out.append([b / 255.0 for b in h[:16]])
            return out

    d = Path(tempfile.mkdtemp()) / "x.db"
    ix = DocumentIndex(db_path=d, embedder=_E())
    ix.index_document("s", "hello world " * 50)
    return ix.stats()
