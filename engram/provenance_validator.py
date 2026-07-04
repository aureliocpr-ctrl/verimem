"""Cycle #111 v2 (2026-05-16) — provenance reference validator with I/O verify.

History
-------

v1 (PR #50, closed without merge) used regex-only pattern allowlist with
``re.fullmatch``. Aurelio stop-check + empirical probe demonstrated the
fix was SECURITY THEATRE: 12 format-valid but semantically void refs
slipped through unchanged::

    pytest                    →  status='verified' kept
    exit 0 / exit0            →  status='verified' kept
    bash:fake:anything        →  status='verified' kept
    bash:notreallyacommand    →  status='verified' kept
    commit abcdef1            →  status='verified' kept  (SHA inventato)
    commit 0000000            →  status='verified' kept
    sha256:deadbeefdeadbeef   →  status='verified' kept
    pytest_collect            →  status='verified' kept
    pytest:test_fake_DNE      →  status='verified' kept
    file:/no/such/path:99999  →  status='verified' kept  (file inesistente)
    arxiv.org/abs/9999.99999  →  status='verified' kept  (paper fake)

The cycle 111 v1 critic round 2 counterexample worker had explicitly
flagged this ("format-valid but semantically-bogus refs accepted —
known-by-design weaknesses, outside the claim's scope") and the human
operator filed the warning as out-of-scope. It was the most important
warning and the response was wrong.

v2 contract
-----------

The validator now enforces **empirical verification** at store time for
``status='verified'``. The acceptable forms shrink to two — both must
pass an I/O check against the configured ``repo_root``:

* ``file:<path>:<lineno>``  — ``<path>`` resolves (absolute, or
  joined to ``repo_root``) to a file that contains at least
  ``<lineno>`` lines.
* ``commit <hex>``  — ``git -C <repo_root> rev-parse --verify
  <hex>^{commit}`` returns exit 0.

Refs that pass the regex pattern but fail the I/O check are demoted.
Refs that don't match any pattern are demoted. Empty ``verified_by``
is demoted.

``status='provisional'`` is accepted with URL / arxiv refs since those
point to external sources and the validator does NOT perform network
fetches at store time (would be slow and brittle). Provisional means
"the model claims this is in the cited paper; not empirically
verified by HippoAgent". URL/arxiv refs for status='provisional' must
match the whitelist domain (arxiv.org / github.com / gitlab.com /
doi.org) so that ``provisional`` refs cannot bypass to ``url:banana``.

Forms REMOVED from the verified allowlist (downgraded to "audit
signal only — see engram.legacy_audit"):

* ``pytest`` / ``pytest_collect`` / ``pytest:<id>``  — would require
  a pytest collect subprocess (slow, brittle, and the test could
  exist while still failing).
* ``exit 0`` / ``exit0``  — meaningless outside a context that
  identifies which command exited; not verifiable.
* ``bash:<cmd>[:<sub>...]``  — historical tool-call trace, not
  verifiable a posteriori. May still appear in
  ``legacy_unverified`` rows but is not admissible for ``verified``.
* ``sha256:<hex>``  — a hash with no payload reference is
  semantically void.

If you have a legitimate ``pytest`` or ``bash`` provenance event,
record it as ``file:<test_path>:<lineno>`` or
``commit <sha>`` that introduces the relevant code, since those ARE
verifiable.

API
---

* :func:`validate_verified_refs(refs, *, repo_root)`  — boolean,
  returns True iff at least one ref passes I/O verification.
* :func:`validate_provisional_refs(refs)`  — boolean, pattern-only
  check on URL / arxiv whitelist for ``status='provisional'``.
* :func:`is_valid_provenance_ref(ref, *, repo_root)`  — single-ref
  predicate kept for backwards-compatible direct use. Combines
  pattern check + I/O verify.
* :func:`invalid_provenance_refs(refs, *, repo_root)`  — list of
  refs that fail :func:`is_valid_provenance_ref`. Order preserved.

Paranoid default
----------------

``repo_root=None`` means "no I/O verification available" and causes
every ``status='verified'`` write to be demoted. This is intentional:
the safe default is to assume the deployment cannot verify, not to
accept on faith.
"""
from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

_LOG = logging.getLogger(__name__)

