"""Il read-path non deve dipendere da un modello di embedding IN-PROCESS.

Perche' questo file esiste (misurato sul corpus reale il 25/07). Il recall
encoda la query passando dal daemon condiviso, quindi in un processo SDK il
modello in-process resta FREDDO. Lo scorer della fusione chiamava invece
``embedding.encode([query])`` — con la lista — e ``encode()`` ha due rami con
contratti opposti:

  * stringa  -> ``_encode_one`` -> daemon condiviso, LRU-cached: 32 ms;
  * lista    -> ramo batch -> ``_model()`` -> cold-load in-process: 26382 ms.

Con un budget di fusione di 2 s il thread veniva ucciso a meta' caricamento, non
lasciava nulla di caldo, e la query successiva ripartiva da zero: 6 overrun su 6
query, 2000 ms buttati ogni volta e la fusione che non consegnava MAI in
produzione. Nessuno dei 8000 test lo vedeva perche' il conftest rende
``_model()`` istantaneo e il modello residente: nella suite i due rami sono
indistinguibili. Questi test rendono osservabile la differenza, invertendo
quella condizione — nessun modello residente e cold-load vietato, che e' la
condizione REALE di un processo servito dal daemon.

Il difetto era gia' stato trovato una volta (audit#2 2026-06-08, A-2, il
commento in ``embedding.encode``) e curato solo per ``HIPPO_ENCODE_DELEGATE_
ONLY``: fuori da quel flag il ramo batch cold-loada ancora. Per questo il file
contiene anche una guardia di CLASSE e non solo il test del call-site.
"""
from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from verimem.semantic import Fact, SemanticMemory

FACTS = [
    "The deploy pipeline retries a failed upload three times.",
    "Rate limiting returns HTTP 429 with a Retry-After header.",
    "The parser rejects malformed headers before validation.",
    "Backups run nightly at 03:00 UTC to the cold bucket.",
]
QUERY = "retry policy on failed upload"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "on")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i, p in enumerate(FACTS):
        sm.store(Fact(id=f"f{i}", proposition=p, topic="t"), embed="sync")
    return sm


@pytest.fixture()
def daemon_only(monkeypatch):
    """Un processo servito dal DAEMON: nessun modello in-process residente, e
    il cold-load e' un errore. Il vettore lo produce lo stub del conftest, cosi'
    le similarita' restano quelle che il resto della suite si aspetta."""
    from verimem import embedding
    stub = embedding._MODEL                      # noqa: SLF001 — lo stub del conftest
    assert stub is not None, "il conftest deve aver installato lo stub"

    def _cold_load_forbidden():
        raise AssertionError(
            "cold-load in-process del modello sul read-path: 26 s dentro un "
            "budget di 2 s, esattamente il difetto misurato il 25/07")

    def _from_daemon(text):
        return np.asarray(stub.encode(text), dtype=np.float32)

    monkeypatch.setattr(embedding, "_MODEL", None)          # non residente
    monkeypatch.setattr(embedding, "_model", _cold_load_forbidden)
    monkeypatch.setattr(embedding, "_encode_via_service", _from_daemon)
    embedding.encode_cache_clear()
    yield
    embedding.encode_cache_clear()


def test_scorer_works_without_an_in_process_model(store, daemon_only):
    """Il numero che lo scorer mette nella ricevuta deve essere REALE anche
    quando il modello vive solo nel daemon. Col ramo batch l'encode esplode, lo
    scorer cade nel suo fail-soft e restituisce 0.0: una similarita' 'misurata
    zero' che in verita' non e' stata misurata — il difetto che lo scorer stesso
    era stato scritto per chiudere."""
    fact = store.get("f0")
    assert fact is not None
    sim = store._extra_similarity_scorer(QUERY)(fact)  # noqa: SLF001
    assert sim > 0.0, (
        "lo scorer ha restituito 0.0 con il modello solo nel daemon: sta "
        "chiedendo un encode che richiede il modello IN-PROCESS")


def test_a_whole_recall_never_touches_the_in_process_model(store, monkeypatch):
    """La proprieta' di SISTEMA, e la sola che avrebbe colto il difetto dov'era:
    un recall completo — fusione accesa — non deve toccare ``_model()`` nemmeno
    una volta. Non basta che il recall risponda: rispondeva anche col difetto,
    perche' il fail-soft dello scorer inghiotte l'errore e restituisce 0.0. Qui
    si conta l'ACCESSO, non l'esito, quindi il test resta valido anche se lo
    scorer venisse riscritto."""
    from verimem import embedding
    stub = embedding._MODEL                              # noqa: SLF001
    accessi: list[str] = []

    def _model_conteggiato():
        accessi.append("cold-load")
        return stub

    monkeypatch.setattr(embedding, "_MODEL", None)       # non residente
    monkeypatch.setattr(embedding, "_model", _model_conteggiato)
    monkeypatch.setattr(embedding, "_encode_via_service",
                        lambda text: np.asarray(stub.encode(text), dtype=np.float32))
    embedding.encode_cache_clear()
    try:
        hits = store.recall(QUERY, k=4)
    finally:
        embedding.encode_cache_clear()

    assert hits, "il recall non ha prodotto risultati senza modello in-process"
    assert not accessi, (
        f"il recall ha chiesto il modello in-process {len(accessi)} volte: in un "
        "processo servito dal daemon ognuna e' un cold-load da ~26 s")


