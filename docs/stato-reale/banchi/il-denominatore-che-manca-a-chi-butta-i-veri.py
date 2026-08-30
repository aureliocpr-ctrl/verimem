"""IL DENOMINATORE CHE MANCA A «A BUTTARE I VERI E' IL MOAT, 25 SU 29».

⚠️ **QUESTO BANCO VERIFICA LA PREMESSA DI UN ORDINE**, e lo dichiaro subito
perche' il conflitto d'interessi va scritto, non nascosto: l'ordine dice di
spostare la priorita' della cura **sul giudice/cut** proprio perche' *«25 dei 29
veri persi sono fermati dal moat»*. Se la premessa non regge, la cura va altrove
— e l'unico modo di saperlo e' misurare.

🔑 **PERCHE' 25/29 NON BASTA, e non e' una critica a chi l'ha misurato**: e' un
**conteggio senza denominatore**. Il moat giudica **ogni** claim che ha una
fonte; un layer lessicale interviene **solo** quando il suo pattern matcha. Un
decisore che vede cento volte piu' casi produce piu' errori in valore assoluto
**anche quando il suo tasso e' migliore**. La domanda leggibile e':

    su quanti VERI ciascun decisore ha avuto l'occasione di sbagliare,
    e su quanti di quelli ha sbagliato davvero?

E' la stessa forma di due errori gia' pagati oggi in casa: contare i **riusi**
invece dei **fatti** (`W7-80`, 83,6% contro 49,8%), e misurare **un'altra leva**
credendo fosse quella (`W7-79`, 1,02% contro 3,00%).

ATTESA DICHIARATA PRIMA DI GUARDARE: il moat fermera' **la maggioranza in valore
assoluto** (giudica tutti), ma il suo **tasso** sui veri sara' **piu' basso** di
quello di almeno un layer lessicale. ⚠️ **Se il tasso del moat fosse il
PEGGIORE, l'ordine ha ragione e lo dico con la stessa forza** — e la cura sul
cut parte con una base misurata invece che con un conteggio.

CONTROLLI CHE POSSONO FALLIRE:
 (1) ✅ **controllo positivo sui FALSI**: devono essere fermati in maggioranza.
     Se il gate fosse spento, il conto sui veri non significherebbe nulla.
 (2) 🪞 **ENTRAMBE le popolazioni**, 300 veri e 300 falsi: su un banco di soli
     veri ogni decisore sembra dannoso, su uno di soli falsi sembra ottimo.
 (3) 📊 **POPOLAZIONE INTERA** (600 claim, l'intero heldout): a 0,1s per
     giudizio dopo il caricamento del modello non serve campionare, quindi non
     c'e' un campione da difendere.
 (4) ⚖️ **il moat e' `L4-grounding`**, che compare fra i `warnings` quando
     `grounding_score < threshold`. Gli altri layer sono i layer lessicali. Se
     un claim e' fermato senza NESSUN warning, lo conto a parte: sarebbe un
     decisore che non si dichiara, ed e' un reperto suo.

    python -u docs/stato-reale/banchi/il-denominatore-che-manca-a-chi-butta-i-veri.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter

DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
MOAT = "L4-grounding"


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    try:
        righe = [json.loads(x) for x in open(DATI, encoding="utf-8")
                 if x.strip()]
    except OSError as e:
        print(f"NON RIUSCITO: dataset illeggibile - {e}")
        return 1

    veri = [r for r in righe if r.get("label") == 1]
    falsi = [r for r in righe if r.get("label") == 0]
    print(f"  dataset: {DATI}")
    print(f"  VERI {len(veri)}   FALSI {len(falsi)}   (popolazione INTERA)")
    if len(veri) < 50 or len(falsi) < 50:
        print("NON RIUSCITO: meno di cinquanta per popolazione.")
        return 1

    # scattato[layer] = su quanti claim il layer si e' pronunciato
    # fermato[layer]  = su quanti di quelli l'esito e' stato negativo
    def _giudica(claim: list[dict], etichetta: str) -> dict[str, object]:
        scattato: Counter[str] = Counter()
        fermato: Counter[str] = Counter()
        muti = 0
        negativi = 0
        t0 = time.time()
        for i, r in enumerate(claim):
            res = run_validation_gate(
                proposition=r["claim"], verified_by=None,
                topic="banco/denominatore", agent=None,
                source=r["source"], ground_write=True)
            layers = {w.get("layer") for w in (res.warnings or [])
                      if isinstance(w, dict) and w.get("layer")}
            negativo = res.action != "persist"
            # Il MOAT si pronuncia SEMPRE: ha una fonte da confrontare, quindi
            # ha sempre l'occasione di sbagliare. I layer lessicali no.
            scattato[MOAT] += 1
            for lay in layers:
                if lay != MOAT:
                    scattato[lay] += 1
            if negativo:
                negativi += 1
                if MOAT in layers:
                    fermato[MOAT] += 1
                for lay in layers:
                    if lay != MOAT:
                        fermato[lay] += 1
                if not layers:
                    muti += 1
            if i and i % 100 == 0:
                print(f"    ...{i}/{len(claim)} ({time.time() - t0:.0f}s)")
        return {"scattato": scattato, "fermato": fermato, "muti": muti,
                "negativi": negativi, "n": len(claim),
                "secondi": time.time() - t0, "etichetta": etichetta}

    print("\n  -- giudico i VERI (l'esito negativo qui e' un ERRORE)")
    v = _giudica(veri, "veri")
    print(f"     {v['negativi']}/{v['n']} veri fermati"
          f"  ({100.0 * int(v['negativi']) / int(v['n']):.1f}%)"
          f"  in {float(v['secondi']):.0f}s")

    # ⚠️ LA TABELLA SI STAMPA QUI, PRIMA DEI FALSI — e non e' un dettaglio di
    #    forma. La prima esecuzione (30/08, 20:19) e' stata uccisa dal timeout
    #    DOPO i veri e PRIMA della stampa: 573s di giudizi buttati, perche' il
    #    risultato principale stava in coda a una misura di controllo. La
    #    lezione e' che l'ordine di stampa e' parte del disegno: **cio' che
    #    risponde alla domanda va emesso appena e' noto**, il controllo dopo.
    _tabella(sc=v["scattato"], fe=v["fermato"],  # type: ignore[arg-type]
             muti=int(v["muti"]))

    print("\n  -- giudico i FALSI (l'esito negativo qui e' il LAVORO)")
    f = _giudica(falsi, "falsi")
    print(f"     {f['negativi']}/{f['n']} falsi fermati"
          f"  ({100.0 * int(f['negativi']) / int(f['n']):.1f}%)")

    # (1) il controllo che deve poter fallire
    quota_falsi = 100.0 * int(f["negativi"]) / int(f["n"])
    if quota_falsi < 50.0:
        print(f"\n     🔴 CADUTO (controllo 1): solo {quota_falsi:.1f}% dei"
              " falsi fermati.")
        print("     Il gate e' spento e IL CONTO SUI VERI QUI SOPRA NON"
              " SIGNIFICA NULLA.")
        return 1
    print(f"     ✅ controllo (1) superato: il gate ferma {quota_falsi:.1f}%"
          " dei falsi,")
    print("     quindi il conto sui veri e' leggibile.")
    return 0


def _tabella(*, sc: Counter, fe: Counter, muti: int) -> None:
    """La tabella dei tassi sui VERI. Separata perche' va emessa appena i veri
    sono finiti: e' la risposta alla domanda, non il controllo."""
    print("\n  == LA TABELLA CHE MANCAVA: numeratore E denominatore")
    print("     («scattato» = quante volte quel decisore si e' pronunciato"
          " su un VERO)")
    print(f"\n     {'decisore':<32}{'scattato':>9}{'fermati':>9}{'tasso':>9}")
    righe_tab = []
    for lay, n_sc in sc.most_common():
        n_fe = fe.get(lay, 0)
        if n_sc == 0:
            continue
        tasso = 100.0 * n_fe / n_sc
        righe_tab.append((lay, n_sc, n_fe, tasso))
    for lay, n_sc, n_fe, tasso in sorted(righe_tab, key=lambda t: -t[3]):
        segno = "🔴" if tasso >= 50 else ("🟡" if tasso >= 20 else "  ")
        print(f"  {segno} {lay:<32}{n_sc:>9}{n_fe:>9}{tasso:>8.1f}%")
    if muti:
        print(f"\n     ⚠️ {muti} veri fermati SENZA alcun warning:"
              " un decisore che non si dichiara.")

    print("\n  == LA RIGA CHE CONTA")
    moat_sc, moat_fe = sc.get(MOAT, 0), fe.get(MOAT, 0)
    moat_tasso = 100.0 * moat_fe / moat_sc if moat_sc else 0.0
    peggiori = [t for t in righe_tab if t[0] != MOAT and t[3] > moat_tasso]
    print(f"     moat (`{MOAT}`): **{moat_fe} veri fermati su {moat_sc}"
          f" giudicati = {moat_tasso:.1f}%**")
    if not peggiori:
        print("     🔴 **NESSUN layer ha un tasso peggiore del moat.**")
        print("     ⇒ La premessa REGGE anche col denominatore: il moat non e'")
        print("     solo il piu' numeroso, e' il **piu' sbagliato in"
              " proporzione**.")
        print("     ⇒ **Spostare la cura sul giudice/cut e' motivato.**")
    else:
        print(f"     🟢 **{len(peggiori)} layer hanno un tasso PEGGIORE del"
              " moat**:")
        for lay, n_sc, n_fe, tasso in sorted(peggiori, key=lambda t: -t[3]):
            print(f"        {lay:<30}{n_fe:>5}/{n_sc:<5} = {tasso:.1f}%")
        print("     ⇒ **Il moat e' il piu' numeroso perche' giudica TUTTI**,")
        print("     non perche' sia il piu' impreciso. Il conteggio assoluto"
              " indicava")
        print("     il decisore sbagliato: **la cura piu' redditizia per"
              " CASO CURATO**")
        print("     sta sui layer qui sopra, quella per VOLUME resta sul"
              " moat.")

    print("\n  ⚠️ COSA NON DICE: **una popolazione pubblica in inglese** —"
          " i nostri")
    print("  verbali italiani sono un'altra distribuzione, e su quella il"
          " rapporto")
    print("  puo' cambiare · il tasso NON dice quanto costa l'errore, solo"
          " quanto")
    print("  e' frequente · e un layer con pochi «scattato» ha un tasso"
          " fragile:")
    print("  guardare il denominatore prima di credere alla percentuale.")


if __name__ == "__main__":
    sys.exit(main())
