"""FORGIA pezzo #27 — Multi-model bench harness: with-vs-without HippoAgent.

The harness runs the SAME task suite under three conditions and groups
results by (condition, provider) so we can quantify the active-memory
uplift across heterogeneous LLMs.

Conditions:

  raw         — single-shot LLM call, no memory / skills / sleep.
                Baseline; measures the model's "cold" capability.

  hippo_cold  — fresh HippoAgent built per task. The agent has wake/sleep
                machinery active but starts with empty memory each time.
                Isolates the value of the wake-loop scaffolding from the
                value of accumulated experience.

  hippo_warm  — single HippoAgent shared across all tasks; an optional
                sleep cycle fires every K tasks. This is where the
                forged primitives (memory + skills + DG/TCM/Hopfield/SR)
                actually pay off — second-time-around tasks get to use
                episodes and skills the agent learned earlier.

Resilience:

  Provider failures (network, quota, 5xx) are isolated per-provider.
  A failing factory or wake exception produces a `RunResult` with
  `success=False, error=...` so aggregation stays honest, and the
  loop continues with the next provider/condition.

Output is a flat list of `RunResult` records. `aggregate()` groups them
by (condition, provider) and emits headline stats (success_rate, mean
tokens, mean latency, mean attempts). `to_jsonable()` makes the records
serialisable for downstream reporting.
"""
from __future__ import annotations

import dataclasses
import re
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .agent import HippoAgent
from .observability import emit, get_log

log = get_log()


# ---- Task case + validator helpers --------------------------------------


@dataclass(frozen=True)
class TaskCase:
    """One benchmark item.

    `validator` takes the agent's final answer and returns
    (success: bool, message: str). The harness does not interpret the
    message; it's surfaced for debugging.
    """
    id: str
    prompt: str
    validator: Callable[[str], tuple[bool, str]]


def _val_contains(needle: str, *, case_insensitive: bool = True
                  ) -> Callable[[str], tuple[bool, str]]:
    """Validator: success iff `needle` appears in answer."""
    def _v(answer: str) -> tuple[bool, str]:
        a = (answer or "").lower() if case_insensitive else (answer or "")
        n = needle.lower() if case_insensitive else needle
        return (n in a, f"expect substring '{needle}'")
    return _v


def _val_equals_int(expected: int) -> Callable[[str], tuple[bool, str]]:
    """Validator: success iff first integer in answer equals `expected`."""
    pat = re.compile(r"-?\d+")

    def _v(answer: str) -> tuple[bool, str]:
        m = pat.search(answer or "")
        if not m:
            return (False, f"no integer in answer; expected {expected}")
        try:
            return (int(m.group()) == expected, f"expect int {expected}")
        except ValueError:
            return (False, f"unparseable int in {m.group()!r}")
    return _v


def default_suite() -> list[TaskCase]:
    """Built-in 5-task trivia suite — fast, deterministic, every model passes.

    Mostly for transport / harness verification. The token + latency
    *gap* between raw and hippo conditions on this suite measures
    HippoAgent's structural overhead, not its value.
    """
    return [
        TaskCase(id="capital", validator=_val_contains("paris"),
                 prompt="What is the capital of France? "
                        "Answer with just the city name."),
        TaskCase(id="math2plus2", validator=_val_equals_int(4),
                 prompt="Compute 2+2. Answer with the integer only."),
        TaskCase(id="reverse", validator=_val_contains("olleh"),
                 prompt="Reverse the string 'hello'. "
                        "Answer with just the result."),
        TaskCase(id="echo", validator=_val_contains("hippoagent"),
                 prompt="Repeat back the word 'hippoagent' exactly."),
        TaskCase(id="format", validator=_val_contains("[1, 2, 3]"),
                 prompt="Format the list [1,2,3] as a JSON array. "
                        "Answer with just the JSON, e.g. [1, 2, 3]."),
    ]


