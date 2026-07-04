"""Bench script: run the FORGIA pezzo #27 multi-model harness.

Usage:

    # Mock-only (always works, deterministic):
    python scripts/bench_with_without_hippo.py --providers mock

    # With real providers (whichever env keys are set):
    python scripts/bench_with_without_hippo.py --providers auto

    # Specific subset:
    python scripts/bench_with_without_hippo.py --providers mock,openai,ollama

The harness runs the same task suite under three conditions
(raw / hippo_cold / hippo_warm) and writes both raw records
(`bench_with_without_hippo.results.json`) and aggregated stats
(`bench_with_without_hippo.summary.json`) to the current `data/`
directory.

A failing provider doesn't abort the bench — its tasks become error
records and the loop continues. The summary table at the end shows the
headline metric (success_rate, mean_tokens, mean_latency_s) for every
(condition, provider) cell that produced at least one result.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Allow `python scripts/bench_with_without_hippo.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.bench_harness import (  # noqa: E402
    ProviderSpec,
    aggregate,
    aggregate_by_iter,
    compositional_suite,
    default_suite,
    hard_memory_recall_suite,
    memory_recall_suite,
    run_full_bench,
    skill_compounding_suite,
    to_jsonable,
)
from engram.config import CONFIG  # noqa: E402
from engram.llm import MockLLM  # noqa: E402

# Provider key → env var that must be present to enable it.
_PROVIDER_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "together": "TOGETHER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "yi": "YI_API_KEY",
    "baichuan": "BAICHUAN_API_KEY",
    "doubao": "DOUBAO_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
}


def _build_factory(name: str):
    """Return a () -> LLM factory for `name`. Mock and ollama need no env."""
    if name == "mock":
        return lambda: MockLLM(scripted=[
            "Paris", "4", "olleh", "hippoagent", "[1, 2, 3]",
        ] * 10)

    def _factory():
        # Force the provider via env so get_llm picks it up.
        os.environ["HIPPO_LLM_PROVIDER"] = name
        from engram.llm import get_llm
        return get_llm(use_mock=False)
    return _factory


def _resolve_providers(arg: str) -> list[ProviderSpec]:
    """Parse --providers (comma-list or 'auto') into ProviderSpec list."""
    if arg.strip().lower() == "auto":
        names: list[str] = ["mock"]
        for n, env in _PROVIDER_ENV.items():
            if os.environ.get(env, "").strip():
                names.append(n)
        # Ollama is local — include if reachable on default host.
        try:
            import httpx
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            if not host.startswith("http"):
                host = "http://" + host
            with httpx.Client(timeout=2.0) as c:
                if c.get(f"{host}/api/tags").status_code == 200:
                    names.append("ollama")
        except Exception:  # noqa: BLE001
            pass
    else:
        names = [n.strip() for n in arg.split(",") if n.strip()]

    return [ProviderSpec(name=n, factory=_build_factory(n)) for n in names]


def _print_summary(stats: dict[tuple[str, str], dict[str, float]]) -> None:
    """Pretty-print the (condition, provider) table to stdout."""
    if not stats:
        print("(no results)")
        return
    rows = [
        ("condition", "provider", "n", "succ", "tok", "lat_s",
         "att", "tok/su", "err"),
    ]
    for (cond, prov), s in sorted(stats.items()):
        # FORGIA pezzo #120: include tokens/success column.
        tps = s.get("tokens_per_success", float("inf"))
        tps_fmt = "inf" if tps == float("inf") else f"{int(tps)}"
        rows.append((
            cond, prov, f"{int(s['n'])}",
            f"{s['success_rate']:.2f}",
            f"{s['mean_tokens']:.0f}",
            f"{s['mean_latency_s']:.2f}",
            f"{s['mean_attempts']:.1f}",
            tps_fmt,
            f"{int(s['n_errors'])}",
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for i, row in enumerate(rows):
        line = "  ".join(c.ljust(widths[j]) for j, c in enumerate(row))
        print(line)
        if i == 0:
            print("  ".join("-" * w for w in widths))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", default="mock",
                        help="comma-list of provider names, or 'auto'.")
    parser.add_argument("--conditions", default="raw,hippo_cold,hippo_warm",
                        help="conditions to run (comma-list).")
    parser.add_argument("--consolidate-every", type=int, default=2,
                        help="run a sleep cycle every N tasks in hippo_warm.")
    parser.add_argument("--output-dir", default=str(CONFIG.data_dir),
                        help="directory for results/summary JSON.")
    parser.add_argument("--n-iter", type=int, default=1,
                        help="run the suite this many times (warm gets the "
                             "compounding effect of repeated exposure).")
    parser.add_argument("--suite", default="default",
                        choices=["default", "skill_compounding",
                                 "memory_recall", "hard_memory_recall",
                                 "compositional"],
                        help="which task suite to run.")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress structured INFO/WARNING logs from "
                             "the agent during the run (cleaner for CI).")
    parser.add_argument("--save-md", action="store_true",
                        help="also save the markdown summary table to "
                             "<output-dir>/bench_with_without_hippo.summary.md")
    parser.add_argument("--max-tasks", type=int, default=0,
                        help="limit the suite to the first N tasks "
                             "(useful for quick smoke; 0 = no limit).")
    parser.add_argument("--clean-data", action="store_true",
                        help="WIPE HIPPO_DATA_DIR contents before the run "
                             "(refuses if HIPPO_DATA_DIR is unset or "
                             "matches the production project/data path).")
    parser.add_argument("--task-id", default="",
                        help="run only the task whose id matches this string "
                             "(useful for reproducing a single-task failure).")
    parser.add_argument("--memory-stats", action="store_true",
                        help="at the end, also print episode + skill counts "
                             "in the data dir (post-bench corpus state).")
    parser.add_argument("--show-failures", action="store_true",
                        help="print task_id + answer preview for every "
                             "failed RunResult (debugging aid).")
    parser.add_argument("--print-config", action="store_true",
                        help="print resolved env vars + key CONFIG values "
                             "before the run starts.")
    parser.add_argument("--list-providers", action="store_true",
                        help="print the providers --providers auto would "
                             "select then exit (no bench).")
    args = parser.parse_args()

    if args.list_providers:
        # FORGIA #88: dry-run discovery — useful before kicking off
        # an expensive auto run.
        candidates: list[str] = ["mock"]
        for n, env in _PROVIDER_ENV.items():
            if os.environ.get(env, "").strip():
                candidates.append(n)
        print("Auto-detected providers:")
        for c in candidates:
            print(f"  - {c}")
        return 0

    if args.print_config:
        # FORGIA #87: surface what the run actually sees.
        from engram.config import CONFIG as _C
        print("[bench] resolved config:")
        for k in ("HIPPO_DATA_DIR", "HIPPO_LLM_PROVIDER", "HIPPO_OFFLINE",
                  "HIPPO_AUTO_FALLBACK", "HIPPO_MODEL"):
            v = os.environ.get(k, "(unset)")
            print(f"  env {k:24s} = {v}")
        for f in ("data_dir", "embedding_dim", "wake_max_steps",
                  "tcm_rho", "dg_d_expand", "dg_k_sparse"):
            print(f"  CONFIG.{f:19s} = {getattr(_C, f, '?')}")

    if args.clean_data:
        # FORGIA #64 — only clean isolated data dirs. Refuse the
        # production tree to avoid catastrophic "make bench wipes my
        # episodes" mistakes.
        import shutil

        from engram.config import _project_root
        env_dir = os.environ.get("HIPPO_DATA_DIR", "").strip()
        if not env_dir:
            print(
                "[bench] --clean-data refused: HIPPO_DATA_DIR is unset; "
                "the production data tree is too risky to wipe.",
                file=sys.stderr,
            )
            return 2
        target = Path(env_dir).expanduser().resolve()
        production = (_project_root() / "data").resolve()
        if target == production:
            print(
                f"[bench] --clean-data refused: HIPPO_DATA_DIR resolves to "
                f"the production tree {production}.",
                file=sys.stderr,
            )
            return 2
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        print(f"[bench] cleaned {target}")

    if args.quiet:
        # FORGIA #60 — silence agent logs for CI runs. Every emit() / log
        # warning lands at WARNING level by default; bumping the wrapper
        # to ERROR (40) drops everything below ERROR.
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(40),
        )

    providers = _resolve_providers(args.providers)
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if args.suite == "skill_compounding":
        suite = skill_compounding_suite()
    elif args.suite == "memory_recall":
        suite = memory_recall_suite()
    elif args.suite == "hard_memory_recall":
        suite = hard_memory_recall_suite()
    elif args.suite == "compositional":
        suite = compositional_suite()
    else:
        suite = default_suite()
    if args.max_tasks > 0:
        suite = suite[: args.max_tasks]
    if args.task_id:
        suite = [c for c in suite if c.id == args.task_id]
        if not suite:
            print(f"[bench] no task matched id={args.task_id!r}", file=sys.stderr)
            return 2

    print(f"[bench] providers: {[p.name for p in providers]}")
    print(f"[bench] conditions: {conditions}")
    print(f"[bench] cases: {len(suite)} × {args.n_iter} iters")

    t_start = time.perf_counter()
    all_results = []
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    incremental_path = out_dir / "bench_with_without_hippo.partial.json"

    def _persist_partial(snapshot):  # FORGIA #49: incremental save
        try:
            with open(incremental_path, "w", encoding="utf-8") as f:
                json.dump(to_jsonable(all_results + list(snapshot)),
                          f, indent=2, default=str)
        except Exception:  # noqa: BLE001
            pass

    for it in range(args.n_iter):
        results = run_full_bench(
            cases=suite, providers=providers,
            conditions=conditions,
            consolidate_every=args.consolidate_every,
            on_cell_done=_persist_partial,
        )
        for r in results:
            r.extra = {**r.extra, "iter": it}
        all_results.extend(results)

    elapsed = time.perf_counter() - t_start
    stats = aggregate(all_results)
    stats_by_iter = aggregate_by_iter(all_results) if args.n_iter > 1 else {}

    # Persist
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "bench_with_without_hippo.results.json"
    summary_path = out_dir / "bench_with_without_hippo.summary.json"
    iters_path = out_dir / "bench_with_without_hippo.by_iter.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(all_results), f, indent=2, default=str)
    if stats_by_iter:
        with open(iters_path, "w", encoding="utf-8") as f:
            json.dump(
                {f"{k[0]}|{k[1]}|iter{k[2]}": v
                 for k, v in stats_by_iter.items()},
                f, indent=2,
            )
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {f"{k[0]}|{k[1]}": v for k, v in stats.items()},
            f, indent=2,
        )

    if args.save_md:
        # FORGIA #61: render the summary as markdown and save next to the JSON.
        from scripts.bench_summary_md import render_table
        md_path = out_dir / "bench_with_without_hippo.summary.md"
        md_payload = {f"{k[0]}|{k[1]}": v for k, v in stats.items()}
        try:
            md_path.write_text(render_table(md_payload), encoding="utf-8")
        except Exception:  # noqa: BLE001
            md_path = None  # type: ignore[assignment]

    print()
    print(f"[bench] wall-clock: {elapsed:.1f}s "
          f"({len(all_results)} results)")
    print(f"[bench] wrote {results_path}")
    print(f"[bench] wrote {summary_path}")
    if stats_by_iter:
        print(f"[bench] wrote {iters_path}")
    if args.save_md and md_path is not None:
        print(f"[bench] wrote {md_path}")
    print()
    _print_summary(stats)
    if stats_by_iter:
        print()
        print("Per-iter (compounding effect):")
        rows = sorted(stats_by_iter.items())
        for (cond, prov, it), s in rows:
            print(
                f"  {cond:12s} {prov:12s} iter={it}  "
                f"succ={s['success_rate']:.2f}  "
                f"tok={int(s['mean_tokens']):5d}  "
                f"lat={s['mean_latency_s']:.2f}s"
            )

    # FORGIA #58: macro hit rate per (condition, provider). Lets you
    # see at a glance how often the procedural fast-path engaged.
    macro_buckets: dict[tuple[str, str], list[bool]] = {}
    for r in all_results:
        if r.condition.startswith("hippo"):
            macro_buckets.setdefault(
                (r.condition, r.provider), [],
            ).append(bool(r.extra.get("used_macro", False)))
    if any(macro_buckets.values()):
        print()
        print("Macro fast-path hit rate (hippo conditions only):")
        for key, hits in sorted(macro_buckets.items()):
            rate = sum(hits) / len(hits) if hits else 0.0
            print(f"  {key[0]:12s} {key[1]:12s}  {rate:.0%} "
                  f"({sum(hits)}/{len(hits)})")

    if args.show_failures:
        # FORGIA #85: dump task_id + answer preview for every failure.
        failed = [r for r in all_results if not r.success]
        if failed:
            print()
            print(f"Failures ({len(failed)} of {len(all_results)}):")
            for r in failed:
                ans = r.extra.get("answer", "")
                err = r.error or ""
                preview = (err or ans or "")[:120].replace("\n", " ")
                print(
                    f"  [{r.condition:11s} {r.provider:10s}] "
                    f"{r.task_id:24s}  → {preview}"
                )

    if args.memory_stats:
        # FORGIA #80 + #155: post-bench corpus state with FORGIA #143/#144
        # analytics surface (outcome breakdown + steps + token usage).
        try:
            from engram.memory import EpisodicMemory
            from engram.skill import SkillLibrary
            mem = EpisodicMemory()
            sk = SkillLibrary()
            print()
            print(f"Post-bench corpus ({CONFIG.data_dir}):")
            print(f"  episodes: {mem.count()}")
            print(f"  skills:   {sk.count()} "
                  f"(promoted={sk.count(status='promoted')}, "
                  f"candidate={sk.count(status='candidate')})")
            ob = mem.outcome_breakdown()
            if ob:
                print(f"  outcomes: {ob}")
            tu = mem.token_usage_summary()
            if tu["n_with_tokens"] > 0:
                print(f"  tokens:   total={int(tu['total'])} "
                      f"mean={int(tu['mean'])} max={int(tu['max'])}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [memory-stats failed: {exc}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
