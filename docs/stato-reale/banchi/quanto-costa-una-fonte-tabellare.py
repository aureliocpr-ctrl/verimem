"""QUANTO COSTA, ALLA PORTA, CHE LA FONTE SIA UNA TABELLA.

\U0001f4cc **IL NUMERO CHE MANCA A `W7-95`.** Là ho letto **9 casi a mano** e
ho trovato che il moat boccia le **sintesi di fonti tabellari** — *«i passati
sono 10»* contro *«10 passed»*, *«nessuna delle sette celle…»* che va
**calcolata**. Ma **2 casi netti e 4 plausibili non sono una misura**, e la
cella lo dichiara.

\U0001f9ed **E tocca un reperto di @ws5** delle 18:41 (*«su fonte LUNGA E
TABELLARE il gate e' rovesciato»*): gliel'ho offerto sul canale, non l'ha
raccolto, e allora lo misuro io **portandogli i numeri**, non togliendogli il
reperto.

\U0001f6ab **PRIMA HO CHIESTO AL PRODOTTO** (`verimem doctor`, lezione del
27/08 e richiamo di @ws2 stanotte): dice `moat-judge 9432/14333 giudicati`,
`topic-crowding`, `trust-rank-coverage`, `confidence-vs-verifica` — **nulla
sulle tabelle**. Il banco serve.

\U0001f3af LA DOMANDA: **i fatti con fonte TABELLARE vengono bocciati piu' di
quelli con fonte DISCORSIVA?**

ATTESA DICHIARATA PRIMA: **si', e nettamente** — se il moat riconosce le
trascrizioni e boccia le conclusioni, una fonte tabellare invita a scrivere
conclusioni. ⚠️ **Se i due tassi fossero simili, `W7-95` resta un'osservazione
su 2 casi e non una classe**, e lo dico con la stessa forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) 🪞 **IL CONFONDENTE VERO E' LA LUNGHEZZA**: le fonti tabellari sono piu'
     lunghe per natura. Il banco stampa le mediane E ripete il confronto su
     una **sotto-popolazione appaiata per lunghezza** (stessa fascia di
     caratteri). Se il divario sparisce li', **era la lunghezza**.
 (2) ⚠️ **PREFLIGHT sul moat** (`W7-87`).
 (3) 📊 **baseline RIGIUDICATO oggi** (lezione di `W7-94`).
 (4) ⚖️ **la classificazione e' un'euristica MIA** e va stampata con qualche
     esempio, perche' chi legge possa contestarla.

⚠️ **E UN LIMITE CHE VIENE DA `W7-90`**: `grounding_span` **non e' la fonte
intera**, e' un estratto (budget 400, max osservato 932). Quindi qui misuro
**se l'ESTRATTO sembra una tabella**, non se lo fosse il documento originale.
E' il dato che il giudice ha visto, quindi per la domanda va bene — ma il nome
«fonte» sarebbe improprio e lo dico.

    python -u docs/stato-reale/banchi/quanto-costa-una-fonte-tabellare.py
"""

from __future__ import annotations

import re
import sqlite3
import statistics
import sys
import time

CUT = 40.0
TETTO = 90
#: righe che "sembrano una riga di tabella": due o piu' colonne separate da un
#: pipe, un punto mediano, o tre spazi di allineamento.
RIGA_TAB = re.compile(r"(\|.*\|)|(·.*·)|(\S {3,}\S.* {3,}\S)")


