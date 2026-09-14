"""T-MAP-9 — quando il delegato NON C'E', nessuno chiede un daemon nuovo.

⚠️ COSA E' SUCCESSO DAVVERO, il 09/09 sera, sulla macchina di Aurelio. Il
servizio di encoding e' morto ed e' rinato alle 23:02:29 con un modello diverso
da quello dello store (``paraphrase-multilingual-MiniLM-L12-v2`` a 384 contro
``intfloat/multilingual-e5-base`` a 768, e 18.107 fatti sani a 768). Il client
lo rifiuta — giustamente, ``daemon_usable`` e' model-aware — e in delegate-only
non c'e' ripiego locale: ogni scrittura degrada. **Per 64 minuti**, e nel
frattempo 14 fatti sono entrati con l'embedding DIFFERITO senza che nessuno lo
sapesse.

🎯 L'ASIMMETRIA, che e' la causa radice, in ``_encode_prepared_within_budget``::

    if t.is_alive():                     # RAMO 1 — l'encoding e' TROPPO LENTO
        _LOG.warning("… kicking the encode daemon awake")
        _es.ensure_running()             # <<< SVEGLIA IL DAEMON
        return None

    if "err" in box:                     # RAMO 2 — l'encoding NON E' DISPONIBILE
        if isinstance(box["err"], embedding.EncodeDelegateUnavailable):
            return None                  # <<< e basta. Nessuno sveglia niente.
        raise box["err"]

Il ramo «lento» chiede un daemon nuovo, il ramo «assente» no — e lo stato
degradato **si autoconserva**: ogni scrittura fallisce allo stesso modo e
nessuna chiede il daemon giusto, finche' non nasce un processo nuovo per altri
motivi. Anche il docstring promette il kick solo per l'overrun.

📌 E il resto del meccanismo E' SANO, verificato prima di accusarlo: il lock del
singleton NON blocca il sostituto (``_owner_is_zombie`` usa ``daemon_usable``,
model-aware, e il lock risultava rubabile — 3844 s contro 600 di grazia). Non
c'e' nessun deadlock: manca solo che qualcuno CHIEDA il daemon.

📏 Livello: la funzione condivisa da save e recall, con un ORACOLO al posto
dell'encoder — misura CHI VIENE CHIAMATO, non quanto e' bravo il modello. Zero
RAM, gira in CI senza cross-encoder.

🧪 IL CONTROLLO POSITIVO E' IL RAMO GEMELLO: stesso banco, stessa funzione, ma
con un encode LENTO — li' ``ensure_running`` DEVE essere chiamato. Verde li' e
rosso qui dice che il difetto e' **del ramo**, non della spia: se fossero rossi
tutti e due, la mia spia sarebbe scollegata e il rosso non direbbe niente.
"""
from __future__ import annotations

import time

import pytest

from verimem import embedding, semantic


@pytest.fixture
def spia_del_daemon(monkeypatch):
    """Registra ogni richiesta di svegliare il daemon, senza svegliarne nessuno."""
    from verimem import encode_service
    chiamate: list[float] = []
    monkeypatch.setattr(
        encode_service, "ensure_running", lambda *a, **kw: chiamate.append(time.time())
    )
    return chiamate


def test_col_delegato_ASSENTE_nessuno_chiede_un_daemon_nuovo(
    monkeypatch, spia_del_daemon
):
    """RED atteso. E' lo stato reale del 09/09: il delegato non c'e' (o ha il
    modello sbagliato), la scrittura degrada — e nessuno prova a rimediare."""
    def _assente(*a, **kw):
        raise embedding.EncodeDelegateUnavailable(
            "encode daemon unavailable and in-process cold-load is disabled "
            "(HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade"
        )

    monkeypatch.setattr(embedding, "encode", _assente)

    esito = semantic._encode_prepared_within_budget("un fatto qualsiasi", 5.0)

    assert esito is None, (
        "il ramo non ha degradato: questo banco misura l'altra meta' del "
        f"comportamento e il suo rosso non direbbe niente (esito={esito!r})"
    )
    assert spia_del_daemon, (
        "NESSUNO HA CHIESTO UN DAEMON NUOVO. La scrittura degrada in silenzio e "
        "lo stato si autoconserva: la prossima scrittura fallira' identica. Il "
        "ramo gemello, otto righe piu' su, chiama ensure_running() — questo no."
    )


def test_controllo_positivo_col_TIMEOUT_il_daemon_viene_svegliato(
    monkeypatch, spia_del_daemon
):
    """VERDE atteso, ed e' cio' che rende leggibile il rosso qui sopra: la spia
    e' attaccata e il meccanismo funziona — sull'altro ramo."""
    def _lentissimo(*a, **kw):
        time.sleep(1.5)
        return [0.0]

    monkeypatch.setattr(embedding, "encode", _lentissimo)

    esito = semantic._encode_prepared_within_budget("un fatto qualsiasi", 0.2)

    assert esito is None, "col budget sforato l'esito deve essere il differimento"
    assert spia_del_daemon, (
        "nemmeno il ramo del timeout sveglia il daemon: allora la spia e' "
        "scollegata e il rosso dell'altra cella non prova niente"
    )
