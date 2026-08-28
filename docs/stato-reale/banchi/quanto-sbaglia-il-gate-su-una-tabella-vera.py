# -*- coding: utf-8 -*-
"""IL TASSO DI FALSO ALLARME SU SOURCE TABELLARI VERE — e la popolazione opposta.

W7-25 e W7-30 hanno trovato due difetti che si somigliano: `L4.1` perde il
valore adiacente a una parola di `_RIFERIMENTO_RE`, `L4.2` prende come grandezza
la parola a DESTRA del numero. Entrambi colpiscono una **tabella allineata**,
che e' la forma di ogni output di strumento — cioe' la source che `O3` impone.

Nessuno dei due dice QUANTO. Qui il numero, sulle mie source REALI di stasera:
gli output dei banchi che ho eseguito, non testi costruiti per l'occasione.

⚖️ DUE POPOLAZIONI, ed e' il punto del banco: sui soli VERI un tasso di allarme
alto sembra un difetto grave, ma se il gate segnala allo stesso modo anche i
FALSI allora non separa niente e il numero sui veri non significa nulla. Si
consegna la SEPARAZIONE, non una meta'. **E si conta PER LAYER**: la prima
lettura di questo banco diceva «8 su 8 e 8 su 8, non separa», e mescolava due
comportamenti opposti.

Chiamo `run_validation_gate` direttamente: nessuna scrittura, nessun fatto nel
corpus.

CONTROLLI CHE POSSONO FALLIRE:
 (1) i FALSI devono essere segnalati. Se il gate tace anche su quelli, sto
     misurando un gate spento e il tasso sui veri non vale niente. **Questo
     controllo ha gia' salvato il banco una volta**: la prima versione chiamava
     `run_validation_gate` senza `ground_write=True`, e il gate taceva su TUTTE
     E SEDICI le coppie — `_grounding_write_on()` legge `ENGRAM_GROUNDING_WRITE`
     e senza quella variabile il blocco L4 (`anti_confab_gate.py:2337`) non gira
     affatto. Senza il controllo avrei consegnato «zero falsi allarmi».
 (2) le source devono essere quelle vere: le leggo dai file che i banchi hanno
     prodotto stasera, e se un file manca lo dico invece di sostituirlo.

    python -u docs/stato-reale/banchi/quanto-sbaglia-il-gate-su-una-tabella-vera.py
"""

from __future__ import annotations

import io
import os
import sys

BASE = ("C:/Users/aurel/AppData/Local/Temp/claude/"
        "C--Users-aurel-Desktop-ProgettiAI/78ba9444-dd97-498f-bd48-07ca991638a4/"
        "scratchpad/")

# (file della source, claim VERO, claim FALSO — stessa forma, numero cambiato)
CASI = [
    ("ws4_veto2.txt",
     "Il controllo sul package verimem riporta 6 identificativi di sessione in 3 file.",
     "Il controllo sul package verimem riporta 9 identificativi di sessione in 3 file."),
    ("ws4_veto2.txt",
     "Il controllo sul package verimem esamina 421 file py.",
     "Il controllo sul package verimem esamina 555 file py."),
    ("ws4_nuda.txt",
     "Nella vista nuda i layers vuoti sono 408 su 500.",
     "Nella vista nuda i layers vuoti sono 277 su 500."),
    ("ws4_nuda.txt",
     "Nella vista nuda la colonna quarantined_by e' piena su 406 righe.",
     "Nella vista nuda la colonna quarantined_by e' piena su 311 righe."),
    ("ws4_dist.txt",
     "Sulle 500 righe la colonna quarantined_by porta moat su 279 righe.",
     "Sulle 500 righe la colonna quarantined_by porta moat su 132 righe."),
    ("ws4_dist.txt",
     "Le etichette generiche scartate sono 314 e le colonne vuote sono 94.",
     "Le etichette generiche scartate sono 207 e le colonne vuote sono 61."),
    ("ws4_wheel.txt",
     "Il wheel verimem porta 7 identificativi di sessione in 4 file.",
     "Il wheel verimem porta 3 identificativi di sessione in 4 file."),
    ("ws4_sdist.txt",
     "L artefatto esamina 423 file py.",
     "L artefatto esamina 388 file py."),
]


