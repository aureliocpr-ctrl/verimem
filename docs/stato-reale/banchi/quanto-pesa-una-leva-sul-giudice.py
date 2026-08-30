"""QUANTO PESA UNA LEVA SUL GIUDICE — lo strumento, non il reperto.

`W7-77` ha misurato **una** leva (`e'` → `è`) su **tutta** la popolazione che la
contiene, e ha trovato: p95 **17,7** · p99 **69,2** · max **92,562**, con il
**3,07%** dei casi che **attraversa una soglia**. E ha dichiarato il limite:

    `è`/`e'` e' UNA differenza ortografica: non dice nulla sulle altre.

Nello stesso momento un'altra istanza ha trovato che **un articolo**
(*«competente per territorio»* contro *«per il territorio»*) sposta il giudice
di **25,6 punti** e ribalta l'esito, **deterministico 3 su 3** — e ha
dichiarato il **suo** limite con la stessa onesta':

    non e' «l'articolo sposta il giudice» in generale: e' «ESISTE una coppia
    equivalente dove sposta 25,6 punti». Un caso dimostrato, non un fenomeno.

⇒ **Le due misure sono complementari e a ciascuna manca cio' che l'altra ha**:
io ho la **frequenza su una leva**, lei ha l'**esistenza su un'altra**. Il pezzo
che manca a entrambe e' **la frequenza della sua leva**.

\U0001f3af **Questo file non e' un reperto: e' lo STRUMENTO** che serve a farlo.
Prende una **leva** — una coppia (regex, sostituzione) — e produce la stessa
analisi di `W7-77` su qualunque popolazione del corpus la contenga:

  · il **rumore del giudice**, rimisurato ogni volta e mai ereditato
  · i casi **senza punteggio contati a parte**, mai come zero
  · la distribuzione a **percentili** (su una coda la media non dice nulla)
  · **quanti ATTRAVERSANO** `cut` e `tau_hi` — che e' la domanda vera: uno
    spostamento di 50 punti fra 99,9 e 49,9 non cambia nessun verdetto
  · e la **condizione di ritiro dichiarata prima**, che oggi mi ha costretta a
    ritirare una mia cella di venticinque minuti.

⚠️ **Cosa NON fa**: non sceglie la leva. Chi la sceglie deve poter dire
**perche' due testi che differiscono per quella leva significano la stessa
cosa** — altrimenti misura una differenza di senso, non di forma.

    python -u docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py [nome_leva]

    LEVE disponibili: accento (default) · articolo · maiuscole · spazi
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys

#: (regex che TROVA la forma A, funzione che produce la forma B, descrizione)
LEVE: dict[str, tuple[re.Pattern[str], object, str]] = {
    "accento": (re.compile(r"\be'(?=\s)"),
                lambda m: "è",
                "`e'` → `è` (la leva di W7-77)"),
    "articolo": (re.compile(r"\bper (?=[a-z]{4,}\b)"),
                 lambda m: "per il ",
                 "«per X» → «per il X» (la leva dell'altra istanza)"),
    "maiuscole": (re.compile(r"(?<=\. )[a-z](?=[a-z]{3,})"),
                  lambda m: m.group(0).upper(),
                  "iniziale minuscola dopo il punto → maiuscola"),
    "spazi": (re.compile(r"(?<=[a-z]), (?=[a-z])"),
              lambda m: " , ",
              "«a, b» → «a , b» (spaziatura attorno alla virgola)"),
}
#: la condizione di ritiro, dichiarata PRIMA di vedere i dati.
SOGLIA_CODA = 5.0   # % di casi oltre 10 punti


def main() -> int:
    nome = (sys.argv[1] if len(sys.argv) > 1 else "accento").strip()
    if nome not in LEVE:
        print(f"NON RIUSCITO: leva sconosciuta «{nome}». Disponibili:"
              f" {', '.join(LEVE)}")
        return 1
    trova, sostituisci, descr = LEVE[nome]
    print(f"  LEVA: {nome} — {descr}")

    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.grounding_gate import _ce_band_tau_hi
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    TAU, CUT = _ce_band_tau_hi(), 40.0
    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select id, proposition, grounding_span, writer_role, verified_by, topic "
        "from facts where superseded_by is null "
        "and grounding_span is not null and grounding_span <> ''").fetchall()
    casi = [r for r in righe if trova.search(r[1] or "")]
    print(f"  fatti vivi con fonte: {len(righe)}  ·  che contengono la leva:"
          f" {len(casi)}")
    print(f"  tau_hi={TAU:.0f} · cut={CUT:.0f} · {2 * len(casi)} giudizi")
    if len(casi) < 30:
        print(f"NON RIUSCITO: {len(casi)} casi, meno di trenta: **una coda al"
              " 3% non sarebbe distinguibile dall'assenza**. Serve una leva")
        print("piu' frequente, o si misura l'ESISTENZA e non la frequenza.")
        return 1

    def voto(t: str, r) -> float | None:
        _f, _p, span, wr, vb_raw, topic = r
        try:
            vb = json.loads(vb_raw or "[]")
        except Exception:  # noqa: BLE001
            vb = []
        g = run_validation_gate(proposition=t, verified_by=vb, topic=topic,
                                agent=None, source=span, writer_role=wr,
                                narrative_l1_skip=False, ground_write=True)
        sc = getattr(g, "grounding_score", None)
        return None if sc is None else float(sc)

    print("\n  -- CONTROLLO (1): il rumore del giudice, RIMISURATO per questa leva")
    r0 = casi[0]
    a1, a2 = voto(r0[1] or "", r0), voto(r0[1] or "", r0)
    if a1 is None or a2 is None:
        print("     ⚠️ punteggio assente sul primo caso: non parto.")
        return 1
    rumore = abs(a1 - a2)
    print(f"     {a1:.4f} e {a2:.4f}  → rumore {rumore:.4f}")

    diffs, coppie, senza = [], [], 0
    for r in casi:
        t = r[1] or ""
        sa, sb = voto(t, r), voto(trova.sub(sostituisci, t), r)
        if sa is None or sb is None:
            senza += 1
            continue
        diffs.append(abs(sb - sa))
        coppie.append((r[0], sa, sb))
    print(f"\n  -- CONTROLLO (2): senza punteggio {senza}, con punteggio"
          f" {len(diffs)}  (i primi NON contati come zero)")
    if not diffs:
        print("NON RIUSCITO: nessun caso con punteggio.")
        return 1

    ad = sorted(diffs)
    def pct(p): return ad[min(len(ad) - 1, int(p * len(ad)))]
    print("\n  -- CONTROLLO (3): PERCENTILI, non media")
    for p in (0.50, 0.75, 0.90, 0.95, 0.99):
        print(f"     p{int(p * 100):<3} {pct(p):>10.3f}")
    print(f"     max  {ad[-1]:>10.3f}")

    print("\n  == QUANTI ATTRAVERSANO (la domanda vera)")
    a_tau = sum(1 for _i, a, b in coppie if (a >= TAU) != (b >= TAU))
    a_cut = sum(1 for _i, a, b in coppie if (a >= CUT) != (b >= CUT))
    print(f"     tau_hi={TAU:.0f} : {a_tau}  ({100.0 * a_tau / len(coppie):.2f}%)")
    print(f"     cut={CUT:.0f}    : {a_cut}  ({100.0 * a_cut / len(coppie):.2f}%)")

    grossi = 100.0 * sum(1 for x in ad if x >= 10) / len(ad)
    print(f"\n  == LA RIGA CHE CONTA  (condizione dichiarata: coda > {SOGLIA_CODA}%"
          " ⇒ la leva CONTA)")
    if grossi > SOGLIA_CODA:
        print(f"     🔴 **LA LEVA `{nome}` CONTA**: {grossi:.2f}% dei casi oltre i")
        print(f"     10 punti, e {a_tau + a_cut} attraversamenti di soglia su")
        print(f"     {len(coppie)}. ⇒ Non e' un caso isolato: e' una frequenza.")
    elif a_tau or a_cut:
        print(f"     🟡 Coda sottile ({grossi:.2f}%) ma {a_tau + a_cut}")
        print("     attraversamenti: **esiste** e non e' frequente.")
    else:
        print(f"     🟢 Coda {grossi:.2f}% e **zero attraversamenti**: su questa")
        print("     popolazione la leva non cambia nessun verdetto.")

    for fid, a, b in sorted(coppie, key=lambda x: -abs(x[2] - x[1]))[:5]:
        print(f"     {fid}  {a:8.3f} → {b:8.3f}   delta {b - a:+9.3f}")

    print("\n  ⚠️ COSA NON DICE: la leva la sceglie chi lancia il banco, e deve")
    print("  poter dire **perche' le due forme significano la stessa cosa**. Se")
    print("  non puo', qui si misura una differenza di SENSO travestita da")
    print("  differenza di forma. E i numeri valgono per QUESTO corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