def hard_memory_recall_suite() -> list[TaskCase]:
    """12 paired tasks (6 seed / 6 query) — harder than memory_recall_suite.

    Three classes of recall difficulty:
      a) **Direct token recall**: same as the easy suite — seed `X = "Y"`,
         query "what was Y?".
      b) **Paraphrased query**: seed mentions "color", query asks
         "hue I told you about".
      c) **Multi-step recall**: seed embeds two facts; the query asks
         the agent to combine them ("the pin code XOR the year").

    A correct retrieval AND a correct synthesis are both needed —
    so a model that retrieves the wrong episode (or no episode at all)
    fails even though raw mode also fails.
    """
    return [
        # --- seeds ----------------------------------------------------
        TaskCase(id="seed-A", validator=_val_contains("ok"),
                 prompt="Remember this fact: my codename is QUARTZ-ECHO. "
                        "Reply with just 'ok'."),
        TaskCase(id="seed-B", validator=_val_contains("ok"),
                 prompt="Remember this fact: the favourite hue I always pick "
                        "is celadon-green. Reply with just 'ok'."),
        TaskCase(id="seed-C", validator=_val_contains("ok"),
                 prompt="Remember this fact: my secret pin code is 5742, "
                        "and the year I joined was 2018. Reply with just 'ok'."),
        TaskCase(id="seed-D", validator=_val_contains("ok"),
                 prompt="Remember this fact: my preferred drink is "
                        "matcha-latte-X3. Reply with just 'ok'."),
        TaskCase(id="seed-E", validator=_val_contains("ok"),
                 prompt="Remember this fact: my pet's name is "
                        "ZEPHYR-X42. Reply with just 'ok'."),
        TaskCase(id="seed-F", validator=_val_contains("ok"),
                 prompt="Remember this fact: my favourite kitchen tool is "
                        "a moka-RUBI-9000. Reply with just 'ok'."),
        # --- queries --------------------------------------------------
        # direct token recall
        TaskCase(id="query-A-direct", validator=_val_contains("quartz-echo"),
                 prompt="What was my codename? Answer with just the value."),
        TaskCase(id="query-D-direct", validator=_val_contains("matcha-latte-x3"),
                 prompt="What was my preferred drink? Answer with just the value."),
        # paraphrased
        TaskCase(id="query-B-paraphrased",
                 validator=_val_contains("celadon-green"),
                 prompt="What hue did I tell you about earlier? "
                        "Answer with just the value."),
        TaskCase(id="query-E-paraphrased",
                 validator=_val_contains("zephyr-x42"),
                 prompt="What's the name of the animal that lives with me? "
                        "Answer with just the name."),
        # multi-step (needs the fact retrieved + a synthesis)
        TaskCase(id="query-C-synthesis",
                 validator=_val_equals_int(5742 + 2018),
                 prompt="Compute the SUM of the secret pin code I told you "
                        "and the year I joined. Answer with the integer."),
        TaskCase(id="query-F-direct",
                 validator=_val_contains("rubi-9000"),
                 prompt="What kitchen tool did I tell you about? "
                        "Answer with just the value."),
    ]


