"""La curva di ammissione del giudice che gira DAVVERO in produzione.

`halumem_admission_sweep.py` traccia la curva con un giudice LLM
(`--model claude-sonnet-4-6`). Da 2026-07-18 il moat gira sul CE locale quando
non c'e' un llm iniettato — cioe' per l'utente appena installato, e per questa
macchina. La curva del CE non e' mai stata tracciata, quindi la soglia di
ammissione spedita (40) e' calibrata su un giudice diverso da quello che
giudica.

Perche' conta: la decisione del 2026-07-21 fissa il cancello del flip di
`ENGRAM_GRADED_ADMISSION` a `clean-adm >= 90%` con `noise-rej >= 95%`, e le due
misure esistenti danno numeri diversi fra loro (t40: 80% nello sweep di giugno,
66.7% nella misura di luglio). Nessuna delle due dice cosa fa il CE.

Stessa definizione di clean/noise dei bench esistenti — importata, non
riscritta, cosi' i numeri sono confrontabili:

  * clean = memory point dell'utente con la SUA sessione come source
  * noise = memory point di un ALTRO utente contro quella stessa sessione

Gratis (nessuna chiamata a modelli esterni) e ripetibile: seed fisso.

    python -m benchmark.halumem_admission_sweep_local_ce --clean 60 --noise 60
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SOGLIE = (10, 20, 30, 40, 50, 60, 70, 80, 90)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl",
                    default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--clean", type=int, default=60)
    ap.add_argument("--noise", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from benchmark.halumem_writepath_moat import _all_facts, _clean_facts
    from verimem.local_grounding import try_local_score

    users = []
    with open(a.jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                users.append(json.loads(line))
    if not users:
        print("dataset vuoto")
        return 1

    rnd = random.Random(a.seed)

    # clean: (fatto, la sua sessione)
    puliti: list[tuple[str, str]] = []
    for u in users:
        puliti.extend(_clean_facts(u))
    rnd.shuffle(puliti)
    puliti = puliti[:a.clean]

    # noise: un fatto di un ALTRO utente contro una sessione che non lo contiene
    tutti: list[str] = []
    for u in users:
        tutti.extend(_all_facts(u))
    rnd.shuffle(tutti)
    rumore: list[tuple[str, str]] = []
    for i in range(min(a.noise, len(puliti))):
        estraneo = tutti[i % len(tutti)]
        _sorgente = puliti[(i + 1) % len(puliti)][1]
        if estraneo and estraneo not in _sorgente:
            rumore.append((estraneo, _sorgente))

    def punteggia(coppie):
        out = []
        for fatto, src in coppie:
            r = try_local_score(src, fatto)
            out.append(float(r[0]) if r is not None else None)
        return [s for s in out if s is not None]

    print(f"punteggio {len(puliti)} clean e {len(rumore)} noise col CE locale…")
    s_clean = punteggia(puliti)
    s_noise = punteggia(rumore)
    if not s_clean or not s_noise:
        print("il CE locale non ha prodotto punteggi (modello assente?)")
        return 1

    res = {
        "judge": "local_ce",
        "clean_n": len(s_clean), "noise_n": len(s_noise),
        "clean_mean": round(sum(s_clean) / len(s_clean), 2),
        "noise_mean": round(sum(s_noise) / len(s_noise), 2),
        "sweep": [],
    }
    for t in SOGLIE:
        adm = sum(1 for s in s_clean if s >= t) / len(s_clean)
        rej = sum(1 for s in s_noise if s < t) / len(s_noise)
        res["sweep"].append({
            "threshold": t,
            "clean_admit_rate": round(adm, 3),
            "noise_reject_rate": round(rej, 3),
        })

    print(f"\nclean mean {res['clean_mean']}   noise mean {res['noise_mean']}")
    print(f"{'soglia':>7} {'clean-adm':>10} {'noise-rej':>10}   cancello (>=90/>=95)")
    for r in res["sweep"]:
        ok = "SI" if (r["clean_admit_rate"] >= 0.90
                      and r["noise_reject_rate"] >= 0.95) else "no"
        print(f"{r['threshold']:>7} {r['clean_admit_rate']:>10.3f} "
              f"{r['noise_reject_rate']:>10.3f}   {ok}")

    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"\nscritto {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
