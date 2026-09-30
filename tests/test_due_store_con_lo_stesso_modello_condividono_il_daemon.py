"""Due store con lo stesso modello, sulla stessa macchina, usano lo stesso daemon.

Il daemon codifica e giudice testo con il suo modello: la cartella dati di chi lo
chiama non entra nel suo lavoro. Con la chiave per cartella dati (la prima stesura
della scoperta per configurazione, 28/09) ogni store avviava il suo daemon da ~6 GB
impegnati, e N store sulla stessa macchina rompevano il tetto per macchina della
riga 7. MISURATO nel job di accettazione del 29/09 (#168, job 109551779207): la
fixture `utente(tmp_path)` da' una cartella dati nuova a ogni test, e la cella di
riga 3 non trovava piu' il daemon caldo delle celle prima.

La decisione (lead, 29/09 20:5x): la chiave e' (modello, dimensione), nella home.
L'incidente del 28/09 resta curato perche' modelli diversi hanno chiavi diverse.

NESSUN MODELLO, nessun processo: si leggono i percorsi.
"""
from __future__ import annotations

from verimem import encode_service as svc
from verimem.config import CONFIG


def _percorsi_con(**campi):
    originali = {k: getattr(CONFIG, k) for k in campi}
    try:
        for chiave, valore in campi.items():
            object.__setattr__(CONFIG, chiave, valore)
        return svc.percorsi_della_configurazione()
    finally:
        for chiave, valore in originali.items():
            object.__setattr__(CONFIG, chiave, valore)


def test_due_cartelle_dati_con_lo_stesso_modello_trovano_lo_stesso_daemon(tmp_path):
    """RED con la chiave per cartella dati: due store = due daemon."""
    primo = _percorsi_con(data_dir=tmp_path / "store-a")
    secondo = _percorsi_con(data_dir=tmp_path / "store-b")

    assert primo == secondo, f"due store, due daemon: {primo[0]} e {secondo[0]}"


def test_un_altro_modello_ha_un_altro_daemon(tmp_path):
    """GUARDIA dell'incidente del 28/09: il modello dei test non trova quello di
    produzione, e quindi non lo puo' sfrattare."""
    produzione = _percorsi_con(embedding_model="intfloat/multilingual-e5-base",
                               embedding_dim=768)
    test = _percorsi_con(
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        embedding_dim=384)

    assert produzione[0] != test[0] and produzione[1] != test[1] and produzione[2] != test[2]
