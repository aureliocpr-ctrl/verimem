"""Shared embedding-encode service (one warm model for many processes).

Why this exists
---------------
`sentence-transformers` costs ~20s to load per process. Each of the N hippo
MCP servers loads its own copy (~500 MB RAM each → multi-GB), and every fresh
`clp` CLI invocation that needs an embedding pays the full ~20s cold load.

This service loads the PRODUCTION encoder (``CONFIG.embedding_model``) ONCE and
answers encode requests over a localhost TCP socket. ``engram.embedding.encode``
tries this service first and falls back to an in-process load if the service is
unreachable — so the service is a pure optimisation, never a hard dependency.

It produces the SAME vectors as the in-process path (same model, same
``normalize_embeddings=True``), so results stay comparable to the embeddings
already stored in ``semantic.db``.

Protocol (length-prefixed JSON, big-endian uint32 frame length):
  REQ:  {"text": "..."}              ->  RESP {"ok": true, "vec": [384 floats]}
  REQ:  {"texts": ["a", "b"]}        ->  RESP {"ok": true, "vecs": [[...],[...]]}
  REQ:  {"ping": true}               ->  RESP {"ok": true, "model": "...", "pid": N}
  on error:                              RESP {"ok": false, "error": "..."}

Discovery file ``~/.engram/encode_service.json`` ({pid, port, model,
started_at}) lets clients find the port. The server idle-exits after
``IDLE_TIMEOUT_S`` so it never lingers forever.
"""
from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

DISCOVERY_PATH = Path.home() / ".engram" / "encode_service.json"


def _idle_timeout_s() -> float:
    """Seconds of inactivity before the daemon self-exits.

    The legacy 30-min default was the root of the 2026-06-05 "Engram hangs on
    save/recall" incident: the daemon idle-died mid-session, so the next
    store()/recall() cold-loaded the model in-process (~22s measured). Default
    now 8h — survives a work session, still cleans up overnight. Override with
    ``ENGRAM_ENCODE_IDLE_S`` (``0`` = never idle-exit / permanent daemon).
    """
    raw = os.environ.get("ENGRAM_ENCODE_IDLE_S", "").strip()
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return 8 * 3600.0  # 8 hours


IDLE_TIMEOUT_S = _idle_timeout_s()
_MAX_FRAME = 8 * 1024 * 1024  # 8 MB guard against bogus length headers


