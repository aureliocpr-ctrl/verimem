"""L'astensione, misurata DOVE IL PRODOTTO VIVE — cioè fuori da pytest.

La promessa: «*on a question it cannot support, it ABSTAINS ("I don't know")
instead of stitching a guess from weak matches*».

⚠️ PERCHÉ UNO SCRIPT E NON UN TEST, che è il punto di questo file.
`tests/conftest.py:121` installa `_stub_embedding_model` come
``@pytest.fixture(autouse=True)``: sotto pytest i vettori vengono dall'SHA-256
dei token (`:90`). L'astensione dipende dalla rilevanza, la rilevanza dai
coseni, e con coseni finti TUTTO risulta irrilevante. Misurato il 2026-08-29
(cella W2-38), stessa domanda e stesso corpus:

    fuori da pytest  ->  abstained=False SEMPRE, anche sulla targa inventata
    dentro pytest    ->  abstained=True  SEMPRE, anche sulle domande sostenute

I due regimi danno risposte OPPOSTE. Un presidio scritto in pytest avrebbe
registrato l'opposto della realtà, e sarebbe stato verde. Per questo il buco
che le celle W2-35/36 misurano NON si chiude aggiungendo test: si chiude con
un banco che gira fuori dalla suite. Questo.

⛔ SOLA LETTURA sul corpus: nessuna scrittura, nessuna env modificata.

Uso:  python scripts/banco_astensione_corpus_grande.py
      python scripts/banco_astensione_corpus_grande.py --min-relevance auto
Esce 0 se il banco ha potuto misurare, 2 se il corpus non c'è. L'esito della
PROMESSA sta nella riga di sintesi, non nell'exit code: questo è un banco, non
un cancello.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys
import time

#: ⚠️ NON `CONFIG.semantic_db`: sarebbe giusto qui (lo script gira fuori da
#: pytest), ma tenere il percorso esplicito rende il banco leggibile e uguale a
#: sé stesso anche se qualcuno lo lancia con le env di un altro store.
CORPUS = pathlib.Path.home() / ".engram" / "semantic" / "semantic.db"

#: ⛔ ENTRAMBE LE POPOLAZIONI, che è ciò che rende il banco informativo.
#: Sui soli "non sostenute" un prodotto che si astiene sempre sembrerebbe
#: perfetto; sulle sole "sostenute", uno che non si astiene mai.
NON_SOSTENUTE = [
    "qual e' il numero di targa dell'automobile di Aurelio?",
    "quale versione di Kubernetes usa il cluster di produzione di OnlyPaws?",
    "qual e' il codice IBAN del conto corrente aziendale?",
]
SOSTENUTE = [
    "che cos'e' il moat di verimem?",
    "che cos'e' quarantined_by?",
    "che cosa fa il gate anti-confabulazione?",
]


def _quanti_fatti() -> int | None:
    try:
        con = sqlite3.connect(f"file:{CORPUS}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        con.close()
        return int(n)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-relevance", default=None,
                    help="passato a trust_report: un float, oppure 'auto'")
    args = ap.parse_args()

    n_fatti = _quanti_fatti()
    if n_fatti is None:
        print(f"  corpus non leggibile in {CORPUS} — niente da misurare")
        return 2

    mr = args.min_relevance
    if mr is not None and mr != "auto":
        mr = float(mr)
    kw = {} if mr is None else {"min_relevance": mr}

    from verimem.client import Memory
    m = Memory(path=str(CORPUS))

    print(f"  REGIME: corpus {CORPUS} · {n_fatti} fatti · sola lettura · "
          f"min_relevance={mr!r} · {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {'domanda':56} {'abstained':>10} {'n_facts':>8}")
    esiti: dict[str, list[bool]] = {"non_sostenute": [], "sostenute": []}
    for etichetta, domande in (("non_sostenute", NON_SOSTENUTE),
                               ("sostenute", SOSTENUTE)):
        for q in domande:
            rep = m.trust_report(q, **kw)
            rep = rep if isinstance(rep, dict) else getattr(rep, "__dict__", {})
            a = rep.get("abstained")
            esiti[etichetta].append(a is True)
            print(f"  [{etichetta[:3]}] {q[:50]:50} {str(a):>10} "
                  f"{str(rep.get('n_facts')):>8}")

    ast_no = sum(esiti["non_sostenute"])
    ast_si = sum(esiti["sostenute"])
    tot_no, tot_si = len(NON_SOSTENUTE), len(SOSTENUTE)
    # ⚠️ LA RIGA DI SINTESI, e il banco la stampa DA SÉ: contare le righe a mano
    # è come ci si sbaglia. Le due metà vanno lette INSIEME — l'astensione su
    # tutto è inutile quanto l'astensione su niente.
    print(f"\n  SINTESI  si astiene su {ast_no}/{tot_no} NON sostenute "
          f"(atteso: {tot_no}/{tot_no})  ·  su {ast_si}/{tot_si} sostenute "
          f"(atteso: 0/{tot_si})")
    if ast_no == tot_no and ast_si == 0:
        print("  ⇒ LA PROMESSA REGGE su questo corpus")
    elif ast_no == 0:
        print("  ⇒ LA PROMESSA NON REGGE: non si astiene mai, nemmeno su una "
              "domanda inventata")
    elif ast_si == tot_si:
        print("  ⇒ SOVRA-ASTENSIONE: si astiene anche su cio' che il corpus "
              "sostiene — il difetto opposto, altrettanto inutile")
    else:
        print("  ⇒ PARZIALE: leggere le due colonne, non il totale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
