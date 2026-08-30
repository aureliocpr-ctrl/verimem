"""LA SONDA DEL VICINO SUL CORPUS NOSTRO, DOVE I NUMERI CI SONO.

\U0001f4cc **SEGUITO DI `W7-93`**, che ha fallito e ha detto perche': su
`truthfulqa` **1 solo dei 73 veri persi porta un numero** — quel dataset e'
discorsivo. La domanda restava buona, sbagliata era la popolazione.

\U0001f511 **I NOSTRI VERBALI SONO L'OPPOSTO**: «i run completed sono 1167»,
«88/300 veri fermati», «`grounding_span` max 932». **Se la cecita' numerica di
`W7-91`/`W7-92` morde da qualche parte, morde qui.**

\U0001f3af LA DOMANDA: **fra i fatti del corpus che il moat ha bocciato e che
portano un numero, quanti RISALGONO sostituendo quel numero con il vicino
`n+1`** — in claim E fonte insieme, cosi' il claim resta vero e cambia solo il
token?

ATTESA DICHIARATA PRIMA: **piu' alta che su `truthfulqa`** (dove la domanda non
era nemmeno ponibile), ma **sotto il 20%**: `W7-92` misura chiazze locali, non
una cecita' diffusa. ⚠️ **Se fosse >30% e' un difetto che tocca i nostri fatti
tutti i giorni** e va portato al gruppo come tale. ⚠️ **Se fosse ~0, `W7-92`
resta un fenomeno di laboratorio** e lo dico con la stessa forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) 🪞 **CONTROLLO NEGATIVO OBBLIGATORIO**: la stessa sostituzione sui fatti
     **AMMESSI**. Se anche li' l'esito ballasse, la sonda non isola niente e il
     numero non va usato. E' il controllo che ha salvato `W7-93`.
 (2) ⚠️ **PREFLIGHT sul moat** (`W7-87`).
 (3) 📊 **il baseline si RIGIUDICA**: il `grounding_score` nel DB e' quello
     del momento della scrittura, con build e soglie di allora. Confrontare un
     punteggio storico con uno di oggi misurerebbe il tempo, non il numero.
 (4) ⚖️ **il numero deve stare in ENTRAMBI** claim e fonte: se sta solo nel
     claim, sostituirlo non conserva la verita' e misurerei altro.

    python -u docs/stato-reale/banchi/il-vicino-sul-corpus-vero.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
import time

CUT = 40.0
NUM = re.compile(r"(?<![\d.,])(\d{2,})(?![\d.,])")
TETTO = 45  # per popolazione: 2 giudizi ciascuno, ~1,3s l'uno


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
        "select proposition, grounding_span, status from facts "
        "where superseded_by is null and grounding_span is not null "
        "and grounding_span <> '' and proposition is not null").fetchall()

    # (4) il numero deve stare in entrambi
    def _candidati(rr: list) -> list:
        out = []
        for prop, span, st in rr:
            comuni = [n for n in set(NUM.findall(prop)) if n in span]
            if comuni:
                out.append((prop, span, st, comuni[0]))
        return out

    tutti = _candidati(righe)
    print(f"  fatti vivi con fonte: {len(righe)}")
    print(f"  …con un numero presente in ENTRAMBI: {len(tutti)}"
          f"  ({100.0 * len(tutti) / max(1, len(righe)):.1f}%)")
    if len(tutti) < 20:
        print("NON RIUSCITO: meno di venti candidati. La domanda e' mal posta")
        print("anche qui, e lo dico invece di spremere una quota.")
        return 1

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

    def _g(claim: str, source: str) -> float:
        try:
            res = run_validation_gate(
                proposition=claim, verified_by=None, topic="banco/vicino-vero",
                agent=None, source=source, ground_write=True)
        except Exception:  # noqa: BLE001
            return -1.0
        return (float(res.grounding_score)
                if res.grounding_score is not None else -1.0)

    # (3) il baseline si rigiudica OGGI, non si legge dal DB
    print(f"\n  -- rigiudico il baseline su {min(TETTO * 4, len(tutti))}"
          " candidati (i punteggi storici sono di build diverse)")
    sotto, sopra = [], []
    t = time.time()
    for i, (prop, span, _st, n) in enumerate(tutti[:TETTO * 4]):
        g = _g(prop, span)
        if g < 0:
            continue
        (sotto if g < CUT else sopra).append((prop, span, n, g))
        if i and i % 50 == 0:
            print(f"    ...{i} ({time.time() - t:.0f}s)")
    print(f"     sotto il cut OGGI: {len(sotto)}  ·  sopra: {len(sopra)}")
    if len(sotto) < 5:
        print("NON RIUSCITO: meno di cinque fatti sotto il cut fra i")
        print("candidati: non ho una popolazione di persi su cui misurare.")
        return 1

    def _vicino(pop: list, eti: str) -> tuple[int, int, list]:
        cambi, provati, esempi = 0, 0, []
        for prop, span, n, g0 in pop[:TETTO]:
            try:
                nuovo = str(int(n) + 1)
            except ValueError:
                continue
            cl, src = prop.replace(n, nuovo), span.replace(n, nuovo)
            if cl == prop or src == span:
                continue
            g1 = _g(cl, src)
            if g1 < 0:
                continue
            provati += 1
            if (g0 < CUT) != (g1 < CUT):
                cambi += 1
                if len(esempi) < 5:
                    esempi.append((n, nuovo, g0, g1, prop[:64]))
        print(f"     {eti}: {cambi} cambi di esito su {provati} provati")
        return cambi, provati, esempi

    print("\n  -- sostituisco il numero col VICINO (n+1) in claim E fonte")
    c_sotto, p_sotto, es = _vicino(sotto, "SOTTO il cut")
    c_sopra, p_sopra, _ = _vicino(sopra, "SOPRA il cut (controllo)")

    if not p_sotto or not p_sopra:
        print("NON RIUSCITO: una delle due popolazioni non ha prodotto"
              " sostituzioni.")
        return 1
    q_sotto = 100.0 * c_sotto / p_sotto
    q_sopra = 100.0 * c_sopra / p_sopra

    print("\n  == LA RIGA CHE CONTA")
    print(f"     bocciati che RISALGONO col vicino: {c_sotto}/{p_sotto}"
          f"  ({q_sotto:.1f}%)")
    print(f"     ammessi che CADONO col vicino    : {c_sopra}/{p_sopra}"
          f"  ({q_sopra:.1f}%)   <- rumore")

    # (1) il controllo che deve poter fallire
    if q_sopra >= q_sotto:
        print("\n     🟢 **LA SONDA NON ISOLA NULLA**: il vicino muove gli"
              " ammessi quanto")
        print("     i bocciati. Il numero sopra **non va usato**, e"
              " `W7-92` non e'")
        print("     dimostrato sul corpus. Lo dico con la stessa forza.")
    elif q_sotto >= 30.0:
        print(f"\n     🔴 **{q_sotto:.1f}% dei bocciati risale cambiando SOLO"
              " il numero**,")
        print(f"     contro un rumore del {q_sopra:.1f}%.")
        print("     ⇒ **La cecita' numerica tocca i NOSTRI fatti**, non e' un")
        print("     fenomeno di laboratorio: un fatto vero cade perche' porta"
              " un")
        print("     numero sfortunato, e succede ogni giorno.")
    elif c_sotto:
        print(f"\n     🟡 **{q_sotto:.1f}% ({c_sotto} casi)**, rumore"
              f" {q_sopra:.1f}%: il fenomeno")
        print("     esiste sul corpus ma e' **minoritario**.")
    else:
        print("\n     🟢 **ZERO**: nessun bocciato risale cambiando il numero.")
        print("     ⇒ **`W7-92` resta un fenomeno di laboratorio** e non"
              " spiega")
        print("     i rifiuti del corpus.")

    if es:
        print("\n  esempi di cambio d'esito:")
        for n, nu, g0, g1, cl in es:
            print(f"     {n}->{nu}   {g0:6.2f} -> {g1:6.2f}   «{cl}…»")

    print("\n  ⚠️ COSA NON DICE: **`n+1` e' UNA sonda**, non tutte le"
          " vicinanze ·")
    print("  i tetti per popolazione sono dichiarati · un cambio d'esito prova")
    print("  che in QUELLA coppia il verdetto dipende dal token numerico,"
          " non che")
    print("  il valore sia cieco in assoluto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
