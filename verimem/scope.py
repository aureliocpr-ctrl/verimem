"""B-1 multi-tenancy — mem0-parity scoping via a ZERO-SCHEMA topic prefix.

Canonical prefix order: ``user:<u>/agent:<a>/run:<r>/<base-topic>``. Each segment
is present only when that dimension is supplied. Reuses the ``agent:`` convention
from :mod:`verimem.agent_scope`, so agent-only scoping is byte-identical to the
pre-existing one. No DB schema change: the scope lives in the topic string and is
filtered at recall time. Strict per-dimension isolation (a fact scoped to
``user=alice`` is invisible to a ``user=bob`` query); unscoped/shared facts are
opt-in via ``include_shared``.

Caveat (accepted, same as agent_scope): a legitimate topic that literally starts
with ``user:`` / ``agent:`` / ``run:`` would be parsed as scoped. Topics in
practice are namespaced like ``project/x`` / ``lessons/y``, so this is rare; the
zero-schema simplicity is the deliberate trade.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

# Canonical dimension order — prefix segments are emitted in THIS order
# regardless of kwarg order, so the same scope always yields the same topic.
_DIMS = ("user_id", "agent_id", "run_id")
_KEY = {"user_id": "user", "agent_id": "agent", "run_id": "run"}
_KEY_REV = {v: k for k, v in _KEY.items()}

_ID_OK = re.compile(r"^[A-Za-z0-9_\-.]+$")
_SEG = re.compile(r"^(user|agent|run):([^/]+)/")


def _validate(dim: str, value: str) -> None:
    if not value or not _ID_OK.match(value):
        raise ValueError(
            f"{dim} must be a simple identifier [A-Za-z0-9_-.], got {value!r}"
        )


def parse_scope(topic: str | None) -> dict:
    """Split ``topic`` into its leading scope segments + base topic.

    Returns ``{user_id, agent_id, run_id, base}``. Leading ``<key>:<val>/``
    segments are consumed left-to-right; a repeated dim stops parsing (the rest
    is treated as the base topic). Absent dims are ``None``.
    """
    out: dict = {"user_id": None, "agent_id": None, "run_id": None, "base": topic or ""}
    rest = topic or ""
    while True:
        m = _SEG.match(rest)
        if not m:
            break
        kw = _KEY_REV[m.group(1)]
        if out[kw] is not None:
            break  # same dim twice -> stop; leave remainder as base
        out[kw] = m.group(2)
        rest = rest[m.end():]
    out["base"] = rest
    return out


def scoped_topic(
    topic: str, *, user_id: str | None = None,
    agent_id: str | None = None, run_id: str | None = None,
) -> str:
    """Prefix ``topic`` with the supplied scope dims in canonical order.

    Idempotent + merging: existing leading scope segments are parsed and merged
    with the supplied dims (supplied values override), so re-scoping never nests
    (no ``user:a/user:a/...``). No-op when no dims are supplied.
    """
    parsed = parse_scope(topic)
    for dim, val in (("user_id", user_id), ("agent_id", agent_id), ("run_id", run_id)):
        if val is not None:
            _validate(dim, val)
            parsed[dim] = val
    prefix = "".join(
        f"{_KEY[dim]}:{parsed[dim]}/" for dim in _DIMS if parsed[dim] is not None
    )
    return f"{prefix}{parsed['base']}"


def lead_prefix(
    *, user_id: str | None = None,
    agent_id: str | None = None, run_id: str | None = None,
) -> str | None:
    """The contiguous LEADING canonical scope prefix (``user:`` → ``agent:`` →
    ``run:``) usable as a SQL ``topic LIKE '<prefix>%'`` narrow so scoped
    queries are complete at scale (compete only among the tenant's own rows).

    Returns ``None`` when the leading dim (``user_id``) is absent: a non-leading
    dim (e.g. ``agent_id`` without ``user_id``) cannot form a prefix and the
    caller must fall back to oversample + :func:`matches_scope` post-filtering.
    The prefix stops at the first gap (``user_id`` + ``run_id`` without
    ``agent_id`` yields ``"user:<u>/"`` only).
    """
    if user_id is None:
        return None
    out = f"user:{user_id}/"
    if agent_id is not None:
        out += f"agent:{agent_id}/"
        if run_id is not None:
            out += f"run:{run_id}/"
    return out


def scoped_fetch_limit(
    base: int, *, scoped: bool, has_prefix: bool,
    agent_id: str | None = None, run_id: str | None = None,
    factor: int = 8, cap: int,
) -> int:
    """Fetch bound for a scoped query whose hits are post-filtered by
    :func:`matches_scope`.

    Oversample (``base * factor``, capped at ``cap``) so the post-filter can't
    silently UNDER-RETURN — UNLESS the leading prefix already covers every
    specified dim, in which case the post-filter is redundant and ``base``
    suffices.

    The gap the oversample protects against (correctness-hunt #3 medium): a
    ``run_id`` WITHOUT ``agent_id``. :func:`lead_prefix` stops at the first gap
    and yields only ``"user:<u>/"``, yet :func:`matches_scope` still filters on
    ``run_id`` and drops the non-matching rows. With ``base`` rows fetched under
    the partial prefix, a query whose run owns only a few of the user's many
    facts returns far fewer than ``base`` rows that actually match — informazione
    reale persa al recall. A complete prefix (no gap) makes the post-filter a
    no-op, so ``base`` is exact and we skip the oversample.
    """
    prefix_complete = has_prefix and not (run_id is not None and agent_id is None)
    if prefix_complete:
        return base
    if scoped:
        return min(base * factor, cap)
    return base


def matches_scope(
    topic: str | None, *, user_id: str | None = None,
    agent_id: str | None = None, run_id: str | None = None,
    include_shared: bool = False,
) -> bool:
    """True if ``topic``'s scope satisfies the query.

    For each SPECIFIED query dim, the fact's parsed value must equal it (strict
    tenant isolation). Unspecified query dims are wildcards. A fact that is
    UNSCOPED on a constrained dim matches only when ``include_shared=True``.
    A query with no dims constrains nothing (current/global behavior).
    """
    parsed = parse_scope(topic)
    for dim, want in (("user_id", user_id), ("agent_id", agent_id), ("run_id", run_id)):
        if want is None:
            continue
        have = parsed[dim]
        if have == want:
            continue
        if have is None and include_shared:
            continue
        return False
    return True


@dataclass(frozen=True)
class Scope:
    """L'ambito a cui e' LEGATO un handle — lo store o il motore — invece di un
    argomento che ogni chiamata deve ricordarsi di passare.

    ATLAS (29/09): fino a qui il restringimento lo faceva chi legge — la riga di
    comando e il server MCP, ciascuno con la sua copia — e un consumatore della
    libreria, saltando quel codice, vedeva i fatti di tutti. Un handle legato
    applica l'ambito a OGNI lettura e scrittura: non c'e' una chiamata in cui
    dimenticarlo, e un argomento non lo allarga (`topic` lo riporta dentro).
    La semantica e' quella di :func:`matches_scope`, la stessa delle porte.
    """

    user_id: str | None = None
    agent_id: str | None = None
    run_id: str | None = None
    include_shared: bool = False

    def __post_init__(self) -> None:
        for dim in _DIMS:
            val = getattr(self, dim)
            if val is not None:
                _validate(dim, val)

    @property
    def vuoto(self) -> bool:
        """Nessuna dimensione: l'handle vede tutto, come prima di Atlas."""
        return all(getattr(self, dim) is None for dim in _DIMS)

    def contiene(self, topic: str | None) -> bool:
        return matches_scope(
            topic, user_id=self.user_id, agent_id=self.agent_id,
            run_id=self.run_id, include_shared=self.include_shared)

    def prefisso(self) -> str | None:
        """Il prefisso che restringe in SQL, o None quando da solo non basta:
        senza utente non c'e' un prefisso iniziale, e con `include_shared` i
        fatti condivisi stanno fuori da qualunque prefisso."""
        if self.include_shared:
            return None
        return lead_prefix(user_id=self.user_id, agent_id=self.agent_id,
                           run_id=self.run_id)

    def topic(self, topic: str | None) -> str:
        """Un topic riportato nell'ambito: quello che si scrive ci finisce
        dentro, e un filtro che nomina un altro utente viene riscritto nel
        proprio — le dimensioni dell'handle vincono, come in `scoped_topic`."""
        return scoped_topic(topic or "", user_id=self.user_id,
                            agent_id=self.agent_id, run_id=self.run_id)

    def stretto(self, altro: Scope) -> Scope:
        """L'ambito di un handle derivato da uno gia' legato: puo' solo
        restringere. Cambiare una dimensione gia' fissata, o aprire i fatti
        condivisi a chi non li vedeva, sarebbe allargare, e si rifiuta."""
        if self.vuoto:
            return altro
        valori: dict[str, str | None] = {}
        for dim in _DIMS:
            mio, chiesto = getattr(self, dim), getattr(altro, dim)
            if mio is not None and chiesto is not None and mio != chiesto:
                raise PermissionError(
                    f"un handle legato a {dim}={mio!r} non si rilega a {chiesto!r}")
            valori[dim] = mio if mio is not None else chiesto
        if altro.include_shared and not self.include_shared:
            raise PermissionError(
                "un handle legato senza i fatti condivisi non li apre")
        return Scope(**valori, include_shared=self.include_shared
                     and altro.include_shared)

    def parametri_sql(self) -> tuple[str | None, str | None, str | None, int]:
        return (self.user_id, self.agent_id, self.run_id,
                1 if self.include_shared else 0)


def clausola_sql(colonna: str = "topic") -> str:
    """Il predicato dell'ambito in SQL, con i quattro parametri di
    :meth:`Scope.parametri_sql`. E' la STESSA `matches_scope` delle porte, non
    una sua traduzione in LIKE: due formulazioni divergerebbero sui casi di
    bordo (una dimensione ripetuta nel topic, il `_` che in LIKE e' un jolly)."""
    return f"verimem_nell_ambito({colonna}, ?, ?, ?, ?)"


def _nell_ambito_sql(topic, user_id, agent_id, run_id, include_shared) -> int:
    return 1 if matches_scope(
        topic, user_id=user_id, agent_id=agent_id, run_id=run_id,
        include_shared=bool(include_shared)) else 0


def registra_nella_connessione(conn: sqlite3.Connection) -> None:
    """Rende il predicato disponibile a una connessione dello store. Pura e
    senza stato: l'ambito arriva come parametro, quindi la stessa funzione
    serve anche alle connessioni riusate fra handle diversi."""
    conn.create_function("verimem_nell_ambito", 5, _nell_ambito_sql,
                         deterministic=True)


__all__ = [
    "parse_scope", "scoped_topic", "matches_scope", "lead_prefix",
    "scoped_fetch_limit", "Scope", "clausola_sql", "registra_nella_connessione",
]
