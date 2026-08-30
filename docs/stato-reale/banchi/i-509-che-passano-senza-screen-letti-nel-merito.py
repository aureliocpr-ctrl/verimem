"""I 509 CHE PASSANO SENZA SCREEN, LETTI NEL MERITO — non contati.

`W7-69` ha misurato che **551 fatti `narrative` avrebbero acceso un layer `L1`**
e che **solo 42 (7,6%) sono checkpoint**: gli altri **509** hanno topic
`project` (397), `lessons` (44), `guardia` (32). E ha dichiarato il limite:

    «avrebbe acceso un layer» NON e' «e' falso» — `L1` e' un rilevatore
    lessicale e i suoi falsi allarmi sono misurati altrove.

⇒ **Il numero da solo e' un LIMITE SUPERIORE del silenzio.** Per sapere se il
silenzio costa davvero bisogna **leggere**, e la lezione della giornata e'
esattamente questa: contare mi ha salvata dall'impressione, ma **contare non
basta a dire che cosa sono quei fatti**.

QUESTO BANCO NON MISURA: **estrae e stampa** un campione dei 509 con il layer
che si sarebbe acceso e la proposizione intera, perche' io li legga e li
classifichi **a mano, nella cella**. E' un attrezzo, non un verdetto.

⚠️ **PERCHE' NON E' UN CAMPIONE CASUALE, e cosa faccio invece**: `Math.random`
non serve — prendo **uno ogni N** lungo tutta la popolazione ordinata per id,
cosi' non leggo solo i piu' vecchi. **E' la trappola in cui sono caduta in
`W7-69`**: i primi quattro erano tutti handoff perche' erano i piu' VECCHI, e
ho quasi concluso il falso.

⚡ **Costo**: `W7-69` girava `_l1_warnings` su 8822 fatti (~13 min). Qui filtro
PRIMA con le regex dei detector piu' frequenti (`L1.13`, `L1.15`) e giro la
funzione completa solo sui sopravvissuti: 1646 invece di 8822, meno di 2 min.

🪞 **E IL PRE-FILTRO NON E' NEUTRO — misurato, non supposto**: trova **385**
accesi dove `W7-69` ne contava **551**. La differenza sono i fatti che accendono
**solo** gli altri layer (`L1.10`, `L1.20`, `L1.16`, `L1.9`, `L1.18`), che
nessuna delle due regex intercetta. ⇒ **I numeri di questo banco NON sono quelli
di `W7-69`**, e la popolazione da cui pesco e' **348**, non 509. Per leggere
casi veri va benissimo; per contare no, e lo dico invece di lasciarlo credere.

    python -u docs/stato-reale/banchi/i-509-che-passano-senza-screen-letti-nel-merito.py
"""

from __future__ import annotations

import json
import sqlite3
import sys

QUANTI = 24
MARCHE = ("pre-compact", "handoff", "master fact", "checkpoint", "resume",
          "session")


def main() -> int:
    try:
        from verimem.anti_confab_gate import _l1_warnings
        from verimem.config import CONFIG
        from verimem.gate_router import classify_provenance
        from verimem.l1_completion_detector import _COMPLETION_PATTERN
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, "
        "topic, created_at from facts "
        "where superseded_by is null and meta_narrative = 1 "
        "order by id").fetchall()
    print(f"  narrative vivi: {len(righe)}")

    # PRE-FILTRO largo: la regex di L1.13 piu' le parole di L1.15. Serve solo a
    # non girare 15 detector su tutto; chi lo supera viene giudicato davvero.
    L115 = ("verificat", "testat", "verified", "tested", "validat")
    cand = [r for r in righe
            if _COMPLETION_PATTERN.search(r[1] or "")
            or any(w in (r[1] or "").casefold() for w in L115)]
    print(f"  passano il pre-filtro: {len(cand)}"
          f"  ({100.0 * len(cand) / len(righe):.1f}%)")

    accesi = []
    for fid, prop, span, wr, vb_raw, topic, ca in cand:
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        ws = _l1_warnings(prop or "", vb, source=span or None,
                          provenance=classify_provenance(wr, vb))
        lay = sorted({str((w or {}).get("layer") or "?") for w in (ws or [])})
        if lay:
            accesi.append((fid, prop, topic, lay))
    print(f"  di quelli, accendono un layer: {len(accesi)}")

    non_ck = [a for a in accesi
              if not any(m in (a[1] or "").casefold()[:120] for m in MARCHE)]
    print(f"  NON checkpoint: {len(non_ck)}")
    if not non_ck:
        print("  nessun caso da leggere.")
        return 1

    # ⚠️ UNO OGNI N lungo tutta la popolazione: leggere i primi e' esattamente
    #    l'errore di `W7-69`.
    passo = max(1, len(non_ck) // QUANTI)
    scelti = non_ck[::passo][:QUANTI]
    print(f"\n  == {len(scelti)} casi, uno ogni {passo}, da leggere NEL MERITO")
    print(f"  (la popolazione e' ordinata per id, quindi copre tutto l'arco)\n")
    for n, (fid, prop, topic, lay) in enumerate(scelti, 1):
        print(f"  [{n:>2}] {fid}  {','.join(lay)}")
        print(f"       topic: {topic}")
        print(f"       {(prop or '')[:300]}")
        print()

    print("  ⚠️ COSA NON DICE: questo banco non giudica nulla — stampa. La")
    print("  classificazione la faccio io leggendo, e va scritta nella cella")
    print("  con il criterio dichiarato, altrimenti e' un'impressione.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