def _recvall(conn: socket.socket, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def recv_msg(conn: socket.socket) -> dict | None:
    """Read one length-prefixed JSON message. None on clean EOF."""
    hdr = _recvall(conn, 4)
    if hdr is None:
        return None
    (length,) = struct.unpack(">I", hdr)
    if length <= 0 or length > _MAX_FRAME:
        raise ValueError(f"bad frame length {length}")
    body = _recvall(conn, length)
    if body is None:
        return None
    return json.loads(body.decode("utf-8"))


def send_msg(conn: socket.socket, obj: dict) -> None:
    data = json.dumps(obj).encode("utf-8")
    conn.sendall(struct.pack(">I", len(data)) + data)


def read_discovery(path: Path | None = None) -> dict | None:
    """Return the running service's discovery info, or None if absent/unparseable.

    Does NOT verify the process is alive — clients detect a dead daemon via a
    failed connect and fall back to in-process encoding.
    """
    p = path or DISCOVERY_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _default_encode_fn(text: str):
    # In-process encode via the LOCAL path (never the service) so the server
    # does not recurse into itself. Same model + normalisation as the fallback,
    # so vectors are identical to what clients would compute in-process.
    from . import embedding

    return embedding._encode_local(text)


class EncodeServer:
    """Threaded localhost encode server. ``encode_fn`` is injectable for tests."""

    def __init__(
        self,
        encode_fn: Callable[[str], object] | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        idle_timeout_s: float = IDLE_TIMEOUT_S,
        discovery_path: Path | None = None,
        model_name: str = "",
        model_dim: int = 0,
    ) -> None:
        self._encode_fn = encode_fn or _default_encode_fn
        self._host = host
        self._port = port
        self._idle_timeout_s = idle_timeout_s
        self._discovery_path = discovery_path or DISCOVERY_PATH
        self._model_name = model_name
        # Additive (2026-06-03): advertise the vector dim alongside the model
        # name so a client can verify BOTH before trusting the daemon (a model
        # with the same name but different dim would be a misconfig). 0 = unknown.
        self._model_dim = model_dim
        self._sock: socket.socket | None = None
        self._last_request = time.time()
        self._lock = threading.Lock()
        self._stop = threading.Event()

    @property
    def port(self) -> int:
        return self._sock.getsockname()[1] if self._sock else self._port

    def _touch(self) -> None:
        with self._lock:
            self._last_request = time.time()

    def _idle_for(self) -> float:
        with self._lock:
            return time.time() - self._last_request

    def _to_list(self, vec) -> list:
        return [float(x) for x in vec]

    def _handle_request(self, req: dict) -> dict:
        if req.get("ping"):
            return {
                "ok": True, "model": self._model_name,
                "dim": self._model_dim, "pid": os.getpid(),
            }
        if "texts" in req:
            vecs = [self._to_list(self._encode_fn(t)) for t in req["texts"]]
            return {"ok": True, "vecs": vecs}
        if "text" in req:
            return {"ok": True, "vec": self._to_list(self._encode_fn(req["text"]))}
        return {"ok": False, "error": "request must contain 'text', 'texts', or 'ping'"}

    def _serve_conn(self, conn: socket.socket) -> None:
        with conn:
            while not self._stop.is_set():
                try:
                    req = recv_msg(conn)
                except (ValueError, json.JSONDecodeError) as exc:
                    try:
                        send_msg(conn, {"ok": False, "error": str(exc)})
                    except OSError:
                        pass
                    return
                if req is None:
                    return
                self._touch()
                try:
                    resp = self._handle_request(req)
                except Exception as exc:  # noqa: BLE001 — never kill the server
                    resp = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                try:
                    send_msg(conn, resp)
                except OSError:
                    return

    def _write_discovery(self) -> None:
        self._discovery_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._discovery_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({
                "pid": os.getpid(),
                "port": self.port,
                "host": self._host,
                "model": self._model_name,
                "dim": self._model_dim,
                "started_at": time.time(),
            }),
            encoding="utf-8",
        )
        tmp.replace(self._discovery_path)

    def _clear_discovery(self) -> None:
        try:
            data = json.loads(self._discovery_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if data.get("pid") == os.getpid():
            try:
                self._discovery_path.unlink()
            except OSError:
                pass

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self._host, self._port))
        self._sock.listen(16)
        self._sock.settimeout(1.0)
        self._write_discovery()

    def serve_forever(self) -> None:
        if self._sock is None:
            self.start()
        try:
            while not self._stop.is_set():
                try:
                    conn, _ = self._sock.accept()
                except TimeoutError:
                    if self._idle_for() > self._idle_timeout_s:
                        break
                    continue
                except OSError:
                    break
                threading.Thread(
                    target=self._serve_conn, args=(conn,), daemon=True,
                ).start()
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop.set()
        self._clear_discovery()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


# --- Auto-spawn (lazy, windowless) -----------------------------------------
_SPAWN_LOCK_PATH = Path.home() / ".engram" / "encode_service.spawn.lock"
_SPAWN_COOLDOWN_S = 60.0

# --- Daemon singleton lock (2026-07-10 RAM incident) -------------------------
# The spawn cooldown above narrows the window but cannot close it: at machine
# boot N MCP servers call ensure_running() within milliseconds, two daemons
# start, and BOTH load the ~GB model before either writes discovery — the
# loser then lingers idle for hours at full weight (measured: 2 × 1.9 GB).
# The daemon itself must be the arbiter: take an atomic pid lock BEFORE the
# model load and exit cheaply if another live daemon holds it.
DAEMON_LOCK_PATH = Path.home() / ".engram" / "encode_service.daemon.lock"


