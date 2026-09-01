"""Quanti artefatti di benchmark si difendono da soli dal cattivo uso?

PERCHE'. Il 01/09 ho trovato due file dello STESSO repo che si comportano in
modo opposto (`LANT-148`, `LANT-149`):

  DESIGN-memory-ablation          «Nothing in here is a result»   protetto
  bench_with_without_hippo.json    nessuna avvertenza             si legge come
                                   «la memoria fa fallire il prodotto al 100%»

Il secondo NON e' sbagliato: e' un run col mock, dichiarato nel nome della
chiave (`raw|mock`). Ma chi apre il json e non il codice legge una misura che
non esiste. ⇒ La domanda generale: **quanti artefatti portano con se' il
proprio regime e il proprio limite, e quanti dipendono da un documento esterno?**

COSA CONTA COME «PROTETTO». Tre gradi, dichiarati perche' il confine e'
arbitrario:
  · REGIME   una chiave che dice COME e' stato prodotto (env, provider, modello,
             dataset, n) — permette di riprodurlo
  · LIMITE   una chiave che dice cosa NON prova (note, caveat, warning)
  · NUDO     ne' l'uno ne' l'altro: numeri e basta

⚠️ Il grado «REGIME» lo cerco per NOME DI CHIAVE, e un nome che non ho previsto
lo conto come assente: **sovrastima i nudi**. Stampo le chiavi dei nudi cosi'
il lettore vede se il mio elenco era corto (e' la lezione «stampa le chiavi
prima di contare»).
"""
import json
import sys
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
CARTELLE = [RADICE / "benchmark/results", RADICE / "data"]

#: ⚠️ la PRIMA versione di queste liste era MONOLINGUE, ed e' la classe ③ delle
#: cinque che pago piu' spesso. L'ho scoperto solo perche' il banco STAMPA le
#: chiavi dei nudi: `c10_lato_mem0.json` risultava nudo e ha `nota` e
#: `popolazione` — cioe' porta sia il limite sia il regime, in italiano.
#: Il confronto fra le due liste e' stampato in fondo: e' l'unico modo di
#: sapere quanto costava il difetto invece di dichiararlo curato.
REGIME_EN = {"dataset", "model", "embedding_model", "provider", "n",
             "n_questions", "k", "seed", "env", "config", "commit", "version",
             "backend", "embedding_dim", "protocol", "split"}
LIMITE_EN = {"metric_note", "note", "notes", "caveat", "caveats", "warning",
             "limits", "limitations", "disclaimer", "status"}
REGIME = REGIME_EN | {"popolazione", "modello", "regime", "sorgente", "fonte",
                      "corpus", "versione", "campione"}
LIMITE = LIMITE_EN | {"nota", "note_it", "limite", "limiti", "avvertenza",
                      "avvertenze", "cautela", "stato"}


def _chiavi(o) -> set:
    if isinstance(o, dict):
        return set(o)
    if isinstance(o, list) and o and isinstance(o[0], dict):
        return set(o[0])
    return set()


def main() -> int:
    conto, nudi = Counter(), []
    for cartella in CARTELLE:
        if not cartella.exists():
            continue
        for p in sorted(cartella.glob("*.json")):
            try:
                k = _chiavi(json.loads(p.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                conto["illeggibile"] += 1
                continue
            ha_lim = bool(k & LIMITE)
            ha_reg = bool(k & REGIME)
            if ha_lim and ha_reg:
                conto["regime + limite"] += 1
            elif ha_lim:
                conto["solo limite"] += 1
            elif ha_reg:
                conto["solo regime"] += 1
            else:
                conto["NUDO"] += 1
                nudi.append((p.name, sorted(k)[:6]))

    tot = sum(conto.values())
    print(f"  {tot} artefatti json in benchmark/results e data\n")
    for k, v in conto.most_common():
        print(f"     {v:>4}  {k}   ({100*v/max(1,tot):.1f}%)")

    print(f"\n  ⚠️ le chiavi dei NUDI, per farvi vedere se il mio elenco era corto:")
    for nome, k in nudi[:10]:
        print(f"     {nome[:44]:<46} {k}")
    if len(nudi) > 10:
        print(f"     … e altri {len(nudi)-10}")
    #: --- quanto costava la lista monolingue, misurato e non dichiarato ---
    solo_en = 0
    for cartella in CARTELLE:
        if not cartella.exists():
            continue
        for p in sorted(cartella.glob("*.json")):
            try:
                k = _chiavi(json.loads(p.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
            if not (k & LIMITE_EN) and not (k & REGIME_EN) and (
                    (k & LIMITE) or (k & REGIME)):
                solo_en += 1
    print(f"\n  🪞 artefatti che la lista SOLO INGLESE contava come nudi e che"
          f" non lo sono: {solo_en}")
    print("     (classe ③ «liste monolingue» — trovata perche' il banco stampa")
    print("      le chiavi invece di limitarsi a contarle)")

    print("\n  ⇒ un artefatto NUDO non e' sbagliato: e' leggibile solo da chi")
    print("    apre anche il codice. Il rimedio misurato costa QUATTRO PAROLE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
