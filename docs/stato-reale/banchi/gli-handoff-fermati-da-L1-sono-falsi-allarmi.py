"""GLI HANDOFF FERMATI DA `L1` SONO FALSI ALLARMI? — la specifica, sulla popolazione vera.

Un'altra istanza ha misurato che **meta' della quarantena e' `handoff/`** e che la
causa e' la famiglia `L1` (**`L1.13` su 68 di 80**). Quella e' la CAUSA. Questo
banco fa il passo dopo, che e' il fronte assegnato a me: **la SPECIFICA** —
`L1` *deve* fermare quei fatti, oppure li ferma per sbaglio?

⚖️ **Non e' una domanda retorica, e la risposta non e' ovvia in nessuna delle due
direzioni.** Un handoff dice tipicamente *«ho completato X, la suite e' verde»*:
e' **letteralmente** un self-claim di completamento, cioe' esattamente cio' che
`L1.13` esiste per fermare. Ma se lo ferma sempre, **il prodotto non puo'
ricordare il proprio lavoro fra una sessione e l'altra** — e quella e' una
promessa che il prodotto fa.

COSA MISURO, e NON e' un'attribuzione: `quarantined_by` e' vuoto sul 61,1% della
coda (misurato in `W7-50`), quindi **non posso dire chi ha fermato cosa**. Faccio
una **RIVALUTAZIONE**: prendo gli handoff quarantinati e chiedo al detector di
oggi, **con la fonte che quel fatto ha conservato**, se li fermerebbe.

LE TRE CLASSI, e ognuna vuole una decisione diversa:
  A. **senza span** -> nessuna fonte conservata: il detector ferma, e per la
     specifica attuale **ha ragione**. La domanda diventa: perche' scriviamo
     handoff senza fonte?
  B. **con span, e oggi PASSA** -> 🔴 **falso allarme**: la cura del 28/08 lo
     perdonerebbe, ma il fatto e' in quarantena. O e' stato scritto prima della
     cura, o e' stato fermato da altro.
  C. **con span, e oggi FERMA ancora** -> il participio non e' nella fonte: o e'
     un self-claim vero, o e' **la famiglia che TRADUCE** (`W7-50`).

CONTROLLI CHE POSSONO FALLIRE:
 (1) se non ci sono handoff quarantinati, il banco non ha oggetto e lo dico.
 (2) **controllo positivo**: un self-claim nudo costruito da me DEVE essere
     fermato. Se passa, il detector non e' acceso e nessun conteggio vale.
 (3) **controllo negativo**: lo stesso claim con una fonte che porta il
     participio DEVE passare. Se non passa, sto misurando un detector rotto.

    python -u docs/stato-reale/banchi/gli-handoff-fermati-da-L1-sono-falsi-allarmi.py
"""

from __future__ import annotations

import collections
import sqlite3
import sys

NUDO = "La migrazione e' completata e tutti i test passano."
CON_FONTE = "Il refactoring e' finito."
FONTE_CHE_SOSTIENE = (
    "Verbale del 12 marzo: il refactoring del modulo di pagamento e' finito "
    "e consegnato al collaudo."
)


def main() -> int:
    try:
        from verimem.config import CONFIG
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim as ferma,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (2): il detector e' ACCESO? (self-claim nudo)")
    if ferma(proposition=NUDO, verified_by=None, source=None) is None:
        print("     CADUTO - un self-claim nudo passa: il detector non e' acceso")
        print("     e nessun conteggio di questo banco vale.")
        return 1
    print("     retto - il self-claim nudo e' fermato")

    print("\n  -- CONTROLLO (3): e PERDONA quando la fonte porta il participio?")
    if ferma(proposition=CON_FONTE, verified_by=None,
             source=FONTE_CHE_SOSTIENE) is not None:
        print("     CADUTO - ferma anche con la fonte che lo sostiene: la cura")
        print("     del 28/08 non e' attiva in questa copia, e la classe B non")
        print("     sarebbe distinguibile.")
        return 1
    print("     retto - con la fonte che porta il participio, passa")

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = list(con.execute(
        "SELECT proposition, topic, grounding_span, grounding_score "
        "FROM facts WHERE status='quarantined' AND superseded_by IS NULL"))
    hand = [r for r in righe if (r[1] or "").strip().lower().startswith("handoff")]
    print(f"\n  db: {CONFIG.semantic_db}")
    print(f"  quarantinati vivi: {len(righe)}   con topic handoff: {len(hand)}"
          f"   ({100.0 * len(hand) / max(1, len(righe)):.1f}%)")
    if not hand:
        print("  NON RIUSCITO: nessun handoff quarantinato, il banco non ha oggetto.")
        return 1

    d = collections.Counter()
    esempi_b, esempi_c = [], []
    for prop, _t, span, _gs in hand:
        s = (span or "").strip()
        if not s:
            d["A senza span"] += 1
            continue
        if ferma(proposition=prop, verified_by=None, source=s) is None:
            d["B con span, oggi PASSA"] += 1
            if len(esempi_b) < 3:
                esempi_b.append((prop, s))
        else:
            d["C con span, oggi FERMA"] += 1
            if len(esempi_c) < 3:
                esempi_c.append((prop, s))

    print(f"\n  == LA RIVALUTAZIONE, su {len(hand)} handoff quarantinati")
    for k, v in d.most_common():
        print(f"     {v:>5}  ({100.0 * v / len(hand):>5.1f}%)  {k}")

    for nome, ess in (("B — oggi PASSEREBBERO (falsi allarmi)", esempi_b),
                      ("C — oggi sono ancora fermati", esempi_c)):
        if ess:
            print(f"\n  == {nome}")
            for prop, s in ess:
                print(f"     claim: {prop[:88]}")
                print(f"     span : {s[:88].replace(chr(10), ' ')}")
                print()

    print("  -- LA SPECIFICA CHE NE ESCE, e le tre classi vogliono cure diverse")
    a, b, c = (d["A senza span"], d["B con span, oggi PASSA"],
               d["C con span, oggi FERMA"])
    print(f"     A={a}  B={b}  C={c}")
    if a and a >= max(b, c):
        print("     ⇒ IL PESO STA IN A: gli handoff arrivano SENZA FONTE, quindi")
        print("     `L1` fa esattamente il suo mestiere e nessuna cura di layer li")
        print("     salverebbe. 🔑 La domanda non e' «come perdonarli» ma **perche'")
        print("     scriviamo la nostra continuita' senza allegarne l'evidenza**.")
    if b:
        print(f"     ⇒ 🔴 {b} sono FALSI ALLARMI oggi: hanno la fonte che li")
        print("     sostiene e il detector attuale li perdonerebbe. Sono scritti")
        print("     PRIMA della cura, oppure fermati da un altro layer.")
        print("     ⚠️ Distinguerlo richiede una data, e questo banco NON la guarda.")
    if c:
        print(f"     ⇒ {c} restano fermati con la loro fonte: o sono self-claim")
        print("     veri, o sono la famiglia che TRADUCE (W7-50). Il banco NON")
        print("     separa i due casi.")

    print("\n  ⚠️ COSA NON DICE: non attribuisce la quarantena a `L1` — il campo")
    print("  `quarantined_by` e' vuoto sul 61,1% della coda. E' una RIVALUTAZIONE")
    print("  col detector di oggi, non una ricostruzione di cosa accadde allora.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
