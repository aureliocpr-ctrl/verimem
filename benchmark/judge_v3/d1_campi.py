"""The fields every D1 builder writes, and the check every builder runs before writing.

D1 has more than one builder (dialogues, documents, paraphrases) and they write the same fields: a field
two builders read in two ways mixes the halves without an error. It happened on 2026-09-29 with
`n_unita`, a position for one builder and a count for the other. So the names say what they hold:

  unita_nella_memoria  how many units `decomponi()` makes of the memory
  indice_unita         which of those units the claim is, counted from 0

and the check does not trust the builder: it runs `decomponi()` on every memory, wants the claim to BE
unit `indice_unita` and the count to be the number of units, and wants the rows of a (source, memory)
pair to cover all of its units. The same (source, claim) pair appears once: the judge reads only the
source and the claim, so two labels on one pair would teach it both answers, and the same label twice
counts one example as two and shifts the proportions a builder declares. `senza_coppie_ripetute()`
removes the repeats by construction, before the check.

The units depend on the version of `decomponi()`, so this module imports the verimem of THIS checkout
and refuses any other; builders take `decomponi` from here.
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


def coda(claim: str, soggetto: str) -> str:
    """The claim without its subject and final stop, to coordinate it: «Mara went to X.» -> «went to X»."""
    corpo = claim[len(soggetto):].strip() if claim.startswith(soggetto) else claim
    return corpo.rstrip(".")


def unita_con_etichetta(memoria: str, atomici: list[tuple[str, int]], soggetto: str) -> list[tuple[str, int]]:
    """`decomponi()` on the memory; every unit takes the lowest label among the atomic claims it contains
    (their body without the subject is inside the unit). A unit that contains no atomic claim is an
    error of the builder, and it stops."""
    out = []
    for unita in decomponi(memoria):
        dentro = [e for a, e in atomici if coda(a, soggetto).lower() in unita.lower()]
        if not dentro:
            raise ValueError(f"unit with no known atomic claim: {unita!r} from {memoria!r}")
        out.append((unita, min(dentro)))
    return out


def senza_coppie_ripetute(righe: list[dict]) -> list[dict]:
    """The rows with every (source, claim) pair once, in their order. A memory split in several units is
    kept whole or dropped whole, because the check wants all of its units, and it wins over a one-unit
    row that repeats one of its pairs: the unit carries the same example and its memory too."""
    gruppi: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)
    for k, r in enumerate(righe):
        # one row per unit: the same memory with the same source can come from two constructions, and
        # its units must not be counted twice inside the group either
        gruppi[(r["fonte"], r["memoria"])].setdefault(r["indice_unita"], k)
    visti: set[tuple[str, str]] = set()
    tieni: set[int] = set()
    for per_unita in gruppi.values():                    # first the memories split in several units
        indici = list(per_unita.values())
        if righe[indici[0]]["unita_nella_memoria"] < 2:
            continue
        coppie = {(righe[k]["fonte"], righe[k]["claim"]) for k in indici}
        if not coppie & visti:
            visti |= coppie
            tieni.update(indici)
    for k, r in enumerate(righe):                        # then the one-unit rows, in order
        coppia = (r["fonte"], r["claim"])
        if r["unita_nella_memoria"] < 2 and coppia not in visti:
            visti.add(coppia)
            tieni.add(k)
    return [r for k, r in enumerate(righe) if k in tieni]


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
        if coppia in etichette:
            prima_etichetta, prima_riga = etichette[coppia]
            if prima_etichetta != r["etichetta"]:
                raise ValueError(f"{r['id']}: the pair has label {r['etichetta']} here and {prima_etichetta} "
                                 f"in {prima_riga}")
            raise ValueError(f"{r['id']}: the pair is already in {prima_riga}: one example counted twice")
        etichette[coppia] = (r["etichetta"], r["id"])
        chiave = (r["fonte"], r["memoria"])
        indici[chiave].add(i)
        quante[chiave] = n
    for chiave, visti in indici.items():
        if visti != set(range(quante[chiave])):
            raise ValueError(f"memory {chiave[1]!r}: rows cover units {sorted(visti)} of {quante[chiave]}")
