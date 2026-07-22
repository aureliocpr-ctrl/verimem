"""P4 — anti-circularity eval for the L3 subject pre-filter on EXTERNAL data.

The method constraint (case-F lesson, 2026-07-21): every FP/FN number must come
from an external dataset or third-party gold, never from pairs we authored and
labeled ourselves. This harness builds conflict pairs MECHANICALLY from real
Wikidata triples, so the labels are structural, not our judgment:

  TRUE-CONFLICT pair (same subject, must COMPARE): the sentence of a triple
      (S, P, O1) vs the SAME (S, P) with O2 swapped in from another triple of
      the same predicate — a value mutation, the canonical stored-fact clash.
  CROSS pair (different subjects, must SKIP or at worst compare — skipping is
      the precision win): sentences of two triples with DIFFERENT subjects S1,
      S2 (and different predicates, so no accidental same-fact overlap).

Measures verimem.subject_extract.same_subject:
  * conflict_compare_rate — fraction of TRUE-CONFLICT pairs that reach the
    judge (recall of the filter; a skip here = the critic's FN class, e.g.
    aliased/renamed subjects — the number the promotion gate needs);
  * cross_skip_rate — fraction of CROSS pairs skipped (the precision win; a
    compare here is not WRONG — fail-open — just judge budget spent).

Data: live SPARQL against query.wikidata.org (~N triples, 3 predicates with
human-readable labels). Offline fallback: --jsonl to reuse a cached pull.

    python -m benchmark.wikidata_subject_eval --n 60 \
        --out benchmark/results/wikidata_subject_eval.json
"""
from __future__ import annotations

import argparse
import json
import random
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: (predicate id, natural-language template) — templates render a triple as the
#: stored-fact sentence a memory would hold. Chosen for unambiguous rendering.
PREDICATES = [
    ("P36", "The capital of {s} is {o}."),
    ("P169", "The chief executive officer of {s} is {o}."),
    ("P159", "The headquarters of {s} is located in {o}."),
]

_SPARQL = """
SELECT ?sLabel ?oLabel WHERE {{
  ?s wdt:{pid} ?o .
  ?s rdfs:label ?sLabel . FILTER(LANG(?sLabel) = "en")
  ?o rdfs:label ?oLabel . FILTER(LANG(?oLabel) = "en")
}} LIMIT {limit}
"""

#: v2 (the critic's FN class, measured on EXTERNAL aliases): same query but
#: also pulling the subject's skos:altLabel — the entity's OFFICIAL alternate
#: name. Rendering one side of a TRUE conflict with the alias measures how
#: often the filter loses a real conflict when the same entity is named two
#: ways ("production database" vs "primary database" class). Labels stay
#: mechanical: Wikidata asserts the alias identity, not us.
_SPARQL_ALIAS = """
SELECT ?sLabel ?alt ?oLabel WHERE {{
  ?s wdt:{pid} ?o .
  ?s rdfs:label ?sLabel . FILTER(LANG(?sLabel) = "en")
  ?s skos:altLabel ?alt . FILTER(LANG(?alt) = "en")
  ?o rdfs:label ?oLabel . FILTER(LANG(?oLabel) = "en")
}} LIMIT {limit}
"""


