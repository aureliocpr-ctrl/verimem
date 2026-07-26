"""Una misura di retrieval deve dire in che regime e' stata presa.

I file in ``benchmark/results/`` portano il modello di embedding e il k, ma non
dicono se il cross-encoder stava rerankando, se la fusione era attiva, ne' se un
breaker era scattato a meta' del giro. Cosi' un numero non e' riproducibile e
non e' nemmeno interpretabile: i valori di riferimento di questo corpus non
dichiarano se il CE fosse in funzione, e il 26/07 si e' scoperto che il CE si
spegneva DA SOLO dopo cinque sforamenti — quindi una misura poteva descrivere un
prodotto degradato senza che nulla lo segnalasse.

E' la stessa classe del "+40 ms" di BENCHMARKS.md, misurato col cap della
fusione disattivato: vero nel regime in cui e' stato preso, falso in quello a
cui veniva applicato. Il difetto non era la misura, era il non dichiarare quale
regime descrivesse.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BENCH = Path(__file__).resolve().parents[1] / "benchmark"
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from eval_retrieval_with_gt import evaluate_all, read_path_regime  # noqa: E402

from verimem import semantic as sem  # noqa: E402


def test_the_envelope_actually_carries_the_regime(tmp_path):
    """Il test che mancava, trovato da una mutazione: togliere il campo
    dall'envelope non faceva fallire NIENTE, perche' tutti gli altri test qui
    chiamano ``read_path_regime`` direttamente. Una funzione perfetta che
    nessuno invoca non registra nulla, e il file su disco resta senza regime
    esattamente come prima."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    env = evaluate_all(sm, {"queries": []}, k=5,
                       paths=["facts_cosine_with_legacy"])
    assert "read_path_regime" in env, (
        "l'envelope scritto su disco non porta il regime: i numeri restano "
        "irripetibili, che e' il difetto che questo cambiamento cura")
    assert env["read_path_regime"]["embedding_model"]


def test_the_regime_names_the_two_things_that_decide_the_numbers():
    """Rerank e fusione: se uno dei due era spento, i numeri descrivono un
    prodotto diverso da quello che si crede di aver misurato."""
    r = read_path_regime()
    assert "rerank_enabled" in r
    assert "fusion_enabled" in r


def test_the_regime_reports_a_tripped_breaker():
    """Il caso che rende una misura ingannevole senza che nulla lo dica: il
    breaker scatta a meta' del giro e le query successive non hanno il CE.
    Va letto DOPO la corsa, non prima, altrimenti non lo si vede."""
    sem._rerank_breaker_reset()
    assert read_path_regime()["rerank_breaker"]["tripped"] is False
    try:
        for _ in range(sem._rerank_breaker_n() + 1):
            sem._rerank_breaker_overrun()
        assert read_path_regime()["rerank_breaker"]["tripped"] is True, (
            "un breaker scattato non compare nel regime: la misura sembra "
            "quella del prodotto e invece e' quella del bi-encoder da sola")
    finally:
        sem._rerank_breaker_reset()


def test_the_regime_reports_skipped_reranks():
    """Dal 26/07 il rerank ha uno slot unico: chi arriva mentre un predict e'
    in volo prende l'ordine del bi-encoder. Un giro in cui hanno saltato quasi
    tutte le query non e' una misura del rerank, e chi legge il risultato deve
    poterlo vedere."""
    sem._rerank_breaker_reset()
    lease = sem._rerank_inflight_acquire()
    assert lease
    try:
        for _ in range(3):
            sem._rerank_inflight_acquire()      # tre salti
        assert read_path_regime()["rerank_slot_skipped"] == 3
    finally:
        sem._rerank_inflight_release(lease)
        sem._rerank_breaker_reset()


def test_the_regime_survives_a_missing_environment():
    """Gira anche senza nessuna variabile impostata: un blocco di metadati che
    solleva farebbe perdere la misura che accompagna, e sarebbe un prezzo
    assurdo per un campo informativo."""
    r = read_path_regime()
    assert isinstance(r.get("embedding_model"), str) and r["embedding_model"]
    assert isinstance(r.get("rerank_budget_s"), float)


def test_the_regime_is_json_serialisable():
    """Finisce dentro l'envelope scritto su disco: se un valore non fosse
    serializzabile, il giro morirebbe alla riga del salvataggio, dopo aver
    speso tutto il tempo della valutazione."""
    import json

    json.dumps(read_path_regime())


@pytest.mark.parametrize("chiave", [
    "embedding_model", "rerank_enabled", "rerank_model", "rerank_budget_s",
    "rerank_pairs", "rerank_breaker", "rerank_slot_skipped",
    "fusion_enabled", "fusion_breaker_tripped", "fusion_budget_s",
    "rerank_resident_at_end",
])
def test_every_field_that_changes_a_number_is_present(chiave):
    """Elenco esplicito invece di un controllo generico: se qualcuno togliesse
    un campo, il test deve dire QUALE, non solo che il conto non torna."""
    assert chiave in read_path_regime()
