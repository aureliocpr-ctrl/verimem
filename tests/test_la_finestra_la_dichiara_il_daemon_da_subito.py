"""Il daemon dichiara la finestra dalla PRIMA scoperta, non dopo il primo giudizio.

MISURATO il 2026-09-28 su uno scrittore in delegate-only con un daemon appena
nato (sabbia, modelli veri): alla prima scrittura con fonte lo scrittore importa
transformers e torch (25 MB unici prima, 725 dopo, 1478 impegnati), e la pila
del primo import di torch porta a `local_grounding._tokenizzatore`, chiamato da
`try_local_score` perche' la scoperta non diceva `applies_window`. Il daemon lo
dichiara solo quando ha il tokenizzatore, e lo caricava alla prima richiesta
`gate_pairs`: fino ad allora ogni client che scrive riduce lo span da se'. Dopo
un riavvio lo pagano tutte le sessioni che scrivono presto, per tutta la loro vita.

NESSUN MODELLO: il giudice e' finto e il tokenizzatore e' un oggetto qualsiasi;
l'avvio del daemon si ferma dove comincerebbe a servire.
"""
from __future__ import annotations

from verimem import embedding, encode_service, local_grounding


def _avvio_senza_modelli(monkeypatch, giudice) -> list[bool]:
    """Esegue `encode_service.main()` fino al punto in cui il daemon si annuncia
    e restituisce cosa dichiarerebbe la sua prima scoperta."""
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: giudice)
    monkeypatch.setattr(local_grounding, "_judge", giudice)
    monkeypatch.setattr(embedding, "_encode_local", lambda testo: [0.0])
    monkeypatch.setattr(encode_service, "acquire_daemon_lock", lambda *a, **k: True)
    monkeypatch.setattr(encode_service, "release_daemon_lock", lambda *a, **k: None)
    dichiarato: list[bool] = []
    # `serve_forever` e' dove il daemon scrive la scoperta; `_write_discovery`
    # dichiara `applies_window` con `_puo_ridurre_lo_span()`.
    monkeypatch.setattr(encode_service.EncodeServer, "serve_forever",
                        lambda self: dichiarato.append(encode_service._puo_ridurre_lo_span()))
    encode_service.main()
    return dichiarato


def test_la_prima_scoperta_dichiara_la_finestra(monkeypatch):
    """LA CURA. RED sul tronco: quando il daemon si annuncia il tokenizzatore
    del giudice non c'e', e la sua prima scoperta dice «non riduco»."""
    class _Giudice:
        _tok = None

        def _tokenizzatore(self):
            self._tok = object()
            return self._tok

    assert _avvio_senza_modelli(monkeypatch, _Giudice()) == [True], (
        "il daemon si annuncia senza il tokenizzatore del giudice: ogni client "
        "che scrive prima del suo primo giudizio importa transformers e torch "
        "per ridurre lo span da se'")


def test_senza_il_modello_del_giudice_il_daemon_parte_lo_stesso(monkeypatch):
    """GUARDIA: tokenizzatore assente (modello non su disco), il daemon si
    annuncia come prima e dichiara «non riduco»."""
    class _Assente:
        _tok = None

        def _tokenizzatore(self):
            return None

    assert _avvio_senza_modelli(monkeypatch, _Assente()) == [False]


def test_un_tokenizzatore_che_esplode_non_ferma_il_daemon(monkeypatch):
    """GUARDIA: un errore nel caricare la finestra non deve costare il daemon."""
    class _Rotto:
        _tok = None

        def _tokenizzatore(self):
            raise OSError("tokenizer.json illeggibile")

    assert _avvio_senza_modelli(monkeypatch, _Rotto()) == [False]
