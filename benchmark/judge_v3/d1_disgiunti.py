"""Are the D1 pairs disjoint from the benches that judge the v3 judge?

The plan wants the D1 templates DISJOINT from the 112 matrix and from the G0 probes: a judge trained on
the gate's own sentences would pass the gate from memory. This counts the word n-grams (default 4) that
D1 rows share with every string literal in `benchmark/moat_multilingual_matrix.py` and in the benches
under `docs/stato-reale/banchi/` (a superset of the G0 probes), and names the files they come from.
Digits and template slots are not words. It reads the `fonte`, `memoria` and `claim` of each row, the
fields every D1 builder writes. Exit 1 if any n-gram is shared.

The instrument is not blind. Measured 2026-09-29 on the dialogue pairs (`d1_dialoghi@3`, 2160 rows)
against 580 bench files: n=3 finds 5 shared trigrams, all of them function phrases («due giorni fa»,
«il corso di»), n=2 finds 58, n=4 finds none.

Run from the root of the checkout:
    python benchmark/judge_v3/d1_disgiunti.py benchmark/judge_v3/d1-dialoghi.jsonl [--n 4]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
BANCHI = [RADICE / "benchmark" / "moat_multilingual_matrix.py",
          *sorted((RADICE / "docs" / "stato-reale" / "banchi").glob("*.py"))]
PAROLA = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")
SEGNAPOSTO = re.compile(r"\{[^}]*\}")


def ngrammi(testo: str, n: int) -> set[tuple[str, ...]]:
    parole = [p.lower() for p in PAROLA.findall(SEGNAPOSTO.sub(" ", testo))]
    return {tuple(parole[i:i + n]) for i in range(len(parole) - n + 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("righe", nargs="+", type=Path, help="D1 jsonl files")
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()

    dove: dict[tuple[str, ...], set[str]] = defaultdict(set)
    stringhe = 0
    for f in BANCHI:
        # a bench that does not parse would silently shrink the reference: it stops the check instead
        albero = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                stringhe += 1
                for g in ngrammi(nodo.value, a.n):
                    dove[g].add(f.name)

    d1: dict[tuple[str, ...], int] = defaultdict(int)
    righe = 0
    for f in a.righe:
        with open(f, encoding="utf-8") as fh:
            for riga in fh:
                r = json.loads(riga)
                righe += 1
                for campo in ("fonte", "memoria", "claim"):
                    for g in ngrammi(r[campo], a.n):
                        d1[g] += 1

    comuni = sorted(set(d1) & set(dove), key=lambda g: (-d1[g], g))
    print(f"benches: {len(BANCHI)} files, {stringhe} strings · D1: {righe} rows · "
          f"{a.n}-grams shared: {len(comuni)}")
    for g in comuni[:25]:
        print(f"  {' '.join(g)!r:45} D1 x{d1[g]:<5} {sorted(dove[g])[:3]}")
    return 1 if comuni else 0


if __name__ == "__main__":
    sys.exit(main())
