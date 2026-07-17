"""Cycle #50 — held-out retrieval bench: with-Engram vs without-Engram.

THE HONEST PROXY QUESTION:
  Engram claims "memory makes Claude smarter". The full end-to-end test
  (live LLM with vs without memory across N agentic tasks) is expensive
  ($20-50 per run with real API providers) and noisy. This bench
  measures the PREREQUISITE that the end-to-end claim depends on:
  given a held-out query semantically close to a stored fact, can
  Engram's retrieval surface the relevant fact in the top-K?

  If retrieval @ K=5 has 0 precision, no downstream agent benefit is
  possible — the LLM never sees the relevant memory.
  If retrieval @ K=5 has >50% precision, agent benefit is mechanically
  available (whether it translates to better final answers is a
  separate question for #50b).

Setup:
  - Pre-populate a fresh SemanticMemory with 100 realistic facts
    spanning 10 topics (10 facts per topic).
  - Generate 30 held-out queries that paraphrase or generalize a
    specific seed fact (so the ground-truth retrieval target is known).
  - Run two conditions:
      A) WITH-ENGRAM: hippo_facts_recall(query, k=5)
         — semantic search over the 100-fact corpus
      B) WITHOUT-ENGRAM: random 5-fact sample
         — baseline of what a memoryless agent would see if forced
         to pick K facts at random; expected precision ~ 5/100 = 5%

Metrics per condition:
  - Precision@5: fraction of held-out queries where the gold fact
    appears in top-5
  - MRR (Mean Reciprocal Rank): 1/rank of gold fact in top-K, averaged
    across queries (0 if not in top-K)
  - Mean cosine similarity of top-1 result

The bench writes data/bench_retrieval_held_out.json and prints a
table. Acceptance: WITH-ENGRAM precision@5 must be ≥ 10× the
WITHOUT-ENGRAM baseline (otherwise the retrieval claim doesn't hold).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Force offline + CPU for reproducibility across machines.
os.environ.setdefault("HIPPO_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("PYTHONUTF8", "1")
os.environ["ENGRAM_RECALL_RERANK"] = "0"  # CE default-ON since 2026-06-10 — historical bi-encoder numbers

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

tmp = Path(tempfile.mkdtemp(prefix="cycle50-retrieval-"))
os.environ["HIPPO_DATA_DIR"] = str(tmp)
os.environ["ENGRAM_DATA_DIR"] = str(tmp)

from verimem.semantic import Fact, SemanticMemory  # noqa: E402

# ---------------------------------------------------------------------------
# Seed corpus: 100 facts across 10 topics — varied, realistic
# ---------------------------------------------------------------------------

_CORPUS: list[tuple[str, str]] = [
    # topic -> proposition
    ("project/auth", "The auth.py module uses bcrypt with cost factor 12"),
    ("project/auth", "Session tokens expire after 24 hours of inactivity"),
    ("project/auth", "Failed login attempts trigger a 5-minute lockout after 5 tries"),
    ("project/auth", "Password reset emails are sent via SendGrid"),
    ("project/auth", "Two-factor auth uses TOTP with 30-second windows"),
    ("project/auth", "API keys are rotated every 90 days automatically"),
    ("project/auth", "JWT tokens are signed with HS256 and a 32-byte secret"),
    ("project/auth", "OAuth integration supports Google and GitHub providers"),
    ("project/auth", "Login endpoint is rate-limited to 10 requests per minute per IP"),
    ("project/auth", "User passwords must be at least 12 characters with mixed case"),
    ("project/database", "Primary database is PostgreSQL 15 hosted on AWS RDS"),
    ("project/database", "Connection pool size is set to 20 max connections"),
    ("project/database", "Read replicas exist in us-east-1 and eu-west-1 regions"),
    ("project/database", "Database backups run nightly at 03:00 UTC"),
    ("project/database", "Schema migrations use Alembic with up/down scripts"),
    ("project/database", "Indexes on users.email and orders.created_at are required"),
    ("project/database", "Foreign keys enforce ON DELETE CASCADE for user records"),
    ("project/database", "The orders table is partitioned by month for performance"),
    ("project/database", "Stale connections are reaped after 5 minutes of idle time"),
    ("project/database", "Read-only queries use a dedicated replica connection pool"),
    ("project/frontend", "The React app uses Vite 5 as the build tool"),
    ("project/frontend", "State management is handled by Zustand stores"),
    ("project/frontend", "Tailwind CSS is configured with a custom color palette"),
    ("project/frontend", "Routing uses React Router v6 with lazy-loaded routes"),
    ("project/frontend", "API calls go through a shared axios instance with interceptors"),
    ("project/frontend", "Forms use react-hook-form with zod validation schemas"),
    ("project/frontend", "Theme toggle persists user choice in localStorage"),
    ("project/frontend", "Component tests use Vitest with React Testing Library"),
    ("project/frontend", "Production bundle is split by route via dynamic imports"),
    ("project/frontend", "Service worker caches static assets for offline use"),
    ("project/deploy", "Production deploys are automated via GitHub Actions on tag push"),
    ("project/deploy", "Staging environment redeploys on every push to main"),
    ("project/deploy", "Container images are stored in GitHub Container Registry"),
    ("project/deploy", "Kubernetes manifests use Kustomize for environment overlays"),
    ("project/deploy", "Database migrations run as a pre-deploy hook in the helm chart"),
    ("project/deploy", "Rollback procedure is documented in docs/runbook/rollback.md"),
    ("project/deploy", "Production cluster runs on EKS with 3 worker nodes"),
    ("project/deploy", "Secrets are pulled from AWS Secrets Manager at pod startup"),
    ("project/deploy", "Health checks ping /healthz with a 5-second interval"),
    ("project/deploy", "Blue-green deployments use Argo Rollouts for traffic shifting"),
    ("preferences/aurelio", "Aurelio prefers Python over JavaScript for backend code"),
    ("preferences/aurelio", "Aurelio expects responses in Italian by default"),
    ("preferences/aurelio", "Aurelio runs Claude Code on Windows 11 with miniconda Python"),
    ("preferences/aurelio", "Aurelio values brevity over verbose explanations"),
    ("preferences/aurelio", "Aurelio requires TDD with critic-orchestrator validation"),
    ("preferences/aurelio", "Aurelio is the CEO directing technical decisions"),
    ("preferences/aurelio", "Aurelio uses Engram for persistent cross-session memory"),
    ("preferences/user", "User email is user@example.com"),
    ("preferences/aurelio", "Aurelio prefers main-line trunk-based development workflow"),
    ("preferences/aurelio", "Aurelio reviews PRs personally before merge"),
    ("knowledge/algorithms", "Binary search has O(log n) time complexity"),
    ("knowledge/algorithms", "Quicksort has O(n log n) average but O(n^2) worst case"),
    ("knowledge/algorithms", "Dijkstra's algorithm finds shortest paths in weighted graphs"),
    ("knowledge/algorithms", "Bloom filters give false positives but never false negatives"),
    ("knowledge/algorithms", "Consistent hashing minimizes data movement during resharding"),
    ("knowledge/algorithms", "MapReduce splits work into map then reduce phases"),
    ("knowledge/algorithms", "B-trees keep all leaves at the same depth for balanced reads"),
    ("knowledge/algorithms", "LRU cache eviction removes the least recently accessed item"),
    ("knowledge/algorithms", "Topological sort orders nodes by dependency in a DAG"),
    ("knowledge/algorithms", "Bellman-Ford handles negative-weight edges, Dijkstra does not"),
    ("knowledge/python", "List comprehensions are faster than equivalent for loops"),
    ("knowledge/python", "asyncio is single-threaded with cooperative concurrency"),
    ("knowledge/python", "Dataclasses provide __init__ and __repr__ automatically"),
    ("knowledge/python", "Context managers ensure cleanup via __enter__ and __exit__"),
    ("knowledge/python", "Type hints are runtime-introspectable via typing.get_type_hints"),
    ("knowledge/python", "Walrus operator := allows assignment inside expressions"),
    ("knowledge/python", "f-strings are faster than .format() or % formatting"),
    ("knowledge/python", "GIL prevents true parallel execution of pure-Python code"),
    ("knowledge/python", "Generators yield values lazily and preserve state between yields"),
    ("knowledge/python", "Decorators wrap functions to add behavior without modifying them"),
    ("lessons/debugging", "Always check if function is actually called before assuming logic bug"),
    ("lessons/debugging", "Bisect to find regression — git bisect or binary file search"),
    ("lessons/debugging", "Reproduce locally before debugging — flaky reports waste time"),
    ("lessons/debugging", "Add print statements at suspect boundaries to trace data flow"),
    ("lessons/debugging", "Read the actual error message, not the inferred meaning"),
    ("lessons/debugging", "Distinguish symptoms from root cause before patching"),
    ("lessons/debugging", "Silent failures hide bugs — log every exception caught"),
    ("lessons/debugging", "Verify assumption with hello world before complex setup"),
    ("lessons/debugging", "Check environment differences between local and CI"),
    ("lessons/debugging", "Bug reports without reproduction steps are nearly useless"),
    ("api/endpoints", "POST /api/users creates a user with email, name, password"),
    ("api/endpoints", "GET /api/orders returns paginated list of user's orders"),
    ("api/endpoints", "DELETE /api/sessions/:id logs out a specific session"),
    ("api/endpoints", "PATCH /api/users/:id updates user profile fields"),
    ("api/endpoints", "POST /api/payments creates a Stripe payment intent"),
    ("api/endpoints", "GET /api/health returns service status and version info"),
    ("api/endpoints", "POST /api/auth/refresh exchanges refresh for access token"),
    ("api/endpoints", "GET /api/admin/metrics requires admin role authentication"),
    ("api/endpoints", "POST /api/uploads accepts multipart files up to 100 MB"),
    ("api/endpoints", "GET /api/search performs full-text search via Elasticsearch"),
    ("ops/incidents", "Incident #142 was caused by an unindexed query in production"),
    ("ops/incidents", "Memory leak in worker pool fixed by recycling after 1000 jobs"),
    ("ops/incidents", "CDN cache poisoning resolved by purging and re-validating headers"),
    ("ops/incidents", "Database deadlock during checkout fixed by reordering locks"),
    ("ops/incidents", "Slow SQL query optimized via composite index on (user_id, status)"),
    ("ops/incidents", "Connection pool exhaustion under load fixed by increasing max_conns"),
    ("ops/incidents", "Disk full on /var/log resolved by adding logrotate config"),
    ("ops/incidents", "TLS cert expired silently — added monitoring with 14-day alert"),
    ("ops/incidents", "Race condition in cron job fixed by adding lock file"),
    ("ops/incidents", "Slow startup time reduced via lazy import of heavy modules"),
]

# 30 held-out queries: paraphrases of corpus facts. (query, idx_of_gold_fact_in_corpus)
_QUERIES: list[tuple[str, int]] = [
    ("What hashing algorithm does the auth module use?", 0),
    ("How long until a session expires?", 1),
    ("What happens after too many failed logins?", 2),
    ("Where is the Postgres database hosted?", 10),
    ("What is the max connection pool size?", 11),
    ("Which build tool does the frontend use?", 20),
    ("How is state managed in the React app?", 21),
    ("How do production deploys get triggered?", 30),
    ("Which container registry do we use?", 32),
    ("Which language does Aurelio prefer for backend?", 40),
    ("What language should I respond in?", 41),
    ("What is Aurelio's role on this project?", 45),
    ("What is the time complexity of binary search?", 50),
    ("Which algorithm handles negative edge weights?", 59),
    ("Are list comprehensions faster than for loops?", 60),
    ("Does asyncio use multiple threads?", 61),
    ("Why does GIL matter in Python?", 67),
    ("What should I check before assuming a logic bug?", 70),
    ("How do I find which commit introduced a regression?", 71),
    ("Why is silent failure a problem in debugging?", 76),
    ("How do I create a new user via API?", 80),
    ("Which endpoint logs out a specific session?", 82),
    ("What does the payments endpoint do?", 84),
    ("What caused incident 142?", 90),
    ("How was the memory leak in workers fixed?", 91),
    ("What fixed the database deadlock?", 93),
    ("How was the cron job race condition fixed?", 98),
    ("How long until the auth lockout ends?", 2),  # paraphrase
    ("Is bcrypt actually used for password hashing?", 0),  # direct
    ("What rate limit applies to login attempts?", 8),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str,
                        default=str(REPO / "data" / "bench_retrieval_held_out.json"))
    args = parser.parse_args()

    print("=== Cycle #50 retrieval bench ===")
    print(f"  corpus:  {len(_CORPUS)} facts")
    print(f"  queries: {len(_QUERIES)} held-out paraphrases")
    print(f"  k:       {args.k}")
    print()

    store = SemanticMemory(db_path=tmp / "semantic.db")
    fact_ids: list[str] = []
    t0 = time.time()
    for topic, prop in _CORPUS:
        f = Fact(proposition=prop, topic=topic, confidence=0.95)
        store.store(f)
        fact_ids.append(f.id)
    t_seed = time.time() - t0
    print(f"Corpus seeded in {t_seed:.2f}s")
    print()

    # ----- WITH-ENGRAM -----
    print("Condition A: WITH-ENGRAM (hippo_facts_recall semantic)")
    rng = random.Random(args.seed)
    a_hits = 0
    a_rr = []  # reciprocal ranks
    a_top1_cos = []
    t0 = time.time()
    for query, gold_idx in _QUERIES:
        results = store.recall(query, k=args.k)
        gold_id = fact_ids[gold_idx]
        rank = None
        for i, (fact, score) in enumerate(results, start=1):
            if i == 1:
                a_top1_cos.append(score)
            if fact.id == gold_id:
                rank = i
                break
        if rank is not None:
            a_hits += 1
            a_rr.append(1.0 / rank)
        else:
            a_rr.append(0.0)
    t_a = time.time() - t0
    a_p = a_hits / len(_QUERIES)
    a_mrr = statistics.mean(a_rr) if a_rr else 0.0
    a_top1_mean = statistics.mean(a_top1_cos) if a_top1_cos else 0.0
    print(f"  precision@{args.k}: {a_p:.3f}  ({a_hits}/{len(_QUERIES)})")
    print(f"  MRR@{args.k}:       {a_mrr:.3f}")
    print(f"  mean top-1 cos:  {a_top1_mean:.3f}")
    print(f"  wall:            {t_a:.2f}s")
    print()

    # ----- WITHOUT-ENGRAM (random baseline) -----
    print("Condition B: WITHOUT-ENGRAM (random k-sample baseline)")
    rng = random.Random(args.seed)
    b_hits = 0
    b_rr = []
    t0 = time.time()
    for _query, gold_idx in _QUERIES:
        gold_id = fact_ids[gold_idx]
        sample_idxs = rng.sample(range(len(fact_ids)), args.k)
        rank = None
        for i, idx in enumerate(sample_idxs, start=1):
            if fact_ids[idx] == gold_id:
                rank = i
                break
        if rank is not None:
            b_hits += 1
            b_rr.append(1.0 / rank)
        else:
            b_rr.append(0.0)
    t_b = time.time() - t0
    b_p = b_hits / len(_QUERIES)
    b_mrr = statistics.mean(b_rr) if b_rr else 0.0
    print(f"  precision@{args.k}: {b_p:.3f}  ({b_hits}/{len(_QUERIES)})")
    print(f"  MRR@{args.k}:       {b_mrr:.3f}")
    print(f"  wall:            {t_b:.2f}s")
    print()

    # ----- Comparison -----
    ratio = a_p / b_p if b_p > 0 else float("inf")
    print("=== Comparison ===")
    print(f"  precision ratio A/B:   {ratio:.1f}×")
    print(f"  MRR ratio A/B:         "
          f"{a_mrr / b_mrr if b_mrr > 0 else float('inf'):.1f}×")
    print()

    # Acceptance criterion
    ACCEPT_RATIO = 10.0
    verdict = "PASS" if ratio >= ACCEPT_RATIO else "FAIL"
    print(f"  acceptance ≥{ACCEPT_RATIO:.0f}×: {verdict}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "n_corpus": len(_CORPUS),
        "n_queries": len(_QUERIES),
        "k": args.k,
        "seed": args.seed,
        "with_engram": {
            "precision_at_k": a_p,
            "mrr": a_mrr,
            "mean_top1_cos": a_top1_mean,
            "wall_s": round(t_a, 3),
            "hits": a_hits,
        },
        "without_engram": {
            "precision_at_k": b_p,
            "mrr": b_mrr,
            "wall_s": round(t_b, 3),
            "hits": b_hits,
        },
        "ratio_precision_a_over_b": ratio,
        "verdict": verdict,
    }, indent=2), encoding="utf-8")
    print(f"  full JSON:           {out_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
