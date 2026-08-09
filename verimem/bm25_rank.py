"""BM25 lexical ranking over fact propositions via SQLite FTS5 (competitor-gap
step 3a, 2026-06-14).

Closes Zep's first-class-BM25 gap and fixes EXACT-TOKEN recall: a commit SHA, a
file path, an error string or an API name is a single rare token the bi-encoder
smears into a dense neighborhood, so pure-cosine ranks it poorly — BM25 ranks it
first. This is the third RRF signal (alongside dense-cosine and entity-PPR); the
wiring into recall's fusion is step 3b.

Leaf module, no SemanticMemory dependency. Maintains a standalone FTS5 index
(``facts_fts(fact_id UNINDEXED, proposition)``) synced to the curated facts by row
count — a cheap heuristic sufficient for this building block; step 3b replaces it
with triggers / incremental sync. Fail-soft: returns [] on any error.
"""
from __future__ import annotations

import re
import sqlite3

#: curated view = same default filter recall uses (no superseded / hidden rows).
#: Giro 2: 'user_belief' is part of the hidden set — BM25 feeds the fusion's
#: extra-id ranklist, and a ranklist that can carry belief ids re-opens the
#: default-view side-door get(live_only=True) closes (defense in depth: both
#: layers filter, so neither is load-bearing alone).
_CURATED = ("superseded_by IS NULL "
            "AND status NOT IN ('orphaned', 'quarantined', 'user_belief')")

#: Informative-token guard (2026-07-07, fact a2217252f9ad): sotto questo numero
#: di righe FTS il filtro df non si applica (contratto storico invariato).
MIN_CORPUS_FOR_DF_FILTER = 50
#: Un token presente in più di questa quota del corpus non discrimina nulla:
#: l'OR-di-tutti-i-token lo faceva comunque matchare, riempiendo il ranklist di
#: rumore che in RRF sfrattava dense hit validi al k stretto.
DF_CEILING = 0.25

#: Function/question word (en+it): mai informative come segnale LESSICALE, e il
#: filtro df NON le prende — in un corpus di proposizioni dichiarative "what",
#: "did", "on" sono RARE (df bassa) ma il loro match è rumore puro (i 3 flip
#: residui del micro-bench 2026-07-07). Linguistica, non corpus-dipendente →
#: sempre attiva. Volutamente corta: solo funzionali inequivocabili.
_QUERY_STOPWORDS = frozenset({
    # en — question/aux/function
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "did", "does", "do", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "will", "would", "can", "could", "should", "shall",
    "may", "might", "must", "the", "an", "of", "to", "in", "on", "at", "by",
    "as", "for", "with", "from", "into", "about", "and", "or", "but", "not",
    "it", "its", "his", "her", "their", "them", "they", "he", "she", "you",
    "your", "there", "this", "that", "these", "those", "any", "some",
    # it — interrogative/funzionali
    "cosa", "che", "chi", "quando", "dove", "perche", "come", "quale", "quali",
    # it+en — le interrogative di QUANTITA'. C'erano tutte le altre e non
    # queste, cioe' proprio quelle che introducono una domanda di CONTEGGIO.
    # Misurato 2026-08-03 su uno store di quattro fatti di listino:
    #     count(query="quanto costa il piano annuale")  ->  0
    # mentre «Il piano annuale di VeriMem costa 100 euro.» era nello store:
    # `count` fa un AND sui token informativi e «quanto» restava fra questi.
    #
    # Il prodotto le conosce gia' altrove: `query_intent._STOP` — la lista del
    # router di cardinalita' — ha `how many much number count times quanti
    # quante volte numero`. Due liste, due verita', e query_intent ha i PLURALI
    # e non i singolari (una dimenticanza di genere, non di criterio).
    #
    # NON entrano i SOSTANTIVI omografi, misurati sul corpus vero (5371 fatti):
    #     count 43 — e' il nome di un metodo di questo prodotto
    #     numero 139 · volte 75 · number 10 · times 3
    # In questo dominio sono contenuto, e toglierli renderebbe non cercabili i
    # fatti che ne parlano. Stessa decisione presa per `ai` (281 come sigla
    # contro 254 come preposizione).
    "quanto", "quanta", "quanti", "quante", "many", "much",
    "il", "lo", "la", "le", "gli", "un", "una", "uno", "di", "da", "per",
    "con", "su", "tra", "fra", "del", "della", "dei", "delle", "nel", "nella",
    "ed", "sono", "era", "erano", "ha", "hanno", "aveva",
    # it — preposizioni ARTICOLATE. Ce n'erano 6 su 32 (solo le forme di `di`
    # e `in`), e le mancanti non erano rare: misurato 2026-08-02 sul corpus
    # vero, 5343 fatti vivi, `sul` in 590 (11.0%), `dal` in 522 (9.8%), `col`
    # in 298 (5.6%), `alla` in 266 (5.0%). Il filtro df non le tocca — sotto
    # il DF_CEILING del 25% — che è esattamente il caso previsto dalla nota
    # qui sopra: rare in df, rumore puro nel match.
    #
    # Generate dalla REGOLA (preposizione × articolo) e non elencate a occhio,
    # perché è così che le prime sei erano rimaste sole.
    #
    # `ai` e `al` sono ESCLUSE di proposito: questa lista è consultata sul
    # testo abbassato, e nel corpus vero «AI» maiuscolo parola intera sta in
    # 281 fatti contro i 254 di «ai» preposizione (e «AL» in 32). Metterle
    # dentro toglierebbe la sigla dal percorso lessicale in un corpus che
    # parla di AI. Distinguere per capitalizzazione è una cura diversa, da
    # misurare sul ranking prima di scriverla.
    "dello", "degli",
    "allo", "alla", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nello", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi",
})