def _pid_alive(pid: int) -> bool:
    """Best-effort liveness. Unknown/odd states err on 'alive' — a false
    'alive' only makes a daemon defer (cheap); a false 'dead' would let two
    daemons load the model (the incident).

    NOT ``os.kill(pid, 0)`` on Windows: ``signal.CTRL_C_EVENT == 0``, so
    CPython routes ``os.kill(pid, 0)`` to ``GenerateConsoleCtrlEvent(
    CTRL_C_EVENT, pid)`` — a Ctrl-C to the console PROCESS GROUP the caller
    shares. It bounced back as a KeyboardInterrupt that killed the windows CI
    suite at ~66% intermittently (root-caused 2026-07-16). Windows uses an
    OpenProcess/exit-code probe instead; POSIX keeps the signal-0 idiom."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _pid_alive_windows(pid: int) -> bool:
    """Windows liveness via the Win32 API — never sends a console control event
    (see ``_pid_alive``). ``OpenProcess`` failing with ACCESS_DENIED means the
    process exists but is not queryable (alive); ``GetExitCodeProcess`` returning
    ``STILL_ACTIVE`` (259) means running. Unknown states err on 'alive'."""
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259
    _ERROR_ACCESS_DENIED = 5
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # not found -> dead; access-denied -> exists but opaque -> alive
        return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True  # can't read the exit code -> err on 'alive'
        return code.value == _STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _read_lock_owner(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


# Empty-lock grace: the O_EXCL winner creates the file THEN writes its pid;
# a reader in that gap must WAIT, not steal (the observed double-daemon race:
# both at 1.9 GB, lock owned by the thief). Verify delay: after any write we
# read back — concurrent stealers all write, only the LAST keeps the lock, so
# exactly one process ever loads the model.
_LOCK_STEAL_GRACE_S = 0.25
_LOCK_VERIFY_DELAY_S = 0.10


def acquire_daemon_lock(lock_path: Path | None = None) -> bool:
    """Atomically claim the one-daemon-per-machine lock.

    True → this process may load the model and serve. False → another LIVE
    daemon owns it; exit before paying the load. A dead owner's lock is
    stolen; our own pid is re-entrant (restart within one process)."""
    path = lock_path or DAEMON_LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    me = str(os.getpid())
    claimed = False
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, me.encode("ascii"))
        finally:
            os.close(fd)
        claimed = True
    except FileExistsError:
        pass
    except OSError:
        # Unwritable lock dir: do not brick encoding on a fs quirk — serve.
        return True
    if not claimed:
        owner = _read_lock_owner(path)
        if owner == os.getpid():
            return True
        # Empty pid → a winner may be between open and write. Grace-wait for
        # the pid to land before declaring the lock garbage.
        deadline = time.time() + _LOCK_STEAL_GRACE_S
        while owner == 0 and time.time() < deadline:
            time.sleep(0.03)
            owner = _read_lock_owner(path)
        if owner == os.getpid():
            return True
        if owner and _pid_alive(owner):
            return False
        # dead (or persistently empty) owner → steal
        try:
            path.write_text(me, encoding="utf-8")
        except OSError:
            return False
    # Verify-readback: with concurrent claimants the LAST writer wins and
    # everyone else yields here — never two model loads.
    time.sleep(_LOCK_VERIFY_DELAY_S)
    return _read_lock_owner(path) == os.getpid()


def release_daemon_lock(lock_path: Path | None = None) -> None:
    """Remove the lock iff THIS process owns it (never someone else's)."""
    path = lock_path or DAEMON_LOCK_PATH
    try:
        if path.read_text(encoding="utf-8").strip() == str(os.getpid()):
            path.unlink()
    except (OSError, ValueError):
        pass


def is_reachable(info: dict | None = None, timeout: float = 0.4) -> bool:
    """True if a daemon is listening per the discovery file (or given info)."""
    info = info if info is not None else read_discovery()
    if not info or not info.get("port"):
        return False
    try:
        conn = socket.create_connection(
            (info.get("host", "127.0.0.1"), info["port"]), timeout=timeout,
        )
        conn.close()
        return True
    except OSError:
        return False


def daemon_usable(info: dict | None = None, timeout: float = 0.4) -> bool:
    """True iff a daemon is reachable AND advertises ``CONFIG.embedding_model``.

    The cold-hang fix (2026-06-05): ``is_reachable`` is MODEL-BLIND, but
    ``embedding._encode_via_service`` rejects a daemon whose model != CONFIG
    (a same-dim wrong-model daemon would silently poison the corpus). Using
    ``is_reachable`` to decide "a daemon is up, skip warming this process"
    (preload) therefore disagreed with what encode actually does: across a
    model switch (e.g. the e5 flip) a stale daemon left preload skipping the
    local warm AND every encode cold-loading in-process (~20s on the request
    thread). This is the single source of truth both sides must use.
    """
    from .config import CONFIG

    info = info if info is not None else read_discovery()
    if not info or info.get("model") != CONFIG.embedding_model:
        return False
    return is_reachable(info, timeout=timeout)


def _spawn_detached() -> None:
    """Spawn the daemon in a DETACHED, windowless process (no console flash).

    Uses pythonw.exe on Windows + DETACHED_PROCESS|CREATE_NO_WINDOW so no black
    shell appears (the lesson from the earlier daemon black-shell incident)."""
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pyw) if pyw.exists() else sys.executable
    creationflags = 0
    if os.name == "nt":
        creationflags = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen(
        [exe, "-m", "engram.encode_service"],
        creationflags=creationflags,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True,
    )


