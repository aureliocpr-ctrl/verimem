"""Independence + deconfound validation on the REAL gate path (Vivarium P88 reproduction).

Aurelio mandate 2026-07-11: "testa tutto sul corpus ... altrimenti e' tutto inutile".
The shipped independence write-gate and its P88 deconfound are unit-tested but ship
default OFF, pending reproduction on a real path. This is that reproduction: it drives
the REAL gate (Memory.add, real embedder, real recall, the real SourceTrustBook) — the
same infrastructure as source_trust_miniworld — and adds the attack the current gate
does NOT survive: a COLLUDER CARTEL.

Threat the current >=2-DISTINCT rule misses
------------------------------------------
The shipped source-trust confirms a value asserted by >=2 DISTINCT source-IDs. A cartel
of N colluders with distinct IDs all asserting the SAME false value therefore confirms
ITSELF — manufactured consensus. Independence collapses the cartel (identical report
vectors) to one witness; deconfound keeps HONEST sources (who agree because both track
the truth) from being collapsed too.

Four conditions, same stream, real gate:
  OFF             ENGRAM_SOURCE_TRUST unset
  ON              source-trust, >=2-distinct (FOOLED: the cartel self-confirms)
  ON+INDEP        + ENGRAM_SOURCE_INDEPENDENCE       (cartel -> one witness)
  ON+INDEP+DECONF + ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND (honest not false-merged)

PRE-REGISTERED CRITERIA (declared BEFORE the first run)
  C1  independence denies the cartel fabricated trust:
        cartel_consistency(ON) >= 0.75  AND  cartel_consistency(ON+INDEP) <= 0.60
  C2  the cartel does NOT out-rank the honest under the mature policy (no inversion):
        honest_consistency(ON+INDEP+DECONF) > cartel_consistency(ON+INDEP+DECONF)
  C3  deconfound rescues honest corroboration from the raw false-merge:
        honest_consistency(ON+INDEP+DECONF) >= 0.75
        (and >= honest_consistency(ON+INDEP) — deconfound never hurts the honest)
Honest INCONCLUSIVE mode: if honest never reach >=2 agreement (consistency stays at the
0.5 neutral prior everywhere), C2/C3 are reported INCONCLUSIVE, not passed.

    python -m benchmark.independence_validation --seed 11
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from benchmark.source_trust_miniworld import (
    _PROP_TMPL,
    WorldConfig,
    extract_value,
    generate_stream,
)

RESULTS_DIR = Path(__file__).parent / "results"
_NEUTRAL = 0.5


@dataclass(frozen=True)
class CartelConfig:
    n_colluders: int = 4        # distinct IDs -> defeat the >=2-DISTINCT rule
    n_cartel_keys: int = 8      # contested keys the cartel lies about every tick


def _cartel_value(key_idx: int) -> str:
    """A fixed 6-char alnum false value per cartel key (matches extract_value; a
    random truth colliding with it is ~0)."""
    return f"crt{key_idx:03d}"


def add_cartel(stream: list[dict[str, Any]], cfg: WorldConfig,
               cc: CartelConfig) -> list[dict[str, Any]]:
    """Append coordinated cartel events: every colluder asserts the SAME false value
    on each cartel key, every tick. Honest sources also write these keys (truth), so
    the cartel's falsehood is a CONTESTED claim, not an uncontested one."""
    cartel_keys = [f"project_{i}" for i in range(cc.n_cartel_keys)]
    colluders = [f"colluder_{i}" for i in range(cc.n_colluders)]
    cval = {k: _cartel_value(i) for i, k in enumerate(cartel_keys)}
    extra: list[dict[str, Any]] = []
    for t in range(cfg.ticks):
        for src in colluders:
            for k in cartel_keys:
                extra.append({"tick": t, "source": src, "kind": "colluder",
                              "key": k, "value": cval[k], "true_value": None,
                              "prev_value": None})
    return stream + extra, cartel_keys, colluders, cval


