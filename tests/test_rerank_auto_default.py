"""Il cross-encoder di default e' AUTO: solo sulle query corte, dove vince.

LA STORIA COMPLETA, perche' il default e' stato ON per 46 giorni e la ragione
per cui cambia merita il contesto. Il flip a ON (10/06) aveva una misura vera:
sonde-parafrasi corte, R@1 0,533 -> 0,683, p=0,00052 (`bench_rerank_fair.py`,
n=120). Ma misurava SOLO il regime amico del CE. Sul traffico misto reale
(GT 304 query, 26/07) l'aggregato e' nullo — Delta MRR +0,0078, p=0,716 —
e la segmentazione mostra il perche': due effetti veri e OPPOSTI.

  1 fatto atteso / query corta :  +0,146 MRR  (47 meglio / 16 peggio)
  2+ fatti / query lunga       :  -0,080 MRR  (12 meglio / 38 peggio)

Stabile su split-half (+0,15/+0,14 e -0,08/-0,08 su meta' indipendenti), non e'
troncatura (mediana 16 parole vs finestra 512), e la politica condizionale
scelta su una meta' VINCE sull'altra in entrambe le direzioni (B->A: OFF 0,391,
ON 0,415, politica 0,493; A->B: OFF 0,385, ON 0,376, politica 0,446), con la
stessa soglia (<=9 parole) scelta indipendentemente dalle due meta', e un
plateau largo (10-16 parole battono entrambi i puri). Il sempre-ON, oltre a
costare +2067 ms su OGNI query, cambia segno tra le due meta': instabile.

Quindi: mode AUTO = CE solo se la query ha al piu' ENGRAM_RERANK_AUTO_MAX_WORDS
parole (default 10, dal plateau). Una query lunga in auto NON deve nemmeno
CARICARE il CE — stesso pattern del guard sui documenti lunghi ("skipped, not
even loaded"): saltare dopo il load pagherebbe 43,6 s per non usarlo.

La soglia viene da UN corpus (questo, n=304, un utente): e' dichiarato, e' il
motivo per cui e' un env e non una costante, e resta falsificabile da un
secondo corpus. ON e OFF espliciti restano forzabili come sempre.
"""
from __future__ import annotations

import threading
import time

import pytest

from verimem import semantic
from verimem.client import Memory

CORTA = "dove vive il daemon"                                   # 4 parole
LUNGA = ("spiegami in dettaglio tutto quello che sappiamo sul daemon di "
         "encode e sul suo ciclo di vita completo")             # 18 parole

FACTS = [
    "The Eiffel Tower is a wrought-iron lattice tower in Paris.",
    "Marie Curie won two Nobel Prizes for her work on radioactivity.",
    "The Amazon River discharges more water than any other river.",
]


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    semantic._rerank_breaker_reset()
    yield
    semantic._rerank_breaker_reset()


def test_the_mode_parses_unset_as_auto(monkeypatch):
    """Il cuore del cambio di default: assente = auto, non piu' = on."""
    monkeypatch.delenv("ENGRAM_RECALL_RERANK", raising=False)
    assert semantic._rerank_mode() == "auto"
    for v in ("auto", " AUTO "):
        monkeypatch.setenv("ENGRAM_RECALL_RERANK", v)
        assert semantic._rerank_mode() == "auto"
    for v in ("1", "on", "true", "yes"):
        monkeypatch.setenv("ENGRAM_RECALL_RERANK", v)
        assert semantic._rerank_mode() == "on", f"{v!r} deve forzare ON"
    for v in ("0", "off", "false", "no"):
        monkeypatch.setenv("ENGRAM_RECALL_RERANK", v)
        assert semantic._rerank_mode() == "off", f"{v!r} deve forzare OFF"


def test_enabled_still_means_not_off(monkeypatch):
    """cli.py e preload.py scaldano il CE se PUO' servire: in auto puo'."""
    monkeypatch.delenv("ENGRAM_RECALL_RERANK", raising=False)
    assert semantic._rerank_enabled() is True
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    assert semantic._rerank_enabled() is False


