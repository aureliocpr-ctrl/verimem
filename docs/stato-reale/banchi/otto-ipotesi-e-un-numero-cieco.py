"""OTTO IPOTESI LINGUISTICHE CADUTE, E LA CAUSA ERA UN NUMERO.

\U0001f4cc **IL CASO E' DI @ws8**, che l'ha isolato e ha fatto cadere cinque
ipotesi prima di me. Questo banco fa il test che aveva dichiarato mancante — e
poi altri tre, perche' anche quello e' caduto.

IL FALSO NEGATIVO, dal suo messaggio delle 21:51::

    source: "ORA 21:47:09 del 30/08 · coda: completed=1167 · queued=895
             · in_progress=13"
    «…i completed sono 1167.»  ->  0.58  🔴   (VERO, e la source lo dice)
    «…i queued sono 895.»      -> 99.43  ✅   (VERO)

LE OTTO IPOTESI, tutte eseguite e tutte cadute::

    SUE   ① il glifo nella source        tolto: 0.2528 -> 0.2352   identico
          ② due affermazioni in una      una frase con DUE passa a 99.97
          ③ la source non ha i numeri    li contiene tutti
          ④ e' la parola inglese in IT   «completati» 0.51 · «conclusi» 0.42
          ⑤ e' un numero a 4 cifre       delta=2451 -> 98.56 in gemella
    MIE   ⑥ e' la parola `completed`     cade anche `alfa`, che non vuol dire
                                          niente
          ⑦ e' la POSIZIONE nella source alfa PRIMO 0,52 e beta SECONDO 99,97,
                                          ma alfa SECONDO cade lo stesso (0,63)
          ⑧ e' il PREFISSO `ORA…·`       tolto, sostituito, ridotto: cade
                                          sempre

\U0001f3af **E LA VARIABILE CHE RESTAVA, tenuta ferma da tutti e otto senza
accorgersene: IL VALORE.**

    source: "ORA 21:47:09 del 30/08 · coda: alfa=<N> · beta=895 · gamma=13"
    claim : "Nella coda i alfa sono <N>."

    alfa=1167     0.52  🔴   <- il solo che cade
    alfa=1168    99.96  ✅   <- piu' uno
    alfa=1000    99.97  ✅      alfa=895   99.97  ✅
    alfa=116     99.93  ✅      alfa=11670 99.94  ✅
    alfa=13      99.90  ✅      alfa=7     99.94  ✅
    alfa=2451    43.33  🟡   <- sopra il cut, ma dieci volte piu' basso

⇒ 🔑 **`1167` e `1168` differiscono di UNO e il verdetto passa da 0,52 a
99,96.** Nessuna lettura linguistica regge: **e' il token numerico**.

⚖️ **E `completed` e' scagionato**: la STESSA informazione nella forma della
source (`completed=1167`) passa a **99,82**; e' la riscrittura in prosa che
cade. Il giudice non ha nulla contro quella parola.

⚠️ **COSA NON E' SCRIVIBILE**: *«il gate e' cieco ai numeri a quattro cifre»* —
`1168`, `1000`, `2451` e `11670` passano. **Non e' una classe, sono singoli
valori**, e quanti siano non e' misurato: si spazza un intervallo con la stessa
source e si conta.

❓ **UNA DISCREPANZA APERTA**: il controllo ⑤ di @ws8 dava `alfa=1167 -> 99.96`
su una source gemella, il mio da' `0.52`. Stesso nome, stesso numero, esiti
opposti ⇒ **la differenza e' nella source**, e senza la sua verbatim non la
chiudo. Se il suo 99,96 regge, `1167` non e' cieco *in assoluto* ma **dentro
certe source**, che e' un reperto piu' stretto.

\U0001fa9e **LA LEZIONE**: quando otto ipotesi linguistiche cadono di fila, **la
causa non e' nel testo**. Il testo e' cio' che si legge, ma il decisore e' un
modello — e i modelli hanno punti ciechi che nessuna grammatica predice.

    python -u docs/stato-reale/banchi/otto-ipotesi-e-un-numero-cieco.py
"""

from __future__ import annotations

import sys
import time

SOURCE = "ORA 21:47:09 del 30/08 · coda: alfa={n} · beta=895 · gamma=13"
CLAIM = "Nella coda i alfa sono {n}."
#: 1167 e' il caso; 1168 e' il vicino che deve passare; gli altri danno il
#: contesto. Se cadessero TUTTI, non avrei isolato niente.
NUMERI = ["1167", "1168", "1000", "895", "116", "11670", "13", "7", "2451"]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    # ⚠️ Senza questo il gate ammette tutto con `L4-skipped` (`W7-87`).
    print("  -- preflight: il moat deve essere CALDO")
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

    print(f"\n  source: {SOURCE.format(n='<N>')}")
    print(f"  claim : {CLAIM.format(n='<N>')}\n")
    esiti: dict[str, float] = {}
    for n in NUMERI:
        try:
            res = run_validation_gate(
                proposition=CLAIM.format(n=n), verified_by=None,
                topic="banco/numero-cieco", agent=None,
                source=SOURCE.format(n=n), ground_write=True)
        except Exception as e:  # noqa: BLE001
            print(f"     alfa={n:<7} ERRORE {type(e).__name__}: {e}")
            continue
        g = float(res.grounding_score) if res.grounding_score is not None \
            else -1.0
        esiti[n] = g
        print(f"  {'🔴' if g < 40 else ('🟡' if g < 80 else '✅')}"
              f" {g:>7.2f}   alfa={n}")

    if "1167" not in esiti or "1168" not in esiti:
        print("\nNON RIUSCITO: mancano i due casi del confronto.")
        return 1

    # Il controllo che deve poter fallire: se cadessero tutti, la variabile
    # isolata non e' il valore ma qualcosa che non ho tenuto fermo.
    passati = [n for n, g in esiti.items() if g >= 40]
    if len(passati) < 2:
        print(f"\n     CADUTO: passano solo {passati}. Non ho isolato il"
              " valore,")
        print("     sto misurando qualcos'altro che non ho tenuto fermo.")
        return 1

    print("\n  == LA RIGA CHE CONTA")
    a, b = esiti["1167"], esiti["1168"]
    if a < 40 <= b:
        print(f"     🔴 **`1167` da' {a:.2f} e `1168` da' {b:.2f}**:"
              " differiscono di UNO")
        print("     e il verdetto si ribalta. ⇒ **La causa non e' nel testo:"
              " e' il")
        print("     token numerico.** Otto ipotesi linguistiche cadute prima"
              " di questa.")
        print(f"     Passano {len(passati)} valori su {len(esiti)}: non e'"
              " una classe,")
        print("     **sono singoli valori**, e quanti siano non e' misurato.")
    else:
        print(f"     🟢 **NON si riproduce**: 1167 -> {a:.2f} · 1168 ->"
              f" {b:.2f}.")
        print("     Il reperto del 30/08 non regge in questa esecuzione, e va"
              " detto")
        print("     con la stessa forza. Il giudice puo' essere cambiato: -"
              " verificare")
        print("     la build prima di concludere.")

    print("\n  ⚠️ COSA NON DICE: **una sola source** · non spiega **perche'**"
          " (un CE")
    print("  distillato non si interroga) · **il caso e il perimetro sono di"
          " @ws8**:")
    print("  qui e' isolata una variabile che le otto ipotesi tenevano ferma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