def _tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"\w+", query.lower())
            if len(t) >= 2 and t not in _QUERY_STOPWORDS]


def _to_fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 MATCH expr: OR of double-quoted tokens
    (quoting each token neutralizes FTS5 operators, so arbitrary input never
    raises a syntax error; OR maximizes recall, the rank does the ordering)."""
    return " OR ".join(f'"{t}"' for t in _tokens(query))


def _informative_fts_query(conn: sqlite3.Connection, query: str) -> str:
    """MATCH expr limitata ai token con document-frequency <= DF_CEILING.

    Su corpus >= MIN_CORPUS_FOR_DF_FILTER un token onnipresente ("guests" in un
    corpus di soggiorni) non ordina nulla: tenerlo nella OR produce un top-N
    quasi-random. Se nessun token è informativo la query è vuota → il chiamante
    ritorna [] e la fusione degrada al dense puro. Sotto il floor: tutti i token
    (identico al comportamento storico)."""
    toks = _tokens(query)
    if not toks:
        return ""
    n_fts = conn.execute("SELECT count(*) FROM facts_fts").fetchone()[0]
    if n_fts < MIN_CORPUS_FOR_DF_FILTER:
        return " OR ".join(f'"{t}"' for t in toks)
    keep: list[str] = []
    seen: set[str] = set()
    for t in toks:
        if t in seen:
            continue
        seen.add(t)
        df = conn.execute(
            "SELECT count(*) FROM facts_fts WHERE facts_fts MATCH ?",
            (f'"{t}"',),
        ).fetchone()[0]
        if df / n_fts <= DF_CEILING:
            keep.append(t)
    return " OR ".join(f'"{t}"' for t in keep)


def _ensure_fts(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts "
        "USING fts5(fact_id UNINDEXED, proposition)"
    )
    # Incremental sync via triggers (no O(N) rebuild): the FTS index mirrors EVERY
    # facts row 1:1; the curated/status filter is applied at QUERY time (status can
    # change after insert, so it can't live in the trigger). O(1) per write.
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_ai AFTER INSERT ON facts BEGIN "
        "INSERT INTO facts_fts(fact_id, proposition) "
        "VALUES (new.id, new.proposition); END"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_ad AFTER DELETE ON facts BEGIN "
        "DELETE FROM facts_fts WHERE fact_id = old.id; END"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS facts_fts_au AFTER UPDATE ON facts BEGIN "
        "DELETE FROM facts_fts WHERE fact_id = old.id; "
        "INSERT INTO facts_fts(fact_id, proposition) "
        "VALUES (new.id, new.proposition); END"
    )
    # One-time backfill for rows that predate the FTS table/triggers.
    n_fts = conn.execute("SELECT count(*) FROM facts_fts").fetchone()[0]
    if n_fts == 0:
        n_all = conn.execute("SELECT count(*) FROM facts").fetchone()[0]
        if n_all > 0:
            conn.execute(
                "INSERT INTO facts_fts(fact_id, proposition) "
                "SELECT id, proposition FROM facts"
            )
    conn.commit()


def bm25_fact_ids(query: str | None, db_path, *, limit: int = 20) -> list[str]:
    """Return fact ids ranked by BM25 over their proposition, best first.

    Fail-soft: ``[]`` on empty query / no tokens / any sqlite or FTS error.
    """
    if not query:
        return []
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        try:
            _ensure_fts(conn)
            expr = _informative_fts_query(conn, query)
            if not expr:
                return []
            rows = conn.execute(
                "SELECT facts_fts.fact_id FROM facts_fts "
                "JOIN facts ON facts.id = facts_fts.fact_id "
                f"WHERE facts_fts MATCH ? AND facts.{_CURATED} "
                "ORDER BY bm25(facts_fts) LIMIT ?",
                (expr, int(max(1, limit))),
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — fail-soft; the fusion degrades without BM25
        return []


__all__ = ["bm25_fact_ids"]