# --------------------------------------------------------------------------
# Guardia di CLASSE. Il call-site curato era uno, ma il pattern e' il difetto:
# passare UN SOLO testo al ramo batch non da' alcun vantaggio di batching e
# porta il cold-load. Un batch VERO (N testi) resta legittimo e non e' coperto.
# Escluso ``self.embedder.encode([...])``: e' un embedder iniettato, un altro
# oggetto con un altro contratto.
# --------------------------------------------------------------------------
_PKG = Path(__file__).resolve().parent.parent / "verimem"


def _single_element_batch_encodes() -> list[str]:
    trovati: list[str] = []
    for py in _PKG.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError):        # non e' il lavoro di questo test
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fn = node.func
            is_module_encode = (
                isinstance(fn, ast.Attribute) and fn.attr == "encode"
                and isinstance(fn.value, ast.Name)
                and fn.value.id in ("embedding", "_embedding")
            )
            if not is_module_encode:
                continue
            arg = node.args[0]
            if isinstance(arg, (ast.List, ast.Tuple)) and len(arg.elts) == 1:
                trovati.append(f"{py.name}:{node.lineno}")
    return trovati


def test_no_single_element_batch_encode_in_the_package():
    """``embedding.encode([x])`` prende il ramo batch — che cold-loada — per un
    solo testo, cioe' paga il rischio senza il beneficio. La forma giusta e'
    ``embedding.encode(x)``: daemon-first e LRU-cached."""
    trovati = _single_element_batch_encodes()
    assert not trovati, (
        "encode() con una lista di UN elemento (ramo batch = cold-load "
        f"in-process, 26 s misurati): {trovati}. Usa encode(x) senza lista.")


# --------------------------------------------------------------------------
# Il BREAKER. Il cold-load era la causa prossima; la ragione per cui e' vissuto
# per settimane e' che nulla lo fermava. encode ha un breaker dal 2026-06-06,
# il rerank dal 2026-07-10 — con un commento che descrive parola per parola
# questo scenario — la fusione non ne aveva nessuno, e ha continuato a pagare
# 2 s per query per un risultato che non riceveva mai.
# --------------------------------------------------------------------------
@pytest.fixture()
def fusione_che_sfonda(monkeypatch):
    """Una fusione che supera SEMPRE il budget, senza dipendere dai tempi veri:
    budget minuscolo e corpo lento."""
    import time

    from verimem import ppr_seed, semantic
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0.01")
    monkeypatch.setattr(ppr_seed, "fuse_dense_and_ppr",
                        lambda *a, **kw: time.sleep(0.5) or [])
    semantic._fusion_breaker_reset()                     # noqa: SLF001
    yield semantic
    semantic._fusion_breaker_reset()                     # noqa: SLF001


def test_systematic_overruns_trip_the_breaker(store, fusione_che_sfonda):
    """Dopo N overrun consecutivi la fusione si spegne per il processo: e' la
    differenza fra pagare il budget 5 volte e pagarlo per sempre."""
    semantic = fusione_che_sfonda
    n = semantic._fusion_breaker_n()                     # noqa: SLF001
    assert n > 0, "il default del breaker non deve essere 'disattivato'"
    for _ in range(n):
        store.recall(QUERY, k=4)
    assert semantic._fusion_breaker_tripped(), (         # noqa: SLF001
        f"{n} overrun consecutivi non hanno fatto scattare il breaker: il "
        "recall continuerebbe a pagare il budget a ogni query")


def test_a_tripped_breaker_stops_attempting_the_fusion(store, fusione_che_sfonda):
    """Scattato il breaker, la fusione non va nemmeno TENTATA — se venisse
    tentata il breaker sarebbe una diagnosi, non una cura."""
    semantic = fusione_che_sfonda
    for _ in range(semantic._fusion_breaker_n()):        # noqa: SLF001
        store.recall(QUERY, k=4)
    assert semantic._fusion_breaker_tripped()            # noqa: SLF001

    from verimem import ppr_seed
    tentativi: list[int] = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ppr_seed, "fuse_dense_and_ppr",
                   lambda *a, **kw: tentativi.append(1) or [])
        store.recall(QUERY, k=4)
    assert not tentativi, "la fusione e' stata tentata a breaker scattato"


def test_an_in_budget_success_re_arms_the_count(store, fusione_che_sfonda):
    """Una contesa passeggera non deve spegnere niente in permanenza: un
    successo in budget azzera il contatore. Senza questo, N overrun sparsi
    nell'arco di una sessione lunga spegnerebbero una fusione sana."""
    semantic = fusione_che_sfonda
    n = semantic._fusion_breaker_n()                     # noqa: SLF001
    for _ in range(n - 1):                               # un passo dalla soglia
        store.recall(QUERY, k=4)
    assert not semantic._fusion_breaker_tripped()        # noqa: SLF001

    from verimem import ppr_seed
    with pytest.MonkeyPatch.context() as mp:             # una fusione che ce la fa
        mp.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "5")
        mp.setattr(ppr_seed, "fuse_dense_and_ppr",
                   lambda dense, *a, **kw: list(dense))
        store.recall(QUERY, k=4)

    for _ in range(n - 1):                               # di nuovo sotto soglia
        store.recall(QUERY, k=4)
    assert not semantic._fusion_breaker_tripped(), (      # noqa: SLF001
        "il contatore non e' stato azzerato dal successo: overrun non "
        "consecutivi spengono una fusione sana")
