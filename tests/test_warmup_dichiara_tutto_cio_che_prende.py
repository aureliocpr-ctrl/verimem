"""`warmup` annunciava un terzo di quello che scarica.

La descrizione diceva «~1.1 GB of model weights» — il solo embedder — e col
default il comando ne prendeva **tre**::

    embedder   intfloat/multilingual-e5-base                1082 MB   dichiarato
    gate       local_gate_ce_v2                              746 MB   «~656 MB» ❌
    reranker   cross-encoder/mmarco-mMiniLMv2-L12-H384-v1    470 MB   MAI NOMINATO
                                                     TOTALE ~2.3 GB

⇒ Chi leggeva la prima riga decideva su un terzo del costo. E il «~656 MB» del
gate era **cablato nel testo dell'help**: la cartella su disco è 746,1 MB
(`model.safetensors` 737,7 + `tokenizer.json` 8,3), un solo formato, niente
duplicati che spieghino la differenza.

📌 IL PEZZO C'ERA E NON ERA COLLEGATO. `_quanto_scarica()` esisteva già, con la
regola giusta scritta nel suo docstring — *«an unmeasured model does NOT
inherit another one's figure: saying nothing is honest, saying someone else's
number is not»* — e veniva chiamata **solo per l'embedder**. Qui la stessa
regola si applica all'insieme invece che al singolo.

⚠️ IL METODO DI MISURA DEL GATE È DIVERSO dagli altri due e sta scritto accanto
al numero: gli altri sono download cronometrati su cache vuota (19/08), il gate
è la cartella su disco. Coincidono per i safetensors, che non sono compressi,
ma chi rifà il conto deve saperlo.
"""
from __future__ import annotations

import pytest

from verimem.cli import (
    _MODEL_DOWNLOAD_MB,
    _WARMUP_DI_DEFAULT,
    _totale_di_default,
)


def test_il_default_prende_tre_modelli_non_uno():
    """Il fatto che rende il resto necessario."""
    assert len(_WARMUP_DI_DEFAULT) == 3, (
        f"warmup non prende più tre modelli: {_WARMUP_DI_DEFAULT}. Se è "
        f"cambiato, la descrizione del comando va rifatta con lo stesso numero")


def test_il_totale_e_la_somma_di_cio_che_prende_davvero():
    """⚠️ 1000 E NON 1024, ed è un cambio DELIBERATO del 22/08.

    La prima stesura di questo test divideva per 1024 come il codice, e il
    risultato era un numero in GiB con l'etichetta «GB»: 2298 MB davano
    «~2.2 GB» qui e «~2.3 GB» nel README, per la STESSA cartella. La tabella
    `_MODEL_DOWNLOAD_MB` è in MB DECIMALI (il gate misura 746 058 368 byte =
    746.1 MB, che in MiB fa 711.5), quindi 1000 è l'unità coerente.

    Il test resta rosso se qualcuno torna a 1024: l'unità è dichiarata qui,
    non ereditata dal codice — un test che ricopia la formula del codice non
    può accorgersi che la formula è sbagliata.
    """
    atteso = sum(_MODEL_DOWNLOAD_MB[n] for n in _WARMUP_DI_DEFAULT
                 if n in _MODEL_DOWNLOAD_MB)
    testo = _totale_di_default()
    assert f"{atteso / 1000:.1f} GB" in testo, (
        f"il totale annunciato ({testo!r}) non è la somma dei modelli che il "
        f"default prende ({atteso} MB in MB decimali)")


def test_il_totale_non_e_piu_quello_del_solo_embedder():
    """IL DIFETTO: la descrizione diceva «~1.1 GB», cioè l'embedder da solo."""
    solo_embedder = _MODEL_DOWNLOAD_MB["intfloat/multilingual-e5-base"]
    testo = _totale_di_default()
    assert f"{solo_embedder / 1000:.1f} GB" not in testo, (
        f"il totale coincide ancora col solo embedder: {testo!r}")


@pytest.mark.parametrize("assente", list(_WARMUP_DI_DEFAULT))
def test_un_modello_non_misurato_viene_NOMINATO_non_sparisce(
        assente, monkeypatch):
    """⚖️ IL PRESIDIO CHE VALE PIÙ DEL TOTALE: se un modello esce dalla tabella
    dei pesi, il conto non deve semplicemente calare — sarebbe un numero più
    piccolo e più rassicurante, prodotto da un'ASSENZA di misura.

    È la stessa forma d'errore che il doctor ha già curato («UNKNOWN, not
    zero») e che il docstring di `_quanto_scarica` enuncia per il singolo.
    """
    ridotta = {k: v for k, v in _MODEL_DOWNLOAD_MB.items() if k != assente}
    monkeypatch.setattr("verimem.cli._MODEL_DOWNLOAD_MB", ridotta)
    testo = _totale_di_default()
    assert "never measured" in testo, (
        f"tolto {assente!r} dalla tabella, il totale non lo dichiara: {testo!r}")
    assert assente in testo, (
        f"il modello non misurato non viene NOMINATO: {testo!r}")


def test_l_help_del_gate_legge_la_tabella_invece_di_cablare_il_numero():
    """Il «~656 MB» era scritto a mano nell'help e sbagliato di 90 MB. Un
    numero cablato in una frase invecchia da solo."""
    from verimem.cli import app
    atteso = _MODEL_DOWNLOAD_MB["local_gate_ce_v2"]
    aiuti = []
    for c in getattr(app, "registered_commands", []):
        if getattr(c, "callback", None) and c.callback.__name__ == "warmup":
            import inspect
            for p in inspect.signature(c.callback).parameters.values():
                h = getattr(p.default, "help", None)
                if h:
                    aiuti.append(h)
    if not aiuti:
        pytest.skip("l'help di warmup non è ispezionabile da qui")
    testo = " ".join(aiuti)
    assert f"{atteso} MB" in testo, (
        f"l'help del gate non porta il numero della tabella ({atteso} MB): "
        f"{testo!r}")
    assert "656" not in testo, "il numero cablato sbagliato è tornato"
