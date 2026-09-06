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
1. Ensure the shared encode daemon (verimem.encode_service) is running —
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


def _segnala_rerank_delegato(*, log=None) -> None:
    """Chiede al daemon se sa rerankare, e lo registra. Nessun modello caricato.

    Serve a far trovare alla PRIMA query il budget giusto. Con il CE spostato
    nel daemon, `_reranker_ready()` e' falso finche' il daemon non ha risposto
    almeno una volta: la prima query si da' quindi il budget del cold-load
    (0.25s), un predict remoto (~2.8s) non ci sta, e quella query perde il
    rerank. Misurato il 2026-07-31 su un processo fresco con daemon caldo:
    `timeout_cold` alla prima, `applied` dalla seconda in poi — 11 su 12.

    Nel regime reale quella prima query e' TUTTO: 256 processi su 293 ne fanno
    una sola e muoiono. Una probe da millisecondi sul thread di boot la
    recupera, e non costa RAM: il modello resta nel daemon, qui si registra
    soltanto che c'e'.
    """
    try:
        from . import semantic
        if not semantic._rerank_enabled():
            return
        if semantic._rerank_via_daemon([("probe", "probe")]) is not None and \
                log is not None:
            log.info("mcp_preload_rerank_delegato_al_daemon")
    except Exception as exc:  # noqa: BLE001 — una probe non fa morire il boot
        if log is not None:
            log.warning("mcp_preload_rerank_probe_failed", error=str(exc))


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


def _deve_scaldare_il_giudice() -> bool:
    """Il moat sul write e' acceso ESPLICITAMENTE per questo processo?

    Se lo e', quel server GIUDICHERA', e il modello va scaldato all'avvio invece
    che alla prima scrittura: in delegate-only la prima scrittura non viene
    giudicata (misurato 2026-07-30: ~45s di ``NoGroundingJudge`` prima che il
    warm atterri) e nessuno la rimette in coda quando il giudice si sveglia. Il
    fatto entra non verificato e ci resta.

    Condizionato al flag, e non e' un dettaglio: scaldare il cross-encoder in
    OGNI server MCP e' costato ~450 MB per processo nell'incidente RAM del
    2026-07-10. Chi non accende il moat sul write non paga niente. Assente =
    NO: solo una scelta esplicita compra il modello.
    """
    return (os.environ.get("ENGRAM_GROUNDING_WRITE", "").strip().lower()
            in {"1", "true", "yes", "on"})


def _warm_moat_judge(*, log=None) -> None:
    """Carica il giudice del moat fuori dal thread di richiesta. Best-effort:
    il fallimento e' gia' memorizzato sul giudice e l'advisory continua a
    funzionare — un warm non fa mai morire il boot."""
    try:
        from .local_grounding import get_local_judge
        get_local_judge()._ensure_scorer()
        if log is not None:
            log.info("mcp_preload_moat_judge_complete")
    except Exception as exc:  # noqa: BLE001 — il warm non deve mai uccidere il boot
        if log is not None:
            log.warning("mcp_preload_moat_judge_failed", error=str(exc))


def _service_enabled() -> bool:
    return os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() not in _FALSY


def _scalda_le_librerie_del_giudice(*, log=None) -> None:
    """Carica le LIBRERIE che il giudice usera', all'avvio e non sotto richiesta.

    ⚠️ Non e' il warm del modello (``_warm_moat_judge``, che legge 746 MB ed e'
    condizionato a un flag): qui si importano solo le librerie native. Sono due
    cose diverse e la differenza e' il punto — questo costa 0,3 s, non dipende
    dal modello e non puo' fallire perche' il modello manca.

    PERCHE' ESISTE, misurato il 2026-09-06 sul server MCP:

      · con una richiesta IN CORSO, nel processo non si carica piu' NESSUNA
        estensione C — bloccata anche una senza alcun legame con scipy — mentre
        il GIL resta libero (una sonda continua a stampare per tutti i 121 s);
      · PRIMA che la richiesta arrivi, lo stesso import passa in 0,5 s;
      · la prima scrittura con fonte si fermava dentro
        ``transformers.pytorch_utils`` → ``scipy.linalg._fblas`` e NON TORNAVA
        (1800,0 s, finestra dichiarata). Caricando la catena qui: 17,3 s di
        mediana (16,9 · 17,7 · 16,9), e la seconda scrittura 0,1 s.

    ⚠️ Il PERCHE' un import non finisca mentre una richiesta e' in corso resta
    un'IPOTESI — il loader lock di Windows — e non e' osservabile da Python. La
    cura non ne dipende: il caricamento va fatto dove il caricamento si puo'
    fare, cioe' prima di servire.

    Best-effort come tutto il preload: se fallisce, si prosegue. Un warm non fa
    mai morire il boot.
    """
    try:
        import scipy.linalg  # noqa: F401 — e' il caricamento, non l'uso
        if log is not None:
            log.info("mcp_preload_librerie_del_giudice_pronte")
    except Exception as exc:  # noqa: BLE001 — il warm non deve mai uccidere il boot
        if log is not None:
            log.warning("mcp_preload_librerie_del_giudice_fallito", error=str(exc))