def _observe_tick(mem, tick_events, truth_now: dict[str, str], *,
                  independence: bool, deconfound: bool) -> None:
    """Independence-aware acceptance (the fix the first run demanded). The naive rule
    (accept the value with the most DISTINCT sources) hands the write-majority cartel
    the 'accepted' slot, so honest truth-tellers become the contradictors and their
    trust inverts. Here 'accepted' is the value with the most INDEPENDENT witnesses,
    and the audit anchor (a >=2-asserted value the WORLD knows is false = the outcome/
    do-operator, honest world-knows-truth note) is fed BEFORE clustering so the
    deconfound already bites at tick 0. A value with <2 independent witnesses accepts
    nobody — so an un-corroborated cartel key never contradicts the honest."""
    book = mem._source_trust_book()
    by_key: dict[str, list[dict[str, Any]]] = {}
    for ev in tick_events:
        by_key.setdefault(ev["key"], []).append(ev)
        book.record_report(ev["source"], ev["key"], ev["value"])   # feed vectors first
    for key, evs in by_key.items():
        by_value: dict[str, set[str]] = {}
        for ev in evs:
            by_value.setdefault(ev["value"], set()).add(ev["source"])
        tv = truth_now.get(key)
        for value, srcs in by_value.items():        # audit anchor from ground truth
            if len(srcs) >= 2 and tv is not None and value != tv:
                mem.source_trust_observe(audited_false=(key, value))

        def witnesses(srcs: set[str]) -> int:
            if not independence:
                return len(srcs)
            return book.independent_clusters(sorted(srcs), deconfounded=deconfound)

        accepted_val, accepted_srcs = max(by_value.items(),
                                          key=lambda kv: witnesses(kv[1]))
        if witnesses(accepted_srcs) < 2:
            continue        # no independently-corroborated value -> contradict nobody
        mem.source_trust_observe(
            confirmation=sorted(accepted_srcs),
            reports={s: {key: accepted_val} for s in accepted_srcs})
        for value, srcs in by_value.items():
            if value == accepted_val:
                continue
            for s in sorted(srcs):
                mem.source_trust_observe(contradiction=s)


def _truth_at_each_tick(stream: list[dict[str, Any]]) -> list[dict[str, str]]:
    """truth_now per tick, from the honest/liar events that carry true_value."""
    ticks = max((ev["tick"] for ev in stream), default=-1) + 1
    per = [{} for _ in range(ticks)]
    for ev in stream:
        if ev["true_value"] is not None:
            per[ev["tick"]][ev["key"]] = ev["true_value"]
    # forward-fill keys a tick didn't touch
    for t in range(1, ticks):
        for k, v in per[t - 1].items():
            per[t].setdefault(k, v)
    return per


