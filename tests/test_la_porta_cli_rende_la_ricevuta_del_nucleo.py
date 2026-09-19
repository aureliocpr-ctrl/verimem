"""La porta CLI rende la Ricevuta del nucleo, e con ``--json`` stdout e' SOLO JSON.

Questo banco misura alla PORTA — esegue `python -m verimem.cli` in un processo
suo — e non leggendo il sorgente: il livello a cui misuri decide il verdetto, e
qui la domanda e' «che cosa riceve chi usa il prodotto», non «che cosa c'e'
scritto in cli.py».

IL ROSSO CHE QUESTO BANCO COGLIE, misurato il 18/09 prima della cura:

    $ verimem save "..." --json | python -c "import json,sys; json.load(sys.stdin)"
    json.decoder.JSONDecodeError: Extra data: line 1 column 5 (char 4)

Due righe di giornale (`flow.entity`, `flow.write`) cadono su STDOUT prima
dell'oggetto. Ed `exit_code` resta 0 in tutti e due i casi: chi mette `| jq` in
fondo prende un errore di parsing e crede di aver funzionato. E' pulito solo con
`HIPPO_LOG_STDERR=1`, che nessun utente sa di dover mettere.

⚠️ LA TERZA CELLA E' QUELLA CHE DECIDE. `--json` sta su sette comandi: se la
cura vale solo per `save`, e' una copia e non una superficie, e gli altri sei
restano rotti in silenzio. Per questo qui si misura anche `tip --json`, che e'
un comando che LEGGE — nessuna scrittura, nessun giudice da caricare.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from verimem.core import CHIAVI

RADICE = Path(__file__).resolve().parents[1]

#: Una scrittura che lo schermo lessicale FERMA: e' un auto-elogio senza fonte.
#: Non serve nessun giudice per bocciarla, quindi la cella resta veloce.
FRASE_FERMATA = "Il servizio funziona perfettamente, verificato in produzione."


def _cli(*argomenti: str, store: Path) -> subprocess.CompletedProcess:
    """Esegue la porta in un processo separato, su uno store isolato.

    ⚠️ TUTTE E QUATTRO le variabili, non tre: il 14/09 tre variabili puntavano
    a uno store di prova e la scrittura e' finita in quello vero.
    """
    ambiente = dict(os.environ)
    ambiente.update(
        ENGRAM_DATA_DIR=str(store), HIPPO_DATA_DIR=str(store),
        VERIMEM_DATA_DIR=str(store), ENGRAM_EVENT_LOG=str(store / "eventi.jsonl"),
    )
    #: Se fosse posta dall'ambiente di chi esegue i test, la cella misurerebbe
    #: quella e non la cura: e' il confondente che questo banco esiste per
    #: escludere.
    ambiente.pop("HIPPO_LOG_STDERR", None)
    return subprocess.run(
        [sys.executable, "-u", "-m", "verimem.cli", *argomenti],
        cwd=RADICE, env=ambiente, capture_output=True, text=True, timeout=600,
    )


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "store"


def test_save_json_e_leggibile_da_una_macchina(store: Path):
    """Il rosso di partenza: `json.load` moriva con «Extra data»."""
    esito = _cli("save", "Una riga qualunque di controllo.",
                 "--topic", "prova/1b1", "--json", "--local", store=store)
    assert esito.returncode == 0, esito.stderr[-800:]
    json.loads(esito.stdout)          # se muore qui, stdout non e' solo JSON


def test_un_ALTRO_comando_con_json_e_altrettanto_pulito(store: Path):
    """LA CELLA CHE DECIDE fra una superficie e una copia.

    Se passa solo `save`, la cura e' stata messa dentro un comando invece che
    nel punto per cui ogni comando passa, e gli altri sei restano rotti senza
    che nessuno lo veda.
    """
    _cli("save", "Un fatto da mettere sulla catena.", "--topic", "prova/1b1",
         "--json", "--local", store=store)
    esito = _cli("tip", "--json", store=store)
    assert esito.returncode == 0, esito.stderr[-800:]
    json.loads(esito.stdout)


def test_la_ricevuta_porta_le_chiavi_del_nucleo(store: Path):
    """Le quattordici di `CHIAVI`, per INSIEME e non per conteggio.

    ⚠️ Il conteggio non falsifica niente: il 18/09 la CLI ne rendeva undici, e
    un controllo su «almeno quattordici» sarebbe passato appena qualcuno
    avesse aggiunto tre campi qualsiasi. Qui si confrontano i NOMI.
    """
    esito = _cli("save", "Un altro fatto di controllo.", "--topic", "prova/1b1",
                 "--json", "--local", store=store)
    reso = json.loads(esito.stdout)
    mancanti = sorted(set(CHIAVI) - set(reso))
    assert not mancanti, f"la porta non rende: {mancanti}"


def test_una_scrittura_fermata_dice_CHI_l_ha_fermata(store: Path):
    """Il rosso del pari: la CLI non diceva chi aveva fermato.

    `quarantined_by` esiste nel dizionario del cancello ma e' CONDIZIONALE
    (`client.py`), e nessuno lo portava in un campo con un nome stabile. Una
    ricevuta che dice «fermato» senza dire da CHI e' meta' ricevuta.

    ⚠️ PERCHE' UNA SOURCE CHE NON SOSTIENE, e non un auto-elogio: `save` scrive
    come NOTA di sessione (`meta_narrative=True`) e per quella via lo schermo
    lessicale NON gira — quattro frasi di auto-elogio sono passate tutte come
    «ammesso». Qui serve il moat, e il moat gira solo con una source. La prima
    stesura di questa cella si arrendeva con uno `skip` quando la frase passava:
    uno skip in un banco che deve provare una cura e' un guardiano che mente, e
    va tolto, non spiegato.
    """
    esito = _cli("save", "Il totale della fattura e' 500 euro.",
                 "--topic", "prova/1b1",
                 "--source", "Il documento riporta un totale di 300 euro.",
                 "--json", "--local", store=store)
    reso = json.loads(esito.stdout)
    assert reso["esito"] == "fermato", f"atteso fermato, reso {reso.get('esito')!r}"
    assert reso["fermato_da"], "fermato senza dire da CHI"


def test_il_punteggio_viaggia_con_la_sua_scala_e_il_margine_e_calcolato(store: Path):
    """Tre numeri e una parola, o nessuno dei tre.

    Il 13/09 un margine di 0,31 e' stato letto ~60 confrontando due scale. Qui
    il margine lo calcola la `Ricevuta`, non chi legge, e la scala ha un nome.
    """
    esito = _cli("save", "Il totale della fattura e' 500 euro.",
                 "--topic", "prova/1b1",
                 "--source", "Il documento riporta un totale di 300 euro.",
                 "--json", "--local", store=store)
    reso = json.loads(esito.stdout)
    if reso["punteggio"] is None:
        #: ⚠️ NON UNO SKIP TRAVESTITO: qui si misura l'IMPLICAZIONE «se c'e' un
        #: punteggio allora c'e' la sua scala», e senza punteggio l'implicazione
        #: e' vera — ma allora devono essere vuoti TUTTI E TRE, perche' una
        #: scala senza numero e' un'etichetta su niente. La prima stesura
        #: pretendeva il punteggio e cadeva quando il giudice non era
        #: disponibile: misurava la macchina, non il contratto.
        assert reso["scala"] is None and reso["soglia"] is None
        assert reso["margine"] is None
        return
    assert reso["scala"], "punteggio senza scala"
    assert reso["modello"], "punteggio senza modello"
    assert reso["margine"] == pytest.approx(reso["punteggio"] - reso["soglia"])


def test_il_giornale_e_SPOSTATO_non_SOPPRESSO(store: Path):
    """La cura pigra sarebbe zittire tutto, e sarebbe peggio del difetto.

    Chi guarda solo stdout non distingue «il giornale e' andato su stderr» da
    «il giornale non c'e' piu'», e la seconda toglie a chi debugga l'unica
    traccia che ha. Questa cella pretende che le righe ci siano ANCORA, di la'.
    """
    esito = _cli("save", "Un fatto per il giornale.", "--topic", "prova/1b1",
                 "--json", "--local", store=store)
    json.loads(esito.stdout)                      # stdout pulito
    assert "flow.write" in esito.stderr, "il giornale e' sparito invece di spostarsi"


def test_i_campi_dello_store_non_sono_mai_vuoti(store: Path):
    esito = _cli("save", "Un fatto per i campi dello store.", "--topic",
                 "prova/1b1", "--json", "--local", store=store)
    reso = json.loads(esito.stdout)
    assert reso["store"], "store vuoto"
    assert reso["store_decided_by"], "store_decided_by vuoto"


def test_CONTROLLO_NEGATIVO_senza_json_la_pagina_umana_non_cambia(store: Path):
    """Senza `--json` lo stdout resta quello di oggi.

    Se anche il percorso umano diventasse muto, avrei spostato il giornale a
    TUTTI e non solo a chi chiede la macchina — e quello non e' l'invariante.
    Questa cella e' la meta' che impedisce alla cura di essere troppo larga.
    """
    esito = _cli("save", "Un fatto per il percorso umano.", "--topic",
                 "prova/1b1", "--local", store=store)
    assert esito.returncode == 0, esito.stderr[-800:]
    assert esito.stdout.strip(), "senza --json lo stdout e' diventato muto"
    with pytest.raises(json.JSONDecodeError):
        json.loads(esito.stdout)      # resta prosa, non diventa JSON


def test_remember_il_verbo_del_FATTO_rende_la_stessa_ricevuta(store: Path):
    """`remember` e' la porta di chi scrive un FATTO, e non aveva uscita macchina.

    `save` scrive un CHECKPOINT: passa come nota di sessione e per quella via
    lo schermo lessicale non gira — misurato, quattro frasi di auto-elogio
    ammesse tutte. Chi scrive fatti usa `remember`, quindi e' li' che una
    ricevuta leggibile serve davvero; e deve essere LA STESSA, dallo stesso
    adattatore, o sono due schemi sulla stessa porta.
    """
    esito = _cli("remember", "Il callback della CLI gira prima del primo log.",
                 "--topic", "prova/1b1", "--json", store=store)
    reso = json.loads(esito.stdout)
    mancanti = sorted(set(CHIAVI) - set(reso))
    assert not mancanti, f"remember non rende: {mancanti}"
    assert reso["store"] and reso["store_decided_by"]
