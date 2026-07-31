"""Hang watchdog — make intermittent multi-minute MCP hangs DIAGNOSABLE.

When a tool call exceeds a wall-clock budget, dump ALL thread stacks to
``~/.engram/hang-traces/`` so the exact blocking frame is captured in the act
(``_MODEL_LOCK.acquire`` / socket ``recv`` / sqlite lock / a stale-code path).
Without this, a hang that only reproduces in a user's specific session is a
black box.

CONTRACT — observability ONLY:
  * never changes dispatch behaviour (the call runs exactly as before),
  * never raises (a broken trace dir must not break the tool),
  * never cancels/returns the call (it only LOGS; fixing is a separate concern),
  * a fast call leaves NO file (the header-only file is cleaned up).

faulthandler's timer is process-global, so only ONE call is watched at a time
(a non-blocking lock); concurrent calls run unwatched rather than clobbering the
timer. With the synchronous MCP dispatch (one tool body on the loop at a time)
this watches effectively every call.
"""
from __future__ import annotations

import faulthandler
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_TRACE_DIR = Path(
    os.environ.get("HIPPO_HANG_TRACE_DIR")
    or (Path.home() / ".engram" / "hang-traces")
)
# Below this many bytes the file is header-only (nothing was dumped) → delete.
_HEADER_MAX_BYTES = 300
_ARMED = threading.Lock()

#: Tetto per file. `dump_traceback_later(..., repeat=True)` ridà l'INTERO dump
#: di tutti i thread a ogni intervallo finché la chiamata non finisce: su uno
#: stallo di dieci minuti con budget 30s sono venti dump, e dal secondo in poi
#: è lo stesso stack — zero informazione in più a costo pieno. Misurato il
#: 2026-07-31 sulla macchina di Aurelio: un singolo trace di `hippo_health` da
#: **24.211.732 byte**. Il PRIMO dump, quello che contiene la diagnosi, non
#: viene mai toccato da questo tetto.
_MAX_FILE_BYTES = int(os.environ.get("HIPPO_HANG_TRACE_MAX_BYTES") or 2_000_000)

#: Quanti trace tenere nella cartella. Erano 300 per 34 MB, accumulati in mesi:
#: chi accende una diagnostica non deve ricordarsi di spegnerla.
_MAX_FILES = int(os.environ.get("HIPPO_HANG_TRACE_MAX_FILES") or 40)

#: Ogni quanto guardare se il file ha sfondato il tetto. Un thread leggero: il
#: dump lo scrive faulthandler a livello C e non si può interrompere da dentro.
_CONTROLLO_S = 0.2

#: I sorveglianti attivi. Solo una chiamata alla volta e' osservata (`_ARMED`),
#: quindi la lista ha al massimo un elemento — ma tenerla evita che un thread
#: sopravviva alla sua chiamata se qualcosa va storto in mezzo.
_sorveglianti: list[threading.Event] = []


def _pota_i_vecchi() -> None:
    """Tiene i ``_MAX_FILES`` trace più recenti. Best-effort come tutto il
    modulo: una cartella assente o non scrivibile costa la potatura, mai la
    chiamata che si sta osservando."""
    try:
        file = sorted(_TRACE_DIR.glob("hang-*.txt"),
                      key=lambda p: p.stat().st_mtime)
        for p in file[:max(0, len(file) - _MAX_FILES)]:
            p.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001 — observability only, never raises
        pass


@contextmanager
def hang_trace(label: str, budget_s: float):
    """Wrap a tool call. If it runs longer than ``budget_s`` seconds, append a
    full all-thread stack dump to a per-call file under ``_TRACE_DIR``."""
    if not budget_s or budget_s <= 0:
        yield
        return
    # Process-global faulthandler timer → only one watcher at a time.
    if not _ARMED.acquire(blocking=False):
        yield
        return
    f = None
    path = None
    armed = False
    try:
        _TRACE_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(label))[:40]
        path = _TRACE_DIR / f"hang-{int(time.time())}-{os.getpid()}-{safe}.txt"
        f = open(path, "w", encoding="utf-8")
        f.write(
            f"HANG WATCHDOG  tool={label}  pid={os.getpid()}  budget={budget_s}s\n"
            "the stacks below were dumped because the call exceeded the budget:\n"
        )
        f.flush()
        faulthandler.dump_traceback_later(budget_s, repeat=True, file=f)
        armed = True
        _pota_i_vecchi()
        # Sorvegliante del tetto: il dump lo scrive faulthandler in C e non si
        # puo' fermare da dentro, quindi lo si guarda da fuori e si disarma il
        # timer quando il file ha sfondato. Daemon: non trattiene il processo.
        stop = threading.Event()
        _sorveglianti.append(stop)

        def _sorveglia(percorso=path, ferma=stop):
            while not ferma.wait(_CONTROLLO_S):
                try:
                    if percorso.stat().st_size <= _MAX_FILE_BYTES:
                        continue
                    faulthandler.cancel_dump_traceback_later()
                    with open(percorso, "a", encoding="utf-8") as g:
                        g.write(
                            f"\n[watchdog] tetto di {_MAX_FILE_BYTES} byte "
                            f"raggiunto: i dump successivi ripetevano lo stesso "
                            f"stack e sono stati fermati. Il primo dump qui "
                            f"sopra e' quello che contiene la diagnosi.\n")
                except Exception:  # noqa: BLE001 — mai far fallire la chiamata
                    pass
                return

        threading.Thread(target=_sorveglia, name="hang-trace-cap",
                         daemon=True).start()
    except Exception:  # noqa: BLE001 — tracing is best-effort, never break the call
        if f is not None:
            try:
                f.close()
            except Exception:  # noqa: BLE001
                pass
            f = None
    try:
        yield
    finally:
        for s in _sorveglianti:
            s.set()
        _sorveglianti.clear()
        if armed:
            try:
                faulthandler.cancel_dump_traceback_later()
            except Exception:  # noqa: BLE001
                pass
        if f is not None:
            try:
                size = f.tell()
                f.close()
                if size <= _HEADER_MAX_BYTES and path is not None:
                    path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        _ARMED.release()
