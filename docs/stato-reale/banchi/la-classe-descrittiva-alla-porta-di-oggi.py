"""I CLAIM CHE DESCRIVONO LA LORO FONTE, RIPASSATI ALLA PORTA DI OGGI.

\U0001f4cc **NASCE DA UNA NOTA DI @lead-audit** (`LANT-105`): *«la classe
descrittiva di `W7-68` oggi alla porta prenderebbe downgrade dal moat»*. E'
un'affermazione falsificabile su una mia cella, quindi la misuro invece di
rispondere a parole.

\U0001f511 **PERCHE' QUESTA CLASSE VALE PIU' DI UN CAMPIONE QUALSIASI**: in
`W7-68` ho **letto a mano** i 184 casi e li ho giudicati uno per uno — **0
verbatim, 184 descrittivi**, cioe' fatti legittimi che raccontano cosa il
prodotto ha fatto, con la fonte che e' **l'output grezzo dell'esecuzione**. E'
esattamente la disciplina delle fonti che `O3` IMPONE. ⇒ **Su questa
popolazione ho un'etichetta di verita' fatta a mano**, e un downgrade qui non
e' un sospetto: e' un **falso positivo documentato**.

\U0001f9ed **E CHIUDE UN LIMITE CHE HO DICHIARATO TRE VOLTE STASERA**: `W7-86`
e `W7-88` misurano su `truthfulqa`, **popolazione pubblica inglese**, e ogni
volta ho scritto *«i nostri verbali italiani sono un'altra distribuzione»*.
Questa **e'** quella distribuzione: fatti nostri, italiani, con fonti che sono
output di terminale.

\U0001f3af LA DOMANDA: **la classe descrittiva prende downgrade piu' spesso
della popolazione generale?**

ATTESA DICHIARATA PRIMA: **si', e piu' spesso** — un cross-encoder di
entailment cerca se la fonte IMPLICA il claim, ma qui la fonte **mostra** cio'
che il claim **descrive**, e le due cose non sono la stessa relazione logica.
⚠️ **Se il tasso fosse uguale o piu' basso, la nota di @lead-audit cade e lo
dico con la stessa forza.**

CONTROLLI CHE POSSONO FALLIRE:
 (1) 🪞 **DUE POPOLAZIONI APPAIATE**: descrittivi e non-descrittivi, stessa
     numerosita'. Su una sola classe ogni tasso sembra alto o basso senza
     metro.
 (2) ⚠️ **PREFLIGHT sul moat** (`W7-87`): senza, il gate ammette tutto con
     `L4-skipped` e il banco misura il warmup. 0/300 in 26s, gia' pagato.
 (3) \U0001f6a8 **IL CONFONDENTE, dichiarato**: i descrittivi possono essere
     diversi in altro modo — piu' lunghi, piu' tecnici, pieni di simboli. Il
     banco stampa **lunghezza mediana** delle due classi: se differiscono
     molto, il confronto e' sporco e va detto.
 (4) ✅ **controllo positivo**: qualche fatto deve passare in ENTRAMBE le
     classi. Se cadessero tutti, sto misurando un gate rotto e non una classe.

    python -u docs/stato-reale/banchi/la-classe-descrittiva-alla-porta-di-oggi.py
"""

from __future__ import annotations

import sqlite3
import statistics
import sys
import time

