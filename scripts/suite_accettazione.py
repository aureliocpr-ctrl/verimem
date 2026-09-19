"""The acceptance suite, with a last line that cannot lie.

WHY THIS EXISTS. The documented command was::

    pytest -m accettazione --collect-only -q | tail -1

and with a broken list it printed, measured on 2026-09-17::

    ================== 13317 tests collected in 70.02s (0:01:10) ==================
    exit code 4

Thirteen thousand instead of six hundred and fifty-one, while the suite was
broken. The guard had fired - framed message, exit 4 - and pytest's own
collection summary printed after it, so the tail showed a bigger, calmer number.
Nobody lied: the reader was handed the wrong line.

WHAT THIS DOES. Runs the collection, reads the EXIT CODE, and prints exactly one
line: the true number, or the word ROTTA and the reason. A reader who only ever
looks at the last line still gets the truth.

    ACCETTAZIONE 651 raccolti
    ACCETTAZIONE ROTTA: tests/accettazione.txt elenca 1 file che la raccolta ...

IT DOES NOT RUN THE TESTS, only the collection - that is the scope that was
approved, and running them is the obvious next step, stated here so nobody has
to guess whether it was forgotten.
"""
from __future__ import annotations

import re
import subprocess
import sys

#: `651/13317 tests collected` (selezione) oppure `13317 tests collected` (tutto)
_RACCOLTI = re.compile(r"(?:(\d+)/\d+|(\d+)) tests? collected")
#: la cornice che la guardia dell'elenco stampa su stderr prima di sollevare
_MOTIVO = re.compile(r"^(tests/accettazione\.txt .*)$", re.MULTILINE)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    esito = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "accettazione",
         "--collect-only", "-q", *argv],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    uscita = (esito.stdout or "") + "\n" + (esito.stderr or "")

    if esito.returncode == 0:
        trovati = _RACCOLTI.search(uscita)
        quanti = (trovati.group(1) or trovati.group(2)) if trovati else None
        if quanti is None:
            # Esito zero e nessun numero: non si stampa un numero inventato.
            print("ACCETTAZIONE ROTTA: pytest non ha detto quanti test ha "
                  "raccolto (esito 0 senza riga di raccolta)")
            return 1
        print(f"ACCETTAZIONE {quanti} raccolti")
        return 0

    motivo = _MOTIVO.search(uscita)
    if motivo:
        print(f"ACCETTAZIONE ROTTA: {motivo.group(1).strip()}")
    else:
        coda = [r for r in uscita.splitlines() if r.strip()][-1:] or [""]
        print(f"ACCETTAZIONE ROTTA: pytest e' uscito {esito.returncode} "
              f"({coda[0].strip()[:120]})")
    return 1


if __name__ == "__main__":  # pragma: no cover - riga d'ingresso
    raise SystemExit(main())
