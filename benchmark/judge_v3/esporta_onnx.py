"""Export the product's embedder to ONNX, fp32 and int8, and measure the parity step by step.

The embedder is the one the product loads (verimem/config.py: intfloat/multilingual-e5-base, 768
dimensions): sentence-transformers' Transformer -> mean Pooling -> Normalize, encoded with
normalize_embeddings=True. For an e5 model the product prefixes the text: «passage: » for what it
stores and «query: » for what it searches (verimem/embedding.py, as_passage and as_query). The prefix
is text, so it stays with whoever calls the graph, and the texts of the steps carry it as the product
does. The graph written here holds the pooling and the normalization too, so its output IS the
product's vector, and whoever runs it needs onnxruntime and a tokenizer, not torch.

It runs in its own venv, never in the shared environment:

    python -m venv --system-site-packages <venv>
    <venv>/Scripts/python -m pip install -r benchmark/judge_v3/requirements-esporta-onnx.txt
    <venv>/Scripts/python benchmark/judge_v3/esporta_onnx.py --uscita <folder>

--system-site-packages reuses the product's torch, transformers, sentence-transformers, tokenizers
and onnxruntime: the export traces the code that made the vectors in the corpus, and the int8 comes
out of the onnxruntime that will run it. The venv adds only onnx and onnxscript, which torch's
exporter needs.

The parity is measured in steps that separate the causes, with the thresholds written here before
any run:
  0. the graph in torch against SentenceTransformer.encode: the wrapper is the product;
  1. the token ids of the runtime tokenizer against sentence-transformers' ones, then the ONNX fp32
     against SentenceTransformer.encode, in batches and one text alone: the export;
  2. each int8 against the ONNX fp32 and against SentenceTransformer.encode: the quantization. It is
     measured and written, not judged here: the int8 is judged on the corpus, against the vectors
     the product has stored (recall@k and cosine), where a failure has a price, re-encoding it.

Two int8 are written, because onnxruntime's quantize_dynamic says reduce_range «may improve the
accuracy for some models running on non-VNNI machine», and the product runs on its users' CPUs,
not on the one that exports: model_int8.onnx (8-bit weights) and model_int8_rr.onnx (7-bit
weights). The corpus decides which one ships.

Everything goes in manifesto.json beside the models: the versions read from the imported modules,
the sha256 of inputs and outputs, the options, the numbers of every step and the verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

MODELLO_DEL_PRODOTTO = "intfloat/multilingual-e5-base"
PACCHETTI = ("torch", "transformers", "sentence_transformers", "tokenizers",
             "onnx", "onnxscript", "onnxruntime", "numpy")

#: the threshold of the steps judged here (0 and 1): the lowest cosine over the texts
SOGLIA_COSENO_MINIMO = 0.99999

#: the int8 variants, by file name: quantize_dynamic's options
VARIANTI_INT8 = {
    "model_int8.onnx": {"per_channel": False, "reduce_range": False},
    "model_int8_rr.onnx": {"per_channel": False, "reduce_range": True},
}

#: the texts of the steps: four languages and two more scripts, the shapes the product encodes
#: (a fact, a negation, a question, a number, a timestamp, a command), the product's own prefixes,
#: an empty string, and one text longer than 512 tokens so that the truncation is exercised
TESTI = [
    "passage: Il contratto LC-0417 prevede un affitto di 850 euro al mese.",
    "query: quanto costa l'affitto del contratto LC-0417?",
    "passage: The daemon keeps the model in memory and exits after ten minutes of idle time.",
    "query: when does the daemon exit?",
    "Il contratto LC-0417 prevede un affitto di 850 euro al mese.",
    "Non è vero che il deposito sia di tre mensilità.",
    "Quante pompe sono ferme nell'impianto PL-0203?",
    "La riunione di progetto è fissata per il 14 ottobre alle 10:30.",
    "The lease LC-0417 sets the rent at 850 euros per month.",
    "Which version of the judge was used for the last release?",
    "The daemon keeps the model in memory and exits after ten minutes of idle time.",
    "Water boils at 100 degrees Celsius at sea level.",
    "Le contrat LC-0417 fixe le loyer à 850 euros par mois.",
    "La station de pompage compte douze pompes, dont trois à l'arrêt.",
    "Quelle est la date de la prochaine mise à jour ?",
    "El contrato LC-0417 fija el alquiler en 850 euros al mes.",
    "La planta tiene doce bombas y tres están paradas.",
    "¿Cuándo se publicó la versión 0.7.6?",
    "Das Treffen findet am Montag statt.",
    "東京は日本の首都です。",
    "2026-09-30T21:17:51Z",
    "verimem save --topic project/x --source out.txt",
    "OK",
    "",
    " ".join(["Il giudice legge la fonte e la frase, e decide se la fonte sostiene la frase."] * 60),
]


class ConPooling(torch.nn.Module):
    """The product's vector as one graph: the transformer, then the mean over the tokens the mask
    keeps (as sentence-transformers' Pooling), then the L2 normalization (as its Normalize)."""

    def __init__(self, auto_model: torch.nn.Module) -> None:
        super().__init__()
        self.auto_model = auto_model

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        token = self.auto_model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        maschera = attention_mask.unsqueeze(-1).to(token.dtype)
        media = (token * maschera).sum(dim=1) / torch.clamp(maschera.sum(dim=1), min=1e-9)
        return torch.nn.functional.normalize(media, p=2, dim=1)


def pooling_e_normalize():
    """sentence-transformers' Pooling and Normalize classes, from where the installed version keeps
    them: sentence_transformer.modules in 5.4 (models/ is deprecated there), models/ before."""
    try:
        from sentence_transformers.sentence_transformer.modules import Normalize, Pooling
    except ImportError:
        from sentence_transformers.models import Normalize, Pooling
    return Pooling, Normalize


def controlla_moduli(moduli) -> None:
    """Refuse any pipeline the graph above does not reproduce, instead of exporting it wrong."""
    Pooling, Normalize = pooling_e_normalize()
    moduli = list(moduli)
    nomi = [type(m).__name__ for m in moduli]
    if len(moduli) != 3:
        raise ValueError(f"pipeline {nomi}: the export writes Transformer -> mean Pooling -> Normalize only")
    primo, pooling, norma = moduli
    if not hasattr(primo, "auto_model"):
        raise ValueError(f"pipeline {nomi}: the first module has no auto_model to export")
    if getattr(primo, "do_lower_case", False):
        raise ValueError("the model lowercases the text, and the runtime tokenizer would not")
    if not isinstance(pooling, Pooling):
        raise ValueError(f"pipeline {nomi}: the second module is not a Pooling")
    modo = pooling.pooling_mode
    modi = (modo,) if isinstance(modo, str) else tuple(modo)
    if modi != ("mean",):
        raise ValueError(f"pooling {modi}: the graph pools with the mean only")
    if not isinstance(norma, Normalize):
        raise ValueError(f"pipeline {nomi}: the third module is not a Normalize")


def coseni(a, b) -> np.ndarray:
    """The cosine of each row of a with the same row of b."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return (a * b).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def richiamo_a_k(sim_rif, sim_alt, k: int) -> float:
    """recall@k: for each row (a query), the share of the reference's top-k neighbours that the other
    encoder also puts in its top-k, averaged over the rows. Both are similarity rows over the same
    corpus; whoever calls it removes the query itself when the query is in the corpus."""
    primi_rif = np.argsort(-np.asarray(sim_rif), axis=1, kind="stable")[:, :k]
    primi_alt = np.argsort(-np.asarray(sim_alt), axis=1, kind="stable")[:, :k]
    return float(np.mean([len(set(r) & set(a)) / k for r, a in zip(primi_rif.tolist(), primi_alt.tolist(), strict=True)]))


def versioni() -> dict[str, str | None]:
    """The versions of the modules as imported here; None for a module that is not importable."""
    uscita: dict[str, str | None] = {"python": platform.python_version()}
    for nome in PACCHETTI:
        try:
            uscita[nome] = importlib.import_module(nome).__version__
        except ImportError:
            uscita[nome] = None
    return uscita


def sha256(percorso: Path) -> str:
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def _confronto(rif, alt) -> dict:
    c = coseni(rif, alt)
    scarto = np.abs(np.asarray(rif, dtype=np.float64) - np.asarray(alt, dtype=np.float64)).max()
    return {"coseno_minimo": float(c.min()), "coseno_mediano": float(np.median(c)),
            "scarto_assoluto_massimo": float(scarto)}


def _tokenizzatore(file_json: Path, lunghezza: int, pad_id: int, pad_token: str):
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(file_json))
    tok.enable_truncation(max_length=lunghezza)
    tok.enable_padding(pad_id=pad_id, pad_token=pad_token)
    return tok


def _vettori_onnx(file_onnx: Path, testi: list[str], tok, lotto: int = 8) -> tuple[np.ndarray, float]:
    """The vectors of an ONNX file on onnxruntime's CPU provider, and the ms per text of a second pass."""
    import onnxruntime as ort

    sessione = ort.InferenceSession(str(file_onnx), providers=["CPUExecutionProvider"])

    def passata() -> np.ndarray:
        vettori = []
        for i in range(0, len(testi), lotto):
            codifiche = tok.encode_batch(testi[i:i + lotto])
            ingresso = {"input_ids": np.array([c.ids for c in codifiche], dtype=np.int64),
                        "attention_mask": np.array([c.attention_mask for c in codifiche], dtype=np.int64)}
            vettori.append(sessione.run(["sentence_embedding"], ingresso)[0])
        return np.concatenate(vettori)

    vettori = passata()
    inizio = time.perf_counter()
    passata()
    return vettori, (time.perf_counter() - inizio) * 1000 / len(testi)


def _operatori(file_onnx: Path) -> dict[str, int]:
    import onnx

    conta: dict[str, int] = {}
    for nodo in onnx.load(str(file_onnx), load_external_data=False).graph.node:
        conta[nodo.op_type] = conta.get(nodo.op_type, 0) + 1
    return dict(sorted(conta.items()))


def esegui(modello: str, uscita: Path, opset: int | None) -> dict:
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    inizio = time.perf_counter()
    cartella = Path(snapshot_download(modello, local_files_only=True))
    st = SentenceTransformer(modello, local_files_only=True, device="cpu")
    if st.prompts and any(st.prompts.values()) or st.default_prompt_name:
        raise ValueError(f"the model adds a prompt ({st.default_prompt_name!r}, {st.prompts}): the graph does not")
    controlla_moduli(st)
    lunghezza = int(st.max_seq_length)
    pad_id, pad_token = int(st.tokenizer.pad_token_id), str(st.tokenizer.pad_token)
    manifesto: dict = {
        "modello": modello, "revisione": cartella.name, "lunghezza_massima": lunghezza,
        "pad_id": pad_id, "pad_token": pad_token, "uscita": "sentence_embedding",
        "versioni": versioni(), "soglia_coseno_minimo": SOGLIA_COSENO_MINIMO,
        "testi": {"quanti": len(TESTI), "sha256": hashlib.sha256("\n".join(TESTI).encode("utf-8")).hexdigest()},
        "ingressi_sha256": {f.name: sha256(f) for f in (cartella / "model.safetensors", cartella / "tokenizer.json")},
        "passi": {},
    }
    atteso = st.encode(TESTI, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)

    # step 0: the graph in torch, fed by sentence-transformers' own tokenization
    grafo = ConPooling(st[0].auto_model).eval()
    caratteristiche = st.tokenize(TESTI)
    with torch.no_grad():
        nel_grafo = grafo(caratteristiche["input_ids"], caratteristiche["attention_mask"]).numpy()
    manifesto["passi"]["0_grafo_contro_encode"] = _confronto(atteso, nel_grafo)

    # step 1: the export, then the runtime tokenizer and the ONNX fp32
    uscita.mkdir(parents=True, exist_ok=True)
    file_fp32 = uscita / "model.onnx"
    esempio = st.tokenize(TESTI[:2])
    lotto, lunghezza_dim = torch.export.Dim("lotto"), torch.export.Dim("lunghezza", max=lunghezza)
    torch.onnx.export(
        grafo, (esempio["input_ids"], esempio["attention_mask"]), str(file_fp32),
        input_names=["input_ids", "attention_mask"], output_names=["sentence_embedding"],
        dynamic_shapes={"input_ids": {0: lotto, 1: lunghezza_dim}, "attention_mask": {0: lotto, 1: lunghezza_dim}},
        dynamo=True, external_data=False, opset_version=opset,
    )
    shutil.copyfile(cartella / "tokenizer.json", uscita / "tokenizer.json")
    tok = _tokenizzatore(uscita / "tokenizer.json", lunghezza, pad_id, pad_token)
    ids_hf = st.tokenizer(TESTI, truncation=True, max_length=lunghezza)["input_ids"]
    ids_runtime = [c.ids[: sum(c.attention_mask)] for c in tok.encode_batch(TESTI)]
    diversi = [i for i, (a, b) in enumerate(zip(ids_hf, ids_runtime, strict=True)) if list(a) != list(b)]
    fp32, ms_fp32 = _vettori_onnx(file_fp32, TESTI, tok)
    # a short text that its batch of 8 pads (the longest text in it has 49 characters), now alone: a batch of 1
    corto = TESTI.index("OK")
    da_solo, _ = _vettori_onnx(file_fp32, [TESTI[corto]], tok, lotto=1)
    manifesto["passi"]["1_token_ids_diversi"] = diversi
    manifesto["passi"]["1_fp32_contro_encode"] = {**_confronto(atteso, fp32), "ms_per_testo": ms_fp32}
    manifesto["passi"]["1_fp32_da_solo_contro_nel_lotto"] = _confronto(fp32[corto:corto + 1], da_solo)

    # step 2: the int8 variants, measured and not judged here
    from onnxruntime.quantization import QuantType, quantize_dynamic

    manifesto["int8"] = {}
    for nome, opzioni in VARIANTI_INT8.items():
        file_int8 = uscita / nome
        quantize_dynamic(model_input=str(file_fp32), model_output=str(file_int8),
                         weight_type=QuantType.QInt8, **opzioni)
        int8, ms_int8 = _vettori_onnx(file_int8, TESTI, tok)
        manifesto["int8"][nome] = {
            "opzioni": {"weight_type": "QInt8", **opzioni},
            "contro_fp32": _confronto(fp32, int8), "contro_encode": _confronto(atteso, int8),
            "ms_per_testo": ms_int8, "operatori": _operatori(file_int8),
        }

    import onnx

    modello_fp32 = onnx.load(str(file_fp32), load_external_data=False)
    manifesto["opset"] = {o.domain or "ai.onnx": o.version for o in modello_fp32.opset_import}
    manifesto["operatori_fp32"] = _operatori(file_fp32)
    manifesto["uscite"] = {f.name: {"sha256": sha256(f), "mb": round(f.stat().st_size / 2**20, 1)}
                           for f in sorted(uscita.iterdir()) if f.suffix in (".onnx", ".json") and f.name != "manifesto.json"}
    passi = manifesto["passi"]
    manifesto["verdetto_export"] = bool(
        not diversi
        and passi["0_grafo_contro_encode"]["coseno_minimo"] >= SOGLIA_COSENO_MINIMO
        and passi["1_fp32_contro_encode"]["coseno_minimo"] >= SOGLIA_COSENO_MINIMO
        and passi["1_fp32_da_solo_contro_nel_lotto"]["coseno_minimo"] >= SOGLIA_COSENO_MINIMO
    )
    manifesto["durata_s"] = round(time.perf_counter() - inizio, 1)
    (uscita / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifesto


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modello", default=MODELLO_DEL_PRODOTTO)
    parser.add_argument("--uscita", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=None, help="default: torch's exporter's")
    args = parser.parse_args(argv)
    if sys.prefix == sys.base_prefix:
        print("run it in its own venv (see the docstring), not in the shared environment", file=sys.stderr)
        return 2
    manifesto = esegui(args.modello, args.uscita, args.opset)
    print(json.dumps({k: manifesto[k] for k in ("passi", "int8", "uscite", "verdetto_export", "durata_s")},
                     ensure_ascii=False, indent=2))
    return 0 if manifesto["verdetto_export"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
