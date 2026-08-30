"""L'ACCENTO SPOSTA IL PUNTEGGIO DEL GIUDICE? — il dettaglio non spiegato di `W7-74`.

`W7-74` ha misurato il costo alla porta dell'apostrofo e ha lasciato **due
dettagli non spiegati**. Il secondo e' questo::

    2 casi cambiano il layer che DECIDE (`L4-review` → `L4-grounding`)
    mantenendo `downgrade`: l'accento sposta chi decide, non l'esito.
    Non l'avevo previsto e non lo spiego.

**Ora lo spiego, o lo lascio cadere.** Letto il codice (`anti_confab_gate.py:2817`),
`L4-review` e' *«borderline grounding in the CE review band [cut, tau_hi) —
held for review»*. ⇒ **E' un layer di BANDA: dipende dal PUNTEGGIO.**

🔑 **Se cambiando `e'` in `è` il layer cambia, allora e' cambiato il
`grounding_score`** — cioe' **il giudice da' un voto diverso alla stessa frase
scritta in due modi che significano la stessa cosa.**

LA DOMANDA: **di quanto si sposta il punteggio, e quanto spesso attraversa una
soglia?** Perche' la conseguenza per la vetrina e' pesante: se il voto dipende
da come scrivi e non da cosa dici, **il verdetto ha una componente ortografica**.

ATTESA DICHIARATA PRIMA: gli spostamenti ci sono ma sono **piccoli** (il modello
vede due testi quasi identici) e attraversano una soglia **di rado** — nel
campione di `W7-74`, 2 casi su 24. ⚠️ **Se invece fossero grandi**, il giudice
sarebbe sensibile all'ortografia in un modo che nessuno ha misurato, e sarebbe
un reperto di prima grandezza. ⚠️ **E se fossero tutti ZERO**, allora il cambio
di layer in `W7-74` ha un'ALTRA causa e la mia spiegazione cade: lo dico.

CONTROLLI CHE POSSONO FALLIRE:
 (1) **il moat deve girare**: senza `ground_write=True` e senza fonte
     `grounding_score` torna `None` e leggerei un'assenza come un valore
     (lezione `W7-62`). Prendo **solo** i fatti con `grounding_span`.
 (2) **controllo di stabilita'**: la stessa identica proposizione, giudicata due
     volte, deve dare lo **stesso** punteggio. Se il giudice fosse rumoroso da
     solo, ogni differenza sotto quel rumore non significherebbe niente —
     ed e' la misura che rende leggibile tutto il resto.
 (3) **la DISTRIBUZIONE delle differenze**, stampata prima di qualunque media:
     una media su una distribuzione bimodale non dice niente.

    python -u docs/stato-reale/banchi/l-accento-sposta-il-punteggio-del-giudice.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys

APO = re.compile(r"\be'(?=\s)")
CAMPIONE = 16


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, topic "
        "from facts where superseded_by is null "
        "and grounding_span is not null and grounding_span <> ''"
    ).fetchall()
    con_apo = [r for r in righe if APO.search(r[1] or "")]
    print(f"  fatti vivi CON FONTE: {len(righe)}")
    print(f"  di cui con `e'`     : {len(con_apo)}")
    if len(con_apo) < 8:
        print("NON RIUSCITO: meno di otto casi, non misuro una distribuzione.")
        return 1

    passo = max(1, len(con_apo) // CAMPIONE)
    scelti = con_apo[::passo][:CAMPIONE]

    def voto(testo: str, r) -> tuple[float | None, str, list[str]]:
        _fid, _p, span, wr, vb_raw, topic = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        g = run_validation_gate(
            proposition=testo, verified_by=vb, topic=topic, agent=None,
            source=span, writer_role=wr, narrative_l1_skip=False,
            ground_write=True)
        sc = getattr(g, "grounding_score", None)
        ws = getattr(g, "warnings", None) or []
        return (None if sc is None else float(sc),
                str(getattr(g, "action", None)),
                sorted({str((w or {}).get("layer") or "?") for w in ws}))

    print("\n  -- CONTROLLO (2): il giudice e' STABILE su se stesso?")
    r0 = scelti[0]
    a1, _, _ = voto(r0[1] or "", r0)
    a2, _, _ = voto(r0[1] or "", r0)
    if a1 is None or a2 is None:
        print("     ⚠️ `grounding_score` ASSENTE: il moat non ha girato e non")
        print("     leggo l'assenza come un valore. Mi fermo.")
        return 1
    print(f"     stessa frase, due giri: {a1:.4f} e {a2:.4f}"
          f"  → rumore {abs(a1 - a2):.4f}")
    rumore = abs(a1 - a2)

    print(f"\n  == LO SPOSTAMENTO su {len(scelti)} casi")
    print(f"     {'con e-apostrofo':>16}{'con e-accentata':>18}{'delta':>10}   layer")
    diffs, cross, senza = [], 0, 0
    for r in scelti:
        t = r[1] or ""
        sa, aza, laya = voto(t, r)
        sb, azb, layb = voto(APO.sub("è", t), r)
        if sa is None or sb is None:
            senza += 1
            continue
        d = sb - sa
        diffs.append(d)
        if laya != layb or aza != azb:
            cross += 1
        segno = "  ← CAMBIA" if (laya != layb or aza != azb) else ""
        print(f"     {sa:>16.2f}{sb:>18.2f}{d:>+10.2f}   "
              f"{','.join(laya)} → {','.join(layb)}{segno}")

    if senza:
        print(f"     ⚠️ {senza} casi senza punteggio, esclusi (non contati come 0)")
    if not diffs:
        print("NON RIUSCITO: nessun caso con punteggio in entrambi i giri.")
        return 1

    print("\n  -- CONTROLLO (3): LA DISTRIBUZIONE, prima di qualunque media")
    ad = sorted(abs(d) for d in diffs)
    for lo, hi in ((0, 0.01), (0.01, 0.5), (0.5, 2), (2, 10), (10, 1e9)):
        n = sum(1 for x in ad if lo <= x < hi)
        eti = f"|delta| in [{lo}, {hi})" if hi < 1e9 else f"|delta| >= {lo}"
        print(f"     {eti:<26}{n}")
    print(f"     mediana {ad[len(ad) // 2]:.3f} · massimo {ad[-1]:.3f}"
          f" · rumore misurato {rumore:.4f}")

    print("\n  == LA RIGA CHE CONTA")
    sopra_rumore = sum(1 for x in ad if x > max(rumore, 0.01))
    if sopra_rumore == 0:
        print("     🪞 **NESSUNO spostamento sopra il rumore del giudice.**")
        print("     ⇒ La mia spiegazione del cambio di layer in `W7-74` CADE:")
        print("     l'accento non sposta il punteggio, e quei due casi hanno")
        print("     un'altra causa che non conosco. Lo dico con la stessa forza.")
    elif ad[-1] < 1.0:
        print(f"     🟢 {sopra_rumore} spostamenti sopra il rumore, ma il massimo")
        print(f"     e' {ad[-1]:.3f} punti su 100: **il giudice e' quasi**")
        print("     **insensibile all'ortografia**, e il cambio di layer avviene")
        print("     solo quando il punteggio era gia' **appiccicato a una**")
        print("     **soglia**. ⇒ Il difetto non e' del giudice: e' della BANDA,")
        print("     che trasforma una differenza trascurabile in un verdetto")
        print("     diverso.")
    else:
        print(f"     🔴 Il massimo spostamento e' {ad[-1]:.2f} punti su 100, con")
        print(f"     {cross} cambi di layer su {len(diffs)}: **il giudice VOTA**")
        print("     **diversamente la stessa frase scritta in due modi**, e la")
        print("     conseguenza per la vetrina e' che il verdetto ha una")
        print("     componente ortografica.")

    print("\n  ⚠️ COSA NON DICE: e' UN modello e UNA macchina; il rumore l'ho")
    print("  misurato su UN caso ripetuto due volte, non su una popolazione. E")
    print("  `è`/`e'` e' UNA differenza ortografica: non dice nulla sulle altre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
