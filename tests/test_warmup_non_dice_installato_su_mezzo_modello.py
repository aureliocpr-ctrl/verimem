"""`verimem warmup` si dichiarava soddisfatto con mezzo modello sul disco.

Il comando che esiste apposta per procurare il giudice decideva con
`local_ce_available()`, che risponde True sui soli metadati — ed è voluto: è
quel True a far partire il tentativo di caricamento, ed è il tentativo a
produrre la dichiarazione onesta «the grounding judge failed to load» sulla
ricevuta di un write. Ma `warmup` non deve decidere se GIUDICARE: deve decidere
se SCARICARE. Misurato il 17/08 su una cartella con il solo `config.json` —
ciò che un'estrazione interrotta lascia, visto che i metadati pesano 1 KB e i
pesi 737 MB::

    $ verimem warmup
    ✓ moat gate model already installed
    EXIT=0                       (e la cartella resta com'era)

⇒ Da quello stato non si usciva se non cancellando la cartella a mano, e nel
frattempo il moat non gira: un write reale torna `judged=False`,
`grounding_score=None`, e un claim smentito dalla propria fonte viene ammesso.

⚠️ La cura della FUNZIONE (`ensure_gate_model`, commit 7b72a9ea) non bastava, ed
è la ragione per cui questo file esiste separato: il comando corto-circuitava
PRIMA di chiamarla. Misurare la funzione e concludere che il comando fosse a
posto è l'errore che questo banco impedisce — commesso, e scoperto solo
eseguendo il comando.

📌 Il verdetto di `warmup` resta 0 anche quando il download fallisce: è
«best-effort, failure reports honestly, never crashes», dichiarato nel codice, e
il fallimento VIENE riportato. Non è ciò che questo file presidia.
"""
from __future__ import annotations

import pytest

from verimem import local_grounding as lg


def _scarica_finto(chiamate):
    def download(sorgente, dest):
        chiamate.append((sorgente, dest))
    return download


@pytest.fixture
def metadati_senza_pesi(tmp_path, monkeypatch):
    """Un'estrazione interrotta: `config.json` c'è, i pesi no."""
    d = tmp_path / "local_gate_ce_v2"
    d.mkdir()
    (d / "config.json").write_text('{"model_type": "xlm-roberta"}',
                                   encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(d))
    return d


@pytest.fixture
def modello_completo(tmp_path, monkeypatch):
    d = tmp_path / "local_gate_ce_v2"
    d.mkdir()
    (d / "config.json").write_text('{"model_type": "xlm-roberta"}',
                                   encoding="utf-8")
    (d / "model.safetensors").write_bytes(b"\x00")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(d))
    return d


def test_il_comando_NON_si_dichiara_soddisfatto_con_i_soli_metadati(
        metadati_senza_pesi):
    """Il criterio che `warmup` usa per decidere se scaricare.

    Si prova la condizione che il comando valuta, non il testo che stampa: il
    testo è già presidiato altrove e cambia, il criterio no.
    """
    assert lg.holds_the_weights(metadati_senza_pesi) is False, (
        "con i soli metadati il comando crede di avere il modello e non "
        "riscarica: è lo stato da cui non si esce se non a mano")
    assert lg.local_ce_available() is True, (
        "⚠️ SE QUESTO DIVENTA False la trappola non esiste più e il file "
        "misura un caso che non capita: rileggere, non cancellare. "
        "`local_ce_available` DEVE restare ottimista sui metadati — è quel "
        "True a far partire il tentativo che dichiara «failed to load»")


def test_su_un_modello_completo_il_comando_non_riscarica(modello_completo):
    """⚠️⚠️ IL VINCOLO PIÙ STRETTO: il modo più facile di far passare il test
    sopra è un criterio mai soddisfatto — e allora ogni `warmup` riscarica
    737 MB, difetto peggiore di quello curato."""
    assert lg.holds_the_weights(modello_completo) is True


def test_il_comando_usa_i_PESI_e_non_la_disponibilita(metadati_senza_pesi):
    """⚠️ IL PRESIDIO CHE DECIDE, e vale più degli altri due: quelli provano
    `holds_the_weights`, che era già verde prima della cura. Questo prova che
    `cli.py` la USA — cioè la giuntura, che è dove stava il difetto.

    Si legge il sorgente del comando perché è l'unico modo di distinguere «la
    funzione giusta esiste» da «il comando la chiama»: eseguire `warmup` per
    davvero costa un download.
    """
    import inspect

    from verimem import cli

    sorgente = inspect.getsource(cli.warmup)
    assert "holds_the_weights" in sorgente, (
        "`warmup` non chiama `holds_the_weights`: se decide con "
        "`local_ce_available()` torna a dirsi soddisfatto con mezzo modello")
    assert "elif local_ce_available()" not in sorgente, (
        "`warmup` decide ancora con la disponibilità invece che con i pesi")
