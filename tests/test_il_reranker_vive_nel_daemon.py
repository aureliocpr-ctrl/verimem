"""Il cross-encoder si carica UNA volta, nel daemon, non in ogni processo.

Misurato il 2026-07-31 su un processo fresco, dodici recall della stessa query
distanziate di sei secondi::

     #  attesa   durata  ranking
     1      0s    3.10s  {'rerank': 'timeout_cold', 'fusion': 'timeout'}
     2      6s    0.44s  {'rerank': 'skipped_busy',  'fusion': 'applied'}
     6      6s    0.47s  {'rerank': 'skipped_busy',  'fusion': 'applied'}
     7      6s    2.87s  {'rerank': 'applied',       'fusion': 'applied'}
    12      6s    2.81s  {'rerank': 'applied',       'fusion': 'applied'}

Il reranker entra in gioco alla SETTIMA chiamata, dopo circa trentasei secondi
di vita del processo. Non e' rotto il lease — il lease si libera e il CE arriva
a servire. E' il REGIME: sull'audit log di produzione **256 processi su 293**
chiamano ``hippo_facts_recall`` una volta sola e muoiono, perche' il client va
in timeout e respawna. Per tutti loro il modello si mette a caricare e poi il
processo muore: **trentatre secondi di lavoro buttati, ogni volta**, e il
«R@1 lever» del README non si applica praticamente mai.

Nessun warm in-process puo' aggiustarlo — scaldare al boot vuol dire pagare
~450 MB per processo (l'incidente RAM del 2026-07-10) per un processo che muore
prima di finire il caricamento.

L'embedder questo problema l'ha gia' risolto: un daemon condiviso lo carica una
volta e tutti i processi effimeri lo usano caldo. Il reranker no — il commento
in preload.py lo dice testualmente: «The reranker is NOT delegated to the encode
daemon (it runs in the recall process) and its cold load is ~33s».

Qui si chiude quella asimmetria. Il guadagno non e' far rispondere la prima
chiamata (quella paga comunque): e' che il lavoro di caricamento **non muore
col processo**. Il client va in timeout a 0.25s e degrada come prima, ma il
daemon continua a caricare, e il server MCP successivo — un altro processo —
trova il modello gia' caldo.

``rerank_candidates`` non cambia di una riga: prende uno ``scorer`` iniettato
(``pairs -> [float]``) e non deve sapere se e' locale o remoto.
"""
from __future__ import annotations

import threading
import time

import pytest

from verimem import encode_service as svc
from verimem import semantic


def _punteggio_finto(pairs):
    """Deterministico e riconoscibile: la lunghezza del passage. Serve a
    distinguere «ha risposto il daemon» da «ha risposto un modello locale»."""
    return [float(len(p[1])) for p in pairs]


@pytest.fixture()
def daemon(tmp_path, monkeypatch):
    disc = tmp_path / "encode_service.json"
    s = svc.EncodeServer(
        encode_fn=lambda t: [0.1, 0.2, 0.3],
        rerank_fn=_punteggio_finto,
        host="127.0.0.1", port=0, discovery_path=disc,
        model_name="test-model", model_dim=3,
    )
    th = threading.Thread(target=s.serve_forever, daemon=True)
    th.start()
    for _ in range(200):
        if disc.exists() and svc.read_discovery(disc):
            break
        time.sleep(0.02)
    monkeypatch.setattr(svc, "DISCOVERY_PATH", disc)
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    yield s, disc
    s.stop()


def test_il_daemon_sa_rerankare(daemon):
    """Il protocollo porta le coppie e riporta i punteggi."""
    _, disc = daemon
    punteggi = semantic._rerank_via_daemon(
        [("q", "corto"), ("q", "un passage piu' lungo")], info=svc.read_discovery(disc))
    assert punteggi == [5.0, 21.0], punteggi


def test_lo_scorer_arriva_dal_daemon_senza_caricare_NULLA_qui(daemon,
                                                              monkeypatch):
    """Il punto di tutto: un processo che non ha il modello ottiene comunque i
    punteggi. Se `_load_reranker` provasse a costruire un CrossEncoder qui, il
    monkeypatch sotto lo farebbe esplodere."""
    def _vietato(*a, **k):
        raise AssertionError("ha caricato il cross-encoder in-process")

    monkeypatch.setattr(semantic, "_RERANKER", None)
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers",
                        type("M", (), {"CrossEncoder": _vietato}))
    scorer = semantic._load_reranker()
    assert scorer([("q", "abc")]) == [3.0]


