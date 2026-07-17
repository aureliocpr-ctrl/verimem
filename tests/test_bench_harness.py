"""Tests for FORGIA pezzo #27: multi-model bench harness.

The harness runs the same task suite under raw vs hippo conditions on
multiple LLM providers so we can quantify the active-memory uplift. The
harness must keep going when a single provider fails (quota, network),
recording the failure but not aborting the whole bench.

Five invariants verified:

  1. SUITE STARTUP — `default_suite()` returns non-empty cases, every
     validator returns the expected (bool, str) shape.

  2. RAW PATH — `run_case_raw` with a MockLLM produces a RunResult with
     success/tokens/latency populated when the answer matches; success
     False (no exception) when validator fails.

  3. AGGREGATE — `aggregate()` correctly groups by (condition,
     provider) and computes mean_tokens / success_rate.

  4. BROKEN-PROVIDER ISOLATION — a provider whose factory raises must
     produce a failure record per task, not abort the whole `run_full_bench`.

  5. HIPPO-WARM MEMORY SHARING — across N cases the factory is called
     ONCE (single agent shared), unlike cold which builds per-case.
"""
from __future__ import annotations

from verimem.bench_harness import (
    ProviderSpec,
    RunResult,
    TaskCase,
    _val_contains,
    _val_equals_int,
    aggregate,
    default_suite,
    run_case_raw,
    run_full_bench,
    run_suite_hippo_cold,
    run_suite_hippo_warm,
)
from verimem.llm import MockLLM

# ---------- Test 1: default suite + validators ------------------------


def test_default_suite_validators_run():
    s = default_suite()
    assert s, "default_suite is empty"
    for case in s:
        ok, msg = case.validator("dummy answer that won't match")
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


def test_validator_helpers_correct():
    v = _val_contains("paris")
    assert v("The capital is Paris.")[0]
    assert not v("nothing here")[0]

    v2 = _val_equals_int(42)
    assert v2("the answer is 42")[0]
    assert not v2("the answer is 41")[0]
    assert not v2("no number")[0]


# ---------- Test 2: run_case_raw -------------------------------------


def test_run_case_raw_success(monkeypatch):
    case = TaskCase(id="t", prompt="capital of france?",
                    validator=_val_contains("paris"))
    llm = MockLLM(scripted=["Paris is the capital."])
    r = run_case_raw(case, llm, provider="mock")
    assert r.success
    assert r.condition == "raw"
    assert r.provider == "mock"
    assert r.tokens > 0
    assert r.attempts == 1
    assert r.error == ""


def test_run_case_raw_validation_fails_no_exception():
    case = TaskCase(id="t", prompt="?",
                    validator=_val_equals_int(42))
    llm = MockLLM(scripted=["I don't know"])
    r = run_case_raw(case, llm, provider="mock")
    assert not r.success
    assert r.error == "", f"unexpected error path: {r.error}"


# ---------- Test 3: aggregate ----------------------------------------


def test_aggregate_computes_stats():
    rs = [
        RunResult(condition="raw", provider="p", task_id="t1",
                  success=True, tokens=10, latency_s=0.1, attempts=1),
        RunResult(condition="raw", provider="p", task_id="t2",
                  success=False, tokens=20, latency_s=0.2, attempts=1),
        RunResult(condition="hippo_warm", provider="p", task_id="t1",
                  success=True, tokens=50, latency_s=1.0, attempts=3),
    ]
    g = aggregate(rs)
    assert g[("raw", "p")]["success_rate"] == 0.5
    assert g[("raw", "p")]["n"] == 2
    assert abs(g[("raw", "p")]["mean_tokens"] - 15.0) < 1e-6
    assert g[("hippo_warm", "p")]["mean_attempts"] == 3.0


# ---------- Test 4: broken provider isolation ------------------------


def test_run_full_bench_isolates_broken_provider():
    cases = [TaskCase(id="t1", prompt="?", validator=_val_contains("ok"))]

    def good_factory():
        return MockLLM(scripted=["ok"])

    def bad_factory():
        raise RuntimeError("provider down")

    providers = [
        ProviderSpec(name="good", factory=good_factory),
        ProviderSpec(name="bad", factory=bad_factory),
    ]
    out = run_full_bench(cases, providers, conditions=["raw"])
    by_key = {(r.provider, r.condition): r for r in out}
    assert by_key[("good", "raw")].success
    assert not by_key[("bad", "raw")].success
    assert "factory failed" in by_key[("bad", "raw")].error.lower() or \
           "provider down" in by_key[("bad", "raw")].error


