"""P2.a — Entity-Centric Knowledge Graph (minimum viable).

Spec: docs/specs/p2-entity-centric-kg.md (commit 48678a2).

Scope di questo modulo (P2.a):
  - 3 tabelle SQLite: entities, entity_aliases, entity_facts
  - `EntityStore` con store / get_by_name / add_alias / link_fact /
    facts_for_entity
  - Look-up case-insensitive su canonical_name e alias

Out-of-scope (P2.b/c):
  - entity_edges con weight + predicate
  - PPR retrieval (richiede networkx + edge graph)
  - OpenIE LLM-based extraction
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import unicodedata
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Top-level networkx import: paga cold-start una volta al boot del
# modulo invece che alla prima ppr() — elimina p99 outlier ~1s.
# Round-3 bench L1 cycle #70 (docs/bench/cycle-70-p2-load).
import networkx as nx

from .config import CONFIG

_SCHEMA = """
-- Schema v3: name_norm/alias_norm sono Python-lowered (str.lower(),
-- full-Unicode) e indicizzati. SQLite LOWER() è ASCII-only quindi
-- inadatto a un KG che contiene Müller, Erdős, Schrödinger, İstanbul.
-- Round-3 critic counterexample 0.95.
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    name_norm TEXT NOT NULL DEFAULT '',  -- Python str.lower()
    type TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
-- v1 non-unique index su LOWER(canonical_name) (ASCII-only, deprecato).
-- Migration v3 lo droppa e crea UNIQUE su name_norm Python-side.
CREATE INDEX IF NOT EXISTS idx_entities_name_lower
    ON entities(LOWER(canonical_name));

CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_norm TEXT NOT NULL DEFAULT '',  -- Python str.lower()
    PRIMARY KEY (entity_id, alias),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_aliases_alias_lower
    ON entity_aliases(LOWER(alias));

