"""Una cartella VUOTA convince il prodotto che il giudice del moat c'e'.

Misurato il 15/08 su `origin/main` (`e199f55b`): puntato il modello a una
cartella esistente e vuota — lo stato in cui un download interrotto lascia il
disco — il prodotto rispondeva cosi'. **Curato il 17/08**: le due righe usano
ora `_holds_a_model`, e i due test che erano `xfail(strict=True)` sono i primi
due qui sotto, senza marcatore.

    _holds_a_model(dir)   False     <- il criterio giusto, gia' in casa
    local_ce_available()  True      <- local_grounding.py:309, `.exists()`
    judge_state()         "ready"   <- local_grounding.py:285, stesso criterio
    warmup                "moat gate model already installed"  EXIT=0
    doctor                "local CE gate model installed (state here: ready)"

⇒ Il comando che esiste APPOSTA per procurare il giudice si dichiara
soddisfatto, e non riprova piu'. `warmup --force` non esiste, `doctor` non
nomina il percorso e il README nomina il modello ma mai dove sta: dalla
cartella vuota non si esce se non cancellandola a mano.

Come ci si finisce dentro: `_download_and_extract_tar` crea la destinazione
PRIMA di scaricare (riga 346), quindi una rete che cade, un `Ctrl-C` o un
sha256 che non torna lasciano la cartella li', vuota, per sempre.

Cosa NON e' rotto, e sta qui perche' un banco che misura solo il difetto non
dice quanto e' grave: la SCRITTURA regge. Con la cartella vuota il gate non
ammette nulla come verificato — `moat=not_run:no_judge`, `status=model_claim`,
`confidence_tier=unverified`. Il difetto inganna la diagnostica, non il moat.

I due `xfail(strict=True)` sono caduti il 17/08, quando le righe 285 e 309
hanno cominciato a usare `_holds_a_model(j.model_dir)` — la funzione era gia'
dieci righe piu' su, nello stesso file. Il prezzo previsto qui («i due che
cadono provano *il modello c'e'* con un `mkdir`, cioe' sono verdi grazie a
questo difetto») e' stato confermato: erano `test_lo_stato_del_giudice_ha_un_
nome` e `test_l_advisory_non_dice_piu_che_il_modello_manca`, curati mettendo
un `config.json` nella cartella che simulava il modello.

⚠️ Il conto era 2 su 15 file di banco; rifatto il 17/08 su 19 file (il
perimetro e' cresciuto) i falliti sono 4: i due `mkdir` piu' due di
`test_il_gate_dice_se_il_giudice_non_si_carica.py`, che presidiava il ramo
«c'e' ma non si carica» usando come esca proprio la cartella vuota. Curato
quello, l'esca giusta e' `config.json` senza i pesi. **Una cura che chiude un
difetto e lascia scoperto il ramo che qualcun altro presidiava non e' finita.**
"""

from __future__ import annotations

import pytest

from verimem import local_grounding as lg


@pytest.fixture
def cartella_vuota(monkeypatch, tmp_path):
    """Lo stato che un download interrotto lascia: la cartella c'e', vuota."""
    d = tmp_path / "local_gate_ce_v2"
    d.mkdir()
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(d))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    lg._GATE_DELEGATO["ok"] = False
    yield d
    monkeypatch.setattr(lg, "_judge", None, raising=False)


def test_il_criterio_giusto_e_gia_in_casa(cartella_vuota):
    """La controprova che rende leggibili i due xfail qui sotto: la funzione
    che sa distinguere una cartella vuota da un modello esiste gia'."""
    assert lg._holds_a_model(cartella_vuota) is False


def test_una_cartella_vuota_non_e_un_giudice(cartella_vuota):
    """Il difetto sul booleano che il gate legge per dire «ho un giudice»."""
    assert lg.local_ce_available() is False, (
        "una cartella vuota non contiene un giudice: dirlo disponibile manda "
        "il gate nel ramo L4 e `warmup` a non scaricare piu' nulla")


def test_una_cartella_vuota_non_e_uno_stato_pronto(cartella_vuota):
    """Il difetto sulla PAROLA che tre superfici leggono (doctor, l'advisory
    L4, la ricevuta MCP) — il commento a fianco della riga 285 lo dichiara."""
    assert lg.judge_state() == "absent", (
        "«ready» su una cartella vuota: e' la diagnosi che manda l'operatore "
        "a cercare un problema di caricamento invece di un modello mancante")


def test_chi_scarica_invece_riprova_e_lo_dice(cartella_vuota):
    """La popolazione opposta, e il motivo per cui la cura e' UNA riga:
    `ensure_gate_model` guarda gia' `config.json`, quindi sulla stessa
    cartella riprova e riporta onestamente il fallimento. E' `warmup` a non
    arrivarci mai, perche' corto-circuita su `local_ce_available()` prima."""
    chiamate: list[tuple] = []

    def finto_download(sorgente, dest):
        chiamate.append((sorgente, dest))

    ok, messaggio = lg.ensure_gate_model(model_dir=cartella_vuota,
                                         download=finto_download)
    assert len(chiamate) == 1, "sulla cartella vuota il download NON e' stato ritentato"
    assert ok is False
    assert "config.json" in messaggio, messaggio


def test_un_download_interrotto_lascia_la_cartella_che_mente(tmp_path):
    """L'anello che innesca tutto: la destinazione nasce PRIMA del download
    (riga 346), quindi un fallimento transitorio diventa permanente."""
    dest = tmp_path / "local_gate_ce_v2"

    def opener_che_cade(url):
        raise OSError("connessione caduta a meta' scaricamento")

    assert not dest.exists()
    with pytest.raises(OSError):
        lg._download_and_extract_tar("https://esempio.invalido/x.tar.gz", dest,
                                     opener=opener_che_cade)
    assert dest.exists(), "la destinazione non e' stata creata: l'anello e' cambiato"
    assert list(dest.iterdir()) == [], "la cartella non e' vuota: l'anello e' cambiato"
    assert lg._holds_a_model(dest) is False
