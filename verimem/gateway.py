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
``uvicorn verimem.gateway:app_factory``.
"""
from __future__ import annotations

import functools
import re
import secrets
import sqlite3
import threading
import time
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from typing import Any

try:  # fastapi è la stessa dipendenza opzionale della dashboard
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
    from fastapi.responses import HTMLResponse, Response, StreamingResponse
except ImportError as _exc:  # pragma: no cover — surfaced by the CLI command
    FastAPI = None  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR = _exc

#: Host header values accepted by the personal (no-key) loopback mode —
#: anti DNS-rebinding: evil.example resolving to 127.0.0.1 does NOT match.
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})

#: Peer addresses accepted by the personal (no-key) loopback mode. The Host
#: header alone is CLIENT-CONTROLLED, so checking it was never authentication:
#: a deployment that binds non-loopback and sets local_tenant would hand the
#: local tenant to any remote caller that simply sent `Host: localhost`
#: (red-team audit F5). The peer address is set by the transport, not the
#: caller. "testclient" is Starlette's in-process ASGI caller — there is no
#: network peer at all there, so it cannot be a rebinding vector.
_LOCAL_PEERS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def _host_only(raw: str | None) -> str:
    """Strip the :port from a Host header, correctly for IPv6 (opus LOW-6:
    ``"[::1]".rsplit(":",1)[0]`` gave ``"[:"`` → the loopback IPv6 client fell to
    401). ``[::1]`` / ``[::1]:8080`` → ``[::1]``; ``127.0.0.1:8377`` → ``127.0.0.1``;
    a bare ``::1`` (no brackets, no port) → ``::1``."""
    s = (raw or "").strip()
    if s.startswith("["):
        return s[: s.index("]") + 1] if "]" in s else s
    if s.count(":") == 1:            # host:port (IPv4 / name) — one colon only
        return s.rsplit(":", 1)[0]
    return s                         # bare IPv6 (::1) or bare host — no port

_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}\Z")  # \Z not $ (critic LOW-5: $ lets a trailing \n through)

#: Windows reserved device names (lowercase — the slug is lowercase-only). A
#: tenant_id becomes a directory ``tenants/<id>/memory.db``; a dir named CON/AUX/
#: NUL/COM1…/LPT1… is reserved at ANY path level on Windows (the product's host),
#: so creation would fail. Reserved is the base name (before any extension):
#: ``con.db`` is reserved, ``console`` is not (AUDIT-LEDGER mod.4, 2026-07-16).
_WIN_RESERVED: frozenset[str] = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)

#: Trust dashboard: UNA pagina self-contained (no CDN, no template engine).
#: Statica per costruzione — nessun dato, nessuna chiave, nessun tenant id
#: viene mai interpolato qui dentro; il browser fetcha /v1/stats con la
#: bearer key che l'utente incolla (sessionStorage: muore con la tab).
_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verimem — Trust Dashboard</title>
<style>
  :root { color-scheme: light dark;
    --bg:#0e1116; --card:#161b22; --ink:#e6edf3; --dim:#8b949e;
    --ok:#3fb950; --warn:#d29922; --bad:#f85149; --info:#58a6ff; --line:#30363d; }
  @media (prefers-color-scheme: light) {
    :root { --bg:#f6f8fa; --card:#ffffff; --ink:#1f2328; --dim:#59636e;
            --line:#d1d9e0; } }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--bg); color:var(--ink); min-height:100vh;
         font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif; padding:2rem 1rem; }
  main { max-width:880px; margin:0 auto; }
  h1 { font-size:1.25rem; font-weight:600; }
  h1 small { color:var(--dim); font-weight:400; margin-left:.5rem; }
  .sub { color:var(--dim); margin:.25rem 0 1.5rem; font-size:.9rem; }
  form { display:flex; gap:.5rem; margin-bottom:1.5rem; flex-wrap:wrap; }
  input { flex:1; min-width:240px; background:var(--card); color:var(--ink);
          border:1px solid var(--line); border-radius:8px; padding:.55rem .8rem; }
  button { background:var(--info); color:#fff; border:0; border-radius:8px;
           padding:.55rem 1.1rem; cursor:pointer; font-weight:600; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
          gap:.75rem; margin-bottom:.75rem; }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:1rem 1.1rem; }
  .card .n { font-size:2.1rem; font-weight:700; font-variant-numeric:tabular-nums; }
  .card .l { color:var(--dim); font-size:.82rem; margin-top:.15rem; }
  .admitted .n { color:var(--ok); } .quarantined .n { color:var(--warn); }
  .rejected .n { color:var(--bad); } .abstained .n { color:var(--info); }
  .wide { margin-bottom:.75rem; }
  .wide h2 { font-size:.85rem; color:var(--dim); text-transform:uppercase;
             letter-spacing:.06em; margin-bottom:.5rem; }
  .row { display:flex; justify-content:space-between; padding:.3rem 0;
         border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }
  .row:last-child { border-bottom:0; }
  .muted { color:var(--dim); }
  #err { color:var(--bad); margin-bottom:1rem; display:none; }
  footer { color:var(--dim); font-size:.8rem; margin-top:1.5rem; }
</style>
</head>
<body>
<main>
  <h1>Trust odometer <small>Verimem gateway</small></h1>
  <p class="sub">What the admission gate actually did on your store —
    observable actions, counted live. Your API key stays in this tab
    (sessionStorage) and is sent only as an Authorization header.</p>
  <form id="f">
    <input id="k" type="password" placeholder="paste your API key (vm_ prefix)"
           autocomplete="off">
    <button type="submit">Load my stats</button>
  </form>
  <p id="err"></p>
  <div id="board" style="display:none">
    <div class="grid">
      <div class="card admitted"><div class="n" id="n-admitted">0</div>
        <div class="l">writes admitted</div></div>
      <div class="card quarantined"><div class="n" id="n-quarantined">0</div>
        <div class="l">unsupported claims quarantined</div></div>
      <div class="card rejected"><div class="n" id="n-rejected">0</div>
        <div class="l">writes rejected (not stored)</div></div>
      <div class="card abstained"><div class="n" id="n-abstained">0</div>
        <div class="l">honest &ldquo;I don't know&rdquo; (explain events)</div></div>
    </div>
    <div class="card wide"><h2>Gate layers that fired</h2><div id="layers"></div></div>
    <div class="card wide"><h2>Live facts by status</h2><div id="store"></div></div>
    <div class="card wide"><h2>Usage</h2><div id="usage"></div></div>
    <footer id="meta"></footer>
  </div>
</main>
<script>
(function () {
  var STORE = 'verimem_bearer';
  var f = document.getElementById('f'), inp = document.getElementById('k');
  var err = document.getElementById('err'), board = document.getElementById('board');
  function rows(el, obj, empty) {
    var keys = Object.keys(obj || {}).sort();
    if (!keys.length) { el.innerHTML = '<div class="row muted">' + empty + '</div>'; return; }
    el.innerHTML = keys.map(function (name) {
      return '<div class="row"><span>' + name + '</span><span>' + obj[name] + '</span></div>';
    }).join('');
  }
  function render(d) {
    board.style.display = 'block'; err.style.display = 'none';
    var led = (d.trust || {}).ledger || {};
    ['admitted', 'quarantined', 'rejected', 'abstained'].forEach(function (a) {
      document.getElementById('n-' + a).textContent = led[a] || 0;
    });
    rows(document.getElementById('layers'), (d.trust || {}).by_layer,
         'no gate layer has fired yet');
    rows(document.getElementById('store'), (d.trust || {}).store, 'empty store');
    rows(document.getElementById('usage'), d.usage, 'no usage recorded yet');
    document.getElementById('meta').textContent =
      'tenant: ' + d.tenant + ' - refreshed ' + new Date().toLocaleTimeString() +
      ' - auto-refresh 30s';
  }
  function load() {
    var tok = sessionStorage.getItem(STORE);
    if (!tok) return;
    fetch('/v1/stats', { headers: { 'Authorization': 'Bearer ' + tok } })
      .then(function (r) {
        if (r.status === 401) { sessionStorage.removeItem(STORE);
          throw new Error('invalid key - paste it again'); }
        if (!r.ok) throw new Error('gateway error ' + r.status);
        return r.json();
      })
      .then(render)
      .catch(function (e) {
        board.style.display = 'none';
        err.textContent = e.message; err.style.display = 'block';
      });
  }
  f.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var v = inp.value.trim();
    if (v) { sessionStorage.setItem(STORE, v); inp.value = ''; load(); }
  });
  setInterval(load, 30000);
  load();
})();
</script>
</body>
</html>
"""

