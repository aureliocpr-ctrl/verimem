"""Search/Replace edit format — the same pattern Aider uses for GPT-4-class models.

The agent emits edits as fenced blocks like:

    path/to/file.py
    <<<<<<< SEARCH
    def old_name():
        pass
    =======
    def new_name():
        return 42
    >>>>>>> REPLACE

Multiple blocks per turn allowed. The block is applied verbatim — SEARCH
text must match exactly (whitespace-sensitive). On mismatch we don't
silently corrupt the file; we report the mismatch and let the agent retry.

Why search/replace and not whole-file rewrite:
  • smaller token output (only the changed region travels)
  • reviewable: humans see exactly what changed before applying
  • robust: if SEARCH doesn't match, we abort cleanly instead of overwriting
  • model-friendly: most modern models (Opus, Sonnet, Haiku, GPT, DeepSeek)
    produce reliable diffs in this format.

Module is pure (no I/O for the parsing path) so it tests fast.
"""
from __future__ import annotations

import difflib
import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EditBlock:
    path: str       # workspace-relative
    search: str     # text to find (verbatim)
    replace: str    # text to substitute


@dataclass
class ApplyResult:
    block: EditBlock
    ok: bool
    reason: str = ""        # populated on failure
    diff: str = ""          # unified diff applied (success only)


# Match a path line followed by a SEARCH/REPLACE block.
# We accept either bare path or fenced ```path on its own line.
_BLOCK_RE = re.compile(
    r"(?:^|\n)"
    r"(?:```[\w./+-]*\s*\n)?"          # optional opening fence
    r"(?P<path>[^\n<>=`]+?)\n"         # path line
    r"<{3,}\s*SEARCH\s*\n"
    r"(?P<search>.*?)"                 # search body (possibly empty)
    r"\n?={3,}[^\n]*\n"                # divider — leading \n is optional so empty SEARCH works
    r"(?P<replace>.*?)"
    r"\n?>{3,}\s*REPLACE\s*"           # closing — leading \n optional for empty REPLACE
    r"(?:\n```)?",                     # optional closing fence
    re.DOTALL,
)


def parse_edits(text: str) -> list[EditBlock]:
    """Extract all SEARCH/REPLACE blocks from the agent's output.

    Robust to:
      • markdown code fences around the whole block
      • leading/trailing blank lines
      • Windows CRLF (we normalise to LF on parse)
      • multiple blocks in one turn
    """
    if not text:
        return []
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[EditBlock] = []
    for m in _BLOCK_RE.finditer(norm):
        path = m.group("path").strip().strip("`").strip()
        search = m.group("search")
        replace = m.group("replace")
        # Strip a single leading/trailing newline (the format adds them
        # mechanically) but preserve the rest of the body verbatim.
        if search.startswith("\n"):
            search = search[1:]
        if search.endswith("\n"):
            search = search[:-1]
        if replace.startswith("\n"):
            replace = replace[1:]
        if replace.endswith("\n"):
            replace = replace[:-1]
        if not path:
            continue
        blocks.append(EditBlock(path=path, search=search, replace=replace))
    return blocks


def make_diff(path: str, before: str, after: str, context: int = 3) -> str:
    """Unified diff suitable for terminal display."""
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="a/" + path,
        tofile="b/" + path,
        n=context,
    ))


# --- Sensitive-file deny-list (CVE-011) -----------------------------------

# Directories whose contents are blocked outright. Match is case-insensitive
# on Windows. The agent should not be self-modifying its CI, IDE config, or
# version-control internals via search/replace.
_DENY_DIRS: tuple[str, ...] = (
    ".git", ".vscode", ".idea", ".devcontainer",
    ".github", ".hg", ".svn",
)

# Filenames blocked anywhere in the tree.
_DENY_NAMES: tuple[str, ...] = (
    "Makefile", "makefile",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile", "Pipfile.lock", "poetry.lock",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
    ".env", ".envrc", ".npmrc", ".pypirc",
)

# Glob patterns blocked against the path basename.
_DENY_GLOBS: tuple[str, ...] = (
    "*.sh", "*.bat", "*.ps1", "*.cmd",
    "*.pem", "*.key", "*.crt", "*.p12",
)


def _editfmt_allow_sensitive() -> bool:
    """Operator override — opt in via _EDITFMT_ALLOW_SENSITIVE=1."""
    return os.environ.get(
        "_EDITFMT_ALLOW_SENSITIVE", "",
    ).strip().lower() in ("1", "true", "yes", "on")


