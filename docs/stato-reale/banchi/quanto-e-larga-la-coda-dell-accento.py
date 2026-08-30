"""QUANTO E' LARGA LA CODA DELL'ACCENTO — `W7-75` ha visto la mediana, `W7-76` la coda.

Due celle mie, pubblicate a sei minuti di distanza, dicono cose che sembrano
opposte e non lo sono:

    `W7-75`  16 casi: mediana 0,004 · massimo 0,405 · rumore del giudice 0,0000
             ⇒ «il giudice e' insensibile all'ortografia»
    `W7-76`  2 casi:  55,361 → 3,779, delta **-51,582**
             ⇒ «l'accento ribalta un verdetto su un fatto VERO»

⇒ **Sono la stessa distribuzione vista in due punti**: il corpo e la coda. E
`W7-76` dichiara il proprio limite — *«due casi, ed e' lo stesso claim scritto
due volte: e' un'ESISTENZA, non una frequenza»*.

🎯 **Questo banco misura la FREQUENZA**: su **tutti** i fatti vivi con `e'` e
una fonte, quanto vale il delta e **quanti casi stanno nella coda**.

ATTESA DICHIARATA PRIMA: la distribuzione e' **fortemente asimmetrica** — la
stragrande maggioranza sotto 1 punto e una manciata di casi enormi. ⚠️ **Se
invece la coda fosse spessa** (diciamo piu' del 5% sopra i 10 punti), allora
`W7-75` sarebbe stata **fuorviante** e non solo incompleta, e la conclusione
«il giudice e' insensibile» andrebbe **ritirata**, non ristretta.

⚠️ **E la domanda che conta per il prodotto non e' il delta, e' quanti
ATTRAVERSANO una soglia**: uno spostamento di 50 punti fra 99,9 e 49,9 non
cambia niente se entrambi stanno dalla stessa parte del `cut`. Le due cose si
contano separate.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **il rumore del giudice**, rimisurato qui e non ereditato da `W7-75`: se
     non fosse piu' 0, la soglia di leggibilita' cambierebbe.
 (2) **i casi senza punteggio si contano a parte**, mai come zero (`W7-62`).
 (3) **la distribuzione si stampa a percentili**, non a media: su una
     distribuzione a coda la media e' il numero meno informativo che esista.

⚡ **Costo**: ~2 giudizi per caso su qualche centinaio di casi. Lanciato in
background; il numero di casi lo stampa in cima cosi' si sa cosa aspettare.

    python -u docs/stato-reale/banchi/quanto-e-larga-la-coda-dell-accento.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys

APO = re.compile(r"\be'(?=\s)")


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.grounding_gate import _ce_band_tau_hi
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    TAU = _ce_band_tau_hi()
    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, topic "
        "from facts where superseded_by is null "
        "and grounding_span is not null and grounding_span <> ''"
    ).fetchall()
    casi = [r for r in righe if APO.search(r[1] or "")]
    print(f"  fatti vivi con fonte: {len(righe)}  ·  di cui con `e'`: {len(casi)}")
    print(f"  tau_hi = {TAU:.1f}  ·  due giudizi per caso ⇒ {2 * len(casi)} giudizi")
    if len(casi) < 30:
        print("NON RIUSCITO: meno di trenta casi, non misuro una coda.")
        return 1

    def voto(t: str, r) -> float | None:
        _f, _p, span, wr, vb_raw, topic = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        g = run_validation_gate(
            proposition=t, verified_by=vb, topic=topic, agent=None,
            source=span, writer_role=wr, narrative_l1_skip=False,
            ground_write=True)
        sc = getattr(g, "grounding_score", None)
        return None if sc is None else float(sc)

    print("\n  -- CONTROLLO (1): il rumore del giudice, RIMISURATO qui")
    r0 = casi[0]
    a1, a2 = voto(r0[1] or "", r0), voto(r0[1] or "", r0)
    if a1 is None or a2 is None:
        print("     ⚠️ punteggio assente sul primo caso: non parto.")
        return 1
    rumore = abs(a1 - a2)
    print(f"     {a1:.4f} e {a2:.4f}  → rumore {rumore:.4f}")

    print(f"\n  == LA DISTRIBUZIONE su {len(casi)} casi")
    diffs, senza, coppie = [], 0, []
    for r in casi:
        t = r[1] or ""
        sa, sb = voto(t, r), voto(APO.sub("è", t), r)
        if sa is None or sb is None:
            senza += 1
            continue
        diffs.append(abs(sb - sa))
        coppie.append((r[0], sa, sb))

    print("\n  -- CONTROLLO (2): i casi senza punteggio, contati A PARTE")
    print(f"     senza punteggio: {senza}  ·  con punteggio: {len(diffs)}")
    if not diffs:
        print("NON RIUSCITO: nessun caso con punteggio.")
        return 1

    ad = sorted(diffs)

    def pct(p: float) -> float:
        return ad[min(len(ad) - 1, int(p * len(ad)))]

    print("\n  -- CONTROLLO (3): PERCENTILI, non media")
    for p in (0.50, 0.75, 0.90, 0.95, 0.99):
        print(f"     p{int(p * 100):<3} {pct(p):>10.3f}")
    print(f"     max  {ad[-1]:>10.3f}   ·   rumore {rumore:.4f}")

    print("\n  == QUANTI NELLA CODA")
    for soglia in (1, 5, 10, 25, 50):
        n = sum(1 for x in ad if x >= soglia)
        print(f"     |delta| >= {soglia:<3} : {n:>4}"
              f"  ({100.0 * n / len(ad):.2f}%)")

    # 🔑 CIO' CHE CONTA PER IL PRODOTTO: non il delta, ma chi ATTRAVERSA.
    print("\n  == E QUANTI ATTRAVERSANO UNA SOGLIA (la domanda vera)")
    attraversa_tau = sum(1 for _i, a, b in coppie
                         if (a >= TAU) != (b >= TAU))
    attraversa_cut = sum(1 for _i, a, b in coppie
                         if (a >= 40.0) != (b >= 40.0))
    print(f"     attraversano tau_hi={TAU:.0f} : {attraversa_tau}"
          f"  ({100.0 * attraversa_tau / len(coppie):.2f}%)")
    print(f"     attraversano cut=40      : {attraversa_cut}"
          f"  ({100.0 * attraversa_cut / len(coppie):.2f}%)")

    print("\n  == LA RIGA CHE CONTA")
    grossi = sum(1 for x in ad if x >= 10)
    quota = 100.0 * grossi / len(ad)
    if quota > 5:
        print(f"     🔴 LA CODA E' SPESSA: {quota:.1f}% dei casi si sposta di")
        print("     almeno 10 punti. ⇒ `W7-75` non era incompleta, era")
        print("     **FUORVIANTE**, e la sua conclusione va RITIRATA non ristretta.")
    elif attraversa_tau or attraversa_cut:
        print(f"     🟡 CODA SOTTILE ({quota:.2f}% sopra 10 punti) MA NON VUOTA, e")
        print(f"     **{attraversa_tau + attraversa_cut} casi ATTRAVERSANO una")
        print("     soglia** ⇒ il verdetto cambia per un accento. **La rarita'")
        print("     non e' una difesa quando l'esito e' un fatto vero bocciato.**")
    else:
        print(f"     🟢 Coda sottile ({quota:.2f}% sopra 10 punti) e **nessun")
        print("     attraversamento di soglia**: gli spostamenti grandi ci sono")
        print("     ma non cambiano nessun verdetto su questa popolazione.")
        print("     ⇒ `W7-76` resta vero come esistenza e **non ha una frequenza**")
        print("     che pesi: lo dico con la stessa forza con cui l'ho pubblicato.")

    peggiori = sorted(coppie, key=lambda x: -abs(x[2] - x[1]))[:5]
    print("\n  i cinque spostamenti maggiori:")
    for fid, a, b in peggiori:
        print(f"     {fid}  {a:8.3f} → {b:8.3f}   delta {b - a:+9.3f}")

    print("\n  ⚠️ COSA NON DICE: UN modello e UNA macchina; `è`/`e'` e' UNA")
    print("  differenza ortografica; e il campione e' l'INTERA popolazione con")
    print("  `e'` e fonte, quindi i numeri valgono per QUESTO corpus, non per")
    print("  un traffico da cliente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
