"""Un giudice candidato, hallucination-guard in ONNX, con la firma del giudice del prodotto.

Il giudice del moat è uno ``Scorer`` (``verimem/local_grounding.py``): una lista di coppie
(fonte, affermazione) in ingresso, una lista di punteggi in [0, 100] in uscita. Questo
modulo costruisce lo stesso oggetto sopra i classificatori hallucination-guard
(Horizon-Labs, Apache-2.0, base mmBERT, ``id2label`` = {0: UNSUPPORTED, 1: SUPPORTED}).
Il candidato entra così NELLO STESSO PUNTO del giudice attuale, e la selezione dello span,
la finestra, le soglie e la fascia del prodotto restano quelle di sempre::

    from verimem.local_grounding import set_local_judge
    set_local_judge(make_guard_judge(cartella_del_modello))

Serve a MISURARE un candidato sugli stessi banchi del giudice attuale; non è un giudice
del prodotto.

Il punteggio è P(SUPPORTED) × 100, cioè il softmax dei due logit. È la regola della
valutazione pubblicata dagli autori (``code/ground/evaluate_ground.py``):
``tok(contesto, risposta, truncation="longest_first", max_length=2048)``, poi
``softmax(logits)[:, indice di SUPPORTED]``. Le scelte sono tre, tutte prese da lì:

- l'ordine della coppia: text = la fonte, text_pair = l'affermazione;
- la finestra è di 2048 token, il ``--max_len`` di default della loro valutazione. La fonte
  arriva già ridotta dal selettore dello span del prodotto;
- gli ingressi del grafo sono ``input_ids`` e ``attention_mask``, come in
  ``code/train/export_onnx.py``. I nomi però si leggono dalla sessione, non si assumono.

Le dipendenze sono solo ``onnxruntime``, ``tokenizers`` e ``numpy``: niente torch e niente
transformers. È la forma che il giudice avrebbe se il prodotto lo adottasse, e la memoria
del candidato si misura su questa.

Il controllo positivo: lo scorer conta le coppie che ha giudicato
(``scorer.coppie_giudicate``). Se chi lo installa legge 0 dopo un banco, il giudizio l'ha
dato un altro giudice.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from verimem.local_grounding import LocalGroundingJudge

#: il file del modello quantizzato int8 degli autori, nella disposizione di transformers.js
FILE_ONNX_INT8 = "onnx/model_quantized.onnx"

#: il ``--max_len`` di default di ``code/ground/evaluate_ground.py``
FINESTRA_DEGLI_AUTORI = 2048


def _indice_di_supported(cartella: Path) -> tuple[int, dict[int, str]]:
    config = json.loads((cartella / "config.json").read_text(encoding="utf-8"))
    etichette = {int(k): str(v).upper() for k, v in config["id2label"].items()}
    indici = [i for i, v in etichette.items() if v == "SUPPORTED"]
    # niente ripiego sull'indice 1: un modello con etichette diverse deve fermarsi qui,
    # non essere misurato al contrario
    if len(indici) != 1:
        raise ValueError(f"{cartella}: id2label senza un SUPPORTED unico: {etichette}")
    return indici[0], etichette


def make_guard_scorer(cartella: str | Path, *, file_onnx: str = FILE_ONNX_INT8,
                      max_length: int = FINESTRA_DEGLI_AUTORI, batch_size: int = 8,
                      thread: int | None = None) -> Callable[[list[tuple[str, str]]], list[float]]:
    """Lo ``Scorer`` di hallucination-guard: (fonte, affermazione) -> P(SUPPORTED) x 100.

    CPU soltanto (``CPUExecutionProvider``). ``thread`` fissa ``intra_op_num_threads``;
    ``None`` lascia il default di ONNX Runtime, e ``scorer.descrizione`` dice cosa è
    stato usato davvero.
    """
    import numpy as np
    import onnxruntime as ort
    import tokenizers
    from tokenizers import Tokenizer

    cartella = Path(cartella)
    indice, etichette = _indice_di_supported(cartella)

    tok = Tokenizer.from_file(str(cartella / "tokenizer.json"))
    tok.no_padding()
    tok.enable_truncation(max_length=max_length, strategy="longest_first")
    config_tok = json.loads((cartella / "tokenizer_config.json").read_text(encoding="utf-8"))
    pad = tok.token_to_id(config_tok["pad_token"])
    if pad is None:
        raise ValueError(f"{cartella}: il pad_token {config_tok['pad_token']!r} non è nel vocabolario")
    # la COPPIA deve arrivare al modello come due sequenze: un post-processor senza il
    # modello per le coppie le incollerebbe, e il giudice leggerebbe un testo solo
    prova = tok.encode("fonte di prova", "affermazione di prova")
    if not {0, 1} <= {s for s in prova.sequence_ids if s is not None}:
        raise ValueError(f"{cartella}: il tokenizzatore non codifica la coppia come due sequenze")

    opzioni = ort.SessionOptions()
    if thread:
        opzioni.intra_op_num_threads = int(thread)
    sessione = ort.InferenceSession(str(cartella / file_onnx), sess_options=opzioni,
                                    providers=["CPUExecutionProvider"])
    ingressi = [i.name for i in sessione.get_inputs()]
    if "input_ids" not in ingressi or not set(ingressi) <= {"input_ids", "attention_mask",
                                                            "token_type_ids"}:
        raise ValueError(f"{cartella / file_onnx}: ingressi del grafo inattesi: {ingressi}")
    uscita = sessione.get_outputs()[0].name

    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        punteggi: list[float] = []
        for i in range(0, len(batch), batch_size):
            pezzo = batch[i:i + batch_size]
            codifiche = tok.encode_batch([(fonte or "", affermazione or "")
                                          for fonte, affermazione in pezzo])
            lunghezza = max(len(c.ids) for c in codifiche)
            # riempimento a DESTRA con il pad del tokenizzatore, maschera a 0 sul riempimento:
            # la testa di ModernBERT fa la media sui soli token con maschera 1
            tensori = {nome: np.zeros((len(codifiche), lunghezza), dtype=np.int64)
                       for nome in ("input_ids", "attention_mask", "token_type_ids")}
            tensori["input_ids"].fill(pad)
            for riga, c in enumerate(codifiche):
                n = len(c.ids)
                tensori["input_ids"][riga, :n] = c.ids
                tensori["attention_mask"][riga, :n] = 1
                tensori["token_type_ids"][riga, :n] = c.type_ids
            logits = sessione.run([uscita], {nome: tensori[nome] for nome in ingressi})[0]
            if logits.shape != (len(pezzo), len(etichette)):
                raise ValueError(f"logit di forma {logits.shape}, attesa {(len(pezzo), len(etichette))}")
            logits = logits - logits.max(axis=1, keepdims=True)
            probabilita = np.exp(logits)
            probabilita /= probabilita.sum(axis=1, keepdims=True)
            punteggi.extend(float(p) * 100.0 for p in probabilita[:, indice])
            scorer.coppie_giudicate += len(pezzo)
        return punteggi

    scorer.coppie_giudicate = 0
    scorer.descrizione = {
        "modello": str(cartella / file_onnx),
        "byte": (cartella / file_onnx).stat().st_size,
        "provider": sessione.get_providers(),
        "ingressi": ingressi,
        "uscita": uscita,
        "indice_supported": indice,
        "finestra": max_length,
        "thread": opzioni.intra_op_num_threads,     # 0 = default di ONNX Runtime
        "onnxruntime": ort.__version__,
        "tokenizers": tokenizers.__version__,
    }
    return scorer


def make_guard_judge(cartella: str | Path, **opzioni: Any) -> LocalGroundingJudge:
    """Il candidato come ``LocalGroundingJudge``, pronto per ``set_local_judge``.

    La cartella del giudice è quella del candidato, così che la finestra del prodotto
    (``_entro_la_finestra``) conti i token con il SUO tokenizzatore e allo stesso limite.
    ``ENGRAM_LOCAL_GATE_MODEL`` batte l'argomento (``_resolve_model_dir``): se punta
    altrove, la finestra conterebbe con il tokenizzatore di un altro modello, e allora ci
    si ferma qui.
    """
    from verimem.local_grounding import LocalGroundingJudge

    cartella = Path(cartella)
    max_length = int(opzioni.get("max_length", FINESTRA_DEGLI_AUTORI))
    giudice = LocalGroundingJudge(model_dir=cartella, scorer=make_guard_scorer(cartella, **opzioni),
                                  max_length=max_length)
    if giudice.model_dir.resolve() != cartella.resolve():
        raise ValueError(f"il giudice legge {giudice.model_dir}, non {cartella}: "
                         "ENGRAM_LOCAL_GATE_MODEL punta a un altro modello")
    return giudice
