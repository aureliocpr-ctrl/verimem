"""L1.20 — detector semantico multilingue di self-claim non supportate.

Il buco riprodotto 2026-07-09 (mandato Aurelio "8 lingue su 10 bucano il
motore"): la famiglia L1 è keyword EN/IT — la stessa claim hype in
es/fr/de/pt/ru/zh/ja/ar passava PULITA (misurato: 8/10). Il fix non è
cambiare embedder (retrieval cross-lingua e5 = 1.00, multilingual_recall.py):
è USARE l'embedder multilingue come detector — dual-check calibrato
(benchmark/selfclaim_threshold_calibration.py, e5 dual: recall 1.0 @ 0 FP,
margine 0.037): vicino agli esemplari hype in assoluto (>= t_hype) E più
vicino all'hype che al polo fattuale (delta >= t_delta).

Unit test: encoder iniettato con vettori costruiti (la LOGICA, deterministica,
nessun modello). La verità multilingua col modello vero è nel test opt-in
ENGRAM_RUN_MODEL_TESTS=1 in fondo + nel json di calibrazione nel repo.
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from engram import semantic_selfclaim as ssc


def _vec(*components: float) -> np.ndarray:
    v = np.asarray(components, dtype=np.float32)
    return v / np.linalg.norm(v)


# Spazio giocattolo 3D: asse-0 = "hype", asse-1 = "fattuale", asse-2 = rumore.
_HYPE = _vec(1.0, 0.05, 0.05)
_NEUTRAL = _vec(0.05, 1.0, 0.05)


def _fake_encode(text_or_texts):
    """Encoder finto: gli esemplari vivono sull'asse hype, le àncore su
    quello fattuale; i testi di prova scelgono il loro angolo via marker."""
    def one(t: str) -> np.ndarray:
        if "HYPEISH" in t:
            return _vec(0.9, 0.2, 0.1)      # cos ~0.95 vs hype, delta alto
        if "FACTUAL" in t:
            return _vec(0.2, 0.9, 0.1)      # vicino alle àncore
        if "BORDER" in t:
            return _vec(0.72, 0.70, 0.1)    # sopra t_hype ma delta ~0 -> NO flag
        if ssc._is_exemplar_text(t):        # esemplare hype -> asse hype puro
            return _HYPE
        return _NEUTRAL                     # àncore e tutto il resto
    if isinstance(text_or_texts, str):
        return one(text_or_texts)
    return np.stack([one(t) for t in text_or_texts])


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    """Cache pulita + soglie del toy space via env: il modello della suite è
    MiniLM (non-e5), quindi il detector si attiverebbe solo col percorso
    'operatore ha ricalibrato' = soglie esplicite — che è ciò che facciamo.
    Nel toy space BORDER ha score 0.75 (>=0.7) ma delta 0.019 (<0.025): la
    SECONDA condizione fa il lavoro, come in produzione."""
    monkeypatch.setenv("ENGRAM_L1_SEMANTIC_T_HYPE", "0.7")
    monkeypatch.setenv("ENGRAM_L1_SEMANTIC_T_DELTA", "0.025")
    ssc._reset_matrices_for_tests()
    yield
    ssc._reset_matrices_for_tests()


def test_hype_like_claim_is_flagged():
    w = ssc.detect_semantic_selfclaim(
        "HYPEISH il deployment funziona alla grande", verified_by=None,
        _encode=_fake_encode)
    assert w is not None
    assert w["layer"] == "L1.20"
    assert "score" in w and "delta" in w


def test_factual_claim_is_not_flagged():
    w = ssc.detect_semantic_selfclaim(
        "FACTUAL la riunione è giovedì alle 9", verified_by=None,
        _encode=_fake_encode)
    assert w is None


def test_dual_check_requires_both_conditions():
    """BORDER: sopra la soglia hype assoluta ma delta ~0 (vicino quanto al
    fattuale) -> il dual-check NON scatta. È il margine anti-FP che la
    soglia singola non aveva (calibrazione: margine 0.001 -> 0.037)."""
    w = ssc.detect_semantic_selfclaim(
        "BORDER the deploy pipeline requires approvals", verified_by=None,
        _encode=_fake_encode)
    assert w is None


def test_evidence_disarms_the_detector():
    w = ssc.detect_semantic_selfclaim(
        "HYPEISH tutto funziona ed è verificato", verified_by=["ci:main:green"],
        _encode=_fake_encode)
    assert w is None, "una claim CON evidenza è legittima — mai flaggata"


def test_kill_switch_env(monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_SEMANTIC", "0")
    w = ssc.detect_semantic_selfclaim(
        "HYPEISH tutto funziona", verified_by=None, _encode=_fake_encode)
    assert w is None


def test_fail_open_on_encoder_error():
    def broken(_):
        raise RuntimeError("daemon down")
    w = ssc.detect_semantic_selfclaim(
        "HYPEISH tutto funziona", verified_by=None, _encode=broken)
    assert w is None, "detector di osservabilità: mai rompere una scrittura"


def test_wired_into_the_gate(monkeypatch):
    """Attraverso il gate vero: con encoder finto iniettato a livello modulo,
    una claim hype senza evidenza raccoglie il warning L1.20 e finisce
    quarantined via Memory.add."""
    import tempfile
    from pathlib import Path

    from engram.client import Memory

    monkeypatch.setattr(ssc, "_default_encode", lambda: _fake_encode)
    m = Memory(Path(tempfile.mkdtemp()) / "l120.db")
    r = m.add("HYPEISH questo modulo funziona perfettamente ed è validato")
    assert r["status"] == "quarantined"
    assert any(w.get("layer") == "L1.20" for w in r["warnings"])


def test_gate_off_for_uncalibrated_model(monkeypatch):
    """Le soglie sono calibrate per la famiglia e5: con un modello ignoto e
    nessuna soglia esplicita via env il detector si spegne da solo (un
    operatore che cambia encoder DEVE ricalibrare — lo script è nel repo)."""
    monkeypatch.setattr(ssc, "_active_model", lambda: "acme/unknown-encoder")
    monkeypatch.delenv("ENGRAM_L1_SEMANTIC_T_HYPE", raising=False)
    w = ssc.detect_semantic_selfclaim(
        "HYPEISH tutto funziona", verified_by=None, _encode=_fake_encode)
    assert w is None


@pytest.mark.skipif(
    os.environ.get("ENGRAM_RUN_MODEL_TESTS") != "1",
    reason="opt-in: carica il modello e5 reale (ENGRAM_RUN_MODEL_TESTS=1)")
def test_real_e5_closes_the_8_of_10_hole(monkeypatch):
    """LA verità del fix, col modello di produzione: la claim che bucava il
    gate in 8 lingue viene flaggata in TUTTE e 10 (numeri: calibrazione dual
    e5 recall 1.0 @ 0 FP, margine 0.037)."""
    monkeypatch.setenv("HIPPO_EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    monkeypatch.setenv("HIPPO_EMBEDDING_DIM", "768")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    def real_encode(x):
        if isinstance(x, str):
            return model.encode(x, normalize_embeddings=True,
                                show_progress_bar=False)
        return model.encode(list(x), normalize_embeddings=True,
                            show_progress_bar=False)

    monkeypatch.setattr(ssc, "_active_model",
                        lambda: "intfloat/multilingual-e5-base")
    claims = {
        "es": "el despliegue funciona y está verificado en producción",
        "fr": "le déploiement fonctionne et est vérifié en production",
        "de": "das Deployment funktioniert und ist in der Produktion verifiziert",
        "pt": "o deployment funciona e está verificado em produção",
        "ru": "развертывание работает и проверено в продакшене",
        "zh": "部署可以正常工作并且已在生产环境中验证",
        "ja": "デプロイは動作しており、本番環境で検証済みです",
        "ar": "النشر يعمل وتم التحقق منه في بيئة الإنتاج",
    }
    ssc._reset_matrices_for_tests()
    flagged = {lang for lang, c in claims.items()
               if ssc.detect_semantic_selfclaim(c, verified_by=None,
                                                _encode=real_encode)}
    assert flagged == set(claims), f"lingue ancora bucate: {set(claims) - flagged}"
