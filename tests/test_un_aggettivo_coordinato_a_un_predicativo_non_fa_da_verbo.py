"""Un aggettivo coordinato a un predicativo («è freddo e forte la mattina») non e'
un verbo, anche se e' seguito da un determinante: la regola morfologica stretta
lo spezzava («Il vento forte la mattina.») in 8 controlli difficili su 10
(banco non cieco, 07/09 13:01, predizione contro la regola depositata prima).

La cura: se il pezzo PRECEDENTE finisce con una copula e una sola parola
(«è freddo», «sono vuote», «resta aperta»), il primo token del pezzo che segue
« e » e' coordinato a quel predicativo — e' un altro aggettivo — e non fa da
verbo morfologico. Il prezzo, dichiarato: un verbo vero coordinato a un
predicativo («è aperta e affitta la sala») resta fuso; «affitta» non e' in
lista e la fonte lo dira'.
"""
from __future__ import annotations

import pytest

from verimem.atomic_claims import decomponi

DIFFICILI = [
    "Il vento è freddo e forte la mattina.",
    "La piazza è vuota e grande ogni domenica.",
    "Il pane è caldo e dolce le prime ore.",
    "La riunione è lunga e breve ogni tanto.",
    "Il fiume è lento e verde la sera.",
    "La cucina è stretta e piena le sere d'estate.",
    "La musica è bassa e leggera la notte.",
    "Il cortile è pulito e libero ogni mattina.",
    "La stanza è pulita e libera ogni mattina.",
    "Le finestre sono chiuse e sporche la mattina.",
]
# la coda con un verbo VERO dopo un predicativo si spezza ancora quando il verbo e' in lista
ANCORA_DUE = [
    "La biblioteca è aperta e resta aperta il sabato.",
    "Il vento è forte e porta la pioggia la mattina.",
]
# dopo un PARTICIPIO («è aperta», «sono arrivati») cio' che segue puo' essere un
# verbo: la guardia del predicativo non scatta, e un verbo fuori lista si spezza
DOPO_UN_PARTICIPIO = [
    "La biblioteca è aperta e affitta la sala ai privati.",
    "Alcuni partecipanti non sono arrivati e rinvia la firma.",
]
# il prezzo dichiarato della guardia del TEMPO: un verbo fuori lista seguito da un
# determinante e una parola di tempo («lavora la domenica») resta fuso alla testa
PREZZO = "Il falegname porta i mobili a domicilio e lavora la domenica."


@pytest.mark.parametrize("testo", DIFFICILI)
def test_un_aggettivo_dopo_un_predicativo_resta_un_claim_solo(testo):
    claims = decomponi(testo)
    assert len(claims) == 1, claims


@pytest.mark.parametrize("testo", ANCORA_DUE + DOPO_UN_PARTICIPIO)
def test_un_verbo_dopo_un_predicativo_o_un_participio_si_spezza_ancora(testo):
    assert len(decomponi(testo)) == 2, decomponi(testo)


def test_il_prezzo_dichiarato_un_verbo_fuori_lista_seguito_da_un_tempo_resta_fuso():
    assert len(decomponi(PREZZO)) == 1, decomponi(PREZZO)