def memory_recall_suite() -> list[TaskCase]:
    """6 paired tasks (3 set, 3 query) that REQUIRE long-term memory.

    Setup tasks ("remember X = Y") seed knowledge that the query tasks
    ("what was Y?") later need. With **raw** mode, every task is a
    blank slate — the queries cannot succeed because the model has no
    way to recall the seed. With **hippo_warm**, the seeds are stored
    as episodes and the query phase can retrieve them via semantic
    recall — predicted success ≫ raw.

    This is the suite that should make HippoAgent's value visible
    where the others can't:
      - default suite: same accuracy across conditions (trivia).
      - skill_compounding: same accuracy, different latency (macros).
      - memory_recall: DIFFERENT ACCURACY (raw fails, warm succeeds).

    Design notes:
      - The seeds use unusual phrases so a non-cheating model can't
        guess from training.
      - Validators are tight (specific token in answer).
      - Queries arrive AFTER all seeds so the consolidate_every
        argument has a chance to fire mid-suite.
    """
    return [
        # --- seed phase ----------------------------------------------------
        TaskCase(id="seed-color", validator=_val_contains("ok"),
                 prompt="Remember this fact: my favourite color is "
                        "ULTRAMARINE-7Q. Reply with just 'ok'."),
        TaskCase(id="seed-pet", validator=_val_contains("ok"),
                 prompt="Remember this fact: my pet's name is "
                        "ZEPHYR-X42. Reply with just 'ok'."),
        TaskCase(id="seed-pin", validator=_val_contains("ok"),
                 prompt="Remember this fact: my favourite pin code is "
                        "9173. Reply with just 'ok'."),
        # --- query phase ---------------------------------------------------
        TaskCase(id="query-color", validator=_val_contains("ultramarine-7q"),
                 prompt="What was my favourite color? "
                        "Answer with just the value."),
        TaskCase(id="query-pet", validator=_val_contains("zephyr-x42"),
                 prompt="What was my pet's name? Answer with just the name."),
        TaskCase(id="query-pin", validator=_val_equals_int(9173),
                 prompt="What was my favourite pin code? "
                        "Answer with just the integer."),
    ]


def compositional_suite() -> list[TaskCase]:
    """FORGIA #182 — compositional generalization at increasing depth.

    Tests whether the agent learns *atomic* skills and composes them
    on tasks that require chaining 1, 2, or 3 of them in sequence.

    Phase 1 (seed): teach ROT3 (Caesar +3) and REVERSE via worked examples.
    Phase 2 (Lv1):  apply 1 skill on a fresh input.
    Phase 3 (Lv2):  apply 2 skills in sequence.
    Phase 4 (Lv3):  apply 3 skills in sequence.

    The hypothesis: hippo conditions (cold/warm) should beat raw on
    Lv2 and especially Lv3, where chaining 3 transformations is
    error-prone for a single-shot LLM. The gap should *widen with depth*
    — that's the scaling signal.
    """
    return [
        # --- Seed phase: teach the two atomic skills -----------------------
        TaskCase(
            id="seed-rot3",
            validator=_val_contains("ok"),
            prompt=(
                "Define the operation ROT3: shift each letter forward by 3 "
                "positions in the alphabet (a→d, b→e, ... w→z, x→a, y→b, "
                "z→c). Examples: ROT3('cat') = 'fdw'. ROT3('xyz') = 'abc'. "
                "Acknowledge with just 'ok'."
            ),
        ),
        TaskCase(
            id="seed-reverse",
            validator=_val_contains("ok"),
            prompt=(
                "Define the operation REVERSE: invert the character order "
                "of a string. Examples: REVERSE('cat') = 'tac'. "
                "REVERSE('hello') = 'olleh'. Acknowledge with just 'ok'."
            ),
        ),
        # --- Lv1: 1 skill --------------------------------------------------
        TaskCase(
            id="lv1-rot3-quick",
            validator=_val_contains("txlfn"),
            prompt="Apply ROT3 to 'quick'. Reply with the result only.",
        ),
        TaskCase(
            id="lv1-rev-puzzle",
            validator=_val_contains("elzzup"),
            prompt="Apply REVERSE to 'puzzle'. Reply with the result only.",
        ),
        # --- Lv2: 2 skills chained -----------------------------------------
        TaskCase(
            id="lv2-rot3-rev-flame",
            validator=_val_contains("hpdoi"),
            prompt=(
                "Apply ROT3, then REVERSE, to 'flame'. "
                "Reply with the result only."
            ),
        ),
        TaskCase(
            id="lv2-rev-rot3-stone",
            validator=_val_contains("hqrwv"),
            prompt=(
                "Apply REVERSE, then ROT3, to 'stone'. "
                "Reply with the result only."
            ),
        ),
        # --- Lv3: 3 skills chained -----------------------------------------
        TaskCase(
            id="lv3-three-bridge",
            validator=_val_contains("kmjoxh"),
            prompt=(
                "Apply ROT3, then REVERSE, then ROT3 again, to 'bridge'. "
                "Reply with the result only."
            ),
        ),
        TaskCase(
            id="lv3-three-planet",
            validator=_val_contains("sodqhw"),
            prompt=(
                "Apply REVERSE, then ROT3, then REVERSE again, to 'planet'. "
                "Reply with the result only."
            ),
        ),
        # --- Lv4: 4 skills chained -----------------------------------------
        TaskCase(
            id="lv4-four-crystal",
            validator=_val_contains("ixeyzgr"),
            prompt=(
                "Apply ROT3, then REVERSE, then ROT3, then REVERSE again, "
                "to 'crystal'. Reply with the result only."
            ),
        ),
        TaskCase(
            id="lv4-four-thunder",
            validator=_val_contains("znatjkx"),
            prompt=(
                "Apply ROT3, then REVERSE, then ROT3, then REVERSE again, "
                "to 'thunder'. Reply with the result only."
            ),
        ),
        # --- Lv5: 5 skills chained -----------------------------------------
        TaskCase(
            id="lv5-five-magnetic",
            validator=_val_contains("vjpwncrl"),
            prompt=(
                "Apply ROT3, then REVERSE, then ROT3, then REVERSE, then ROT3 "
                "again, to 'magnetic'. Reply with the result only."
            ),
        ),
        TaskCase(
            id="lv5-five-forest",
            validator=_val_contains("zykxul"),
            prompt=(
                "Apply REVERSE, then ROT3, then REVERSE, then ROT3, then "
                "REVERSE again, to 'forest'. Reply with the result only."
            ),
        ),
    ]