def test_the_threshold_reads_env_and_defaults_to_ten(monkeypatch):
    monkeypatch.delenv("ENGRAM_RERANK_AUTO_MAX_WORDS", raising=False)
    assert semantic._rerank_auto_max_words() == 10
    monkeypatch.setenv("ENGRAM_RERANK_AUTO_MAX_WORDS", "3")
    assert semantic._rerank_auto_max_words() == 3
    monkeypatch.setenv("ENGRAM_RERANK_AUTO_MAX_WORDS", "spazzatura")
    assert semantic._rerank_auto_max_words() == 10
    monkeypatch.setenv("ENGRAM_RERANK_AUTO_MAX_WORDS", "0")
    assert semantic._rerank_auto_max_words() == 1, "minimo 1, mai 0"


def _mem(tmp_path, monkeypatch, chiamate: dict):
    """Store vero + CE finto che REGISTRA se viene caricato/usato."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "auto")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", "5")
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BUDGET_S", "5")
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")     # isola il rerank
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "30")

    def loader():
        chiamate["load"] = chiamate.get("load", 0) + 1

        def score(pairs):
            chiamate["score"] = chiamate.get("score", 0) + len(pairs)
            return [0.5] * len(pairs)
        return score

    monkeypatch.setattr(semantic, "_load_reranker", loader)
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: True)
    mem = Memory(tmp_path / "m.db")
    for f in FACTS:
        mem.add(f, topic="auto", verified_by=["source-doc:t"])
    return mem


def _aspetta_worker():
    for t in [t for t in threading.enumerate() if t.name == "hippo-rerank"]:
        t.join(10)


def test_auto_reranks_a_short_query(tmp_path, monkeypatch):
    chiamate: dict = {}
    mem = _mem(tmp_path, monkeypatch, chiamate)
    mem.search(CORTA, k=3)
    _aspetta_worker()
    assert chiamate.get("load", 0) >= 1, (
        "query corta in auto: il CE doveva essere usato e non e' stato "
        "nemmeno caricato")


def test_auto_skips_a_long_query_without_loading(tmp_path, monkeypatch):
    """Il punto che paga: saltare DOPO il load costerebbe 43,6 s a vuoto."""
    chiamate: dict = {}
    mem = _mem(tmp_path, monkeypatch, chiamate)
    assert len(LUNGA.split()) > 10
    t0 = time.time()
    out = mem.search(LUNGA, k=3)
    trascorso = time.time() - t0
    _aspetta_worker()
    assert chiamate.get("load", 0) == 0, (
        "query lunga in auto: il CE e' stato CARICATO — il gate deve stare "
        "prima del load, non dopo")
    assert chiamate.get("score", 0) == 0
    assert out, "il salto del CE non deve svuotare il risultato"
    assert trascorso < 3.0, "la query lunga non deve aspettare nessun budget CE"


def test_the_threshold_is_the_boundary(tmp_path, monkeypatch):
    chiamate: dict = {}
    mem = _mem(tmp_path, monkeypatch, chiamate)
    monkeypatch.setenv("ENGRAM_RERANK_AUTO_MAX_WORDS", "3")
    mem.search("quattro parole sono troppe", k=3)   # 4 > 3 -> salta
    _aspetta_worker()
    assert chiamate.get("load", 0) == 0
    mem.search("tre parole bastano", k=3)           # 3 <= 3 -> rerank
    _aspetta_worker()
    assert chiamate.get("load", 0) >= 1


def test_forced_on_ignores_the_length_gate(tmp_path, monkeypatch):
    """Chi scrive ENGRAM_RECALL_RERANK=1 vuole il CE SEMPRE, come oggi."""
    chiamate: dict = {}
    mem = _mem(tmp_path, monkeypatch, chiamate)
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    mem.search(LUNGA, k=3)
    _aspetta_worker()
    assert chiamate.get("load", 0) >= 1, (
        "ON esplicito: la query lunga doveva essere rerankata comunque")


def test_the_regime_records_the_mode(monkeypatch):
    """I bench dichiarano il regime (lezione della varianza, 26/07): senza il
    mode, un numero misurato in auto sarebbe indistinguibile da uno in ON."""
    from benchmark.eval_retrieval_with_gt import read_path_regime
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "auto")
    r = read_path_regime()
    assert r["rerank_mode"] == "auto"
    assert r["rerank_auto_max_words"] == semantic._rerank_auto_max_words()
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    assert read_path_regime()["rerank_mode"] == "on"
