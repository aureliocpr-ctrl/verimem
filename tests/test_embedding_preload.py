"""Tests for non-blocking embedding warm-up (verimem.preload) and the
thread-safety of verimem.embedding._model().

Root cause these guard: the sentence-transformers model takes ~20s to load.
A synchronous eager preload blocks the MCP attach handshake; a lazy load
blocks the first user call. The fix warms in a background daemon thread.
"""
from __future__ import annotations

import threading
import time

import pytest

from verimem import embedding, encode_service, preload

# Captured at import time — before conftest's autouse `embedding._model` stub
# applies — so one test can exercise the REAL _model() double-checked lock.
_REAL_MODEL = embedding._model


@pytest.fixture(autouse=True)
def _clean_preload_env(monkeypatch):
    monkeypatch.delenv("HIPPO_EAGER_PRELOAD", raising=False)
    monkeypatch.delenv("HIPPO_PRELOAD_BACKGROUND", raising=False)
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    # Default: no usable shared daemon, zero wait → preload falls through to
    # the local _warm path. Tests that exercise the daemon path override these.
    # NB: preload is now MODEL-AWARE — it gates on daemon_usable() (reachable AND
    # serving CONFIG.embedding_model), not the model-blind is_reachable().
    monkeypatch.setattr(encode_service, "ensure_running", lambda: False)
    monkeypatch.setattr(encode_service, "is_reachable", lambda *a, **k: False)
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: False)
    monkeypatch.setattr(preload, "_DAEMON_WARM_WAIT_S", 0.0)
    yield


def test_background_preload_returns_immediately(monkeypatch):
    """Il chiamante NON aspetta il warm del modello — misurato sul FATTO,
    non su un cronometro.

    ⚠️ PERCHE' NON C'E' PIU' UNA SOGLIA, e la storia serve a non rimettercela.

    Qui c'era ``assert elapsed < 0.3``. Dal 06/09 ``preload_embedding()``
    chiama ``_scalda_le_librerie_del_giudice()`` in modo SINCRONO prima di
    avviare i thread — e' la cura di T1b, voluta e misurata (col warm su un
    thread di sfondo il banco end-to-end dava 0 giri su 3, col pre-import
    sincrono 3 su 3). Quel pre-import sfora 0,3 s, quindi la cella era ROSSA:
    misurata l'08/09 sul candidato 0ffd5ef7 PULITO, ``blocked for 0.62s``.

    🔴 E in CI passava lo stesso, perche' la suite intera aveva gia' importato
    ``scipy`` e li' l'import costa zero. **Un verde prestato dall'ordine dei
    test**: la cella non presidiava piu' niente e non lo diceva.

    IL COSTO, misurato l'08/09 su questa macchina, e' proprio cio' che rende
    la soglia il righello sbagliato::

        _scalda_le_librerie_del_giudice, processo nuovo   1.55 s
        _scalda_le_librerie_del_giudice, gia' importato   0.00 s
        dentro pytest, cella isolata                      0.55-0.62 s

    Tre valori per la stessa chiamata: dipende da cosa c'e' gia' in
    ``sys.modules``, che e' esattamente cio' che un test non controlla.

    ⇒ Si misura la PROPRIETA' VERA, che e' booleana e non ha soglie: quando
    ``preload_embedding()`` ritorna, **il warm non e' ancora avvenuto**. Il
    gemello ``test_sync_preload_blocks_until_loaded`` mostra l'altro verso
    (col preload sincrono ``calls == ["warmup"]`` gia' al ritorno), quindi la
    coppia distingue davvero i due comportamenti.

    📌 La soglia del gemello (``elapsed >= 0.45``) resta e va bene: «almeno»
    e' sicuro perche' un'attesa puo' solo crescere. E' «al piu'» che cade
    appena l'ambiente cambia.
    """
    calls: list[str] = []

    def slow_encode(text):
        time.sleep(1.0)
        calls.append(text)

    monkeypatch.setattr(embedding, "encode", slow_encode)

    t0 = time.time()
    thread = preload.preload_embedding()
    elapsed = time.time() - t0

    assert calls == [], (
        f"il chiamante ha aspettato il warm del modello: al ritorno di "
        f"preload_embedding() il warm era gia' finito ({calls!r}, "
        f"{elapsed:.2f}s). Il warm deve girare su un thread di sfondo — con "
        f"il modello vero sono ~20 s sull'handshake di attach."
    )
    assert thread is not None
    thread.join(timeout=3)
    assert calls == ["warmup"], "background warm-up must actually run"


def test_sync_preload_blocks_until_loaded(monkeypatch):
    calls: list[str] = []

    def slow_encode(text):
        time.sleep(0.5)
        calls.append(text)

    monkeypatch.setattr(embedding, "encode", slow_encode)
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "0")

    t0 = time.time()
    thread = preload.preload_embedding()
    elapsed = time.time() - t0

    assert thread is None
    assert elapsed >= 0.45, "sync preload should block until warm-up done"
    assert calls == ["warmup"]


def test_disabled_preload_skips(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(embedding, "encode", lambda t: calls.append(t))
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "0")

    thread = preload.preload_embedding()

    assert thread is None
    assert calls == []


def test_preload_uses_daemon_and_skips_local_warm(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(embedding, "encode", lambda t: calls.append(t))
    # Override the fixture default: a USABLE daemon (reachable AND serving
    # CONFIG's model) IS present. Model-aware gate, not bare reachability.
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: True)
    thread = preload.preload_embedding()
    assert thread is not None
    thread.join(timeout=3)
    assert calls == []  # usable daemon → no local model load (RAM saved)


def test_preload_warms_local_when_service_disabled(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(embedding, "encode", lambda t: calls.append(t))
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")  # ignore the shared daemon
    thread = preload.preload_embedding()
    assert thread is not None
    thread.join(timeout=3)
    assert calls == ["warmup"]  # service disabled → warm own model


def test_model_loads_once_under_concurrency(monkeypatch):
    """Concurrent first-callers of _model() must load the model ONCE.

    Patches the module's own _load_model() (reliable — sentence_transformers
    uses lazy imports that defeat patching SentenceTransformer directly).
    """
    # conftest autouse-stubs embedding._model; restore the REAL one here.
    monkeypatch.setattr(embedding, "_model", _REAL_MODEL)
    embedding._reset_model_for_tests()
    counter = {"n": 0}

    class FakeModel:
        pass

    def fake_load():
        counter["n"] += 1
        time.sleep(0.3)  # widen the race window
        return FakeModel()

    monkeypatch.setattr(embedding, "_load_model", fake_load)

    results = []

    def call():
        results.append(embedding._model())

    threads = [threading.Thread(target=call) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter["n"] == 1, f"_load_model called {counter['n']}x (must be 1)"
    assert len(results) == 6 and all(r is results[0] for r in results)
    embedding._reset_model_for_tests()