_KEYS_SCHEMA = """
CREATE TABLE IF NOT EXISTS gateway_keys (
    key_id     TEXT PRIMARY KEY,
    key_hash   TEXT NOT NULL UNIQUE,
    tenant_id  TEXT NOT NULL,
    name       TEXT NOT NULL DEFAULT '',
    plan       TEXT NOT NULL DEFAULT 'free',
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
            try:   # migration: older key DBs predate the plan column
                conn.execute("ALTER TABLE gateway_keys "
                             "ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
                conn.commit()
            except sqlite3.OperationalError:
                pass   # column already present

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _hash(api_key: str) -> str:
        return sha256(api_key.encode("utf-8")).hexdigest()

    def create(self, *, tenant_id: str, name: str = "", plan: str = "free") -> str:
        """Crea una chiave per ``tenant_id`` e la ritorna IN CHIARO — l'unica
        volta che esiste fuori dallo sha256. ``tenant_id`` è uno slug validato
        (finisce in un path di filesystem). ``plan`` = il tier commerciale
        (free/pro/enterprise/self_host); normalizzato al minimo-privilegio se ignoto."""
        if not _TENANT_RE.match(tenant_id or ""):
            raise ValueError(
                f"tenant_id non valido: {tenant_id!r} (slug [a-z0-9._-], max 64)")
        # critic HIGH-1 (2026-07-16): Windows strips TRAILING dots/spaces from
        # directory names, so `acme.` and `acme` map to the SAME
        # `tenants/<id>/memory.db` → two distinct tenant_ids share one physical
        # DB = broken isolation. Reject a trailing dot (the regex already blocks
        # trailing space). An INTERIOR dot ("a.b") is untouched by Windows → ok.
        if tenant_id.endswith("."):
            raise ValueError(
                f"tenant_id {tenant_id!r} must not end with '.' — Windows strips "
                "trailing dots, collapsing it onto another tenant's directory")
        if tenant_id.split(".", 1)[0] in _WIN_RESERVED:
            raise ValueError(
                f"tenant_id {tenant_id!r} is a reserved device name on Windows "
                "(con/aux/nul/com1-9/lpt1-9) — the per-tenant directory can't be created")
        from .gateway_plans import get_plan
        plan_name = get_plan(plan).name
        api_key = "vm_" + secrets.token_hex(20)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO gateway_keys "
                "(key_id, key_hash, tenant_id, name, plan, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(8), self._hash(api_key), tenant_id,
                 name, plan_name, time.time()),
            )
            conn.commit()
        return api_key

    def plan_for_tenant(self, tenant_id: str) -> str:
        """The tenant's subscription tier — the plan on its most recent live key,
        else ``free`` (a tenant is one customer on one plan)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT plan FROM gateway_keys WHERE tenant_id = ? "
                "AND revoked_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (tenant_id,)).fetchone()
        return row["plan"] if row else "free"

    def resolve(self, api_key: str | None) -> str | None:
        """La chiave presentata → tenant_id, o None (mancante/ignota/revocata).

        Lookup sull'indice UNIQUE di ``key_hash`` (O(log n)) invece del
        fetchall+loop O(n·chiavi) pre-2026-07-15. Il confronto avviene solo
        tra sha256 (mai plaintext): il timing del btree sull'hash non dà
        segnale utile a chi non conosce già gli hash a riposo, e l'hash non
        è invertibile — il ``compare_digest`` per-riga proteggeva un canale
        che qui non esiste."""
        if not api_key:
            return None
        presented = self._hash(api_key)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT tenant_id FROM gateway_keys "
                "WHERE key_hash = ? AND revoked_at IS NULL",
                (presented,),
            ).fetchone()
        return row["tenant_id"] if row else None

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
                "SELECT key_id, tenant_id, name, plan, created_at, revoked_at "
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


class _Metering:
    """Contatori d'uso per tenant, persistiti accanto alle chiavi.

    Il ponte 'software → servizio': senza contatori non si fattura e non si
    vedono gli abusi. UPSERT per giorno/tenant (single-node, Fase 1); include
    le trust-metrics che nessun competitor espone: scritture ammesse vs
    rifiutate dal gate."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS gateway_usage (
        tenant_id TEXT NOT NULL,
        day       TEXT NOT NULL,
        requests  INTEGER NOT NULL DEFAULT 0,
        reads     INTEGER NOT NULL DEFAULT 0,
        writes    INTEGER NOT NULL DEFAULT 0,
        stored_ok INTEGER NOT NULL DEFAULT 0,
        rejected  INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (tenant_id, day)
    );
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.executescript(self._SCHEMA)

    def bump(self, tenant_id: str, *, reads: int = 0, writes: int = 0,
             stored_ok: int = 0, rejected: int = 0) -> None:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute(
                    "INSERT INTO gateway_usage "
                    "(tenant_id, day, requests, reads, writes, stored_ok, rejected) "
                    "VALUES (?, ?, 1, ?, ?, ?, ?) "
                    "ON CONFLICT(tenant_id, day) DO UPDATE SET "
                    "requests = requests + 1, reads = reads + excluded.reads, "
                    "writes = writes + excluded.writes, "
                    "stored_ok = stored_ok + excluded.stored_ok, "
                    "rejected = rejected + excluded.rejected",
                    (tenant_id, day, reads, writes, stored_ok, rejected))
                conn.commit()
        except sqlite3.Error:  # noqa: PERF203 — metering must never break serving
            pass

    def totals(self) -> dict[str, dict[str, int]]:
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT tenant_id, SUM(requests) requests, SUM(reads) reads, "
                "SUM(writes) writes, SUM(stored_ok) stored_ok, "
                "SUM(rejected) rejected FROM gateway_usage GROUP BY tenant_id",
            ).fetchall()
        return {r["tenant_id"]: {k: int(r[k] or 0) for k in
                                 ("requests", "reads", "writes",
                                  "stored_ok", "rejected")}
                for r in rows}

    def usage_for(self, tenant_id: str, *,
                  since_day: str | None = None) -> list[dict[str, Any]]:
        """Per-DAY usage for one tenant since ``since_day`` (YYYY-MM-DD inclusive) —
        the billing-period line items a monthly invoice sums. Empty list if none."""
        sql = ("SELECT day, requests, reads, writes, stored_ok, rejected "
               "FROM gateway_usage WHERE tenant_id = ?")
        params: list[Any] = [tenant_id]
        if since_day:
            sql += " AND day >= ?"
            params.append(since_day)
        sql += " ORDER BY day ASC"
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error:
            return []
        return [dict(r) for r in rows]


def _gateway_min_relevance() -> float | str:
    """The gateway's default read-path abstention floor. ``ENGRAM_GATEWAY_MIN_RELEVANCE``:
    ``auto`` (default — the store self-calibrates per tenant), a float (fixed floor), or
    ``off``/``0`` (no floor, the old permissive behaviour). Making the enterprise API
    abstain by default is the point of a TRUST product; it stays a tunable dial because
    the e5 score band is compressed."""
    import os
    raw = os.environ.get("ENGRAM_GATEWAY_MIN_RELEVANCE", "auto").strip().lower()
    if raw in ("off", "none", ""):
        return 0.0
    if raw == "auto":
        return "auto"
    try:
        return max(0.0, float(raw))
    except ValueError:
        return "auto"


def _flow_ctx(tenant_id: str):
    """Flow-context per la LIVE Engine Room: da quando l'emissione vive nel
    CORE (``verimem.flow_events``, chiamata da ``Memory.add/search/explain``),
    il gateway non emette più direttamente — arricchisce il contesto con
    ``tenant`` (il filtro privacy di ``/v1/events/flow``) e ``surface``.
    Ritorna il token da passare a ``_flow_ctx_reset`` in un ``finally``."""
    from .flow_events import set_flow_context
    return set_flow_context(tenant=tenant_id, surface="gateway")


def _flow_ctx_reset(token: Any) -> None:
    try:
        from .flow_events import reset_flow_context
        reset_flow_context(token)
    except Exception:  # noqa: BLE001 — mai nel percorso d'errore del handler
        pass


#: Max flow lines processed per SSE tick — anti-burst bound so a huge append
#: (or the first read after a long idle) can't block the event loop.
_FLOW_MAX_LINES_PER_TICK = 1000


def _parse_flow_line(ln: str, tenant_id: str, see_untenanted: bool) -> dict[str, Any] | None:
    """Parse one events.jsonl line and keep it only if it's a ``flow.*`` event
    for THIS tenant (privacy). ``see_untenanted`` lets personal-mode (the local
    operator) also see tenant-less machine activity. Returns None to drop."""
    import json as _json
    try:
        rec = _json.loads(ln)
    except ValueError:
        return None
    if not str(rec.get("name", "")).startswith("flow."):
        return None
    _pt = (rec.get("payload") or {}).get("tenant")
    if _pt != tenant_id and not (see_untenanted and _pt is None):
        return None
    return rec


def _read_flow_bytes(path: Path, offset: int, tenant_id: str,
                     see_untenanted: bool, cap: int) -> tuple[list[dict[str, Any]], int]:
    """Incremental byte-offset reader for the flow SSE stream. Reads ONLY the
    bytes appended since ``offset`` (never the whole file), so N concurrent
    clients cost O(new bytes) per tick, not O(file). Returns
    ``(flow_records_for_tenant, new_offset)``.

    Contract (pinned by ``test_gateway_flow_incremental``):
    * rotation/truncation (``size < offset``) → restart from 0;
    * a trailing partial line (no final ``\\n``) is NOT consumed — held for the
      next tick, so a write-in-progress is never emitted or skipped;
    * ``cap`` (0 = unbounded) bounds lines consumed per tick; the offset advances
      only over what was consumed, so the remainder resumes next tick — no loss.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return [], offset
    if size < offset:          # rotated / truncated under us
        offset = 0
    if size <= offset:
        return [], offset
    try:
        with path.open("rb") as f:
            f.seek(offset)
            raw = f.read()
    except OSError:
        return [], offset
    nl = raw.rfind(b"\n")
    if nl == -1:               # no complete line yet (partial write) — consume nothing
        return [], offset
    complete = raw[: nl + 1]
    lines = [b for b in complete.split(b"\n") if b]
    if cap and len(lines) > cap:
        lines = lines[:cap]
        consumed = sum(len(b) + 1 for b in lines)   # +1 per '\n'
    else:
        consumed = nl + 1
    out: list[dict[str, Any]] = []
    for lb in lines:
        rec = _parse_flow_line(lb.decode("utf-8", errors="replace"),
                               tenant_id, see_untenanted)
        if rec is not None:
            out.append(rec)
    return out, offset + consumed


