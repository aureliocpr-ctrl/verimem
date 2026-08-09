"""Flow-event fan-out for the LIVE Engine Room — emitted at the CORE.

Every ``Memory.add`` / ``search`` / ``explain`` emits a ``flow.write`` /
``flow.recall`` event through :mod:`verimem.observability` (BUS + structlog +
``events.jsonl`` — the jsonl is the cross-process bus the live surfaces tail:
``/ui/engine`` in the gateway, ``verimem flow tail`` in a terminal).

Because the emission lives in the core, EVERY surface is covered: the REST
gateway, the MCP server (Claude Code, Cursor, or ANY other vendor's agent
that mounts it), plain SDK use, the CLI. Events carry flow METADATA only
(status/score/ids/topic) — never fact content.

Tagging:

* ``surface`` — where the call came from: ``sdk`` (default), ``mcp``,
  ``gateway``. Ambient default via env ``ENGRAM_FLOW_SURFACE`` (set once by
  the MCP server at bootstrap — env, not contextvar, so it survives thread
  pools); per-request override via :func:`set_flow_context`.
* ``actor`` — the agent's label, from env ``VERIMEM_ACTOR`` (or legacy
  ``ENGRAM_ACTOR``): a codex/gemini/gpt agent sets it in its MCP config and
  every one of its events arrives labeled — the single multi-agent panel.
* ``tenant`` — gateway only, via :func:`set_flow_context` (contextvar,
  per-request); the gateway's ``/v1/events/flow`` privacy filter matches on
  it, so core events without a tenant are never streamed to a tenant.

Best-effort by contract: :func:`emit_flow` NEVER raises into the caller's
write/read path.
"""
from __future__ import annotations

import contextvars
import os
from typing import Any

_CTX: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "verimem_flow_ctx", default=None)


def set_flow_context(**fields: Any) -> contextvars.Token:
    """Overlay ambient fields onto every flow event in this context
    (gateway: ``tenant`` + ``surface``). ``None`` values are dropped.
    Returns the token for :func:`reset_flow_context`."""
    cur = dict(_CTX.get() or {})
    cur.update({k: v for k, v in fields.items() if v is not None})
    return _CTX.set(cur)


def reset_flow_context(token: contextvars.Token | None = None) -> None:
    """Clear the overlay (or restore to ``token`` if given)."""
    if token is not None:
        _CTX.reset(token)
    else:
        _CTX.set(None)


#: Impronta della memoria a cui gli eventi si riferiscono, calcolata una
#: volta per processo. `None` = non ancora calcolata.
_IMPRONTA: str | None = None


def reset_store_fingerprint() -> None:
    """Ricalcola l'impronta e il build alla prossima emissione (banchi, e chi
    cambia data dir a processo vivo)."""
    global _IMPRONTA, _BUILD
    _IMPRONTA = None
    _BUILD = None


def _store_fingerprint() -> str:
    """QUALE memoria ha prodotto questo evento — impronta, non percorso.

    Il 2026-08-07 tre misure indipendenti sono cadute nella stessa ora
    sullo stesso file: ws3 «il 94% delle quarantene in events.jsonl poggia
    su fatti che non esistono piu', la fonte e' MULTI-STORE e non lo dice»,
    ws1 lo conferma al decimale e trova la causa vera («il journal e'
    inquinato all'88% dal nostro dogfooding: `events.jsonl` non viene
    isolato da HIPPO_DATA_DIR»), ws4 lo ritrova sulla propria tabella.

    E' un difetto mio a meta': avevo curato il PERCORSO del log (deriva
    dalla data dir invece di essere fisso) e aggiunto l'avviso quando
    diverge — ma `EVENT_LOG_PATH` si fissa all'IMPORT, quindi chi imposta
    la data dir DOPO (cioe' ogni banco) continua a scrivere nel journal di
    casa. La cura dichiarava la divergenza e non la rendeva LEGGIBILE a
    valle: chi analizza il file non poteva separare le due popolazioni, e
    ha dovuto inventarsi un join sui fatti vivi che introduce un secondo
    taglio non scelto.

    Non si impedisce la scrittura — un evento perso e' peggio di un evento
    da filtrare — si dice a quale memoria appartiene.

    IMPRONTA e non percorso: il percorso e' lungo, cambia di macchina e
    questo campo finisce su una pagina web e in file che ci scambiamo.
    L'impronta e' stabile, corta, e basta a dire «questi due eventi
    vengono da memorie diverse».
    """
    global _IMPRONTA
    if _IMPRONTA is None:
        from hashlib import sha256
        try:
            from ._compat import data_dir
            _radice = str(data_dir().resolve())
        except Exception:  # noqa: BLE001 — un tag non rompe un'emissione
            _radice = os.environ.get("HIPPO_DATA_DIR", "") or "unknown"
        _IMPRONTA = sha256(_radice.encode("utf-8")).hexdigest()[:12]
    return _IMPRONTA


