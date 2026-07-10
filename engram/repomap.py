"""Lightweight repo map — inspired by Aider's PageRank-ranked symbol map.

We don't need full tree-sitter parsing for a v1: a regex-based extractor
on common languages (Python, JS/TS) gets us a useful "what's defined
where" map that the agent can lean on for navigation. The map is bounded
in size (token budget) so we don't blow the context window on big repos.

The ranking is intentionally simple: bias toward (a) shorter paths
(top-level modules first), (b) more symbols (richer files), (c) recent
mtime (recently-edited files are more relevant), (d) skills the agent
has used recently (they pin attention to the same files).

Per-file results are cached on disk keyed by (path, mtime, size). On a
1k-file repo the cold scan is ~250ms; warm hits are ~10ms.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import CONFIG
from .observability import get_log

log = get_log()


# Per-language regex extractors. Each returns (kind, name, line_no).
_PY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<kind>def|class|async\s+def)\s+(?P<name>[A-Za-z_][\w]*)"
    r"(?P<sig>[^:\n]*)",
    re.MULTILINE,
)
_JS_RE = re.compile(
    r"^(?P<kind>export\s+(?:default\s+)?(?:async\s+)?function|"
    r"export\s+(?:default\s+)?class|"
    r"function|class|const|let|var)"
    r"\s+(?P<name>[A-Za-z_$][\w$]*)"
    r"(?P<sig>[^{=\n]*)",
    re.MULTILINE,
)
_RUST_RE = re.compile(
    r"^(?P<kind>pub\s+fn|fn|pub\s+struct|struct|pub\s+enum|enum|pub\s+trait|trait|impl)"
    r"\s+(?P<name>[A-Za-z_][\w]*)"
    r"(?P<sig>[^{\n]*)",
    re.MULTILINE,
)
_GO_RE = re.compile(
    r"^(?P<kind>func|type)\s+(?:\([^)]+\)\s+)?(?P<name>[A-Za-z_][\w]*)"
    r"(?P<sig>[^{\n]*)",
    re.MULTILINE,
)


_LANG_BY_SUFFIX = {
    ".py": ("python", _PY_RE),
    ".js": ("javascript", _JS_RE),
    ".ts": ("typescript", _JS_RE),
    ".tsx": ("typescript", _JS_RE),
    ".jsx": ("javascript", _JS_RE),
    ".rs": ("rust", _RUST_RE),
    ".go": ("go", _GO_RE),
}


_IGNORED_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".idea", ".vscode",
    ".tox", "htmlcov", ".next", "data", "target",
}


@dataclass
class Symbol:
    kind: str       # def | class | function | const | …
    name: str
    line: int
    signature: str = ""   # for def/fn: "(self, item, priority)" — visible to the agent


@dataclass
class FileEntry:
    path: str       # workspace-relative
    lang: str
    symbols: list[Symbol] = field(default_factory=list)
    size: int = 0
    mtime: float = 0.0
    score: float = 0.0


def _scan_file(
    path: Path, root: Path,
    mtime: float | None = None, size: int | None = None,
) -> FileEntry | None:
    suffix = path.suffix.lower()
    lang_re = _LANG_BY_SUFFIX.get(suffix)
    if lang_re is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lang, regex = lang_re
    syms: list[Symbol] = []
    for m in regex.finditer(text):
        kind = m.group("kind").strip()
        name = m.group("name")
        line = text[: m.start()].count("\n") + 1
        try:
            raw = m.group("sig") or ""
        except (IndexError, re.error):
            raw = ""
        sig = raw.strip().rstrip(":").strip()[:120]
        syms.append(Symbol(kind=kind, name=name, line=line, signature=sig))
    rel = str(path.relative_to(root)).replace("\\", "/")
    if mtime is None or size is None:
        try:
            st = path.stat()
            size, mtime = st.st_size, st.st_mtime
        except OSError:
            size, mtime = 0, 0.0
    return FileEntry(path=rel, lang=lang, symbols=syms, size=size, mtime=mtime)


def _walk_files(root: Path) -> list[tuple[Path, float, int]]:
    """Yield (path, mtime, size) tuples via `os.scandir`.

    scandir returns DirEntry objects whose stat() is cached on Windows
    (the WIN32_FIND_DATA already includes mtime/size). This lets us
    decide cache hit/miss without an extra Path.stat() round trip.
    """
    out: list[tuple[Path, float, int]] = []
    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    name = entry.name
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if name not in _IGNORED_DIRS:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            suffix = Path(name).suffix.lower()
                            if suffix in _LANG_BY_SUFFIX:
                                st = entry.stat()
                                out.append(
                                    (Path(entry.path), st.st_mtime, st.st_size)
                                )
                    except OSError:
                        continue
        except OSError:
            continue
    return out


def _entry_to_cache(e: FileEntry) -> dict:
    return {
        "path": e.path, "lang": e.lang, "size": e.size, "mtime": e.mtime,
        "symbols": [asdict(s) for s in e.symbols],
    }


def _entry_from_cache(d: dict) -> FileEntry:
    return FileEntry(
        path=d["path"], lang=d["lang"], size=d.get("size", 0),
        mtime=d.get("mtime", 0.0),
        symbols=[Symbol(**s) for s in d.get("symbols", [])],
    )


def _default_cache_path(root: Path) -> Path:
    """Return a per-repo cache path under CONFIG.data_dir.

    Keying on the workspace root means multiple repos served by the same
    HippoAgent install don't collide.
    """
    import hashlib
    h = hashlib.sha1(str(root.resolve()).encode("utf-8"),
                     usedforsecurity=False).hexdigest()[:12]
    return CONFIG.data_dir / f"repomap_cache_{h}.json"


def _load_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    # FORGIA pezzo #37: corruption guard — a hand-edited cache containing
    # `null`, `[...]`, or a scalar would later crash on `.get(...)` calls.
    return raw if isinstance(raw, dict) else {}


def _save_cache(path: Path, cache: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError as exc:
        log.warning("repomap_cache_save_failed", error=str(exc))


def scan_repo(
    root: Path,
    max_files: int = 200,
    use_cache: bool = True,
    cache_path: Path | None = None,
) -> list[FileEntry]:
    """Walk the workspace, return file entries with symbols (Python/JS/TS/Rust/Go).

    Per-file mtime+size cache: re-scanning an unchanged file just rehydrates
    the cached symbols. Disable with `use_cache=False` for tests.
    """
    cpath = cache_path if cache_path is not None else _default_cache_path(root)
    cache = _load_cache(cpath) if use_cache else {}
    cache_dirty = False
    entries: list[FileEntry] = []
    candidates = _walk_files(root)
    for p, mtime, size in candidates:
        rel = str(p.relative_to(root)).replace("\\", "/")
        ck = cache.get(rel)
        if (
            use_cache and ck and ck.get("mtime") == mtime
            and ck.get("size") == size
        ):
            entries.append(_entry_from_cache(ck))
        else:
            e = _scan_file(p, root, mtime=mtime, size=size)
            if e is None:
                continue
            entries.append(e)
            if use_cache:
                cache[rel] = _entry_to_cache(e)
                cache_dirty = True
        if len(entries) >= max_files * 4:
            break
    if use_cache and cache_dirty:
        live = {
            str(p.relative_to(root)).replace("\\", "/")
            for p, _m, _s in candidates
        }
        for stale in [k for k in cache if k not in live]:
            cache.pop(stale, None)
        _save_cache(cpath, cache)
    return entries


def rank_files(
    entries: list[FileEntry],
    recent_skill_paths: set[str] | None = None,
    now: float | None = None,
) -> list[FileEntry]:
    """Score + sort. Higher score = more relevant.

    Heuristic blend:
      • +1.0  per ~10 symbols (richer files rank higher)
      • +0.5  bonus for shortish paths (top-level files)
      • +1.0  if mtime within last 24h (recency)
      • +1.5  if path appears in a recently-applied skill provenance
    """
    now = now or time.time()
    recent_skill_paths = recent_skill_paths or set()
    for e in entries:
        s = 0.0
        s += min(3.0, len(e.symbols) / 10.0)
        depth = e.path.count("/")
        s += max(0.0, 1.0 - depth * 0.15)
        age_h = max(0.0, (now - e.mtime) / 3600.0) if e.mtime else 999.0
        if age_h <= 24:
            s += 1.0 * (1.0 - age_h / 24.0)
        if e.path in recent_skill_paths:
            s += 1.5
        e.score = s
    entries.sort(key=lambda x: -x.score)
    return entries


def render_repomap(entries: list[FileEntry], max_chars: int = 4000) -> str:
    """Render a compact, scannable repo map under a token budget."""
    lines: list[str] = []
    used = 0
    lines.append("## REPO MAP (top files by relevance)")
    used += len(lines[0]) + 1
    for e in entries:
        head = f"\n### {e.path}  · {e.lang}  · {len(e.symbols)} symbols"
        if used + len(head) + 200 > max_chars:
            break
        lines.append(head)
        used += len(head)
        # List up to 12 symbols per file, with signature when short.
        # Long signatures sometimes confuse smaller models — cap to 60 chars.
        for sym in e.symbols[:12]:
            sig_str = ""
            if sym.signature and len(sym.signature) <= 60:
                sig_str = sym.signature
            ln = f"  L{sym.line:>4}  {sym.kind:<10} {sym.name}{sig_str}"
            if used + len(ln) + 1 > max_chars:
                break
            lines.append(ln)
            used += len(ln) + 1
        if len(e.symbols) > 12:
            extra = f"  …+{len(e.symbols) - 12} more"
            if used + len(extra) + 1 < max_chars:
                lines.append(extra)
                used += len(extra) + 1
    return "\n".join(lines)


def build_repomap(
    root: Path,
    recent_skill_paths: set[str] | None = None,
    max_files: int = 80,
    max_chars: int = 4000,
    use_cache: bool = True,
    cache_path: Path | None = None,
) -> str:
    """One-shot helper: scan, rank, render."""
    entries = scan_repo(root, use_cache=use_cache, cache_path=cache_path)
    entries = rank_files(entries, recent_skill_paths=recent_skill_paths)[:max_files]
    return render_repomap(entries, max_chars=max_chars)
