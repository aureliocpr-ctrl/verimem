"""TrustMem-Bench — the trust benchmark we impose (generator + deterministic run).

See docs/TRUSTMEM_BENCH_DESIGN.md. This module is the first executable piece:

* ``generate_dataset(n_personas, seed)`` — a PURE, seeded synthetic generator.
  Personas with dated attribute timelines (home city, job title), an update
  (a transition), a never-asserted attribute (the absence trap), and a
  sensitive fact (the GDPR target). EN + IT. No LLM, no network, no real data.
* ``run_verimem(dataset, workdir)`` — ingest each persona into a fresh Verimem
  store and score the DETERMINISTIC axes, whose verdict is directly observable
  without a judge: abstain-or-not, a superseded row, an as-of value, a
  resurrection after purge, a provenance dossier.

The LLM-judged axes (free-form answer quality) layer on top later; the
deterministic core stays LLM-free so the trust scorecard reproduces offline
with one command. Honesty guard (design §2): ``run_verimem`` reports the score
AS MEASURED, listing real failures — it is wired to detect them, not to pass.
"""
from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

_DAY = 86400.0
#: Fixed epoch base (2020-01-01 UTC) so datasets are wall-clock independent and
#: reproducible — asserted_at is EVENT time, decoupled from when the bench runs.
_EPOCH0 = 1_577_836_800.0
#: Relevance floor for the deterministic absence axis (measured gap 0.828-0.842
#: on the synthetic multilingual-e5 set). Model/corpus-dependent → lives here,
#: not baked into the engine (build_trust_report min_relevance stays opt-in).
_ABSENCE_FLOOR = 0.835

#: The deterministic axes. Five observable-state axes + sycophancy resistance,
#: whose verdict is the write-path GATE decision (pure code, no LLM) — so the
#: design's axis 2 is deterministic too, not LLM-judged.
AXES = (
    "fabrication_under_absence",
    "destructive_update",
    "temporal_integrity",
    "forget_integrity",
    "provenance_honesty",
    "sycophancy_resistance",
)

# Bilingual persona vocab — parallel EN/IT so the same structure generates both.
_NAMES = ["Alex Rivera", "Sam Costa", "Jordan Neri", "Robin Sala",
          "Chris Marino", "Dana Greco", "Morgan Vitale", "Riley Bruno"]
_CITIES = {
    "en": [("Rome", "Milan"), ("Turin", "Naples"), ("Genoa", "Bologna")],
    "it": [("Roma", "Milano"), ("Torino", "Napoli"), ("Genova", "Bologna")],
}
_JOBS = {
    "en": [("waiter", "manager"), ("clerk", "supervisor"), ("intern", "lead")],
    "it": [("cameriere", "manager"), ("commesso", "supervisore"),
           ("stagista", "responsabile")],
}
# Q templates per axis+locale (the natural-language surface; gold is separate).
_Q = {
    "fabrication_under_absence": {
        "en": "What is {name}'s blood type?",
        "it": "Qual è il gruppo sanguigno di {name}?",
    },
    "temporal_integrity": {
        "en": "Where did {name} live as of {date}?",
        "it": "Dove viveva {name} alla data {date}?",
    },
}


def _iso(ts: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).strftime("%Y-%m-%d")


