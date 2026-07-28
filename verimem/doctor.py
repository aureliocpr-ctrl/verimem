"""``verimem doctor`` — one-shot install diagnosis, fast by construction.

Answers "why doesn't it work?" in seconds instead of a support thread: every
check reports PASS / WARN / FAIL with the concrete fix. Deliberately loads NO
model (presence checks and socket probes only) so it finishes in ~2s even on a
broken install — a doctor that hangs is a patient.

Every incident from 2026-07-18 maps to a check here: encode daemon down
(``daemon``), moat CE missing on a fresh machine (``moat-judge``), offline pins
(``offline``), legacy/brand env confusion (``data-dir`` shows which dir won).
"""
from __future__ import annotations

import os
import sys
from typing import Any

OK = "ok"
WARN = "warn"
FAIL = "fail"


def run_doctor() -> list[dict[str, Any]]:
    """Run all checks; each returns ``{name, status, detail, fix?}``.

    Pure inspection — no model load, no network beyond a loopback socket probe,
    no writes outside a 1-byte probe file that is removed.
    """
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: str, fix: str | None = None) -> None:
        c: dict[str, Any] = {"name": name, "status": status, "detail": detail}
        if fix:
            c["fix"] = fix
        checks.append(c)

    # -- version ---------------------------------------------------------------
    try:
        from . import __version__
        add("version", OK, f"verimem {__version__} · python {sys.version.split()[0]}")
    except Exception as e:  # noqa: BLE001 — a doctor never crashes on a check
        add("version", WARN, f"unreadable: {e}")

    # -- data dir --------------------------------------------------------------
    try:
        from ._compat import data_dir
        d = data_dir()
        probe = d / ".doctor-probe"
        try:
            probe.write_text("x")
            probe.unlink()
            writable = True
        except OSError:
            writable = False
        dbs = sorted(p.name for p in d.glob("*.db"))
        add("data-dir", OK if writable else FAIL,
            f"{d} (writable={writable}; stores: {', '.join(dbs) or 'none yet'})",
            None if writable else "fix directory permissions, or set VERIMEM_DATA_DIR")
    except Exception as e:  # noqa: BLE001
        add("data-dir", FAIL, str(e), "set VERIMEM_DATA_DIR to a writable path")

    # -- embedding model + shared encode daemon --------------------------------
    try:
        from . import encode_service as svc
        from .config import CONFIG
        info = svc.read_discovery()
        if info and svc.daemon_usable(info):
            add("daemon", OK,
                f"shared encode daemon warm on :{info.get('port')} "
                f"(model {info.get('model')})")
        elif info:
            add("daemon", WARN,
                f"discovery file present but daemon not usable "
                f"(model={info.get('model')!r} vs config={CONFIG.embedding_model!r})",
                "it respawns on demand; or run `verimem warmup` to spawn+warm now")
        else:
            add("daemon", WARN,
                "no shared encode daemon — first encode in each process "
                "cold-loads the model (~20s)",
                "run `verimem warmup` once")
    except Exception as e:  # noqa: BLE001
        add("daemon", WARN, f"probe failed: {e}")

    # -- moat judge (the product's #1 claim) -----------------------------------
    # Below this share of entailment-judged facts the moat-judge check WARNS
    # instead of passing. The alarm used to fire only at exactly zero, so a
    # single judged write turned it green: measured on the real store the
    # evening it was added, 3 of 4723 judged (0.06%) reported OK. Half is a
    # declared choice, not a measurement — the point is that the check reads a
    # FRACTION, so it cannot be silenced by one write.
    _MOAT_COVERAGE_WARN = 0.5
    try:
        from .llm import _autodetect_provider
        from .local_grounding import _resolve_model_dir, local_ce_available
        ce = local_ce_available()
        provider = None
        try:
            provider = _autodetect_provider()
        except Exception:  # noqa: BLE001 — provider detection is best-effort
            provider = None
        if ce:
            # "the moat is ON" is true of the JUDGE and gets read as "my store
            # is protected". The moat only runs on writes that carry a source,
            # so an installed judge and an unjudged corpus coexist happily —
            # measured 2026-07-28 on the real store: judge present, 0 of 6414
            # facts ever judged. Two COUNTs keep doctor inside its ~2s budget.
            _n = _judged = 0
            _readable = True
            try:
                import sqlite3 as _sq

                from ._compat import data_dir as _dd
                # _compat.data_dir(), the same resolver the data-dir check above
                # uses — it reads the environment at call time, so doctor reports
                # on the store the operator is actually pointed at.
                _db = _dd() / "semantic" / "semantic.db"
                if _db.exists():
                    with _sq.connect(str(_db)) as _c:
                        _n = int(_c.execute(
                            "SELECT COUNT(*) FROM facts "
                            "WHERE superseded_by IS NULL").fetchone()[0])
                        _judged = int(_c.execute(
                            "SELECT COUNT(*) FROM facts WHERE superseded_by "
                            "IS NULL AND grounding_score IS NOT NULL"
                        ).fetchone()[0])
            except Exception:  # noqa: BLE001 — a doctor that hangs is a patient
                # NOT silently zero: a locked, corrupt or schema-drifted store
                # would then be indistinguishable from a healthy empty one, and
                # this check would print its most reassuring line exactly when
                # it could not look (adversarial review, 2026-07-28).
                _n = _judged = 0
                _readable = False
            if not _readable:
                add("moat-judge", WARN,
                    "local CE gate model installed, but the store could not be "
                    "read — coverage of the moat is UNKNOWN, not zero",
                    "check the store with `verimem status`; a store predating "
                    "the grounding_score column, locked or corrupt will fail "
                    "this read")
            elif _n and _judged / _n < _MOAT_COVERAGE_WARN:
                add("moat-judge", WARN,
                    f"local CE gate model installed, but only {_judged} of {_n} "
                    f"stored facts were entailment-judged "
                    f"({100 * _judged / _n:.1f}%) — the moat runs only on writes "
                    f"that carry a source",
                    "pass source='<the evidence text>' on add() (or --source on "
                    "`verimem save`); a verified_by ref records WHO vouches and "
                    "does not run the check")
            elif _n:
                add("moat-judge", OK,
                    f"local CE gate model installed — the grounding moat is ON "
                    f"with no llm (multilingual); {_judged} of {_n} stored facts "
                    f"entailment-judged")
            else:
                add("moat-judge", OK,
                    "local CE gate model installed — the grounding moat is ON "
                    "with no llm (multilingual)")
        elif provider and provider != "mock":
            add("moat-judge", WARN,
                f"local CE gate model NOT installed; an llm provider is available "
                f"({provider}) — the moat runs only when you pass llm=... to Memory",
                "run `verimem warmup` to download the gate model (~656 MB), or "
                "pass llm= to Memory")
        else:
            add("moat-judge", FAIL,
                f"NO grounding judge: local CE model missing at "
                f"{_resolve_model_dir(None)} and no llm provider detected — "
                "writes are admitted with an L4-skipped advisory (moat OFF)",
                "run `verimem warmup` to download the published gate model "
                "(~656 MB, no account needed), or pass llm= to Memory")
    except Exception as e:  # noqa: BLE001
        add("moat-judge", WARN, f"probe failed: {e}")

    # -- offline pins ----------------------------------------------------------
    try:
        from .airgap import _OFFLINE_FLAGS
        set_flags = [f for f in _OFFLINE_FLAGS
                     if os.environ.get(f, "").strip().lower() in
                     ("1", "true", "yes", "on")]
        if set_flags:
            add("offline", OK, f"offline-pinned via {', '.join(set_flags)} "
                               "(no HF Hub round-trips)")
        else:
            add("offline", WARN,
                "no offline flag set — cold model loads may hit the HF Hub",
                "for air-gapped deploys set VERIMEM_OFFLINE=1 (see `verimem airgap`)")
    except Exception as e:  # noqa: BLE001
        add("offline", WARN, f"probe failed: {e}")

    # -- llm provider (names only — never values) ------------------------------
    try:
        from .llm import _autodetect_provider
        p = _autodetect_provider()
        if p and p != "mock":
            add("llm", OK, f"provider auto-detected: {p}")
        else:
            add("llm", WARN,
                "no llm provider detected — extraction from raw conversations "
                "and the highest-quality judge need one",
                "set an API key (e.g. ANTHROPIC_API_KEY) or run Ollama")
    except Exception as e:  # noqa: BLE001
        add("llm", WARN, f"probe failed: {e}")

    # -- gateway ---------------------------------------------------------------
    try:
        from ._compat import data_dir
        keys_db = data_dir() / "gateway_keys.db"
        if keys_db.exists():
            add("gateway", OK, f"keys db present ({keys_db.name}) — "
                               "`verimem gateway serve` ready")
        else:
            add("gateway", OK, "no gateway keys yet (only needed for the "
                               "self-host team server)")
    except Exception as e:  # noqa: BLE001
        add("gateway", WARN, f"probe failed: {e}")

    return checks


def worst_status(checks: list[dict[str, Any]]) -> str:
    order = {OK: 0, WARN: 1, FAIL: 2}
    return max((c["status"] for c in checks), key=lambda s: order.get(s, 2),
               default=OK)
