"""The parity of an ONNX embedder on the product's corpus, against the vectors the product has stored.

P1 (lead, 30/09 20:39): the parity of the int8 vectors «contro gli fp32 gia' nel corpus (recall@k e
coseno sui 18k fatti): se la parita' non regge, il prezzo include la ricodifica del corpus, e si dice
prima».

It opens the store READ-ONLY (SQLite mode=ro) and reads only the live rows the active model wrote:
embedding_model equal to the model, a vector of its size, not replaced by a later fact. It writes and
prints numbers only, never a proposition. It needs onnxruntime, tokenizers and sentence-transformers,
which the product's environment has, and the folder esporta_onnx.py wrote (the ONNX files, the
tokenizer and manifesto.json):

    python benchmark/judge_v3/parita_corpus_onnx.py --store <semantic.db> \
        --onnx <folder>/model_int8.onnx --uscita <folder>/parita_model_int8.json

What it measures for one ONNX file, with the texts prefixed as the product does (verimem/embedding.py:
«passage: » for what it stores, «query: » for what it searches):
  C. the CONTROL: for a sample of facts, the product's own fp32 encode (SentenceTransformer on CPU)
     against the stored vector. It must be ~1, or the stored vectors are not what the rest assumes
     (another device, another text, another model under the same name);
  1. the cosine of the ONNX passage vector with the stored one, for every fact read;
  2. recall@k WITHOUT re-encoding: a sample of facts as queries, encoded fp32 by the product and by the
     ONNX, searched in the stored corpus with the fact itself left out; and the shift of the score of
     the reference's top-1, because the product's thresholds were calibrated on e5-base scores;
  3. recall@k WITH the corpus re-encoded: ONNX queries in the ONNX corpus, against fp32 queries in the
     stored one.
The verdict is not here: its thresholds are fixed with the lead before the run.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import esporta_onnx  # noqa: E402  (the same folder: the metrics and the tokenizer are the export's)

#: queries per block of the similarity rows: 250 x ~18k floats64 stays near 36 MB
BLOCCO = 250


def apri_in_sola_lettura(percorso: Path) -> sqlite3.Connection:
    """The store as SQLite opens it read-only: any write through this connection fails."""
    return sqlite3.connect(f"{Path(percorso).resolve().as_uri()}?mode=ro", uri=True)


def leggi_corpus(percorso: Path, modello: str, dimensione: int) -> tuple[list[str], list[str], np.ndarray]:
    """The live facts whose vector the model wrote, by id: ids, propositions, vectors (float32)."""
    conn = apri_in_sola_lettura(percorso)
    try:
        righe = conn.execute(
            "SELECT id, proposition, embedding FROM facts WHERE embedding_model = ? "
            "AND length(embedding) = ? AND superseded_by IS NULL ORDER BY id",
            (modello, dimensione * 4),
        ).fetchall()
    finally:
        conn.close()
    vettori = np.frombuffer(b"".join(r[2] for r in righe), dtype=np.float32).reshape(len(righe), dimensione)
    return [r[0] for r in righe], [r[1] for r in righe], vettori.copy()


def richiamo_senza_se_stesso(sim_rif, sim_alt, se_stessi, k: int) -> float:
    """recall@k when every query is a fact of the corpus: its own column is left out of both rows."""
    sim_rif = np.array(sim_rif, dtype=np.float64, copy=True)
    sim_alt = np.array(sim_alt, dtype=np.float64, copy=True)
    righe = np.arange(len(se_stessi))
    sim_rif[righe, se_stessi] = -np.inf
    sim_alt[righe, se_stessi] = -np.inf
    return esporta_onnx.richiamo_a_k(sim_rif, sim_alt, k)


def vettori_onnx(file_onnx: Path, testi: list[str], tok, thread: int, lotto: int = 32) -> np.ndarray:
    """The vectors of an ONNX file, in the order of the texts (encoded by length, to pad little)."""
    import onnxruntime as ort

    opzioni = ort.SessionOptions()
    opzioni.intra_op_num_threads = thread
    sessione = ort.InferenceSession(str(file_onnx), sess_options=opzioni, providers=["CPUExecutionProvider"])
    ordine = np.argsort([len(t) for t in testi], kind="stable")
    uscita: np.ndarray | None = None
    for i in range(0, len(testi), lotto):
        scelti = ordine[i:i + lotto]
        codifiche = tok.encode_batch([testi[j] for j in scelti])
        ingresso = {"input_ids": np.array([c.ids for c in codifiche], dtype=np.int64),
                    "attention_mask": np.array([c.attention_mask for c in codifiche], dtype=np.int64)}
        vettori = sessione.run(["sentence_embedding"], ingresso)[0]
        if uscita is None:
            uscita = np.empty((len(testi), vettori.shape[1]), dtype=np.float32)
        uscita[scelti] = vettori
    assert uscita is not None, "no text to encode"
    return uscita


def _quantili(valori: np.ndarray) -> dict:
    return {"quanti": int(len(valori)), "minimo": float(valori.min()), "p01": float(np.quantile(valori, 0.01)),
            "p05": float(np.quantile(valori, 0.05)), "mediano": float(np.median(valori))}


def _confronto_per_blocchi(q_rif, c_rif, q_alt, c_alt, se_stessi, ks) -> tuple[dict, np.ndarray]:
    """recall@k over the corpus without the query's own fact, block by block, and the shift of the score
    that the other encoder gives to the reference's top-1."""
    somme = dict.fromkeys(ks, 0.0)
    spostamenti = []
    for i in range(0, len(q_rif), BLOCCO):
        fine = min(i + BLOCCO, len(q_rif))
        sim_rif = q_rif[i:fine].astype(np.float64) @ c_rif.T.astype(np.float64)
        sim_alt = q_alt[i:fine].astype(np.float64) @ c_alt.T.astype(np.float64)
        propri = se_stessi[i:fine]
        for k in ks:
            somme[k] += richiamo_senza_se_stesso(sim_rif, sim_alt, propri, k) * (fine - i)
        righe = np.arange(fine - i)
        sim_rif[righe, propri] = -np.inf
        primo = sim_rif.argmax(axis=1)
        spostamenti.append(sim_alt[righe, primo] - sim_rif[righe, primo])
    return {k: somme[k] / len(q_rif) for k in ks}, np.concatenate(spostamenti)


