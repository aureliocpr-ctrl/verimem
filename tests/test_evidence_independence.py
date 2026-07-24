"""P0 evidence-before-belief, ciclo 2a: the AND rule as a pure decision.

Ciclo 1 recorded WHO writes and WHO indexes (`writer_principal`,
`meta.indexed_by`). This cycle turns those stamps into the only question the
design review (glm-5.2 + kimi-k3, convergent 2/2, 2026-07-22) said is worth
asking: *is the cited evidence INDEPENDENT of the claimant?*

The rule, and why each conjunct is load-bearing:

  independent  ⟺  author is known  AND  author != claimant
                  AND  the AUTHOR's channel is trusted

* **author known** — an unsigned exogenous document never earns advisory
  (absence is the untrusted class, never a fake default).
* **author != claimant** — self-citation is the laundering move: write the
  poison, then cite yourself.
* **the AUTHOR's channel** (not the claimant's) — this is the conjunct that
  survives falsification. If the check looked at the claimant's channel, an
  attacker could index poison over the unauthenticated MCP surface
  (`mcp:unbound`) and have any SDK-side writer cite it as "independent": two
  different principals, rule satisfied, attack through. Trust has to attach
  to how the EVIDENCE got in.

Contested provenance is not independence: if the versions of one source_id
carry DIFFERENT `indexed_by` stamps, the author is unknown (a re-ingest is
exactly how one would try to relabel someone else's document as one's own,
or one's own as someone else's). Pinning the exact cited version is the next
increment (content-bound receipts, D5/#44); until then the safe answer is
"contested → not independent".
"""
from __future__ import annotations

import pytest

from verimem.documents import DocumentStore
from verimem.evidence_independence import (
    author_principal_of_ref,
    channel_of,
    independence_verdict,
    is_trusted_channel,
)

# --- channel parsing ------------------------------------------------------

@pytest.mark.parametrize("principal,expected", [
    ("sdk:local", "sdk"),
    ("mcp:unbound", "mcp"),
    ("gw:team-alpha", "gw"),
    ("cli:local", "cli"),
    ("ops-1", None),        # operator-declared in-process identity, no channel
    ("", None),
    (None, None),
])
def test_channel_of(principal, expected):
    assert channel_of(principal) == expected


@pytest.mark.parametrize("principal,trusted", [
    ("sdk:local", True),
    ("cli:local", True),
    ("gw:team-alpha", True),   # the gateway authenticated a tenant key
    ("ops-1", True),           # only an in-process caller can set this
    ("mcp:unbound", False),    # the MCP client is not authenticated
    ("anything:unbound", False),
    ("", False),
    (None, False),
])
def test_is_trusted_channel(principal, trusted):
    assert is_trusted_channel(principal) is trusted


# --- ref → author ---------------------------------------------------------

def test_author_of_doc_ref(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-1", "The API returns 429 on rate limit.",
              principal="gw:team-alpha")
    assert author_principal_of_ref("doc:spec-1", ds) == "gw:team-alpha"