def _quota_reserve(pending: dict[str, int], lock: Any, tenant_id: str,
                   plan: Any, count_fn: Any) -> bool:
    """Atomically reserve one fact slot against the plan's cap. TOCTOU-safe:
    the real count (``count_fn()``) and the in-flight reservations (``pending``)
    are read together UNDER ``lock``, so a write already in flight counts against
    the cap — concurrent writes at cap-1 can't ALL pass. Returns True (reserved,
    caller MUST ``_quota_release`` in a finally) or False (over quota → 402).
    Uncapped plans (enterprise/self_host) short-circuit True with no state."""
    if getattr(plan, "max_facts", None) is None:
        return True
    with lock:
        p = pending.get(tenant_id, 0)
        if not plan.within_facts(count_fn() + p):
            return False
        pending[tenant_id] = p + 1
        return True


def _quota_release(pending: dict[str, int], lock: Any, tenant_id: str,
                   plan: Any) -> None:
    """Release a slot reserved by ``_quota_reserve`` (call in a finally). Once the
    write has landed it's in the real count, so the reservation must drop whether
    the add succeeded, quarantined, or raised. No-op for uncapped plans."""
    if getattr(plan, "max_facts", None) is None:
        return
    with lock:
        p = pending.get(tenant_id, 0) - 1
        if p <= 0:
            pending.pop(tenant_id, None)
        else:
            pending[tenant_id] = p


def _shadow_observe(tenant_id: str, surface: str, hits: list[dict[str, Any]] | None,
                    actual: dict[str, Any], *, mem: Any = None,
                    q: str | None = None) -> None:
    """Phase-1 SHADOW hook (REMORSE graft, handoff 2026-07-16): feed the
    per-tenant AdaptiveLedger with recall exposure and LOG its would-be
    decision next to the gateway's ACTUAL one — never touching the response
    (the 13/7 dead-gates lesson inverted: observe on real traffic first,
    apply in phase 2 behind a per-tenant flag). Kill-switch
    ``ENGRAM_SHADOW_LEDGER=0``. Everything is best-effort: a broken shadow
    must never break a request. For the answer surface (which retrieves
    internally) a small shadow-only search supplies the topics — a phase-1
    cost that disappears when phase 2 threads topics through ``answer()``."""
    import os
    import time as _time
    if os.environ.get("ENGRAM_SHADOW_LEDGER", "1").strip().lower() in (
            "0", "off", "false", "no"):
        return
    try:
        from . import event_jsonl_log as _ejl
        from .adaptive_ledger import get_shadow
        now = _time.time()
        if hits is None and mem is not None and q:
            hits = mem.search(q, k=4)
        topics = [str(h.get("topic") or "untopiced") for h in (hits or [])]
        shadow = get_shadow()
        shadow.observe_recall(tenant_id, topics, now=now)
        dominant = (max(dict.fromkeys(topics), key=topics.count)
                    if topics else "none")
        dec = shadow.decision(tenant_id, dominant, now=now)
        _ejl.append_event("shadow.ledger",
                          {"surface": surface, **dec, "actual": actual})
    except Exception:  # noqa: BLE001 — shadow-only, swallow everything
        pass


def _replay_receive(body: bytes, original: Any) -> Any:
    """Un ASGI ``receive`` che emette UNA volta il corpo bufferizzato come un
    unico ``http.request`` completo, poi delega all'originale (disconnect ecc.)."""
    sent = False

    async def receive() -> Any:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await original()

    return receive


def _prepend_message(first: Any, original: Any) -> Any:
    """``receive`` che ri-emette un messaggio gia' consumato, poi delega."""
    sent = False

    async def receive() -> Any:
        nonlocal sent
        if not sent:
            sent = True
            return first
        return await original()

    return receive


class _BodyLimitMiddleware:
    """ASGI middleware anti-DoS sul data plane.

    Il guard precedente (``@app.middleware("http")``) si fidava del SOLO header
    ``Content-Length``: una richiesta ``Transfer-Encoding: chunked`` senza quel
    header saltava il tetto e veniva processata (security audit G1, 2026-07-11 —
    PoC: body 5KB su cap 1KB passava a 200 e veniva scritto). Qui misuriamo i
    BYTE REALI: dreniamo il corpo con un tetto duro e, se supera il cap,
    rispondiamo 413 SENZA far girare l'app; se sta sotto, lo ri-iniettiamo
    intatto a valle. Il chunked sotto il cap passa (contiamo, non vietiamo)."""

    def __init__(self, app: Any, *, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or self.max_body_bytes <= 0:
            await self.app(scope, receive, send)
            return
        # fast-path: un Content-Length onesto e oltre-cap si rifiuta subito,
        # senza nemmeno leggere il corpo.
        for name, value in scope.get("headers") or ():
            if (name == b"content-length" and value.isdigit()
                    and int(value) > self.max_body_bytes):
                await self._reject(send)
                return
        # drena il corpo bufferizzando fino a cap+1 byte; oltre = 413. Il buffer
        # e' limitato dal cap stesso (<=1MB di default): costo trascurabile.
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") != "http.request":
                # es. http.disconnect prima del corpo: ri-emetti e delega.
                await self.app(scope, _prepend_message(message, receive), send)
                return
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
            if len(body) > self.max_body_bytes:
                await self._reject(send)
                return
        # sotto il cap: ri-inietta il corpo consolidato, poi delega.
        await self.app(scope, _replay_receive(body, receive), send)

    async def _reject(self, send: Any) -> None:
        import json as _json
        body = _json.dumps(
            {"detail": f"body too large (max {self.max_body_bytes} bytes)"}
        ).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


#: Defensive headers stamped on every gateway response. Purely ADDITIVE (a route
#: that sets its own value wins). ``nosniff`` is safe because the UI assets are
#: served with correct MIME types. HSTS is deliberately ABSENT: it belongs at the
#: TLS-terminating proxy (verimem.com already sends a 2-year preload HSTS), and
#: asserting it from a possibly-plain-HTTP local bind is a footgun. The CSP is set
#: separately, by content type (see below).
_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"permissions-policy",
     b"geolocation=(), camera=(), microphone=(), browsing-topics=()"),
)

#: CSP for API/JSON/error responses: anti-clickjacking that does NOT constrain
#: resource loading.
_BASE_CSP = b"frame-ancestors 'none'"