def run_condition(cfg: WorldConfig, cc: CartelConfig, db_path: Path, *,
                  trust_on: bool, independence: bool, deconfound: bool) -> dict[str, Any]:
    os.environ["ENGRAM_SOURCE_TRUST"] = "1" if trust_on else "0"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE"] = "1" if independence else "0"
    os.environ["ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND"] = "1" if deconfound else "0"
    os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "0"
    from engram.client import Memory
    from engram.source_trust import reset_book_cache
    reset_book_cache()
    mem = Memory(db_path)
    base = generate_stream(cfg)
    stream, cartel_keys, colluders, cval = add_cartel(base, cfg, cc)
    truth_per_tick = _truth_at_each_tick(stream)
    now = time.time()
    tick_ts = {t: now - (cfg.ticks - 1 - t) * 2 * 86400.0 for t in range(cfg.ticks)}
    quarantined = 0
    for t in range(cfg.ticks):
        tick_events = [ev for ev in stream if ev["tick"] == t]
        for ev in tick_events:
            res = mem.add(_PROP_TMPL.format(key=ev["key"], value=ev["value"]),
                          topic=f"world/{ev['key']}",
                          verified_by=[f"source-doc:{ev['source']}:t{t}"],
                          asserted_at=tick_ts[t])
            quarantined += int(res.get("status") == "quarantined")
        if trust_on:
            _observe_tick(mem, tick_events, truth_per_tick[t],
                          independence=independence, deconfound=deconfound)

    # recall-level cartel success: for a contested cartel key, does recall return the
    # colluded false value as the top answer?
    final_truth = truth_per_tick[-1] if truth_per_tick else {}
    cartel_top = 0
    for k in cartel_keys:
        hits = mem.search(f"What is the access code of {k}?", k=3)
        vals = [extract_value(h.get("text", "")) for h in hits]
        vals = [v for v in vals if v]
        if vals and vals[0] == cval[k]:
            cartel_top += 1

    def cons(src: str) -> float:
        return mem.consistency_trust(src) if trust_on else _NEUTRAL
    honest = [f"honest_{i}" for i in range(cfg.n_honest)]
    hon = [cons(s) for s in honest]
    car = [cons(s) for s in colluders]
    return {
        "cartel_consistency": round(mean(car), 4) if car else _NEUTRAL,
        "honest_consistency": round(mean(hon), 4) if hon else _NEUTRAL,
        "cartel_consistency_all": {s: round(cons(s), 4) for s in colluders},
        "honest_neutral": all(abs(v - _NEUTRAL) < 1e-9 for v in hon),
        "cartel_top1_recall": f"{cartel_top}/{len(cartel_keys)}",
        "quarantined_writes": quarantined,
        "n_writes": len(stream),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--keys", type=int, default=20)
    ap.add_argument("--ticks", type=int, default=8)
    ap.add_argument("--colluders", type=int, default=4)
    ap.add_argument("--cartel-keys", type=int, default=8)
    args = ap.parse_args()

    cfg = WorldConfig(n_keys=args.keys, ticks=args.ticks, seed=args.seed)
    cc = CartelConfig(n_colluders=args.colluders, n_cartel_keys=args.cartel_keys)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        off = run_condition(cfg, cc, Path(td) / "off.db",
                            trust_on=False, independence=False, deconfound=False)
        on = run_condition(cfg, cc, Path(td) / "on.db",
                           trust_on=True, independence=False, deconfound=False)
        indep = run_condition(cfg, cc, Path(td) / "indep.db",
                              trust_on=True, independence=True, deconfound=False)
        deconf = run_condition(cfg, cc, Path(td) / "deconf.db",
                               trust_on=True, independence=True, deconfound=True)

    inconclusive = deconf["honest_neutral"] and indep["honest_neutral"]
    verdict = {
        "C1_independence_denies_cartel":
            on["cartel_consistency"] >= 0.75 and indep["cartel_consistency"] <= 0.60,
        "C2_no_inversion_mature":
            deconf["honest_consistency"] > deconf["cartel_consistency"],
        "C3_deconfound_rescues_honest":
            (deconf["honest_consistency"] >= 0.75
             and deconf["honest_consistency"] >= indep["honest_consistency"]),
        "honest_inconclusive": inconclusive,
    }
    verdict["reproduction_holds"] = (
        verdict["C1_independence_denies_cartel"]
        and verdict["C2_no_inversion_mature"]
        and verdict["C3_deconfound_rescues_honest"]
        and not inconclusive)
    report = {
        "config": asdict(cfg) | asdict(cc),
        "off": off, "on": on, "on_indep": indep, "on_indep_deconf": deconf,
        "verdict": verdict,
        "criterion": "PRE-REGISTERED: C1 cartel_cons ON>=0.75 & INDEP<=0.60; "
                     "C2 honest>cartel under deconf; C3 honest>=0.75 & deconf>=indep",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps(report, indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"independence_validation_seed{args.seed}_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
