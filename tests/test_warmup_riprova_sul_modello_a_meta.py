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

🔴 **CIO' CHE QUESTO BANCO NON COPRE, e va letto prima di crederlo chiuso: il
COMANDO `verimem warmup` mente ancora.** Misurato alla porta dopo questa cura,
sulla stessa cartella a meta'::

    $ verimem warmup
    ✓ moat gate model already installed        EXIT=0

perche' `cli.py:421` corto-circuita su `local_ce_available()` — che sui soli
metadati risponde True **per progetto**, ed e' giusto cosi': e' quel True a far
partire il tentativo di caricamento, ed e' il tentativo a produrre la
dichiarazione onesta «the grounding judge failed to load» sulla ricevuta.
⇒ La cura di quella riga vive in `cli.py`, che il 17/08 e' la superficie di
un'altra istanza, e le e' stata segnalata con la riga esatta e il criterio
pronto (`holds_the_weights`). **Qui e' curata la funzione, non il comando**, ed
e' una distinzione che questo file dichiara invece di lasciar credere il
contrario: misurare `ensure_gate_model` e concludere che `warmup` sia a posto e'
esattamente l'errore che il resto del banco esiste per impedire.

📌 Limite, misurato e dichiarato: il criterio e' «i file ci sono». Un
`model.safetensors` dal contenuto corrotto passa ancora — quello richiede una
corruzione esterna, mentre la cartella vuota e quella a meta' sono stati che il
prodotto produce da se' (la destinazione nasce prima del download, l'estrazione
mette i metadati prima dei pesi).
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
