"""Extra tools that extend the agent's reach beyond Python execution.

Categories:
  - File system: read/write/list/search files. Sandboxed to a configurable root.
  - Web: fetch a URL, get readable text/HTML.
  - Vision: describe an image via a multimodal LLM.
  - Webcam: snap a frame from the default camera and (optionally) describe it.
  - Desktop: screenshot, click, type, key — full computer use.

Safety model:
  - Each capability is OPT-IN via env or settings. By default only file-system
    (within data dir) and web fetch are enabled. Computer-use, webcam, and
    arbitrary file system access require explicit toggle.
  - Every dangerous action emits an observability event before executing.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path

import httpcore
import httpx

from .config import CONFIG
from .observability import emit, get_log
from .tools import ToolResult, ToolSpec

log = get_log()


# ---------------------------------------------------------------------------
# Capability flags — read once per call so settings changes apply live.
# ---------------------------------------------------------------------------


def _enabled(name: str, default: bool = False) -> bool:
    return os.environ.get(f"HIPPO_ENABLE_{name.upper()}", "").strip().lower() in (
        "1", "true", "yes", "on",
    ) or (default and os.environ.get(f"HIPPO_DISABLE_{name.upper()}", "").strip().lower()
          not in ("1", "true", "yes", "on"))


def _fs_roots() -> list[Path]:
    """Allowed roots for filesystem ops.

    Default policy (v0.2): STRICT — only the project data dir. The previous
    permissive `$HOME` default exposed `~/.ssh`, `~/.aws`, `~/.gnupg`,
    browser profiles, and IDE configs to the LLM (CVE-003 / SEC V4).

    Lock down via:
      • HIPPO_FS_ROOT=/some/path    → single explicit root, only there
      • (default)                    → strict (data dir only)

    Opt out via UI (`UserSettings.perm_filesystem`):
      • "strict"  → data dir only (default, this is what apply_to_env sets
                    via HIPPO_FS_STRICT=1)
      • "home"    → user home + data dir (HIPPO_FS_HOME=1)
      • "full"    → root drive (HIPPO_FS_ROOT=/ or C:\\)
    """
    custom = os.environ.get("HIPPO_FS_ROOT", "").strip()
    if custom:
        return [Path(custom).resolve()]

    # Permissive home scope (opt-in).
    if os.environ.get("HIPPO_FS_HOME", "").strip().lower() in ("1", "true", "yes", "on"):
        home = Path.home().resolve()
        return [home, CONFIG.data_dir.resolve()]

    # Default: strict — data dir only. Even if HIPPO_FS_STRICT is unset, we
    # remain strict (V4 fix). Setting HIPPO_FS_STRICT=1 explicitly is also
    # honoured (idempotent).
    return [CONFIG.data_dir.resolve()]


# Sensitive paths that are never readable/writable, regardless of root scope.
# Applied as suffix-match against the resolved path (case-insensitive on Win).
_SENSITIVE_SUBPATHS: tuple[str, ...] = (
    ".ssh", ".aws", ".gnupg", ".docker", ".kube", ".azure",
    "credentials", "credentials.json", ".env", ".netrc",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "user_settings.json", "secrets.json",
)


def _strip_editor_backup_suffixes(name: str) -> str:
    """Strip editor backup/swap suffixes so `.env~` matches like `.env`.

    Covers Vim/Emacs/general patterns:
      - trailing `~` (Vim/Emacs)
      - `.bak`, `.backup`, `.old`, `.orig`, `.swp`, `.swo`, `.tmp`
      - leading `#...#` (Emacs autosave) and `.#...` (Emacs lockfile)
      - `.save` (nano)
    Repeats until stable so combos like `.env.bak~` collapse to `.env`.
    """
    if not name:
        return name
    suffixes = (".bak", ".backup", ".old", ".orig", ".swp", ".swo",
                ".tmp", ".save")
    prev = None
    while name and name != prev:
        prev = name
        # Trailing tilde
        if name.endswith("~"):
            name = name[:-1]
            continue
        # Trailing common backup extensions (case-insensitive on Windows)
        for s in suffixes:
            cmp = name.lower() if os.name == "nt" else name
            if cmp.endswith(s):
                name = name[: -len(s)]
                break
        else:
            # Emacs autosave  #foo#  →  foo
            if name.startswith("#") and name.endswith("#") and len(name) > 2:
                name = name[1:-1]
                continue
            # Emacs lockfile  .#foo  →  foo
            if name.startswith(".#") and len(name) > 2:
                name = name[2:]
                continue
            break
    return name


def _is_sensitive(path: Path) -> bool:
    """Return True if `path` resolves under (or matches) a known-sensitive name."""
    try:
        parts = path.resolve().parts
    except OSError:
        return False
    norm = tuple(p.lower() if os.name == "nt" else p for p in parts)
    needles = tuple(s.lower() if os.name == "nt" else s for s in _SENSITIVE_SUBPATHS)
    for part in norm:
        if part in needles:
            return True
    # filename match — also strip editor backup suffixes (.env~, .env.bak, #.env#)
    name = norm[-1] if norm else ""
    stripped = _strip_editor_backup_suffixes(name)
    if stripped in needles:
        return True
    # rescan2 fix 2026-06-02 (NONNA): famiglia dotenv (secrets/exports). Il match
    # ESATTO bloccava solo '.env' ma NON '.env.local'/'.env.production'/'prod.env'
    # -> leak. Copriamo la CLASSE: .env, .env.<stage>, *.env, .envrc.
    if (stripped == ".env" or stripped.startswith(".env.")
            or stripped.endswith(".env") or stripped == ".envrc"):
        return True
    # filename ends with .pem/.key (case-insensitive on Windows already via norm)
    if name.endswith(".pem") or name.endswith(".key"):
        return True
    if stripped.endswith(".pem") or stripped.endswith(".key"):
        return True
    return False


def _is_within_any(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------------------
# File system
# ---------------------------------------------------------------------------


def fs_read_file(path: str, max_bytes: int = 32768) -> ToolResult:
    p = Path(path)
    if _is_sensitive(p):
        emit("fs_sensitive_blocked", op="read", path=str(p))
        return ToolResult(ok=False, output="",
                          error="path matches sensitive deny-list (ssh/aws/credentials/secrets)")
    roots = _fs_roots()
    if not _is_within_any(p, roots):
        return ToolResult(ok=False, output="",
                          error=f"path outside allowed roots: {[str(r) for r in roots]}")
    if not p.exists():
        return ToolResult(ok=False, output="", error="file not found")
    if not p.is_file():
        return ToolResult(ok=False, output="", error="not a regular file")
    try:
        data = p.read_bytes()[:max_bytes]
        text = data.decode("utf-8", errors="replace")
        return ToolResult(ok=True, output=text,
                          extra={"size": p.stat().st_size, "path": str(p)})
    except Exception as exc:
        return ToolResult(ok=False, output="", error=str(exc))


def fs_write_file(path: str, content: str, append: bool = False) -> ToolResult:
    p = Path(path)
    if _is_sensitive(p):
        emit("fs_sensitive_blocked", op="write", path=str(p))
        return ToolResult(ok=False, output="",
                          error="path matches sensitive deny-list (ssh/aws/credentials/secrets)")
    roots = _fs_roots()
    if not _is_within_any(p, roots):
        return ToolResult(ok=False, output="",
                          error=f"path outside allowed roots: {[str(r) for r in roots]}")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        emit("fs_write", path=str(p), bytes=len(content), append=append)
        return ToolResult(ok=True, output=f"wrote {len(content)} chars to {p}",
                          extra={"path": str(p), "size": p.stat().st_size})
    except Exception as exc:
        return ToolResult(ok=False, output="", error=str(exc))


def fs_list_dir(path: str = "", pattern: str = "*") -> ToolResult:
    roots = _fs_roots()
    p = (roots[0] / path) if path else roots[0]
    if not _is_within_any(p, roots):
        return ToolResult(ok=False, output="", error=f"outside allowed roots {[str(r) for r in roots]}")
    if not p.exists():
        return ToolResult(ok=False, output="", error="dir not found")
    items = []
    for x in sorted(p.glob(pattern)):
        if _is_sensitive(x):  # SCAN-68 FIX 2026-06-02 (NONNA): la deny-list valeva solo
            continue          # per read/write; list la bypassava -> rivelava .pem/.key/ssh/aws
        items.append({"name": x.name, "type": "dir" if x.is_dir() else "file",
                      "size": x.stat().st_size if x.is_file() else 0})
    return ToolResult(ok=True, output=f"{len(items)} entries in {p}",
                      extra={"items": items})


def fs_search_files(pattern: str, contains: str = "") -> ToolResult:
    """Find files matching glob pattern; optionally filter by content substring."""
    root = _fs_roots()[0]
    matches = []
    try:
        for p in root.rglob(pattern):
            if p.is_file():
                if _is_sensitive(p):  # SCAN-68 FIX 2026-06-02 (NONNA): non leggere/rivelare
                    continue          # file sensibili (fs_search leggeva pure il contenuto via `contains`)
                if contains:
                    try:
                        if contains.lower() in p.read_text(encoding="utf-8",
                                                           errors="ignore").lower():
                            matches.append(str(p.relative_to(root)))
                    except Exception:
                        continue
                else:
                    matches.append(str(p.relative_to(root)))
            if len(matches) >= 100:
                break
        return ToolResult(ok=True, output=f"{len(matches)} matches",
                          extra={"matches": matches})
    except Exception as exc:
        return ToolResult(ok=False, output="", error=str(exc))


# ---------------------------------------------------------------------------
# Shell (terminal access)
# ---------------------------------------------------------------------------


def shell_run(command: str, cwd: str = "", timeout_s: int = 30) -> ToolResult:
    """Execute an arbitrary shell command. GATED by HIPPO_ENABLE_SHELL=1.

    On Windows runs through cmd.exe; elsewhere through /bin/sh -c.
    Captures stdout+stderr (truncated to ~16KB) and returns the exit code.
    """
    if not _enabled("shell", default=False):
        return ToolResult(ok=False, output="",
                          error="shell access disabled. set HIPPO_ENABLE_SHELL=1")
    import subprocess as _sp
    emit("shell_run", command=command[:200], cwd=cwd, timeout_s=timeout_s)
    try:
        cwd_path = cwd if cwd else None
        if os.name == "nt":
            proc = _sp.run(
                ["cmd", "/c", command], capture_output=True,
                # `text=True` with cp1252 locale crashes on UTF-8 program output;
                # capture bytes and decode permissively below.
                timeout=timeout_s, cwd=cwd_path,
            )
        else:
            proc = _sp.run(
                ["/bin/sh", "-c", command], capture_output=True,
                timeout=timeout_s, cwd=cwd_path,
            )
        stdout = (proc.stdout or b"").decode("utf-8", errors="replace")[:16384]
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[:8192]
        ok = proc.returncode == 0
        out = stdout + (("\n[stderr]\n" + stderr) if stderr else "")
        return ToolResult(
            ok=ok, output=out,
            error="" if ok else f"exit={proc.returncode}\n{stderr or stdout}",
            extra={"returncode": proc.returncode, "command": command[:300]},
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, output="", error=f"timeout after {timeout_s}s")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(ok=False, output="", error=str(exc))


# ---------------------------------------------------------------------------
# Web
# ---------------------------------------------------------------------------


def _ip_is_blocked(addr: str) -> bool:
    """True if a literal IP string is loopback / RFC1918 / link-local /
    multicast / reserved / unspecified / cloud-metadata.

    A non-IP string (e.g. a hostname) is not classifiable here and returns
    False — resolve it first.
    """
    import ipaddress
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return bool(
        ip.is_loopback or ip.is_private or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        # AWS/GCP/Azure metadata service (already link-local, kept explicit)
        or str(ip) == "169.254.169.254"
    )


def _host_is_allowlisted(host: str) -> bool:
    """Honour the OLLAMA_HOST allowlist: an explicitly configured ollama host
    is permitted even when it points at loopback. Exact hostname match only."""
    if not host:
        return False
    ollama_url = os.environ.get("OLLAMA_HOST", "").strip()
    if not ollama_url:
        return False
    from urllib.parse import urlparse as _up
    try:
        ohost = _up(ollama_url).hostname or ""
    except (ValueError, AttributeError):
        ohost = ""
    return bool(ohost and host.lower() == ohost.lower())


def _is_blocked_host(host: str) -> bool:
    """Reject loopback / RFC1918 / link-local / cloud-metadata destinations.

    SSRF defense (CVE-006 / SEC V10). The check resolves the hostname so a
    DNS rebind to e.g. 127.0.0.1 is also rejected. The allowlist for
    `OLLAMA_HOST` is honoured: explicit ollama URLs pass.

    NOTE: this is a *pre-flight* check for a fast, friendly error message and
    telemetry. It does NOT by itself close the DNS-rebind / TOCTOU window —
    httpx performs its own, independent resolution at connect time, and the
    record can change between the two lookups. `_SSRFGuardBackend` pins the
    connection to the validated IP and is the actual security boundary. Keep
    both (defence in depth).
    """
    import socket as _sock
    if not host:
        return True
    if _host_is_allowlisted(host):
        return False
    # Resolve and check every returned address (plus the literal host itself).
    candidates: list[str] = [host]
    try:
        infos = _sock.getaddrinfo(host, None)
        candidates += [info[4][0] for info in infos]
    except (_sock.gaierror, OSError):
        # Hostname unresolvable — let httpx raise a normal error downstream
        return False
    return any(_ip_is_blocked(addr) for addr in candidates)


class _SSRFBlocked(httpcore.ConnectError):
    """Connection refused because the target resolved to a blocked address."""


class _SSRFGuardBackend:
    """httpcore network-backend wrapper that closes the SSRF DNS-rebind /
    TOCTOU window.

    `_is_blocked_host()` resolves + validates a host, but httpx then resolves
    AGAIN, independently, at connect time — so a host that looked public during
    validation can rebind to 127.0.0.1 / 169.254.169.254 / RFC1918 before the
    socket is opened. This wrapper resolves the host ONCE here, validates every
    returned address, and connects to a *validated* IP literal (pinning): the
    address we validate is the address we connect to. The request URL is left
    untouched, so TLS SNI / certificate verification and the Host header stay
    bound to the original hostname.

    Under respx (tests) httpcore's ConnectionPool.handle_request is patched, so
    this backend is never exercised — real-network behaviour only.
    """

    def __init__(self, inner) -> None:
        self._inner = inner

    def connect_tcp(self, host, port, timeout=None, local_address=None,
                    socket_options=None):
        target = host
        if not _host_is_allowlisted(host):
            import socket as _sock
            try:
                infos = _sock.getaddrinfo(host, port)
            except (_sock.gaierror, OSError) as exc:
                # We could not resolve the host ourselves. We must NOT fall
                # through to inner.connect_tcp(host): that would trigger a
                # blind, *unvalidated* re-resolution — exactly the TOCTOU we
                # are closing. Fail the connection instead.
                raise httpcore.ConnectError(
                    f"could not resolve {host!r} for SSRF validation: {exc}"
                ) from exc
            ips = [info[4][0] for info in infos]
            blocked = [ip for ip in ips if _ip_is_blocked(ip)]
            if not blocked and _ip_is_blocked(host):
                blocked = [host]
            if blocked:
                raise _SSRFBlocked(
                    f"destination {host!r} resolves to a blocked address "
                    f"{blocked[0]!r} — refused (SSRF rebind guard: loopback / "
                    f"RFC1918 / link-local / cloud-metadata)"
                )
            if not ips:
                # No address to validate/pin to — refuse rather than hand the
                # hostname to a blind re-resolution.
                raise httpcore.ConnectError(
                    f"no address resolved for {host!r} (SSRF validation)"
                )
            target = ips[0]  # pin to the validated IP; no second DNS lookup
        return self._inner.connect_tcp(
            target, port, timeout=timeout, local_address=local_address,
            socket_options=socket_options,
        )

    def connect_unix_socket(self, *args, **kwargs):
        return self._inner.connect_unix_socket(*args, **kwargs)

    def sleep(self, seconds):
        return self._inner.sleep(seconds)


def _install_ssrf_guard(client: httpx.Client) -> None:
    """Wrap the network backend of `client`'s transport(s) in-place so every
    TCP connection is resolved-once-then-validated. httpx's own transport
    construction (proxy / env / TLS settings) is left intact."""
    transports = [getattr(client, "_transport", None)]
    transports += list(getattr(client, "_mounts", {}).values())
    for t in transports:
        pool = getattr(t, "_pool", None)
        backend = getattr(pool, "_network_backend", None)
        if backend is not None and not isinstance(backend, _SSRFGuardBackend):
            pool._network_backend = _SSRFGuardBackend(backend)


def _ssrf_client(**kwargs) -> httpx.Client:
    """An ``httpx.Client`` whose outgoing connections are SSRF-rebind-guarded.

    Drop-in replacement for ``httpx.Client(**kwargs)`` for any fetch of an
    attacker-influenced URL (web_fetch, vision image fetch).
    """
    client = httpx.Client(**kwargs)
    _install_ssrf_guard(client)
    return client


# EHS-05 (codex scan 2026-06-02): cap massimo di byte scaricati da web_fetch
# PRIMA della decodifica/troncamento testo. Evita che un server malevolo o una
# risorsa enorme venga interamente bufferizzata in RAM (DoS). 5 MB e' ampio per
# estrarre testo da qualunque pagina ragionevole.
_MAX_FETCH_BYTES = 5_000_000


def _read_body_capped(resp, max_bytes: int) -> bytes:
    """Read an httpx *streaming* response body up to ``max_bytes``, then stop.

    Closes the unbounded-download window: iterates the stream and stops as soon
    as the cap is reached, so a multi-GB response never lands fully in memory.
    Returns at most ``max_bytes`` bytes.
    """
    buf = bytearray()
    for chunk in resp.iter_bytes():
        if not chunk:
            continue
        buf.extend(chunk)
        if len(buf) >= max_bytes:
            del buf[max_bytes:]
            break
    return bytes(buf)


def web_fetch(url: str, max_chars: int = 16000) -> ToolResult:
    """Fetch a URL, return cleaned text body.

    SSRF-hardened: rejects loopback, RFC1918, link-local, and cloud-metadata
    destinations (CVE-006). Followed redirects are not re-validated by the
    httpx client; we therefore set `follow_redirects=False` and handle one
    safe redirect manually.
    """
    if not _enabled("web", default=True):
        return ToolResult(ok=False, output="",
                          error="web access disabled in current permissions")
    if not re.match(r"^https?://", url):
        return ToolResult(ok=False, output="", error="only http(s) URLs allowed")
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        return ToolResult(ok=False, output="", error=f"bad URL: {exc}")
    host = parsed.hostname or ""
    if _is_blocked_host(host):
        emit("web_fetch_blocked", url=url, host=host, reason="ssrf")
        return ToolResult(ok=False, output="",
                          error=f"destination host {host!r} is on the SSRF blocklist "
                                f"(loopback / RFC1918 / link-local / metadata)")
    try:
        with _ssrf_client(timeout=20.0, follow_redirects=False,
                          headers={"User-Agent": "verimem/0.7 (research)"}) as c:
            current = url
            redirected = False
            # at most 2 passes: original request + one validated redirect
            for _attempt in range(2):
                with c.stream("GET", current) as r:
                    # Follow exactly one redirect, re-validating the destination.
                    if r.status_code in (301, 302, 303, 307, 308) and not redirected:
                        location = r.headers.get("location", "")
                        if not location:
                            r.raise_for_status()
                            break
                        next_url = location if location.startswith("http") else \
                            f"{parsed.scheme}://{parsed.netloc}{location}"
                        next_host = urlparse(next_url).hostname or ""
                        if _is_blocked_host(next_host):
                            emit("web_fetch_blocked", url=next_url, host=next_host,
                                 reason="ssrf-after-redirect")
                            return ToolResult(ok=False, output="",
                                              error=f"redirect to blocked host {next_host!r}")
                        current = next_url
                        redirected = True
                        continue
                    r.raise_for_status()
                    ct = r.headers.get("content-type", "")
                    # EHS-05 (codex 2026-06-02): read the body in streaming with a
                    # hard byte cap BEFORE decoding/cap-by-chars, so a malicious or
                    # huge response cannot be fully buffered into RAM (DoS).
                    body = _read_body_capped(r, _MAX_FETCH_BYTES)
                    enc = r.encoding or "utf-8"
                    try:
                        raw = body.decode(enc, errors="replace")
                    except (LookupError, TypeError):
                        raw = body.decode("utf-8", errors="replace")
                    if "html" in ct or url.endswith(".html") or url.endswith("/"):
                        text = _strip_html(raw)
                    else:
                        text = raw
                    text = text[:max_chars]
                    emit("web_fetch", url=url, status=r.status_code, bytes=len(body))
                    return ToolResult(ok=True, output=text,
                                      extra={"status": r.status_code, "content_type": ct,
                                             "url": str(r.url)})
            return ToolResult(ok=False, output="",
                              error="redirect without destination")
    except Exception as exc:
        return ToolResult(ok=False, output="", error=str(exc))


def web_search(query: str, n: int = 5) -> ToolResult:
    """DuckDuckGo HTML search → list of (title, url, snippet)."""
    if not _enabled("web", default=True):
        return ToolResult(ok=False, output="",
                          error="web access disabled in current permissions")
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = c.get("https://duckduckgo.com/html/", params={"q": query})
            r.raise_for_status()
            results = _parse_ddg(r.text, limit=n)
        return ToolResult(ok=True, output=f"{len(results)} results",
                          extra={"results": results})
    except Exception as exc:
        return ToolResult(ok=False, output="", error=str(exc))


def _strip_html(html: str) -> str:
    """FORGIA #191 — HTML→text via stdlib parser (was: regex, CodeQL FP).

    The previous implementation used `re.sub(r"<script[\\s\\S]*?</script>", ...)`
    which CodeQL flagged as `py/bad-tag-filter`: regex-based tag stripping
    can be bypassed by nested or whitespace-padded tags
    (`<scr<script>ipt>` survives one substitution and reassembles).

    Switch to `html.parser` (stdlib): the parser tracks tag state and
    drops all `<script>` / `<style>` / `<noscript>` / `<iframe>` content
    correctly even with nesting and unusual whitespace.

    Output: plain text suitable for LLM consumption (never displayed to
    a browser).
    """
    from html.parser import HTMLParser

    class _Stripper(HTMLParser):
        _DROP_TAGS = {"script", "style", "noscript", "iframe", "object", "embed"}

        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self._buf: list[str] = []
            self._skip_depth = 0

        def handle_starttag(self, tag: str, attrs: list) -> None:
            if tag.lower() in self._DROP_TAGS:
                self._skip_depth += 1

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() in self._DROP_TAGS and self._skip_depth > 0:
                self._skip_depth -= 1

        def handle_data(self, data: str) -> None:
            if self._skip_depth == 0:
                self._buf.append(data)

        def get_text(self) -> str:
            return "".join(self._buf)

    parser = _Stripper()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML — fall back to a conservative stdlib pass.
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    text = re.sub(r"\s+", " ", parser.get_text())
    return text.strip()


def _parse_ddg(html: str, limit: int = 5) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
        r'.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html, flags=re.S,
    ):
        url, title, snippet = m.group(1), _strip_html(m.group(2)), _strip_html(m.group(3))
        if url.startswith("//duckduckgo.com/l/?uddg="):
            from urllib.parse import parse_qs, unquote
            qs = parse_qs(url.split("?", 1)[1])
            url = unquote(qs.get("uddg", [url])[0])
        out.append({"title": title, "url": url, "snippet": snippet})
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


def _read_image_to_b64_and_media_type(source: str) -> tuple[str, str]:
    """source is a file path or http(s) URL. Returns (b64, media_type)."""
    if re.match(r"^https?://", source):
        from urllib.parse import urlparse
        # SCAN-68 FIX 2026-06-02 (NONNA): SSRF guard (CVE-006). Fetchava URL
        # arbitrarie senza _is_blocked_host (la difesa che web_fetch gia applica)
        # -> http://169.254.169.254/... (cloud-metadata) o loopback/RFC1918
        # colpivano risorse interne. Check host iniziale + ogni hop di redirect
        # (no auto-follow cieco, come web_fetch).
        cur = source
        with _ssrf_client(timeout=30.0, follow_redirects=False) as c:
            r = None
            for _ in range(5):
                h = urlparse(cur).hostname or ""
                if _is_blocked_host(h):
                    raise ValueError(f"blocked host (SSRF): {h}")
                r = c.get(cur)
                if r.is_redirect and r.headers.get("location"):
                    loc = r.headers["location"]
                    if loc.startswith("/"):
                        pu = urlparse(cur)
                        loc = f"{pu.scheme}://{pu.netloc}{loc}"
                    cur = loc
                    continue
                break
            r.raise_for_status()
            data = r.content
            ct = r.headers.get("content-type", "image/jpeg").split(";")[0]
    else:
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(source)
        data = p.read_bytes()
        suffix = p.suffix.lower().lstrip(".")
        ct = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
              "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/jpeg")
    return base64.b64encode(data).decode("ascii"), ct


# Default vision-capable model per provider. Override at runtime via
# HIPPO_VISION_MODEL env var (e.g. HIPPO_VISION_MODEL=qwen2-vl:7b for Ollama).
# These are the smallest model that supports vision in each provider, so
# vision_describe works out of the box without forcing the user to upgrade.
VISION_MODELS: dict[str, str] = {
    # Native multimodal — Anthropic Claude (all 4.x models support vision)
    "anthropic": "claude-haiku-4-5-20251001",
    # OpenAI: GPT-4o family supports vision; -mini is the cheap path.
    "openai": "gpt-4o-mini",
    # Google Gemini: Flash supports vision and is free tier.
    "gemini": "gemini-1.5-flash",
    # Groq: Llama 4 Scout (vision-capable, 2026 replacement for the
    # decommissioned llama-3.2-vision). Free tier.
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    # xAI: Grok 4 has vision.
    "xai": "grok-4",
    # Mistral: Pixtral.
    "mistral": "pixtral-12b-latest",
    # OpenRouter routes to anything — pick a known vision id.
    "openrouter": "anthropic/claude-haiku-4.5",
    # DeepSeek: VL2 family.
    "deepseek": "deepseek-vl2",
    # Alibaba Qwen: qwen-vl-plus / qwen-vl-max.
    "qwen": "qwen-vl-plus",
    # Zhipu GLM-4V.
    "zhipu": "glm-4v",
    # Moonshot Kimi vision.
    "moonshot": "moonshot-v1-8k-vision-preview",
    # 01.AI Yi vision.
    "yi": "yi-vision",
    # ByteDance Doubao vision.
    "doubao": "doubao-vision-pro-32k",
    # NVIDIA NIM hosts many vision models — meta llama 3.2 vision.
    "nvidia": "meta/llama-3.2-90b-vision-instruct",
    # Hugging Face router — Llama 3.2 Vision.
    "huggingface": "meta-llama/Llama-3.2-90B-Vision-Instruct",
    # Together / Fireworks: Llama 3.2 Vision.
    "together": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
    "fireworks": "accounts/fireworks/models/llama-v3p2-90b-vision-instruct",
    # Ollama: llava is the default if installed; user can set OLLAMA_VISION_MODEL
    # to qwen2-vl, llama3.2-vision, bakllava, llava-llama3, moondream, etc.
    "ollama": "llava",
    # Local OpenAI-compat — depends on what's loaded; LM Studio / vLLM users
    # should set HIPPO_VISION_MODEL explicitly.
    "lmstudio": "local-model",
    "vllm": "local-model",
    "localai": "local-model",
}


def _resolve_vision_model(provider: str) -> str:
    """Pick the vision-capable model for the given provider.

    Resolution order:
      1. HIPPO_VISION_MODEL env var
      2. VISION_MODELS[provider]
      3. None → caller falls back to provider-default
    """
    custom = os.environ.get("HIPPO_VISION_MODEL", "").strip()
    if custom:
        return custom
    if provider == "ollama":
        # Ollama has its own override
        ov = os.environ.get("OLLAMA_VISION_MODEL", "").strip()
        if ov:
            return ov
    return VISION_MODELS.get(provider, "")


def vision_describe(image: str, prompt: str = "Describe what you see in detail.") -> ToolResult:
    """Describe an image using the active multimodal LLM provider.

    Provider-specific dispatch:
    - Anthropic: native vision via SDK (image source = base64).
    - OpenAI-compat (OpenAI/Groq/Gemini/xAI/Mistral/Qwen/...): chat completion
      with `{"type":"image_url"}` block — works for any OpenAI-spec provider.
    - Ollama: /api/generate with `images` field (base64 list).

    Each provider uses its dedicated vision-capable model from VISION_MODELS
    (overridable via HIPPO_VISION_MODEL or OLLAMA_VISION_MODEL).
    """
    if not _enabled("vision", default=True):
        return ToolResult(ok=False, output="",
                          error="vision disabled in current permissions")
    try:
        b64, media_type = _read_image_to_b64_and_media_type(image)
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"cannot load image: {exc}")

    forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip().lower()
    from .llm import _autodetect_provider, _canonical
    provider = _canonical(forced) if forced else _autodetect_provider()
    emit("vision_describe", provider=provider, source=image[:80])

    try:
        if provider == "anthropic":
            return _vision_anthropic(b64, media_type, prompt)
        if provider == "ollama":
            return _vision_ollama(b64, prompt)
        # OpenAI-compatible providers
        return _vision_openai_compat(provider, b64, media_type, prompt)
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"vision call failed: {exc}")


def _vision_anthropic(b64: str, media_type: str, prompt: str) -> ToolResult:
    from anthropic import Anthropic
    client = Anthropic(api_key=CONFIG.anthropic_api_key)
    model = _resolve_vision_model("anthropic") or CONFIG.model_executor
    resp = client.messages.create(
        model=model, max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                                              "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return ToolResult(ok=True, output=text,
                      extra={"model": model, "tokens": resp.usage.input_tokens + resp.usage.output_tokens})


def _vision_ollama(b64: str, prompt: str) -> ToolResult:
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = _resolve_vision_model("ollama") or "llava"
    with httpx.Client(timeout=120.0) as c:
        # Probe: if the requested vision model isn't available, give a clear error.
        try:
            tags = c.get(f"{base}/api/tags").json()
            installed = [m.get("name", "") for m in tags.get("models", [])]
            # Match by exact name OR base name (qwen2-vl matches qwen2-vl:7b)
            if model not in installed and not any(
                m.startswith(model + ":") or m == model for m in installed
            ):
                hint = ", ".join(installed) or "(none)"
                return ToolResult(
                    ok=False, output="",
                    error=f"Ollama vision model '{model}' not installed. "
                          f"Run: `ollama pull {model}`. "
                          f"Available: {hint}",
                )
        except Exception:
            pass
        r = c.post(f"{base}/api/generate", json={
            "model": model, "prompt": prompt, "images": [b64], "stream": False,
        })
        r.raise_for_status()
        data = r.json()
    return ToolResult(ok=True, output=data.get("response", ""),
                      extra={"model": model})


def _vision_openai_compat(provider: str, b64: str, media_type: str, prompt: str) -> ToolResult:
    from openai import OpenAI

    from .llm import PROVIDERS
    spec = PROVIDERS.get(provider)
    if not spec:
        return ToolResult(ok=False, output="", error=f"vision not implemented for {provider}")
    api_key = os.environ.get(spec["env"], "")
    base_url = spec["base_url"]
    if "base_url_env" in spec and os.environ.get(spec["base_url_env"]):
        base_url = os.environ[spec["base_url_env"]]
    # Use a vision-capable model for this provider, NOT the executor default
    # which may be text-only (e.g. deepseek-chat is text-only, deepseek-vl is vision).
    model = _resolve_vision_model(provider) or spec["default_model"]
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model, max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                ],
            }],
        )
    except Exception as exc:
        return ToolResult(
            ok=False, output="",
            error=f"vision call to {provider}/{model} failed: {exc}. "
                  f"Hint: set HIPPO_VISION_MODEL to a vision-capable model id "
                  f"for this provider.",
        )
    text = resp.choices[0].message.content or ""
    return ToolResult(ok=True, output=text, extra={"model": model, "provider": provider})


# ---------------------------------------------------------------------------
# Webcam
# ---------------------------------------------------------------------------


def webcam_snapshot(camera_index: int = 0, save_path: str | None = None) -> ToolResult:
    """Capture one frame from the default camera. Returns the saved path."""
    if not _enabled("webcam", default=False):
        return ToolResult(ok=False, output="",
                          error="webcam disabled. set HIPPO_ENABLE_WEBCAM=1")
    try:
        import cv2  # type: ignore
    except ImportError:
        return ToolResult(ok=False, output="", error="opencv-python not installed")
    cap = cv2.VideoCapture(camera_index)
    try:
        if not cap.isOpened():
            return ToolResult(ok=False, output="",
                              error=f"cannot open camera {camera_index}")
        # Some cameras need a few frames to warm up
        for _ in range(5):
            cap.read()
        ok, frame = cap.read()
        if not ok or frame is None:
            return ToolResult(ok=False, output="", error="failed to capture frame")
    finally:
        cap.release()
    out = Path(save_path) if save_path else (CONFIG.data_dir / "webcam" / "snapshot.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), frame)
    h, w = frame.shape[:2]
    emit("webcam_snapshot", path=str(out), width=w, height=h)
    return ToolResult(ok=True, output=f"saved {w}x{h} frame to {out}",
                      extra={"path": str(out), "width": w, "height": h})


def webcam_describe(prompt: str = "Describe who or what you see in this webcam image.",
                    camera_index: int = 0) -> ToolResult:
    snap = webcam_snapshot(camera_index=camera_index)
    if not snap.ok:
        return snap
    path = (snap.extra or {}).get("path", "")
    desc = vision_describe(path, prompt)
    if desc.ok:
        desc.extra = {**(desc.extra or {}), "image_path": path}
    return desc


# ---------------------------------------------------------------------------
# Desktop (computer use)
# ---------------------------------------------------------------------------


# --- pyautogui safety (CVE-010 / SEC V11) ---------------------------------


_HOTKEY_DENY: frozenset[str] = frozenset({
    # System / login
    "win+l", "ctrl+alt+del", "ctrl+alt+delete",
    # Force quit / shutdown shortcuts
    "alt+f4", "cmd+q", "command+q",
    # Power / shutdown chords
    "ctrl+alt+end", "ctrl+shift+esc",
})


def _init_pyautogui_safety(pg) -> None:
    """Pin FAILSAFE on, enforce a small per-action sleep.

    `pyautogui.FAILSAFE = True` makes mouse-to-corner abort the script.
    `pyautogui.PAUSE = 0.05` rate-limits all calls to ~20/sec (V11 fix).
    """
    try:
        pg.FAILSAFE = True
        if not getattr(pg, "PAUSE", None) or pg.PAUSE < 0.05:
            pg.PAUSE = 0.05
    except Exception:  # noqa: BLE001 — defensive; we are best-effort
        pass


def desktop_screenshot(save_path: str | None = None,
                       describe: bool = False,
                       prompt: str = "Describe the desktop screen contents in detail.") -> ToolResult:
    # SCAN-68 FIX 2026-06-02 (NONNA): gate computer-use MANCANTE. desktop_click/
    # type/key sono gateati con HIPPO_ENABLE_COMPUTER_USE (default OFF) ma
    # screenshot no -> catturava lo schermo (info-disclosure) senza opt-in.
    # Allineato agli altri desktop tool.
    if not _enabled("computer_use", default=False):
        return ToolResult(ok=False, output="",
                          error="computer use disabled. set HIPPO_ENABLE_COMPUTER_USE=1")
    try:
        import pyautogui  # type: ignore
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"pyautogui not available: {exc}")
    _init_pyautogui_safety(pyautogui)
    out = Path(save_path) if save_path else (CONFIG.data_dir / "screenshots" / "screen.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot()
    img.save(out)
    w, h = img.size
    emit("desktop_screenshot", path=str(out), width=w, height=h)
    if describe:
        d = vision_describe(str(out), prompt)
        d.extra = {**(d.extra or {}), "path": str(out), "width": w, "height": h}
        return d
    return ToolResult(ok=True, output=f"saved {w}x{h} screenshot to {out}",
                      extra={"path": str(out), "width": w, "height": h})


def desktop_click(x: int, y: int, button: str = "left", clicks: int = 1) -> ToolResult:
    if not _enabled("computer_use", default=False):
        return ToolResult(ok=False, output="",
                          error="computer use disabled. set HIPPO_ENABLE_COMPUTER_USE=1")
    try:
        import pyautogui  # type: ignore
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"pyautogui not available: {exc}")
    _init_pyautogui_safety(pyautogui)
    emit("desktop_click", x=x, y=y, button=button, clicks=clicks)
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    return ToolResult(ok=True, output=f"clicked at ({x},{y}) button={button}")


def desktop_type(text: str, interval: float = 0.02) -> ToolResult:
    if not _enabled("computer_use", default=False):
        return ToolResult(ok=False, output="",
                          error="computer use disabled. set HIPPO_ENABLE_COMPUTER_USE=1")
    try:
        import pyautogui  # type: ignore
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"pyautogui not available: {exc}")
    _init_pyautogui_safety(pyautogui)
    emit("desktop_type", chars=len(text))
    pyautogui.typewrite(text, interval=interval)
    return ToolResult(ok=True, output=f"typed {len(text)} chars")


def desktop_key(key: str, unsafe: bool = False) -> ToolResult:
    """Press a key or hotkey combo.

    CVE-010 / SEC V11 fix: combos in `_HOTKEY_DENY` (e.g. `win+l`,
    `ctrl+alt+del`, `alt+f4`, `cmd+q`) are refused unless `unsafe=True`
    is passed explicitly.
    """
    if not _enabled("computer_use", default=False):
        return ToolResult(ok=False, output="",
                          error="computer use disabled. set HIPPO_ENABLE_COMPUTER_USE=1")
    norm = key.strip().lower().replace(" ", "")
    if not unsafe and norm in _HOTKEY_DENY:
        emit("desktop_key_blocked", key=norm, reason="deny-list")
        return ToolResult(ok=False, output="",
                          error=f"hotkey {key!r} is on the safety deny-list "
                                "(pass unsafe=True to override)")
    try:
        import pyautogui  # type: ignore
    except Exception as exc:
        return ToolResult(ok=False, output="", error=f"pyautogui not available: {exc}")
    _init_pyautogui_safety(pyautogui)
    emit("desktop_key", key=key)
    if "+" in key:
        keys = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    return ToolResult(ok=True, output=f"pressed {key}")


# ---------------------------------------------------------------------------
# Tool registry — extend default_tools()
# ---------------------------------------------------------------------------


def extra_tools() -> dict[str, ToolSpec]:
    """All extra tools, keyed by name. Combine with default_tools() for full set."""
    return {
        "fs_read_file": ToolSpec(
            name="fs_read_file",
            description="Read a text file (UTF-8) from the allowed root. "
                        "Returns up to 32KB.",
            schema={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "max_bytes": {"type": "integer"}},
                    "required": ["path"]},
            handler=fs_read_file,
        ),
        "fs_write_file": ToolSpec(
            name="fs_write_file",
            description="Write text to a file under the allowed root. "
                        "Set append=true to append.",
            schema={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "content": {"type": "string"},
                                   "append": {"type": "boolean"}},
                    "required": ["path", "content"]},
            handler=fs_write_file,
        ),
        "fs_list_dir": ToolSpec(
            name="fs_list_dir",
            description="List entries in a directory (relative to allowed root). "
                        "Optional glob pattern.",
            schema={"type": "object",
                    "properties": {"path": {"type": "string"},
                                   "pattern": {"type": "string"}}},
            handler=fs_list_dir,
        ),
        "fs_search_files": ToolSpec(
            name="fs_search_files",
            description="Recursively find files matching a glob, optionally "
                        "filtering by content substring.",
            schema={"type": "object",
                    "properties": {"pattern": {"type": "string"},
                                   "contains": {"type": "string"}},
                    "required": ["pattern"]},
            handler=fs_search_files,
        ),
        "web_fetch": ToolSpec(
            name="web_fetch",
            description="Fetch a URL and return readable text. "
                        "HTML pages are stripped of tags.",
            schema={"type": "object",
                    "properties": {"url": {"type": "string"},
                                   "max_chars": {"type": "integer"}},
                    "required": ["url"]},
            handler=web_fetch,
        ),
        "web_search": ToolSpec(
            name="web_search",
            description="Web search via DuckDuckGo. Returns title/url/snippet for top N.",
            schema={"type": "object",
                    "properties": {"query": {"type": "string"},
                                   "n": {"type": "integer"}},
                    "required": ["query"]},
            handler=web_search,
        ),
        "vision_describe": ToolSpec(
            name="vision_describe",
            description="Describe an image (path or URL) using a multimodal LLM. "
                        "Works with Anthropic/OpenAI/Ollama/Groq/etc.",
            schema={"type": "object",
                    "properties": {"image": {"type": "string"},
                                   "prompt": {"type": "string"}},
                    "required": ["image"]},
            handler=vision_describe,
        ),
        "webcam_snapshot": ToolSpec(
            name="webcam_snapshot",
            description="Capture a frame from the default webcam, save as JPEG. "
                        "Returns the saved file path.",
            schema={"type": "object",
                    "properties": {"camera_index": {"type": "integer"},
                                   "save_path": {"type": "string"}}},
            handler=webcam_snapshot,
        ),
        "webcam_describe": ToolSpec(
            name="webcam_describe",
            description="Capture from webcam and describe with vision LLM. "
                        "'Who is in front of the camera?'",
            schema={"type": "object",
                    "properties": {"prompt": {"type": "string"},
                                   "camera_index": {"type": "integer"}}},
            handler=webcam_describe,
        ),
        "desktop_screenshot": ToolSpec(
            name="desktop_screenshot",
            description="Capture full desktop screenshot. If describe=true, "
                        "also pass to a vision LLM and return the description.",
            schema={"type": "object",
                    "properties": {"save_path": {"type": "string"},
                                   "describe": {"type": "boolean"},
                                   "prompt": {"type": "string"}}},
            handler=desktop_screenshot,
        ),
        "desktop_click": ToolSpec(
            name="desktop_click",
            description="Click at (x,y). Disabled by default; "
                        "set HIPPO_ENABLE_COMPUTER_USE=1 to enable.",
            schema={"type": "object",
                    "properties": {"x": {"type": "integer"},
                                   "y": {"type": "integer"},
                                   "button": {"type": "string"},
                                   "clicks": {"type": "integer"}},
                    "required": ["x", "y"]},
            handler=desktop_click,
        ),
        "desktop_type": ToolSpec(
            name="desktop_type",
            description="Type text into the focused window. Requires "
                        "HIPPO_ENABLE_COMPUTER_USE=1.",
            schema={"type": "object",
                    "properties": {"text": {"type": "string"},
                                   "interval": {"type": "number"}},
                    "required": ["text"]},
            handler=desktop_type,
        ),
        "desktop_key": ToolSpec(
            name="desktop_key",
            description="Press a key or key combination ('enter', 'ctrl+s'). "
                        "Requires HIPPO_ENABLE_COMPUTER_USE=1.",
            schema={"type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"]},
            handler=desktop_key,
        ),
        "shell_run": ToolSpec(
            name="shell_run",
            description="Execute an arbitrary shell command (cmd.exe on Windows, "
                        "/bin/sh elsewhere). Returns stdout+stderr and exit code. "
                        "Requires HIPPO_ENABLE_SHELL=1.",
            schema={"type": "object",
                    "properties": {"command": {"type": "string"},
                                   "cwd": {"type": "string"},
                                   "timeout_s": {"type": "integer"}},
                    "required": ["command"]},
            handler=shell_run,
        ),
    }


def all_tools() -> dict[str, ToolSpec]:
    """default Python sandbox + all extras."""
    from .tools import default_tools
    out = dict(default_tools())
    out.update(extra_tools())
    return out
