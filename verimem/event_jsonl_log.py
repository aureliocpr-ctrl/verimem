"""Cross-process event log — append-only JSONL.

Il bus in-process (``verimem.observability.BUS``) emette eventi solo nel
processo corrente. La memory-map live dashboard (feature/memory-map-live)
deve invece mostrare cosa fanno **altre istanze HippoAgent** che girano
in parallelo (CLI, IDE, MCP server, daemon Auto-Dream). Quei processi
condividono lo stesso ``~/.engram/`` data dir ma non lo stesso event bus
Python, quindi serve un canale shared via filesystem.

Soluzione: ogni ``emit()`` su ``observability`` appende una riga JSONL
qui. La route ``/api/memory-map/events`` fa tail-and-poll del file e
ri-emette via SSE ai client connessi al browser.

Formato — una riga JSON per evento::

    {"name": "...", "payload": {...}, "ts": 1234567890.123}

Append atomico fino a PIPE_BUF, sufficiente per JSON line < 4KB tipici.
Idempotente: la dir parent viene creata se manca. Best-effort: payload
non serializzabili o errori I/O sono inghiottiti — il bus principale
non viene mai rotto da questo modulo.

Dove vive il file: ``<data dir>/events.jsonl``, cioè la data dir che
l'utente ha scelto (``HIPPO_DATA_DIR`` e alias). Fino al 2026-08-05 il
default era ``~/.engram`` scritto a mano, quindi chi isolava lo store
scriveva comunque la telemetria nel corpus di casa. ``ENGRAM_EVENT_LOG``
resta l'override esplicito e vince su tutto.

⚠️ ``EVENT_LOG_PATH`` è calcolato all'IMPORT del modulo: settare le env
dopo non ha effetto, e per questo i test lo monkey-patchano direttamente
(o girano in un subprocesso, che è il modo di verificare il default vero).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def _default_event_log() -> Path:
    """``<data dir>/events.jsonl`` — the log lives where the store lives.

    It used to be ``Path.home() / ".engram"`` written by hand, so a caller
    who isolated the store with ``HIPPO_DATA_DIR`` (the lever the product
    itself teaches: the alias warning says "HIPPO_DATA_DIR wins") kept
    writing telemetry into the home corpus — measured 2026-08-05, 39 lines
    of isolated benches landed in the production log. Store and observability
    stay two separate things: ``ENGRAM_EVENT_LOG`` remains the explicit
    override for whoever wants the log elsewhere. Best-effort: if the data
    dir cannot be resolved, the historical home path stands.
    """
    override = os.environ.get("ENGRAM_EVENT_LOG", "").strip()
    if override:
        return Path(override)
    try:
        from ._compat import data_dir
        return Path(data_dir()) / "events.jsonl"
    except Exception:  # noqa: BLE001 — observability never breaks an import
        return Path.home() / ".engram" / "events.jsonl"


EVENT_LOG_PATH: Path = _default_event_log()

# A7 (audit 2026-06-08): cap the append-only log. Every emit() — incl. every MCP
# tool call — appends a line here; with no rotation a long-running server grew
# events.jsonl to hundreds of MB. Override via ENGRAM_EVENT_LOG_MAX_BYTES.
_EVENT_LOG_MAX_BYTES: int = int(
    os.environ.get("ENGRAM_EVENT_LOG_MAX_BYTES", str(5 * 1024 * 1024))
    or (5 * 1024 * 1024)
)


def _maybe_rotate() -> None:
    """Rotate ``EVENT_LOG_PATH`` to a single ``.1`` backup once it exceeds
    ``_EVENT_LOG_MAX_BYTES`` (``os.replace`` is atomic), bounding total to ~2x
    the cap. Best-effort: any error leaves the log as-is (never breaks emit)."""
    try:
        if EVENT_LOG_PATH.stat().st_size < _EVENT_LOG_MAX_BYTES:
            return
    except OSError:
        return
    try:
        os.replace(EVENT_LOG_PATH, EVENT_LOG_PATH.with_name(EVENT_LOG_PATH.name + ".1"))
    except OSError:
        pass


#: L'avviso di divergenza si dà UNA volta per processo: su un log che scrive
#: centinaia di righe l'ora, ripeterlo sarebbe il rumore che fa ignorare gli
#: avvisi veri.
_DIVERGENZA_AVVISATA: bool = False


def _avvisa_se_diverge() -> None:
    """Dichiara quando il log finisce lontano dallo store in uso.

    ``EVENT_LOG_PATH`` è calcolato all'import: chi setta ``HIPPO_DATA_DIR``
    DOPO aver importato ottiene i fatti nella cartella isolata e gli eventi
    nel corpus di casa. È l'ordine fra import ed env a decidere, e finora
    nessuno lo diceva — la stessa causa per cui 210 fatti di laboratorio
    sono finiti in produzione (misurato 2026-08-05).

    Non sposta il file: cambiarlo a metà corsa spezzerebbe i lettori già
    attaccati, e la scelta di dove scrivere non è di questa funzione. Tace
    quando la divergenza è una scelta esplicita (``ENGRAM_EVENT_LOG``) e
    quando non c'è. Best-effort: non solleva mai.
    """
    global _DIVERGENZA_AVVISATA
    if _DIVERGENZA_AVVISATA or os.environ.get("ENGRAM_EVENT_LOG", "").strip():
        return
    try:
        from ._compat import data_dir
        atteso = Path(data_dir()) / "events.jsonl"
        if atteso.resolve() == EVENT_LOG_PATH.resolve():
            return
        _DIVERGENZA_AVVISATA = True
        import warnings
        warnings.warn(
            f"il log eventi scrive in {EVENT_LOG_PATH} mentre la data dir in "
            f"uso è {data_dir()}: i fatti e la loro telemetria stanno in due "
            f"posti diversi. Succede quando HIPPO_DATA_DIR è impostata DOPO "
            f"l'import di verimem (EVENT_LOG_PATH si fissa all'import). "
            f"Impostala prima, oppure dichiara ENGRAM_EVENT_LOG se la vuoi "
            f"davvero altrove.",
            RuntimeWarning, stacklevel=3)
    except Exception:  # noqa: BLE001 — un avviso non può rompere un emit
        pass


def append_event(
    name: str,
    payload: dict[str, Any],
    ts: float | None = None,
) -> None:
    """Append one event line to ``EVENT_LOG_PATH``.

    Safe da chiamare da qualunque processo: la dir parent viene creata
    se manca, errori I/O o di serializzazione vengono inghiottiti.
    """
    _avvisa_se_diverge()
    try:
        EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    _maybe_rotate()
    rec: dict[str, Any] = {
        "name": name,
        "payload": payload,
        "ts": ts if ts is not None else time.time(),
    }
    try:
        line = json.dumps(rec, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        # Payload con oggetti non serializzabili anche dopo default=str
        return
    try:
        with EVENT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        return


def tail_events(
    since_ts: float = 0.0,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Read events newer than ``since_ts``, up to ``limit`` records.

    Fallback per polling-mode quando il push SSE non basta (es. il
    browser ha perso la connessione). Restituisce gli ultimi ``limit``
    eventi con ``ts > since_ts``, in ordine di apparizione nel file.
    """
    if not EVENT_LOG_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        with EVENT_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if float(rec.get("ts", 0.0)) > since_ts:
                    out.append(rec)
    except OSError:
        return []
    return out[-limit:]


def log_size_bytes() -> int:
    """Return current log size in bytes — 0 if file missing."""
    try:
        return EVENT_LOG_PATH.stat().st_size
    except OSError:
        return 0


__all__ = ["EVENT_LOG_PATH", "append_event", "tail_events", "log_size_bytes"]
