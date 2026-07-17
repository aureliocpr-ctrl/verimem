"""Tier C — conversational-raw transcript index (``verimem.transcript_index``).

Terzo strato di memoria, ISOLATO dal corpus accettato (``semantic.db``): un
indice low-trust del transcript grezzo — cosa è stato detto e *come*, verbatim.
È l'antidoto strutturale alla confabulazione: quando c'è dubbio su cosa è
realmente successo, si consulta il *nastro*, non il fatto distillato (che può
essere confabulato). Dà inoltre provenance ai fatti accettati.

Invarianti di sicurezza (perché NON inquina):
  - **Store SEPARATO** (DB dedicato, mai ``semantic.db``) → isolamento
    by-construction. È la rete PORTANTE: niente di qui può affiorare nel recall
    del corpus accettato.
  - **confidence = 0.0 + source_type = 'conversational_raw'** su ogni riga → se
    mai una ricerca federata futura lo includesse, sta in fondo ed è marcato
    debole (seconda rete, difesa in profondità).
  - **Pull-only**: questa API è dedicata; NON è wired in
    ``SemanticMemory.recall`` né nel banner di sessione.
  - **embedding_model per-riga + filtro recall** (lezione v9): evita il
    poisoning same-dim se il modello di embedding cambia.

La promozione ``turn → Fact`` verificato (con provenance), attraverso il gate
anti-confab, è una fase successiva. Qui: solo cattura + recall grezzo.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import embedding as emb
from .config import _LEGACY_EMBEDDING_MODEL, CONFIG
from .redaction import redact_secrets

#: Modello assunto per le righe pre-stamp (``embedding_model`` NULL = MiniLM
#: storico). Importato FROZEN da ``.config`` (NON ridefinito qui) e DECOUPLED dal
#: default ATTIVO: dopo il flip 2026-06-04 l'attivo è multilingue ma una riga NULL
#: resta MiniLM ed è ESCLUSA dal recall (anti cross-space poisoning, BUCO-2).
#: Allineato a semantic/memory/skill v9. ``_LEGACY_EMBEDDING_MODEL`` importato sopra.

#: Tag di provenienza: marca ogni riga come fonte debole/non verificata.
SOURCE_TYPE: str = "conversational_raw"

#: Fiducia di default: ~0 (conversazione grezza, NON verità accettata).
DEFAULT_CONFIDENCE: float = 0.0


@dataclass
class Turn:
    """Un turno di conversazione grezzo (verbatim)."""

    text: str
    session_id: str = "unknown"
    role: str = "user"
    ts: float = 0.0
    source_path: str = ""
    source_offset: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    confidence: float = DEFAULT_CONFIDENCE
    source_type: str = SOURCE_TYPE


def default_db_path() -> Path:
    """Path di default del Tier C — DB dedicato, separato da ``CONFIG.semantic_db``.

    Override con env ``HIPPO_TRANSCRIPT_DB`` (config ops + isolamento nei test).
    """
    env = os.environ.get("HIPPO_TRANSCRIPT_DB", "").strip()
    if env:
        return Path(env)
    return Path(CONFIG.data_dir) / "conversational" / "transcript.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    ts              REAL DEFAULT 0,
    role            TEXT,
    text            TEXT NOT NULL,
    embedding       BLOB,
    embedding_model TEXT,
    source_path     TEXT,
    source_offset   INTEGER DEFAULT 0,
    confidence      REAL DEFAULT 0.0,
    source_type     TEXT DEFAULT 'conversational_raw'
);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
"""

_INSERT = (
    "INSERT OR REPLACE INTO turns(id, session_id, ts, role, text, embedding, "
    "embedding_model, source_path, source_offset, confidence, source_type) "
    "VALUES(?,?,?,?,?,?,?,?,?,?,?)"
)