def test_senza_daemon_si_carica_in_processo_come_prima(monkeypatch, tmp_path):
    """La delega e' un'ottimizzazione, mai una dipendenza: spento il servizio,
    il comportamento torna quello di sempre."""
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    assert semantic._rerank_via_daemon([("q", "x")]) is None


def test_un_daemon_VECCHIO_non_rompe_niente(tmp_path, monkeypatch):
    """Un daemon che non sa rerankare (versione precedente) risponde errore, e
    il chiamante deve degradare al locale invece di propagare."""
    disc = tmp_path / "encode_service.json"
    s = svc.EncodeServer(encode_fn=lambda t: [0.1], rerank_fn=None,
                         host="127.0.0.1", port=0, discovery_path=disc,
                         model_name="test-model", model_dim=1)
    th = threading.Thread(target=s.serve_forever, daemon=True)
    th.start()
    for _ in range(200):
        if disc.exists() and svc.read_discovery(disc):
            break
        time.sleep(0.02)
    try:
        monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
        assert semantic._rerank_via_daemon(
            [("q", "x")], info=svc.read_discovery(disc)) is None
    finally:
        s.stop()


def test_la_prontezza_conta_anche_il_daemon(daemon, monkeypatch):
    """Il pezzo che mancava, e che si e' visto solo misurando.

    Col CE spostato nel daemon, ``_RERANKER`` resta None per sempre in questo
    processo. Se la prontezza guardasse solo quello, OGNI query si darebbe il
    budget del cold-load (0.25s), un predict remoto (~2.8s) non ci starebbe
    mai, e il rerank non si applicherebbe — con un daemon caldo dall'altra
    parte. Misurato: dodici recall tutte `timeout_cold`.
    """
    monkeypatch.setattr(semantic, "_RERANKER", None)
    monkeypatch.setitem(semantic._RERANK_DELEGATO, "ok", False)
    assert semantic._reranker_ready() is False

    semantic._rerank_via_daemon([("q", "x")])
    assert semantic._reranker_ready() is True, (
        "il daemon ha rerankato ma il processo si considera ancora a freddo: "
        "la prossima query si darebbe il budget del cold-load")


def test_la_probe_di_boot_non_carica_nessun_modello(daemon, monkeypatch):
    """La probe serve a far trovare alla PRIMA query il budget giusto — 256
    processi su 293 ne fanno una sola. Deve costare millisecondi e zero RAM:
    se caricasse il CE sarebbe il warm in-process che l'incidente RAM del
    2026-07-10 ha tolto (~450 MB per processo)."""
    from verimem import preload

    def _vietato(*a, **k):
        raise AssertionError("la probe ha caricato il cross-encoder")

    # Opt-in esplicito: il conftest pinna ENGRAM_RECALL_RERANK=0 per tutta la
    # suite (una recall non deve tentare il load del CE vero), e i test del
    # rerank lo riaccendono dentro il test. Senza, la probe esce subito — ed e'
    # giusto cosi': non si scalda cio' che l'operatore ha spento.
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setattr(semantic, "_load_reranker", _vietato)
    monkeypatch.setitem(semantic._RERANK_DELEGATO, "ok", False)
    preload._segnala_rerank_delegato()
    assert semantic._RERANK_DELEGATO["ok"] is True


def test_col_rerank_SPENTO_la_probe_non_disturba_il_daemon(daemon, monkeypatch):
    """Il rovescio: se l'operatore ha spento il rerank, non si interroga
    nessuno. Una probe che gira comunque sarebbe lavoro per una funzione che
    non verra' usata."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setitem(semantic._RERANK_DELEGATO, "ok", False)
    from verimem import preload
    preload._segnala_rerank_delegato()
    assert semantic._RERANK_DELEGATO["ok"] is False


def test_il_token_serve_anche_per_il_rerank(daemon):
    """Stessa superficie di sicurezza dell'encode: senza token per-boot il
    daemon non lavora per nessuno."""
    import socket as _socket
    info = svc.read_discovery(daemon[1])
    conn = _socket.create_connection((info["host"], info["port"]), timeout=2)
    try:
        svc.send_msg(conn, {"rerank_pairs": [["q", "x"]]})  # senza token
        resp = svc.recv_msg(conn)
    finally:
        conn.close()
    assert resp and resp.get("ok") is False, resp
    assert "unauthorized" in str(resp.get("error", "")).lower(), resp
