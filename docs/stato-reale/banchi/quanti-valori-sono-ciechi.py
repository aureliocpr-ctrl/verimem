"""QUANTI VALORI NUMERICI FANNO CADERE UN CLAIM VERO.

\U0001f4cc **SEGUITO DI `W7-91`**, dove `1167` dava `0.52` e `1168` `99.96`
sulla stessa source e lo stesso claim. Quella cella dichiarava:

    ⛔ NON scrivibile: «il gate e' cieco ai numeri a quattro cifre» — 1168,
    1000, 2451 e 11670 passano ⇒ **sono singoli valori**, e **quanti siano
    non e' misurato**.

Questo banco misura quel numero. Il caso e' di @ws8, che non l'ha rivendicato:
gliel'avevo offerto sul canale e procedo come dichiarato.

\U0001f3af LA DOMANDA: **su un intervallo, quale frazione dei valori fa cadere
un claim vero sotto il cut?**

\U0001f511 **PERCHE' CONTA, e non e' curiosita'**: `W7-86` misura che **il moat
perde 73 degli 88 veri** su `truthfulqa`. Se una frazione non trascurabile dei
valori e' cieca, **una parte di quei falsi negativi ha una causa meccanica**,
non semantica — e il passo dopo e' guardare se i veri persi di `W7-86`
contengano valori ciechi.

⚠️ IL DISEGNO, e perche' non basta un intervallo contiguo: se spazzassi solo
1000-1300 e trovassi pochi ciechi, non saprei se il fenomeno e' raro **o se
quell'intervallo e' fortunato**. Quindi due popolazioni:

    CONTIGUA   1100-1250, tutti i valori          -> densita' locale
    SPARSA     valori su cinque ordini di grandezza -> il fenomeno e' uniforme?

ATTESA DICHIARATA PRIMA: **pochi ciechi, sotto il 5%**, e **sparsi senza
struttura visibile**. ⚠️ Se fossero molti (>20%) e' una causa sistemica e
cambia la lettura di `W7-86`. ⚠️ Se fossero **zero a parte 1167**, il fenomeno
e' un singolo punto patologico e va detto cosi': **un aneddoto misurato**, non
una classe.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **`1167` DEVE cadere**: e' la riproduzione. Se non cade, il giudice e'
     cambiato fra le due esecuzioni e mi fermo.
 (2) ✅ **la maggioranza DEVE passare**: se cadessero quasi tutti, non sto
     misurando valori ciechi ma un claim malformato.
 (3) ⚠️ **PREFLIGHT sul moat** (`W7-87`), senza il quale tutto passa con
     `L4-skipped` e il banco misura il warmup.
 (4) 🪞 **una sola source e un solo claim**: la variabile e' SOLO il valore.
     Cio' che ne esce vale per QUESTA coppia, e il banco lo dichiara.

    python -u docs/stato-reale/banchi/quanti-valori-sono-ciechi.py
"""

from __future__ import annotations

import sys
import time

SOURCE = "ORA 21:47:09 del 30/08 · coda: alfa={n} · beta=895 · gamma=13"
CLAIM = "Nella coda i alfa sono {n}."
CUT = 40.0