CREATE TABLE IF NOT EXISTS entity_facts (
    fact_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY (fact_id, entity_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_entity_facts_entity
    ON entity_facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_facts_fact
    ON entity_facts(fact_id);

-- P2.b (migration v5): entity_edges per neighbors + PPR retrieval.
-- PRIMARY KEY composito su (src, dst, predicate) garantisce dedupe
-- idempotente. source_fact_id soft-reference (no FK cross-DB).
CREATE TABLE IF NOT EXISTS entity_edges (
    src_entity TEXT NOT NULL,
    dst_entity TEXT NOT NULL,
    predicate TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    source_fact_id TEXT,
    created_at REAL NOT NULL,
    PRIMARY KEY (src_entity, dst_entity, predicate),
    FOREIGN KEY (src_entity) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (dst_entity) REFERENCES entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON entity_edges(src_entity);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON entity_edges(dst_entity);

-- P3 minimal (migration v6): entity_attrs key-value store generico.
-- Riusabile da multi-anchor self-model + future P4 metadata.
-- value_json TEXT contiene JSON serializzato (supporta number/str/
-- dict/list). UPSERT via INSERT OR REPLACE su PK composito.
CREATE TABLE IF NOT EXISTS entity_attrs (
    entity_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (entity_id, key),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_attrs_entity
    ON entity_attrs(entity_id);
"""


def _norm(s: str) -> str:
    """Unicode-canonical, case-folded normalizer per equality matching.

    Pipeline (in ordine): `(s or "").strip()` → `unicodedata.normalize`
    `("NFC", ...)` → `.lower()`. Tre garanzie distinte:

      1. Full Unicode case-folding (Ü→ü, Ő→ő, Ç→ç). SQLite built-in
         LOWER() è ASCII-only e non lo fa (round-3 counterexample 0.95).
      2. Form-folding NFC: precompone caratteri combinati. macOS APFS,
         OCR, scraping web possono mescolare NFC ('Müller', 6 cp) e NFD
         ('Müller' u + combining diaeresis, 7 cp); senza normalizzare
         restano byte-distinti (round-4 counterexample 0.92).
      3. Trim: spazi leading/trailing non sono semanticamente rilevanti.
    """
    return unicodedata.normalize(
        "NFC", (s or "").strip(),
    ).lower()


def _migrate_v1_initial(conn: sqlite3.Connection) -> None:  # noqa: ARG001
    """v1 no-op: lo schema base è già creato via _SCHEMA executescript
    nel costruttore. Serve solo a stabilire un punto di partenza
    contiguo per ensure_schema_version (current=0 → 1 → 2)."""
    return


def _migrate_v2_unique_index(conn: sqlite3.Connection) -> None:
    """Round 2 critic counterexample fix #1: garantisce UNIQUE index su
    LOWER(canonical_name).

    Se esisteva l'index v1 non-unique (`idx_entities_name_lower`), lo
    droppa. Prima del CREATE UNIQUE, dedup eventuali duplicate esistenti
    (case-insensitive): tiene il created_at minore e riassegna
    entity_aliases + entity_facts al survivor.
    """
    # 1) cleanup pre-existing duplicates (case-insensitive)
    dup_rows = conn.execute(
        "SELECT LOWER(canonical_name) AS k, "
        "GROUP_CONCAT(id, '|') AS ids "
        "FROM entities GROUP BY LOWER(canonical_name) HAVING COUNT(*) > 1"
    ).fetchall()
    for row in dup_rows:
        ids = row["ids"].split("|")
        # survivor = id con min created_at; gli altri vengono assorbiti
        order_rows = conn.execute(
            f"SELECT id FROM entities WHERE id IN "  # noqa: S608
            f"({','.join('?' * len(ids))}) "
            "ORDER BY created_at ASC, id ASC",
            ids,
        ).fetchall()
        survivor = order_rows[0]["id"]
        losers = [r["id"] for r in order_rows[1:]]
        for loser in losers:
            conn.execute(
                "UPDATE OR IGNORE entity_aliases SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "UPDATE OR IGNORE entity_facts SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "DELETE FROM entity_aliases WHERE entity_id = ?",
                (loser,),
            )
            conn.execute(
                "DELETE FROM entity_facts WHERE entity_id = ?",
                (loser,),
            )
            conn.execute("DELETE FROM entities WHERE id = ?", (loser,))
    # 2) drop old non-unique index if present
    conn.execute("DROP INDEX IF EXISTS idx_entities_name_lower")
    # 3) ensure new unique index (v2 — ancora ASCII-only via SQLite
    # LOWER. La v3 successiva lo droppa e ricrea su name_norm Unicode.)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "idx_entities_name_lower_unique "
        "ON entities(LOWER(canonical_name))"
    )


def _migrate_v3_python_norm(conn: sqlite3.Connection) -> None:
    """Round 3 critic counterexample fix #2: sostituisce gli index basati
    su SQLite LOWER() (ASCII-only) con index su colonne `name_norm` e
    `alias_norm` popolate Python-side con `str.lower()` full-Unicode.

    Schema delta:
      - entities: ADD COLUMN name_norm TEXT NOT NULL DEFAULT ''
      - entity_aliases: ADD COLUMN alias_norm TEXT NOT NULL DEFAULT ''
      - backfill di entrambe via Python str.lower()
      - dedup di duplicate Unicode (es. MÜLLER/Müller pre-existenti)
      - DROP idx_entities_name_lower, idx_entities_name_lower_unique,
        idx_aliases_alias_lower
      - CREATE UNIQUE INDEX su entities(name_norm),
        CREATE INDEX su entity_aliases(alias_norm)
    """
    # 1) ALTER TABLE ADD COLUMN (idempotente via check PRAGMA table_info)
    cols_entities = {
        r["name"] for r in conn.execute(
            "PRAGMA table_info(entities)",
        ).fetchall()
    }
    if "name_norm" not in cols_entities:
        conn.execute(
            "ALTER TABLE entities ADD COLUMN name_norm TEXT "
            "NOT NULL DEFAULT ''"
        )
    cols_aliases = {
        r["name"] for r in conn.execute(
            "PRAGMA table_info(entity_aliases)",
        ).fetchall()
    }
    if "alias_norm" not in cols_aliases:
        conn.execute(
            "ALTER TABLE entity_aliases ADD COLUMN alias_norm TEXT "
            "NOT NULL DEFAULT ''"
        )

    # 2) Backfill: Python str.lower() su tutte le row (full Unicode)
    rows = conn.execute(
        "SELECT id, canonical_name FROM entities"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE entities SET name_norm = ? WHERE id = ?",
            ((r["canonical_name"] or "").strip().lower(), r["id"]),
        )
    rows = conn.execute(
        "SELECT entity_id, alias FROM entity_aliases"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE entity_aliases SET alias_norm = ? "
            "WHERE entity_id = ? AND alias = ?",
            ((r["alias"] or "").strip().lower(),
             r["entity_id"], r["alias"]),
        )

    # 3) Dedup duplicate Unicode (group by name_norm Python-computed)
    dup_rows = conn.execute(
        "SELECT name_norm, GROUP_CONCAT(id, '|') AS ids "
        "FROM entities "
        "WHERE name_norm != '' "
        "GROUP BY name_norm HAVING COUNT(*) > 1"
    ).fetchall()
    for row in dup_rows:
        ids = row["ids"].split("|")
        order_rows = conn.execute(
            f"SELECT id FROM entities WHERE id IN "  # noqa: S608
            f"({','.join('?' * len(ids))}) "
            "ORDER BY created_at ASC, id ASC",
            ids,
        ).fetchall()
        survivor = order_rows[0]["id"]
        losers = [r["id"] for r in order_rows[1:]]
        for loser in losers:
            conn.execute(
                "UPDATE OR IGNORE entity_aliases SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "UPDATE OR IGNORE entity_facts SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "DELETE FROM entity_aliases WHERE entity_id = ?",
                (loser,),
            )
            conn.execute(
                "DELETE FROM entity_facts WHERE entity_id = ?",
                (loser,),
            )
            conn.execute("DELETE FROM entities WHERE id = ?", (loser,))

    # 4) Drop old ASCII-only indexes
    conn.execute("DROP INDEX IF EXISTS idx_entities_name_lower")
    conn.execute("DROP INDEX IF EXISTS idx_entities_name_lower_unique")
    conn.execute("DROP INDEX IF EXISTS idx_aliases_alias_lower")

    # 5) New Unicode-safe indexes
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_name_norm_unique "
        "ON entities(name_norm)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_aliases_alias_norm "
        "ON entity_aliases(alias_norm)"
    )


def _migrate_v4_nfc_norm(conn: sqlite3.Connection) -> None:
    """Round 4 critic counterexample fix #3: ri-backfilla name_norm /
    alias_norm via `_norm()` che ora include `unicodedata.normalize`
    `("NFC", ...)`.

    Senza NFC, due stringhe visivamente identiche con encoding diverso
    (NFC pre-composto vs NFD u+combining-diaeresis) restavano byte-
    distinte e producevano duplicate. macOS APFS, OCR, scraping web,
    e P2.c OpenIE writer le mescoleranno deterministicamente.

    Idempotente: applicarlo due volte è un no-op (NFC è idempotente).

    Round-4 counterexample 0.9 fix: se il DB v3 contiene già duplicate
    NFC+NFD (l'UNIQUE INDEX v3 le vede byte-distinte), le UPDATE
    successive violerebbero il vincolo. Soluzione: DROP l'UNIQUE INDEX
    PRIMA delle UPDATE, dedup, poi ricreare UNIQUE.
    """
    # 0) DROP UNIQUE INDEX v3 (verrà ricreato alla fine). Senza questo
    # passaggio, le UPDATE collassano due righe NFC/NFD nello stesso
    # name_norm e violano l'UNIQUE costruito da v3.
    conn.execute("DROP INDEX IF EXISTS idx_entities_name_norm_unique")

    # 1) Recompute name_norm con NFC (str.lower seguito da NFC via _norm)
    rows = conn.execute(
        "SELECT id, canonical_name FROM entities"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE entities SET name_norm = ? WHERE id = ?",
            (_norm(r["canonical_name"]), r["id"]),
        )

    # 2) Dedup duplicate post-NFC (NFC+NFD pre-existenti ora collassano)
    dup_rows = conn.execute(
        "SELECT name_norm, GROUP_CONCAT(id, '|') AS ids "
        "FROM entities WHERE name_norm != '' "
        "GROUP BY name_norm HAVING COUNT(*) > 1"
    ).fetchall()
    for row in dup_rows:
        ids = row["ids"].split("|")
        order_rows = conn.execute(
            f"SELECT id FROM entities WHERE id IN "  # noqa: S608
            f"({','.join('?' * len(ids))}) "
            "ORDER BY created_at ASC, id ASC",
            ids,
        ).fetchall()
        survivor = order_rows[0]["id"]
        losers = [r["id"] for r in order_rows[1:]]
        for loser in losers:
            conn.execute(
                "UPDATE OR IGNORE entity_aliases SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "UPDATE OR IGNORE entity_facts SET entity_id = ? "
                "WHERE entity_id = ?",
                (survivor, loser),
            )
            conn.execute(
                "DELETE FROM entity_aliases WHERE entity_id = ?",
                (loser,),
            )
            conn.execute(
                "DELETE FROM entity_facts WHERE entity_id = ?",
                (loser,),
            )
            conn.execute("DELETE FROM entities WHERE id = ?", (loser,))

    # 3) Recompute alias_norm con NFC
    rows = conn.execute(
        "SELECT entity_id, alias FROM entity_aliases"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE entity_aliases SET alias_norm = ? "
            "WHERE entity_id = ? AND alias = ?",
            (_norm(r["alias"]), r["entity_id"], r["alias"]),
        )

    # 4) Ricrea UNIQUE INDEX su name_norm — adesso senza duplicate
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_name_norm_unique "
        "ON entities(name_norm)"
    )


def _migrate_v6_entity_attrs(conn: sqlite3.Connection) -> None:
    """P3 minimal — entity_attrs key-value store generico. Idempotente
    via CREATE IF NOT EXISTS (lo schema base è già in _SCHEMA).
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS entity_attrs (
            entity_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            PRIMARY KEY (entity_id, key),
            FOREIGN KEY (entity_id) REFERENCES entities(id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_attrs_entity
            ON entity_attrs(entity_id);
        """
    )


def _migrate_v5_entity_edges(conn: sqlite3.Connection) -> None:
    """P2.b — entity_edges table per neighbors + PPR. Lo schema è già
    creato da _SCHEMA executescript (CREATE TABLE IF NOT EXISTS), questo
    step esiste solo per stabilire il punto di ladder v4→v5 e permettere
    futuri delta non-additivi (es. nuovi index o triggers).
    """
    # Defensive: garantisce l'esistenza della tabella anche se un DB
    # legacy l'avesse droppata manualmente. CREATE IF NOT EXISTS è
    # idempotente.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS entity_edges (
            src_entity TEXT NOT NULL,
            dst_entity TEXT NOT NULL,
            predicate TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 1.0,
            source_fact_id TEXT,
            created_at REAL NOT NULL,
            PRIMARY KEY (src_entity, dst_entity, predicate),
            FOREIGN KEY (src_entity) REFERENCES entities(id)
                ON DELETE CASCADE,
            FOREIGN KEY (dst_entity) REFERENCES entities(id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_edges_src
            ON entity_edges(src_entity);
        CREATE INDEX IF NOT EXISTS idx_edges_dst
            ON entity_edges(dst_entity);
        """
    )


@dataclass
class Entity:
    canonical_name: str = ""
    type: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)


class EntityStore:
    """SQLite-backed entity store con alias resolution e fact linking."""

    def __init__(self, db_path: Path | None = None) -> None:
        # Default path: <CONFIG.data_dir>/entity_kg/entity_kg.db
        if db_path is None:
            db_path = CONFIG.data_dir / "entity_kg" / "entity_kg.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # session() state is per-thread: store() runs on daemon threads via
        # store_within_budget, and sqlite connections are not cross-thread.
        self._session_local = threading.local()
        # PPR graph cache (competitor-gap step 1, 2026-06-14): ppr/ppr_weighted
        # rebuilt the full nx.DiGraph from entity_edges on EVERY call — fine for a
        # manual tool, too slow to fuse the graph signal into hot recall. Cache the
        # built graph keyed by a cross-process PRAGMA data_version probe (mirror of
        # Semantic/EpisodicMemory): add_edge's commit bumps data_version so the
        # cache rebuilds, otherwise reads reuse it. This is the enabling
        # optimization that makes the entity-PPR ranking affordable default-ON.
        self._graph: Any = None
        self._graph_dv = -2  # sentinel; never equals a real/-1 probe initially
        self._dv_conn: sqlite3.Connection | None = None
        self._dv_lock = threading.Lock()
        self._graph_lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            try:
                from .migrations import ensure_schema_version

                ensure_schema_version(
                    conn, db_id="entity_kg",
                    target_version=6,
                    migrations=[
                        (1, _migrate_v1_initial),
                        (2, _migrate_v2_unique_index),
                        (3, _migrate_v3_python_norm),
                        (4, _migrate_v4_nfc_norm),
                        (5, _migrate_v5_entity_edges),
                        (6, _migrate_v6_entity_attrs),
                    ],
                )
            except ImportError:  # pragma: no cover — defensive
                pass

    @contextmanager
    def session(self) -> Iterator[EntityStore]:
        """Share ONE connection across a batch of store/link/add_edge calls.

        Latency fix (2026-06-10): the per-call ``_connect`` pattern opened
        ~76 connections per ingested fact (one per store/link_fact/add_edge)
        — 122 ms/store locally and a broken 3 s anti-hang guard on the cold
        windows CI runner. Inside a session every ``_connect`` reuses the
        thread's open connection; commit happens once on exit, rollback on
        error. Nested sessions reuse the outer one. Thread-isolated via
        ``threading.local`` (store() runs on daemon threads through
        ``store_within_budget``).
        """
        if getattr(self._session_local, "conn", None) is not None:
            yield self  # nested: the outer session owns commit/close
            return
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
            from engram._sqlite_pragma import synchronous_mode
            conn.execute(f"PRAGMA synchronous={synchronous_mode()};")
            conn.execute("PRAGMA foreign_keys=ON;")
        except sqlite3.OperationalError:
            pass
        self._session_local.conn = conn
        try:
            yield self
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            self._session_local.conn = None
            conn.close()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # Inside a session() reuse the thread's connection — the session
        # owns commit/close (intermediate reads must see its writes).
        sess: sqlite3.Connection | None = getattr(
            self._session_local, "conn", None,
        ) if hasattr(self, "_session_local") else None
        if sess is not None:
            yield sess
            return
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
            from engram._sqlite_pragma import synchronous_mode
            conn.execute(f"PRAGMA synchronous={synchronous_mode()};")
            conn.execute("PRAGMA foreign_keys=ON;")
        except sqlite3.OperationalError:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def store(self, entity: Entity) -> str:
        """Insert entity. If `canonical_name` already exists
        (case-insensitive Unicode, on entities.canonical_name only — NOT
        on alias), return the existing id without duplicating.

        Contract (post round-3 critic fix):
          - canonical_name strippato deve essere non-vuoto → ValueError.
          - dedupe Unicode-safe via name_norm (Python str.lower(),
            full Unicode case-folding). SQLite LOWER() ASCII-only NON è
            usato in alcun confronto.
          - dedupe SOLO su canonical_name match (mai cross-alias), per
            permettere promozione alias→canonical di entity distinte.
          - Concorrency-safe: BEGIN IMMEDIATE serializza i writer;
            UNIQUE INDEX su name_norm è il backstop DB-level che
            converte la finestra residua in IntegrityError gestita
            con re-SELECT.
        """
        canon = (entity.canonical_name or "").strip()
        if not canon:
            raise ValueError(
                "Entity.canonical_name must be non-empty (got "
                f"{entity.canonical_name!r})"
            )
        canon_norm = _norm(canon)
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                # già in transazione o WAL non disponibile: procediamo;
                # lo UNIQUE INDEX su name_norm garantisce correttezza.
                pass
            row = conn.execute(
                "SELECT id FROM entities WHERE name_norm = ?",
                (canon_norm,),
            ).fetchone()
            if row is not None:
                return row["id"]
            try:
                conn.execute(
                    "INSERT INTO entities "
                    "(id, canonical_name, name_norm, type, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (entity.id, canon, canon_norm, entity.type,
                     entity.created_at),
                )
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT id FROM entities WHERE name_norm = ?",
                    (canon_norm,),
                ).fetchone()
                if row is not None:
                    return row["id"]
                raise
        return entity.id

    def get_by_name(self, name_or_alias: str) -> Entity | None:
        """Lookup case-insensitive Unicode: prima su canonical_name,
        poi su alias. Ritorna None se nessuna entity trovata.
        """
        if not name_or_alias:
            return None
        needle = _norm(name_or_alias)
        if not needle:
            return None
        with self._connect() as conn:
            # 1) match canonical name (Python-normalized)
            row = conn.execute(
                "SELECT * FROM entities WHERE name_norm = ?",
                (needle,),
            ).fetchone()
            if row is not None:
                return self._row_to_entity(row)
            # 2) match alias (Python-normalized)
            row = conn.execute(
                "SELECT e.* FROM entities e "
                "JOIN entity_aliases a ON a.entity_id = e.id "
                "WHERE a.alias_norm = ?",
                (needle,),
            ).fetchone()
            if row is not None:
                return self._row_to_entity(row)
        return None

    def add_alias(self, entity_id: str, alias: str) -> None:
        """Add alias for an existing entity. Idempotent.

        Popola anche `alias_norm` via Python str.lower() per lookup
        Unicode-safe (round-3 critic counterexample 0.95).
        """
        a = (alias or "").strip()
        if not a:
            return
        a_norm = _norm(a)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO entity_aliases "
                "(entity_id, alias, alias_norm) VALUES (?, ?, ?)",
                (entity_id, a, a_norm),
            )

    def link_fact(self, fact_id: str, entity_id: str) -> None:
        """Associate a fact_id to an entity. Idempotent
        (PRIMARY KEY (fact_id, entity_id))."""
        if not fact_id or not entity_id:
            return
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO entity_facts (fact_id, entity_id) "
                "VALUES (?, ?)",
                (fact_id, entity_id),
            )

    def facts_for_entity(self, entity_id: str) -> list[str]:
        """Return all fact_ids linked to this entity."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT fact_id FROM entity_facts WHERE entity_id = ?",
                (entity_id,),
            ).fetchall()
        return [r["fact_id"] for r in rows]

    def entities_for_fact(self, fact_id: str) -> list[str]:
        """Return all entity_ids linked to this fact (inverse of
        ``facts_for_entity``)."""
        if not fact_id:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT entity_id FROM entity_facts WHERE fact_id = ?",
                (fact_id,),
            ).fetchall()
        return [r["entity_id"] for r in rows]

    def aliases_of(self, entity_id: str) -> list[str]:
        """Return all aliases for an entity."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT alias FROM entity_aliases WHERE entity_id = ?",
                (entity_id,),
            ).fetchall()
        return [r["alias"] for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM entities",
            ).fetchone()[0]

    # ---------- P3 minimal: entity_attrs key-value store ------------

    def set_attr(
        self, entity_id: str, key: str, value: Any,
    ) -> None:
        """UPSERT su entity_attrs. value viene JSON-serializzato.
        Update mantiene created_at originale, aggiorna updated_at.
        """
        if not entity_id or not key:
            raise ValueError("entity_id and key must be non-empty")
        try:
            value_json = json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"value not JSON-serializable: {e}"
            ) from e
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO entity_attrs "
                "(entity_id, key, value_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(entity_id, key) DO UPDATE SET "
                "value_json = excluded.value_json, "
                "updated_at = excluded.updated_at",
                (entity_id, key, value_json, now, now),
            )

    def get_attrs(self, entity_id: str) -> dict[str, Any]:
        """Ritorna dict {key → JSON-decoded value}. Empty se entity
        non esiste o non ha attrs."""
        if not entity_id:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value_json FROM entity_attrs "
                "WHERE entity_id = ?",
                (entity_id,),
            ).fetchall()
        out: dict[str, Any] = {}
        for r in rows:
            try:
                out[r["key"]] = json.loads(r["value_json"])
            except (ValueError, TypeError):
                out[r["key"]] = r["value_json"]  # fallback raw
        return out

    def get_attr(
        self, entity_id: str, key: str, default: Any = None,
    ) -> Any:
        """Ritorna singolo attr decoded, o `default` se mancante."""
        if not entity_id or not key:
            return default
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value_json FROM entity_attrs "
                "WHERE entity_id = ? AND key = ?",
                (entity_id, key),
            ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value_json"])
        except (ValueError, TypeError):
            return row["value_json"]

    # ---------- P2.b: edges + neighbors + PPR -----------------------

    def add_edge(
        self,
        src_entity: str,
        dst_entity: str,
        predicate: str,
        weight: float = 1.0,
        source_fact_id: str | None = None,
    ) -> None:
        """Insert directed edge src -> dst with predicate metadata.

        Idempotente: PRIMARY KEY (src, dst, predicate) + INSERT OR
        IGNORE. Se la tripla esiste, la chiamata è no-op (weight
        originale preservato — politica conservativa per P2.b minimal).
        """
        if not src_entity or not dst_entity or not predicate:
            raise ValueError(
                "src_entity, dst_entity, predicate must be non-empty"
            )
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO entity_edges "
                "(src_entity, dst_entity, predicate, weight, "
                "source_fact_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (src_entity, dst_entity, predicate, float(weight),
                 source_fact_id, time.time()),
            )

    def _db_data_version(self) -> int:
        """Cross-process cache-coherence probe (mirror of Semantic/EpisodicMemory).

        ``PRAGMA data_version`` on a LONG-LIVED connection changes whenever any
        other connection/process commits to entity_kg.db — including add_edge from
        the write-path EntityStore (semantic.store builds a separate instance). On
        any sqlite error: drop the probe conn and return -1 (a sentinel that never
        equals a stored dv → forces a rebuild rather than serving a stale graph).
        """
        with self._dv_lock:
            try:
                if self._dv_conn is None:
                    self._dv_conn = sqlite3.connect(
                        self.db_path, timeout=10.0, check_same_thread=False,
                    )
                return int(
                    self._dv_conn.execute("PRAGMA data_version").fetchone()[0]
                )
            except sqlite3.Error:
                try:
                    if self._dv_conn is not None:
                        self._dv_conn.close()
                except sqlite3.Error:
                    pass
                self._dv_conn = None
                return -1

    def _get_graph(self) -> Any:
        """Build (or reuse) the entity nx.DiGraph from entity_edges.

        Cached across calls and invalidated by ``data_version`` (any edge/entity
        commit, same-instance or cross-process). Returns a graph that callers MUST
        treat as read-only (pagerank does not mutate it).
        """
        dv = self._db_data_version()
        with self._graph_lock:
            if self._graph is not None and self._graph_dv == dv:
                return self._graph
            graph = nx.DiGraph()
            with self._connect() as conn:
                for row in conn.execute("SELECT id FROM entities"):
                    graph.add_node(row["id"])
                for row in conn.execute(
                    "SELECT src_entity, dst_entity, weight FROM entity_edges",
                ):
                    graph.add_edge(
                        row["src_entity"], row["dst_entity"],
                        weight=float(row["weight"]),
                    )
            self._graph = graph
            self._graph_dv = dv
            return graph

    def edges_from(self, entity_id: str) -> list[dict[str, Any]]:
        """Return outgoing edges (src_entity = entity_id)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT src_entity, dst_entity, predicate, weight, "
                "source_fact_id, created_at FROM entity_edges "
                "WHERE src_entity = ? ORDER BY created_at ASC",
                (entity_id,),
            ).fetchall()
        return [
            {
                "src_entity": r["src_entity"],
                "dst_entity": r["dst_entity"],
                "predicate": r["predicate"],
                "weight": float(r["weight"]),
                "source_fact_id": r["source_fact_id"],
                "created_at": float(r["created_at"]),
            }
            for r in rows
        ]

    def neighbors(
        self,
        entity_id: str,
        k: int = 10,
        hops: int = 1,
    ) -> list[dict[str, Any]]:
        """BFS neighbors fino a `hops` di distanza, capped a `k`.

        Ritorna lista di dict `{entity_id, predicate, weight, distance}`
        ordinata per distance asc, poi per inserzione (created_at via
        edges_from). NON include il nodo di partenza.
        """
        if hops < 1 or k < 1:
            return []
        visited: dict[str, int] = {entity_id: 0}
        result: list[dict[str, Any]] = []
        queue: list[tuple[str, int]] = [(entity_id, 0)]
        while queue:
            cur, d = queue.pop(0)
            if d >= hops:
                continue
            for edge in self.edges_from(cur):
                dst = edge["dst_entity"]
                if dst in visited:
                    continue
                visited[dst] = d + 1
                result.append({
                    "entity_id": dst,
                    "predicate": edge["predicate"],
                    "weight": edge["weight"],
                    "distance": d + 1,
                })
                queue.append((dst, d + 1))
        return result[:k]

    def traced_paths(
        self,
        entity_id: str,
        max_hops: int = 2,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Multi-hop traversal that KEEPS the chain of custody — the trust
        differentiator ``neighbors`` throws away.

        BFS from ``entity_id``; for each reachable target the FULL edge chain
        that reached it (shortest path — fewest links = most trust), each hop
        carrying ``predicate`` + ``source_fact_id`` + ``weight``. Per path:

        * ``hops``       — ordered edges ``{src_entity, dst_entity, predicate,
          source_fact_id, weight}`` from the start to the target;
        * ``grounded``   — True iff EVERY hop cites a ``source_fact_id`` (an
          ungrounded hop is FLAGGED, not hidden — the caller can abstain);
        * ``min_weight`` — the weakest link, i.e. the trust of the whole path;
        * ``path_weight``— product of hop weights (decays with length).

        Shortest path wins on ties (BFS reaches a node at its minimal depth
        first); a node is never revisited within a path, so cycles terminate.
        Returns at most ``k`` paths, shortest first then by ``min_weight``
        desc. Deterministic, no model, no network — the safe core the
        answerer and TrustReport build the reasoning dossier on.
        """
        if max_hops < 1 or k < 1:
            return []
        best: dict[str, dict[str, Any]] = {}
        # queue holds (current_node, path_so_far); BFS guarantees the first
        # time we settle a target it is via a shortest path.
        queue: list[tuple[str, list[dict[str, Any]]]] = [(entity_id, [])]
        while queue:
            cur, path = queue.pop(0)
            if len(path) >= max_hops:
                continue
            on_path = {entity_id} | {h["dst_entity"] for h in path}
            for edge in self.edges_from(cur):
                dst = edge["dst_entity"]
                if dst in on_path:
                    continue  # no revisit within this path -> cycle-safe
                hop = {
                    "src_entity": edge["src_entity"],
                    "dst_entity": dst,
                    "predicate": edge["predicate"],
                    "source_fact_id": edge["source_fact_id"],
                    "weight": edge["weight"],
                }
                new_path = path + [hop]
                # settle the target the FIRST time BFS reaches it (shortest);
                # a later, longer path to the same target is discarded.
                if dst not in best:
                    weights = [h["weight"] for h in new_path]
                    product = 1.0
                    for w in weights:
                        product *= w
                    best[dst] = {
                        "target": dst,
                        "hops": new_path,
                        "grounded": all(
                            h["source_fact_id"] for h in new_path),
                        "min_weight": min(weights),
                        "path_weight": product,
                    }
                queue.append((dst, new_path))
        out = sorted(
            best.values(),
            key=lambda p: (len(p["hops"]), -p["min_weight"]))
        return out[:k]

    def _rank_facts(
        self,
        ranked: list[dict[str, Any]],
        k_facts: int,
    ) -> list[dict[str, Any]]:
        """Rank facts by the summed PPR mass of the entities linking them.

        The HippoRAG retrieval signal proper (2026-06-10): the legacy
        ``facts`` union is unusable at corpus scale (live probe "Engram"
        → 1 039 unordered facts). A fact linked by SEVERAL high-score
        entities beats a fact hanging off one hub. One aggregate query
        for all top-k entities; deterministic (-score, fact_id) order.
        """
        if not ranked or k_facts <= 0:
            return []
        score_of = {r["entity_id"]: float(r["score"]) for r in ranked}
        ids = list(score_of)
        placeholders = ",".join("?" * len(ids))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT fact_id, entity_id FROM entity_facts "
                f"WHERE entity_id IN ({placeholders})",  # noqa: S608 — ids are internal uuids
                ids,
            ).fetchall()
        agg: dict[str, dict[str, Any]] = {}
        for r in rows:
            d = agg.setdefault(r["fact_id"], {"score": 0.0, "n": 0})
            d["score"] += score_of[r["entity_id"]]
            d["n"] += 1
        out = [
            {"fact_id": fid, "score": float(v["score"]),
             "n_entities": int(v["n"])}
            for fid, v in agg.items()
        ]
        out.sort(key=lambda x: (-x["score"], x["fact_id"]))
        return out[:k_facts]

    def fact_counts(self, entity_ids: list[str]) -> tuple[int, dict[str, int]]:
        """(fatti distinti totali in entity_facts, {entity_id: n fatti linkati}).

        Serve all'hub-guard del PPR seeding (2026-07-07): un'entità che linka
        una quota alta del corpus non discrimina nulla come seed. Due query
        aggregate, nessun fetch di righe.
        """
        if not entity_ids:
            return 0, {}
        placeholders = ",".join("?" * len(entity_ids))
        with self._connect() as conn:
            total = conn.execute(
                "SELECT count(DISTINCT fact_id) FROM entity_facts",
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT entity_id, count(DISTINCT fact_id) AS n "
                f"FROM entity_facts WHERE entity_id IN ({placeholders}) "  # noqa: S608 — internal uuids
                "GROUP BY entity_id",
                entity_ids,
            ).fetchall()
        return int(total), {r["entity_id"]: int(r["n"]) for r in rows}

    def ppr(
        self,
        query_entities: list[str],
        damping: float = 0.5,
        k: int = 20,
        k_facts: int = 20,
    ) -> dict[str, Any]:
        """Personalized PageRank su grafo entity (HippoRAG pattern).

        Costruisce DiGraph in memoria da TUTTI gli edge in
        entity_edges (full corpus), applica `nx.pagerank` con
        personalization uniforme sui `query_entities` validi (ignorati
        gli id sconosciuti). Ritorna:
          - `ranked`: top-k entity ordinate per score desc
          - `facts`: union dei fact_id linked alle entity top-k
            (legacy, NON ordinata per rilevanza — back-compat)
          - `facts_ranked`: top-`k_facts` fact ordinati per somma degli
            score PPR delle entity che li linkano (il segnale di
            retrieval vero e proprio)
          - `graph_size`: {nodes, edges}

        Determinismo: networkx.pagerank è deterministico se il grafo
        ha edges weighted; usa power-iteration con tol=1e-6 default.
        """
        if not 0.0 <= damping <= 1.0:
            raise ValueError(
                f"damping must be in [0, 1], got {damping}"
            )
        # 1) build (or reuse the cached) DiGraph da tutti gli edges
        graph = self._get_graph()

        # 2) personalization su query_entities validi
        valid_seeds = [
            qe for qe in query_entities if graph.has_node(qe)
        ]
        personalization: dict[str, float] | None
        if valid_seeds:
            # SPARSE: only the seeds. networkx assigns 0.0 to every omitted
            # node, so this is identical to a dense zero-fill but avoids the
            # per-call O(graph_nodes) allocation over the full corpus.
            mass = 1.0 / len(valid_seeds)
            personalization = {s: mass for s in valid_seeds}
        else:
            # nessun seed valido → uniform pagerank (default networkx)
            personalization = None

        if graph.number_of_nodes() == 0:
            return {
                "ranked": [],
                "facts": [],
                "facts_ranked": [],
                "graph_size": {"nodes": 0, "edges": 0},
            }

        # 3) compute pagerank — tol e max_iter default networkx;
        # deterministico su grafo statico.
        scores = nx.pagerank(
            graph,
            alpha=damping,
            personalization=personalization,
            tol=1e-6,
            max_iter=200,
        )

        # 4) top-k ordinato deterministicamente
        ranked_pairs = sorted(
            scores.items(),
            key=lambda kv: (-kv[1], kv[0]),  # tie-break by id asc
        )[:k]
        ranked = [
            {"entity_id": eid, "score": float(score)}
            for eid, score in ranked_pairs
        ]

        # 5) facts unione dalle top-k entity
        facts: list[str] = []
        seen: set[str] = set()
        for r in ranked:
            for fid in self.facts_for_entity(r["entity_id"]):
                if fid not in seen:
                    seen.add(fid)
                    facts.append(fid)

        return {
            "ranked": ranked,
            "facts": facts,
            "facts_ranked": self._rank_facts(ranked, k_facts),
            "graph_size": {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
            },
        }

    def ppr_weighted(
        self,
        personalization: dict[str, float],
        damping: float = 0.5,
        k: int = 20,
        k_facts: int = 20,
    ) -> dict[str, Any]:
        """Variante di ppr() che accetta `personalization` dict
        pre-pesato (entity_id → weight in [0, 1], sommabile a 1.0).

        Usato da P3 hippo_anchor_recall per applicare decay temporale
        esponenziale ai pesi degli anchor. Stesso contratto di ppr():
        include `facts_ranked` (top-`k_facts` per somma degli score).
        """
        if not 0.0 <= damping <= 1.0:
            raise ValueError(
                f"damping must be in [0, 1], got {damping}"
            )
        graph = self._get_graph()
        if graph.number_of_nodes() == 0:
            return {
                "ranked": [], "facts": [], "facts_ranked": [],
                "graph_size": {"nodes": 0, "edges": 0},
            }
        # Filter personalization a nodi presenti nel grafo
        valid_pers: dict[str, float] = {}
        total = 0.0
        for eid, w in personalization.items():
            if graph.has_node(eid) and w > 0:
                valid_pers[eid] = float(w)
                total += float(w)
        if not valid_pers or total <= 0:
            # uniform fallback
            full = None
        else:
            # SPARSE: only the weighted seeds (networkx zero-fills the rest);
            # avoids the per-call O(graph_nodes) dense build over the corpus.
            full = {eid: w / total for eid, w in valid_pers.items()}

        scores = nx.pagerank(
            graph, alpha=damping, personalization=full,
            tol=1e-6, max_iter=200,
        )
        ranked_pairs = sorted(
            scores.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )[:k]
        ranked = [
            {"entity_id": eid, "score": float(score)}
            for eid, score in ranked_pairs
        ]
        facts: list[str] = []
        seen: set[str] = set()
        for r in ranked:
            for fid in self.facts_for_entity(r["entity_id"]):
                if fid not in seen:
                    seen.add(fid)
                    facts.append(fid)
        return {
            "ranked": ranked,
            "facts": facts,
            "facts_ranked": self._rank_facts(ranked, k_facts),
            "graph_size": {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
            },
        }

    def list_anchors(self) -> list[dict[str, Any]]:
        """List all entity with type='anchor' + their attrs."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, canonical_name FROM entities "
                "WHERE type = 'anchor'",
            ).fetchall()
        out = []
        for r in rows:
            out.append({
                "entity_id": r["id"],
                "name": r["canonical_name"],
                "attrs": self.get_attrs(r["id"]),
            })
        return out

    @staticmethod
    def _row_to_entity(r: sqlite3.Row) -> Entity:
        return Entity(
            id=r["id"],
            canonical_name=r["canonical_name"],
            type=r["type"] or "",
            created_at=float(r["created_at"]),
        )
