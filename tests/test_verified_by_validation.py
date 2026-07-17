"""Cycle #111 v2 (2026-05-16) — verified_by hard-gate with I/O verify.

History
-------

v1 (PR #50, closed without merge) used regex-only ``re.fullmatch``.
Empirical probe by Aurelio showed 12 format-valid but semantically-void
refs slipped through unchanged (``pytest``, ``exit 0``, ``bash:fake``,
``commit abcdef1`` with invented SHA, ``file:/no/such/path:99999``,
``arxiv.org/abs/9999.99999``). The critic round 2 counterexample worker
had flagged this and the response was wrong.

v2 contract
-----------

* ``status='verified'``  → at least one ``verified_by`` ref must pass
  EMPIRICAL I/O verification:
    - ``file:<path>:<lineno>`` → filesystem check (file exists + has
      ≥<lineno> lines).
    - ``commit <sha>`` → ``git rev-parse --verify <sha>^{commit}``
      returns 0 in ``repo_root``.
* ``status='provisional'`` → at least one ref must match URL/arxiv
  whitelist pattern (no I/O — provisional ≠ verified).
* All other statuses → no gate.
* ``repo_root=None`` → paranoid default: every ``status='verified'``
  write is demoted (no way to verify).

This test module sets up a real on-disk git repo (tmp_path) with one
file and one commit so the I/O verification has something to point at.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory

# ---------------------------------------------------------------------------
# Fixtures: real tmp git repo + file with known content
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Initialise a real on-disk git repo with one file and one commit.

    Returns the repo root. Tests use this both as ``repo_root`` for the
    SemanticMemory hard-gate AND as the source of truth for valid
    ``file:`` and ``commit`` refs.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    # Init git, configure local identity (CI environments may not have one).
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Cycle 111 Test"],
        cwd=repo, check=True,
    )
    # Write a file with 10 lines so we can probe lineno boundaries.
    src = repo / "src.py"
    src.write_text(
        "\n".join(f"line_{i}" for i in range(1, 11)) + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "src.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "cycle111-v2 fixture commit"],
        cwd=repo, check=True,
    )
    return repo


@pytest.fixture
def real_commit_sha(git_repo: Path) -> str:
    """HEAD SHA of the fixture repo (40-hex). Used as a valid ``commit <sha>``
    ref payload in the demote/pass tests below."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_repo, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def sm_with_repo(tmp_path: Path, git_repo: Path) -> SemanticMemory:
    """SemanticMemory configured WITH repo_root → I/O verify enabled."""
    return SemanticMemory(
        db_path=tmp_path / "sm.db", repo_root=git_repo,
    )


@pytest.fixture
def sm_no_repo(tmp_path: Path) -> SemanticMemory:
    """SemanticMemory WITHOUT repo_root → paranoid default (all 'verified'
    writes demoted)."""
    return SemanticMemory(db_path=tmp_path / "sm.db")


# ---------------------------------------------------------------------------
# Verified pass-through: real file ref + real commit ref
# ---------------------------------------------------------------------------