def skill_compounding_suite() -> list[TaskCase]:
    """8 strongly-related tasks that should share a single skill.

    The setup: each task asks the agent to apply the SAME procedure
    (sum the digits of a number) to a different input. A wake-loop
    with active memory should:
      - on the first run, learn the procedure (extract digits, sum
        them, return the int);
      - on every subsequent run, retrieve the past episode + matching
        skill, retrieve the macro if it was compiled, and answer with
        ~zero LLM tokens via the procedural fast-path.

    A raw single-shot LLM has no memory and re-derives the procedure
    every time — same accuracy, constant per-task cost.

    Validator pins the integer in the answer; we don't care about
    surrounding prose. Every input is small enough that even a
    non-reasoning model gets the answer right.
    """
    inputs_and_expected = [
        ("123", 6),    # 1+2+3
        ("456", 15),   # 4+5+6
        ("789", 24),
        ("1024", 7),
        ("4096", 19),
        ("13579", 25),
        ("24680", 20),
        ("99999", 45),
    ]
    return [
        TaskCase(
            id=f"digitsum-{n}",
            validator=_val_equals_int(expected),
            prompt=(
                f"Sum the digits of {n} and return the integer result. "
                f"Answer with the integer only, no prose."
            ),
        )
        for n, expected in inputs_and_expected
    ]


# ---- Result record ------------------------------------------------------


@dataclass
class RunResult:
    """One measurement: (condition × provider × task) → outcome.

    On a clean validator-pass: `success=True, error=""`.
    On a clean validator-fail: `success=False, error=""`.
    On an exception: `success=False, error="<type>: <msg>"`.
    """
    condition: str
    provider: str
    task_id: str
    success: bool = False
    tokens: int = 0
    latency_s: float = 0.0
    attempts: int = 0
    error: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---- Single-task runners ------------------------------------------------


_RAW_SYSTEM = (
    "You are a precise assistant. Answer the user's question with the "
    "shortest correct answer. No preamble, no explanation."
)


