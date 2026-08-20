"""«rate 5 → rate 7» e' lo STESSO rate che cambia, non due record.

Il criterio posizionale di `_record_numerati_diversi` legge «<parola> <intero>»
come un'etichetta di record — «issue 41» e «issue 42» sono due issue — e su
quella famiglia ha ragione. Ma la stessa forma copre anche i VALORI numerati che
si aggiornano, e li' l'esito e' rovesciato: due scritture sullo stesso rate
finiscono per coesistere invece di aggiornarsi, e il recall serve il valore
vecchio accanto al nuovo.

MISURATO il 2026-08-20 con un A/B su tre alberi (worktree puliti, porcelain 0):

                                7d3e97a7   41ff5f34   40f6b5d8
    «uses rate 5 for billing»
      -> «rate 7»                False ok   True ROTTO  True ROTTO
    «loads profile 1 at boot»
      -> «profile 2»             False ok   True ROTTO  True ROTTO
    «issue 41» / «issue 42»       True ok    True ok     True ok
    «servizio 0» / «servizio 1»   True ok    True ok     True ok

E' una REGRESSIONE entrata con `41ff5f34`: prima quei due casi si aggiornavano.
La popolazione che quella cura doveva servire (issue, servizi) non e' toccata —
il criterio fa il suo lavoro e si porta dietro questi due.

⚠️ NON e' il vocabolario: `_ETICHETTE_RECORD` ha 19 voci e NON contiene
`rate` ne' `profile` (verificato). Chi cerchera' la causa li' non la trova.

I casi che DEVONO coesistere stanno qui accanto a quelli che devono aggiornarsi:
se cadono quelli, il rotto e' questo banco e non il prodotto.

MARCATORE: `xfail(strict=True)` e non un rosso, e la ragione va detta. Il
progetto ha UN SOLO rosso in CI ed e' il presidio del rilascio, che si spegne
pubblicando: aggiungere un secondo rosso bloccherebbe quella decisione, e la
decisione e' di Aurelio, non mia. `strict=True` significa che il giorno in cui
qualcuno cura questo difetto il test FALLISCE e chiede di togliere il marcatore
— non diventa un sensore scollegato. Se si preferisce il rosso, si toglie la
riga del marcatore e basta.
"""
from __future__ import annotations

import types

import pytest

from verimem.anti_confab_gate import _ETICHETTE_RECORD, _entita_diverse


def _diverse(a: str, b: str) -> bool:
    return _entita_diverse(types.SimpleNamespace(proposition=a),
                           types.SimpleNamespace(proposition=b))


AGGIORNANO = [
    ("rate", "uses rate 5 for billing", "uses rate 7 for billing"),
    ("profile", "loads profile 1 at boot", "loads profile 2 at boot"),
]

COESISTONO = [
    ("issue numerate", "issue 41 nel tracker e' aperta", "issue 42 nel tracker e' aperta"),
    ("servizi numerati", "Il servizio 0 ascolta sulla porta 8000.",
     "Il servizio 1 ascolta sulla porta 8001."),
    ("righe di un file", "la riga 12 di client.py va cambiata",
     "la riga 340 di client.py va cambiata"),
]


@pytest.mark.parametrize("nome,prima,dopo", AGGIORNANO, ids=[c[0] for c in AGGIORNANO])
@pytest.mark.xfail(strict=True, reason=(
    "APERTO 2026-08-20: regressione entrata con 41ff5f34. Il criterio posizionale "
    "legge «rate 5» come etichetta di record, quindi due valori dello stesso rate "
    "coesistono invece di aggiornarsi. Prima di quel commit erano corretti. "
    "strict=True: il giorno che si risolve, questo test FALLISCE e va tolto il marcatore."))
def test_un_valore_numerato_che_cambia_aggiorna_il_precedente(nome, prima, dopo):
    assert not _diverse(prima, dopo), (
        f"{nome}: «{prima}» e «{dopo}» sono lo stesso valore che cambia, "
        "non due record distinti")


@pytest.mark.parametrize("nome,uno,due", COESISTONO, ids=[c[0] for c in COESISTONO])
def test_CONTROLLO_i_record_numerati_continuano_a_coesistere(nome, uno, due):
    """La popolazione che il criterio posizionale serve. Se cade, il rotto e' il banco."""
    assert _diverse(uno, due), f"{nome}: sono due record distinti e devono restare entrambi"


def test_CONTROLLO_la_causa_non_e_il_vocabolario():
    """Chi cerchera' la causa in `_ETICHETTE_RECORD` non la trova: non ci sono."""
    assert "rate" not in _ETICHETTE_RECORD
    assert "profile" not in _ETICHETTE_RECORD
