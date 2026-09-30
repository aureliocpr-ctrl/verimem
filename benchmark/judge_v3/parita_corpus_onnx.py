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
        --onnx <folder>/model_int8.onnx <folder>/model_int8_rr.onnx --uscita <folder>/parita_corpus.json

What it measures, with the texts prefixed as the product does (verimem/embedding.py: «passage: » for
what it stores, «query: » for what it searches). The control and the fp32 queries are computed once, and
every ONNX file is measured on the same sample:
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

#: the thresholds, fixed with the lead BEFORE the run (30/09 22:02)
SOGLIA_CONTROLLO = 0.9999  # C: lowest cosine, the product's fp32 encode against the stored vector
SOGLIA_COSENO_P01 = 0.98  # 1: the ONNX passage vector against the stored one
SOGLIA_COSENO_MEDIANO = 0.99
SOGLIA_RICHIAMO_10 = 0.95  # 2 and 3
SOGLIA_RICHIAMO_1 = 0.90  # 2
SOGLIA_SPOSTAMENTO_P99 = 0.02  # 2: the shift of the reference's top-1 score


def verdetto(numeri: dict) -> dict[str, str]:
    """The verdict of every file, with the thresholds above: it holds without re-encoding if (1) and (2)
    hold, it holds with the corpus re-encoded if (3) holds, otherwise it does not hold. A control under its
    threshold stops everything: the stored vectors would not be what the rest assumes."""
    if numeri["C_controllo_fp32_contro_memorizzati"]["minimo"] < SOGLIA_CONTROLLO:
        return {"controllo": "non regge: ci si ferma"}
    esiti = {}
    for nome, f in numeri["per_file"].items():
        coseno, senza = f["1_coseno_onnx_contro_memorizzati"], f["2_richiamo_senza_ricodifica"]
        uno = coseno["p01"] >= SOGLIA_COSENO_P01 and coseno["mediano"] >= SOGLIA_COSENO_MEDIANO
        due = (senza["10"] >= SOGLIA_RICHIAMO_10 and senza["1"] >= SOGLIA_RICHIAMO_1
               and f["2_spostamento_del_punteggio_top1"]["p99"] <= SOGLIA_SPOSTAMENTO_P99)
        tre = f["3_richiamo_con_ricodifica"]["10"] >= SOGLIA_RICHIAMO_10
        esiti[nome] = "regge senza ricodifica" if uno and due else "regge con la ricodifica" if tre else "non regge"
    return esiti


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


def allinea_al_riferimento(ids: list[str], testi: list[str], vettori: np.ndarray,
                           ids_riferimento: list[str]) -> tuple[list[str], list[str], np.ndarray]:
    """The rows of a frozen reference, in its order: a run that resumes measures the SAME corpus as the run
    that froze it, even if facts were written in between. A fact of the reference that is gone stops the run."""
    posizione = {fatto: k for k, fatto in enumerate(ids)}
    mancanti = [fatto for fatto in ids_riferimento if fatto not in posizione]
    if mancanti:
        raise RuntimeError(f"{len(mancanti)} fatti del riferimento non sono più nel corpus: il riferimento va rifatto")
    scelti = [posizione[fatto] for fatto in ids_riferimento]
    return list(ids_riferimento), [testi[k] for k in scelti], vettori[scelti]


def richiamo_senza_se_stesso(sim_rif, sim_alt, se_stessi, k: int) -> float:
    """recall@k when every query is a fact of the corpus: its own column is left out of both rows."""
    sim_rif = np.array(sim_rif, dtype=np.float64, copy=True)
    sim_alt = np.array(sim_alt, dtype=np.float64, copy=True)
    righe = np.arange(len(se_stessi))
    sim_rif[righe, se_stessi] = -np.inf
    sim_alt[righe, se_stessi] = -np.inf
    return esporta_onnx.richiamo_a_k(sim_rif, sim_alt, k)


def _passo(messaggio: str) -> None:
    """Where the run is, with the time: a run cut by its cap must say where it was (30/09: it did not)."""
    print(f"[{time.strftime('%H:%M:%S')}] {messaggio}", flush=True)