# Pattern compile (whole-string match enforced via fullmatch at call site).
# These describe SHAPE only — semantic verification is the I/O step.
_FILE_PATTERN = re.compile(r"file:([^\s][^\s]*):(\d+)")
_COMMIT_PATTERN = re.compile(r"commit[:\s]+([a-f0-9]{6,40})", re.IGNORECASE)  # colon O spazio: allinea ai detector L1 (_COMMIT_REF_PREFIXES usa 'commit:') e chiude il double-bind di formato (bench anti-confab 2026-06-03). Esistenza commit resta git-verificata.

# Provisional-tier patterns (URL / arxiv whitelist — domain-restricted).
_ALLOWED_URL_DOMAIN = (
    r"(?:arxiv\.org|github\.com|gitlab\.com|doi\.org)"
)
_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"url:(?:https?://)?" + _ALLOWED_URL_DOMAIN + r"/\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"https?://" + _ALLOWED_URL_DOMAIN + r"/\S*",
        re.IGNORECASE,
    ),
    re.compile(r"arxiv\.org/(?:abs|html)/\d{4}\.\d{4,5}\S*", re.IGNORECASE),
)


# ---------------------------------------------------------------------------
# I/O checks
# ---------------------------------------------------------------------------


def _verify_file_ref(ref: str, *, repo_root: Path | None) -> bool:
    """Return True iff ``ref`` is ``file:<path>:<lineno>`` AND the path
    resolves to a file with at least ``<lineno>`` non-zero lines.

    Resolution rule:
      * Absolute path → used as-is.
      * Relative path → joined with ``repo_root``. If ``repo_root`` is
        None, the ref is unverifiable → returns False.

    Defensive against symlinks-out-of-root and oversized files by
    capping the read at <lineno> lines.
    """
    m = _FILE_PATTERN.fullmatch((ref or "").strip())
    if m is None:
        return False
    path_str, lineno_str = m.group(1), m.group(2)
    try:
        lineno = int(lineno_str)
    except ValueError:
        return False
    if lineno < 1:
        return False
    p = Path(path_str)
    if not p.is_absolute():
        if repo_root is None:
            return False
        p = (repo_root / p).resolve()
    else:
        try:
            p = p.resolve()
        except OSError:
            return False
    # Defense against symlink-out-of-root and path-traversal
    # (e.g. file:../../etc/passwd:1 with relative, or an absolute path
    # to a system file that happens to exist). After resolve(), the
    # path MUST still be inside repo_root. is_relative_to is Python 3.9+.
    if repo_root is not None:
        try:
            root_resolved = Path(repo_root).resolve()
        except OSError:
            return False
        try:
            p.relative_to(root_resolved)
        except ValueError:
            return False
    if not p.exists() or not p.is_file():
        return False
    try:
        with p.open("rb") as f:
            count = 0
            for _ in f:
                count += 1
                if count >= lineno:
                    return True
        return False
    except (OSError, PermissionError):
        return False


def _verify_commit_ref(ref: str, *, repo_root: Path | None) -> bool:
    """Return True iff ``ref`` is ``commit <hex6-40>`` AND
    ``git rev-parse --verify <hex>^{commit}`` returns 0 in ``repo_root``.

    Returns False when ``repo_root`` is None or not a git repo, or
    when the subprocess fails for any reason.
    """
    if repo_root is None:
        return False
    m = _COMMIT_PATTERN.fullmatch((ref or "").strip())
    if m is None:
        return False
    sha = m.group(1)
    from ._proc_quiet import quiet_popen_kwargs
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
            cwd=str(repo_root),
            capture_output=True,
            timeout=5.0,
            check=False,
            **quiet_popen_kwargs(),  # cycle #136: no Windows CMD pop-up
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_BARE_SHA = re.compile(r"[a-f0-9]{6,40}", re.IGNORECASE)