# ---------- Test 5: hippo_warm shares memory across cases ------------


def test_hippo_warm_builds_one_agent():
    cases = [
        TaskCase(id="t1", prompt="task one",
                 validator=_val_contains("never matches xyz123")),
        TaskCase(id="t2", prompt="task two",
                 validator=_val_contains("never matches xyz123")),
    ]
    builds = {"n": 0}

    def factory():
        builds["n"] += 1
        return MockLLM(scripted=["x"] * 50)

    out = run_suite_hippo_warm(cases, "mock", factory)
    assert builds["n"] == 1, f"expected 1 build, got {builds['n']}"
    assert len(out) == 2
    assert all(r.condition == "hippo_warm" for r in out)
    assert all(r.provider == "mock" for r in out)


def test_hippo_cold_builds_one_agent_per_case():
    cases = [
        TaskCase(id="t1", prompt="task one",
                 validator=_val_contains("never matches xyz123")),
        TaskCase(id="t2", prompt="task two",
                 validator=_val_contains("never matches xyz123")),
    ]
    builds = {"n": 0}

    def factory():
        builds["n"] += 1
        return MockLLM(scripted=["x"] * 50)

    out = run_suite_hippo_cold(cases, "mock", factory)
    assert builds["n"] == 2, f"expected 2 builds, got {builds['n']}"
    assert len(out) == 2
    assert all(r.condition == "hippo_cold" for r in out)


# ---------- Test 6: skill_compounding_suite -------------------------


def test_skill_compounding_suite_shape():
    """FORGIA pezzo #34: a richer task suite that should benefit from
    accumulated skills. Validators must work in isolation."""
    from verimem.bench_harness import skill_compounding_suite
    s = skill_compounding_suite()
    assert len(s) == 8, f"expected 8 tasks, got {len(s)}"
    seen_ids: set[str] = set()
    for case in s:
        assert case.id.startswith("digitsum-")
        assert case.id not in seen_ids, "duplicate task id"
        seen_ids.add(case.id)
        ok, msg = case.validator("dummy")
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


def test_skill_compounding_validators_correct():
    """Each task's validator must accept the right answer."""
    from verimem.bench_harness import skill_compounding_suite
    expected = {
        "digitsum-123": "6", "digitsum-456": "15", "digitsum-789": "24",
        "digitsum-1024": "7", "digitsum-4096": "19", "digitsum-13579": "25",
        "digitsum-24680": "20", "digitsum-99999": "45",
    }
    for case in skill_compounding_suite():
        ans = expected[case.id]
        ok, _ = case.validator(ans)
        assert ok, f"validator rejected the right answer for {case.id}: {ans}"
        ok_wrong, _ = case.validator("0")
        assert not ok_wrong, f"validator accepted '0' for {case.id}"


# ---------- Test 7: memory_recall_suite -----------------------------


def test_memory_recall_suite_shape():
    """FORGIA pezzo #39: paired seed/query tasks. 6 tasks (3 seed, 3 query)."""
    from verimem.bench_harness import memory_recall_suite
    s = memory_recall_suite()
    assert len(s) == 6
    seeds = [c for c in s if c.id.startswith("seed-")]
    queries = [c for c in s if c.id.startswith("query-")]
    assert len(seeds) == 3
    assert len(queries) == 3
    # Seed validators accept "ok"; query validators check the actual seed value.
    for c in seeds:
        assert c.validator("ok")[0]
    qmap = {
        "query-color": "ULTRAMARINE-7Q",
        "query-pet": "ZEPHYR-X42",
        "query-pin": "9173",
    }
    for c in queries:
        assert c.validator(qmap[c.id])[0], (
            f"query validator rejected the seed value: {c.id}"
        )
        assert not c.validator("totally wrong")[0]


# ---------- Test 8: hard_memory_recall_suite -----------------------


def test_hard_memory_recall_suite_shape():
    """FORGIA pezzo #41: 12 paired tasks (6 seed / 6 query)."""
    from verimem.bench_harness import hard_memory_recall_suite
    s = hard_memory_recall_suite()
    assert len(s) == 12
    seeds = [c for c in s if c.id.startswith("seed-")]
    queries = [c for c in s if c.id.startswith("query-")]
    assert len(seeds) == 6
    assert len(queries) == 6
    for c in seeds:
        assert c.validator("ok")[0]
    qmap = {
        "query-A-direct": "QUARTZ-ECHO",
        "query-B-paraphrased": "celadon-green",
        "query-C-synthesis": str(5742 + 2018),
        "query-D-direct": "matcha-latte-X3",
        "query-E-paraphrased": "ZEPHYR-X42",
        "query-F-direct": "RUBI-9000",
    }
    for c in queries:
        ok, _ = c.validator(qmap[c.id])
        assert ok, f"validator rejected the right answer for {c.id}"


