"""Verimem self-host gateway — REST API multi-tenant sopra l'SDK Memory.

Roadmap #3, scenario B "server di team" (fact 805158d9a8ee): il motore era già
multi-client (SQLite WAL, 500 processi concorrenti a 0 errori) ma l'unico
transport era MCP stdio sullo stesso host + una dashboard loopback. Questo
modulo aggiunge il transport remoto self-hostabile: il cliente ospita la
memoria a casa propria (LAN / server privato / VPS), il dato non passa da noi.

Design:
  * **auth API-key** — chiavi ``vm_<40hex>`` generate server-side, mostrate
    UNA volta; a riposo solo lo sha256 (``gateway_keys.db``), revoca senza
    cancellare (audit). Confronto sull'hash via ``secrets.compare_digest``.
  * **un DB per tenant** — ``<data_dir>/tenants/<tenant_id>/memory.db``: lo
    sharding orizzontale naturale del design (fact 7ddba09db602). Il tenant
    deriva SOLO dalla chiave presentata, mai da un campo della richiesta —
    niente path traversal, niente confused deputy.
  * **stessa semantica dell'SDK** — ogni write passa il gate anti-confab, ogni
    read porta provenance; ``explain`` è il TrustReport via HTTP.
  * **niente LLM implicito** (O4): l'ingest conversazionale è disponibile solo
    se l'operatore costruisce l'app con un ``llm``; senza, 400 onesto.

Deploy: bind di default loopback; per l'esposizione remota l'operatore mette
il gateway dietro un reverse-proxy TLS (nginx/caddy) — il TLS non lo
reimplementiamo. Avvio: ``verimem gateway serve`` (CLI) o
``uvicorn engram.gateway:app_factory``.
"""
from __future__ import annotations

import re
import secrets
import sqlite3
import threading
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

try:  # fastapi è la stessa dipendenza opzionale della dashboard
    from fastapi import Depends, FastAPI, Header, HTTPException, Query
except ImportError as _exc:  # pragma: no cover — surfaced by the CLI command
    FastAPI = None  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR = _exc

_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

_KEYS_SCHEMA = """
CREATE TABLE IF NOT EXISTS gateway_keys (
    key_id     TEXT PRIMARY KEY,
    key_hash   TEXT NOT NULL UNIQUE,
    tenant_id  TEXT NOT NULL,
    name       TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    revoked_at REAL
);
"""