def _git_sha_exists(sha: str, *, repo_root: Path | None) -> bool:
    """True iff ``sha`` (bare hex) is a real commit in ``repo_root``.

    Same I/O check as :func:`_verify_commit_ref` but on a BARE sha (no
    ``commit `` prefix), so it can back the GATE's colon vocabulary
    (``commit:<sha>`` / ``git:<sha>``) which ``_COMMIT_PATTERN`` (space
    form) does not match. Never raises.
    """
    sha = (sha or "").strip()
    if repo_root is None or _BARE_SHA.fullmatch(sha) is None:
        return False
    from ._proc_quiet import quiet_popen_kwargs
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
            cwd=str(repo_root), capture_output=True, timeout=5.0,
            check=False, **quiet_popen_kwargs(),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def evidence_ref_exists(ref: str, *, repo_root: Path | None) -> bool:
    """True iff ``ref`` is an existence-verifiable evidence ref that ACTUALLY
    exists. Handles the anti-confab GATE's colon vocabulary
    (``commit:<sha>`` / ``git:<sha>`` → git rev-parse; ``file:<path>:<line>``
    → filesystem) PLUS the provenance space form (``commit <sha>``).

    Returns False for non-existence-verifiable kinds (``pytest:`` / ``bash:``
    / freeform): those are NOT proof of existence (cycle #111 v2 removed them
    from the verified allowlist). ``repo_root=None`` → False (paranoid).
    """
    if not isinstance(ref, str):
        return False
    s = ref.strip()
    if not s:
        return False
    if ":" in s:
        kind, _, val = s.partition(":")
        k = kind.strip().lower()
        if k in ("commit", "git"):
            return _git_sha_exists(val, repo_root=repo_root)
        if k == "file":
            return _verify_file_ref(s, repo_root=repo_root)
    # space form ``commit <sha>`` / ``file:...`` fall through to the canonical
    # validator.
    return is_valid_provenance_ref(s, repo_root=repo_root)


def any_evidence_ref_exists(
    refs: Iterable[str] | None, *, repo_root: Path | None,
) -> bool:
    """True iff at least one ref in ``refs`` is existence-verifiable AND exists.

    Used by ``run_validation_gate`` to catch FABRICATED evidence: a
    well-formed ``commit:deadbeef`` that suppresses an L1 claim detector but
    does not exist in the repo. Empty / all-unverifiable → False.
    """
    return any(
        evidence_ref_exists(r, repo_root=repo_root) for r in (refs or [])
    )


def is_valid_provenance_ref(
    ref: str, *, repo_root: Path | None = None,
) -> bool:
    """Return True iff ``ref`` matches one of the two verifiable forms
    AND the corresponding I/O check passes.

    Use :func:`validate_verified_refs` when checking a *list* of refs
    (the gate logic is "at least one verifiable ref"). This single-ref
    predicate is exposed for direct callers and tests.

    Empty / whitespace / non-string refs return False.
    """
    if not isinstance(ref, str):
        return False
    s = ref.strip()
    if not s:
        return False
    if _verify_file_ref(s, repo_root=repo_root):
        return True
    if _verify_commit_ref(s, repo_root=repo_root):
        return True
    return False


def validate_verified_refs(
    refs: list[str], *, repo_root: Path | None = None,
) -> bool:
    """Return True iff ``refs`` is non-empty AND at least one ref passes
    :func:`is_valid_provenance_ref`. This is the contract used by
    ``SemanticMemory.store`` to gate ``status='verified'`` writes.
    """
    if not refs:
        return False
    return any(is_valid_provenance_ref(r, repo_root=repo_root) for r in refs)


def validate_provisional_refs(refs: list[str]) -> bool:
    """Return True iff ``refs`` is non-empty AND at least one ref matches
    the URL/arxiv whitelist (domain restricted to arxiv/github/gitlab/doi).

    No I/O check is performed: ``provisional`` means "external source
    cited but not empirically verified". Pattern check only.
    """
    if not refs:
        return False
    for r in refs:
        if not isinstance(r, str):
            continue
        s = r.strip()
        if not s:
            continue
        if any(p.fullmatch(s) for p in _URL_PATTERNS):
            return True
    return False


def invalid_provenance_refs(
    refs: list[str], *, repo_root: Path | None = None,
) -> list[str]:
    """Return the subset of ``refs`` that fail
    :func:`is_valid_provenance_ref`. Order preserved. Empty input →
    empty output. Does NOT deduplicate.
    """
    return [
        r for r in (refs or [])
        if not is_valid_provenance_ref(r, repo_root=repo_root)
    ]


__all__ = [
    "is_valid_provenance_ref",
    "validate_verified_refs",
    "validate_provisional_refs",
    "invalid_provenance_refs",
    "evidence_ref_exists",
    "any_evidence_ref_exists",
]
