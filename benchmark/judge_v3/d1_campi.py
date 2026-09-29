"""The fields every D1 builder writes, and the check every builder runs before writing.

D1 has more than one builder (dialogues, documents, paraphrases) and they write the same fields: a field
two builders read in two ways mixes the halves without an error. It happened on 2026-09-29 with
`n_unita`, a position for one builder and a count for the other. So the names say what they hold:

  unita_nella_memoria  how many units `decomponi()` makes of the memory
  indice_unita         which of those units the claim is, counted from 0

and the check does not trust the builder: it runs `decomponi()` on every memory, wants the claim to BE
unit `indice_unita` and the count to be the number of units, and wants the rows of a (source, memory)
pair to cover all of its units. The same (source, claim) pair never carries two labels: two
constructions that meet on one pair would teach the judge both answers. The units depend on the version of `decomponi()`, so this module
imports the verimem of THIS checkout and refuses any other; builders take `decomponi` from here.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE))
import verimem  # noqa: E402
from verimem.atomic_claims import decomponi  # noqa: E402

if RADICE not in Path(verimem.__file__).resolve().parents:
    raise ImportError(f"verimem comes from {verimem.__file__}, not from this checkout ({RADICE})")

CAMPI = ("id", "lingua", "tipo", "fonte", "memoria", "claim", "etichetta",
         "unita_nella_memoria", "indice_unita", "generatore", "seme")


def controlla(righe: list[dict]) -> None:
    """Raise ValueError at the first row that breaks a field rule; return None if all rows keep them."""
    indici: dict[tuple[str, str], set[int]] = defaultdict(set)
    quante: dict[tuple[str, str], int] = {}
    etichette: dict[tuple[str, str], tuple[int, str]] = {}
    for r in righe:
        manca = [c for c in CAMPI if c not in r]
        if manca:
            raise ValueError(f"{r.get('id')}: fields missing {manca}")
        if r["etichetta"] not in (0, 1):
            raise ValueError(f"{r['id']}: etichetta {r['etichetta']!r} is not 0 or 1")
        unita = decomponi(r["memoria"])
        n, i = r["unita_nella_memoria"], r["indice_unita"]
        if n != len(unita):
            raise ValueError(f"{r['id']}: unita_nella_memoria={n}, decomponi() makes {len(unita)}")
        if not 0 <= i < n:
            raise ValueError(f"{r['id']}: indice_unita={i} outside 0..{n - 1}")
        if r["claim"] != unita[i]:
            raise ValueError(f"{r['id']}: the claim is not unit {i} of the memory: {unita[i]!r}")
        coppia = (r["fonte"], r["claim"])
        prima = etichette.setdefault(coppia, (r["etichetta"], r["id"]))
        if prima[0] != r["etichetta"]:
            raise ValueError(f"{r['id']}: the pair has label {r['etichetta']} here and {prima[0]} in {prima[1]}")
        chiave = (r["fonte"], r["memoria"])
        indici[chiave].add(i)
        quante[chiave] = n
    for chiave, visti in indici.items():
        if visti != set(range(quante[chiave])):
            raise ValueError(f"memory {chiave[1]!r}: rows cover units {sorted(visti)} of {quante[chiave]}")
