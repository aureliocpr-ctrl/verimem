"""Esegue la suite in FETTE parallele, senza un master che possa appendersi.

Perche' non xdist. Provato due volte il 2026-07-31 su questa macchina (20 core,
31 GB): con `-n 8 --dist loadfile` e poi con `-n 4 --dist loadgroup
--timeout=600`, in entrambi i casi i worker sono crashati
(`replacing crashed worker` x3) e il master e' rimasto appeso al 99% per 90
minuti SENZA DARE NESSUN VERDETTO. Un gate che non termina e' peggio di un gate
lento: non si sa nemmeno cosa e' fallito.

Il dump dei crash indica il punto::

    verimem/local_grounding.py:59   make_finetuned_scorer
    verimem/local_grounding.py:125  _ensure_scorer

cioe' piu' worker che caricano lo STESSO cross-encoder nello stesso istante.

Qui non c'e' nessun master: N processi `pytest` indipendenti, ognuno su una
fetta di file, ognuno col suo log e il suo EXIT. Se una fetta si appende o
crasha, le altre finiscono comunque e il suo log dice quale file stava
girando — informazione che con xdist andava persa.

Le fette si fanno per FILE (mai spezzando un file su due processi): i test di
uno stesso file condividono fixture e stato di modulo, e separarli
cambierebbe cio' che misurano.

Uso::

    python scripts/suite_a_fette.py            # 4 fette, default
    python scripts/suite_a_fette.py --fette 6 --seed 2069628213
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _file_di_test() -> list[Path]:
    return sorted((REPO / "tests").rglob("test_*.py"))


def _fette(file: list[Path], n: int) -> list[list[Path]]:
    """Round-robin sulla DIMENSIONE decrescente: le fette finiscono insieme.

    Dividere in blocchi contigui metterebbe i file grandi tutti nella stessa
    fetta, e il tempo totale sarebbe quello della fetta sfortunata.
    """
    ordinati = sorted(file, key=lambda p: p.stat().st_size, reverse=True)
    gruppi: list[list[Path]] = [[] for _ in range(n)]
    peso = [0] * n
    for f in ordinati:
        i = peso.index(min(peso))
        gruppi[i].append(f)
        peso[i] += f.stat().st_size
    return gruppi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fette", type=int, default=4)
    ap.add_argument("--seed", default="")
    ap.add_argument("--out", default=str(REPO / ".suite_fette"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gruppi = _fette(_file_di_test(), args.fette)

    procs = []
    t0 = time.time()
    for i, g in enumerate(gruppi):
        log = out / f"fetta{i}.log"
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
               *[str(p.relative_to(REPO)) for p in g]]
        if args.seed:
            cmd = [c for c in cmd if c not in ("-p", "no:randomly")]
            cmd += ["-p", "randomly", f"--randomly-seed={args.seed}"]
        f = log.open("w", encoding="utf-8")
        procs.append((i, subprocess.Popen(cmd, cwd=str(REPO), stdout=f,
                                          stderr=subprocess.STDOUT), f, log,
                      len(g)))
        print(f"fetta {i}: {len(g)} file -> {log.name}")

    esiti = []
    for i, p, f, log, n_file in procs:
        rc = p.wait()
        f.close()
        coda = [r for r in log.read_text(encoding="utf-8",
                                         errors="replace").splitlines()
                if "passed" in r or "failed" in r or "error" in r]
        esiti.append((i, rc, coda[-1] if coda else "(nessun riepilogo)"))

    durata = (time.time() - t0) / 60
    #: ⚠️ `args.fette` e' il numero RICHIESTO, non quello concluso:
    #: stamparlo qui faceva leggere «3 fette in 11.9 min» come un
    #: completamento anche quando la suite era stata uccisa a meta'
    #: (reperto @ws3, verificato in `LANT-63`, curato il 02/09 mentre la
    #: controfirmavo). Lo script SA gia' quali fette non hanno un
    #: riepilogo — lo stampa riga per riga poco sotto — e qui non lo
    #: usava. Quando i due numeri coincidono la riga dice quanto prima.
    concluse = sum(1 for _i, _rc, _riga in esiti
                   if _riga != "(nessun riepilogo)")
    print(f"\n=== {concluse} fette CONCLUSE su {args.fette} richieste, "
          f"in {durata:.1f} min ===")
    peggio = 0
    for i, rc, riga in esiti:
        print(f"  fetta {i}  EXIT={rc}  {riga}")
        peggio = max(peggio, rc)
    print(f"\nEXIT={peggio}")
    return peggio


if __name__ == "__main__":
    raise SystemExit(main())