# ---------- Test 9: aggregate_by_iter ----------------------------


def test_aggregate_by_iter_groups_by_iteration():
    """FORGIA pezzo #43: separating per iter lets us see the compounding."""
    from verimem.bench_harness import aggregate_by_iter
    rs = [
        RunResult(condition="hippo_warm", provider="p", task_id="t1",
                  success=False, tokens=10, latency_s=1.0, attempts=2,
                  extra={"iter": 0}),
        RunResult(condition="hippo_warm", provider="p", task_id="t2",
                  success=True, tokens=20, latency_s=0.5, attempts=1,
                  extra={"iter": 1}),
        RunResult(condition="hippo_warm", provider="p", task_id="t3",
                  success=True, tokens=15, latency_s=0.4, attempts=1,
                  extra={"iter": 1}),
    ]
    g = aggregate_by_iter(rs)
    # iter 0 separate from iter 1
    assert g[("hippo_warm", "p", 0)]["success_rate"] == 0.0
    assert g[("hippo_warm", "p", 0)]["n"] == 1
    assert g[("hippo_warm", "p", 1)]["success_rate"] == 1.0
    assert g[("hippo_warm", "p", 1)]["n"] == 2
    assert abs(g[("hippo_warm", "p", 1)]["mean_tokens"] - 17.5) < 1e-6


def test_aggregate_by_iter_default_iter_zero():
    """Records without an `iter` extra field must still aggregate (iter=0)."""
    from verimem.bench_harness import aggregate_by_iter
    rs = [
        RunResult(condition="raw", provider="p", task_id="t1",
                  success=True, tokens=5),
    ]
    g = aggregate_by_iter(rs)
    assert ("raw", "p", 0) in g


# ---------- Test 10: on_cell_done incremental save ----------------------


def test_on_cell_done_callback_invoked():
    """FORGIA pezzo #49: on_cell_done fires after every cell."""
    from verimem.bench_harness import (
        ProviderSpec,
        run_full_bench,
    )
    cases = [TaskCase(id="t1", prompt="?", validator=_val_contains("ok"))]
    cells_done = []

    def cb(results_so_far):
        cells_done.append(len(results_so_far))

    def factory():
        return MockLLM(scripted=["ok"])

    providers = [ProviderSpec(name="mock", factory=factory)]
    out = run_full_bench(cases, providers, conditions=["raw"], on_cell_done=cb)
    assert len(cells_done) == 1, f"expected 1 callback, got {len(cells_done)}"
    assert cells_done[0] == len(out)


def test_on_cell_done_failure_doesnt_break_run():
    """A raising callback must not abort the bench."""
    from verimem.bench_harness import (
        ProviderSpec,
        run_full_bench,
    )
    cases = [TaskCase(id="t1", prompt="?", validator=_val_contains("ok"))]

    def cb(results_so_far):
        raise RuntimeError("callback boom")

    def factory():
        return MockLLM(scripted=["ok"])

    out = run_full_bench(
        cases, [ProviderSpec(name="mock", factory=factory)],
        conditions=["raw"], on_cell_done=cb,
    )
    assert len(out) == 1, "bench must complete even when callback raises"


# ---------- Test 11: aggregate edge cases -----------------------


def test_aggregate_empty_results():
    """FORGIA pezzo #54: aggregate() must not crash on empty input."""
    from verimem.bench_harness import aggregate
    assert aggregate([]) == {}


def test_aggregate_all_errors():
    """All-error cell still produces stats (success_rate=0, n_errors>0)."""
    from verimem.bench_harness import aggregate
    rs = [
        RunResult(condition="raw", provider="p", task_id="t1",
                  success=False, error="boom"),
        RunResult(condition="raw", provider="p", task_id="t2",
                  success=False, error="boom"),
    ]
    g = aggregate(rs)
    assert g[("raw", "p")]["success_rate"] == 0.0
    assert g[("raw", "p")]["n_errors"] == 2.0
    assert g[("raw", "p")]["n"] == 2.0


