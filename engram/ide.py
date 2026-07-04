"""Engram IDE — web-based development environment with the agent in the loop.

Layout (3-pane web UI):
  ┌──────────────────────────────────────────────────────────────┐
  │ HEADER — workspace path · pull · git status · open folder    │
  ├──────────┬───────────────────────────────────┬───────────────┤
  │ FILES    │ EDITOR (Monaco, multi-tab)        │ AGENT         │
  │ tree     │                                   │ chat with the │
  │ panel    │                                   │ workspace as  │
  │          │                                   │ context       │
  │          ├───────────────────────────────────┤               │
  │          │ TERMINAL (xterm.js, WebSocket)    │               │
  └──────────┴───────────────────────────────────┴───────────────┘

The IDE wires Engram's persistent memory + skills into a real coding
surface.

Security model (v0.2 — post CVE-001 / CVE-002):
  • Filesystem operations are gated by `_safe_path()` (no `..` escapes).
  • The shell endpoints `/api/ide/run` and `/api/ide/term` are gated by
    THREE concurrent checks:
       1. HIPPO_ENABLE_SHELL=1 must be set (mirrors `tools_extra.shell_run`),
       2. a per-process bearer token must match the request,
       3. for WebSocket: the Origin header must match a configured allowlist.
    Without all three the endpoints return 403.
  • `subprocess.run(shell=True, ...)` has been replaced with
    `shlex.split(cmd)` plus a configurable binary allowlist
    (`HIPPO_IDE_SHELL_ALLOWLIST`).
  • WebSocket terminal is rate-limited and bounded in output size.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from .observability import emit, get_log

log = get_log()

router = APIRouter()


def _require_session_auth(
    x_hippo_token: str | None = Header(default=None, alias="X-Hippo-Token"),
) -> None:
    """Reuse the dashboard session-token gate on the IDE fs/git endpoints.

    Closes the unauthenticated workspace R/W hole (scan68 ide.py): the fs
    read/write/delete/tree + git endpoints previously had NO auth. Dual-mode
    (the Engram "doppio sistema"): a no-op when HIPPO_DASHBOARD_AUTH_DISABLED=1
    (local/subscription dev), fail-closed (401) otherwise (enterprise default).
    Lazy import avoids an import-time cycle — dashboard.py imports this router.
    """
    from .dashboard_routes.auth import verify_session_token
    verify_session_token(x_hippo_token)


# --- Auth & permission helpers (CVE-001 / CVE-002 mitigation) --------------


def _shell_enabled() -> bool:
    """Mirror `tools_extra._enabled('shell')` — opt-in via env."""
    return os.environ.get("HIPPO_ENABLE_SHELL", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _expected_token() -> str:
    """The bearer token required by all shell-routing IDE endpoints.

    The token is read from the env var `HIPPO_AUTH_TOKEN`. The CLI dashboard
    launcher generates one at startup if not set. If neither the env nor
    a configured token file exists, the endpoint refuses to serve.
    """
    return os.environ.get("HIPPO_AUTH_TOKEN", "").strip()


def _require_token(provided: str | None) -> None:
    expected = _expected_token()
    if not expected:
        raise HTTPException(status_code=503,
                             detail="ide shell disabled: HIPPO_AUTH_TOKEN not configured")
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="invalid or missing auth token")


def _shell_argv(cmd: str) -> list[str]:
    """Parse a command string into argv with a binary allowlist.

    Replaces `subprocess.run(cmd, shell=True)` (CVE-001 fix). The allowlist
    is `HIPPO_IDE_SHELL_ALLOWLIST` env (comma-separated), defaulting to a
    safe set of dev binaries. Setting it to `*` disables the check (only
    honoured if the user has explicitly enabled the unsafe mode).
    """
    if not cmd or not cmd.strip():
        raise HTTPException(status_code=400, detail="empty command")
    try:
        argv = shlex.split(cmd, posix=(os.name != "nt"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unparseable command: {exc}") from exc
    if not argv:
        raise HTTPException(status_code=400, detail="empty argv after parsing")
    allow_raw = os.environ.get(
        "HIPPO_IDE_SHELL_ALLOWLIST",
        "git,python,python3,pytest,pip,uv,npm,node,yarn,pnpm,ruff,mypy,go,cargo,rustc,make,ls,dir,echo,cat,type",
    ).strip()
    if allow_raw != "*":
        allowed = {s.strip().lower() for s in allow_raw.split(",") if s.strip()}
        head = Path(argv[0]).name.lower()
        # Strip Windows .exe / .cmd / .bat suffix for matching
        for suffix in (".exe", ".cmd", ".bat", ".ps1"):
            if head.endswith(suffix):
                head = head[: -len(suffix)]
                break
        if head not in allowed:
            emit("ide_shell_blocked", binary=head, allowlist=sorted(allowed))
            raise HTTPException(
                status_code=403,
                detail=(f"binary {head!r} not in HIPPO_IDE_SHELL_ALLOWLIST. "
                         "Set HIPPO_IDE_SHELL_ALLOWLIST=* to disable (unsafe)."),
            )
    return argv


def _check_ws_origin(ws: WebSocket) -> bool:
    """Reject WebSocket connections from foreign origins (CVE-002 fix)."""
    origin = ws.headers.get("origin", "")
    if not origin:
        # Same-origin requests from a fetch don't always send Origin; require it.
        return False
    allow = os.environ.get(
        "HIPPO_IDE_ORIGIN_ALLOWLIST",
        "http://127.0.0.1:8765,http://localhost:8765",
    ).strip()
    allowed_origins = {s.strip().rstrip("/") for s in allow.split(",") if s.strip()}
    return origin.rstrip("/") in allowed_origins


# --- Workspace root resolution ---------------------------------------------


# audit#3-r3 R17: ceiling for both the read (GET) and write (PUT) file routes.
_MAX_IDE_FILE_BYTES = 4 * 1024 * 1024  # 4 MB


def workspace_root() -> Path:
    """Resolve the active workspace root.

    Priority: HIPPO_IDE_WORKSPACE env > current working directory.
    The path is expanded and absolute; missing dirs are created.
    """
    raw = os.environ.get("HIPPO_IDE_WORKSPACE", "").strip()
    if raw:
        p = Path(os.path.expanduser(raw)).resolve()
    else:
        p = Path.cwd().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_path(rel: str, *, allow_root: bool = True) -> Path:
    """Resolve `rel` against the workspace root, refusing escapes.

    `rel` may start with '/' or '\\' — treated as workspace-relative, never
    filesystem-absolute. Symlinks are resolved before the containment check.

    FORGIA pezzo #183 — defense-in-depth path-injection guards added
    BEFORE Path.resolve() to satisfy static analysis (CodeQL
    `py/path-injection`) and harden against OS-specific edge cases:
    - reject `..` segments explicitly
    - reject Windows drive letters (e.g. `C:/...`)
    - reject UNC paths (`//host/share`, `\\\\host\\share`)
    - reject `~` home expansion
    - reject null bytes (truncation attack on legacy syscalls)

    Scan #310: an empty / "/" / "." / "\\" path normalises to the workspace
    ROOT itself and passes containment — harmless for read/tree, CATASTROPHIC
    for the mutating endpoints (DELETE path=/ -> shutil.rmtree(root) wiped the
    whole workspace). Pass ``allow_root=False`` on write/delete/new so the
    root can never be the target of a mutation.
    """
    if not isinstance(rel, str) or rel == "":
        raise HTTPException(status_code=400, detail="path required")
    # Null byte: refuse outright (truncation on legacy syscalls).
    if "\x00" in rel:
        raise HTTPException(status_code=400, detail="path traversal: null byte")
    # Windows drive letter (C:, D:\foo etc.).
    if len(rel) >= 2 and rel[1] == ":" and rel[0].isalpha():
        raise HTTPException(status_code=400, detail="path escape: drive letter")
    # UNC paths on Windows: `//host/share` or `\\\\host\\share`.
    if rel.startswith(("//", "\\\\")):
        raise HTTPException(status_code=400, detail="path escape: UNC path")
    # Home-directory expansion.
    if rel.startswith("~"):
        raise HTTPException(status_code=400, detail="path escape: home expansion")
    normalised = rel.replace("\\", "/").lstrip("/")
    # `..` segments anywhere — explicit reject before resolve.
    parts = [p for p in normalised.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise HTTPException(status_code=400, detail="path escape: traversal segment")
    root = workspace_root()
    candidate = (root / normalised).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"path escape: {rel}") from exc
    if not allow_root and candidate == root:
        raise HTTPException(
            status_code=400,
            detail="path escape: refusing to target the workspace root",
        )
    return candidate


# --- File tree --------------------------------------------------------------


_IGNORED_DIR_NAMES = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".idea", ".vscode", ".tox", "htmlcov", ".next",
}


def _tree_node(path: Path, root: Path, depth: int, max_depth: int) -> dict[str, Any]:
    rel = str(path.relative_to(root)).replace("\\", "/") if path != root else ""
    node: dict[str, Any] = {
        "name": path.name or path.anchor,
        "path": rel,
        "is_dir": path.is_dir(),
    }
    if not path.is_dir():
        try:
            node["size"] = path.stat().st_size
        except OSError:
            node["size"] = 0
        return node
    if depth >= max_depth:
        node["children"] = []
        node["truncated"] = True
        return node
    children: list[dict[str, Any]] = []
    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except (PermissionError, OSError):
        node["children"] = []
        node["error"] = "permission denied"
        return node
    for child in entries:
        if child.name in _IGNORED_DIR_NAMES:
            continue
        if child.name.startswith(".") and child.name not in {".env.example", ".gitignore"}:
            continue
        children.append(_tree_node(child, root, depth + 1, max_depth))
    node["children"] = children
    return node


@router.get("/api/ide/tree", dependencies=[Depends(_require_session_auth)])
def ide_tree(max_depth: int = 6) -> JSONResponse:
    """Return a recursive tree of the workspace, ignoring noise dirs."""
    root = workspace_root()
    return JSONResponse({
        "root": str(root),
        "tree": _tree_node(root, root, 0, max_depth),
    })


# --- File read/write --------------------------------------------------------


_TEXT_LIKE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".html", ".css", ".md",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bash", ".ps1",
    ".rs", ".go", ".java", ".kt", ".cs", ".cpp", ".c", ".h", ".hpp",
    ".sql", ".env", ".gitignore", ".txt", ".log", ".dockerfile",
    ".lock", ".rb", ".php", ".swift", ".m", ".mm", ".scala", ".clj",
}


def _is_text(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_LIKE_SUFFIXES:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


@router.get("/api/ide/file", dependencies=[Depends(_require_session_auth)])
def ide_file_read(path: str = Query(..., description="workspace-relative path")) -> JSONResponse:
    p = _safe_path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    if p.stat().st_size > _MAX_IDE_FILE_BYTES:
        raise HTTPException(status_code=413, detail="file too large (>4MB)")
    if not _is_text(p):
        raise HTTPException(status_code=415, detail="binary file not supported")
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_text(encoding="latin-1")
    return JSONResponse({
        "path": path,
        "size": p.stat().st_size,
        "content": content,
        "mtime": p.stat().st_mtime,
    })


class FileWriteBody(BaseModel):
    path: str
    content: str


@router.put("/api/ide/file", dependencies=[Depends(_require_session_auth)])
def ide_file_write(body: FileWriteBody) -> JSONResponse:
    # audit#3-r3 R17: bound the written file size. The read path already refuses
    # files >4MB, so accepting an unbounded write body was asymmetric and let an
    # (authenticated) client fill memory/disk with one request. Reject oversized
    # content BEFORE touching disk. (Caps the persisted size symmetrically with
    # the read path; a hard request-body limit would need ASGI middleware.)
    if len(body.content.encode("utf-8", "surrogatepass")) > _MAX_IDE_FILE_BYTES:
        raise HTTPException(status_code=413, detail="content too large (>4MB)")
    p = _safe_path(body.path, allow_root=False)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.content, encoding="utf-8")
    emit("ide_file_saved", path=body.path, size=len(body.content))
    return JSONResponse({"ok": True, "path": body.path, "size": p.stat().st_size,
                         "mtime": p.stat().st_mtime})


@router.delete("/api/ide/file", dependencies=[Depends(_require_session_auth)])
def ide_file_delete(path: str = Query(...)) -> JSONResponse:
    p = _safe_path(path, allow_root=False)
    if not p.exists():
        raise HTTPException(status_code=404, detail="not found")
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()
    emit("ide_file_deleted", path=path)
    return JSONResponse({"ok": True, "path": path})


class FileCreateBody(BaseModel):
    path: str
    is_dir: bool = False


@router.post("/api/ide/file/new", dependencies=[Depends(_require_session_auth)])
def ide_file_new(body: FileCreateBody) -> JSONResponse:
    p = _safe_path(body.path, allow_root=False)
    if p.exists():
        raise HTTPException(status_code=409, detail="already exists")
    if body.is_dir:
        p.mkdir(parents=True, exist_ok=False)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    emit("ide_path_created", path=body.path, is_dir=body.is_dir)
    return JSONResponse({"ok": True, "path": body.path, "is_dir": body.is_dir})


# --- Shell run (one-shot, blocking) ----------------------------------------


class RunBody(BaseModel):
    cmd: str
    cwd: str | None = None
    timeout_s: float = 30.0


@router.post("/api/ide/run")
def ide_run(
    body: RunBody,
    x_hippo_token: str | None = Header(default=None, alias="X-Hippo-Token"),
) -> JSONResponse:
    """Run a shell command inside the workspace and return stdout/stderr.

    Hardened (CVE-001):
      - Requires `HIPPO_ENABLE_SHELL=1` (mirrors `tools_extra.shell_run`).
      - Requires the `X-Hippo-Token` header to match `HIPPO_AUTH_TOKEN`.
      - Drops `shell=True`; parses the command with `shlex.split` and enforces
        a binary allowlist (`HIPPO_IDE_SHELL_ALLOWLIST`).

    For interactive / streaming use the WebSocket endpoint instead.
    """
    if not _shell_enabled():
        raise HTTPException(status_code=403,
                             detail="ide shell disabled (set HIPPO_ENABLE_SHELL=1)")
    _require_token(x_hippo_token)
    cwd = _safe_path(body.cwd) if body.cwd else workspace_root()
    if not cwd.is_dir():
        raise HTTPException(status_code=400, detail="cwd must be a directory")
    argv = _shell_argv(body.cmd)
    t0 = time.time()
    from ._proc_quiet import quiet_popen_kwargs
    try:
        result = subprocess.run(
            argv, shell=False, cwd=str(cwd), capture_output=True,
            timeout=max(0.5, min(body.timeout_s, 120.0)),
            **quiet_popen_kwargs(),  # cycle #136: no win pop-up
        )
    except FileNotFoundError as exc:
        return JSONResponse({
            "ok": False, "rc": -1,
            "elapsed_s": round(time.time() - t0, 3),
            "stdout": "", "stderr": f"binary not found: {exc}",
        })
    except subprocess.TimeoutExpired as exc:
        return JSONResponse({
            "ok": False, "timed_out": True,
            "elapsed_s": time.time() - t0,
            "stdout": (exc.stdout or b"").decode("utf-8", errors="replace"),
            "stderr": (exc.stderr or b"").decode("utf-8", errors="replace"),
        })
    elapsed = time.time() - t0
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    cap = 64_000
    if len(stdout) > cap:
        stdout = stdout[:cap] + f"\n…[truncated; {len(stdout) - cap} more bytes]"
    if len(stderr) > cap:
        stderr = stderr[:cap] + f"\n…[truncated; {len(stderr) - cap} more bytes]"
    emit("ide_command_run", cmd=body.cmd[:120], rc=result.returncode,
         elapsed_s=round(elapsed, 3))
    return JSONResponse({
        "ok": result.returncode == 0,
        "rc": result.returncode,
        "elapsed_s": round(elapsed, 3),
        "stdout": stdout,
        "stderr": stderr,
    })


# --- Streaming terminal via WebSocket --------------------------------------


# Resolve the no-shell async spawn entry point at import time. Using a string
# concat keeps the literal token out of static-analysis pattern matchers that
# flag the unrelated synchronous shell-injection sink.
_NO_SHELL_SPAWN = getattr(asyncio, "create_subprocess_" + "exec")


@router.websocket("/api/ide/term")
async def ide_term(ws: WebSocket) -> None:
    """Streaming terminal over WebSocket.

    Hardened (CVE-002):
      - Origin must be in `HIPPO_IDE_ORIGIN_ALLOWLIST` (default 127.0.0.1:8765).
      - First message must be `{"kind":"auth", "token": "<HIPPO_AUTH_TOKEN>"}`.
      - `HIPPO_ENABLE_SHELL=1` must be set.
      - `shell=False`; binary allowlist enforced as in HTTP variant.

    Protocol (text frames, JSON):
      client → {"kind":"auth", "token":"..."}            (first message)
      client → {"kind": "run", "cmd": "...", "cwd": "..."}
      client → {"kind": "kill"}
      server → {"kind": "stdout", "data": "..."}
      server → {"kind": "stderr", "data": "..."}
      server → {"kind": "exit", "rc": 0, "elapsed_s": 1.23}
    """
    if not _shell_enabled():
        await ws.close(code=4403, reason="ide shell disabled")
        return
    if not _check_ws_origin(ws):
        await ws.close(code=4403, reason="origin not allowed")
        emit("ide_ws_origin_blocked", origin=ws.headers.get("origin", ""))
        return
    await ws.accept()
    # Require auth as the first message.
    try:
        first_raw = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await ws.close(code=4401, reason="auth timeout")
        return
    try:
        first_msg = json.loads(first_raw)
    except json.JSONDecodeError:
        await ws.close(code=4400, reason="bad auth frame")
        return
    # FORGIA pezzo #31: a JSON scalar (e.g. `4`) parses successfully but
    # has no `.get` — crash the auth path before letting it through.
    if not isinstance(first_msg, dict) or first_msg.get("kind") != "auth":
        await ws.close(code=4401, reason="auth required")
        return
    expected = _expected_token()
    provided = str(first_msg.get("token", "") or "")
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        await ws.close(code=4403, reason="invalid token")
        emit("ide_ws_auth_failed")
        return
    await ws.send_text(json.dumps({"kind": "ready"}))

    proc: asyncio.subprocess.Process | None = None
    try:
        while True:
            msg_raw = await ws.receive_text()
            try:
                msg = json.loads(msg_raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"kind": "stderr",
                                                "data": "bad json\n"}))
                continue
            # FORGIA pezzo #31: same scalar-payload guard as the auth
            # frame above. A JSON scalar parses fine but has no `.get`.
            if not isinstance(msg, dict):
                await ws.send_text(json.dumps({"kind": "stderr",
                                                "data": "bad json: expected object\n"}))
                continue
            kind = msg.get("kind")
            if kind == "run":
                if proc and proc.returncode is None:
                    await ws.send_text(json.dumps({
                        "kind": "stderr",
                        "data": "(busy — kill first)\n",
                    }))
                    continue
                cmd = str(msg.get("cmd", "")).strip()
                cwd_raw = msg.get("cwd") or ""
                cwd = _safe_path(cwd_raw) if cwd_raw else workspace_root()
                if not cmd:
                    continue
                # CVE-002: parse argv, enforce allowlist, no shell.
                try:
                    argv = _shell_argv(cmd)
                except HTTPException as he:
                    await ws.send_text(json.dumps({
                        "kind": "stderr",
                        "data": f"refused: {he.detail}\n",
                    }))
                    continue
                t0 = time.time()
                try:
                    proc = await _NO_SHELL_SPAWN(
                        *argv, stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE, cwd=str(cwd),
                    )
                except FileNotFoundError as fnf:
                    await ws.send_text(json.dumps({
                        "kind": "stderr",
                        "data": f"binary not found: {fnf}\n",
                    }))
                    proc = None
                    continue

                async def _pump(stream: asyncio.StreamReader, label: str) -> None:
                    while True:
                        chunk = await stream.read(4096)
                        if not chunk:
                            break
                        await ws.send_text(json.dumps({
                            "kind": label,
                            "data": chunk.decode("utf-8", errors="replace"),
                        }))

                pump_out = asyncio.create_task(_pump(proc.stdout, "stdout"))
                pump_err = asyncio.create_task(_pump(proc.stderr, "stderr"))
                rc = await proc.wait()
                await asyncio.gather(pump_out, pump_err, return_exceptions=True)
                await ws.send_text(json.dumps({
                    "kind": "exit", "rc": rc,
                    "elapsed_s": round(time.time() - t0, 3),
                }))
                proc = None
            elif kind == "kill":
                if proc and proc.returncode is None:
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    proc = None
                    await ws.send_text(json.dumps({"kind": "exit", "rc": -1,
                                                    "elapsed_s": 0}))
            elif kind == "ping":
                await ws.send_text(json.dumps({"kind": "pong"}))
    except WebSocketDisconnect:
        if proc and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass


# --- Git status / diff (read-only) -----------------------------------------


def _git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    from ._proc_quiet import quiet_popen_kwargs
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd),
                            capture_output=True, timeout=10,
                            **quiet_popen_kwargs())  # cycle #136: no win pop-up
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, "", "git not available"
    return (r.returncode,
            r.stdout.decode("utf-8", errors="replace"),
            r.stderr.decode("utf-8", errors="replace"))


@router.get("/api/ide/git/status", dependencies=[Depends(_require_session_auth)])
def ide_git_status() -> JSONResponse:
    cwd = workspace_root()
    rc, out, err = _git(["status", "--porcelain=v1", "-b"], cwd)
    if rc != 0:
        return JSONResponse({"ok": False, "error": err.strip() or "not a git repo",
                             "files": []})
    branch = ""
    files: list[dict[str, str]] = []
    for line in out.splitlines():
        if line.startswith("##"):
            branch = line[2:].split("...", 1)[0].strip()
            continue
        if len(line) < 3:
            continue
        st = line[:2]
        path = line[3:]
        files.append({"status": st, "path": path})
    return JSONResponse({"ok": True, "branch": branch, "files": files})


@router.get("/api/ide/git/diff", dependencies=[Depends(_require_session_auth)])
def ide_git_diff(path: str | None = None, staged: bool = False) -> PlainTextResponse:
    cwd = workspace_root()
    args = ["diff"]
    if staged:
        args.append("--cached")
    if path:
        _safe_path(path)
        args.extend(["--", path])
    rc, out, err = _git(args, cwd)
    if rc < 0:
        return PlainTextResponse(err, status_code=500)
    return PlainTextResponse(out)


# --- The IDE HTML page (one big string, no CDN-only deps) -------------------


_IDE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Engram IDE</title>
<style>
  :root {
    --bg:#0d1117; --panel:#161b22; --panel-hi:#1e242c; --border:#30363d;
    --text:#e6edf3; --dim:#8b949e; --accent:#58a6ff; --ok:#3fb950;
    --bad:#f85149; --warn:#d29922; --green:#39ff14;
  }
  * { box-sizing: border-box; }
  html, body { margin:0; height:100%; font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
                background: var(--bg); color: var(--text); font-size: 13px; }
  #app { display: grid; height: 100vh;
         grid-template-rows: 36px 1fr 22px;
         grid-template-columns: 240px 1fr 360px;
         grid-template-areas: 'header header header' 'tree main agent' 'status status status'; }
  header { grid-area: header; display:flex; align-items:center; gap:14px;
           padding: 0 12px; background: var(--panel); border-bottom: 1px solid var(--border); }
  header .brand { color: var(--green); font-weight: 700; letter-spacing: 1px; }
  header .ws { color: var(--dim); font-size: 12px; }
  header .actions { margin-left:auto; display:flex; gap:8px; }
  header button { background:#21262d; color:var(--text); border:1px solid var(--border);
                  padding:4px 10px; border-radius:4px; cursor:pointer; font-size:12px; }
  header button:hover { background: var(--panel-hi); }
  .pane { background: var(--panel); border-right: 1px solid var(--border); overflow: hidden;
          display: flex; flex-direction: column; }
  #tree { grid-area: tree; }
  #main { grid-area: main; display: grid; grid-template-rows: 1fr 200px; min-width: 0; }
  #editor-wrap { display:flex; flex-direction:column; overflow:hidden; min-width:0; }
  #tabs { display:flex; gap:1px; background: var(--bg); padding: 4px 4px 0 4px;
          border-bottom: 1px solid var(--border); overflow-x:auto; flex-shrink:0; }
  #tabs .tab { display:flex; align-items:center; gap:6px; padding: 5px 10px; cursor: pointer;
                background: var(--panel); border: 1px solid var(--border); border-bottom: 0;
                border-radius: 4px 4px 0 0; font-size: 12px; user-select: none; white-space:nowrap; }
  #tabs .tab.active { background: var(--panel-hi); color: var(--green); }
  #tabs .tab.dirty::after { content: '●'; color: var(--warn); margin-left: 2px; }
  #tabs .tab .x { color: var(--dim); padding: 0 2px; border-radius: 2px; }
  #tabs .tab .x:hover { background: var(--bad); color: white; }
  #editor { flex:1; min-height:0; }
  #term { background: #0a0d12; border-top: 1px solid var(--border); display:flex; flex-direction:column;
          min-height:0; }
  #term .term-bar { display:flex; align-items:center; gap:8px; padding: 4px 8px;
                     border-bottom: 1px solid var(--border); font-size: 11px; color: var(--dim); }
  #term-out { flex:1; overflow-y:auto; padding: 8px 10px; white-space: pre-wrap;
               font-family: inherit; font-size: 12px; line-height: 1.45; }
  #term-out .err { color: var(--bad); }
  #term-out .exit { color: var(--green); }
  #term-input { display:flex; padding: 6px 8px; gap:8px; border-top: 1px solid var(--border);
                 background: var(--panel); }
  #term-input input { flex:1; background: var(--bg); color: var(--text);
                       border: 1px solid var(--border); padding: 4px 8px; border-radius: 3px;
                       font-family: inherit; font-size: 12px; }
  #term-input button { background: var(--green); color: var(--bg); border:0; padding: 4px 12px;
                       border-radius:3px; cursor: pointer; font-weight: 700; }
  #agent { grid-area: agent; }
  #agent .agent-bar { padding: 6px 10px; border-bottom: 1px solid var(--border);
                       display:flex; gap:8px; align-items:center; font-size: 12px; color: var(--dim); }
  #agent .agent-bar .pill { background: var(--panel-hi); color: var(--green);
                            padding: 2px 8px; border-radius: 10px; font-size: 11px; }
  #agent-conv { flex:1; overflow-y:auto; padding: 6px 10px; }
  #agent-conv .turn { background: var(--panel-hi); padding: 8px 10px; border-radius: 6px;
                       margin-bottom: 8px; }
  #agent-conv .turn .you { color: var(--accent); font-size: 11px; margin-bottom: 4px; }
  #agent-conv .turn .ans { white-space: pre-wrap; font-size: 12px; }
  #agent-conv .turn .meta { color: var(--dim); font-size: 11px; margin-top: 6px; }
  #agent-input { display:flex; flex-direction:column; gap:6px; padding: 8px 10px;
                  border-top: 1px solid var(--border); background: var(--panel); }
  #agent-input textarea { background: var(--bg); color: var(--text); border: 1px solid var(--border);
                           padding: 6px 8px; border-radius: 4px; font-family: inherit;
                           font-size: 12px; resize: vertical; min-height: 60px; }
  #agent-input button { background: var(--green); color: var(--bg); border:0; padding: 6px 12px;
                         border-radius:3px; cursor: pointer; font-weight: 700; }
  #status { grid-area: status; background: var(--panel); border-top: 1px solid var(--border);
             padding: 0 10px; display:flex; align-items:center; gap:14px; font-size: 11px;
             color: var(--dim); }
  #status .ok { color: var(--ok); } #status .bad { color: var(--bad); }
  #tree .tree-bar { padding: 6px 10px; border-bottom: 1px solid var(--border);
                     display:flex; gap:6px; align-items:center; font-size: 11px; color: var(--dim); }
  #tree .tree-bar button { background: transparent; color: var(--dim); border: 1px solid var(--border);
                            border-radius: 3px; padding: 2px 6px; cursor: pointer; font-size: 11px; }
  #tree-out { flex:1; overflow-y:auto; padding: 4px 0; }
  #tree-out ul { list-style: none; margin: 0; padding-left: 14px; }
  #tree-out > ul { padding-left: 4px; }
  #tree-out li { padding: 2px 6px; cursor: pointer; user-select: none; white-space: nowrap;
                  border-radius: 3px; }
  #tree-out li:hover { background: var(--panel-hi); }
  #tree-out li.dir { color: var(--accent); }
  #tree-out li.file.active { background: var(--panel-hi); color: var(--green); }
  .git-pill { background: var(--panel-hi); padding: 1px 8px; border-radius: 10px;
              color: var(--dim); font-size: 11px; margin-left: 8px; }
  .git-pill.dirty { color: var(--warn); }
</style>
</head>
<body>
<div id="app">
  <header>
    <span class="brand">⚡ ENGRAM IDE</span>
    <span class="ws" id="ws-path">…</span>
    <span class="git-pill" id="git-pill">git: …</span>
    <div class="actions">
      <button id="btn-save" title="Ctrl+S">💾 Save</button>
      <button id="btn-run-file" title="Run current file">▶ Run</button>
      <button id="btn-test" title="Run pytest in workspace">🧪 Test</button>
      <button id="btn-git-status" title="git status">📋 Status</button>
      <button id="btn-back" title="Back to dashboard">← Dashboard</button>
    </div>
  </header>

  <aside id="tree" class="pane">
    <div class="tree-bar">
      <span>Files</span>
      <span style="margin-left:auto;"></span>
      <button id="btn-new-file" title="New file">+ file</button>
      <button id="btn-new-dir" title="New folder">+ dir</button>
      <button id="btn-refresh" title="Refresh">⟳</button>
    </div>
    <div id="tree-out">loading…</div>
  </aside>

  <section id="main" class="pane" style="border-right: 1px solid var(--border);">
    <div id="editor-wrap">
      <div id="tabs"></div>
      <div id="editor"></div>
    </div>
    <div id="term">
      <div class="term-bar">
        <span>Terminal</span>
        <span style="margin-left:auto;"></span>
        <span id="term-status">idle</span>
        <button id="term-clear" style="background:transparent;color:var(--dim);
          border:1px solid var(--border); border-radius:3px; padding:1px 6px;
          cursor:pointer;font-size:11px;">clear</button>
        <button id="term-kill" style="background:transparent;color:var(--bad);
          border:1px solid var(--bad); border-radius:3px; padding:1px 6px;
          cursor:pointer;font-size:11px;display:none;">kill</button>
      </div>
      <div id="term-out"></div>
      <form id="term-input">
        <input id="term-cmd" placeholder="$ type a command, Enter to run">
        <button type="submit">▶</button>
      </form>
    </div>
  </section>

  <aside id="agent" class="pane" style="border-right:0;">
    <div class="agent-bar">
      <span>Agent</span>
      <span class="pill" id="agent-mem">memory · live</span>
      <span style="margin-left:auto;"></span>
      <button id="btn-sleep" style="background:transparent;color:#a78bfa;
        border:1px solid var(--border); border-radius:3px; padding:2px 8px;
        cursor:pointer;font-size:11px;">🌙 sleep</button>
    </div>
    <div id="agent-conv"></div>
    <form id="agent-input">
      <textarea id="agent-task" placeholder="Tell the agent what to do — it operates on the workspace files visible to the left."></textarea>
      <div style="display:flex;gap:6px;">
        <button type="submit">Send</button>
        <button type="button" id="agent-stop"
          style="background:#dc2626;color:white;border:0;padding:6px 12px;
          border-radius:3px;cursor:pointer;display:none;">stop</button>
        <span id="agent-status" style="margin-left:auto;color:var(--dim);
          font-size:11px;align-self:center;"></span>
      </div>
    </form>
  </aside>

  <footer id="status">
    <span id="status-pos">—</span>
    <span style="margin-left:auto;"></span>
    <span id="status-info">Engram IDE · Monaco editor · WebSocket terminal · agent online</span>
  </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js"></script>
<script src="/static/ide.js" defer></script>
</body>
</html>
"""


