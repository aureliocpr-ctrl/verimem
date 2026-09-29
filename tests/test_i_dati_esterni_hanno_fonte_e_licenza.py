"""Ogni dataset esterno che il repository ridistribuisce dichiara fonte e licenza.

`benchmark/data/external/` contiene campioni di dati scritti da altri: HaluEval (MIT),
SQuAD 2.0 (CC BY-SA 4.0, che chiede attribuzione e che gli adattamenti restino sotto la
stessa licenza) e TruthfulQA (Apache-2.0). Il README della cartella attribuiva solo HaluEval.
Chi clona o forka il repository ridistribuisce anche gli altri due: la loro attribuzione
deve stare accanto ai file.

La cella: per ogni famiglia di file (il nome prima di `_dev`/`_heldout`/`_unanswerable`),
il README ha una sezione che la nomina, con una riga `Source:` e una riga `License:`.
"""
from __future__ import annotations

import re
from pathlib import Path

CARTELLA = Path(__file__).resolve().parents[1] / "benchmark" / "data" / "external"


def _famiglie() -> list[str]:
    return sorted({re.sub(r"_(dev|heldout|unanswerable)\.jsonl$", "", p.name)
                   for p in CARTELLA.glob("*.jsonl")})


def test_ogni_dataset_esterno_ha_fonte_e_licenza_nel_readme() -> None:
    famiglie = _famiglie()
    # CONTROLLO POSITIVO: senza file la cella non misurerebbe niente
    assert famiglie, f"nessun dataset in {CARTELLA}"
    sezioni = re.split(r"\n## ", (CARTELLA / "README.md").read_text(encoding="utf-8"))
    mancano = [f for f in famiglie
               if not any(f in s and "Source:" in s and "License:" in s for s in sezioni)]
    assert not mancano, f"dataset ridistribuiti senza fonte o licenza nel README: {mancano}"