CONTIGUA = [str(n) for n in range(1100, 1251)]
SPARSA = [str(n) for n in
          (3, 7, 12, 19, 42, 77, 99, 128, 256, 314, 500, 512, 777, 999,
           1024, 1500, 1667, 1999, 2048, 2451, 3141, 4096, 5000, 6666,
           8192, 9999, 10000, 12345, 16384, 20000, 31415, 50000, 65536,
           99999, 100000, 123456)]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

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

    def _spazza(valori: list[str], eti: str) -> dict[str, float]:
        esiti: dict[str, float] = {}
        t = time.time()
        for i, n in enumerate(valori):
            try:
                res = run_validation_gate(
                    proposition=CLAIM.format(n=n), verified_by=None,
                    topic="banco/valori-ciechi", agent=None,
                    source=SOURCE.format(n=n), ground_write=True)
            except Exception:  # noqa: BLE001
                continue
            esiti[n] = (float(res.grounding_score)
                        if res.grounding_score is not None else -1.0)
            if i and i % 50 == 0:
                print(f"    {eti}: ...{i}/{len(valori)}"
                      f" ({time.time() - t:.0f}s)")
        return esiti

    print(f"\n  -- CONTIGUA: {CONTIGUA[0]}-{CONTIGUA[-1]}"
          f" ({len(CONTIGUA)} valori)")
    cont = _spazza(CONTIGUA, "cont")
    print(f"\n  -- SPARSA: {len(SPARSA)} valori su cinque ordini di grandezza")
    spar = _spazza(SPARSA, "spar")

    # (1) la riproduzione
    if "1167" not in cont:
        print("\nNON RIUSCITO: 1167 non e' stato giudicato.")
        return 1
    if cont["1167"] >= CUT:
        print(f"\n     CADUTO (controllo 1): 1167 da' {cont['1167']:.2f},"
              " sopra il cut.")
        print("     Il reperto di `W7-91` NON si riproduce: il giudice puo'"
              " essere")
        print("     cambiato. Verificare la build prima di concludere"
              " qualsiasi cosa.")
        return 1
    print(f"\n     ✅ controllo (1): 1167 -> {cont['1167']:.2f}, riprodotto")

    for eti, es in (("CONTIGUA", cont), ("SPARSA", spar)):
        ciechi = sorted((n for n, g in es.items() if g < CUT), key=int)
        quota = 100.0 * len(ciechi) / max(1, len(es))
        print(f"\n  == {eti}: {len(ciechi)} ciechi su {len(es)}"
              f"  ({quota:.1f}%)")
        if ciechi:
            print(f"     {', '.join(ciechi[:40])}"
                  f"{' …' if len(ciechi) > 40 else ''}")
        # (2) il controllo che deve poter fallire
        if quota > 50.0:
            print(f"     CADUTO (controllo 2): cade il {quota:.1f}%."
                  " Non sto misurando")
            print("     valori ciechi ma un claim malformato.")
            return 1

    tutti = {**cont, **spar}
    ciechi = sorted((n for n, g in tutti.items() if g < CUT), key=int)
    quota = 100.0 * len(ciechi) / max(1, len(tutti))
    print("\n  == LA RIGA CHE CONTA")
    if quota >= 20.0:
        print(f"     🔴 **{quota:.1f}% dei valori fa cadere un claim VERO**"
              f" ({len(ciechi)}/{len(tutti)}).")
        print("     ⇒ **Causa SISTEMICA**, non un punto patologico: cambia la"
              " lettura")
        print("     dei veri persi di `W7-86`, e il passo dopo e' guardare se"
              " quelli")
        print("     contengano valori di questa lista.")
    elif len(ciechi) > 1:
        print(f"     🟡 **{len(ciechi)} valori ciechi su {len(tutti)}"
              f" ({quota:.1f}%)**: il fenomeno")
        print("     esiste oltre `1167` ma e' **raro**. Non e' una classe e"
              " non spiega")
        print("     `W7-86` da solo — resta un difetto reale su casi"
              " singoli.")
    else:
        print("     🟢 **SOLO `1167`**: nessun altro valore cade in"
              f" {len(tutti)} provati.")
        print("     ⇒ **E' un punto patologico isolato, non una classe.**"
              " `W7-91`")
        print("     resta vera e resta un **aneddoto misurato**: lo dico con"
              " la")
        print("     stessa forza con cui avrei annunciato una causa"
              " sistemica.")

    bassi = sorted(((g, n) for n, g in tutti.items() if CUT <= g < 90))
    print(f"\n  -- la fascia intermedia (cut ≤ g < 90): {len(bassi)} valori")
    for g, n in bassi[:10]:
        print(f"     {n:>7}  {g:6.2f}")

    print("\n  ⚠️ COSA NON DICE: **una sola coppia source/claim** — un altro")
    print("  contesto puo' avere altri valori ciechi, e questa quota non si")
    print("  trasferisce · non spiega **perche'** · e non dice se i valori")
    print("  ciechi siano gli stessi fra build diverse del giudice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
