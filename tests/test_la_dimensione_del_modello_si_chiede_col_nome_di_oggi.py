"""La dimensione del modello si chiede col nome che la libreria usa OGGI.

sentence-transformers 6 ha rinominato `get_sentence_embedding_dimension` in
`get_embedding_dimension`: il nome vecchio c'e' ancora, e a ogni chiamata dice
«FutureWarning: ... has been renamed» (misurato nei log della CI del 29/09 con la 6.1.0,
`embedding.py:148`). La 5 ha solo il nome vecchio.

IL DIFETTO NON E' L'AVVISO. `_adopt_true_dim` chiede la dimensione dentro un
`except Exception: pass`: il giorno in cui il nome vecchio sparisce, la domanda
solleva, l'eccezione si inghiotte, e la dimensione VERA non si adotta piu'. E' il
recall vuoto silenzioso che quella funzione esiste per impedire (iter 31: un modello
fuori tabella, 768 presunti contro 1024 veri, ogni vettore scartato dal filtro della
lunghezza). Con gli avvisi trattati da errori — come fa chi li vuole vedere — il
guasto arriva gia' con la 6.

LA CURA si chiede col nome nuovo, e col vecchio solo se il nuovo non c'e'. La cosa
veloce sarebbe stata zittire l'avviso: nasconde la rottura in arrivo e lascia il
guasto dov'e'.

I TRE MODELLI FINTI sono le tre versioni che un utente puo' avere: la 5 (solo il nome
vecchio: il CONTROLLO, gia' verde oggi), la 6 (tutti e due, il vecchio avvisa), la 7 che
verra' (solo il nome nuovo).
"""
from __future__ import annotations

import warnings

import pytest

import verimem.embedding as emb


class _ST5:
    def __init__(self, dim):
        self._dim = dim

    def get_sentence_embedding_dimension(self):
        return self._dim


class _ST6(_ST5):
    def get_embedding_dimension(self):
        return self._dim

    def get_sentence_embedding_dimension(self):
        warnings.warn("The `get_sentence_embedding_dimension` method has been renamed "
                      "to `get_embedding_dimension`.", FutureWarning, stacklevel=2)
        return self._dim


class _ST7:
    def __init__(self, dim):
        self._dim = dim

    def get_embedding_dimension(self):
        return self._dim


@pytest.fixture()
def dimensione_presunta():
    """Lo stato di CONFIG di un modello fuori tabella: 768 PRESUNTI, da correggere."""
    from verimem.config import CONFIG
    prima = (CONFIG.embedding_dim, getattr(CONFIG, "embedding_dim_assumed", False))
    object.__setattr__(CONFIG, "embedding_dim", 768)
    object.__setattr__(CONFIG, "embedding_dim_assumed", True)
    yield CONFIG
    object.__setattr__(CONFIG, "embedding_dim", prima[0])
    object.__setattr__(CONFIG, "embedding_dim_assumed", prima[1])


def test_controllo_la_5_col_solo_nome_vecchio_adotta_la_dimensione(dimensione_presunta):
    emb._adopt_true_dim(_ST5(1024))
    assert dimensione_presunta.embedding_dim == 1024, "il controllo non si accende: banco rotto"
    assert dimensione_presunta.embedding_dim_assumed is False


def test_la_6_con_gli_avvisi_da_errori_adotta_la_dimensione(dimensione_presunta):
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        emb._adopt_true_dim(_ST6(1024))
    assert dimensione_presunta.embedding_dim == 1024, (
        "con la 6 e gli avvisi trattati da errori la dimensione vera non si adotta: "
        "la domanda passa dal nome deprecato e l'avviso muore nell'except")


def test_la_7_col_solo_nome_nuovo_adotta_la_dimensione(dimensione_presunta):
    emb._adopt_true_dim(_ST7(1024))
    assert dimensione_presunta.embedding_dim == 1024, (
        "col solo nome nuovo la dimensione vera non si adotta: restano 768 presunti, "
        "e ogni vettore da 1024 cade dal filtro della lunghezza")


def test_la_verifica_della_dimensione_chiede_col_nome_nuovo(monkeypatch, dimensione_presunta):
    """`verify_model_dim` (il passo prima di una ricodifica) sulla 7: con la domanda
    giusta non ripiega sull'encode di prova, che il modello finto non sa fare."""
    monkeypatch.setattr(emb, "_model", lambda: _ST7(1024))
    assert emb.verify_model_dim() == (False, 1024)