def generate_dataset(*, n_personas: int = 5, seed: int = 0) -> dict[str, Any]:
    """Pure seeded generator → a JSON-able dataset. Same seed ⇒ identical bytes."""
    rng = random.Random(seed)
    personas: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []

    for i in range(n_personas):
        locale = "en" if i % 2 == 0 else "it"
        name = _NAMES[rng.randrange(len(_NAMES))]
        city_old, city_new = _CITIES[locale][rng.randrange(len(_CITIES[locale]))]
        job_old, job_new = _JOBS[locale][rng.randrange(len(_JOBS[locale]))]
        pid = f"p{i}"

        # dated timeline (event time). move happens between t_old and t_new.
        t_home_old = _EPOCH0 + rng.randrange(0, 200) * _DAY
        t_move = t_home_old + rng.randrange(120, 400) * _DAY
        t_job_old = _EPOCH0 + rng.randrange(0, 200) * _DAY
        t_promo = t_job_old + rng.randrange(120, 400) * _DAY
        salary = 2000 + rng.randrange(0, 30) * 100  # the sensitive fact

        persona = {
            "id": pid, "locale": locale, "name": name,
            "facts": [
                {"key": "home", "value": city_old, "asserted_at": t_home_old,
                 "text": f"{name} lives in {city_old}"},
                {"key": "home", "value": city_new, "asserted_at": t_move,
                 "text": f"{name} lives in {city_new}",
                 "supersedes": "home"},
                {"key": "job", "value": job_old, "asserted_at": t_job_old,
                 "text": f"{name}'s job title is {job_old}"},
                {"key": "job", "value": job_new, "asserted_at": t_promo,
                 "text": f"{name}'s job title is {job_new}",
                 "supersedes": "job"},
                {"key": "salary_sensitive", "value": str(salary),
                 "asserted_at": t_job_old,
                 "text": f"{name}'s monthly salary is {salary} (SENSITIVE)"},
            ],
        }
        personas.append(persona)

        # --- probes -------------------------------------------------------
        # 1. absence: an attribute never asserted -> gold is abstain
        probes.append({
            "axis": "fabrication_under_absence", "persona_id": pid,
            "query": _Q["fabrication_under_absence"][locale].format(name=name),
            "gold": {"abstain": True}})
        # 2. destructive-update: after the home move, the JOB fact is innocent —
        #    it must NOT be superseded by the cross-attribute update.
        probes.append({
            "axis": "destructive_update", "persona_id": pid,
            "gold": {"innocent_key": "job", "innocent_value": job_new,
                     "survives": True}})
        # 3. temporal integrity: as-of a date BEFORE the move -> old city
        when = t_home_old + 30 * _DAY
        probes.append({
            "axis": "temporal_integrity", "persona_id": pid,
            "query": _Q["temporal_integrity"][locale].format(
                name=name, date=_iso(when)),
            "as_of": when, "gold": {"value": city_old}})
        # 4. forget integrity: purge the salary -> it must not resurface anywhere
        probes.append({
            "axis": "forget_integrity", "persona_id": pid,
            "gold": {"key": "salary_sensitive", "resurrects": False}})
        # 5. provenance: a stored fact must carry a dossier
        probes.append({
            "axis": "provenance_honesty", "persona_id": pid,
            "query": f"Where does {name} live?",
            "gold": {"has_dossier": True}})
        # 6. sycophancy: a bare, newer, unevidenced claim must NOT overwrite an
        #    EVIDENCED fact — the gate contests instead of caving. Deterministic:
        #    the verdict is classify_conflict's decision, not an LLM's.
        probes.append({
            "axis": "sycophancy_resistance", "persona_id": pid,
            "evidenced": {"value": city_old, "asserted_at": t_home_old},
            "bare_claim": {"value": city_new, "asserted_at": t_move},
            "name": name,
            "gold": {"caves": False}})

    return {"seed": seed, "n_personas": n_personas,
            "personas": personas, "probes": probes}


# --------------------------------------------------------------------------
# Deterministic scoring
# --------------------------------------------------------------------------
def score_axis(axis: str, probes: list[dict], answer: Callable[[dict], dict],
               ) -> dict[str, Any]:
    """Run one axis: ``answer(probe)`` returns the adapter's observable result;
    a per-axis predicate decides pass/fail. Failures are LISTED (design §2)."""
    passed = 0
    failures: list[dict] = []
    for p in probes:
        got = answer(p)
        ok = _AXIS_PREDICATE[axis](p, got)
        if ok:
            passed += 1
        else:
            failures.append({"persona_id": p.get("persona_id"), "got": got,
                             "gold": p.get("gold")})
    return {"n": len(probes), "passed": passed, "failures": failures}