#: Il criterio di `W7-68`, ripreso IDENTICO per misurare la stessa classe:
#: una fonte che contiene un verdetto del gate. E' piu' largo del necessario e
#: la cella lo dichiarava gia'.
CHIAVI = ('"layer"', "admitted id=", "grounding_score=")
TETTO = 120  # per classe: a ~1,9s per giudizio sono ~8 minuti in tutto


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.config import CONFIG
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    c = sqlite3.connect(str(CONFIG.semantic_db))
    righe = c.execute(
        "select proposition, grounding_span from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> ''").fetchall()
    descr = [(p, s) for p, s in righe if any(k in (s or "") for k in CHIAVI)]
    altri = [(p, s) for p, s in righe if not any(k in (s or "") for k in CHIAVI)]
    print(f"  fatti vivi con fonte: {len(righe)}")
    print(f"  DESCRITTIVI (criterio di W7-68): {len(descr)}")
    print(f"  ALTRI                          : {len(altri)}")
    if len(descr) < 30:
        print("NON RIUSCITO: meno di trenta descrittivi, non misuro una quota.")
        return 1

    # (1) popolazioni APPAIATE per numerosita', e un campione DICHIARATO
    n = min(TETTO, len(descr), len(altri))
    passo = max(1, len(altri) // n)
    a = descr[:n]
    b = altri[::passo][:n]
    print(f"\n  campione DICHIARATO: {n} per classe"
          f"  (descrittivi: i primi {n} di {len(descr)}"
          f" · altri: uno ogni {passo} di {len(altri)})")

    # (3) il confondente: le due classi hanno la stessa taglia?
    for eti, pop in (("descrittivi", a), ("altri", b)):
        lc = statistics.median(len(p or "") for p, _s in pop)
        ls = statistics.median(len(s or "") for _p, s in pop)
        print(f"    {eti:<13} lunghezza mediana  claim {lc:.0f}"
              f"  ·  fonte {ls:.0f}")

    # (2) il preflight, senza il quale misuro il warmup
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

    def _passa(pop: list, eti: str) -> tuple[int, int, list[float]]:
        giu = fermati = 0
        punteggi: list[float] = []
        t = time.time()
        for i, (prop, span) in enumerate(pop):
            try:
                res = run_validation_gate(
                    proposition=prop, verified_by=None,
                    topic="banco/descrittivi", agent=None,
                    source=span, ground_write=True)
            except Exception:  # noqa: BLE001
                continue
            giu += 1
            if res.grounding_score is not None:
                punteggi.append(float(res.grounding_score))
            if res.action != "persist":
                fermati += 1
            if i and i % 50 == 0:
                print(f"    {eti}: ...{i}/{len(pop)} ({time.time() - t:.0f}s)")
        return giu, fermati, punteggi

    print("\n  -- ripasso i DESCRITTIVI alla porta di oggi")
    ga, fa, pa = _passa(a, "descr")
    print("\n  -- ripasso gli ALTRI (controllo appaiato)")
    gb, fb, pb = _passa(b, "altri")

    if not ga or not gb:
        print("NON RIUSCITO: una delle due classi non ha prodotto giudizi.")
        return 1

    qa, qb = 100.0 * fa / ga, 100.0 * fb / gb
    print("\n  == I DUE TASSI")
    print(f"     DESCRITTIVI  fermati {fa}/{ga}  ({qa:.1f}%)")
    print(f"     ALTRI        fermati {fb}/{gb}  ({qb:.1f}%)")
    if pa:
        print(f"     punteggio mediano  descrittivi {statistics.median(pa):.2f}"
              f"  ·  altri {statistics.median(pb):.2f}" if pb else "")

    # (4) il controllo che deve poter fallire
    if fa == ga and fb == gb:
        print("\n     CADUTO (controllo 4): cadono TUTTI in entrambe le"
              " classi.")
        print("     Sto misurando un gate rotto, non una classe.")
        return 1

    print("\n  == LA RIGA CHE CONTA")
    if qa > qb + 10.0:
        print("     \U0001f534 **LA NOTA DI @lead-audit REGGE**: la classe"
              " descrittiva prende")
        print(f"     downgrade nel **{qa:.1f}%** dei casi contro il"
              f" **{qb:.1f}%** degli altri.")
        print("     ⇒ E sono fatti che ho **letto a mano** in `W7-68` e"
              " giudicati")
        print("     legittimi: questi downgrade sono **falsi positivi"
              " documentati**,")
        print("     su **popolazione italiana vera** — non su un banco"
              " pubblico inglese.")
    elif qa > qb:
        print(f"     \U0001f7e1 **Differenza piccola**: {qa:.1f}% contro"
              f" {qb:.1f}%. La direzione e' quella")
        print("     della nota, la grandezza no: non basta per una cura.")
    else:
        print(f"     🟢 **LA NOTA NON REGGE su questa popolazione**:"
              f" {qa:.1f}% contro {qb:.1f}%.")
        print("     La classe descrittiva **non** e' penalizzata, e lo dico"
              " con la")
        print("     stessa forza con cui avrei detto il contrario.")

    print("\n  ⚠️ COSA NON DICE: i due gruppi possono differire per altro che"
          " la")
    print("  classe — le lunghezze mediane qui sopra dicono quanto · il"
          " criterio")
    print("  delle chiavi e' quello di `W7-68` e resta piu' largo del"
          " necessario ·")
    print("  l'etichetta «legittimi» vale per i 184 letti allora, non per"
          " ogni")
    print("  fatto che il criterio pesca oggi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