#: Il codice che ha prodotto l'evento. `None` = non ancora calcolato.
_BUILD: str | None = None


def _revisione_git() -> str | None:
    """La revisione corta dell'albero da cui gira il pacchetto, o ``None``.

    Legge `.git` a mano e NON lancia `git`: un sottoprocesso per evento
    sarebbe assurdo, e questo campo deve costare quanto l'impronta dello
    store. Gestisce il caso WORKTREE, dove i ref non stanno nella gitdir
    locale ma nel repo principale indicato da `commondir` — senza, si
    otterrebbe il ramo e non la revisione, cioe' meta' risposta, e la meta'
    mancante e' proprio quella che distingue due checkout dello stesso ramo.
    """
    from pathlib import Path
    try:
        g = Path(__file__).resolve().parent.parent / ".git"
        if g.is_file():                       # worktree: .git e' un puntatore
            riga = g.read_text(encoding="utf-8").strip()
            if riga.startswith("gitdir:"):
                g = Path(riga.split(":", 1)[1].strip())
        if not g.is_dir():
            return None
        h = (g / "HEAD").read_text(encoding="utf-8").strip()
        if not h.startswith("ref:"):
            return h[:8] or None              # HEAD staccata
        ref = h.split(":", 1)[1].strip()
        radici = [g]
        try:
            cd = (g / "commondir").read_text(encoding="utf-8").strip()
            radici.append((g / cd).resolve())
        except OSError:
            pass
        for base in radici:
            p = base / ref
            if p.exists():
                return p.read_text(encoding="utf-8").strip()[:8] or None
            pr = base / "packed-refs"
            if pr.exists():
                for r in pr.read_text(encoding="utf-8").splitlines():
                    if r.endswith(" " + ref):
                        return r.split(" ", 1)[0][:8]
    except (OSError, ValueError):
        return None
    return None


def _build() -> str:
    """DA QUALE CODICE viene questo evento — calcolato una volta per processo.

    Il 2026-08-07 TRE indagini diverse sono finite sullo stesso confondente,
    e nessuna poteva risolverlo dal dato: «`heal_contradictions` non registra
    l'undo» (11 su 11), «solo 3 ritiri su 114 hanno un appiglio», «la
    telemetria e' muta sul `grounding_score` per sdk». **Tutte e tre false**,
    e la causa era la stessa: quelle righe le aveva scritte un ALTRO build.
    Per uscirne bisognava ogni volta rieseguire il codice su uno store nuovo.

    L'impronta dello store dice a quale MEMORIA appartiene un evento; questo
    dice da quale CODICE. Senza, quando piu' build scrivono nello stesso
    journal — cioe' sempre, con piu' worktree in parallelo — un campo mancante
    e un difetto sono indistinguibili.

    ⚠️ LA REVISIONE, NON IL PERCORSO, per la stessa ragione per cui l'impronta
    dello store e' un hash: questo campo finisce in file che ci scambiamo e su
    una pagina web. Fuori da un albero git resta la VERSIONE, che risponde a
    una domanda diversa — due checkout della stessa release hanno la stessa
    versione e revisioni diverse — quindi si distingue nella forma.
    """
    global _BUILD
    if _BUILD is None:
        try:
            rev = _revisione_git()
        except Exception:  # noqa: BLE001 — un tag non rompe un'emissione
            rev = None
        if rev:
            _BUILD = rev
        else:
            try:
                from . import __version__
                _BUILD = f"v{__version__}"
            except Exception:  # noqa: BLE001
                _BUILD = "unknown"
    return _BUILD


