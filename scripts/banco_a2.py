"""Banco di a2 — la supersessione che ritira un fatto che dice ALTRO.

Quattro righe, e servono TUTTE E QUATTRO: la cura giusta e' quella che porta
la riga 1 a 0 lasciando la riga 2 a 1. La cura del 04/08 (leggere la
``source_signature`` in ``canonical_source_of``) e' stata ritirata proprio
perche' portava a 0 anche la riga 2 — vedi il docstring di
``supersession_policy.canonical_source_of``.

Gira FUORI da pytest di proposito: sotto pytest l'embedder e' uno stub su
SHA-256 (``conftest._stub_embedding_model``), e una misura che passa da una
similarita' misurerebbe il righello invece del difetto.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

from verimem import Memory
from verimem.continuity import save_checkpoint

SRC_DUE_RUN = (
    "=== 42bb3839 . ubuntu/py3.13 . job 96509052224 ===\n"
    "= 1 failed, 11767 passed, 42 skipped in 1253.71s =\n"
    "b7bc7b77 py3.13: = 1 failed, 11726 passed, 42 skipped, 8019 warnings ="
)
SRC_CARTELLA = "registro: Rossi 70 kg, poi 75 kg. Bianchi 95 kg."
SRC_ALTRA = "altra cartella: Bianchi 95 kg."

#: (nome, source_a, prop_a, source_b, prop_b, attese_supersessioni)
CASI = [
    ("1a il caso ws7 (due run, stesso stampo)", SRC_DUE_RUN,
     "La cella stampa 1 failed e 11767 passed.", SRC_DUE_RUN,
     "Su b7bc7b77 la cella py3.13 stampa 8019 warnings.", 0),
    ("1c due commit, ENTRAMBI nominati con «Su»", SRC_DUE_RUN,
     "Su 42bb3839 la cella stampa 11767 passed.", SRC_DUE_RUN,
     "Su b7bc7b77 la cella stampa 8019 warnings.", 0),
    ("1b Rossi/Bianchi (il caso del docstring)", SRC_CARTELLA,
     "Il paziente Rossi pesa 70 kg.", SRC_CARTELLA,
     "Il paziente Bianchi pesa 95 kg.", 0),
    ("2  aggiornamento LEGITTIMO (stesso soggetto)", SRC_CARTELLA,
     "Il paziente Rossi pesa 70 kg.", SRC_CARTELLA,
     "Il paziente Rossi pesa 75 kg.", 1),
    ("3  source DIVERSE (presidio del 04/08)", SRC_CARTELLA,
     "Il paziente Rossi pesa 70 kg.", SRC_ALTRA,
     "Il paziente Bianchi pesa 95 kg.", 0),
]


def _misura(caso: tuple) -> tuple[int, str]:
    nome, sa, pa, sb, pb, _attesa = caso
    d = pathlib.Path(tempfile.mkdtemp(prefix="ws7a2_"))
    m = Memory(path=d / "s.db")
    r1 = save_checkpoint(m, pa, topic="banco/a2", source=sa, principal="cli:local")
    r2 = save_checkpoint(m, pb, topic="banco/a2", source=sb, principal="cli:local")
    with sqlite3.connect(str(m.semantic.db_path)) as c:
        sup = c.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL",
        ).fetchone()[0]
    strati = {w.get("layer", "?") for w in (r2.get("warnings") or [])}
    strati |= {w.get("layer", "?") for w in (r1.get("warnings") or [])}
    return sup, ",".join(sorted(strati)) or "-"


def main() -> int:
    print(f"{'caso':46s} {'sup':>4s} {'attesa':>7s}  esito   layer")
    rotte = 0
    for caso in CASI:
        nome, *_, attesa = caso
        sup, strati = _misura(caso)
        ok = sup == attesa
        rotte += 0 if ok else 1
        print(f"{nome:46s} {sup:4d} {attesa:7d}  "
              f"{'ok    ' if ok else 'ROTTA '}  {strati}")
    print(f"\nrighe che non rispettano l'attesa: {rotte} su {len(CASI)}")
    return rotte


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
