"""Le parole che aprono una frase inglese, e i gerundi in tutte e due le lingue, non sono nomi propri.

Il difetto: `_nomi_propri` scartava una parola maiuscola in apertura solo se stava in
`_NON_UNIT_WORDS`, che ha gli articoli e le preposizioni italiane ma non i pronomi, i
determinanti e gli ausiliari inglesi, e nessun gerundio. Sulle memorie estratte da
conversazioni inglesi vere «Both», «Being» e «Working» contavano come nomi propri, e sul
riconoscitore si reggono il confronto «stesso soggetto?» di `quantity_match` e il controllo
dei nomi che la fonte non ha. Sullo store vero, 184 fatti su 18388 aprivano con un gerundio
italiano contato come nome.

Le frasi qui sono scritte apposta, della stessa forma di quelle misurate: il testo delle
conversazioni vere ha una licenza che non entra in questo repository.

Predizione, scritta PRIMA di eseguire: le celle NON_SONO_NOMI rosse sul codice di prima (la
parola d'apertura esce fra i nomi), verdi con la cura; le celle SONO_NOMI verdi prima e dopo.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import _nomi_propri

NON_SONO_NOMI = [
    # (frase, la parola d'apertura che NON e' un nome, i nomi veri che devono restare)
    ("Both Anna and Luca agree on the plan for the fair.", "Both", {"Anna", "Luca"}),
    ("Being in a team of motivated people gave Marco new energy.", "Being", {"Marco"}),
    ("Working on old cars is like therapy for Dave.", "Working", {"Dave"}),
    ("They moved to Lisbon last spring.", "They", {"Lisbon"}),
    ("However, Nora won the regional tournament.", "However", {"Nora"}),
    ("Scrivendo il test ho trovato il difetto in Verimem.", "Scrivendo", {"Verimem"}),
    ("Cercando nel registro, Aldo ha visto la riga.", "Cercando", {"Aldo"}),
]

SONO_NOMI = [
    # (frase, i nomi che devono restare, compreso quello in apertura)
    ("Beijing hosts the games every four years.", {"Beijing"}),
    ("Orlando e' a Roma per lavoro.", {"Orlando", "Roma"}),
    ("Reading is a town in England.", {"Reading", "England"}),
    ("Will joined the club in March.", {"Will", "March"}),
    ("May runs the bakery with Tom.", {"May", "Tom"}),
    ("John admires the defence of the Lakers.", {"John", "Lakers"}),
]


@pytest.mark.parametrize("frase,apertura,nomi", NON_SONO_NOMI)
def test_la_parola_d_apertura_non_e_un_nome_proprio(frase: str, apertura: str, nomi: set[str]) -> None:
    trovati = _nomi_propri(frase)
    assert apertura not in trovati, f"«{apertura}» contato come nome proprio in {frase!r}: {sorted(trovati)}"
    assert nomi <= trovati, f"nomi veri persi in {frase!r}: {sorted(nomi - trovati)}"


@pytest.mark.parametrize("frase,nomi", SONO_NOMI)
def test_CONTROLLO_POSITIVO_il_nome_in_apertura_resta_un_nome(frase: str, nomi: set[str]) -> None:
    trovati = _nomi_propri(frase)
    assert nomi <= trovati, f"nomi veri persi in {frase!r}: {sorted(nomi - trovati)}"