def run_case_raw(case: TaskCase, llm: Any, *, provider: str = "?") -> RunResult:
    """Run one task with a raw LLM call — no memory, no skills, no tools."""
    t0 = time.perf_counter()
    try:
        resp = llm.complete(
            system=_RAW_SYSTEM,
            messages=[{"role": "user", "content": case.prompt}],
        )
        ok, _ = case.validator(resp.text)
        return RunResult(
            condition="raw", provider=provider, task_id=case.id,
            success=ok, tokens=resp.total_tokens,
            latency_s=time.perf_counter() - t0, attempts=1,
            extra={"answer": (resp.text or "")[:200]},
        )
    except Exception as exc:  # noqa: BLE001
        return RunResult(
            condition="raw", provider=provider, task_id=case.id,
            success=False, latency_s=time.perf_counter() - t0,
            error=f"{type(exc).__name__}: {exc}"[:300],
        )


def run_case_hippo(case: TaskCase, agent: HippoAgent, *,
                   provider: str = "?", condition: str = "hippo") -> RunResult:
    """Run one task through HippoAgent's wake loop."""
    t0 = time.perf_counter()
    try:
        wr = agent.run_task(
            task_id=case.id, task_text=case.prompt, validator=case.validator,
        )
        return RunResult(
            condition=condition, provider=provider, task_id=case.id,
            success=bool(wr.success),
            tokens=int(wr.episode.tokens_used or 0),
            latency_s=time.perf_counter() - t0,
            attempts=int(wr.episode.num_steps or 0),
            extra={
                "answer": (wr.episode.final_answer or "")[:200],
                "n_skills_retrieved": len(wr.skills_retrieved),
                # FORGIA #57: distinguish macro fast-path from full ReAct loop.
                "used_macro": bool(getattr(wr, "used_macro", False)),
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("bench_hippo_exception", error=str(exc), task_id=case.id)
        return RunResult(
            condition=condition, provider=provider, task_id=case.id,
            success=False, latency_s=time.perf_counter() - t0,
            error=f"{type(exc).__name__}: {exc}"[:300],
        )


# ---- Suite-level runners ------------------------------------------------


ProviderFactory = Callable[[], Any]


def _factory_failure_results(condition: str, provider_name: str,
                             cases: list[TaskCase], reason: str
                             ) -> list[RunResult]:
    return [RunResult(condition=condition, provider=provider_name,
                      task_id=c.id, success=False,
                      error=f"factory failed: {reason}"[:300])
            for c in cases]


def run_suite_raw(cases: list[TaskCase], provider_name: str,
                  llm_factory: ProviderFactory) -> list[RunResult]:
    """Build LLM once, then run every case with raw single-shot."""
    try:
        llm = llm_factory()
    except Exception as exc:  # noqa: BLE001
        return _factory_failure_results(
            "raw", provider_name, cases,
            f"{type(exc).__name__}: {exc}",
        )
    return [run_case_raw(c, llm, provider=provider_name) for c in cases]


def run_suite_hippo_cold(cases: list[TaskCase], provider_name: str,
                         llm_factory: ProviderFactory) -> list[RunResult]:
    """Each case gets a freshly-built HippoAgent — no shared memory."""
    out: list[RunResult] = []
    for c in cases:
        try:
            llm = llm_factory()
            agent = HippoAgent.build(llm=llm)
        except Exception as exc:  # noqa: BLE001
            out.append(RunResult(
                condition="hippo_cold", provider=provider_name, task_id=c.id,
                success=False,
                error=f"build failed: {type(exc).__name__}: {exc}"[:300],
            ))
            continue
        out.append(run_case_hippo(c, agent, provider=provider_name,
                                  condition="hippo_cold"))
    return out


def run_suite_hippo_warm(cases: list[TaskCase], provider_name: str,
                         llm_factory: ProviderFactory, *,
                         consolidate_every: int = 0) -> list[RunResult]:
    """Single agent shared across cases. consolidate_every>0 → sleep every K tasks."""
    try:
        llm = llm_factory()
        agent = HippoAgent.build(llm=llm)
    except Exception as exc:  # noqa: BLE001
        return _factory_failure_results(
            "hippo_warm", provider_name, cases,
            f"{type(exc).__name__}: {exc}",
        )
    out: list[RunResult] = []
    for i, c in enumerate(cases, start=1):
        out.append(run_case_hippo(c, agent, provider=provider_name,
                                  condition="hippo_warm"))
        if consolidate_every > 0 and i % consolidate_every == 0:
            try:
                agent.consolidate()
            except Exception as exc:  # noqa: BLE001
                log.warning("bench_consolidate_failed", error=str(exc))
    return out


# ---- Provider spec + full bench -----------------------------------------


@dataclass
class ProviderSpec:
    """Named provider factory.

    `factory` is invoked at most once per (provider, condition). For
    hippo_cold the factory may be invoked multiple times — once per task.
    """
    name: str
    factory: ProviderFactory


def run_full_bench(cases: list[TaskCase], providers: list[ProviderSpec], *,
                   conditions: list[str] | None = None,
                   consolidate_every: int = 2,
                   on_cell_done: Callable[[list[RunResult]], None] | None = None,
                   ) -> list[RunResult]:
    """Run every (condition × provider) combination on `cases`.

    A provider that crashes mid-condition only invalidates that
    condition's results — other (condition, provider) cells continue.

    `on_cell_done(results_so_far)` (FORGIA #49) is invoked after every
    (provider, condition) cell completes. Gives the caller a hook for
    incremental persistence (e.g. dump JSON to disk so a long-running
    bench can recover after a crash).
    """
    cond_list = list(conditions or ["raw", "hippo_cold", "hippo_warm"])
    out: list[RunResult] = []
    for prov in providers:
        for cond in cond_list:
            try:
                if cond == "raw":
                    out.extend(run_suite_raw(cases, prov.name, prov.factory))
                elif cond == "hippo_cold":
                    out.extend(run_suite_hippo_cold(cases, prov.name, prov.factory))
                elif cond == "hippo_warm":
                    out.extend(run_suite_hippo_warm(
                        cases, prov.name, prov.factory,
                        consolidate_every=consolidate_every,
                    ))
                else:
                    log.warning("bench_unknown_condition", condition=cond)
                    continue
                emit("bench_condition_done",
                     provider=prov.name, condition=cond, n_cases=len(cases))
            except Exception as exc:  # noqa: BLE001
                log.warning("bench_provider_aborted",
                            provider=prov.name, condition=cond, error=str(exc))
                out.extend([RunResult(
                    condition=cond, provider=prov.name, task_id=c.id,
                    success=False,
                    error=f"suite aborted: {type(exc).__name__}: {exc}"[:300],
                ) for c in cases])
            if on_cell_done is not None:
                try:
                    on_cell_done(out)
                except Exception as exc:  # noqa: BLE001
                    log.warning("bench_on_cell_done_failed", error=str(exc))
    return out


# ---- Aggregation --------------------------------------------------------


def aggregate(results: list[RunResult]
              ) -> dict[tuple[str, str], dict[str, float]]:
    """Group by (condition, provider). Compute headline stats.

    FORGIA pezzo #117: also reports `tokens_per_success` —
    mean_tokens / success_rate, useful as a single-number quality
    signal (lower is better). Infinity when success_rate is 0.
    """
    buckets: dict[tuple[str, str], list[RunResult]] = {}
    for r in results:
        buckets.setdefault((r.condition, r.provider), []).append(r)
    out: dict[tuple[str, str], dict[str, float]] = {}
    for key, rs in buckets.items():
        n = len(rs)
        succ = sum(1 for r in rs if r.success)
        toks = [r.tokens for r in rs]
        lats = [r.latency_s for r in rs]
        atts = [r.attempts for r in rs]
        errs = sum(1 for r in rs if r.error)
        success_rate = succ / n if n else 0.0
        mean_tokens = statistics.fmean(toks) if toks else 0.0
        out[key] = {
            "n": float(n),
            "success_rate": success_rate,
            "mean_tokens": mean_tokens,
            "mean_latency_s": statistics.fmean(lats) if lats else 0.0,
            "mean_attempts": statistics.fmean(atts) if atts else 0.0,
            "n_errors": float(errs),
            "tokens_per_success": (
                mean_tokens / success_rate if success_rate > 0 else float("inf")
            ),
        }
    return out


def aggregate_by_task(results: list[RunResult]
                       ) -> dict[tuple[str, str, str], dict[str, float]]:
    """FORGIA #75: group by (condition, provider, task_id).

    Useful for debugging: identifies which specific tasks fail in a
    cell. e.g. on `hard_memory_recall` the deepseek hippo_warm fail
    is `query-C-synthesis` — visible immediately from this grouping.
    """
    buckets: dict[tuple[str, str, str], list[RunResult]] = {}
    for r in results:
        buckets.setdefault((r.condition, r.provider, r.task_id), []).append(r)
    out: dict[tuple[str, str, str], dict[str, float]] = {}
    for key, rs in buckets.items():
        n = len(rs)
        succ = sum(1 for r in rs if r.success)
        toks = [r.tokens for r in rs]
        lats = [r.latency_s for r in rs]
        out[key] = {
            "n": float(n),
            "success_rate": succ / n if n else 0.0,
            "mean_tokens": statistics.fmean(toks) if toks else 0.0,
            "mean_latency_s": statistics.fmean(lats) if lats else 0.0,
        }
    return out


def aggregate_by_iter(results: list[RunResult]
                       ) -> dict[tuple[str, str, int], dict[str, float]]:
    """FORGIA pezzo #43: group by (condition, provider, iter).

    Iter is read from `RunResult.extra["iter"]` (default 0). Lets you
    plot success-rate / latency curves across replicates of the same
    suite and see the compounding effect — `hippo_warm` should
    typically improve on later iters as memory accumulates, while
    `raw` stays flat.
    """
    buckets: dict[tuple[str, str, int], list[RunResult]] = {}
    for r in results:
        it = int(r.extra.get("iter", 0))
        buckets.setdefault((r.condition, r.provider, it), []).append(r)
    out: dict[tuple[str, str, int], dict[str, float]] = {}
    for key, rs in buckets.items():
        n = len(rs)
        succ = sum(1 for r in rs if r.success)
        toks = [r.tokens for r in rs]
        lats = [r.latency_s for r in rs]
        out[key] = {
            "n": float(n),
            "success_rate": succ / n if n else 0.0,
            "mean_tokens": statistics.fmean(toks) if toks else 0.0,
            "mean_latency_s": statistics.fmean(lats) if lats else 0.0,
        }
    return out


def to_jsonable(results: list[RunResult]) -> list[dict[str, Any]]:
    """Convert RunResult dataclasses to plain dicts (JSON-serializable)."""
    return [dataclasses.asdict(r) for r in results]


def from_jsonable(records: list[dict[str, Any]]) -> list[RunResult]:
    """FORGIA #74: inverse of `to_jsonable` — useful for merging
    bench JSONs across machines / time."""
    out: list[RunResult] = []
    for d in records:
        out.append(RunResult(
            condition=str(d.get("condition", "?")),
            provider=str(d.get("provider", "?")),
            task_id=str(d.get("task_id", "?")),
            success=bool(d.get("success", False)),
            tokens=int(d.get("tokens", 0)),
            latency_s=float(d.get("latency_s", 0.0)),
            attempts=int(d.get("attempts", 0)),
            error=str(d.get("error", "")),
            extra=dict(d.get("extra") or {}),
        ))
    return out


def merge_results(*lists: list[RunResult]) -> list[RunResult]:
    """FORGIA #74: concatenate multiple result lists.

    Trivial implementation today — the value is having a documented
    API so the calling convention is clear (and a single place to
    insert dedup / sort logic later if we ever need it).
    """
    out: list[RunResult] = []
    for ls in lists:
        out.extend(ls)
    return out