def tabellare(fonte: str) -> bool:
    righe = [r for r in (fonte or "").splitlines() if r.strip()]
    if len(righe) < 3:
        # una tabella su una riga sola non c'e': ma un estratto puo' averla
        # compressa, quindi guardo anche i separatori ripetuti in linea.
        return (fonte or "").count(" · ") >= 3
    return sum(1 for r in righe if RIGA_TAB.search(r)) >= 3


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    con = sqlite3.connect(str(CONFIG.semantic_db))
    righe = con.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> '' and proposition is not null").fetchall()
    tab = [(p, s) for p, s in righe if tabellare(s)]
    dis = [(p, s) for p, s in righe if not tabellare(s)]
    print(f"  fatti vivi con fonte: {len(righe)}")
    print(f"  fonte TABELLARE : {len(tab)}"
          f"  ({100.0 * len(tab) / max(1, len(righe)):.1f}%)")
    print(f"  fonte DISCORSIVA: {len(dis)}")
    if len(tab) < 30 or len(dis) < 30:
        print("NON RIUSCITO: una delle due classi ha meno di trenta casi.")
        return 1

    # (4) l'euristica e' mia: la mostro
    print("\n  -- (4) due esempi per classe, perche' l'euristica sia"
          " contestabile")
    for eti, pop in (("TABELLARE", tab), ("DISCORSIVA", dis)):
        for _p, s in pop[:2]:
            print(f"     [{eti}] {s[:96].replace(chr(10), ' | ')}…")

    print("\n  -- preflight: il moat deve essere CALDO")
    warm_local_judge_async()
    t0 = time.time()
    stato = judge_state()
    while stato == "warming" and time.time() - t0 < 180:
        time.sleep(2)
        stato = judge_state()
    print(f"     `judge_state()` = {stato!r}  dopo {time.time() - t0:.1f}s")
    if stato != "ready":
        print("NON RIUSCITO: giudice non pronto, misurerei il warmup.")
        return 1

    def _giudica(pop: list, eti: str) -> list:
        out = []
        passo = max(1, len(pop) // TETTO)
        camp = pop[::passo][:TETTO]
        t = time.time()
        for i, (prop, span) in enumerate(camp):
            try:
                res = run_validation_gate(
                    proposition=prop, verified_by=None, topic="banco/tabella",
                    agent=None, source=span, ground_write=True)
            except Exception:  # noqa: BLE001
                continue
            g = (float(res.grounding_score)
                 if res.grounding_score is not None else None)
            if g is None:
                continue
            out.append((g, len(span), len(prop)))
            if i and i % 40 == 0:
                print(f"    {eti}: ...{i}/{len(camp)} ({time.time() - t:.0f}s)")
        return out

    print(f"\n  -- rigiudico {TETTO} per classe alla porta di oggi")
    gt = _giudica(tab, "tab")
    gd = _giudica(dis, "dis")
    if len(gt) < 20 or len(gd) < 20:
        print("NON RIUSCITO: meno di venti giudizi utili in una classe.")
        return 1

    def _riga(eti: str, dati: list) -> tuple[float, float]:
        b = sum(1 for g, _ls, _lp in dati if g < CUT)
        q = 100.0 * b / len(dati)
        ml = statistics.median([ls for _g, ls, _lp in dati])
        print(f"     {eti:<12}{len(dati):>5}{b:>10}{q:>9.1f}%{ml:>12.0f}")
        return q, ml

    print(f"\n     {'classe':<12}{'n':>5}{'bocciati':>10}{'quota':>10}"
          f"{'len fonte':>12}")
    q_tab, ml_tab = _riga("TABELLARE", gt)
    q_dis, ml_dis = _riga("DISCORSIVA", gd)

    # (1) il confondente: rifaccio il confronto a lunghezza APPAIATA
    print("\n  -- (1) lo stesso confronto su fonti di lunghezza COMPARABILE")
    lo, hi = 200, 420
    at = [d for d in gt if lo <= d[1] <= hi]
    ad = [d for d in gd if lo <= d[1] <= hi]
    if len(at) >= 15 and len(ad) >= 15:
        print(f"     (solo fonti fra {lo} e {hi} caratteri)")
        print(f"\n     {'classe':<12}{'n':>5}{'bocciati':>10}{'quota':>10}"
              f"{'len fonte':>12}")
        qa_t, _ = _riga("TABELLARE", at)
        qa_d, _ = _riga("DISCORSIVA", ad)
    else:
        qa_t = qa_d = -1.0
        print(f"     non appaiabile: {len(at)} e {len(ad)} casi nella fascia.")

    print("\n  == LA RIGA CHE CONTA")
    print(f"     grezzo: TABELLARE {q_tab:.1f}% contro DISCORSIVA"
          f" {q_dis:.1f}%   (len {ml_tab:.0f} contro {ml_dis:.0f})")
    if qa_t >= 0:
        print(f"     appaiato per lunghezza: {qa_t:.1f}% contro {qa_d:.1f}%")
        if qa_t <= qa_d + 3.0:
            # ⚠️ CORRETTO il 31/08 alle 00:07: la prima stesura stampava qui
            #    «era la LUNGHEZZA», e nella prima esecuzione era FALSO — il
            #    grezzo dava 8,9% contro 10,0%, cioe' **nessun divario da
            #    spiegare**, e per giunta col segno opposto. Attribuire a un
            #    confondente un divario che non esiste e' un errore di
            #    lettura, non un'imprecisione: distinguo i due casi.
            if q_tab <= q_dis + 3.0:
                print("\n     🟢 **NESSUN DIVARIO, ne' grezzo ne' appaiato**:"
                      f" {q_tab:.1f}% contro")
                print(f"     {q_dis:.1f}% prima, {qa_t:.1f}% contro"
                      f" {qa_d:.1f}% dopo. **La forma TABELLARE della")
                print("     fonte non costa NULLA alla porta.** ⇒ `W7-95`"
                      " resta")
                print("     un'osservazione su 2 casi letti e **NON e' una"
                      " classe**: lo")
                print("     dico con la stessa forza con cui l'avrei"
                      " annunciata.")
            else:
                print("\n     🟢 **A LUNGHEZZA APPAIATA IL DIVARIO SPARISCE**:"
                      f" c'era ({q_tab:.1f}%")
                print(f"     contro {q_dis:.1f}%) e nella fascia comune non"
                      " c'e' piu'. **Era la")
                print("     LUNGHEZZA, non la tabella.**")
        elif qa_t > qa_d + 10.0:
            print("\n     🔴 **IL DIVARIO REGGE ANCHE A LUNGHEZZA APPAIATA**:"
                  " la forma")
            print("     TABELLARE della fonte costa da sola. ⇒ `W7-95` diventa"
                  " una")
            print("     classe misurata, e tocca **i nostri resoconti**, che"
                  " sono quasi")
            print("     tutti conclusioni su tabelle.")
        else:
            print("\n     🟡 **Divario ridotto ma non nullo**: una parte era la"
                  " lunghezza,")
            print("     una parte no. Serve un disegno piu' fine prima di"
                  " chiamarla classe.")
    else:
        print("\n     ⚪ **SENZA IL CONTROLLO DI LUNGHEZZA IL GREZZO NON SI"
              " LEGGE**:")
        print("     le due classi differiscono anche in taglia, e non ho una"
              " fascia")
        print("     comune abbastanza popolata. **Nessun verdetto.**")

    print("\n  ⚠️ COSA NON DICE: **`grounding_span` non e' la fonte intera**"
          " ma un")
    print("  estratto (`W7-90`: budget 400, max 932) ⇒ misuro se l'ESTRATTO")
    print("  sembra una tabella, che e' cio' che il giudice ha visto, ma"
          " chiamarla")
    print("  «fonte» sarebbe improprio · l'euristica di classificazione e'"
          " MIA ·")
    print("  e non distingue una sintesi VERA da un claim non sostenuto:"
          " quello")
    print("  si vede solo leggendo, come in `W7-95`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