#: CSP for the served HTML console. The pages load ONLY same-origin external
#: assets (``/ui/app.js`` + ``/ui/style.css``) with NO inline <script>, no inline
#: event handlers, no ``style=`` attributes, no eval/new Function, and fetch/SSE
#: only to same-origin ``/v1/*`` — so a locked-down policy is non-breaking AND it
#: neutralizes stored-XSS as defense-in-depth: even if a poisoned fact's text ever
#: slipped past the console's esc(), ``script-src 'self'`` forbids the injected
#: inline script from executing. ``img-src`` allows data: for favicons.
#: ``worker-src 'self' blob:`` exists for exactly one consumer: the console
#: graph's ForceAtlas2 layout runs in a Web Worker that graphology-library
#: spawns from a Blob of its OWN (vendored, same-origin) code. blob: cannot
#: load remote script — only code already admitted by ``script-src 'self'``
#: can mint such a worker, so the no-CDN/no-inline posture is unchanged.
_HTML_CSP = (
    b"default-src 'none'; script-src 'self'; style-src 'self'; "
    b"img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    b"worker-src 'self' blob:; "
    b"base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class _SecurityHeadersMiddleware:
    """ASGI middleware: stamp defensive security headers on EVERY response —
    success, error, streamed, or the 413 short-circuited by the body-limit
    guard. Additive only: a header the app already set is never overwritten, so
    a route may still opt into a stricter value. The CSP is chosen by content
    type: a locked-down policy for the HTML console, ``frame-ancestors`` for
    API/JSON. Wired OUTERMOST so it also covers responses that never reach the
    route handlers."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Any) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers") or ())
                present = {h[0].lower() for h in headers}
                headers.extend((name, value) for name, value in _SECURITY_HEADERS
                               if name not in present)
                if b"content-security-policy" not in present:
                    ctype = next((v for n, v in headers
                                  if n.lower() == b"content-type"), b"")
                    csp = (_HTML_CSP if ctype.lower().startswith(b"text/html")
                           else _BASE_CSP)
                    headers.append((b"content-security-policy", csp))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_app(*, data_dir: str | Path, keys: GatewayKeys | None = None,
               llm: Any = None, grounding_llm: Any = None,
               rate_limit_per_minute: int = 0,
               admin_key: str | None = None,
               max_body_bytes: int = 1_048_576,
               audit_log: bool | None = None,
               local_tenant: str | None = None,
               local_memory: Any = None):
    """Costruisce l'app FastAPI del gateway. ``keys`` iniettabile (test);
    default: ``<data_dir>/gateway_keys.db``.

    ``rate_limit_per_minute`` (0 = off, default): tetto per CHIAVE su una
    finestra scorrevole di 60s — oltre, 429 con ``Retry-After``. In-memory
    per processo (Fase 1 del design datacenter: single-node; il limite
    distribuito è Fase 2+). Ogni chiave ha il suo bucket: il consumo di un
    tenant non tocca gli altri. ``/v1/health`` non è mai limitato (liveness).

    ``admin_key`` (None = default): SENZA, gli endpoint ``/admin/*`` non
    esistono — un gateway senza control plane è byte-identico a prima. CON,
    il control plane HTTP si accende: provisioning tenant remoto
    (``POST /admin/tenants``) e stats con metering per tenant
    (``GET /admin/stats``) — il ponte per offrire il servizio online senza
    SSH sull'host. La admin key non è mai una chiave tenant.

    ``max_body_bytes`` (1 MB default): 413 oltre il limite — anti-DoS sul
    data plane.

    ``local_tenant`` + ``local_memory`` (None = default): la MODALITÀ
    PERSONALE di ``verimem console`` — le richieste SENZA chiave risolvono a
    questo tenant, montato sul suo store ESISTENTE (l'utente singolo vede la
    propria memoria senza gateway/chiavi/config). Modello di fiducia
    "jupyter locale": il chiamante deve bindare SOLO loopback; qui in più
    l'header Host deve essere localhost (anti DNS-rebinding) e una chiave
    PRESENTATA vince sempre (o fallisce forte: chiave invalida = 401, mai
    fallback silenzioso). Senza ``local_tenant`` il gateway è byte-identico
    a prima."""
    # A gateway IS the multi-writer context: N agent sessions can share one
    # tenant key, so the write-gate running inside this process must not
    # assume a single agent owns the store (Kimi audit F2 - it makes
    # same-source supersession default OFF here). setdefault: an explicit
    # operator setting always wins.
    import os as _os
    _os.environ.setdefault("VERIMEM_MULTI_WRITER", "1")
    if FastAPI is None:  # pragma: no cover
        raise ImportError(
            "the gateway needs fastapi — pip install 'verimem[server]'"
        ) from _FASTAPI_IMPORT_ERROR
    data_dir = Path(data_dir)
    keys = keys or GatewayKeys(data_dir / "gateway_keys.db")
    tenants = _TenantMemories(data_dir, llm=llm, grounding_llm=grounding_llm)
    if local_tenant and local_memory is not None:
        # personal mode: the local tenant is served by the user's OWN store,
        # never by a fresh tenants/<id>/memory.db
        tenants._cache[local_tenant] = local_memory
    meter = _Metering(keys.db_path)
    _started_at = time.time()
    app = FastAPI(title="Verimem gateway", docs_url=None, redoc_url=None)

    # Hardening (red-team R1 2026-07-17): FastAPI's DEFAULT RequestValidationError
    # handler serializes exc.errors() with jsonable_encoder, which decodes any
    # raw-bytes `input` (the malformed body it echoes back) as strict utf-8. A
    # typeless POST with a non-utf8 byte (e.g. b"\xff") therefore raised
    # UnicodeDecodeError INSIDE the error handler → 500: an authenticated tenant
    # could crash any write/validation endpoint with a 2-byte payload. Re-encode
    # bytes with errors="replace" so malformed input is always a clean 422.
    from fastapi.encoders import jsonable_encoder as _jsonable_encoder
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse as _JSONResponse

    @app.exception_handler(RequestValidationError)
    async def _bytes_safe_validation_handler(request: Request,
                                             exc: RequestValidationError):
        detail = _jsonable_encoder(
            exc.errors(),
            custom_encoder={bytes: lambda b: b.decode("utf-8", "replace")})
        return _JSONResponse(status_code=422, content={"detail": detail})

    # anti-DoS sul data plane: conta i byte REALI (non solo Content-Length —
    # un chunked senza header saltava il cap, security audit G1 2026-07-11).
    app.add_middleware(_BodyLimitMiddleware, max_body_bytes=max_body_bytes)
    # security headers su OGNI risposta (aggiunto DOPO il body-limit → è il piu'
    # esterno, quindi timbra anche il 413 di quel guard). Additivo, non rompe /ui.
    app.add_middleware(_SecurityHeadersMiddleware)
    # access-audit JSONL (compliance enterprise): OUTERMOST → cattura lo status
    # finale di ogni risposta, anche 401/413. Default ON (un servizio di memoria
    # audita); kill-switch ENGRAM_GATEWAY_AUDIT_LOG=0 o audit_log=False.
    from .gateway_audit import AccessAuditMiddleware, JsonlAuditSink, audit_enabled
    # default ON for a real multi-tenant gateway, OFF for the personal console
    # (local_tenant): an access log is a SERVER control, not a single-user surprise.
    _audit = (audit_enabled(default=local_tenant is None) if audit_log is None
              else bool(audit_log))
    if _audit:
        app.add_middleware(AccessAuditMiddleware,
                           sink=JsonlAuditSink(data_dir / "audit"))

    _buckets: dict[str, list[float]] = {}
    _buckets_lock = threading.Lock()

    # per-tenant in-flight fact reservations (TOCTOU-safe quota enforcement):
    # a write in flight counts against the cap until it lands. Per-app state.
    _quota_pending: dict[str, int] = {}
    _quota_lock = threading.Lock()

    def _check_rate(bucket_key: str, limit: int) -> None:
        if limit <= 0:
            return
        now = time.time()
        with _buckets_lock:
            window = [t for t in _buckets.get(bucket_key, ()) if now - t < 60.0]
            if len(window) >= limit:
                retry = max(1, int(61.0 - (now - window[0])))
                _buckets[bucket_key] = window
                raise HTTPException(
                    status_code=429, detail="rate limit exceeded for this key",
                    headers={"Retry-After": str(retry)})
            window.append(now)
            _buckets[bucket_key] = window

    def _plan_for(tenant_id: str):
        """The tenant's effective plan. Personal mode is the OPERATOR on their
        own machine: plan quotas exist to protect the SaaS, not to cap the
        owner — found live 2026-07-16 (console on a 4499-fact store → every
        write 402'd against the free cap). Local tenant ⇒ uncapped self_host."""
        from .gateway_plans import get_plan
        if local_tenant is not None and tenant_id == local_tenant:
            return get_plan("self_host")
        return get_plan(keys.plan_for_tenant(tenant_id))

    def _tenant(request: Request,
                authorization: str | None = Header(default=None),
                x_api_key: str | None = Header(default=None)) -> str:
        presented = x_api_key
        if not presented and authorization and authorization.startswith("Bearer "):
            presented = authorization[len("Bearer "):]
        if not presented and local_tenant:
            # personal mode: NO key presented at all → the local tenant,
            # ma solo con Host localhost (anti DNS-rebinding). Una chiave
            # presentata e invalida NON cade qui: 401 forte sotto.
            host = _host_only(request.headers.get("host"))
            # BOTH must be loopback: the Host header (anti DNS-rebinding, and
            # client-controlled) AND the actual peer (transport-set, audit F5).
            peer = (getattr(getattr(request, "client", None), "host", "") or "").lower()
            if host.lower() in _LOCAL_HOSTS and peer in _LOCAL_PEERS:
                request.state.tenant = local_tenant   # for the access-audit log
                return local_tenant
        tenant_id = keys.resolve(presented)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="invalid or missing API key")
        request.state.tenant = tenant_id              # for the access-audit log
        # il bucket segue la CHIAVE presentata (hash), non il tenant: due
        # chiavi dello stesso tenant hanno tetti indipendenti e revocabili.
        # Tetto effettivo = il più RESTRITTIVO fra il piano (free 60/min, pro 600,
        # enterprise illimitato) e il parametro globale di create_app (0 = off).
        from .gateway_plans import get_plan
        _pl = get_plan(keys.plan_for_tenant(tenant_id)).rate_limit_per_minute
        _active = [x for x in (_pl, rate_limit_per_minute or None) if x is not None]
        _check_rate(GatewayKeys._hash(presented or ""), min(_active) if _active else 0)
        return tenant_id

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        from . import __version__
        return {"ok": True, "version": __version__}

    @app.get("/v1/quota")
    def quota(tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """The tenant's plan, usage and headroom — what a dashboard shows and what a
        402 (over quota) cites. The SaaS's self-service window into its own limits."""
        from .gateway_plans import quota_status
        plan = _plan_for(tenant_id)
        return quota_status(plan, facts_used=tenants.get(tenant_id).semantic.count())

    @app.get("/v1/usage")
    def usage(since: str | None = Query(default=None),
              tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """The tenant's own metered usage: per-day line items + the period total —
        the self-serve billing view, and the numbers a monthly invoice sums. ``since``
        (YYYY-MM-DD) bounds the billing period; omit for all time."""
        days = meter.usage_for(tenant_id, since_day=since)
        cols = ("requests", "reads", "writes", "stored_ok", "rejected")
        total = {c: sum(int(d.get(c, 0)) for d in days) for c in cols}
        return {"tenant_id": tenant_id,
                "plan": _plan_for(tenant_id).name,
                "since": since, "days": days, "total": total}

    # Write idempotency (live e2e 2026-07-20): a client timeout on a SLOW first
    # write (cold model load) left the write COMPLETING server-side; the retry
    # then stored a twin. Standard fix: the client sends an Idempotency-Key and
    # a replay within the TTL returns the ORIGINAL receipt without re-executing.
    # In-memory per-process cache (tenant, key) -> receipt; 10-min TTL, pruned
    # inline. Honest scope: per-process only - a server restart mid-retry
    # degrades to today's behavior (a twin), never to a lost write.
    # Hardened after an independent red-team audit (F6): the original
    # check->execute->store was three unsynchronized steps, so two retries of
    # the SAME key arriving together both missed the cache and both executed -
    # reproducing the twin write this feature exists to prevent. And pruning
    # was TTL-only, so a flood of UNIQUE keys grew the process for the whole
    # window (rate limiting is off by default) = a cheap memory DoS.
    _idem_cache: OrderedDict[tuple[str, str], tuple[float, dict]] = OrderedDict()
    _idem_lock = threading.Lock()          # guards _idem_cache AND _idem_inflight
    _idem_inflight: dict[tuple[str, str], threading.Lock] = {}
    _IDEM_TTL_S = 600.0
    try:
        _IDEM_MAX = max(1, int(_os.environ.get("VERIMEM_IDEM_MAX", "10000")))
    except ValueError:
        _IDEM_MAX = 10000

    def _idem_entry_lock(tenant_id: str, key: str) -> threading.Lock:
        """One lock per (tenant, key). The caller holds it across the whole
        check->execute->store window, so a concurrent retry WAITS and then
        replays the receipt instead of executing a twin."""
        k = (tenant_id, key)
        with _idem_lock:
            lk = _idem_inflight.get(k)
            if lk is None:
                lk = _idem_inflight[k] = threading.Lock()
            return lk

    def _idem_release(tenant_id: str, key: str, lk: threading.Lock) -> None:
        lk.release()
        with _idem_lock:
            if not lk.locked():            # nobody waiting -> drop the entry
                _idem_inflight.pop((tenant_id, key), None)

    def _idem_get(tenant_id: str, key: str | None) -> dict | None:
        if not key:
            return None
        now = time.time()
        with _idem_lock:
            # insertion-ordered by time: stop at the first still-fresh entry
            while _idem_cache:
                _k, (_ts, _r) = next(iter(_idem_cache.items()))
                if now - _ts > _IDEM_TTL_S:
                    _idem_cache.pop(_k, None)
                else:
                    break
            hit = _idem_cache.get((tenant_id, key))
            return dict(hit[1]) if hit else None

    def _idem_put(tenant_id: str, key: str | None, receipt: dict) -> None:
        if not key:
            return
        with _idem_lock:
            _idem_cache[(tenant_id, key)] = (time.time(), dict(receipt))
            # bounded: a unique-key flood evicts the oldest, never grows
            while len(_idem_cache) > _IDEM_MAX:
                _idem_cache.popitem(last=False)

    app.state.idem_cache = _idem_cache     # introspectable (bounded-growth test)

    @app.post("/v1/memories")
    def add_memory(body: dict, tenant_id: str = Depends(_tenant),
                   idempotency_key: str | None = Header(
                       default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        # ONE lock across check->execute->store for a given key: a simultaneous
        # retry blocks here and then replays the original receipt, instead of
        # racing through the gap and storing a twin (audit F6). No key -> the
        # unchanged path (nothing to de-duplicate against).
        if not idempotency_key:
            return _add_memory_impl(body, tenant_id, None)
        _lk = _idem_entry_lock(tenant_id, idempotency_key)
        _lk.acquire()
        try:
            _replay = _idem_get(tenant_id, idempotency_key)
            if _replay is not None:
                return _replay
            return _add_memory_impl(body, tenant_id, idempotency_key)
        finally:
            _idem_release(tenant_id, idempotency_key, _lk)

    def _add_memory_impl(body: dict, tenant_id: str,
                         idempotency_key: str | None) -> dict[str, Any]:
        mem = tenants.get(tenant_id)
        # input validation at the edge: a malformed type is a client error (400), never
        # a 500 — an unhandled 500 on crafted input is a crashable endpoint = a DoS.
        _msgs, _content = body.get("messages"), body.get("content")
        _bad = None
        # Silent-drop guard (vertical probe 2026-07-18): a body carrying NEITHER
        # 'content' NOR 'messages' would fall through to content="" and return
        # 200 {stored:false, status:"empty"} — from the caller's side a 2xx that
        # silently loses the write (typically a wrong field name like 'text').
        # An explicit content:"" IS addressed by the caller and stays a 200
        # no-op; only the ABSENCE of both content keys is the schema error.
        if _msgs is None and _content is None:
            _CONTENT_LIKE = ("text", "fact", "proposition", "body", "prompt",
                             "message", "msg", "value")
            _stray = next((k for k in _CONTENT_LIKE if k in body), None)
            _hint = (f" (got unknown field {_stray!r})" if _stray else "")
            meter.bump(tenant_id, writes=1, rejected=1)
            raise HTTPException(
                status_code=400,
                detail="provide the fact in 'content' (a string) or 'messages' "
                       f"(a list of {{role, content}}){_hint}")
        if _msgs is not None and not isinstance(_msgs, list):
            _bad = "'messages' must be a list of {role, content}"
        elif _msgs is not None and not all(
                isinstance(m, dict) and isinstance(m.get("role"), str)
                and isinstance(m.get("content"), str) for m in _msgs):
            _bad = "each message must be an object with string 'role' and 'content'"
        elif _msgs is None and _content is not None and not isinstance(_content, str):
            _bad = "'content' must be a string"
        elif not isinstance(body.get("topic", "user"), str):
            _bad = "'topic' must be a string"
        elif body.get("verified_by") is not None and not isinstance(
                body.get("verified_by"), list):
            _bad = "'verified_by' must be a list of strings"
        elif body.get("source") is not None and not isinstance(body.get("source"), str):
            _bad = "'source' must be a string"
        elif body.get("asserted_at") is not None and not isinstance(
                body.get("asserted_at"), (int, float)):
            _bad = "'asserted_at' must be a unix timestamp (number)"
        if _bad is not None:
            meter.bump(tenant_id, writes=1, rejected=1)
            raise HTTPException(status_code=400, detail=_bad)
        messages = body.get("messages")
        content = messages if messages is not None else (body.get("content") or "")
        if messages is not None and llm is None:
            raise HTTPException(
                status_code=400,
                detail="conversation ingest needs a server-side extraction llm: "
                       "start the gateway with one (create_app(llm=...)); "
                       "single verified facts work without it",
            )
        # plan quota teeth (TOCTOU-safe): reserve a fact slot ATOMICALLY — the real
        # count + in-flight reservations are weighed together under one lock, so
        # concurrent writes at cap-1 can't ALL pass the check and overrun the cap.
        # enterprise/self_host are uncapped → the reserve short-circuits, no lock.
        # Placed AFTER the raising checks above so no reservation can be orphaned.
        from .gateway_plans import quota_status
        _plan = _plan_for(tenant_id)
        if not _quota_reserve(_quota_pending, _quota_lock, tenant_id, _plan,
                              mem.semantic.count):
            meter.bump(tenant_id, writes=1, rejected=1)
            raise HTTPException(
                status_code=402,
                detail={"error": "fact quota exceeded for plan "
                                 f"'{_plan.name}' (limit {_plan.max_facts})",
                        "quota": quota_status(_plan,
                                              facts_used=mem.semantic.count())})
        _ftok = _flow_ctx(tenant_id)   # il CORE emette flow.write col tenant
        try:
            # ground: absent → None → the store's preset default (moat ON by
            # default, 2026-07-17). The old bool(..., False) HARD-CODED the moat
            # OFF on the gateway even when a judge was configured, so the flip
            # reached only the SDK — the critic caught exactly this. A judge-less
            # gateway still fail-opens, so this never breaks an unconfigured one.
            _g = body.get("ground")
            res = mem.add(
                content,
                topic=body.get("topic", "user"),
                source=body.get("source"),
                verified_by=body.get("verified_by"),
                ground=None if _g is None else bool(_g),
                gate_mode=body.get("gate_mode"),
                asserted_at=body.get("asserted_at"),
                conversation_id=body.get("conversation_id"),
                user_name=body.get("user_name"),
            )
        except ValueError as exc:
            meter.bump(tenant_id, writes=1, rejected=1)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            _flow_ctx_reset(_ftok)
            _quota_release(_quota_pending, _quota_lock, tenant_id, _plan)
        meter.bump(tenant_id, writes=1,
                   stored_ok=1 if res.get("stored") else 0,
                   rejected=0 if res.get("stored") else 1)
        _idem_put(tenant_id, idempotency_key, res)
        return res

    @app.get("/v1/search")
    def search(q: str = Query(...), k: int = Query(default=5, ge=1, le=100),
               deep: bool = False, as_of: float | None = None,
               with_history: bool = False,
               tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        _ftok = _flow_ctx(tenant_id)   # il CORE emette flow.recall col tenant
        try:
            hits = tenants.get(tenant_id).search(
                q, k=k, deep=deep, as_of=as_of, with_history=with_history)
        finally:
            _flow_ctx_reset(_ftok)
        meter.bump(tenant_id, reads=1)
        _shadow_observe(tenant_id, "search", hits, {"n_hits": len(hits)})
        return {"hits": hits}

    @app.get("/v1/explain")
    def explain(q: str = Query(...), k: int = Query(default=5, ge=1, le=100),
                as_of: float | None = None,
                tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        # The enterprise surface abstains by DEFAULT (the selling point works out of
        # the box): a self-calibrating relevance floor so an unsupported query returns
        # an explicit abstention, not a spurious nearest hit. Env-tunable
        # (ENGRAM_GATEWAY_MIN_RELEVANCE=auto|<float>|off). NB the e5 score band is
        # compressed, so the floor is a precision/recall DIAL — 'auto' is validated on
        # real corpora (HaluEval false_answer 1.0->0.04); small stores may over-abstain.
        _ftok = _flow_ctx(tenant_id)   # il CORE emette flow.recall col tenant
        try:
            report = tenants.get(tenant_id).explain(
                q, k=k, as_of=as_of, min_relevance=_gateway_min_relevance())
        finally:
            _flow_ctx_reset(_ftok)
        meter.bump(tenant_id, reads=1)
        return report

    @app.get("/v1/answer")
    def answer(q: str = Query(...), k: int = Query(default=8, ge=1, le=100),
               trust_conditioning: bool = True,
               verify_threshold: float | None = None,
               tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """Grounding-verified, trust-conditioned answering over the tenant's
        store — the read-path measured on the case-B bench (0.17→0.92) was
        SDK-only until the 2026-07-16 critic pass flagged it; this is the
        gateway surface. Needs the server-side llm (same one conversation
        ingest uses): without it the honest response is a 400, not a crash."""
        if llm is None:
            raise HTTPException(
                status_code=400,
                detail="answering needs a server-side llm: start the gateway "
                       "with one (create_app(llm=...)); /v1/search works "
                       "without it",
            )
        _ftok = _flow_ctx(tenant_id)   # il CORE emette flow.recall col tenant
        try:
            out = tenants.get(tenant_id).answer(
                q, llm=llm, k=k, verify_threshold=verify_threshold,
                trust_conditioning=trust_conditioning)
            # answer's OWN flow event (the internal search already emitted
            # kind=search): the Engine Room shows the verdict as what it is.
            from .flow_events import emit_flow as _emit_flow
            _emit_flow("flow.recall", kind="answer",
                       grounded=bool(out.get("grounded")),
                       abstained=out.get("answer") == "NO ANSWER",
                       reason=str(out.get("reason") or ""))
        finally:
            _flow_ctx_reset(_ftok)
        meter.bump(tenant_id, reads=1)
        _shadow_observe(tenant_id, "answer", None,
                        {"reason": out.get("reason"),
                         "grounded": out.get("grounded")},
                        mem=tenants.get(tenant_id), q=q)
        return out

    @app.get("/v1/correct")
    def correct(q: str = Query(...), k: int = Query(default=5, ge=1, le=100),
                tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """The guardian's gateway surface — ACCEPT / CORRECT / ABSTAIN with
        both sides cited. Wired 2026-07-17 after the mod.3 critic's
        caller-verification found `guardian.correct_read` had ZERO production
        callers (README said "read-path guardian" — SDK/tests/docs only; same
        anti-fuffa pattern as answer() the day before). Deterministic, no LLM:
        works on the personal console too."""
        from .guardian import correct_read
        _ftok = _flow_ctx(tenant_id)   # il CORE emette flow.recall col tenant
        try:
            out = correct_read(tenants.get(tenant_id), q, k=k)
            from .flow_events import emit_flow as _emit_flow
            _emit_flow("flow.recall", kind="correct",
                       verdict=str(out.get("verdict") or ""),
                       abstained=out.get("verdict") == "ABSTAIN",
                       reason=str(out.get("reason") or ""))
        finally:
            _flow_ctx_reset(_ftok)
        meter.bump(tenant_id, reads=1)
        return out

    @app.get("/v1/memories/{fact_id}")
    def get_memory(fact_id: str, tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        item = tenants.get(tenant_id).get(fact_id)
        meter.bump(tenant_id, reads=1)
        if item is None:
            raise HTTPException(status_code=404, detail="fact not found")
        return item

    @app.delete("/v1/memories/{fact_id}")
    def delete_memory(fact_id: str, purge_history: bool = False,
                      tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        removed = tenants.get(tenant_id).delete(
            fact_id, purge_history=purge_history)
        meter.bump(tenant_id, writes=1)
        return {"removed": bool(removed)}

    @app.get("/v1/stats")
    def tenant_stats(tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """L'odometro della fiducia del TUO store: quante scritture ammesse /
        quarantenate / rifiutate, quante astensioni oneste, più il tuo uso.
        Solo bearer key: ogni tenant vede esclusivamente i propri numeri."""
        trust = tenants.get(tenant_id).trust_stats()
        meter.bump(tenant_id, reads=1)
        usage = meter.totals().get(tenant_id, {})
        return {"tenant": tenant_id, "trust": trust, "usage": usage}

    @app.get("/v1/quarantine")
    def quarantine(limit: int = Query(default=50, ge=1, le=500),
                   tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """Il log delle confabulazioni FERMATE: i claim vivi in quarantena,
        i più recenti prima. L'odometro dice QUANTI, questo dice QUALI."""
        items = tenants.get(tenant_id).quarantine_log(limit=limit)
        meter.bump(tenant_id, reads=1)
        return {"items": items, "count": len(items)}

    # ---- knowledge graph (read-only views for the console) ----------------
    _kgs: dict[str, Any] = {}
    _kgs_lock = threading.Lock()

    def _kg_for(tenant_id: str):
        """L'EntityStore del tenant, o None se il KG non esiste ancora.
        Il path è derivato SOLO dal tenant risolto dalla chiave (stessa
        proprietà anti-traversal di ``_TenantMemories``); non crea il DB —
        un tenant senza grafo vede un grafo vuoto, non un file nuovo."""
        from .entity_populate import entity_kg_path_for
        if local_tenant and tenant_id == local_tenant and local_memory is not None:
            db = Path(local_memory.semantic.db_path)  # personal mode: own store
        else:
            db = data_dir / "tenants" / tenant_id / "memory.db"
        kg_path = entity_kg_path_for(db)
        if not kg_path.exists():
            return None
        with _kgs_lock:
            kg = _kgs.get(tenant_id)
            if kg is None:
                from .entity_kg import EntityStore
                kg = EntityStore(db_path=kg_path)
                _kgs[tenant_id] = kg
            return kg

    @app.get("/v1/graph")
    def graph(max_nodes: int = Query(default=300, ge=1, le=2000),
              max_edges: int = Query(default=600, ge=0, le=5000),
              tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """Il grafo entità del tenant, renderizzabile: nodi + edge, ogni edge
        con la sua provenance (``source_fact_id``) e il flag ``grounded``."""
        kg = _kg_for(tenant_id)
        meter.bump(tenant_id, reads=1)
        if kg is None:
            return {"nodes": [], "edges": []}
        return kg.snapshot(max_nodes=max_nodes, max_edges=max_edges)

    @app.get("/v1/graph/full")
    def graph_full(max_nodes: int = Query(default=20000, ge=1, le=200000),
                   max_edges: int = Query(default=200000, ge=1, le=2000000),
                   tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """Il grafo INTERO in formato compatto (nodi in array, archi per
        indice) — per il renderer Canvas della console. ``snapshot`` resta la
        finestra piccola; questo è tutto ciò che c'è, senza campionare."""
        kg = _kg_for(tenant_id)
        meter.bump(tenant_id, reads=1)
        if kg is None:
            return {"n": [], "e": [], "truncated": False,
                    "total_entities": 0, "total_edges": 0}
        return kg.snapshot_full(max_nodes=max_nodes, max_edges=max_edges)

    @app.get("/v1/graph/dossier")
    def graph_dossier(src: str = Query(...),
                      target: str | None = Query(default=None),
                      max_hops: int = Query(default=3, ge=1, le=5),
                      k: int = Query(default=25, ge=1, le=100),
                      tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """Il multi-hop CON la catena di custodia: derivazione citata dai
        fatti reali dello store, o astensione onesta (salto senza fonte,
        fatto citato sparito, target irraggiungibile)."""
        kg = _kg_for(tenant_id)
        meter.bump(tenant_id, reads=1)
        if kg is None:
            if target is None:
                return {"dossiers": []}
            return {"target": target, "abstained": True, "grounded": False,
                    "answer": None,
                    "reason": "no knowledge graph for this tenant yet"}
        from .graph_reasoning import reasoning_dossier
        sem = tenants.get(tenant_id).semantic
        out = reasoning_dossier(kg, sem, src, target=target,
                                max_hops=max_hops, k=k)
        return out if target is not None else {"dossiers": out}

    @app.get("/v1/snapshot")
    def full_snapshot(max_nodes: int = Query(default=300, ge=1, le=2000),
                      max_edges: int = Query(default=600, ge=0, le=5000),
                      quarantine_limit: int = Query(default=50, ge=1, le=500),
                      tenant_id: str = Depends(_tenant)) -> dict[str, Any]:
        """L'occhio per un AGENTE: l'intero stato visibile in UNA chiamata —
        odometro+daily, log quarantena, grafo con provenance, uso. Ciò che
        la console mostra a un umano, in forma strutturata per un AI."""
        mem = tenants.get(tenant_id)
        kg = _kg_for(tenant_id)
        meter.bump(tenant_id, reads=1)
        return {
            "tenant": tenant_id,
            "trust": mem.trust_stats(),
            "quarantine": mem.quarantine_log(limit=quarantine_limit),
            "graph": (kg.snapshot(max_nodes=max_nodes, max_edges=max_edges)
                      if kg is not None else {"nodes": [], "edges": []}),
            "usage": meter.totals().get(tenant_id, {}),
        }

    @app.get("/v1/events")
    async def events(request: Request,
                     max_events: int = Query(default=0, ge=0, le=10),
                     tenant_id: str = Depends(_tenant)):
        """La memoria che LAVORA, in diretta (SSE): lo stato iniziale del
        ledger subito, poi un evento a ogni cambiamento (poll server-side
        2s sul contatore — leggero, cross-process perché il ledger vive nel
        DB). Il client usa fetch-streaming, non EventSource: così la bearer
        key resta in un header (mai in un URL) anche in multi-tenant.

        ``max_events`` (0 = infinito): chiude lo stream dopo N eventi — per
        test e probe deterministici (uno stream infinito che ignora il
        disconnect IMPIANTAVA pytest, visto 2026-07-10). In più il loop
        controlla ``request.is_disconnected()`` e termina quando il client
        se ne va — mai un generatore orfano."""
        import asyncio
        import json as _json
        mem = tenants.get(tenant_id)

        async def gen():
            last: dict[str, Any] | None = None
            sent = 0
            while True:
                if await request.is_disconnected():
                    return
                try:
                    # counters only (daily_days=1): il payload live è il
                    # ledger; il resto lo rifetcha il client quando cambia
                    led = mem._ledger.stats(daily_days=1)["ledger"]
                except Exception:  # noqa: BLE001 — fail-open come il ledger
                    led = last
                if led is not None and led != last:
                    yield "data: " + _json.dumps({"ledger": led}) + "\n\n"
                    last = led
                    sent += 1
                    if max_events and sent >= max_events:
                        return
                await asyncio.sleep(2.0)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    @app.get("/v1/events/flow")
    async def events_flow(request: Request,
                          replay: int = Query(default=0, ge=0, le=50),
                          max_events: int = Query(default=0, ge=0, le=50),
                          tenant_id: str = Depends(_tenant)):
        """Il motore in DIRETTA, evento per evento (SSE): ogni ``flow.write``
        (ammesso/quarantenato) e ``flow.recall`` (risposto/astenuto) del
        PROPRIO tenant — mai di altri (privacy multi-tenant by filter).
        Fonte: events.jsonl (cross-process, già rotato a 5 MB).

        ``replay`` rigioca gli ultimi N eventi al connect (la pagina live non
        parte mai vuota); ``max_events`` (0 = infinito) chiude dopo N — per
        test deterministici, stessa lezione 2026-07-10 di ``/v1/events``.
        Il loop controlla ``request.is_disconnected()``: mai generatori orfani."""
        import asyncio
        import json as _json

        from . import event_jsonl_log as _ejl

        # personal mode (verimem console): il local tenant vede anche gli
        # eventi flow SENZA tenant — l'attività sdk/mcp della macchina
        # (loopback-only, single-user). In multi-tenant resta match esatto.
        _see_untenanted = (local_tenant is not None
                           and tenant_id == local_tenant)

        async def gen():
            sent = 0
            # backlog iniziale (una-tantum al connect): legge tutto il file UNA
            # volta, ne mostra gli ultimi `replay`, poi tiene l'offset di byte.
            backlog, offset = _read_flow_bytes(
                _ejl.EVENT_LOG_PATH, 0, tenant_id, _see_untenanted, 0)
            for rec in (backlog[-replay:] if replay else []):
                yield "data: " + _json.dumps(rec, ensure_ascii=False) + "\n\n"
                sent += 1
                if max_events and sent >= max_events:
                    return
            while True:
                if await request.is_disconnected():
                    return
                # TAIL incrementale: ogni tick legge SOLO i byte nuovi da
                # `offset` (non più l'intero file) → niente amplificazione DoS.
                recs, offset = _read_flow_bytes(
                    _ejl.EVENT_LOG_PATH, offset, tenant_id,
                    _see_untenanted, _FLOW_MAX_LINES_PER_TICK)
                for rec in recs:
                    yield ("data: " + _json.dumps(rec, ensure_ascii=False)
                           + "\n\n")
                    sent += 1
                    if max_events and sent >= max_events:
                        return
                await asyncio.sleep(0.5)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        """La vetrina dell'odometro. Pagina STATICA e senza dati: i numeri
        arrivano solo dal fetch autenticato a /v1/stats fatto dal browser del
        tenant; la bearer key vive in sessionStorage (mai in un URL, mai
        renderizzata server-side). Due tenant ricevono byte identici."""
        return _DASHBOARD_HTML

    # ---- /ui — la trust console (il volto del prodotto) --------------------
    # Stessa proprietà del /dashboard: asset STATICI dal package (nessun
    # dato interpolato server-side); odometro + grafo con catena di custodia
    # + log dei claim bloccati, tutto via fetch autenticato dal browser.
    from . import webui as _webui

    @app.get("/", include_in_schema=False)
    def root() -> Response:
        # a human opening the gateway's root gets the console, not a JSON 404
        return Response(status_code=307, headers={"Location": "/ui"})

    # UI assets ship with NO cache headers -> Chrome's heuristic cache may
    # keep serving a STALE console for days after an upgrade (2026-07-16:
    # "è cambiato poco e nulla" — the user was plausibly looking at the old
    # bundle). no-cache + ETag: always revalidated, 304 when unchanged, so
    # the big vendor bundles are not re-downloaded on every load either.
    @functools.lru_cache(maxsize=64)
    def _asset_etag(fname: str) -> str:
        body = _webui.asset(fname)
        if isinstance(body, str):
            body = body.encode("utf-8")
        return '"' + sha256(body).hexdigest()[:20] + '"'

    def _asset_response(fname: str, request: Request) -> Response:
        etag = _asset_etag(fname)
        headers = {"Cache-Control": "no-cache", "ETag": etag}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(content=_webui.asset(fname),
                        media_type=_webui.media_type(fname), headers=headers)

    @app.get("/ui")
    def ui_index(request: Request) -> Response:
        return _asset_response("index.html", request)

    @app.get("/ui/{asset_name}")
    def ui_asset(asset_name: str, request: Request) -> Response:
        # allowlist, no fs walk; "engine" = la LIVE Engine Room (CSP-clean:
        # markup + engine.css + engine.js, zero inline come la console).
        # vendor-* = i bundle grafo self-hosted (sigma/graphology, MIT,
        # copiati da npm — webui/vendor/README.md): la CSP resta
        # `script-src 'self'`, nessun CDN a runtime.
        allow = {"app.js": "app.js", "style.css": "style.css",
                 "graph.js": "graph.js",
                 "vendor-graphology.js": "vendor/graphology.umd.min.js",
                 "vendor-graphology-library.js": "vendor/graphology-library.min.js",
                 "vendor-sigma.js": "vendor/sigma.min.js",
                 "engine": "engine.html", "engine.css": "engine.css",
                 "engine.js": "engine.js"}
        fname = allow.get(asset_name)
        if fname is None:
            raise HTTPException(status_code=404, detail="unknown asset")
        return _asset_response(fname, request)

    # ---- control plane (/admin/*) — esiste SOLO con una admin key --------
    if admin_key:
        def _admin(x_admin_key: str | None = Header(default=None)) -> None:
            if not (x_admin_key and
                    secrets.compare_digest(x_admin_key, admin_key)):
                raise HTTPException(status_code=401,
                                    detail="invalid or missing admin key")

        @app.post("/admin/tenants")
        def create_tenant(body: dict, _: None = Depends(_admin)) -> dict[str, Any]:
            """Provisioning remoto: tenant + chiave via HTTP (non SSH).
            La chiave si vede UNA volta, qui — hash-only a riposo."""
            _tid = str(body.get("tenant_id", ""))
            # opus tenant-pass MED-2: a tenant_id == local_tenant would resolve
            # onto the operator's PERSONAL store (it's pre-seeded in the cache) —
            # a cross-store leak. The reserved personal id can't be provisioned.
            if local_tenant is not None and _tid == local_tenant:
                raise HTTPException(
                    status_code=400,
                    detail=f"tenant_id {_tid!r} is reserved for personal mode")
            try:
                api_key = keys.create(
                    tenant_id=_tid, name=str(body.get("name", "")))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"tenant_id": body.get("tenant_id"), "api_key": api_key}

        @app.get("/admin/stats")
        def stats(_: None = Depends(_admin)) -> dict[str, Any]:
            """Uso per tenant + le trust-metrics che nessun competitor
            espone (scritture ammesse vs rifiutate dal gate)."""
            usage = meter.totals()
            known = {k["tenant_id"] for k in keys.list()}
            for t in known:
                usage.setdefault(t, {"requests": 0, "reads": 0, "writes": 0,
                                     "stored_ok": 0, "rejected": 0})
            return {"uptime_s": round(time.time() - _started_at, 1),
                    "n_tenants": len(usage), "tenants": usage}

        @app.get("/admin/ui", response_class=HTMLResponse)
        def admin_ui(request: Request) -> Response:
            """La org console (un trust-ring per tenant). Statica e senza
            dati come /ui: i numeri viaggiano solo nel fetch autenticato
            X-Admin-Key; la admin key vive in sessionStorage. Esiste SOLO
            con una admin key configurata, come tutto /admin/*."""
            return _asset_response("admin.html", request)

        @app.get("/admin/ui/admin.js")
        def admin_ui_js(request: Request) -> Response:
            return _asset_response("admin.js", request)

        @app.get("/admin/overview")
        def overview(_: None = Depends(_admin)) -> dict[str, Any]:
            """La vista ORG (SaaS/azienda): per ogni tenant noto il suo
            trust ledger + store + uso — un ring per tenant nella admin
            console. Read-only: un tenant senza store ancora scritto mostra
            zeri, non gli viene creato un DB per il gusto di guardarlo."""
            usage = meter.totals()
            known = {k["tenant_id"] for k in keys.list()} | set(usage)
            zeros = {a: 0 for a in
                     ("admitted", "quarantined", "rejected", "abstained")}
            out = []
            for t in sorted(known):
                db = data_dir / "tenants" / t / "memory.db"
                if db.exists():
                    ts = tenants.get(t).trust_stats()
                    ledger, store_ = ts["ledger"], ts.get("store", {})
                else:
                    ledger, store_ = dict(zeros), {}
                out.append({"tenant": t, "ledger": ledger, "store": store_,
                            "usage": usage.get(t, {})})
            return {"n_tenants": len(out), "tenants": out}

        @app.get("/admin/audit")
        def audit_tail(limit: int = 100, day: str | None = None,
                       tenant: str | None = None,
                       _: None = Depends(_admin)) -> dict[str, Any]:
            """Recent access-audit records (who/what/when) — the compliance trail
            READABLE over HTTP, no SSH. Reads the append-only JSONL under
            ``<data_dir>/audit/`` newest-last; ``day`` (YYYYMMDD) selects one
            rotated file, ``tenant`` filters. Read-only; empty if auditing is off."""
            import json as _json
            adir = data_dir / "audit"
            limit = max(1, min(int(limit), 1000))
            pattern = f"access-{day}.jsonl" if day else "access-*.jsonl"
            # bound the work: without an explicit day, scan only the newest files
            files = sorted(adir.glob(pattern))
            if not day:
                files = files[-3:]
            recs: list[dict[str, Any]] = []
            for f in files:
                try:
                    with open(f, encoding="utf-8") as fh:
                        for ln in fh:
                            ln = ln.strip()
                            if not ln:
                                continue
                            try:
                                r = _json.loads(ln)
                            except Exception:  # noqa: BLE001,PERF203
                                continue
                            if tenant and r.get("tenant") != tenant:
                                continue
                            recs.append(r)
                except OSError:
                    continue
            tail = recs[-limit:]
            return {"n": len(tail), "records": tail}

    return app


__all__ = ["GatewayKeys", "create_app"]