class GatewayKeys:
    """Store SQLite delle API key del gateway (hash-only at rest)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_KEYS_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _hash(api_key: str) -> str:
        return sha256(api_key.encode("utf-8")).hexdigest()

    def create(self, *, tenant_id: str, name: str = "") -> str:
        """Crea una chiave per ``tenant_id`` e la ritorna IN CHIARO — l'unica
        volta che esiste fuori dallo sha256. ``tenant_id`` è uno slug validato
        (finisce in un path di filesystem)."""
        if not _TENANT_RE.match(tenant_id or ""):
            raise ValueError(
                f"tenant_id non valido: {tenant_id!r} (slug [a-z0-9._-], max 64)")
        api_key = "vm_" + secrets.token_hex(20)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO gateway_keys "
                "(key_id, key_hash, tenant_id, name, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (secrets.token_hex(8), self._hash(api_key), tenant_id,
                 name, time.time()),
            )
            conn.commit()
        return api_key

    def resolve(self, api_key: str | None) -> str | None:
        """La chiave presentata → tenant_id, o None (mancante/ignota/revocata)."""
        if not api_key:
            return None
        presented = self._hash(api_key)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key_hash, tenant_id FROM gateway_keys "
                "WHERE revoked_at IS NULL",
            ).fetchall()
        for r in rows:
            if secrets.compare_digest(r["key_hash"], presented):
                return r["tenant_id"]
        return None

    def revoke(self, key_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE gateway_keys SET revoked_at = ? "
                "WHERE key_id = ? AND revoked_at IS NULL",
                (time.time(), key_id),
            )
            conn.commit()
        return cur.rowcount > 0

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key_id, tenant_id, name, created_at, revoked_at "
                "FROM gateway_keys ORDER BY created_at ASC",
            ).fetchall()
        return [dict(r) for r in rows]


class _TenantMemories:
    """Cache {tenant_id → Memory} con un DB isolato per tenant."""

    def __init__(self, data_dir: Path, llm: Any = None,
                 grounding_llm: Any = None) -> None:
        self._data_dir = data_dir
        self._llm = llm
        self._grounding_llm = grounding_llm
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, tenant_id: str):
        with self._lock:
            mem = self._cache.get(tenant_id)
            if mem is None:
                from .client import Memory
                db = self._data_dir / "tenants" / tenant_id / "memory.db"
                db.parent.mkdir(parents=True, exist_ok=True)
                mem = Memory(db, llm=self._llm,
                             grounding_llm=self._grounding_llm)
                self._cache[tenant_id] = mem
            return mem


def create_app(*, data_dir: str | Path, keys: GatewayKeys | None = None,
               llm: Any = None, grounding_llm: Any = None):
    """Costruisce l'app FastAPI del gateway. ``keys`` iniettabile (test);
    default: ``<data_dir>/gateway_keys.db``."""
    if FastAPI is None:  # pragma: no cover
        raise ImportError(
            "the gateway needs fastapi — pip install 'verimem[dashboard]'"
        ) from _FASTAPI_IMPORT_ERROR
    data_dir = Path(data_dir)
    keys = keys or GatewayKeys(data_dir / "gateway_keys.db")
    tenants = _TenantMemories(data_dir, llm=llm, grounding_llm=grounding_llm)
    app = FastAPI(title="Verimem gateway", docs_url=None, redoc_url=None)

    def _tenant(authorization: str | None = Header(default=None),
                x_api_key: str | None = Header(default=None)) -> str:
        presented = x_api_key
        if not presented and authorization and authorization.startswith("Bearer "):
            presented = authorization[len("Bearer "):]
        tenant_id = keys.resolve(presented)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="invalid or missing API key")
        return tenant_id

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        from . import __version__
        return {"ok": True, "version": __version__}

    @app.post("/v1/memories")
    def add_memory(body: dict, tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        mem = tenants.get(tenant_id)
        messages = body.get("messages")
        content = messages if messages is not None else (body.get("content") or "")
        if messages is not None and llm is None:
            raise HTTPException(
                status_code=400,
                detail="conversation ingest needs a server-side extraction llm: "
                       "start the gateway with one (create_app(llm=...)); "
                       "single verified facts work without it",
            )
        try:
            return mem.add(
                content,
                topic=body.get("topic", "user"),
                source=body.get("source"),
                verified_by=body.get("verified_by"),
                ground=bool(body.get("ground", False)),
                gate_mode=body.get("gate_mode"),
                asserted_at=body.get("asserted_at"),
                conversation_id=body.get("conversation_id"),
                user_name=body.get("user_name"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/v1/search")
    def search(q: str = Query(...), k: int = Query(default=5, ge=1, le=100),
               deep: bool = False, as_of: float | None = None,
               with_history: bool = False,
               tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        hits = tenants.get(tenant_id).search(
            q, k=k, deep=deep, as_of=as_of, with_history=with_history)
        return {"hits": hits}

    @app.get("/v1/explain")
    def explain(q: str = Query(...), k: int = Query(default=5, ge=1, le=100),
                as_of: float | None = None,
                tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        return tenants.get(tenant_id).explain(q, k=k, as_of=as_of)

    @app.get("/v1/memories/{fact_id}")
    def get_memory(fact_id: str, tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        item = tenants.get(tenant_id).get(fact_id)
        if item is None:
            raise HTTPException(status_code=404, detail="fact not found")
        return item

    @app.delete("/v1/memories/{fact_id}")
    def delete_memory(fact_id: str, purge_history: bool = False,
                      tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        removed = tenants.get(tenant_id).delete(
            fact_id, purge_history=purge_history)
        return {"removed": bool(removed)}

    return app


__all__ = ["GatewayKeys", "create_app"]
