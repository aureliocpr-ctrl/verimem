"""L4.1 («il claim afferma un valore che la fonte non contiene») dice ASSENTE un
numero che la fonte SCRIVE, quando il numero sta dentro un composto letto in modo
diverso dai due lati. Cella RED (xfail strict): ogni caso e' una riga presa dal
corpus (store, 06/09) e ridotta al minimo; la funzione e' quella del prodotto,
`valore_non_nella_fonte.valori_non_nella_fonte`, senza giudice.

Misurato sul corpus (banco L41-e-i-numeri-composti-sul-corpus, 06/09 14:43):
484 fatti con fonte su 8.003 (6,0%) hanno almeno un valore che L4.1 dice
assente; letti uno per uno i 28 candidati del righello, 16 sono false assenze
(3,3% dei fermabili, 0,2% dei fatti con fonte), in queste forme: l'orario del
claim dentro un timestamp ISO della fonte (9), la stessa stringa con un suffisso
attaccato o in tabella (3), una data dentro un tag o un identificatore (3),
l'intervallo «30-31» (1). Altri 4 sono ARROTONDAMENTI (98.86 contro
98.86549377441406): per il contratto del gate («nessuna aritmetica») sono
assenze vere, e non stanno qui.

Il costo per l'utente: un fatto VERO, con la fonte che scrive il numero, entra
quarantined per «valore non nella fonte». La cura sta nel parser dei due lati
(stesso trattamento per composti e suffissi), ed e' di chi tiene il modulo.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

FALSE_ASSENZE = [
    ("orario dentro un timestamp ISO",
     "Il commit e' fallito alle 14:57.",
     "2c91f864  failure  2026-08-12T14:57  fix: le date"),
    ("orario con la frazione di secondo nella fonte",
     "La directory porta la data 2026-08-13 10:29:36.",
     "2026-08-13 10:29:36.847243800 +0200  tasks/bwws"),
    ("stessa stringa con un suffisso attaccato",
     "Il file contiene 0.971 sei volte.",
     "doc  0.971x1, 0.963x1, 60/60x2"),
    ("stessa stringa, in una riga di tabella",
     "Con soglia 0.40 i cluster sono 1.",
     "nota 0.40 1 431"),
    ("identificatore arXiv con la versione attaccata",
     "Il paper arXiv 2607.26760 elenca MemTensor.",
     "arXiv:2607.26760v1, intestazione: MemTensor"),
    ("data dentro un tag",
     "Il tag si chiama frozen-2026-05-13.",
     "TAG LOCALI: 4   frozen-2026-05-13   non matcha v*"),
]


@pytest.mark.xfail(strict=True, reason="L4.1 legge il composto in modo diverso nel claim e nella fonte")
@pytest.mark.parametrize("claim, fonte", [(c, f) for _n, c, f in FALSE_ASSENZE], ids=[n for n, _c, _f in FALSE_ASSENZE])
def test_RED_un_numero_che_la_fonte_scrive_non_e_assente(claim, fonte):
    assert valori_non_nella_fonte(claim, fonte) == []


def test_controllo_un_numero_che_la_fonte_non_scrive_resta_assente():
    assenti = valori_non_nella_fonte("La cella ha 12 failed.", "job 97037007547  10 failed")
    assert [a.testo for a in assenti] == ["12"]


def test_controllo_lo_stesso_numero_nudo_e_presente():
    assert valori_non_nella_fonte("La cella ha 10 failed.", "job 97037007547  10 failed") == []