def fetch_alias(pid: str, limit: int) -> list[tuple[str, str, str]]:
    q = _SPARQL_ALIAS.format(pid=pid, limit=limit)
    url = ("https://query.wikidata.org/sparql?format=json&query="
           + urllib.parse.quote(q))
    req = urllib.request.Request(url, headers={
        "User-Agent": "verimem-subject-eval/0.1 (research; single small query)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    out = []
    for b in data["results"]["bindings"]:
        s, alt, o = (b["sLabel"]["value"], b["alt"]["value"],
                     b["oLabel"]["value"])
        if any(x.startswith("Q") and x[1:].isdigit() for x in (s, alt, o)):
            continue
        if alt.strip().lower() == s.strip().lower():
            continue
        out.append((s, alt, o))
    return out


def fetch(pid: str, limit: int) -> list[tuple[str, str]]:
    q = _SPARQL.format(pid=pid, limit=limit)
    url = ("https://query.wikidata.org/sparql?format=json&query="
           + urllib.parse.quote(q))
    req = urllib.request.Request(url, headers={
        "User-Agent": "verimem-subject-eval/0.1 (research; single small query)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    out = []
    for b in data["results"]["bindings"]:
        s, o = b["sLabel"]["value"], b["oLabel"]["value"]
        # skip bare-Q labels (no english label resolved) — unusable as text
        if s.startswith("Q") and s[1:].isdigit():
            continue
        if o.startswith("Q") and o[1:].isdigit():
            continue
        out.append((s, o))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="triples per predicate")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--jsonl", default=None,
                    help="cached triples jsonl {pid,s,o} (skip the live pull)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    from verimem.subject_extract import same_subject

    triples: dict[str, list[tuple[str, str]]] = {}
    if a.jsonl:
        for line in open(a.jsonl, encoding="utf-8"):
            d = json.loads(line)
            triples.setdefault(d["pid"], []).append((d["s"], d["o"]))
    else:
        for pid, _ in PREDICATES:
            triples[pid] = fetch(pid, a.n)
        cache = REPO / "benchmark" / "results" / "wikidata_triples_cache.jsonl"
        with open(cache, "w", encoding="utf-8") as f:
            for pid, rows in triples.items():
                for s, o in rows:
                    f.write(json.dumps({"pid": pid, "s": s, "o": o},
                                       ensure_ascii=False) + "\n")

    tmpl = dict(PREDICATES)
    conflict_pairs, cross_pairs = [], []
    for pid, rows in triples.items():
        t = tmpl[pid]
        rows = [r for r in rows if r[0] and r[1]]
        rng.shuffle(rows)
        # TRUE-CONFLICT: same (S,P), object swapped from ANOTHER row (O2 != O1)
        for i, (s, o1) in enumerate(rows):
            o2 = rows[(i + 1) % len(rows)][1]
            if o2 == o1:
                continue
            conflict_pairs.append((t.format(s=s, o=o1), t.format(s=s, o=o2)))
    # CROSS: different subjects, different predicates
    pids = [p for p, _ in PREDICATES]
    for i in range(min(len(triples[p]) for p in pids)):
        (s1, o1) = triples[pids[0]][i]
        (s2, o2) = triples[pids[1]][i]
        if s1 != s2:
            cross_pairs.append((tmpl[pids[0]].format(s=s1, o=o1),
                                tmpl[pids[1]].format(s=s2, o=o2)))

    # v2 — ALIAS axis (critic cb26737b FN class, external labels): a TRUE
    # conflict where one side names the subject by its OFFICIAL skos:altLabel.
    # compare-rate here = the filter's recall under renaming; 1-rate = the FN
    # rate the promotion gate needs.
    alias_pairs: list[tuple[str, str]] = []
    if not a.jsonl:
        for pid, t in tmpl.items():
            rows = triples.get(pid) or []
            for s, alt, o in fetch_alias(pid, a.n):
                o2 = next((oo for _, oo in rows if oo != o), None)
                if o2 is not None:
                    alias_pairs.append((t.format(s=s, o=o),
                                        t.format(s=alt, o=o2)))

    cc = sum(same_subject(x, y) for x, y in conflict_pairs)
    cs = sum(not same_subject(x, y) for x, y in cross_pairs)
    ac = sum(same_subject(x, y) for x, y in alias_pairs)
    missed = [(x, y) for x, y in conflict_pairs if not same_subject(x, y)]
    missed_alias = [(x, y) for x, y in alias_pairs if not same_subject(x, y)]

    res = {
        "n_conflict_pairs": len(conflict_pairs),
        "conflict_compared": cc,
        "conflict_compare_rate": round(cc / len(conflict_pairs), 4) if conflict_pairs else None,
        "n_cross_pairs": len(cross_pairs),
        "cross_skipped": cs,
        "cross_skip_rate": round(cs / len(cross_pairs), 4) if cross_pairs else None,
        "n_alias_pairs": len(alias_pairs),
        "alias_compared": ac,
        "alias_compare_rate": round(ac / len(alias_pairs), 4) if alias_pairs else None,
        "alias_fn_rate": round(1 - ac / len(alias_pairs), 4) if alias_pairs else None,
        "missed_conflicts_sample": [f"{x} || {y}" for x, y in missed[:10]],
        "missed_alias_sample": [f"{x} || {y}" for x, y in missed_alias[:10]],
        "labels": "mechanical (Wikidata slot mutation + skos:altLabel) — not self-authored",
    }
    out = a.out or str(REPO / "benchmark" / "results" / "wikidata_subject_eval.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items()
                      if not k.startswith("missed_")}, indent=1))
    for m in res["missed_conflicts_sample"]:
        print("  MISS:", m[:120])
    for m in res["missed_alias_sample"]:
        print("  MISS-ALIAS:", m[:120])
    print(f"-> {out}")


if __name__ == "__main__":
    main()