def _ambient() -> dict[str, Any]:
    # "unknown", not "sdk": the old default was the NAME OF A REAL SURFACE,
    # so 9357 of 9603 real-corpus writes claimed "sdk" while 438 MCP write
    # calls produced ZERO "mcp" events — a dashboard cannot tell a default
    # from a datum (measured ws4, 2026-08-04). Every real entrypoint now
    # declares itself (cli.main / mcp_server / gateway ctx); what remains
    # genuinely unknown SAYS unknown.
    out: dict[str, Any] = {
        "surface": os.environ.get("ENGRAM_FLOW_SURFACE", "").strip() or "unknown",
        # Sta negli AMBIENT e non su `flow.write`: mettendolo solo li', le
        # quarantene — cioe' proprio la popolazione che ws3 e ws4 stavano
        # misurando quando il difetto e' saltato fuori — resterebbero senza.
        "store": _store_fingerprint(),
        # Accanto all'impronta e non altrove: le due rispondono alle due
        # meta' della stessa domanda — QUALE memoria, QUALE codice — e oggi
        # tre indagini si sono fermate sulla seconda meta' mancante.
        "build": _build(),
    }
    actor = (os.environ.get("VERIMEM_ACTOR", "").strip()
             or os.environ.get("ENGRAM_ACTOR", "").strip())
    if actor:
        out["actor"] = actor
    out.update(_CTX.get() or {})
    return out


def emit_write(*, stored: bool, status: str, fact_id: str, topic: str,
               layers: Any = None, grounding_score: Any = None,
               **extra: Any) -> None:
    """L'UNICO emettitore di ``flow.write`` — una funzione, piu' porte.

    Misurato il 2026-08-07 sul log reale: 8247 eventi ``flow.write``, di
    cui `sdk` 7953, `unknown` 208, `gateway` 48, `cli` 38 e **`mcp` ZERO**.
    La causa non era un tag mancante ma strutturale: `flow.write` compariva
    zero volte in `mcp_server.py`, perche' quella porta costruisce il
    ``Fact`` e chiama ``SemanticMemory.store()`` senza passare da
    ``Memory.add()``, dove viveva l'emissione. Un agente che scrive da MCP
    era invisibile al governo — e ws4 ha misurato che e' anche la porta
    meno coperta dal moat (69,5% contro 99,2% della CLI): il meno
    osservabile e il meno controllato sono lo stesso posto.

    ``judged`` e ``withheld_despite_judge`` si DERIVANO qui e non si
    accettano dal chiamante: se una porta potesse dichiarare `judged=True`
    senza un punteggio, il campo mentirebbe — ed e' il campo su cui questo
    prodotto si vende.
    """
    from .retirement_log import judged_true as _judged_true
    _gs = grounding_score
    emit_flow("flow.write", stored=bool(stored), status=str(status),
              fact_id=str(fact_id), topic=str(topic),
              layers=list(layers or []),
              grounding_score=_gs, judged=_gs is not None,
              withheld_despite_judge=(str(status) in ("quarantined",
                                                      "rejected")
                                      and _judged_true(_gs)),
              **extra)


def emit_flow(name: str, **payload: Any) -> None:
    """Emit one flow event (ambient tags + ``payload``). Never raises."""
    try:
        from .observability import emit
        merged = _ambient()
        merged.update(payload)
        emit(name, **merged)
    except Exception:  # noqa: BLE001 — observability never breaks the path
        pass