def ensure_running() -> bool:
    """Ensure the shared encode daemon is up; spawn it (windowless) if not.

    Returns True if already reachable. If a spawn is triggered it returns False
    (the daemon needs ~20s to warm — callers fall back to in-process meanwhile).
    A lock-file cooldown means concurrent callers (the N MCP servers + CLI)
    spawn at most one daemon. Disabled by ENGRAM_ENCODE_SERVICE=0."""
    if os.environ.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower() in (
        "0", "false", "no", "off",
    ):
        return False
    if daemon_usable():
        return True
    # MODEL-AWARE gate (review 2026-06-20): use daemon_usable (reachable AND advertises
    # CONFIG.embedding_model), NOT the model-blind is_reachable. A stale WRONG-MODEL daemon
    # (e.g. left after an embedding-model switch) is reachable but rejected by
    # _encode_via_service, so gating spawn on is_reachable made ensure_running think "a
    # daemon is up" and never spawn the correct one — every encode then cold-loaded
    # in-process (~20s). daemon_usable is the single source of truth both sides must use.
    # Not usable but a discovery file may linger from a dead/wrong daemon — remove
    # it so clients stop fast-failing against a dead port while a fresh daemon
    # warms (the new daemon rewrites discovery once it is up).
    try:
        DISCOVERY_PATH.unlink()
    except OSError:
        pass
    try:
        if (_SPAWN_LOCK_PATH.exists()
                and time.time() - _SPAWN_LOCK_PATH.stat().st_mtime < _SPAWN_COOLDOWN_S):
            return False  # someone spawned recently; let it finish warming
    except OSError:
        pass
    try:
        _SPAWN_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SPAWN_LOCK_PATH.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass
    try:
        _spawn_detached()
    except Exception:  # noqa: BLE001 — spawn failure must not break callers
        return False
    return False


def main() -> None:
    # Singleton gate FIRST — before the ~GB model load, so a spawn-race loser
    # costs ~50 MB of interpreter for a moment, not 1.9 GB for 8 idle hours.
    if not acquire_daemon_lock():
        return
    try:
        from . import embedding
        from .config import CONFIG

        # Warm the model BEFORE advertising via the discovery file, so any
        # client that finds the file knows the daemon is ready.
        embedding._encode_local("warmup")
        EncodeServer(
            model_name=CONFIG.embedding_model,
            model_dim=CONFIG.embedding_dim,
        ).serve_forever()
    finally:
        release_daemon_lock()


if __name__ == "__main__":
    main()
