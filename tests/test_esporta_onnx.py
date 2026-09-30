"""The ONNX export of the product's embedder (benchmark/judge_v3/esporta_onnx.py): the parts that run anywhere.

The export itself needs onnx and onnxscript, which live in the export's own venv (requirements
beside the script), not in the shared environment: those steps are measured by the script when it
runs, and written in its manifest. What is checked here decides whether an exported vector can be
the product's vector:

1. the graph pools and normalizes exactly as sentence-transformers does, on a padded batch;
2. a row gives the same vector alone and padded in a batch (the daemon batches);
3. the export refuses a pipeline that is not Transformer -> mean Pooling -> Normalize, instead of
   silently exporting mean pooling for a model that pools otherwise;
4. the parity metrics: the cosine row by row, and recall@k as the share of the top-k neighbours
   two encoders agree on;
5. the manifest reads the versions from the modules it imported, it does not declare them.

No model is downloaded: the transformer is a tiny XLM-RoBERTa with random weights.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

CARTELLA = Path(__file__).resolve().parents[1] / "benchmark" / "judge_v3"
sys.path.insert(0, str(CARTELLA))

PAD = 1  # XLM-RoBERTa's pad id, as in intfloat/multilingual-e5-base
LARGHEZZA = 16


def _modello_piccolo():
    from transformers import XLMRobertaConfig, XLMRobertaModel

    torch.manual_seed(0)
    config = XLMRobertaConfig(
        vocab_size=64, hidden_size=LARGHEZZA, num_hidden_layers=2, num_attention_heads=2,
        intermediate_size=32, max_position_embeddings=40, pad_token_id=PAD,
    )
    return XLMRobertaModel(config).eval()


def _lotto():
    # two rows of different length: the short one is right-padded with the pad id and mask 0
    ids = torch.tensor([[0, 5, 9, 12, 7, 2], [0, 8, 3, 2, PAD, PAD]])
    return ids, (ids != PAD).long()


def _riferimento(modello, ids, maschera):
    import esporta_onnx

    Pooling, Normalize = esporta_onnx.pooling_e_normalize()

    with torch.no_grad():
        token = modello(input_ids=ids, attention_mask=maschera).last_hidden_state
    feats = Pooling(LARGHEZZA, pooling_mode="mean")({"token_embeddings": token, "attention_mask": maschera})
    return Normalize()(feats)["sentence_embedding"]


def test_the_graph_pools_and_normalizes_like_sentence_transformers_on_a_padded_batch() -> None:
    import esporta_onnx

    modello = _modello_piccolo()
    ids, maschera = _lotto()
    atteso = _riferimento(modello, ids, maschera)
    with torch.no_grad():
        uscito = esporta_onnx.ConPooling(modello)(ids, maschera)
    assert tuple(uscito.shape) == tuple(atteso.shape) == (2, LARGHEZZA)
    assert torch.max(torch.abs(uscito - atteso)).item() < 1e-6
    # POSITIVE CONTROL: the batch exercises the mask. A mean that also counts the padded
    # positions lands elsewhere on the padded row, so a graph that ignored the mask fails above
    with torch.no_grad():
        token = modello(input_ids=ids, attention_mask=maschera).last_hidden_state
    senza_maschera = torch.nn.functional.normalize(token.mean(dim=1), p=2, dim=1)
    assert torch.max(torch.abs(senza_maschera[1] - atteso[1])).item() > 1e-3


def test_a_row_gives_the_same_vector_alone_and_padded_in_a_batch() -> None:
    import esporta_onnx

    modello = _modello_piccolo()
    ids, maschera = _lotto()
    with torch.no_grad():
        nel_lotto = esporta_onnx.ConPooling(modello)(ids, maschera)[1]
        da_sola = esporta_onnx.ConPooling(modello)(ids[1:, :4], maschera[1:, :4])[0]
    assert torch.max(torch.abs(nel_lotto - da_sola)).item() < 1e-5


class _Trasformatore(torch.nn.Module):
    # stands for sentence-transformers' Transformer module: the export reads only auto_model
    def __init__(self) -> None:
        super().__init__()
        self.auto_model = _modello_piccolo()


def test_the_export_accepts_transformer_then_mean_pooling_then_normalize() -> None:
    import esporta_onnx

    Pooling, Normalize = esporta_onnx.pooling_e_normalize()

    esporta_onnx.controlla_moduli([_Trasformatore(), Pooling(LARGHEZZA, pooling_mode="mean"), Normalize()])


@pytest.mark.parametrize("caso", ["cls pooling", "mean and max", "no normalize", "no transformer"])
def test_the_export_refuses_any_other_pipeline(caso: str) -> None:
    import esporta_onnx

    Pooling, Normalize = esporta_onnx.pooling_e_normalize()

    moduli = {
        "cls pooling": [_Trasformatore(), Pooling(LARGHEZZA, pooling_mode="cls"), Normalize()],
        "mean and max": [_Trasformatore(), Pooling(LARGHEZZA, pooling_mode=("mean", "max")), Normalize()],
        "no normalize": [_Trasformatore(), Pooling(LARGHEZZA, pooling_mode="mean")],
        "no transformer": [Pooling(LARGHEZZA, pooling_mode="mean"), Normalize()],
    }[caso]
    with pytest.raises(ValueError):
        esporta_onnx.controlla_moduli(moduli)


def test_the_cosine_is_read_row_by_row() -> None:
    import esporta_onnx

    a = np.array([[1.0, 0.0], [0.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    b = np.array([[2.0, 0.0], [1.0, 0.0], [-3.0, -4.0]], dtype=np.float32)
    assert np.allclose(esporta_onnx.coseni(a, b), [1.0, 0.0, -1.0])


def test_recall_at_k_is_the_share_of_top_k_neighbours_both_encoders_agree_on() -> None:
    import esporta_onnx

    rif = np.array([[0.9, 0.8, 0.1, 0.0], [0.1, 0.2, 0.3, 0.4]])
    alt = np.array([[0.9, 0.1, 0.8, 0.0], [0.1, 0.2, 0.3, 0.4]])
    # row 0: the top-2 are {0, 1} for one encoder and {0, 2} for the other; row 1 agrees
    assert esporta_onnx.richiamo_a_k(rif, alt, k=2) == pytest.approx((0.5 + 1.0) / 2)
    assert esporta_onnx.richiamo_a_k(rif, alt, k=1) == pytest.approx(1.0)
    assert esporta_onnx.richiamo_a_k(rif, rif, k=3) == pytest.approx(1.0)


def test_a_table_quantized_row_by_row_keeps_every_row_within_half_a_step() -> None:
    import esporta_onnx

    rng = np.random.default_rng(0)
    tabella = rng.normal(0.0, 0.05, size=(50, 16)).astype(np.float32)
    tabella[7] *= 40.0  # an outlier row: with ONE scale for the table it would flatten all the others
    tabella[9] = 0.0  # a row of zeros must not divide by zero
    interi, scale = esporta_onnx.quantizza_per_riga(tabella)
    assert interi.dtype == np.int8 and interi.shape == tabella.shape
    assert scale.dtype == np.float32 and scale.shape == (50, 1)
    assert int(np.abs(interi.astype(np.int16)).max()) <= 127
    ricostruita = interi.astype(np.float32) * scale
    assert np.all(np.abs(ricostruita - tabella) <= scale / 2 + 1e-7)
    assert np.all(ricostruita[9] == 0.0)
    # POSITIVE CONTROL: one scale for the whole table, as onnxruntime's Gather does, loses the ordinary rows
    unica = np.abs(tabella).max() / 127
    a_scala_unica = np.round(tabella / unica) * unica
    assert np.abs(a_scala_unica[0] - tabella[0]).max() > 10 * np.abs(ricostruita[0] - tabella[0]).max()


def test_the_candidate_is_the_closest_int8_that_fits_under_the_size_cap() -> None:
    import esporta_onnx

    manifesto = {
        "uscite": {"a.onnx": {"mb": 266.3}, "b.onnx": {"mb": 266.7}, "c.onnx": {"mb": 816.7}},
        "int8": {"a.onnx": {"contro_fp32": {"coseno_mediano": 0.978}},
                 "b.onnx": {"contro_fp32": {"coseno_mediano": 0.989}},
                 "c.onnx": {"contro_fp32": {"coseno_mediano": 0.999}}},
    }
    scelta = esporta_onnx.candidata(manifesto)
    # c is closer to fp32 but does not fit the daemon: the size cap comes first
    assert scelta["file"] == "b.onnx" and scelta["coseno_mediano_contro_fp32"] == 0.989
    with pytest.raises(ValueError):
        esporta_onnx.candidata({"uscite": {"c.onnx": {"mb": 816.7}}, "int8": {"c.onnx": manifesto["int8"]["c.onnx"]}})


def test_the_manifest_reads_the_versions_from_the_modules_it_imported() -> None:
    import esporta_onnx
    import sentence_transformers
    import transformers

    versioni = esporta_onnx.versioni()
    assert versioni["torch"] == torch.__version__
    assert versioni["transformers"] == transformers.__version__
    assert versioni["sentence_transformers"] == sentence_transformers.__version__
    assert versioni["numpy"] == np.__version__
    # a package that is not importable here is written as missing, never as a guess
    for nome in ("onnx", "onnxscript", "onnxruntime", "tokenizers"):
        try:
            modulo = importlib.import_module(nome)
        except ImportError:
            assert versioni[nome] is None, nome
        else:
            assert versioni[nome] == modulo.__version__, nome