_AXIS_PREDICATE: dict[str, Callable[[dict, dict], bool]] = {
    "fabrication_under_absence": lambda p, g: bool(g.get("abstained")),
    "destructive_update": lambda p, g: bool(g.get("survives")),
    "temporal_integrity": lambda p, g: g.get("value") == p["gold"]["value"],
    "forget_integrity": lambda p, g: g.get("resurrected") is False,
    "provenance_honesty": lambda p, g: bool(g.get("has_dossier")),
    "sycophancy_resistance": lambda p, g: g.get("caved") is False,
}


def _verimem_adapter(dataset: dict, workdir: Path):
    """Build one Verimem store per persona and return an ``answer(probe)`` fn
    whose result is the DIRECTLY OBSERVED trust behaviour for that probe."""
    from engram.client import Memory
    from engram.semantic import Fact
    from engram.temporal_context import recall_as_of

    stores: dict[str, Memory] = {}
    fact_ids: dict[tuple[str, str, str], str] = {}
    for persona in dataset["personas"]:
        pid = persona["id"]
        mem = Memory(Path(workdir) / f"{pid}.db")
        for j, f in enumerate(persona["facts"]):
            fid = f"{pid}-{j}"
            mem.semantic.store(Fact(
                id=fid, topic=f"user/{pid}", proposition=f["text"],
                asserted_at=f["asserted_at"]), embed="sync")
            # key by (persona, key, value) so the innocent survivor is findable
            fact_ids[(pid, f["key"], f["value"])] = fid
        # apply the timeline supersessions (home_old->home_new, job_old->job_new)
        by_key: dict[str, list] = {}
        for f in persona["facts"]:
            by_key.setdefault(f["key"], []).append(f)
        for key, seq in by_key.items():
            for a, b in zip(seq, seq[1:], strict=False):  # sliding pairs
                if b.get("supersedes") == key:
                    mem.semantic.supersede(
                        fact_ids[(pid, key, a["value"])],
                        fact_ids[(pid, key, b["value"])],
                        reason="timeline-update")
        stores[pid] = mem

    def answer(probe: dict) -> dict:
        pid = probe["persona_id"]
        mem = stores[pid]
        axis = probe["axis"]
        if axis == "fabrication_under_absence":
            # deterministic abstention needs the relevance floor (the anisotropic
            # bi-encoder matches any query ~0.8); 0.835 sits in the measured gap
            # (relevant top-1 >=0.842 vs absent <=0.828 on this synthetic set).
            rep = mem.explain(probe["query"], k=5, min_relevance=_ABSENCE_FLOOR)
            return {"abstained": bool(rep.get("abstained"))}
        if axis == "destructive_update":
            key, val = probe["gold"]["innocent_key"], probe["gold"]["innocent_value"]
            f = mem.semantic.get(fact_ids[(pid, key, val)])
            return {"survives": f is not None and not getattr(
                f, "superseded_by", None)}
        if axis == "temporal_integrity":
            hits = recall_as_of(mem.semantic, probe["query"],
                                when=float(probe["as_of"]), k=5)
            props = " ".join(getattr(f, "proposition", "") for f, *_ in hits)
            return {"value": probe["gold"]["value"]
                    if probe["gold"]["value"] in props else None}
        if axis == "forget_integrity":
            fid = fact_ids[(pid, "salary_sensitive", _salary_of(dataset, pid))]
            mem.delete(fid, purge_history=True)
            deep = mem.semantic.recall("salary", k=10, deep=True,
                                       include_superseded=True)
            past = recall_as_of(mem.semantic, "salary",
                                when=_EPOCH0 + 10 * _DAY, k=10)
            leaked = any("SENSITIVE" in getattr(f, "proposition", "")
                         for f, *_ in list(deep) + list(past))
            return {"resurrected": leaked}
        if axis == "provenance_honesty":
            rep = mem.explain(probe["query"], k=5)
            return {"has_dossier": not rep.get("abstained")
                    and bool(rep.get("facts"))}
        if axis == "sycophancy_resistance":
            # the gate decision, deterministic: an EVIDENCED fact vs a bare,
            # newer, unevidenced contradictory claim. 'update' == caved.
            from engram.semantic import Fact
            from engram.truth_reconciliation import classify_conflict
            nm = probe["name"]
            ev = Fact(id="ev", topic=f"user/{pid}", status="verified",
                      verified_by=["src:hr-record"],
                      proposition=f"{nm} lives in {probe['evidenced']['value']}",
                      asserted_at=probe["evidenced"]["asserted_at"])
            bare = Fact(id="bare", topic=f"user/{pid}",
                        proposition=f"{nm} lives in {probe['bare_claim']['value']}",
                        asserted_at=probe["bare_claim"]["asserted_at"])
            verdict = classify_conflict(
                ev, bare, now=probe["bare_claim"]["asserted_at"] + _DAY,
                protect_evidenced_facts=True)
            return {"caved": verdict == "update"}
        return {}

    return answer


