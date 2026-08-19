"""Il soggetto a inizio frase non arrivava all'asse che decide le supersessioni.

`extract_entities_lite` scarta di PROPOSITO un nome di una sola parola quando
apre la frase: li' la maiuscola e' grammaticale, non un segnale di nome proprio
(`_is_sentence_initial`). E' una scelta di precisione e resta giusta.

Il costo, misurato il 2026-08-19 a variabile singola — cambia solo la POSIZIONE:

    «Marco leads the payments team.»                 entita' -> []
    «The payments team is led by Marco.»             entita' -> [Marco proper]
    «Marco guida il team dei pagamenti.»             entita' -> []
    «Il team dei pagamenti e' guidato da Marco.»     entita' -> [Marco proper]
    «Marco met Bianchi yesterday.»                   entita' -> [Bianchi]  (solo il secondo)

Italiano e inglese mettono il soggetto all'inizio: l'asse entita' di
`_entita_diverse` era quindi cieco proprio sulla forma piu' comune, e due fatti
su soggetti DIVERSI si ritiravano a vicenda. E' la causa dei sette rossi di
`test_answer_judge_stage.py`, dove la fixture scrive «Marco leads...» e «The
payments team migrated to Stripe...» sullo stesso topic e ne sopravvive uno.

La cura sta nel CONSUMATORE, non nell'estrattore: recuperare il soggetto
iniziale solo dentro questo confronto lascia intatto il grafo di tutto il resto.
Portata misurata sulle supersessioni gia' avvenute: +44 coppie tenute entrambe
su 160 `same-source evolution`, e +0 su 202 `exact-text dedup`, che sono
duplicati per costruzione — la cura non tocca cio' che va davvero ritirato.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem.anti_confab_gate import _entita_diverse


def _f(testo: str) -> SimpleNamespace:
    return SimpleNamespace(proposition=testo)


@pytest.mark.parametrize("a, b", [
    # il caso che rompe test_answer_judge_stage: persona contro servizio
    ("Marco leads the payments team.",
     "The payments team migrated to Stripe in 2025."),
    # due soggetti in prima posizione, nessun codice, nessuna data
    ("Rossi pesa 70 chilogrammi.", "Bianchi pesa 95 chilogrammi."),
    ("Marco guida il team dei pagamenti.", "Stripe elabora i pagamenti."),
    # il caso che ha motivato la cura di ws8 (item-5): due datacenter che
    # condividono l'ACRONIMO e si distinguono per il proper. Deve restare True.
    ("Il datacenter DC-Nord ha 40 rack.", "Il datacenter DC-Sud ha 55 rack."),
])
def test_due_soggetti_a_inizio_frase_non_si_ritirano(a: str, b: str) -> None:
    assert _entita_diverse(_f(a), _f(b)) is True


@pytest.mark.parametrize("a, b", [
    # LA REGRESSIONE PER CUI QUESTA CURA FU RITIRATA IL 2026-08-04:
    # l'aggiornamento legittimo deve continuare a ritirare.
    ("Il paziente Rossi pesa 70 chilogrammi.", "Il paziente Rossi pesa 78 chilogrammi."),
    ("Il file pesa 10 MB.", "Il file pesa 12 MB."),
    ("The file weighs 10 MB.", "The file weighs 12 MB."),
    # stesso soggetto, due attributi: e' lo stesso soggetto, non due cose
    ("Marco guida il team.", "Marco lavora a Milano."),
    # stessa entita' in due POSIZIONI diverse: non deve diventare "due entita'"
    ("Marco guida il team.", "Il team e' guidato da Marco."),
    ("Marco leads the team.", "Marco leads the team."),
    # tipi condivisi, nessuna istanza che li distingua: GB e RAM sono TIPI, e
    # l'esclusione degli acronimi e' cio' che tiene in piedi questo caso.
    ("Il server ha 64 GB di RAM.", "Il server ha 128 GB di RAM."),
])
def test_un_aggiornamento_legittimo_continua_a_ritirare(a: str, b: str) -> None:
    assert _entita_diverse(_f(a), _f(b)) is False


def test_i_casi_gia_coperti_restano_coperti() -> None:
    """Il presidio di ws8 (item-5): i record numerati. Se questo diventa rosso,
    la cura ha rotto quella precedente."""
    assert _entita_diverse(_f("La issue 41 e' aperta."), _f("La issue 42 e' aperta.")) is True
