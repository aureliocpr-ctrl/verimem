"""Quanto costerebbe togliere la numerazione dallo SPAN prima del giudice?

Misurato in `101b6f08`: togliendo **solo** «Art. N -» dalla fonte, il giudice
passa da **100.0 a 0.4** sullo stesso claim inventato (delta medio **+99.4**,
controlli retti). ⇒ la numerazione inganna **anche il giudice**, non solo
l'estrattore che ho curato.

**Cura candidata**: togliere la numerazione **dallo span** prima di darlo al
giudice. ⚠️ Ma cambia ciò che il giudice vede su **ogni** scrittura con fonte,
quindi **il numero viene prima della cura** — stanotte questa disciplina ha già
sconsigliato una cura su due (date italiane: 11 candidati, **11 falsi**).

DUE MISURE, e la seconda è quella che conta:
  ① **CENSIMENTO** (tutto il corpus, sola lettura): quanti fatti **già
     ammessi** hanno uno span che **contiene** numerazione? È la popolazione
     che la cura toccherebbe.
  ② **EFFETTO** (campione **dichiarato**): su N di quei fatti, si rigiudica il
     **claim vero** contro **(a)** lo span com'è e **(b)** lo span **senza**
     numerazione. Quanti **cambiano verdetto**?

🔑 La logica di ② : sono fatti che il prodotto ha **AMMESSO**. Se togliendo la
numerazione il loro grounding **crolla**, la cura li **quarantinerebbe** — e
quello è il costo. Se **regge**, la cura è gratis su di loro.

LA PREDIZIONE, scritta prima di eseguire: **sotto il 10%** dei fatti del
campione cambia verdetto. Sopra il 30% la cura **non si fa** senza una
decisione di Aurelio: quarantinare centinaia di fatti già ammessi non è un
dettaglio tecnico.

CONTROLLO CHE DEVE POTER FALLIRE: la numerazione deve essere **davvero
presente** negli span del campione — il banco stampa quante occorrenze toglie.
Se togliesse zero, non starei misurando la cura ma il rumore.

⚠️ La regex della numerazione **non la reinvento**: importo `_RIFERIMENTO_RE`
da `quantity_match`, cioè **la stessa definizione che la cura userebbe**. Se
sbaglia lei, sbaglia la cura — e la stima resta fedele alla cura.

    sola lettura sullo store (`mode=ro`) · le riscritture di prova vanno in uno
    store TEMPORANEO · lo store di Aurelio NON viene toccato

    python docs/stato-reale/banchi/ws3-quanto-costerebbe-togliere-la-numerazione-dallo-span.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

#: campione DICHIARATO: quanti fatti rigiudicare due volte ciascuno
N_CAMPIONE = 40


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415
    from verimem.config import CONFIG  # noqa: PLC0415
    from verimem.quantity_match import _RIFERIMENTO_RE  # noqa: PLC0415

    db = str(CONFIG.semantic_db)
    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)}")
    print(f"    lettura: {db}  (mode=ro, nessuna scrittura)")
    print("    riscritture di prova: store TEMPORANEO · regex della numerazione")
    print("    IMPORTATA dal prodotto (_RIFERIMENTO_RE), non reinventata")

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        righe = list(con.execute(
            "SELECT proposition, grounding_span FROM facts "
            "WHERE grounding_span IS NOT NULL AND length(grounding_span) > 0 "
            "AND grounding_score >= 90"))
    finally:
        con.close()

    # ── ① CENSIMENTO ────────────────────────────────────────────────────
    con_numerazione = []
    for prop, span in righe:
        if not prop or not span:
            continue
        if _RIFERIMENTO_RE.search(span):
            con_numerazione.append((prop, span))
    tot = sum(1 for p, s in righe if p and s)
    print("\n  ══ ① CENSIMENTO ══")
    print(f"     fatti ammessi con span (grounding >= 90) ..... {tot}")
    print(f"     ► con NUMERAZIONE nello span ................. {len(con_numerazione)}"
          f"   ({100.0 * len(con_numerazione) / max(tot, 1):.1f}%)")

    if not con_numerazione:
        print("\n     CONTROLLO CADUTO: nessuno span contiene numerazione ⇒ non")
        print("     c'e' popolazione da misurare. NESSUNA STIMA.")
        return 1

    # ── ② EFFETTO su un campione dichiarato ─────────────────────────────
    campione = con_numerazione[:N_CAMPIONE]
    mem = Memory(str(Path(tempfile.mkdtemp()) / "span.db"))
    tolte = 0
    cambiati = []
    invariati = 0
    print(f"\n  ══ ② EFFETTO — campione DICHIARATO di {len(campione)} fatti ══")
    print(f"  {'#':>3} {'con numeraz.':>13} {'senza':>9} {'delta':>8}  esito")
    print("  " + "-" * 62)
    for i, (prop, span) in enumerate(campione):
        pulito, n = _RIFERIMENTO_RE.subn(" ", span)
        tolte += n
        ra = mem.add(prop, topic=f"sp/a/{i}", source=span, validate="full")
        rb = mem.add(prop, topic=f"sp/b/{i}", source=pulito, validate="full")
        ga = float(ra.get("grounding_score") or -1)
        gb = float(rb.get("grounding_score") or -1)
        qa = str(ra.get("status")) == "quarantined"
        qb = str(rb.get("status")) == "quarantined"
        if qa != qb:
            cambiati.append((i, ga, gb, qa, qb, prop[:60]))
            esito = "CAMBIA" if not qa else "cambia (era gia' fermo)"
        else:
            invariati += 1
            esito = ""
        if esito or abs(ga - gb) > 20:
            print(f"  {i:>3} {ga:13.1f} {gb:9.1f} {gb - ga:+8.1f}  {esito}")

    print(f"\n  CONTROLLO: occorrenze di numerazione TOLTE dagli span: {tolte}")
    if tolte == 0:
        print("     CONTROLLO CADUTO: non ho tolto niente ⇒ misuro rumore, non la")
        print("     cura. NESSUNA STIMA.")
        return 1

    # quelli che erano AMMESSI e diventerebbero fermati: e' il costo vero
    costo = [c for c in cambiati if not c[3] and c[4]]
    guadagno = [c for c in cambiati if c[3] and not c[4]]
    quota = 100.0 * len(costo) / max(len(campione), 1)
    print("\n  ══ IL COSTO ══")
    print(f"     campione ................................. {len(campione)}")
    print(f"     invariati ................................ {invariati}")
    print(f"     ► AMMESSI che diventerebbero FERMATI ..... {len(costo)}"
          f"   ({quota:.1f}% del campione)   <- IL COSTO")
    print(f"       fermati che diventerebbero ammessi ..... {len(guadagno)}")

    if costo:
        print("\n  I CASI CHE LA CURA QUARANTINEREBBE (vanno LETTI):")
        for i, ga, gb, _qa, _qb, testo in costo[:10]:
            print(f"     #{i}  {ga:.1f} -> {gb:.1f}   {testo}")

    print("\n  ══ VERDETTO sulla PREDIZIONE ══")
    print(f"     previsto: SOTTO il 10%   ·   misurato: {quota:.1f}%")
    if quota < 10:
        print("     RETTA: la cura toccherebbe pochi fatti gia' ammessi ⇒ si puo'")
        print("     proporre portando i casi, non solo il numero.")
    elif quota < 30:
        print("     SBAGLIATA nella taglia, ma sotto il 30%: proponibile SOLO")
        print("     dichiarando quanti fatti gia' ammessi quarantina, e dopo")
        print("     averli letti.")
    else:
        print("     FALSIFICATA: sopra il 30%. La cura NON si fa senza una")
        print("     decisione di Aurelio.")

    print("\n  ⚠️ LIMITI: il campione sono i PRIMI "
          f"{N_CAMPIONE} in ordine di query, NON un")
    print("     campione casuale — la quota vale su di loro e non si estende al")
    print("     corpus senza dirlo. «grounding alto» non e' «vero»: se il giudice")
    print("     sbagliava, un fatto che la cura ferma e' una CATTURA, non un")
    print("     costo. Lo span e' troncato a 400 caratteri. E il corpus si muove.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
