"""«Il piano mensile costa 20 euro» cancellava «Il piano annuale costa 100 euro».

Aperto da giorni sul percorso dell'utente nuovo: due entità distinte da un
MODIFICATORE venivano lette come «stesso soggetto, valore nuovo», e la seconda
scrittura RITIRAVA la prima. 7 casi su 8, anche in inglese.

LA CAUSA NON ERA LA SOGLIA, ed è per questo che non si chiudeva: si era cercata
nel rapporto di overlap (`ENGRAM_CONFLICT_MIN_SHARED_RATIO`, tarato il
2026-08-03) e lì non poteva stare — su frasi corte la quota è 0.75, dieci volte
sopra qualunque soglia sensata. Il meccanismo giusto c'era già ed è un altro:
`quantity_match.CONTRAST_QUALIFIERS`, trenta gruppi di qualificatori che
distinguono due attributi dello stesso soggetto (read/write, client/server,
primario/replica, collaudo/produzione, caldo/freddo…).

Misurato il 2026-08-04, e la prova sta nel confronto:

    «Il piano annuale costa 100 euro» + «Il piano mensile costa 20 euro»
        -> VIVI=1, l'annuale ritirato
    «The annual plan costs 100 euro»  + «The monthly plan costs 20 euro»
        -> VIVI=1, l'annual ritirato
    «La latenza di lettura è 5 ms»    + «La latenza di scrittura è 9 ms»
        -> VIVI=2, entrambi

La terza coppia sopravvive PERCHÉ `lettura`/`scrittura` è uno dei trenta
gruppi. Le prime due no perché il gruppo della PERIODICITÀ non c'era: i trenta
gruppi coprono il dominio infrastrutturale (letture, repliche, ambienti) e non
quello commerciale e temporale, che è il primo che incontra chi prova il
prodotto con il proprio listino.

È la stessa classe già pagata tre volte in questi giorni — una lista costruita
su un dominio e usata su tutti (le stoplist monolingue, i detector L1 solo
inglesi, gli alias della data dir). Il meccanismo funziona: gli mancava il
mondo.

⚠️ IL VERSO OPPOSTO DEVE RESTARE: due fatti sullo STESSO periodo che dicono
numeri diversi si contraddicono davvero, e lì la supersessione deve continuare
a scattare. Il meccanismo lo fa già da sé — `ca == cb` non è un contrasto — e
l'ultimo test lo presidia.
"""
from __future__ import annotations

import logging
import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.quantity_match import content_tokens, contrasting_attrs

logging.disable(logging.INFO)


def _vivi(a: str, b: str) -> list[str]:
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    m.add(a, topic="mod/prova")
    m.add(b, topic="mod/prova")
    return [f.proposition for f in m.semantic.all()
            if not getattr(f, "superseded_by", None)
            and getattr(f, "status", "") != "quarantined"]


#: Le coppie del percorso utente: stesso soggetto, MODIFICATORE diverso.
DISTINTE = [
    ("Il piano annuale costa 100 euro.", "Il piano mensile costa 20 euro."),
    ("The annual plan costs 100 euro.", "The monthly plan costs 20 euro."),
    ("Il canone trimestrale e' 60 euro.", "Il canone semestrale e' 110 euro."),
    ("Il report giornaliero contiene 40 righe.",
     "Il report settimanale contiene 280 righe."),
]


@pytest.mark.parametrize("a,b", DISTINTE)
def test_due_periodi_diversi_sono_due_fatti(a, b):
    """Il cuore: un modificatore di periodo distingue due entità, non due
    versioni della stessa. Chi scrive il proprio listino non deve perderne
    metà."""
    vivi = _vivi(a, b)
    assert len(vivi) == 2, (
        f"uno dei due e' stato ritirato, ne resta {len(vivi)}: {vivi}\n"
        f"«{a}» e «{b}» parlano di due cose diverse")


@pytest.mark.parametrize("a,b", DISTINTE)
def test_e_il_predicato_del_prodotto_lo_riconosce(a, b):
    """La stessa cosa un livello più sotto, così un domani si vede SUBITO se a
    rompersi è la lista o il percorso che la usa."""
    assert contrasting_attrs(content_tokens(a), content_tokens(b)), (
        f"contrasting_attrs non vede il contrasto fra «{a}» e «{b}»")


def test_il_gruppo_gia_presente_continua_a_funzionare():
    """Il caso che funzionava prima: non deve muoversi."""
    assert len(_vivi("La latenza di lettura e' 5 ms.",
                     "La latenza di scrittura e' 9 ms.")) == 2


def test_LO_STESSO_periodo_con_numeri_diversi_resta_una_contraddizione():
    """IL VERSO OPPOSTO, ed è il vincolo che rende la cura sicura: se il
    modificatore è lo STESSO, i due fatti si contraddicono davvero e la
    supersessione deve continuare a scattare. Senza questo presidio, allargare
    la lista dei qualificatori sarebbe un modo per spegnere il conflitto."""
    vivi = _vivi("Il piano annuale costa 100 euro.",
                 "Il piano annuale costa 500 euro.")
    assert len(vivi) == 1, (
        f"due prezzi diversi per lo STESSO piano annuale sono rimasti "
        f"entrambi vivi: {vivi}. La cura ha spento la supersessione invece di "
        f"insegnarle a distinguere i soggetti")
