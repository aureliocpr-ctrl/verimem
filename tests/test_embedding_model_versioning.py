"""Behind-flag encoder upgrade — additive + reversible (2026-06-03).

Verifica che:
  * il DEFAULT sia identico al legacy (MiniLM 384) quando l'env e' unset
    -> recall NON cambia (stesso modello, stesso byte-length del filtro);
  * il modello/dim siano override-abili via HIPPO_EMBEDDING_MODEL /
    HIPPO_EMBEDDING_DIM (caricamento dietro flag, fresh DB);
  * le primitive di versioning (model_signature / expected_embedding_bytes /
    verify_model_dim) riflettano CONFIG senza side-effect;
  * l'encode service annunci model+dim (additive, backward-compatible).

Hermetic: nessun modello reale caricato (verify_model_dim usa un fake).
"""
from __future__ import annotations

from verimem import embedding
from verimem.config import Config

_LEGACY_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_ACTIVE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # default attivo post-flip 2026-06-04


# --- DEFAULT invariato (env unset) -> recall non cambia --------------------

def test_default_model_is_e5_after_golive(monkeypatch):
    # GO-LIVE e5 2026-06-04: default ATTIVO (env unset) -> e5-base 768d (MRR
    # 0.466->0.710). _LEGACY resta MiniLM (decoupled) per le righe NULL.
    monkeypatch.delenv("HIPPO_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("HIPPO_EMBEDDING_DIM", raising=False)
    c = Config()
    assert c.embedding_model == "intfloat/multilingual-e5-base"
    assert c.embedding_dim == 768


def test_default_signature_is_active_and_bytes_384():
    # Post-flip: model_signature() = modello ATTIVO (multilingue); dim invariata 384.
    assert embedding.model_signature() == _ACTIVE_MODEL
    assert embedding.expected_embedding_bytes() == 384 * 4  # 1536


def test_expected_bytes_equals_semantic_recall_filter():
    # PROVA che il recall NON cambia: il byte-length atteso dalle primitive
    # combacia col filtro hard del recall live (semantic._EXPECTED_EMBEDDING_BYTES).
    from verimem.semantic import _EXPECTED_EMBEDDING_BYTES
    assert embedding.expected_embedding_bytes() == _EXPECTED_EMBEDDING_BYTES == 1536


# --- ENV-FLAG override (fresh DB / eval) -----------------------------------

def test_env_flag_overrides_model_and_dim(monkeypatch):
    monkeypatch.setenv("HIPPO_EMBEDDING_MODEL",
                       "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    monkeypatch.setenv("HIPPO_EMBEDDING_DIM", "768")
    c = Config()
    assert c.embedding_model.endswith("paraphrase-multilingual-mpnet-base-v2")
    assert c.embedding_dim == 768


def test_env_flag_reversible(monkeypatch):
    # Settato e poi tolto -> torna al DEFAULT (e5 dopo il go-live 2026-06-04). Reversibile.
    monkeypatch.setenv("HIPPO_EMBEDDING_MODEL", "x/other")
    assert Config().embedding_model == "x/other"
    monkeypatch.delenv("HIPPO_EMBEDDING_MODEL", raising=False)
    assert Config().embedding_model == "intfloat/multilingual-e5-base"


# --- verify_model_dim (falsification guard, fake model) --------------------

class _FakeModel:
    def __init__(self, dim: int) -> None:
        self._dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim


def test_verify_model_dim_matches(monkeypatch):
    monkeypatch.setattr(embedding, "_model", lambda: _FakeModel(384))
    ok, actual = embedding.verify_model_dim()
    assert ok is True and actual == 384


def test_verify_model_dim_detects_mismatch(monkeypatch):
    # Modello che produce 768 ma CONFIG dice 384 -> mismatch (fail-closed hook).
    monkeypatch.setattr(embedding, "_model", lambda: _FakeModel(768))
    ok, actual = embedding.verify_model_dim()
    assert ok is False and actual == 768


# --- encode_service annuncia dim (additive, backward-compatible) -----------

def test_encode_service_ping_advertises_dim():
    from verimem import encode_service
    srv = encode_service.EncodeServer(
        encode_fn=lambda t: [0.0, 0.0, 0.0],
        model_name="m-test", model_dim=384,
    )
    resp = srv._handle_request({"ping": True})
    assert resp["ok"] is True
    assert resp["model"] == "m-test"
    assert resp["dim"] == 384  # nuovo campo additive


def test_encode_service_dim_defaults_zero_when_unset():
    # Backward-compat: chi non passa model_dim ottiene 0 (campo presente, neutro).
    from verimem import encode_service
    srv = encode_service.EncodeServer(
        encode_fn=lambda t: [0.0], model_name="m",
    )
    assert srv._handle_request({"ping": True})["dim"] == 0