def leggi(nome):
    p = BASE + nome
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8", errors="replace") as f:
        testo = f.read()
    righe = [r for r in testo.splitlines()
             if "RuntimeWarning" not in r
             and "_threshold_of_record" not in r
             and "triton not found" not in r]
    return "\n".join(righe).strip()


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def layer_l4(claim, source):
        """I layer L4.x che parlano su questa coppia. [] = il gate tace."""
        try:
            # `ground_write=True` NON e' un'opzione mia: e' il regime del
            # prodotto (preset `balanced`, `ground=True`). Vedi il CONTROLLO (1).
            g = run_validation_gate(proposition=claim, verified_by=[],
                                    topic=None, agent=None, source=source,
                                    ground_write=True)
        except Exception as e:  # noqa: BLE001
            return [f"ECCEZIONE:{type(e).__name__}"]
        out = []
        for w in (getattr(g, "warnings", None) or []):
            lay = str((w or {}).get("layer") or "")
            if lay.startswith("L4.1") or lay.startswith("L4.2"):
                out.append(lay)
        return out

    veri_segnalati = falsi_segnalati = 0
    v41 = v42 = f41 = f42 = 0
    n = 0
    mancanti = []
    print("  == LE DUE POPOLAZIONI, sulle stesse source reali")
    print(f"     {'source':<18} {'VERO':<26} {'FALSO'}")
    for nome, vero, falso in CASI:
        src = leggi(nome)
        if src is None:
            mancanti.append(nome)
            continue
        n += 1
        lv = layer_l4(vero, src)
        lf = layer_l4(falso, src)
        veri_segnalati += 1 if lv else 0
        falsi_segnalati += 1 if lf else 0
        v41 += 1 if any(x.startswith("L4.1") for x in lv) else 0
        v42 += 1 if any(x.startswith("L4.2") for x in lv) else 0
        f41 += 1 if any(x.startswith("L4.1") for x in lf) else 0
        f42 += 1 if any(x.startswith("L4.2") for x in lf) else 0
        mv = ("SEGNALA " + ",".join(lv)) if lv else "tace"
        mf = ("SEGNALA " + ",".join(lf)) if lf else "tace"
        print(f"     {nome:<18} {mv:<26} {mf}")
        if lv:
            print(f"       ^ FALSO ALLARME su: {vero[:72]}")

    if mancanti:
        print(f"\n  source mancanti, NON sostituite: {mancanti}")
    if n == 0:
        print("  NON RIUSCITO: nessuna source leggibile, non ho misurato niente.")
        return 1

    print(f"\n  == LA LETTURA AGGREGATA, quella che MESCOLA - su {n} coppie")
    print(f"     VERI  segnalati (falso allarme) : {veri_segnalati} su {n}")
    print(f"     FALSI segnalati (il suo lavoro) : {falsi_segnalati} su {n}")

    print("\n  == I DUE LAYER SEPARATI, che e' il numero che decide")
    print(f"     L4.1   sui VERI {v41} su {n}   sui FALSI {f41} su {n}")
    print(f"     L4.2   sui VERI {v42} su {n}   sui FALSI {f42} su {n}")

    print("\n  -- CONTROLLO (1): il gate e' ACCESO sui falsi?")
    if falsi_segnalati == 0:
        print("     CADUTO - il gate tace su TUTTI i falsi: e' spento su questa")
        print("     popolazione, e il tasso sui veri non significa niente.")
        return 1
    print(f"     retto - ferma {falsi_segnalati} falsi su {n}")

    print("\n  -- LA SEPARAZIONE, per layer")
    if v41 == 0 and f41 > 0:
        print(f"     L4.1 SEPARA PERFETTAMENTE: {f41} su {n} sui falsi,"
              f" {v41} su {n} sui veri.")
    elif v41 > 0:
        print(f"     L4.1 sbaglia su {v41} veri: non separa come sembrava.")
    if v42 >= n and f42 < n:
        print(f"     L4.2 ANTI-SEPARA: {v42} su {n} sui VERI e solo {f42} su {n}"
              " sui falsi.")
        print("     I falsi li prende gia' L4.1: su questa forma di source")
        print("     L4.2 aggiunge solo rumore.")
    elif v42 == 0:
        print("     L4.2 non produce falsi allarmi su questa popolazione.")
    else:
        print(f"     L4.2: {v42} sui veri, {f42} sui falsi - leggi le righe sopra")
        print("     prima di citare un numero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
