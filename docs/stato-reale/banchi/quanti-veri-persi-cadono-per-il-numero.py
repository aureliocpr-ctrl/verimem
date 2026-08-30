"""DEI VERI PERSI, QUANTI CADONO PER IL NUMERO E NON PER IL CONTENUTO.

\U0001f9ed **CHIUDE IL CERCHIO fra tre celle mie di stasera**:

    W7-86  dei veri persi, il moat ne boccia 73 su 88
    W7-91  `1167` da' 0.52 e `1168` da' 99.96 — la causa e' il VALORE
    W7-92  i valori ciechi sono a CHIAZZE (42,5% in 1160-1199, 0,0% altrove)

\U0001f3af LA DOMANDA: **fra i veri che il gate perde, quanti cadono perche' il
loro numero e' sfortunato?** Se la quota fosse non trascurabile, **una parte
dei falsi negativi ha causa MECCANICA e non semantica**, e si cura in un modo
completamente diverso.

\U0001f511 **IL TEST, e perche' e' questo**: prendo ogni vero perso che porta
un numero e **sostituisco quel numero con un vicino (`n+1`) SIA nel claim SIA
nella fonte**. Il claim resta **vero** — cambia solo quale token numerico e' in
gioco. Se il punteggio **risale sopra il cut**, la caduta era del valore; se
resta giu', era del contenuto.

⚠️ **PERCHE' IN ENTRAMBI**: cambiando il numero solo nel claim lo renderei
**falso**, e misurerei il gate che fa il suo lavoro. E' l'errore che ho gia'
commesso stasera in `W7-91` — il controllo del banco l'ha intercettato e mi ha
impedito di pubblicare dodici numeri che sembravano una scoperta.

⚠️ **E la cecita' dipende dal CONTESTO** (limite dichiarato in `W7-92`: *«una
sola coppia source/claim»*), quindi ogni valore va provato **nella sua**, mai
nella source del banco precedente.

ATTESA DICHIARATA PRIMA: **una quota piccola, sotto il 10%** dei veri persi con
numero. ⚠️ **Se fosse alta (>30%), la lettura di `W7-86` cambia**: una fetta
dei falsi negativi non e' un problema di giudizio ma di dominio. ⚠️ **Se fosse
zero, `W7-91` resta un caso costruito che non tocca la popolazione reale**, e
va detto con la stessa forza.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **il vicino non deve cambiare il senso**: `n+1` su una quantita' resta
     una quantita'. Il claim modificato e' vero quanto l'originale.
 (2) 🪞 **CONTROLLO NEGATIVO**: la stessa sostituzione sui veri **AMMESSI**.
     Se anche li' il punteggio ballasse molto, la sostituzione muove tutto e
     non isola niente.
 (3) ⚠️ **PREFLIGHT sul moat** (`W7-87`), senza il quale tutto passa con
     `L4-skipped`.
 (4) 📊 **quanti veri persi portano un numero**: se fossero pochissimi, la
     domanda e' mal posta su questa popolazione e lo dico.

    python -u docs/stato-reale/banchi/quanti-veri-persi-cadono-per-il-numero.py
"""

from __future__ import annotations

import json
import re
import sys
import time

DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
CUT = 40.0
#: numeri "sostanziali": salto le cifre isolate 0-9, dove `n+1` cambia poco e
#: il rumore lessicale e' alto.
NUM = re.compile(r"(?<![\d.,])(\d{2,})(?![\d.,])")


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.local_grounding import judge_state, warm_local_judge_async
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    righe = [json.loads(x) for x in open(DATI, encoding="utf-8") if x.strip()]
    veri = [r for r in righe if r.get("label") == 1]
    print(f"  veri nell'heldout: {len(veri)}")

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
                proposition=claim, verified_by=None, topic="banco/num-persi",
                agent=None, source=source, ground_write=True)
        except Exception:  # noqa: BLE001
            return -1.0
        return (float(res.grounding_score)
                if res.grounding_score is not None else -1.0)

    print("\n  -- giudico i veri (per sapere quali si perdono)")
    persi, ammessi = [], []
    t = time.time()
    for i, r in enumerate(veri):
        g = _g(r["claim"], r["source"])
        (persi if g < CUT else ammessi).append((r, g))
        if i and i % 100 == 0:
            print(f"    ...{i}/{len(veri)} ({time.time() - t:.0f}s)")
    print(f"     persi {len(persi)}/{len(veri)}  ·  ammessi {len(ammessi)}")

    # (4) la domanda e' ben posta su questa popolazione?
    def _con_numero(pop: list) -> list:
        out = []
        for r, g in pop:
            nel_claim = set(NUM.findall(r["claim"]))
            comuni = [n for n in nel_claim if n in r["source"]]
            if comuni:
                out.append((r, g, comuni[0]))
        return out

    pn, an = _con_numero(persi), _con_numero(ammessi)
    print(f"\n  -- (4) veri PERSI che portano un numero presente anche nella"
          f" fonte: {len(pn)}/{len(persi)}")
    print(f"        veri AMMESSI idem (controllo negativo): {len(an)}"
          f"/{len(ammessi)}")
    if len(pn) < 5:
        print("NON RIUSCITO: meno di cinque veri persi con numero. La domanda")
        print("e' mal posta su questa popolazione, e lo dico invece di")
        print("spremere una quota da pochi casi.")
        return 1

    def _prova_vicino(casi: list, eti: str) -> tuple[int, int, list]:
        risaliti, provati, esempi = 0, 0, []
        for r, g0, n in casi[:60]:
            try:
                nuovo = str(int(n) + 1)
            except ValueError:
                continue
            cl = r["claim"].replace(n, nuovo)
            src = r["source"].replace(n, nuovo)
            if cl == r["claim"] or src == r["source"]:
                continue
            g1 = _g(cl, src)
            provati += 1
            if (g0 < CUT) != (g1 < CUT):
                risaliti += 1
                if len(esempi) < 5:
                    esempi.append((n, nuovo, g0, g1, r["claim"][:60]))
        print(f"     {eti}: {risaliti} cambi di esito su {provati} provati")
        return risaliti, provati, esempi

    print("\n  -- sostituisco il numero con il VICINO (n+1) in claim E fonte")
    r_persi, p_persi, es = _prova_vicino(pn, "PERSI  ")
    # (2) il controllo negativo
    r_amm, p_amm, _ = _prova_vicino(an, "AMMESSI")

    if not p_persi:
        print("NON RIUSCITO: nessuna sostituzione applicabile.")
        return 1
    quota = 100.0 * r_persi / p_persi
    quota_amm = 100.0 * r_amm / max(1, p_amm)

    print("\n  == LA RIGA CHE CONTA")
    print(f"     veri PERSI che RISALGONO cambiando solo il numero:"
          f" {r_persi}/{p_persi}  ({quota:.1f}%)")
    print(f"     veri AMMESSI che CADONO con la stessa mossa:"
          f" {r_amm}/{p_amm}  ({quota_amm:.1f}%)   <- rumore")

    if quota_amm >= quota:
        print("\n     🟢 **NON isola nulla**: la sostituzione muove gli ammessi"
              " quanto")
        print("     i persi. Il vicino non e' una sonda valida su questa"
              " popolazione,")
        print("     e il numero sopra NON va usato. Lo dico con la stessa"
              " forza.")
    elif quota >= 30.0:
        print(f"\n     🔴 **{quota:.1f}% dei veri persi risale cambiando SOLO"
              " il numero**,")
        print(f"     contro un rumore del {quota_amm:.1f}% sugli ammessi.")
        print("     ⇒ **Una fetta dei falsi negativi ha causa MECCANICA**, non")
        print("     semantica: cambia la lettura di `W7-86` e si cura in modo")
        print("     completamente diverso.")
    elif r_persi:
        print(f"\n     🟡 **{quota:.1f}% ({r_persi} casi)**, rumore"
              f" {quota_amm:.1f}%: il fenomeno")
        print("     tocca la popolazione reale ma **e' minoritario**. `W7-91`"
              " non e'")
        print("     un caso costruito, e non spiega `W7-86`.")
    else:
        print("\n     🟢 **ZERO**: nessun vero perso risale cambiando il"
              " numero.")
        print("     ⇒ **`W7-91` resta vero come caso e NON tocca questa"
              " popolazione**:")
        print("     i veri persi qui cadono per il contenuto. Lo dico con la")
        print("     stessa forza con cui avrei annunciato una causa"
              " meccanica.")

    if es:
        print("\n  esempi di cambio d'esito:")
        for n, nu, g0, g1, cl in es:
            print(f"     {n}->{nu}   {g0:6.2f} -> {g1:6.2f}   «{cl}…»")

    print("\n  ⚠️ COSA NON DICE: **`n+1` e' UNA sonda**, non tutte le vicinanze"
          " ·")
    print("  il tetto di 60 casi per popolazione e' dichiarato · e un cambio"
          " di")
    print("  esito non prova che il valore sia «cieco» in assoluto: prova che"
          " in")
    print("  QUELLA coppia il verdetto dipende dal token numerico.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