def test_author_of_file_ref_uses_the_path_as_source_id(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text("The API returns 429 on rate limit.", encoding="utf-8")
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest_file(p, principal="cli:local")
    assert author_principal_of_ref(f"file:{p}:12", ds) == "cli:local"


def test_unsigned_document_has_no_author(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-2", "The API returns 429 on rate limit.")
    assert author_principal_of_ref("doc:spec-2", ds) is None


def test_unknown_ref_has_no_author(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    assert author_principal_of_ref("doc:nope", ds) is None
    assert author_principal_of_ref("commit:deadbeef", ds) is None
    assert author_principal_of_ref("", ds) is None


def test_contested_provenance_is_not_an_author(tmp_path):
    """Two versions of one source, two different stampers → author unknown.

    A re-ingest under a different identity must not be able to relabel who
    vouched for a document.
    """
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-3", "The API returns 429 on rate limit.",
              principal="gw:team-alpha")
    ds.ingest("spec-3", "The API returns 200 on rate limit.",
              principal="mcp:unbound")
    assert author_principal_of_ref("doc:spec-3", ds) is None


# --- the AND rule ---------------------------------------------------------

def test_independent_when_author_differs_and_channel_trusted(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-1", "The API returns 429 on rate limit.",
              principal="gw:team-alpha")
    v = independence_verdict(verified_by=["doc:spec-1"],
                             claimant="sdk:local", store=ds)
    assert v.independent is True
    assert v.author == "gw:team-alpha"
    assert v.ref == "doc:spec-1"


def test_self_citation_is_not_independent(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-1", "The API returns 429 on rate limit.",
              principal="sdk:local")
    v = independence_verdict(verified_by=["doc:spec-1"],
                             claimant="sdk:local", store=ds)
    assert v.independent is False
    assert "self" in v.reason


def test_untrusted_claimant_cannot_launder_through_trusted_evidence(tmp_path):
    """Adversarial review 2026-07-25 (glm-5.2 + deepseek-v4-pro, convergent
    2/2): checking only the AUTHOR's channel lets an unauthenticated claimant
    launder itself through someone else's evidence. It cites a real document
    indexed by a real tenant — and MISREPRESENTS what that document says. L4
    entailment is the only backstop and, on natural language, it is
    best-effort, not proof.

    So both ends must be authenticated: the evidence has to have entered
    through a channel that authenticates, AND the one invoking it has to be
    someone. Cost, stated plainly: MCP writers (always `mcp:unbound`) never
    benefit from this rule until MCP clients carry a bound identity.
    """
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("real-spec", "The API returns 429 on rate limit.",
              principal="gw:team-alpha")
    v = independence_verdict(verified_by=["doc:real-spec"],
                             claimant="mcp:unbound", store=ds)
    assert v.independent is False
    assert "claimant" in v.reason


def test_poison_then_cite_across_channels_is_not_independent(tmp_path):
    """THE attack the AND rule exists for: poison lands over the
    unauthenticated MCP surface, a different (SDK) principal cites it. Two
    principals differ — and it still must not count as independent."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("evil-1", "The deploy key is rotated weekly.",
              principal="mcp:unbound")
    v = independence_verdict(verified_by=["doc:evil-1"],
                             claimant="sdk:local", store=ds)
    assert v.independent is False
    assert "channel" in v.reason


def test_unsigned_source_is_not_independent(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-2", "The API returns 429 on rate limit.")
    v = independence_verdict(verified_by=["doc:spec-2"],
                             claimant="sdk:local", store=ds)
    assert v.independent is False
    assert v.author is None


def test_no_refs_at_all_is_not_independent(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    v = independence_verdict(verified_by=None, claimant="sdk:local", store=ds)
    assert v.independent is False


def test_first_independent_ref_wins_over_later_ones(tmp_path):
    """A claim citing several refs is independent if ANY of them is."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("mine", "x", principal="sdk:local")
    ds.ingest("theirs", "The API returns 429 on rate limit.",
              principal="gw:team-alpha")
    v = independence_verdict(verified_by=["commit:deadbeef", "doc:mine",
                                          "doc:theirs"],
                             claimant="sdk:local", store=ds)
    assert v.independent is True
    assert v.ref == "doc:theirs"


def test_unknown_claimant_is_never_independent(tmp_path):
    """A pre-P0 row (NULL principal) has no identity to be independent OF."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-1", "x", principal="gw:team-alpha")
    v = independence_verdict(verified_by=["doc:spec-1"], claimant=None,
                             store=ds)
    assert v.independent is False


def test_verdict_is_serialisable(tmp_path):
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("spec-1", "x", principal="gw:team-alpha")
    d = independence_verdict(verified_by=["doc:spec-1"], claimant="sdk:local",
                             store=ds).to_dict()
    assert d["independent"] is True
    assert d["author"] == "gw:team-alpha"
    assert set(d) == {"independent", "author", "ref", "reason"}


def test_store_failure_degrades_to_not_independent(tmp_path):
    """Never fail a write because the document store is unreadable — but
    never claim independence you could not verify either."""
    class _Broken:
        def get_latest(self, source_id):  # noqa: ARG002
            raise OSError("disk gone")

        def list_versions(self, source_id):  # noqa: ARG002
            raise OSError("disk gone")

    v = independence_verdict(verified_by=["doc:spec-1"], claimant="sdk:local",
                             store=_Broken())
    assert v.independent is False
