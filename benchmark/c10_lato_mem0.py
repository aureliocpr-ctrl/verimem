r"""C10, LATO CONCORRENTE — quanto trattiene mem0, MISURATO e non assunto.

Gira in `.venv-mem0bench`, che NON ha `verimem` installato: per questo e' un file
separato dal lato nostro. Nessuna chiave, nessuna rete verso terzi — embedder e5
locale (lo stesso modello che usiamo noi) e `infer=False`, quindi l'LLM di mem0
non viene mai chiamato.

    /c/Users/aurel/Code/HippoAgent/.venv-mem0bench/Scripts/python.exe \
        benchmark/c10_lato_mem0.py --n 100

PERCHE' ESISTE, dopo `LANT-69`. Nel referto avevo scritto che mem0 «per
costruzione non filtra»: su un corpus al 50% falso ne servirebbe il 50%.
**Quella frase e' un'assunzione, non una misura** — ed e' esattamente il tipo di
affermazione che passiamo le giornate a smontare quando la fa qualcun altro.
Qui la conto: scrivo i claim, poi guardo quanti ne restano nello store.

    trattenuti = scritti - presenti      ⇒ se e' 0, non ne trattiene nessuno,
                                           e il 50% diventa un numero MISURATO

⚠️ IL NODO METODOLOGICO, ed e' la ragione della forma di questo banco.

Il primo protocollo confrontava la nostra AMMISSIONE (quanti falsi passano il
gate) col RETRIEVAL di mem0 (cosa torna a una query). **Sono due livelli
diversi**, e avrebbe dato un vantaggio automatico a noi — il difetto che
smontiamo negli altri: *il livello a cui misuri decide il verdetto*. ⇒ La misura
principale qui e' l'AMMISSIONE, la stessa grandezza del lato nostro.

⛔ LIMITE DICHIARATO sul dato secondario (il retrieval). Su `truthfulqa` molti
claim veri sono risposte secche — «Yes», «Cardiff University» — che **nessun
retrieval per similarita' puo' ragionevolmente recuperare da una domanda**.
Misurarlo li' punirebbe entrambi i sistemi per una proprieta' del DATASET, non
per una loro debolezza. Lo stampo come dato secondario e non ci costruisco sopra
nessuna conclusione.

FAIR PLAY, dichiarato. Interrogo `vector_store.search` direttamente invece di
`Memory.search`: il runner di `competitor_probe_mem0.py` documenta un bug di
ranking in `Memory.search`, e passare da li' **handicapperebbe il concorrente**.
Prefisso `query: ` perche' e5 lo richiede: ometterlo lo penalizzerebbe su una
convenzione del MODELLO, non su una sua mancanza. Il numero deve reggere anche
se lo legge chi fa mem0.

E la differenza va detta per quello che e': **mem0 non promette di filtrare**.
Se non trattiene nulla non e' scritto male — e' un prodotto con un'altra
promessa. Il nostro filtro si paga in veri persi (29,0%, `LANT-69`), ed e' la
faccia da pubblicare accanto.

NOTA DI CANTIERE. La versione precedente di questo file e' stata riscritta da
capo invece che rattoppata: tre `\n` dentro un heredoc bash erano diventati a
capo veri, spezzando due stringhe e un commento. Il codice era rotto da quando
l'avevo scritto e non me ne ero accorta perche' non l'avevo ESEGUITO. Il rimedio
non e' scrivere meglio l'heredoc: e' non passare dalla shell per il codice.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
DATI = RADICE / "benchmark" / "data" / "external" / "truthfulqa_pairs_heldout.jsonl"


def build_memory(workdir: str, collection: str):
    """Copiata verbatim da `competitor_probe_mem0.py` — stesso identico
    apparecchio, cosi' il confronto non dipende da come l'ho montato io."""
    from mem0 import Memory
    config = {
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "intfloat/multilingual-e5-base"}},
        "vector_store": {"provider": "chroma",
                         "config": {"collection_name": collection, "path": workdir}},
    }
    return Memory.from_config(config)


def quanti_dentro(mem) -> int:
    """Quanti record ci sono davvero nello store. -1 se la firma non lo espone.

    ⚠️ **NON si usa `vector_store.list()`**: la sua firma e'
    `list(filters=None, top_k: int = 100)` — **un tetto di 100 come DEFAULT**.
    Con 200 claim scritti tornava 100, e il banco concludeva «mem0 TRATTIENE il
    50%». **Era il misuratore che si fermava, e sarebbe stata un'accusa falsa a
    un concorrente** — pubblicata dentro il documento che conta le figure di
    merda. Misurato il 30/08: 0/10 trattenuti su 10 claim, 100/200 su 200. **Due
    campioni incoerenti sono l'unica ragione per cui l'ho visto.**

    ⇒ 🔑 **Un limite di default nel misuratore e' invisibile finche' il campione
    non lo SUPERA.** Un campione piccolo non lo rivela: da' il numero giusto per
    caso. `collection.count()` non ha tetto ed e' la porta corretta.
    """
    try:
        return mem.vector_store.collection.count()
    except Exception:
        pass
    try:  # nomi diversi fra le versioni
        return mem.vector_store.col.count()
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=100, help="quanti ITEM (2 claim l'uno)")
    ap.add_argument("--out", default="benchmark/results/c10_lato_mem0.json")
    a = ap.parse_args()

    with open(DATI, encoding="utf-8") as f:
        righe = [json.loads(r) for r in f if r.strip()][: 2 * a.n]

    # `truthfulqa` non ha un campo `question`: la domanda e' la PRIMA riga di
    # `source`, nel formato "Q: <domanda>" (verificato: 200/200 righe del dev).
    for it in righe:
        if str(it.get("source", "")).lstrip().startswith("Q:"):
            it["question"] = it["source"].lstrip()[2:].splitlines()[0].strip()

    mem = build_memory(tempfile.mkdtemp(prefix="ws7_c10_mem0_"), "c10")

    etichetta_di: dict[str, str] = {}
    for i, it in enumerate(righe):
        claim = it["claim"].strip()
        etichetta_di[claim] = "vero" if it["label"] == 1 else "falso"
        mem.add(claim, user_id="c10", infer=False)
        if (i + 1) % 40 == 0:
            print(f"    scritti ...{i + 1}/{len(righe)} claim", flush=True)

    # ═══ MISURA PRINCIPALE — quanti ne trattiene ═══
    scritti = len(righe)
    dentro = quanti_dentro(mem)
    #: i falsi si contano sulle RIGHE, non su `etichetta_di`: quel dict e'
    #: indicizzato per testo e **fonde i claim identici**. Misurato: 200 righe
    #: -> 191 chiavi, e i falsi passavano da 100 a 97, cioe' dal 50,0% al 48,5%.
    #: I duplicati sono claim senza contesto — «I have no comment» sei volte,
    #: «Trump» tre — che sono anche la ragione per cui il retrieval qui sotto
    #: resta un dato secondario: se il top-1 torna «I have no comment», la sua
    #: etichetta non e' la risposta a QUELLA domanda.
    falsi = sum(1 for x in righe if x["label"] == 0)
    claim_distinti = len(etichetta_di)
    print("")
    print("  === AMMISSIONE — mem0 2.0.4, infer=False, e5 locale ===")
    print(f"  claim scritti:          {scritti:4}")
    print(f"  presenti nello store:   {dentro:4}"
          + ("   (la firma non lo espone)" if dentro < 0 else ""))
    trattenuti = (scritti - dentro) if dentro >= 0 else None
    if trattenuti is not None:
        print(f"  => TRATTENUTI:          {trattenuti:4}/{scritti} = "
              f"{100 * trattenuti / max(1, scritti):5.1f}%   <- MISURATO, non assunto")
        if trattenuti <= 0:
            print(f"  => non ne trattiene nessuno: su un corpus con {falsi} falsi "
                  f"su {scritti}, ne serve {100 * falsi / max(1, scritti):.1f}%")
        else:
            print("  => ne trattiene qualcuno: va guardato QUALI, il numero da solo non basta")

    # ═══ dato SECONDARIO — retrieval, col limite dichiarato sopra ═══
    visti: set[str] = set()
    primo_falso = primo_vero = primo_altro = 0
    for it in righe:
        d = it.get("question")
        if not d or d in visti:
            continue
        visti.add(d)
        qv = mem.embedding_model.embed("query: " + d, "search")
        hit = mem.vector_store.search(query="query: " + d, vectors=qv, top_k=1,
                                      filters={"user_id": "c10"})
        testo = ""
        if hit:
            h = hit[0]
            p = getattr(h, "payload", None) or (h.get("payload") if isinstance(h, dict) else {}) or {}
            testo = (p.get("data") or p.get("memory") or "").strip()
        et = etichetta_di.get(testo)
        primo_falso += et == "falso"
        primo_vero += et == "vero"
        primo_altro += et is None

    tot = max(1, len(visti))
    print("")
    print(f"  --- dato SECONDARIO: retrieval su {len(visti)} domande distinte ---")
    print(f"      primo risultato FALSO {primo_falso:4} = {100 * primo_falso / tot:5.1f}%")
    print(f"      primo risultato VERO  {primo_vero:4} = {100 * primo_vero / tot:5.1f}%")
    print(f"      non riconosciuto      {primo_altro:4} = {100 * primo_altro / tot:5.1f}%")
    print("      (NON e' una conclusione: su questa popolazione molti claim veri")
    print("       sono risposte secche che nessun retrieval recupera da una domanda)")

    corpo = {"sistema": "mem0 2.0.4 (e5 locale, infer=False, zero-API)",
             "popolazione": DATI.name,
             "claim_scritti": scritti, "presenti_nello_store": dentro,
             "trattenuti": trattenuti, "falsi_nel_corpus": falsi,
             "claim_distinti": claim_distinti,
             "retrieval_domande": len(visti), "retrieval_primo_falso": primo_falso,
             "retrieval_primo_vero": primo_vero, "retrieval_non_riconosciuto": primo_altro,
             "nota": "il retrieval e' un dato secondario col limite dichiarato nel docstring"}
    out = RADICE / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpo, indent=2), encoding="utf-8")
    print("")
    print(f"  scritto {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
