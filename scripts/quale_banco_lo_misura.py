"""Quale file di RISULTATI misura questa cosa? — indice di `benchmark/results/`.

PERCHE' ESISTE, e me lo sono guadagnato oggi. Il 30/08 ho aperto
`halumem_admission_sweep.json` (15+15 casi), ho trovato che il commento del gate
cita un numero che quel file non dice, e ho pubblicato un'accusa al prodotto.
**@ws2 mi ha fermata: esisteva `local_gate_calibrate_2026-07-15.json`, 400+400,
26 volte piu' grande, che dava un numero diverso e ribaltava il meccanismo.**

⇒ 🔑 Il difetto non era la fretta: **`benchmark/results/` ha 445 file e nessun
indice.** E lo strumento che avevo scritto la mattina stessa per non duplicare
(`chi_ha_gia_misurato.py`) **cerca nel REGISTRO, non nei RISULTATI** — quindi il
presidio c'era e guardava dall'altra parte.

    python scripts/quale_banco_lo_misura.py cut          # chi misura le soglie
    python scripts/quale_banco_lo_misura.py clean_scores # chi ha popolazioni pulite
    python scripts/quale_banco_lo_misura.py 0.33         # chi contiene questo numero

Ordina per DIMENSIONE DELLA POPOLAZIONE quando riesce a leggerla: **il file piu'
grande va guardato per primo**, ed e' esattamente il passo che mi mancava.

Legge, non scrive. Nessuna dipendenza dal prodotto.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RISULTATI = Path(__file__).resolve().parent.parent / "benchmark" / "results"

#: le chiavi che dichiarano quanto e' grande la popolazione di un banco
CHIAVI_N = ("clean_n", "noise_n", "n", "sessions", "count", "total", "n_reachable")


def popolazione(d: object) -> int | None:
    """La dimensione dichiarata, se il file la dice."""
    if isinstance(d, dict):
        for k in CHIAVI_N:
            v = d.get(k)
            if isinstance(v, int) and v > 0:
                return v
        for k in ("clean_scores", "noise_scores", "scores", "details", "tasks"):
            v = d.get(k)
            if isinstance(v, list) and v:
                return len(v)
    if isinstance(d, list):
        return len(d) or None
    return None


def main(termine: str) -> int:
    file = sorted(RISULTATI.glob("*.json"))
    if not file:
        print(f"  nessun .json in {RISULTATI}")
        return 1
    pat = re.compile(re.escape(termine), re.IGNORECASE)
    trovati: list[tuple[int, str, int | None]] = []
    illeggibili = 0
    for f in file:
        try:
            grezzo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            illeggibili += 1
            continue
        if not pat.search(grezzo):
            continue
        try:
            n = popolazione(json.loads(grezzo))
        except (json.JSONDecodeError, RecursionError):
            n = None
        trovati.append((n if n is not None else -1, f.name, n))

    print(f"  «{termine}» — {len(trovati)} file su {len(file)} in benchmark/results/")
    if illeggibili:
        print(f"  ({illeggibili} illeggibili, non contati)")
    if not trovati:
        print("  nessuno. Se stai per misurarlo tu, sei la prima.")
        return 0
    print(f"\n  {'popolazione':>12}   file")
    print("  " + "-" * 66)
    for _, nome, n in sorted(trovati, reverse=True)[:20]:
        print(f"  {(str(n) if n else '?'):>12}   {nome}")
    if len(trovati) > 20:
        print(f"  … e altri {len(trovati) - 20}")
    grandi = [n for _, _, n in trovati if n]
    if len(grandi) > 1:
        print(f"\n  ⚠️  le popolazioni vanno da {min(grandi)} a {max(grandi)}: "
              f"**guarda prima il piu' grande**.")
        print("     Un reperto trovato sul file piu' piccolo puo' essere una proprieta'")
        print("     di QUEL file e non del prodotto — e' successo il 30/08, a me.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(main(" ".join(sys.argv[1:])))