class TranscriptIndex:
    """Indice isolato e low-trust del transcript grezzo. Pull-only."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # --- write ---------------------------------------------------------
    def store(self, turn: Turn) -> str:
        """Persisti un turno. Stampa SEMPRE embedding_model + confidence=0 +
        source_type (invarianti, non sovrascrivibili dal chiamante)."""
        text = redact_secrets(turn.text or "")[0]   # defense-in-depth (see store_batch)
        vec = emb.encode(text)
        conn = self._connect()
        try:
            conn.execute(_INSERT, (
                turn.id, turn.session_id, turn.ts, turn.role, text,
                emb.serialize(vec), emb.model_signature(),
                turn.source_path, turn.source_offset,
                DEFAULT_CONFIDENCE, SOURCE_TYPE,
            ))
            conn.commit()
        finally:
            conn.close()
        return turn.id

    def store_batch(self, turns) -> int:
        """Persisti molti turni in un colpo (encode batch per velocità)."""
        turns = list(turns)
        if not turns:
            return 0
        # Defense-in-depth (WF1 2026-06-19): redact secrets HERE too, so the Tier C
        # invariant holds for ANY caller (not only ingest via parse_turns). Mirrors the
        # F5 store_batch fix on the semantic/episode path. The redacted text is what gets
        # BOTH embedded and stored.
        texts = [redact_secrets(t.text or "")[0] for t in turns]
        vecs = emb.encode(texts)
        if vecs.ndim == 1:  # difensivo: un solo elemento
            vecs = vecs.reshape(1, -1)
        model = emb.model_signature()
        rows = [
            (
                t.id, t.session_id, t.ts, t.role, texts[i],
                emb.serialize(vecs[i]), model, t.source_path,
                t.source_offset, DEFAULT_CONFIDENCE, SOURCE_TYPE,
            )
            for i, t in enumerate(turns)
        ]
        conn = self._connect()
        try:
            conn.executemany(_INSERT, rows)
            conn.commit()
        finally:
            conn.close()
        return len(rows)

    # --- read (pull-only) ---------------------------------------------
    def _load_rows(self, session_id: str | None):
        # length-guard (parità con semantic.py): scarta SQL-side i blob di
        # lunghezza errata (corrotti/troncati, classe incidente cycle-171
        # embedding=b'') così recall() degrada con grazia invece di crashare in
        # np.array con 'inhomogeneous shape'. expected_embedding_bytes() è
        # CONFIG-derived (regge l'override env della dim) — NON un literal.
        sql = (
            "SELECT id, session_id, ts, role, text, embedding, source_path, "
            "source_offset, confidence, source_type FROM turns "
            "WHERE COALESCE(embedding_model, ?) = ? AND length(embedding) = ?"
        )
        params: list = [
            _LEGACY_EMBEDDING_MODEL, emb.model_signature(),
            emb.expected_embedding_bytes(),
        ]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)
        conn = self._connect()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def recall(self, query: str, k: int = 10, session_id: str | None = None):
        """Recall semantico SUL SOLO Tier C (pull-only). Ritorna ``[(Turn, score)]``.

        NB: deliberatamente NON tocca ``semantic.db``: è l'unico modo di leggere
        questo strato, e non esiste cammino che lo inietti nel recall del corpus.
        """
        rows = self._load_rows(session_id)
        if not rows:
            return []
        qv = emb.encode(query)
        mat = np.array([emb.deserialize(r["embedding"]) for r in rows], dtype=np.float32)
        sims = emb.cosine_matrix(qv, mat)
        # NaN-guard: un embedding di lunghezza giusta (passa il length-guard) ma con
        # valori non-finiti (NaN/inf) produrrebbe score non-finiti che inquinano il
        # ranking. Maschera a -inf e SCARTA quelle righe dal risultato (degrada con
        # grazia invece di restituire score NaN). Classe-fratello di cycle-171 (b'').
        finite = np.isfinite(sims)
        if not finite.all():
            sims = np.where(finite, sims, -np.inf)
        order = np.argsort(-sims)[: max(0, k)]
        return [
            (self._row_to_turn(rows[i]), float(sims[i]))
            for i in order if np.isfinite(sims[i])
        ]

    def get(self, turn_id: str) -> Turn | None:
        """Recupera un turno per id (usato da promozione / ispezione)."""
        conn = self._connect()
        try:
            r = conn.execute(
                "SELECT id, session_id, ts, role, text, source_path, "
                "source_offset, confidence, source_type FROM turns WHERE id = ?",
                (turn_id,),
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_turn(r) if r else None

    def count(self, session_id: str | None = None) -> int:
        conn = self._connect()
        try:
            if session_id is None:
                return int(conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0])
            return int(conn.execute(
                "SELECT COUNT(*) FROM turns WHERE session_id = ?", (session_id,),
            ).fetchone()[0])
        finally:
            conn.close()

    def prune(self, *, max_turns: int | None = None,
              before_ts: float | None = None,
              session_id: str | None = None) -> int:
        """Retention: cancella turni per cap (``max_turns``, tiene i più recenti
        per ts) e/o per età (``before_ts``). Con ``session_id`` lo scope è SOLO
        quella sessione (le altre NON vengono toccate). Ritorna il numero di
        righe cancellate. Per la crescita bounded a scala.
        """
        deleted = 0
        conn = self._connect()
        try:
            if before_ts is not None:
                sql = "DELETE FROM turns WHERE ts < ?"
                params: list = [before_ts]
                if session_id is not None:
                    sql += " AND session_id = ?"
                    params.append(session_id)
                deleted += conn.execute(sql, params).rowcount
            if max_turns is not None:
                if session_id is not None:
                    sql = (
                        "DELETE FROM turns WHERE session_id = ? AND id NOT IN "
                        "(SELECT id FROM turns WHERE session_id = ? "
                        "ORDER BY ts DESC, rowid DESC LIMIT ?)"
                    )
                    params = [session_id, session_id, max_turns]
                else:
                    sql = (
                        "DELETE FROM turns WHERE id NOT IN "
                        "(SELECT id FROM turns ORDER BY ts DESC, rowid DESC LIMIT ?)"
                    )
                    params = [max_turns]
                deleted += conn.execute(sql, params).rowcount
            conn.commit()
        finally:
            conn.close()
        return int(deleted)

    @staticmethod
    def _row_to_turn(r) -> Turn:
        return Turn(
            id=r["id"], session_id=r["session_id"], ts=r["ts"], role=r["role"],
            text=r["text"], source_path=r["source_path"],
            source_offset=r["source_offset"], confidence=r["confidence"],
            source_type=r["source_type"],
        )


__all__ = [
    "Turn",
    "TranscriptIndex",
    "default_db_path",
    "SOURCE_TYPE",
    "DEFAULT_CONFIDENCE",
]
