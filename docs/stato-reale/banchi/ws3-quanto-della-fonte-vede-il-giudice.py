"""LIVELLO: lo store vivo in SOLA LETTURA — la colonna `grounding_span`, cioe' il
pezzo di fonte che il giudice ha effettivamente guardato quando ha ammesso il fatto.

Quanto della fonte vede il giudice? Serve al design del muro 1 (MAX sulle frasi
della fonte): se il giudice di oggi guarda gia' UNA frase, il MAX non e' un'idea
nuova — e' un meccanismo che sostituisce, o affianca, il focus a budget.

    python docs/stato-reale/banchi/ws3-quanto-della-fonte-vede-il-giudice.py

⚡ COSTO ZERO: `mode=ro`, nessun modello. Sotto i 10 s.

━━ DA DOVE VIENE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il design (docs/ricerca/2026-09-05-design-write-n-claim-atomici.md) dichiara M —
le frasi della fonte — NON MISURATO, «perche' le fonti non stanno nel corpus».
Vero a meta': la fonte intera non c'e', ma `grounding_span` conserva il
FRAMMENTO che il giudice ha guardato (client.py:762 lo salva dalla ricevuta del
gate; nasce in `LocalGroundingJudge.coppia`, che taglia la fonte a un budget in
CARATTERI letto da gate_config.json). Quindi da qui non si legge M, si legge
**quanto di M il giudice usa oggi** — che e' il numero che decide se il MAX del
design costa e serve.

━━ MISURATO il 05/09 alle 21:20, corpus vivo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    fatti vivi                         15.328
    con grounding_span non vuoto        7.755   (50,6%)
    frasi per span: media 1,57 · mediana 1 · max 14
    span di UNA frase                   5.391   (69,5%)
    span di >= 3 frasi                  1.089   (14,0%)
    caratteri per span: media 281 · mediana 316 · max 932 · >= 512: 1

⇒ Nel 69,5% dei casi il giudice ha visto UNA frase della fonte: il focus a
  budget fa gia' una selezione, per prossimita' di caratteri. Il MAX del design
  fa una selezione per PUNTEGGIO, su tutte le frasi. Sono due meccanismi per la
  stessa cosa, e il design deve dire come convivono (vincolo N10): il MAX
  DENTRO il budget non cambia niente nel 69,5% dei casi (una frase sola);
  fuori dal budget vede frasi che oggi il giudice non vede — che e' il
  guadagno sulla zavorra in testa (P-b del lead) e il costo in coppie.
⇒ Costo P-G, limite INFERIORE: M_visto = 1,57 frasi medie ⇒ N x M ≈ 2,03 x 1,57
  ≈ 3,2 coppie per scrittura composta con fonte, in un lotto: ~0,8x l'intero
  (banco P6c). M vero e' >= 1,57 e resta da misurare con fonti intere.

━━ COSA NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lo span e' la scelta del focus, non la fonte: il 30,5% di span multi-frase
dice che il budget in caratteri contiene piu' frasi, non che il giudice le
abbia pesate separatamente (le vede insieme: e' la condizione della zavorra).
E `grounding_span` e' popolato in meta' dei fatti vivi: l'altra meta' e' senza
fonte o precede la colonna (anti_confab_gate.py:2826 lo racconta).
"""
from __future__ import annotations

import re
import sqlite3
import statistics as st

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
_FRASI = re.compile(r"(?<=[.!?])\s+")


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tot = con.execute("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL").fetchone()[0]
        spans = [r[0] for r in con.execute(
            "SELECT grounding_span FROM facts WHERE superseded_by IS NULL "
            "AND grounding_span IS NOT NULL AND LENGTH(grounding_span) > 0")]
    finally:
        con.close()
    n = [len([f for f in _FRASI.split(s) if f.strip()]) or 1 for s in spans]
    lung = [len(s) for s in spans]
    uno = sum(1 for x in n if x == 1)
    tre = sum(1 for x in n if x >= 3)
    print("QUANTO DELLA FONTE VEDE IL GIUDICE (grounding_span, sola lettura)\n")
    print(f"  fatti vivi                      : {tot}")
    print(f"  con grounding_span non vuoto    : {len(spans)}  ({100 * len(spans) / tot:.1f}%)")
    print(f"  frasi per span                  : media {sum(n) / len(n):.2f} · mediana {st.median(n):.0f} · max {max(n)}")
    print(f"  span di UNA frase               : {uno}  ({100 * uno / len(n):.1f}%)")
    print(f"  span di >= 3 frasi              : {tre}  ({100 * tre / len(n):.1f}%)")
    print(f"  caratteri per span              : media {sum(lung) / len(lung):.0f} · mediana {st.median(lung):.0f}"
          f" · max {max(lung)} · >= 512: {sum(1 for x in lung if x >= 512)}")
    print(f"\n  ⇒ M_visto (limite inferiore di M) = {sum(n) / len(n):.2f} frasi;"
          f" con N = 2,03 unita' medie: ~{2.03 * sum(n) / len(n):.1f} coppie per scrittura composta con fonte.")


if __name__ == "__main__":
    main()
