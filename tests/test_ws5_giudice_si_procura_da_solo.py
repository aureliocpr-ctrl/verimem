"""Un giudice ASSENTE si scarica da solo; uno ROTTO no. La distinzione e' il punto.

Misurato da utente il 02/09 sul pacchetto 0.7.1 servito da PyPI (HOME vergine):

    $ verimem remember "<claim falso>" --source "<fonte che lo smentisce>"
      flow.write  layers=[]  status=model_claim  stored=True
      admitted                                                   EXIT=0

Il claim falso entra perche' il modello del giudice non c'e', e oggi nessuno lo procura:
``ensure_gate_model()`` e' chiamata SOLO da ``verimem warmup`` (``cli.py:594``), che
l'utente non sa di dover lanciare.

PERCHE' LA DISTINZIONE ASSENTE/ROTTO E' TUTTA LA CURA — il commento accanto al codice
dice perche' il fallimento viene messo in cache::

    # cache the failure: a broken/absent model must not re-pay the load attempt
    # on every gated write

Chi innestasse il download senza distinguere reintrodurrebbe **esattamente** quel costo:
un modello corrotto riproverebbe a ogni scrittura. ⇒ Si scarica **solo se la cartella non
esiste**, una volta, e il fallimento resta in cache come oggi.

COSTO MISURATO (02/09, HOME nuova, una sola esecuzione)::

    ensure_gate_model()               13,4s     711,5 MB
    caricamento del modello           54,1s     (si paga GIA' oggi, senza cura)
    secondo giudizio                   0,2s
"""
from __future__ import annotations

import pytest

import verimem.local_grounding as lg


def _giudice(model_dir):
    """Un giudice che punta a `model_dir`, senza scorer iniettato."""
    return lg.LocalGroundingJudge(model_dir)


def test_modello_ASSENTE_viene_procurato_una_volta_sola(tmp_path, monkeypatch):
    """La cura: cartella inesistente -> si scarica -> si riprova UNA volta.

    RED prima della cura: `_ensure_scorer` solleva senza aver mai chiamato
    `ensure_gate_model`, e `chiamate["fetch"]` resta 0.
    """
    mancante = tmp_path / "non_esiste"
    chiamate = {"fetch": 0, "load": 0}

    def finto_fetch(model_dir=None, **kw):
        chiamate["fetch"] += 1
        # un download RIUSCITO crea la cartella coi pesi
        d = lg._resolve_model_dir(model_dir) if model_dir else mancante
        d.mkdir(parents=True, exist_ok=True)
        (d / "config.json").write_text("{}")
        (d / "model.safetensors").write_bytes(b"\x00")
        return True, f"gate model installed at {d}"

    def finto_load(model_dir, **kw):
        chiamate["load"] += 1
        # fallisce finche' la cartella non c'e'; riesce dopo il download
        from pathlib import Path
        if not (Path(model_dir) / "config.json").exists():
            raise FileNotFoundError(str(model_dir))
        return lambda coppie: [0.5 for _ in coppie]

    monkeypatch.setattr(lg, "ensure_gate_model", finto_fetch)
    monkeypatch.setattr(lg, "make_finetuned_scorer", finto_load)
    # ⚠️ LA SUITE GIRA OFFLINE (misurato: `_download_disattivato()` e' True sotto
    # pytest), e la guardia fa il suo lavoro: senza toglierla, questo test
    # misurerebbe l'offline invece del download. ⇒ E' anche un dato utile di per
    # se': in CI la cura non scarichera' MAI, quindi il timore «una pipeline che
    # tira 711 MB» e' gia' escluso dall'ambiente di test.
    for _f in ("VERIMEM_OFFLINE", "HIPPO_OFFLINE", "ENGRAM_OFFLINE",
               "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(_f, raising=False)

    j = _giudice(mancante)
    scorer = j._ensure_scorer()

    assert scorer is not None, "dopo il download il giudice deve esserci"
    assert chiamate["fetch"] == 1, "il modello assente va procurato UNA volta"
    assert chiamate["load"] == 2, "un tentativo prima del download e uno dopo"


def test_modello_ROTTO_non_viene_riscaricato(tmp_path, monkeypatch):
    """Il controllo NEGATIVO: la cartella c'e' ma e' illeggibile.

    Qui la cura NON deve scattare — scaricare sopra un modello corrotto e'
    proprio il costo che la cache del fallimento esiste per evitare.
    """
    rotto = tmp_path / "rotto"
    rotto.mkdir()
    (rotto / "config.json").write_text("{ questo non e' json valido")
    chiamate = {"fetch": 0, "load": 0}

    def finto_fetch(model_dir=None, **kw):
        chiamate["fetch"] += 1
        return True, "scaricato"

    def finto_load(model_dir, **kw):
        chiamate["load"] += 1
        raise ValueError("config illeggibile")

    monkeypatch.setattr(lg, "ensure_gate_model", finto_fetch)
    monkeypatch.setattr(lg, "make_finetuned_scorer", finto_load)

    j = _giudice(rotto)
    with pytest.raises(Exception):
        j._ensure_scorer()

    assert chiamate["fetch"] == 0, "un modello ROTTO non si riscarica"
    assert chiamate["load"] == 1, "un solo tentativo, poi la cache del fallimento"

    # e il secondo tentativo non ricarica nulla: la cache regge
    with pytest.raises(Exception):
        j._ensure_scorer()
    assert chiamate["load"] == 1, "il fallimento resta in cache come oggi"


def test_il_download_si_disattiva_per_gli_air_gapped(tmp_path, monkeypatch):
    """`VERIMEM_OFFLINE=1` esiste gia' ed e' citata da `doctor` («for air-gapped
    deploys»): una cura che la ignorasse romperebbe una promessa scritta."""
    mancante = tmp_path / "assente_offline"
    chiamate = {"fetch": 0}

    def finto_fetch(model_dir=None, **kw):
        chiamate["fetch"] += 1
        return True, "scaricato"

    def finto_load(model_dir, **kw):
        raise FileNotFoundError(str(model_dir))

    monkeypatch.setattr(lg, "ensure_gate_model", finto_fetch)
    monkeypatch.setattr(lg, "make_finetuned_scorer", finto_load)
    monkeypatch.setenv("VERIMEM_OFFLINE", "1")

    j = _giudice(mancante)
    with pytest.raises(Exception):
        j._ensure_scorer()
    assert chiamate["fetch"] == 0, "offline: nessun download, e il fallimento e' onesto"
