"""Il MAX per frase (muro 1, 3b-bis) perde il claim la cui prova sta su DUE
righe della fonte: nessuna frase da sola lo regge, l'intero si'.

Da dove viene (06/09, Nadia su ws3-i-96-crolli-del-giudice-sui-claim-brevi):
sui 54 claim caduti dei 53 record puliti, rigiudicati sull'INTERO span con
try_local_score, 39 coincidono col MAX per frase e 15 divergono fino a +98 —
«Sui 2329 quarantinati 1728 hanno grounding NULL» prende 24,2 col MAX sulle 7
righe spezzate dello span e 99,98 sull'intero: la prova sono due righe
(«quarantinati ..... 2329» e «mai giudicati (grounding NULL) .... 1728»).

La cura: fra i candidati del MAX c'e' anche l'intero della fonte (nella
finestra del giudice), quando la fonte ha piu' di una frase. Costa una coppia
in piu' per claim nel lotto. Il giudice qui e' FINTO: 95 solo alla coppia
(intero, claim-a-due-righe), 95 anche alla coppia (frase giusta, claim-a-una-
riga), 5 altrove — cosi' la cella distingue i due casi e non misura il CE.
"""
from __future__ import annotations

import pytest

import verimem.local_grounding as lg
from verimem.local_grounding import frasi_della_fonte, punteggi_max_per_frase

FONTE = ("fatti totali ................. 12582. quarantinati ................. 2329. "
         "mai giudicati (grounding NULL) .... 1728 (74.2%). giudicati ......... 601.")
CLAIM_DUE_RIGHE = "Sui 2329 quarantinati 1728 hanno grounding NULL."
CLAIM_UNA_RIGA = "I giudicati sono 601."
FRASE_GIUSTA = "giudicati ......... 601."


class _GiudiceCheVedeSoloLIntero(lg.LocalGroundingJudge):
    def __init__(self) -> None:
        super().__init__()
        self.lotti: list[int] = []
        self._scorer = self._finto

    @property
    def threshold(self) -> float:  # nella base e' una property senza setter
        return 40.0

    def _finto(self, batch):  # noqa: ANN001
        self.lotti.append(len(batch))
        out = []
        for span, claim in batch:
            s = span.strip()
            if claim == CLAIM_DUE_RIGHE:
                out.append(95.0 if s == FONTE.strip() else 5.0)
            else:
                out.append(95.0 if s == FRASE_GIUSTA else 5.0)
        return out

    def _entro_la_finestra(self, span: str) -> str:  # niente tokenizer: costo zero
        return span


@pytest.fixture()
def giudice():
    return _GiudiceCheVedeSoloLIntero()


def test_CONTROLLO_la_fonte_ha_piu_frasi_e_il_finto_distingue_l_intero(giudice):
    assert len(frasi_della_fonte(FONTE)) >= 3
    assert giudice._finto([(FONTE, CLAIM_DUE_RIGHE)]) == [95.0]
    assert giudice._finto([(FRASE_GIUSTA, CLAIM_DUE_RIGHE)]) == [5.0]


def test_il_claim_a_una_riga_lo_regge_la_sua_frase(giudice):
    punti = punteggi_max_per_frase(FONTE, [CLAIM_UNA_RIGA], judge=giudice)
    assert punti is not None and punti[0] >= 40.0, punti


def test_il_claim_a_due_righe_lo_regge_solo_l_intero(giudice):
    punti = punteggi_max_per_frase(FONTE, [CLAIM_DUE_RIGHE], judge=giudice)
    assert punti is not None and punti[0] >= 40.0, punti


def test_un_lotto_solo_con_una_coppia_in_piu_per_claim(giudice):
    punteggi_max_per_frase(FONTE, [CLAIM_UNA_RIGA, CLAIM_DUE_RIGHE], judge=giudice)
    n_frasi = len(frasi_della_fonte(FONTE))
    assert giudice.lotti == [2 * (n_frasi + 1)], giudice.lotti