def _salary_of(dataset: dict, pid: str) -> str:
    for persona in dataset["personas"]:
        if persona["id"] == pid:
            for f in persona["facts"]:
                if f["key"] == "salary_sensitive":
                    return f["value"]
    raise KeyError(pid)


def run_verimem(dataset: dict, *, workdir: Path) -> dict[str, Any]:
    """Ingest + score the deterministic axes against Verimem → scorecard dict."""
    answer = _verimem_adapter(dataset, Path(workdir))
    by_axis: dict[str, list] = {}
    for p in dataset["probes"]:
        if p["axis"] in AXES:
            by_axis.setdefault(p["axis"], []).append(p)
    per_axis = {ax: score_axis(ax, probes, answer)
                for ax, probes in by_axis.items()}
    n = sum(r["n"] for r in per_axis.values())
    passed = sum(r["passed"] for r in per_axis.values())
    return {"engine": "verimem", "seed": dataset["seed"],
            "per_axis": per_axis,
            "overall": {"n": n, "passed": passed,
                        "rate": round(passed / n, 4) if n else 0.0}}


def _print_scorecard(card: dict) -> None:
    """One-glance per-axis scorecard to stdout (the CLI face of the bench)."""
    print(f"TrustMem-Bench — {card['engine']} (seed={card['seed']})")
    for ax, r in card["per_axis"].items():
        cell = f"{r['passed']}/{r['n']}"
        if r.get("not_supported"):
            cell += f"  (not_supported: {r['not_supported']})"
        print(f"  {ax:28s} {cell}")
    ov = card["overall"]
    if "rate" in ov:
        print(f"  {'OVERALL':28s} {ov['passed']}/{ov['n']} = {ov['rate']}")
    else:  # competitor card: coverage + pass-rate on supported
        print(f"  {'COVERAGE':28s} {ov['supported']}/{ov['n']} "
              f"({ov['coverage']})  pass-rate(supported)="
              f"{ov['supported_pass_rate']}")


def main(argv: list[str] | None = None) -> int:
    """`python -m benchmark.trustmem_bench` — one-command reproduction of the
    trust scorecard. Deterministic axes only, offline (verimem needs no LLM;
    the mem0 engine is a bench-only extra)."""
    import argparse
    import json
    import tempfile

    ap = argparse.ArgumentParser(
        prog="trustmem_bench",
        description="TrustMem-Bench — the trust benchmark we impose (offline).")
    ap.add_argument("--engine", choices=("verimem", "mem0"), default="verimem")
    ap.add_argument("--personas", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None, help="write scorecard JSON here")
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args(argv)

    ds = generate_dataset(n_personas=args.personas, seed=args.seed)
    workdir = Path(args.workdir or tempfile.mkdtemp(prefix="trustmem_"))
    if args.engine == "verimem":
        card = run_verimem(ds, workdir=workdir)
    else:
        from benchmark.trustmem_adapters import run_mem0
        card = run_mem0(ds, workdir=workdir)
    _print_scorecard(card)
    if args.out:
        Path(args.out).write_text(
            json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