# ---------- Test 12: from_jsonable + merge_results -----------------


def test_from_jsonable_round_trips():
    """FORGIA pezzo #74: to_jsonable -> from_jsonable preserves data."""
    from verimem.bench_harness import from_jsonable, to_jsonable
    rs = [
        RunResult(condition="raw", provider="p", task_id="t1",
                  success=True, tokens=10, latency_s=0.5, attempts=1,
                  extra={"k": "v"}),
        RunResult(condition="hippo_warm", provider="p", task_id="t2",
                  success=False, error="boom"),
    ]
    rs2 = from_jsonable(to_jsonable(rs))
    assert len(rs2) == 2
    assert rs2[0].condition == "raw"
    assert rs2[0].extra == {"k": "v"}
    assert rs2[0].tokens == 10
    assert rs2[1].error == "boom"
    assert not rs2[1].success


def test_merge_results_concatenates():
    from verimem.bench_harness import merge_results
    a = [RunResult("raw", "p1", "t1", success=True)]
    b = [RunResult("raw", "p2", "t2", success=False)]
    c = [RunResult("hippo", "p3", "t3", success=True)]
    out = merge_results(a, b, c)
    assert len(out) == 3
    assert {r.provider for r in out} == {"p1", "p2", "p3"}


# ---------- Test 13: aggregate_by_task -----------------------


def test_aggregate_by_task_groups_correctly():
    """FORGIA pezzo #75: group by (cond, provider, task_id)."""
    from verimem.bench_harness import aggregate_by_task
    rs = [
        RunResult("raw", "p", "t1", success=True, tokens=10),
        RunResult("raw", "p", "t1", success=False, tokens=20),
        RunResult("raw", "p", "t2", success=True, tokens=15),
    ]
    g = aggregate_by_task(rs)
    assert g[("raw", "p", "t1")]["success_rate"] == 0.5
    assert g[("raw", "p", "t1")]["n"] == 2
    assert g[("raw", "p", "t2")]["success_rate"] == 1.0
    assert g[("raw", "p", "t2")]["n"] == 1


# ---------- Test 14: merge_results edge cases -----------------------


def test_merge_results_empty_lists():
    """FORGIA pezzo #99: merge_results handles empty inputs."""
    from verimem.bench_harness import merge_results
    assert merge_results() == []
    assert merge_results([]) == []
    assert merge_results([], [], []) == []


def test_merge_results_preserves_order():
    """Order across input lists is preserved (concat not sorted)."""
    from verimem.bench_harness import merge_results
    a = [RunResult("raw", "p1", "t1", success=True)]
    b = [RunResult("raw", "p2", "t2", success=False)]
    out = merge_results(a, b)
    assert out[0].provider == "p1"
    assert out[1].provider == "p2"


def test_from_jsonable_handles_missing_extras():
    """Missing extras key → default empty dict."""
    from verimem.bench_harness import from_jsonable
    rs = from_jsonable([{
        "condition": "raw", "provider": "p", "task_id": "t",
        "success": True, "tokens": 5, "latency_s": 0.1, "attempts": 1,
        "error": "", "extra": None,
    }])
    assert rs[0].extra == {}


# ---------- Test 15: tokens_per_success (FORGIA #117) -------------


def test_aggregate_includes_tokens_per_success():
    """FORGIA pezzo #117: tokens / success quality signal."""
    rs = [
        RunResult("raw", "p", "t1", success=True, tokens=100),
        RunResult("raw", "p", "t2", success=True, tokens=200),
        RunResult("raw", "p", "t3", success=False, tokens=50),
    ]
    g = aggregate(rs)
    cell = g[("raw", "p")]
    # success_rate = 2/3 ≈ 0.667; mean_tokens = (100+200+50)/3 ≈ 116.67
    # tokens_per_success ≈ 116.67 / 0.667 ≈ 175
    import math
    assert math.isclose(cell["tokens_per_success"],
                         cell["mean_tokens"] / cell["success_rate"],
                         rel_tol=1e-9)


def test_aggregate_tokens_per_success_inf_on_zero_success():
    """All-fail cell → tokens_per_success = +inf."""
    rs = [
        RunResult("raw", "p", "t1", success=False, tokens=100),
        RunResult("raw", "p", "t2", success=False, tokens=50),
    ]
    g = aggregate(rs)
    import math
    assert math.isinf(g[("raw", "p")]["tokens_per_success"])