def test_verified_with_real_file_ref_stays_verified(
    sm_with_repo: SemanticMemory, git_repo: Path,
) -> None:
    """A ``file:<absolute_path>:<existing_lineno>`` ref against a real
    file keeps status='verified'."""
    src = git_repo / "src.py"
    fact = Fact(
        proposition="line 5 of fixture is line_5",
        topic="test/file-verified",
        status="verified",
        verified_by=[f"file:{src}:5"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "verified"
    assert sm_with_repo.get(fact.id).status == "verified"


def test_verified_with_relative_file_ref_resolves_against_repo_root(
    sm_with_repo: SemanticMemory,
) -> None:
    """A relative ``file:`` ref is joined to repo_root and verified."""
    fact = Fact(
        proposition="relative ref resolves",
        topic="test/relative",
        status="verified",
        verified_by=["file:src.py:10"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "verified"


def test_verified_with_real_commit_ref_stays_verified(
    sm_with_repo: SemanticMemory, real_commit_sha: str,
) -> None:
    """A ``commit <real_HEAD_sha>`` ref against the fixture repo keeps
    status='verified'."""
    fact = Fact(
        proposition="commit ref backed by real SHA",
        topic="test/commit-verified",
        status="verified",
        verified_by=[f"commit {real_commit_sha[:12]}"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "verified"


def test_verified_with_full_commit_sha_stays_verified(
    sm_with_repo: SemanticMemory, real_commit_sha: str,
) -> None:
    fact = Fact(
        proposition="full commit ref",
        topic="test/commit-full",
        status="verified",
        verified_by=[f"commit {real_commit_sha}"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "verified"


def test_verified_with_mixed_one_valid_one_invalid_passes(
    sm_with_repo: SemanticMemory, real_commit_sha: str,
) -> None:
    """At-least-one semantics: a single verifiable ref is enough."""
    fact = Fact(
        proposition="mixed refs, one is real",
        topic="test/mixed",
        status="verified",
        verified_by=["file:/no/such/path:1", f"commit {real_commit_sha[:8]}"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "verified"


# ---------------------------------------------------------------------------
# Verified demote: every v1 syntactic-only bypass must now fail
# ---------------------------------------------------------------------------


_V1_BYPASS_VECTORS: tuple[str, ...] = (
    # Originally-passing semantically void refs that v1 admitted:
    "pytest",
    "pytest_collect",
    "pytest:test_fake_does_not_exist",
    "exit 0",
    "exit0",
    "bash:fake:anything",
    "bash:notreallyacommand",
    "sha256:deadbeefdeadbeef",
    "sha:abcdef123456",
    # File pointer that does NOT resolve:
    "file:/no/such/path:99999",
    "file:does/not/exist.py:1",
    # Commit SHA that does NOT exist in the fixture repo:
    "commit abcdef1",
    "commit 0000000000000000000000000000000000000000",
    # Free-text refs (round 1 critic counterexamples):
    "banana",
    "url:banana",
    "url:something.com/page",
    "lying claim that pytest passed",
    "returned exit 0 trust me bro",
    "let me commit abcdef1 for you",
    # Empty / whitespace:
    "",
    "   ",
)


@pytest.mark.parametrize("bad_ref", _V1_BYPASS_VECTORS)
def test_verified_with_any_v1_bypass_is_demoted(
    sm_with_repo: SemanticMemory, bad_ref: str,
) -> None:
    """Every ref that used to slip through v1 must now demote."""
    fact = Fact(
        proposition=f"poisoning attempt via {bad_ref!r}",
        topic="test/v1-bypass",
        status="verified",
        verified_by=[bad_ref],
    )
    sm_with_repo.store(fact)
    assert fact.status == "model_claim", (
        f"v1 bypass NOT closed: ref={bad_ref!r} kept status='verified'"
    )
    on_disk = sm_with_repo.get(fact.id)
    assert on_disk is not None and on_disk.status == "model_claim"


def test_verified_with_empty_list_is_demoted(sm_with_repo: SemanticMemory) -> None:
    fact = Fact(
        proposition="empty refs", topic="t",
        status="verified", verified_by=[],
    )
    sm_with_repo.store(fact)
    assert fact.status == "model_claim"


def test_path_traversal_outside_repo_is_demoted(
    sm_with_repo: SemanticMemory, tmp_path: Path,
) -> None:
    """Counterexample worker preemptive: a ref pointing OUTSIDE
    repo_root via absolute path must demote even when the target file
    exists. Without the relative_to() check, an attacker could cite
    e.g. /etc/passwd as ``file:/etc/passwd:1`` and pass the gate."""
    outside = tmp_path / "outside.txt"
    outside.write_text("line1\nline2\nline3\n", encoding="utf-8")
    fact = Fact(
        proposition="path traversal attempt", topic="t",
        status="verified",
        verified_by=[f"file:{outside}:1"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "model_claim", (
        "absolute-outside-root ref kept status='verified' "
        "— relative_to() defense failed"
    )


def test_relative_path_traversal_is_demoted(
    sm_with_repo: SemanticMemory,
) -> None:
    """Counterexample worker preemptive: a relative ref with ../..
    that escapes repo_root must demote, even if the resolved path
    points to a real file on disk."""
    fact = Fact(
        proposition="relative traversal", topic="t",
        status="verified",
        verified_by=["file:../../../../etc/passwd:1"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "model_claim"


def test_symlink_out_of_root_is_demoted(
    sm_with_repo: SemanticMemory, git_repo: Path, tmp_path: Path,
) -> None:
    """Counterexample worker preemptive: a symlink INSIDE repo_root
    pointing OUTSIDE must demote — resolve() follows symlinks, so
    relative_to() catches the escape after resolution."""
    outside = tmp_path / "outside_target.txt"
    outside.write_text("line1\nline2\n", encoding="utf-8")
    link = git_repo / "sneaky_link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform/user")
    fact = Fact(
        proposition="symlink-out attack", topic="t",
        status="verified",
        verified_by=[f"file:{link}:1"],
    )
    sm_with_repo.store(fact)
    assert fact.status == "model_claim"


def test_verified_logs_warning_on_demote(
    sm_with_repo: SemanticMemory, caplog,
) -> None:
    fact = Fact(
        proposition="poisoning attempt", topic="t",
        status="verified", verified_by=["banana"],
    )
    with caplog.at_level(logging.WARNING):
        sm_with_repo.store(fact)
    assert any(
        "demoted to model_claim" in rec.getMessage()
        for rec in caplog.records
    ), f"expected demote warning, got: {[r.getMessage() for r in caplog.records]}"


# ---------------------------------------------------------------------------
# Paranoid default: no repo_root → every 'verified' is demoted
# ---------------------------------------------------------------------------


def test_no_repo_root_demotes_even_real_looking_refs(
    sm_no_repo: SemanticMemory,
) -> None:
    """Without repo_root, the gate has no way to verify → demote even
    when the ref LOOKS plausible. This is the paranoid default."""
    fact = Fact(
        proposition="should not pass without repo_root",
        topic="test/no-repo",
        status="verified",
        verified_by=["file:/anything:1", "commit abcdef1234"],
    )
    sm_no_repo.store(fact)
    assert fact.status == "model_claim"


# ---------------------------------------------------------------------------
# Provisional tier: URL / arxiv accepted as pattern-only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url_ref", [
    "url:arxiv.org/abs/2310.11511",
    "url:arxiv.org/abs/2310.11511:sec_3.1",
    "url:https://arxiv.org/abs/2310.11511",
    "url:github.com/aureliocpr-ctrl/hippoagent/blob/main/engram/semantic.py",
    "url:doi.org/10.1234/example",
    "https://arxiv.org/abs/2310.11511",
    "https://github.com/aureliocpr-ctrl/hippoagent",
    "arxiv.org/abs/2310.11511",
])
def test_provisional_with_whitelist_url_stays_provisional(
    sm_no_repo: SemanticMemory, url_ref: str,
) -> None:
    """Whitelisted URL refs are accepted for status='provisional' even
    without repo_root (no I/O verification at provisional tier)."""
    fact = Fact(
        proposition=f"research finding from {url_ref}",
        topic="research/provisional",
        status="provisional",
        verified_by=[url_ref],
    )
    sm_no_repo.store(fact)
    assert fact.status == "provisional"


@pytest.mark.parametrize("bad_url_ref", [
    "url:banana",
    "url:something.com/page",
    "url:not-a-real-url",
    "https://evil.com/payload",
    "banana",
    "",
])
def test_provisional_with_garbage_url_is_demoted(
    sm_no_repo: SemanticMemory, bad_url_ref: str,
) -> None:
    """URL refs outside the arxiv/github/gitlab/doi whitelist demote
    even at provisional tier."""
    fact = Fact(
        proposition=f"attempt to slip through provisional with {bad_url_ref}",
        topic="research/bad-provisional",
        status="provisional",
        verified_by=[bad_url_ref],
    )
    sm_no_repo.store(fact)
    assert fact.status == "model_claim"


# ---------------------------------------------------------------------------
# Non-gated statuses pass through (no false positives)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["model_claim", "legacy_unverified"])
def test_non_verified_status_with_garbage_refs_unchanged(
    sm_with_repo: SemanticMemory, status: str,
) -> None:
    """Only 'verified' and 'provisional' are gated. Other statuses
    carry arbitrary verified_by content unchanged."""
    fact = Fact(
        proposition="some claim", topic="t",
        status=status, verified_by=["banana", "anything"],
    )
    sm_with_repo.store(fact)
    assert fact.status == status
    on_disk = sm_with_repo.get(fact.id)
    assert on_disk is not None and on_disk.status == status


def test_default_fact_is_model_claim(sm_with_repo: SemanticMemory) -> None:
    fact = Fact(proposition="default fact", topic="t")
    sm_with_repo.store(fact)
    assert fact.status == "model_claim"
    assert fact.verified_by == []


# ---------------------------------------------------------------------------
# Direct validator API
# ---------------------------------------------------------------------------


def test_validator_api_surface() -> None:
    """The module must export the four documented helpers."""
    from verimem import provenance_validator as pv

    assert callable(pv.is_valid_provenance_ref)
    assert callable(pv.validate_verified_refs)
    assert callable(pv.validate_provisional_refs)
    assert callable(pv.invalid_provenance_refs)

    # Without repo_root, every single-ref check is False.
    assert pv.is_valid_provenance_ref("file:/anything:1") is False
    assert pv.is_valid_provenance_ref("commit deadbeef") is False
    assert pv.is_valid_provenance_ref("banana") is False
    assert pv.is_valid_provenance_ref("") is False

    # Provisional API: pattern-only, no repo_root.
    assert pv.validate_provisional_refs(
        ["url:arxiv.org/abs/2310.11511"],
    ) is True
    assert pv.validate_provisional_refs(["url:banana"]) is False
    assert pv.validate_provisional_refs([]) is False


def test_validator_with_real_repo(git_repo: Path, real_commit_sha: str) -> None:
    """End-to-end direct call against a real repo."""
    from verimem import provenance_validator as pv

    assert pv.is_valid_provenance_ref(
        f"file:{git_repo / 'src.py'}:3", repo_root=git_repo,
    ) is True
    assert pv.is_valid_provenance_ref(
        f"file:{git_repo / 'src.py'}:9999",  # past EOF
        repo_root=git_repo,
    ) is False
    assert pv.is_valid_provenance_ref(
        f"commit {real_commit_sha[:10]}", repo_root=git_repo,
    ) is True
    assert pv.is_valid_provenance_ref(
        "commit abcdef1", repo_root=git_repo,
    ) is False


# ---------------------------------------------------------------------------
# Regression: status enum still validated
# ---------------------------------------------------------------------------


def test_invalid_status_still_raises(sm_with_repo: SemanticMemory) -> None:
    bad = Fact(proposition="x", topic="t", status="garbage_status")
    with pytest.raises(ValueError, match="status must be one of"):
        sm_with_repo.store(bad)