#: Quanto costa il modello del giudice, misurato il 2026-09-06 nel venv del
#: pacchetto (torch 2.14.0+cpu, modello in ~/.engram/models/local_gate_ce_v2):
#: RSS 18,0 MB dopo l'import di questo modulo, 504,3 MB dopo il warm. Il numero
#: sta qui e non in una frase perche' finisce nel log di avvio: chi paga mezzo
#: giga per processo deve poterlo LEGGERE, non dedurlo.
_COSTO_DEL_GIUDICE_MB = 486


def _dichiara_il_piano_del_giudice(*, log=None) -> None:
    """Dice all'avvio se il giudice verra' scaldato, quanto costa, e la leva.

    Prima non lo diceva: ``_warm_moat_judge`` logga solo QUANDO parte, quindi
    per chi non ha ``ENGRAM_GROUNDING_WRITE`` — il caso normale — all'avvio non
    compariva NESSUNA riga sul giudice. Il silenzio si legge come «tutto a
    posto», e invece vuol dire che la prima scrittura con fonte si carichera'
    il modello addosso (12,7 s caldo, 40,1 s al primo giro).

    Vale identica in entrambi i versi: qualunque sia il default, l'avvio
    dichiara quale e' in vigore e come cambiarlo.
    """
    if log is None:
        return
    if _deve_scaldare_il_giudice():
        log.info("mcp_preload_moat_judge_planned",
                 costo_mb=_COSTO_DEL_GIUDICE_MB,
                 per_spegnerlo="ENGRAM_GROUNDING_WRITE=0")
    else:
        log.info("mcp_preload_moat_judge_skipped",
                 perche="ENGRAM_GROUNDING_WRITE non e' acceso",
                 costo_mb_se_acceso=_COSTO_DEL_GIUDICE_MB,
                 per_accenderlo="ENGRAM_GROUNDING_WRITE=1",
                 altrimenti="la prima scrittura con fonte carica il modello "
                            "nel suo thread (12,7 s caldo, 40,1 s freddo)")


def preload_embedding(*, log=None) -> threading.Thread | None:
    """Warm the embedding model. Returns the background thread, or None.

    Returns None when warm-up is skipped (disabled) or run synchronously.
    The background thread is a daemon so it never blocks process shutdown.
    """
    if os.environ.get("HIPPO_EAGER_PRELOAD", "1").strip().lower() in _FALSY:
        return None

    _dichiara_il_piano_del_giudice(log=log)

    def _run() -> None:
        _scalda_le_librerie_del_giudice(log=log)
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
        if _deve_scaldare_il_giudice():
            _warm_moat_judge(log=log)
        return None

    if warm_ce:
        threading.Thread(
            target=_run_reranker, name="hippo-reranker-preload", daemon=True,
        ).start()
    else:
        # Nessun modello caricato qui: si chiede solo al daemon se rerankera'
        # lui, cosi' la PRIMA query trova il budget pieno invece di quello del
        # cold-load. E' la meta' economica del warm — millisecondi, zero RAM —
        # ed e' quella che conta nel regime osservato, dove quasi ogni processo
        # fa una query sola e muore.
        threading.Thread(
            target=lambda: _segnala_rerank_delegato(log=log),
            name="verimem-rerank-probe", daemon=True,
        ).start()
    # Il giudice del moat, sul SUO thread: modello e lock diversi dall'embedder
    # e dal reranker, quindi scaldarlo qui non blocca ne' recall ne' save.
    if _deve_scaldare_il_giudice():
        threading.Thread(
            target=lambda: _warm_moat_judge(log=log),
            name="verimem-moat-judge-preload", daemon=True,
        ).start()
    thread = threading.Thread(
        target=_run, name="hippo-embedding-preload", daemon=True,
    )
    thread.start()
    return thread