def vettori_onnx(file_onnx: Path, testi: list[str], tok, thread: int, lotto: int = 32) -> np.ndarray:
    """The vectors of an ONNX file, in the order of the texts (encoded by length, to pad little)."""
    import onnxruntime as ort

    opzioni = ort.SessionOptions()
    opzioni.intra_op_num_threads = thread
    sessione = ort.InferenceSession(str(file_onnx), sess_options=opzioni, providers=["CPUExecutionProvider"])
    ordine = np.argsort([len(t) for t in testi], kind="stable")
    uscita: np.ndarray | None = None
    for i in range(0, len(testi), lotto):
        if i and i % 2048 == 0:
            _passo(f"  {file_onnx.name}: {i} testi su {len(testi)}")
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


def esegui(store: Path, file_onnx: list[Path], campione: int, controllo: int, ks: list[int], seme: int,
           thread: int, uscita: Path) -> dict:
    """The reference (the control and the fp32 queries) is computed once; then every ONNX file is measured
    on the same sample, and the numbers are written after each file, so a cut turn keeps what it measured."""
    import torch
    from sentence_transformers import SentenceTransformer

    inizio = time.perf_counter()
    torch.set_num_threads(thread)
    cartella = file_onnx[0].parent
    if any(f.parent != cartella for f in file_onnx):
        raise ValueError("the ONNX files must come from one export folder (one manifest, one tokenizer)")
    manifesto = json.loads((cartella / "manifesto.json").read_text(encoding="utf-8"))
    modello = manifesto["modello"]
    st = SentenceTransformer(modello, local_files_only=True, device="cpu")
    # sentence-transformers 5.4 renamed it; the product accepts older versions too
    dimensione = int((getattr(st, "get_embedding_dimension", None) or st.get_sentence_embedding_dimension)())
    ids, testi, memorizzati = leggi_corpus(store, modello, dimensione)
    # a run cut by its cap resumes from here: the frozen ids (the same corpus) and the fp32 reference
    riferimento = uscita.with_name(uscita.stem + ".riferimento.npz")
    salvato = np.load(riferimento, allow_pickle=False) if riferimento.exists() else None
    if salvato is not None:
        if (int(salvato["seme"]), int(salvato["campione"]), int(salvato["controllo"])) != (seme, campione, controllo):
            raise RuntimeError(f"{riferimento.name} ha altri seme, campione o controllo: cancellalo o usa gli stessi")
        ids, testi, memorizzati = allinea_al_riferimento(ids, testi, memorizzati, [str(x) for x in salvato["ids"]])
    n = len(ids)
    lunghezze = np.array([len(t) for t in testi])
    _passo(f"corpus: {n} righe{' (riferimento ripreso)' if salvato is not None else ''}, caratteri mediani "
           f"{int(np.median(lunghezze))}, oltre 1000 caratteri {int((lunghezze > 1000).sum())}; {thread} thread")
    rng = np.random.default_rng(seme)
    domande_idx = np.sort(rng.choice(n, size=min(campione, n), replace=False))
    passaggi = [f"passage: {t}" for t in testi]
    domande = [f"query: {testi[i]}" for i in domande_idx]

    # C. the control: the product's fp32 encode against what the product stored
    scelti = domande_idx[:controllo]
    if salvato is not None:
        fp32_controllo, q_fp32 = salvato["fp32_controllo"], salvato["q_fp32"]
    else:
        fp32_controllo = st.encode([passaggi[i] for i in scelti], normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False)
        q_fp32 = st.encode(domande, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        np.savez(riferimento, ids=np.array(ids), seme=seme, campione=campione, controllo=controllo,
                 fp32_controllo=fp32_controllo, q_fp32=q_fp32)
    c_controllo = esporta_onnx.coseni(fp32_controllo, memorizzati[scelti])
    _passo(f"controllo: {len(scelti)} fatti, coseno minimo {c_controllo.min():.6f}; domande fp32: {len(domande)}")
    tok = esporta_onnx._tokenizzatore(cartella / "tokenizer.json", manifesto["lunghezza_massima"],
                                      manifesto["pad_id"], manifesto["pad_token"])
    numeri: dict = {
        "modello": modello,
        "store": {"righe_lette": n, "dimensione": dimensione, "filtro": "embedding_model = modello, "
                  "length(embedding) = 4 x dimensione, superseded_by IS NULL"},
        "seme": seme, "domande": len(domande), "k": ks, "thread": thread, "versioni": esporta_onnx.versioni(),
        "C_controllo_fp32_contro_memorizzati": {**_quantili(c_controllo),
                                                "sotto_0_9999": int((c_controllo < 0.9999).sum())},
        "riferimento_s": round(time.perf_counter() - inizio, 1), "riferimento_ripreso": salvato is not None,
        "per_file": {},
    }
    uscita.write_text(json.dumps(numeri, ensure_ascii=False, indent=2), encoding="utf-8")  # the control, at least
    for file in file_onnx:
        partenza = time.perf_counter()
        impronta = esporta_onnx.sha256(file)
        vettori_salvati = uscita.with_name(f"{uscita.stem}.{file.stem}.npz")
        dal_disco = None
        if vettori_salvati.exists():
            dal_disco = np.load(vettori_salvati, allow_pickle=False)
            if str(dal_disco["sha256"]) != impronta or len(dal_disco["onnx_passaggi"]) != n:
                dal_disco = None  # another file or another corpus: encode again
        if dal_disco is not None:
            onnx_passaggi, q_onnx = dal_disco["onnx_passaggi"], dal_disco["q_onnx"]
            _passo(f"{file.name}: vettori ripresi da {vettori_salvati.name}")
        else:
            # 1. the ONNX passage vector of every fact; 2. and 3. the same queries, by the ONNX
            onnx_passaggi = vettori_onnx(file, passaggi, tok, thread)
            _passo(f"{file.name}: {n} passaggi in {time.perf_counter() - partenza:.0f} s")
            q_onnx = vettori_onnx(file, domande, tok, thread)
            np.savez(vettori_salvati, sha256=impronta, onnx_passaggi=onnx_passaggi, q_onnx=q_onnx)
        c_passaggi = esporta_onnx.coseni(onnx_passaggi, memorizzati)
        senza, spostamenti = _confronto_per_blocchi(q_fp32, memorizzati, q_onnx, memorizzati, domande_idx, ks)
        con, _ = _confronto_per_blocchi(q_fp32, memorizzati, q_onnx, onnx_passaggi, domande_idx, ks)
        _passo(f"{file.name}: finito in {time.perf_counter() - partenza:.0f} s")
        assoluti = np.abs(spostamenti)
        numeri["per_file"][file.name] = {
            "sha256": impronta, "vettori_ripresi": dal_disco is not None,
            "1_coseno_onnx_contro_memorizzati": _quantili(c_passaggi),
            "2_richiamo_senza_ricodifica": {str(k): v for k, v in senza.items()},
            "2_spostamento_del_punteggio_top1": {"mediano": float(np.median(assoluti)),
                                                 "p99": float(np.quantile(assoluti, 0.99)),
                                                 "massimo": float(assoluti.max()),
                                                 "medio_con_segno": float(spostamenti.mean())},
            "3_richiamo_con_ricodifica": {str(k): v for k, v in con.items()},
            "durata_s": round(time.perf_counter() - partenza, 1),
        }
        numeri["durata_s"] = round(time.perf_counter() - inizio, 1)
        # the numbers first: a defect of the verdict must not cost the measurement
        uscita.write_text(json.dumps(numeri, ensure_ascii=False, indent=2), encoding="utf-8")
        numeri["verdetto"] = verdetto(numeri)
        uscita.write_text(json.dumps(numeri, ensure_ascii=False, indent=2), encoding="utf-8")
    return numeri


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", type=Path, required=True, help="the product's semantic.db, opened read-only")
    parser.add_argument("--onnx", type=Path, required=True, nargs="+",
                        help="ONNX files of one esporta_onnx.py folder, measured in this order")
    parser.add_argument("--uscita", type=Path, required=True, help="where the numbers go (JSON)")
    parser.add_argument("--campione", type=int, default=2000, help="facts used as queries")
    parser.add_argument("--controllo", type=int, default=200, help="facts re-encoded fp32 for the control")
    parser.add_argument("--k", default="1,5,10")
    parser.add_argument("--seme", type=int, default=20260930)
    parser.add_argument("--thread", type=int, default=4, help="the product's thread budget")
    args = parser.parse_args(argv)
    numeri = esegui(args.store, args.onnx, args.campione, args.controllo,
                    [int(k) for k in args.k.split(",")], args.seme, args.thread, args.uscita)
    print(json.dumps(numeri, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
