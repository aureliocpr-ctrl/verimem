"""Embedding model warm-up (non-blocking, shared-daemon aware).

The sentence-transformers model costs ~20s to load per process. Two bad
options were in play before this module:

- LAZY (HIPPO_EAGER_PRELOAD=0): the load happens on the user's first
  ``hippo_recall`` / ``hippo_facts_search`` call, blocking it for ~20s.
- SYNC EAGER (HIPPO_EAGER_PRELOAD=1, the old production config): the load ran
  before the JSON-RPC stdio loop started, blocking the MCP *attach handshake*
  for ~20s (the client could time out; N servers starting together thrashed
  the machine).

Strategy now (all on a BACKGROUND daemon thread, so attach is instant):
1. Ensure the shared encode daemon (engram.encode_service) is running —
   spawn it windowless if absent. All MCP servers + the CLI then share ONE
   warm model instead of each loading their own (~500 MB × N → ~500 MB).
2. Wait briefly for the daemon to warm. If it comes up, this process does NOT
   load its own model (RAM saved) — encode() will use the daemon.
3. If the daemon never comes up within the window, warm THIS process's model
   as a fallback so the first real query isn't a cold-load cliff.

Env knobs:
- ``HIPPO_EAGER_PRELOAD=0``     -> skip warm-up entirely (lazy on first call).
- ``HIPPO_PRELOAD_BACKGROUND=0`` -> run synchronously before serving (legacy).
- ``ENGRAM_ENCODE_SERVICE=0``    -> ignore the shared daemon, warm locally.
- ``HIPPO_RERANK_PRELOAD=1``     -> ALSO warm the CrossEncoder at boot
  (default OFF since the 2026-07-10 RAM incident: the CE was warmed in EVERY
  MCP server process — ~450 MB × N servers resident even when idle. The
  recall path lazy-loads it with a cold budget — bi-encoder order until warm
  — so boot-warming is an opt-in latency optimisation, not a requirement).
"""
from __future__ import annotations

import os
import threading
import time

_FALSY = {"0", "false", "no", "off"}
# How long the background thread waits for the shared daemon to warm before
# falling back to loading this process's own model.
_DAEMON_WARM_WAIT_S = 25.0


def _warm() -> None:
    # Imported lazily so importing this module is side-effect free / cheap.
    from . import embedding

    embedding.encode("warmup")


def _warm_reranker(*, log=None) -> None:
    """Pre-load the stage-2 cross-encoder reranker (the R@1 lever) in-process.

    The reranker is NOT delegated to the encode daemon (it runs in the recall
    process) and its cold load is ~33s. Without an explicit warm, fresh server
    processes serve rerank-cold recalls (the per-query budget bails to bi-encoder
    order) — the verified R@1 lift silently doesn't apply. It uses its own lock
    (not the embedding _MODEL_LOCK), so warming it here never blocks recall/save;
    recalls during the warm just keep bi-encoder order until it's resident.
    Best-effort: a missing/offline reranker model must never crash boot.
    """
    try:
        from . import semantic
        if not semantic._rerank_enabled():
            return
        semantic._load_reranker()
        if log is not None:
            log.info("mcp_preload_reranker_complete")
    except Exception as exc:  # noqa: BLE001 — warm-up must never crash boot
        if log is not None:
            log.warning("mcp_preload_reranker_failed", error=str(exc))


def _service_enabled() -> bool:
    return os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() not in _FALSY


def preload_embedding(*, log=None) -> threading.Thread | None:
    """Warm the embedding model. Returns the background thread, or None.

    Returns None when warm-up is skipped (disabled) or run synchronously.
    The background thread is a daemon so it never blocks process shutdown.
    """
    if os.environ.get("HIPPO_EAGER_PRELOAD", "1").strip().lower() in _FALSY:
        return None

    def _run() -> None:
        try:
            if _service_enabled():
                from . import encode_service

                # Spawn the shared daemon if absent so all servers + CLI share
                # one warm model. Wait briefly; if a daemon serving OUR model
                # comes up, skip loading this process's own model (RAM saved).
                # MUST be model-aware (daemon_usable, not is_reachable): a stale
                # wrong-model daemon is unusable to encode(), so trusting mere
                # reachability would skip the local warm and leave every encode
                # cold-loading ~20s on the request thread (the cold-hang bug).
                if encode_service.daemon_usable():
                    if log is not None:
                        log.info("mcp_preload_using_shared_daemon")
                    return
                encode_service.ensure_running()
                deadline = time.time() + _DAEMON_WARM_WAIT_S
                while time.time() < deadline:
                    if encode_service.daemon_usable():
                        if log is not None:
                            log.info("mcp_preload_using_shared_daemon")
                        return
                    time.sleep(1.0)
                if log is not None:
                    log.info("mcp_preload_daemon_unavailable_warming_local")
            # DELEGATE-ONLY (MCP server): NEVER cold-load in-process. The ~33s
            # `import sentence_transformers` runs under _MODEL_LOCK and blocks
            # every concurrent recall/save (the recurring hang; hang-trace
            # 2026-06-06 showed this preload thread holding the lock). Leave the
            # server embedding-less — encode() delegates to the shared daemon and
            # degrades (recall→keyword / save→defer) until the daemon is warm.
            from . import embedding as _emb
            if _emb._delegate_only():
                if log is not None:
                    log.info("mcp_preload_delegate_only_skip_local_warm")
                return
            _warm()
            if log is not None:
                log.info("mcp_eager_preload_complete")
        except Exception as exc:  # noqa: BLE001 — warm-up must never crash boot
            if log is not None:
                log.warning("mcp_eager_preload_failed", error=str(exc))

    # Warm the reranker on its OWN daemon thread (separate model + lock from the
    # embedder) — OPT-IN (HIPPO_RERANK_PRELOAD=1). Default off: every MCP server
    # process was paying ~450 MB for a CE most of them never used (2026-07-10
    # RAM incident); the recall path lazy-loads it under a cold budget instead.
    warm_ce = (
        os.environ.get("HIPPO_RERANK_PRELOAD", "0").strip().lower()
        not in _FALSY
    )

    def _run_reranker() -> None:
        _warm_reranker(log=log)

    if os.environ.get("HIPPO_PRELOAD_BACKGROUND", "1").strip().lower() in _FALSY:
        _run()
        if warm_ce:
            _run_reranker()
        return None

    if warm_ce:
        threading.Thread(
            target=_run_reranker, name="hippo-reranker-preload", daemon=True,
        ).start()
    thread = threading.Thread(
        target=_run, name="hippo-embedding-preload", daemon=True,
    )
    thread.start()
    return thread
