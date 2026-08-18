"""Il comando che procura il giudice si dichiarava soddisfatto con mezzo modello.

`ensure_gate_model` decideva con `config.json` in entrambi i punti che contano:
quello che decide di NON riscaricare, e quello che dichiara l'esito. Ma
`config.json` pesa 1 KB e i pesi 737 MB, quindi un'estrazione interrotta lascia
esattamente il primo senza i secondi — e in quello stato, misurato il 17/08::

    $ verimem warmup
    ✓ moat gate model already installed
    Warmup complete — Verimem recall will be instant.
    EXIT=0
    (la cartella dopo contiene ancora il solo config.json)

⇒ Il comando che esiste apposta per procurare il giudice si dichiarava
soddisfatto e non riprovava piu'. Da quello stato non si usciva se non
cancellando la cartella a mano — e nel frattempo il moat non gira: un write
reale torna `judged=False`, `grounding_score=None`, e un claim smentito dalla
propria fonte viene ammesso con l'avviso «the grounding judge failed to load».

⚠️ La popolazione opposta qui non e' un ornamento ma il vincolo piu' stretto:
un criterio piu' severo che riscaricasse 737 MB a ogni `warmup` sarebbe un
difetto peggiore di quello curato. Il test sul modello completo esiste per
vietarlo.

⚠️ **QUESTO BANCO COPRE LA FUNZIONE, NON IL COMANDO** — e la distinzione non e'
pedanteria, e' il difetto che e' costato un giorno. Curata `ensure_gate_model`
il 17/08, `verimem warmup` continuava a rispondere «✓ moat gate model already
installed» con `EXIT=0` sulla stessa cartella a meta', perche' `cli.py`
corto-circuitava su `local_ce_available()` e non arrivava mai qui. Misurare la
funzione e concludere che il comando fosse a posto e' esattamente l'errore che
il resto del banco esiste per impedire — ed e' stato commesso, e scoperto solo
eseguendo il comando.

✅ Il comando e' stato curato il 18/08 (`7ee7e2c6`): decide anche lui con
`holds_the_weights`. Il suo presidio sta in
`test_warmup_non_dice_installato_su_mezzo_modello.py`, che verifica la GIUNTURA
— cioe' che `cli.py` chiami davvero quella funzione — perche' i test sul solo
criterio erano gia' verdi prima della cura e non avrebbero visto niente.

📌 Limite, e ora con la RAGIONE misurata invece che stimata. Il criterio e' «i
file ci sono»: un `model.safetensors` dal contenuto troncato passa ancora. Il
18/08 e' stato chiesto al codice quanto quel caso sia raggiungibile, e la
risposta e' in `_download_and_extract_tar`: il file viene scaricato in un
temporaneo, **lo sha256 viene verificato, e solo se torna si estrae**. Un
download interrotto non arriva quindi mai all'estrazione — viene rifiutato
prima. Per ottenere un file dei pesi troncato serve un'interruzione DURANTE
l'estrazione, cioe' una finestra di pochi secondi su un'operazione locale.

⇒ Gli altri due casi non chiedono nessuna interruzione precisa, capitano per
ORDINE NATURALE: la destinazione nasce prima del download (cartella vuota) e
`config.json` esce dall'archivio prima dei pesi (metadati soli). **E' questa
differenza — non una stima di probabilita' — la ragione per cui il confine sta
qui.** Chi misurasse un file dei pesi troncato in natura ha il diritto di
riaprirlo: il criterio naturale sarebbe l'header di `safetensors`, che dichiara
la propria lunghezza e si legge senza caricare il modello.
"""
from __future__ import annotations

import pytest

from verimem import local_grounding as lg


def _chiama(dest, monkeypatch):
    """`ensure_gate_model` con un download finto: restituisce quante volte
    avrebbe scaricato, l'esito e il messaggio."""
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(dest))
    chiamate: list[tuple] = []
    ok, messaggio = lg.ensure_gate_model(
        download=lambda sorgente, d: chiamate.append((sorgente, d)))
    return len(chiamate), ok, messaggio


@pytest.fixture
def meta_senza_pesi(tmp_path):
    """Un'estrazione interrotta: i metadati ci sono, i pesi no."""
    d = tmp_path / "local_gate_ce_v2"
    d.mkdir()
    (d / "config.json").write_text('{"model_type": "xlm-roberta"}',
                                   encoding="utf-8")
    return d


@pytest.fixture
def modello_completo(tmp_path):
    d = tmp_path / "local_gate_ce_v2"
    d.mkdir()
    (d / "config.json").write_text('{"model_type": "xlm-roberta"}',
                                   encoding="utf-8")
    (d / "model.safetensors").write_bytes(b"\x00")
    return d


def test_sul_modello_a_meta_il_download_viene_RITENTATO(meta_senza_pesi,
                                                        monkeypatch):
    """Il caso: prima qui `warmup` diceva «already installed» e usciva 0."""
    quante, ok, messaggio = _chiama(meta_senza_pesi, monkeypatch)
    assert quante == 1, (
        "sulla cartella con i soli metadati il download NON e' stato "
        "ritentato: e' lo stato da cui non si esce se non a mano")
    assert ok is False, messaggio


def test_il_messaggio_dice_QUALE_pezzo_manca(meta_senza_pesi, monkeypatch):
    """L'operatore deve sapere se ha scaricato mezzo modello o niente: sono due
    diagnosi diverse, e prima il referto diceva sempre «no config.json»."""
    _, _, messaggio = _chiama(meta_senza_pesi, monkeypatch)
    assert "weights" in messaggio, messaggio
    assert "config.json" not in messaggio, (
        f"dice che manca config.json, che invece c'e': {messaggio}")


def test_su_un_modello_COMPLETO_non_si_riscarica_niente(modello_completo,
                                                        monkeypatch):
    """⚠️⚠️ IL VINCOLO PIU' STRETTO, e la ragione per cui questo test vale piu'
    degli altri due: il modo piu' facile di far passare i test sopra e' un
    criterio che non e' mai soddisfatto — e allora ogni `warmup` riscarica
    737 MB. Sarebbe un difetto peggiore di quello curato."""
    quante, ok, messaggio = _chiama(modello_completo, monkeypatch)
    assert quante == 0, (
        f"il modello c'e' ed e' stato riscaricato lo stesso: {messaggio}")
    assert ok is True, messaggio


def test_sulla_cartella_vuota_il_referto_nomina_entrambi(tmp_path,
                                                         monkeypatch):
    """L'altro estremo: quando non c'e' niente il messaggio deve dirlo per
    intero, non fermarsi al primo pezzo mancante."""
    vuota = tmp_path / "local_gate_ce_v2"
    vuota.mkdir()
    quante, ok, messaggio = _chiama(vuota, monkeypatch)
    assert quante == 1 and ok is False, messaggio
    assert "config.json" in messaggio and "weights" in messaggio, messaggio