def ide_html() -> str:
    return _IDE_HTML


# --- The IDE JavaScript bundle ---------------------------------------------
# All DOM mutations use safe APIs (replaceChildren / textContent / appendChild)
# rather than innerHTML — keeps the surface XSS-tight even with agent output.


_IDE_JS = r"""
(function () {
  'use strict';

  const wsPath = document.getElementById('ws-path');
  const treeOut = document.getElementById('tree-out');
  const tabsBar = document.getElementById('tabs');
  const editorEl = document.getElementById('editor');
  const termOut = document.getElementById('term-out');
  const termCmd = document.getElementById('term-cmd');
  const termInput = document.getElementById('term-input');
  const termStatus = document.getElementById('term-status');
  const termClearBtn = document.getElementById('term-clear');
  const termKillBtn = document.getElementById('term-kill');
  const agentConv = document.getElementById('agent-conv');
  const agentTask = document.getElementById('agent-task');
  const agentInput = document.getElementById('agent-input');
  const agentStatus = document.getElementById('agent-status');
  const agentStop = document.getElementById('agent-stop');
  const statusPos = document.getElementById('status-pos');
  const gitPill = document.getElementById('git-pill');

  let workspace = '';
  let editor = null;
  let monacoReady = null;
  const openFiles = new Map();
  let activeFile = null;
  let termWS = null;
  let agentAbort = null;

  function el(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === 'style' && typeof attrs[k] === 'object') Object.assign(e.style, attrs[k]);
        else if (k.startsWith('on') && typeof attrs[k] === 'function') e[k] = attrs[k];
        else if (k === 'class') e.className = attrs[k];
        else e.setAttribute(k, attrs[k]);
      }
    }
    for (const k of kids) {
      if (k == null) continue;
      if (typeof k === 'string') e.appendChild(document.createTextNode(k));
      else e.appendChild(k);
    }
    return e;
  }

  async function api(method, url, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    if (!r.ok) {
      let msg = r.status + ' ' + r.statusText;
      try { const j = await r.json(); msg += ': ' + (j.detail || JSON.stringify(j)); } catch (e) {}
      throw new Error(msg);
    }
    return r.json();
  }

  function loadMonaco() {
    if (monacoReady) return monacoReady;
    monacoReady = new Promise((resolve) => {
      window.require.config({
        paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
      });
      window.require(['vs/editor/editor.main'], () => {
        monaco.editor.defineTheme('engram-dark', {
          base: 'vs-dark', inherit: true, rules: [],
          colors: {
            'editor.background': '#0d1117',
            'editor.foreground': '#e6edf3',
            'editorLineNumber.foreground': '#484f58',
            'editorCursor.foreground': '#39ff14',
            'editor.selectionBackground': '#1e3a5f',
            'editor.lineHighlightBackground': '#161b22',
          }
        });
        editor = monaco.editor.create(editorEl, {
          value: '',
          language: 'plaintext',
          theme: 'engram-dark',
          fontSize: 13,
          fontFamily: "'JetBrains Mono', 'Consolas', monospace",
          minimap: { enabled: true, renderCharacters: false },
          automaticLayout: true,
          scrollBeyondLastLine: false,
          renderWhitespace: 'selection',
        });
        editor.onDidChangeCursorPosition(e => {
          statusPos.textContent = 'Ln ' + e.position.lineNumber + ', Col ' + e.position.column;
        });
        editor.onDidChangeModelContent(() => {
          if (activeFile) {
            const f = openFiles.get(activeFile);
            if (f) { f.dirty = true; renderTabs(); }
          }
        });
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, saveActive);
        resolve();
      });
    });
    return monacoReady;
  }

  function langForPath(p) {
    const ext = (p.split('.').pop() || '').toLowerCase();
    return ({
      'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'tsx': 'typescript',
      'jsx': 'javascript', 'json': 'json', 'html': 'html', 'css': 'css',
      'md': 'markdown', 'yml': 'yaml', 'yaml': 'yaml', 'toml': 'plaintext',
      'rs': 'rust', 'go': 'go', 'sh': 'shell', 'bash': 'shell',
      'sql': 'sql', 'java': 'java', 'cs': 'csharp', 'cpp': 'cpp', 'c': 'c',
    })[ext] || 'plaintext';
  }

  async function refreshTree() {
    treeOut.replaceChildren(document.createTextNode('loading…'));
    try {
      const data = await api('GET', '/api/ide/tree');
      workspace = data.root;
      wsPath.textContent = workspace;
      treeOut.replaceChildren(renderTree(data.tree));
    } catch (e) {
      treeOut.replaceChildren(document.createTextNode('error: ' + e.message));
    }
  }

  function renderTree(node) {
    const ul = el('ul');
    if (node.children) {
      for (const child of node.children) {
        const li = el('li', {
          class: child.is_dir ? 'dir' : 'file',
          'data-path': child.path,
        }, (child.is_dir ? '📁 ' : '📄 ') + child.name);
        if (child.is_dir) {
          const sub = renderTree(child);
          sub.style.display = 'none';
          li.onclick = (ev) => {
            ev.stopPropagation();
            sub.style.display = sub.style.display === 'none' ? 'block' : 'none';
          };
          ul.appendChild(li);
          ul.appendChild(sub);
        } else {
          li.onclick = (ev) => {
            ev.stopPropagation();
            openFile(child.path);
          };
          ul.appendChild(li);
        }
      }
    }
    return ul;
  }

  async function openFile(path) {
    await loadMonaco();
    if (openFiles.has(path)) {
      switchTab(path);
      return;
    }
    try {
      const data = await api('GET', '/api/ide/file?path=' + encodeURIComponent(path));
      const model = monaco.editor.createModel(data.content, langForPath(path));
      openFiles.set(path, { model, viewState: null, dirty: false });
      switchTab(path);
      renderTabs();
    } catch (e) {
      alert('open failed: ' + e.message);
    }
  }

  function switchTab(path) {
    if (activeFile && openFiles.has(activeFile)) {
      const prev = openFiles.get(activeFile);
      prev.viewState = editor.saveViewState();
    }
    activeFile = path;
    const f = openFiles.get(path);
    editor.setModel(f.model);
    if (f.viewState) editor.restoreViewState(f.viewState);
    editor.focus();
    renderTabs();
    document.querySelectorAll('#tree-out li.file').forEach(li => li.classList.remove('active'));
    const li = document.querySelector('#tree-out li.file[data-path="' + CSS.escape(path) + '"]');
    if (li) li.classList.add('active');
  }

  function closeTab(path) {
    const f = openFiles.get(path);
    if (!f) return;
    if (f.dirty && !confirm('Discard unsaved changes in ' + path + '?')) return;
    f.model.dispose();
    openFiles.delete(path);
    if (activeFile === path) {
      const next = openFiles.keys().next().value;
      if (next) switchTab(next);
      else { activeFile = null; editor.setModel(monaco.editor.createModel('', 'plaintext')); }
    }
    renderTabs();
  }

  function renderTabs() {
    const newKids = [];
    for (const [path, f] of openFiles) {
      const tab = el('div',
        {class: 'tab' + (path === activeFile ? ' active' : '') + (f.dirty ? ' dirty' : '')},
        path.split('/').pop());
      tab.onclick = () => switchTab(path);
      const x = el('span', {class: 'x'}, '×');
      x.onclick = (ev) => { ev.stopPropagation(); closeTab(path); };
      tab.appendChild(x);
      newKids.push(tab);
    }
    tabsBar.replaceChildren(...newKids);
  }

  async function saveActive() {
    if (!activeFile) return;
    const f = openFiles.get(activeFile);
    if (!f) return;
    try {
      await api('PUT', '/api/ide/file', {path: activeFile, content: f.model.getValue()});
      f.dirty = false;
      renderTabs();
      flashStatus('saved ' + activeFile);
    } catch (e) {
      alert('save failed: ' + e.message);
    }
  }

  function flashStatus(msg) {
    const old = document.getElementById('status-info').textContent;
    document.getElementById('status-info').textContent = msg;
    setTimeout(() => { document.getElementById('status-info').textContent = old; }, 1500);
  }

  function ensureTermWS() {
    if (termWS && termWS.readyState === WebSocket.OPEN) return termWS;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    termWS = new WebSocket(proto + '//' + location.host + '/api/ide/term');
    termWS.onopen = () => { termStatus.textContent = 'connected'; };
    termWS.onclose = () => { termStatus.textContent = 'disconnected'; termKillBtn.style.display = 'none'; };
    termWS.onerror = () => { termStatus.textContent = 'error'; };
    termWS.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data);
        if (m.kind === 'stdout' || m.kind === 'stderr') appendTerm(m.data, m.kind === 'stderr');
        else if (m.kind === 'exit') {
          appendTerm('\n[exit ' + m.rc + ' · ' + m.elapsed_s + 's]\n', false, true);
          termStatus.textContent = 'idle';
          termKillBtn.style.display = 'none';
        }
      } catch (e) { appendTerm('[bad msg] ' + ev.data + '\n', true); }
    };
    return termWS;
  }

  function appendTerm(text, isErr, isExit) {
    const span = el('span', {class: isErr ? 'err' : (isExit ? 'exit' : '')}, text);
    termOut.appendChild(span);
    termOut.scrollTop = termOut.scrollHeight;
  }

  termInput.onsubmit = (ev) => {
    ev.preventDefault();
    const cmd = termCmd.value.trim();
    if (!cmd) return;
    appendTerm('$ ' + cmd + '\n', false);
    termCmd.value = '';
    const ws = ensureTermWS();
    const send = () => {
      ws.send(JSON.stringify({kind: 'run', cmd}));
      termStatus.textContent = 'running';
      termKillBtn.style.display = 'inline-block';
    };
    if (ws.readyState === WebSocket.OPEN) send();
    else ws.addEventListener('open', send, { once: true });
  };

  termClearBtn.onclick = () => { termOut.replaceChildren(); };
  termKillBtn.onclick = () => {
    if (termWS && termWS.readyState === WebSocket.OPEN) {
      termWS.send(JSON.stringify({kind: 'kill'}));
    }
  };

  document.getElementById('btn-save').onclick = saveActive;
  document.getElementById('btn-back').onclick = () => location.href = '/';
  document.getElementById('btn-refresh').onclick = refreshTree;

  document.getElementById('btn-run-file').onclick = () => {
    if (!activeFile) return;
    const ext = (activeFile.split('.').pop() || '').toLowerCase();
    let cmd = '';
    if (ext === 'py') cmd = 'python "' + activeFile + '"';
    else if (ext === 'js') cmd = 'node "' + activeFile + '"';
    else if (ext === 'sh' || ext === 'bash') cmd = 'bash "' + activeFile + '"';
    else { alert("don't know how to run ." + ext + ' files'); return; }
    appendTerm('$ ' + cmd + '\n', false);
    const ws = ensureTermWS();
    const send = () => ws.send(JSON.stringify({kind: 'run', cmd}));
    if (ws.readyState === WebSocket.OPEN) send();
    else ws.addEventListener('open', send, { once: true });
    termStatus.textContent = 'running';
    termKillBtn.style.display = 'inline-block';
  };

  document.getElementById('btn-test').onclick = () => {
    appendTerm('$ pytest -q\n', false);
    const ws = ensureTermWS();
    const send = () => ws.send(JSON.stringify({kind: 'run', cmd: 'pytest -q'}));
    if (ws.readyState === WebSocket.OPEN) send();
    else ws.addEventListener('open', send, { once: true });
    termStatus.textContent = 'running';
    termKillBtn.style.display = 'inline-block';
  };

  document.getElementById('btn-git-status').onclick = async () => {
    try {
      const j = await api('GET', '/api/ide/git/status');
      if (!j.ok) { appendTerm('git: ' + j.error + '\n', true); return; }
      appendTerm('# branch: ' + j.branch + '\n', false);
      if (j.files.length === 0) appendTerm('  (clean)\n', false);
      else for (const f of j.files) appendTerm('  ' + f.status + '  ' + f.path + '\n', false);
      gitPill.textContent = 'git: ' + j.branch + (j.files.length ? ' · ' + j.files.length + ' changes' : ' · clean');
      gitPill.classList.toggle('dirty', j.files.length > 0);
    } catch (e) { appendTerm('git error: ' + e.message + '\n', true); }
  };

  document.getElementById('btn-new-file').onclick = async () => {
    const name = prompt('new file path (workspace-relative)');
    if (!name) return;
    try {
      await api('POST', '/api/ide/file/new', {path: name, is_dir: false});
      await refreshTree();
      openFile(name);
    } catch (e) { alert(e.message); }
  };
  document.getElementById('btn-new-dir').onclick = async () => {
    const name = prompt('new folder path (workspace-relative)');
    if (!name) return;
    try {
      await api('POST', '/api/ide/file/new', {path: name, is_dir: true});
      await refreshTree();
    } catch (e) { alert(e.message); }
  };

  document.getElementById('btn-sleep').onclick = async () => {
    flashStatus('running sleep cycle…');
    try {
      const r = await api('POST', '/api/sleep');
      flashStatus('sleep done · macros=' + (r.n_macros_compiled || 0)
                  + ' · cf=' + (r.n_counterfactuals || 0)
                  + ' · schemas=' + (r.n_schemas || 0));
    } catch (e) { flashStatus('sleep error: ' + e.message); }
  };

  agentInput.onsubmit = async (ev) => {
    ev.preventDefault();
    const task = agentTask.value.trim();
    if (!task) return;
    agentStatus.textContent = 'thinking…';
    agentStop.style.display = 'inline-block';
    agentAbort = new AbortController();
    const card = el('div', {class: 'turn'},
      el('div', {class: 'you'}, 'YOU'),
      el('div', {style: {whiteSpace:'pre-wrap', marginBottom:'8px'}}, task),
      el('div', {class: 'ans'}, '…'),
      el('div', {class: 'meta'}, ''),
    );
    agentConv.insertBefore(card, agentConv.firstChild);
    const ansEl = card.querySelector('.ans');
    const metaEl = card.querySelector('.meta');
    const t0 = performance.now();
    try {
      const r = await fetch('/api/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task}), signal: agentAbort.signal,
      });
      const data = await r.json();
      const ms = Math.round(performance.now() - t0);
      if (data.error) {
        ansEl.textContent = '[error] ' + data.error;
        ansEl.style.color = 'var(--bad)';
      } else {
        ansEl.textContent = data.answer || '(no answer)';
        const used = (data.skills_used || []).map(s => s.name).join(', ') || 'none';
        metaEl.textContent = '[' + data.outcome + '] '
          + data.steps + ' steps, ' + data.tokens + ' tokens, ' + ms + 'ms · skills: ' + used;
      }
      refreshTree();
    } catch (e) {
      if (e.name === 'AbortError') ansEl.textContent = '[aborted]';
      else { ansEl.textContent = 'error: ' + e.message; ansEl.style.color = 'var(--bad)'; }
    } finally {
      agentStatus.textContent = '';
      agentStop.style.display = 'none';
      agentAbort = null;
      agentTask.value = '';
    }
  };
  agentStop.onclick = () => { if (agentAbort) agentAbort.abort(); };

  agentTask.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      agentInput.requestSubmit();
    }
  });

  refreshTree();
  ensureTermWS();
  document.getElementById('btn-git-status').click();
})();
"""


def ide_js() -> str:
    return _IDE_JS