def esegui(store: Path, file_onnx: Path, campione: int, controllo: int, ks: list[int], seme: int,
           thread: int) -> dict:
    import torch
    from sentence_transformers import SentenceTransformer

    inizio = time.perf_counter()
    torch.set_num_threads(thread)
    cartella = file_onnx.parent
    manifesto = json.loads((cartella / "manifesto.json").read_text(encoding="utf-8"))
    modello = manifesto["modello"]
    st = SentenceTransformer(modello, local_files_only=True, device="cpu")
    dimensione = int(st.get_sentence_embedding_dimension())
    ids, testi, memorizzati = leggi_corpus(store, modello, dimensione)
    n = len(ids)
    rng = np.random.default_rng(seme)
    domande_idx = np.sort(rng.choice(n, size=min(campione, n), replace=False))
    passaggi = [f"passage: {t}" for t in testi]
    domande = [f"query: {testi[i]}" for i in domande_idx]

    # C. the control: the product's fp32 encode against what the product stored
    scelti = domande_idx[:controllo]
    fp32_controllo = st.encode([passaggi[i] for i in scelti], normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)
    c_controllo = esporta_onnx.coseni(fp32_controllo, memorizzati[scelti])

    # 1. the ONNX passage vector of every fact against the stored one
    tok = esporta_onnx._tokenizzatore(cartella / "tokenizer.json", manifesto["lunghezza_massima"],
                                      manifesto["pad_id"], manifesto["pad_token"])
    onnx_passaggi = vettori_onnx(file_onnx, passaggi, tok, thread)
    c_passaggi = esporta_onnx.coseni(onnx_passaggi, memorizzati)

    # 2. and 3. the same queries, fp32 by the product and by the ONNX
    q_fp32 = st.encode(domande, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    q_onnx = vettori_onnx(file_onnx, domande, tok, thread)
    senza, spostamenti = _confronto_per_blocchi(q_fp32, memorizzati, q_onnx, memorizzati, domande_idx, ks)
    con, _ = _confronto_per_blocchi(q_fp32, memorizzati, q_onnx, onnx_passaggi, domande_idx, ks)
    assoluti = np.abs(spostamenti)
    return {
        "modello": modello, "onnx": {"file": file_onnx.name, "sha256": esporta_onnx.sha256(file_onnx)},
        "store": {"righe_lette": n, "dimensione": dimensione, "filtro": "embedding_model = modello, "
                  "length(embedding) = 4 x dimensione, superseded_by IS NULL"},
        "seme": seme, "domande": len(domande), "k": ks,
        "C_controllo_fp32_contro_memorizzati": {**_quantili(c_controllo),
                                                "sotto_0_9999": int((c_controllo < 0.9999).sum())},
        "1_coseno_onnx_contro_memorizzati": _quantili(c_passaggi),
        "2_richiamo_senza_ricodifica": {str(k): v for k, v in senza.items()},
        "2_spostamento_del_punteggio_top1": {"mediano": float(np.median(assoluti)),
                                             "p99": float(np.quantile(assoluti, 0.99)),
                                             "massimo": float(assoluti.max()),
                                             "medio_con_segno": float(spostamenti.mean())},
        "3_richiamo_con_ricodifica": {str(k): v for k, v in con.items()},
        "versioni": esporta_onnx.versioni(), "thread": thread,
        "durata_s": round(time.perf_counter() - inizio, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", type=Path, required=True, help="the product's semantic.db, opened read-only")
    parser.add_argument("--onnx", type=Path, required=True, help="an ONNX file written by esporta_onnx.py")
    parser.add_argument("--uscita", type=Path, required=True, help="where the numbers go (JSON)")
    parser.add_argument("--campione", type=int, default=2000, help="facts used as queries")
    parser.add_argument("--controllo", type=int, default=200, help="facts re-encoded fp32 for the control")
    parser.add_argument("--k", default="1,5,10")
    parser.add_argument("--seme", type=int, default=20260930)
    parser.add_argument("--thread", type=int, default=4, help="the product's thread budget")
    args = parser.parse_args(argv)
    numeri = esegui(args.store, args.onnx, args.campione, args.controllo,
                    [int(k) for k in args.k.split(",")], args.seme, args.thread)
    args.uscita.write_text(json.dumps(numeri, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(numeri, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
