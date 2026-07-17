"""Anti-confabulation retrieval benchmark — the USP eval.

LongMemEval (retrieval recall@k) measures the EMBEDDING layer, where Engram
ties any decent vector store. It does NOT exercise Engram's differentiator: the
anti-confab gate that keeps unverified/hype claims OUT of the recallable set.

This bench measures THAT. Same corpus of (TRUE, CONFABULATED) fact pairs fed to:
  • GATED  = Engram's real anti_confab_gate.run_validation_gate (downgrade -> the
             confab fact is quarantined -> NOT recallable).
  • NAIVE  = a plain vector store: every fact is recallable (what a memory layer
             without a write-time gate does).
Per query (semantically near BOTH the true and the confab fact for a topic) we
take top-k by cosine and count how many CONFABULATED facts leak into the result.

Metric = confabulation-leak rate (lower is better). Also reports the gate's
classification (did it quarantine every confab and keep every true?).

100% local, judge-free, no external API. Uses the REAL gate + the REAL embedding
model (e5), not a mock. Falsifiable: if GATED leak ~= NAIVE leak, the USP is empty.
"""
from __future__ import annotations

import os

os.environ.setdefault("HIPPO_EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
os.environ.setdefault("HIPPO_EMBEDDING_DIM", "768")

import json

import numpy as np

from verimem import embedding
from verimem.anti_confab_gate import run_validation_gate
from verimem.validate_claim import validate_claim


class _BenchFact:
    """Minimal Fact shape for the L3 contradiction measurement."""

    def __init__(self, fid: str, proposition: str) -> None:
        self.id = fid
        self.proposition = proposition
        self.topic = ""
        self.confidence = 0.9
        self.source_episodes: list[str] = []


class _BenchSemantic:
    """Production-faithful keyword backend (SQL LIKE on proposition)."""

    def __init__(self, facts: list[_BenchFact]) -> None:
        self._facts = facts

    def search_facts(self, query: str, *, limit: int = 20, topic=None):
        ql = (query or "").strip().lower()
        return [f for f in self._facts if (not ql) or ql in f.proposition.lower()][:limit]


class _BenchAgent:
    def __init__(self, facts: list[_BenchFact]) -> None:
        self.semantic = _BenchSemantic(facts)

# (topic, query, TRUE fact [factual, no hype], TRUE verified_by, CONFAB fact [hype, no evidence])
PAIRS = [
    ("auth", "how does the authentication module work",
     "The authentication module hashes passwords with bcrypt at cost factor 12.",
     ["file:engram/auth.py:42"],
     "The authentication module is fully production-ready, battle-tested and SHIPPED with zero vulnerabilities."),
    ("cache", "what is the cache eviction policy",
     "The cache evicts entries with an LRU policy bounded at 1024 entries.",
     ["file:engram/cache.py:88"],
     "The caching layer is COMPLETO, fully optimized and MERGED to production after exhaustive testing."),
    ("retry", "how are network retries handled",
     "Network calls retry up to 3 times with exponential backoff starting at 200ms.",
     ["file:engram/net.py:15"],
     "The retry logic has been DIAGNOSED as flawless and is AUTHORIZED for all critical paths."),
    ("ratelimit", "what is the API rate limit",
     "The API limits each client to 100 requests per minute via a token bucket.",
     ["file:engram/limit.py:30"],
     "Rate limiting WORKS perfectly and was VERIFIED to handle infinite load with no degradation."),
    ("backup", "how does the backup system work",
     "Backups run nightly via sqlite VACUUM INTO with a 7-snapshot rotation.",
     ["file:engram/backup.py:55"],
     "The backup system is bulletproof, SHIPPED, and MONITORED 24/7 with guaranteed zero data loss."),
    ("search", "how is full-text search implemented",
     "Full-text search uses an FTS5 virtual table over the proposition column.",
     ["file:engram/search.py:12"],
     "Search is blazing fast, production-grade and was COMPLETO ahead of schedule."),
    ("queue", "how does the job queue process tasks",
     "The job queue is a FIFO backed by a SQLite table polled every 500ms.",
     ["file:engram/queue.py:71"],
     "The queue subsystem is AUTOMATED end-to-end and SHIPPED with flawless reliability."),
    ("session", "how are sessions tracked",
     "Sessions are keyed by a UUID stored in the session table with a TTL of 30 minutes.",
     ["file:engram/session.py:9"],
     "Session handling is MERGED, hardened and AUTHORIZED for enterprise scale."),
    ("metrics", "how are latency metrics collected",
     "Latency metrics are recorded as p50/p95/p99 histograms per endpoint.",
     ["file:engram/metrics.py:40"],
     "The metrics pipeline is production-ready, fully TESTED and MONITORED with no gaps."),
    ("migrate", "how are schema migrations applied",
     "Schema migrations run sequentially at startup guarded by a version table.",
     ["file:engram/migrate.py:23"],
     "Migrations are bulletproof, COMPLETO and SHIPPED with guaranteed rollback safety."),
]

K = 3


def _gate_status(prop: str, verified_by: list[str]) -> str:
    """Real gate verdict -> the status the live write path would assign."""
    g = run_validation_gate(
        proposition=prop, verified_by=verified_by, topic=None, agent=None,
        validate="standard",
    )
    return "model_claim" if g.action == "persist" else "quarantined"


def main() -> None:
    facts = []  # (id, prop, is_confab, status, vec)
    for i, (_topic, _q, tprop, tvb, cprop) in enumerate(PAIRS):
        facts.append((f"t{i}", tprop, False, _gate_status(tprop, tvb),
                      embedding.encode(embedding.as_passage(tprop))))
        facts.append((f"c{i}", cprop, True, _gate_status(cprop, []),
                      embedding.encode(embedding.as_passage(cprop))))

    # Gate classification quality
    confab = [f for f in facts if f[2]]
    true_ = [f for f in facts if not f[2]]
    confab_quarantined = sum(1 for f in confab if f[3] == "quarantined")
    true_kept = sum(1 for f in true_ if f[3] != "quarantined")

    def recallable(gated: bool):
        return [f for f in facts if (not gated) or f[3] != "quarantined"]

    def leak_rate(gated: bool) -> tuple[float, float]:
        naive_recallable = recallable(gated)
        mat = np.vstack([f[4] for f in naive_recallable])
        leaks, precisions = [], []
        for (_topic, q, *_rest) in PAIRS:
            qv = embedding.encode(embedding.as_query(q))
            sims = mat @ qv
            topk = np.argsort(-sims)[:K]
            picked = [naive_recallable[j] for j in topk]
            n_confab = sum(1 for p in picked if p[2])
            leaks.append(1.0 if n_confab > 0 else 0.0)
            precisions.append(sum(1 for p in picked if not p[2]) / len(picked))
        return float(np.mean(leaks)), float(np.mean(precisions))

    naive_leak, naive_prec = leak_rate(gated=False)
    gated_leak, gated_prec = leak_rate(gated=True)

    # Honest boundary (B2): the keyword L1 detectors catch HYPE/completion confab,
    # NOT subtle factual confab (plausible FALSE claims with invented specifics and
    # no trigger words). Measure it so the bench tells the whole truth, not just the
    # flattering 100%->0% on blatant hype.
    SUBTLE_CONFAB = [
        "The cache uses a least-recently-used policy with a 4096 entry ceiling.",
        "Sessions expire after 45 minutes of inactivity by default.",
        "The retry backoff doubles starting from 500 milliseconds.",
        "Rate limiting allows 250 requests per minute per API key.",
        "Backups are kept for 14 daily snapshots before rotation.",
    ]
    # (a) L1-only path: gate with NO corpus (agent=None) — keyword detectors
    # only. This is what catches HYPE confab; blind to subtle factual confab.
    subtle_l1_caught = sum(
        1 for p in SUBTLE_CONFAB
        if run_validation_gate(proposition=p, verified_by=[], topic=None,
                               agent=None, validate="standard").action != "persist"
    )
    # (b) L3 path WITH corpus: the TRUE fact is already in memory and the gate
    # runs validate='full' (or the hippo_validate_claim tool is called). The
    # numeric-quantity contradiction detector (sibling of the year-disjoint
    # rule) flags a claim that states a DIFFERENT value for the same unit.
    _corpus = [_BenchFact(f"t{i}", tprop)
               for i, (_t, _q, tprop, _vb, _c) in enumerate(PAIRS)]
    _agent = _BenchAgent(_corpus)
    subtle_l3_caught = sum(
        1 for p in SUBTLE_CONFAB
        if validate_claim(_agent, p).get("verdict") == "contradicted"
    )

    res = {
        "bench": "anti-confabulation retrieval (USP eval)",
        "model": embedding.model_signature(),
        "n_pairs": len(PAIRS), "k": K,
        "gate_classification": {
            "confab_total": len(confab), "confab_quarantined": confab_quarantined,
            "true_total": len(true_), "true_kept_recallable": true_kept,
        },
        "NAIVE_vector_store": {
            "confab_leak_rate@k": round(naive_leak, 3),
            "recall_precision@k": round(naive_prec, 3),
        },
        "ENGRAM_gated": {
            "confab_leak_rate@k": round(gated_leak, 3),
            "recall_precision@k": round(gated_prec, 3),
        },
        "subtle_confab_limit": {
            "n": len(SUBTLE_CONFAB),
            "caught_L1_only_no_corpus": subtle_l1_caught,
            "caught_L3_with_corpus": subtle_l3_caught,
            "note": (
                "SUBTLE confab = plausible FALSE claims with invented specifics "
                "(numbers) and NO hype trigger words. (a) Keyword L1 detectors "
                f"alone catch {subtle_l1_caught}/{len(SUBTLE_CONFAB)} — blind to "
                "subtle factual confab. (b) WITH the "
                "TRUE fact in memory + L3 numeric-quantity contradiction "
                "(validate='full' / hippo_validate_claim), "
                f"{subtle_l3_caught}/{len(SUBTLE_CONFAB)} are caught: a "
                "claim asserting a DIFFERENT value for the same unit is flagged "
                "'contradicted'. The remaining miss is a unit-parsing edge "
                "('14 daily snapshots' vs '7-snapshot': adjective between number "
                "and noun). HONEST SCOPE: L3 catches confab that CONTRADICTS an "
                "existing fact; novel-domain confab (no prior fact) still needs an "
                "evidence-requirement layer. L3 is OFF on the default 'fast' write "
                "(cost/safety) — activating it on every write is a gated policy "
                "decision. Do NOT overclaim 'prevents all confabulation'."
            ),
        },
        "metric_note": (
            "confab_leak_rate@k = fraction of queries whose top-k recall contains a "
            "confabulated (hype/unverified) fact. Lower=better. NAIVE = plain vector "
            "store (no write-gate); ENGRAM_gated = real anti_confab_gate quarantines "
            "confab at write -> excluded from recall. Same corpus, same e5 embedding."
        ),
    }
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
