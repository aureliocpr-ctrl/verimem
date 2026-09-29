"""`decomponi()` splits French and Spanish coordinations, without breaking «il y a» or «et al.».

The v3 judge is trained on the units `decomponi()` produces, in four languages. Until now the splitter
knew only the Italian and English coordinators («e/ed», «and»), so a French or Spanish memory always
came out whole: the judge would have seen only whole sentences in two of its four languages.

The traps are fixed expressions that contain the coordinator: French «il y a» is «there is», not a
coordination, and «et al.» ends an author list. A noun coordination («pan y mantequilla») must stay one
claim too, as it does in Italian and English. The verb list is shared by all languages, so a French or
Spanish verb form that is also an English word («a», «son», «es») cannot enter it: a cell guards that the
English article «a» is still not a verb.

Pure function, no model. Run from the root of the checkout:

    python -m pytest tests/test_decomponi_spezza_francese_e_spagnolo.py -q -p no:randomly
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import decomponi, ha_verbo_finito


@pytest.mark.parametrize("testo, atteso", [
    ("Claire est allée au marché et fait du vélo le dimanche.",
     ["Claire est allée au marché.", "Claire fait du vélo le dimanche."]),
    ("Lucía fue al mercado y compró pan fresco.",
     ["Lucía fue al mercado.", "Lucía compró pan fresco."]),
    ("Pablo terminó el informe y visitó a su abuela.",
     ["Pablo terminó el informe.", "Pablo visitó a su abuela."]),
])
def test_la_coordinata_francese_e_spagnola_si_spezza(testo: str, atteso: list[str]) -> None:
    assert decomponi(testo) == atteso


@pytest.mark.parametrize("testo", [
    "Il y a trois chats dans le jardin.",
    "Hier il y avait du vent sur la côte.",
    "Smith et al. ont publié l'article en mars.",
    "Pan y mantequilla son baratos en ese mercado.",
])
def test_le_espressioni_fisse_restano_intere(testo: str) -> None:
    assert decomponi(testo) == [testo]


def test_l_articolo_inglese_non_diventa_un_verbo() -> None:
    # «a» is the French «has», and the English article: the shared list must not take it
    assert not ha_verbo_finito("a new bike for the trip")