def _is_sensitive_target(rel_path: str) -> tuple[bool, str]:
    """Return (blocked, reason). Reason is non-empty iff blocked."""
    if _editfmt_allow_sensitive():
        return False, ""
    norm = rel_path.replace("\\", "/")
    parts = [p for p in norm.split("/") if p]
    on_windows = os.name == "nt"
    cmp_parts = [p.lower() for p in parts] if on_windows else list(parts)
    deny_dirs = ([d.lower() for d in _DENY_DIRS] if on_windows
                 else list(_DENY_DIRS))
    for d in deny_dirs:
        if d in cmp_parts:
            return True, f"path under blocked directory: {d!r}"
    if not parts:
        return False, ""
    name = parts[-1]
    cmp_name = name.lower() if on_windows else name
    deny_names = ([n.lower() for n in _DENY_NAMES] if on_windows
                  else list(_DENY_NAMES))
    if cmp_name in deny_names:
        return True, f"filename in deny-list: {name!r}"
    for pattern in _DENY_GLOBS:
        # fnmatch handles case-insensitivity on Windows already
        if fnmatch.fnmatch(name, pattern):
            return True, f"filename matches blocked pattern: {pattern!r}"
    # Reuse tools_extra._is_sensitive when available — covers ssh/aws/etc.
    try:
        from .tools_extra import _is_sensitive
        if _is_sensitive(Path(rel_path)):
            return True, "path matches sensitive deny-list"
    except (ImportError, OSError):
        pass
    return False, ""


def apply_block(block: EditBlock, root: Path) -> ApplyResult:
    """Apply one edit block to the filesystem rooted at `root`.

    On success: returns ok=True with the unified diff that was applied.
    On failure (path escape, missing file, search mismatch, ambiguous match):
    returns ok=False with a human-readable `reason` and an empty diff.
    """
    rel = block.path.replace("\\", "/").lstrip("/")
    blocked, deny_reason = _is_sensitive_target(rel)
    if blocked:
        return ApplyResult(
            block, ok=False,
            reason=(f"refusing to edit sensitive target: {deny_reason}. "
                    "Set _EDITFMT_ALLOW_SENSITIVE=1 to override."),
        )
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return ApplyResult(block, ok=False, reason=f"path escapes workspace: {rel}")

    # Empty SEARCH means "create new file with REPLACE as content"
    if block.search.strip() == "":
        if target.exists() and target.read_text(encoding="utf-8") != "":
            return ApplyResult(
                block, ok=False,
                reason="empty SEARCH but file already has content",
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        before = "" if not target.exists() else target.read_text(encoding="utf-8")
        target.write_text(block.replace, encoding="utf-8")
        return ApplyResult(
            block, ok=True,
            diff=make_diff(rel, before, block.replace),
        )

    if not target.exists():
        return ApplyResult(block, ok=False,
                            reason=f"file does not exist: {rel}")
    try:
        before = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ApplyResult(block, ok=False,
                            reason=f"file not UTF-8: {rel}")

    occurrences = before.count(block.search)
    if occurrences == 0:
        return ApplyResult(
            block, ok=False,
            reason=("SEARCH text not found in file (whitespace must match exactly). "
                     f"first 80 chars of search: {block.search[:80]!r}"),
        )
    if occurrences > 1:
        return ApplyResult(
            block, ok=False,
            reason=f"SEARCH text matches {occurrences} times — make it more specific",
        )
    after = before.replace(block.search, block.replace, 1)
    target.write_text(after, encoding="utf-8")
    return ApplyResult(
        block, ok=True,
        diff=make_diff(rel, before, after),
    )


def apply_blocks(blocks: list[EditBlock], root: Path) -> list[ApplyResult]:
    """Apply multiple blocks. Each is independent; one failing does not roll back others."""
    results: list[ApplyResult] = []
    for b in blocks:
        results.append(apply_block(b, root))
    return results


# --- Tool-style entry point — used by the agent's tool dispatcher ----------


SEARCH_REPLACE_INSTRUCTIONS = """\
## EDIT FORMAT — READ CAREFULLY (you MUST follow this verbatim)

When you need to change a file, emit a SEARCH/REPLACE block in EXACTLY
this format. The path goes on its own line, NO fences around the block:

    path/to/file.py
    <<<<<<< SEARCH
    <verbatim text from the file — whitespace must match byte-for-byte>
    =======
    <new text>
    >>>>>>> REPLACE

ABSOLUTE RULES (violation = silent file corruption avoided, but your edit
WILL NOT APPLY):

  1. SEARCH text must appear EXACTLY ONCE in the file. If it appears
     multiple times, include surrounding lines until it is unique.
  2. SEARCH text must be COPIED VERBATIM from the file — same spaces,
     same tabs, same line-endings. Never paraphrase, never re-indent,
     never collapse blank lines. If you guess, the edit fails.
  3. To create a NEW file: leave SEARCH empty, put the full content in
     REPLACE. The file must not already exist.
  4. To rename a function across multiple files: emit ONE SEARCH/REPLACE
     block PER FILE — never bundle multiple files into one block.
  5. Before you decide what to edit, read the file with run_python or
     fs_read_file so your SEARCH text is real, not invented.
  6. When writing tests for a class or function you didn't define, READ
     ITS SIGNATURE FIRST — do not guess argument names or order.
"""
