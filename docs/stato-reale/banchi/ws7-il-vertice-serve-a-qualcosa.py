# -*- coding: utf-8 -*-
"""IL VERTICE — di quanto si riduce il FALSO che un agente si rilegge?

PERCHE' ESISTE. Il registro ha 119 celle e misurano tutte **come** funziona il
prodotto: quale layer scatta, su quale porta, con quale punteggio. **Nessuna
misura se SERVE.** La riga e' dichiarata scoperta nel file dal 27/08 e nessuna
l'ha rivendicata; ed e' la domanda che Aurelio ha fatto quel giorno — «stiamo
davvero andando avanti, o giriamo in tondo?».

COSA MISURA. La differenza che un utente vive: **non** «il gate ferma X», ma
**cosa si ritrova in mano quando rilegge**. Stesso corpus, due store:

    SENZA  ogni claim entra (e' la memoria che un agente ha senza verimem:
           scrive quello che crede e se lo ritrova identico)
    CON    entrano solo i claim che il gate ammette

poi si interroga ogni store e si contano i **dati falsi che tornano indietro**.

COSA NON MISURA, e va detto prima dei numeri: **non e' un agente vero.** E' un
proxy — nessun modello genera i claim, li scrivo io. Dice quanto del falso il
gate toglie dalla memoria, **non** quanto un agente sbaglierebbe di meno nei
suoi compiti. Chi lo cita come «un agente con verimem sbaglia meno» lo sta
usando per dire piu' di quello che misura.

ATTESA DICHIARATA PRIMA DELLA MISURA (falsificabile): **la riduzione sara'
PARZIALE, non totale.** Il registro dice gia' che alcune classi passano — la
riga 12 misura la negazione ammessa 46 volte su 108, la riga 30 l'omissione
12 su 12 — quindi un banco che desse 100% starebbe misurando se stesso.

LE CLASSI, prese da quelle che il registro ha gia' misurato, cosi' il numero e'
interpretabile invece che aneddotico:

    cifra inventata   (riga 31, W7-2: fermata)         -> atteso FERMATO
    aggiunta          (LANT-27: fermata)               -> atteso FERMATO
    negazione         (riga 12: passa 46/108)          -> atteso PASSA
    omissione         (riga 30: passa 12/12)           -> atteso PASSA
    scambio           (W7-7: entra 3 volte su 7)       -> incerto

CONTROLLO CHE DEVE POTER FALLIRE: i claim VERI devono sopravvivere in
ENTRAMBI gli store. Un gate che li togliesse avrebbe un tasso di falsi
bellissimo e sarebbe inutile: e' la ragione per cui si misurano **due
popolazioni**, non una.

    python docs/stato-reale/banchi/ws7-il-vertice-serve-a-qualcosa.py

Store TEMPORANEO via `HIPPO_DATA_DIR`. Fuori da pytest (li' l'embedder e' uno
stub su SHA-256 e misurerebbe il righello).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FONTE = (
    "Relazione tecnica del 4 aprile. Il collaudo dell'impianto e' stato completato "
    "con esito positivo. La potenza installata e' di 320 kW. Il costo sostenuto per "
    "l'intervento e' di 48000 euro. Il collaudo non ha riguardato la linea secondaria, "
    "che resta esclusa dalla garanzia."
)

#: (classe, claim, e' falso?, cosa il registro fa prevedere)
CASI = [
    ("vero-1",     "La potenza installata e' di 320 kW.", False, "passa"),
    ("vero-2",     "Il costo sostenuto per l'intervento e' di 48000 euro.", False, "passa"),
    ("vero-3",     "Il collaudo dell'impianto e' stato completato con esito positivo.", False, "passa"),
    ("cifra",      "La potenza installata e' di 850 kW.", True, "FERMATO (riga 31)"),
    ("cifra-2",    "Il costo sostenuto per l'intervento e' di 12000 euro.", True, "FERMATO (riga 31)"),
    ("aggiunta",   "La potenza installata e' di 320 kW ed e' stata certificata dall'ente regionale.",
     True, "FERMATO (LANT-27)"),
    ("negazione",  "Il collaudo dell'impianto non e' stato completato.", True, "passa (riga 12)"),
    ("omissione",  "Il collaudo ha riguardato la linea secondaria.", True, "passa (riga 30)"),
    ("stato",      "La garanzia copre la linea secondaria.", True, "passa (riga 12, schema stato)"),
    ("scambio",    "Il costo sostenuto per l'intervento e' di 320 euro.", True, "incerto (W7-7)"),
]


def main() -> int:
    # Controllo che DEVE poter fallire: i dati falsi non stanno nella fonte.
    for tok in ("850", "12000", "ente regionale"):
        if tok in FONTE:
            print(f"  CONTROLLO CADUTO: «{tok}» e' dentro la fonte")
            return 1
    print("  controllo retto: nessuno dei dati inventati e' nella fonte")
    veri = sum(1 for _c, _t, falso, _p in CASI if not falso)
    print(f"  due popolazioni: {veri} claim VERI e {len(CASI) - veri} FALSI\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    radice = Path(tempfile.mkdtemp())
    con = Memory(str(radice / "con_gate.db"))
    senza = Memory(str(radice / "senza_gate.db"))

    print(f"  {'classe':<11} {'falso':<6} {'esito col gate':<14} {'ground':>7}   previsto dal registro")
    print("  " + "-" * 88)
    ammessi_con, scritti_senza = [], []
    for classe, claim, falso, previsto in CASI:
        ric = con.add(claim, topic=f"vertice/{classe}", source=FONTE, validate="full")
        stato = str(ric.get("status"))
        ground = float(ric.get("grounding_score") or -1)
        if stato != "quarantined":
            ammessi_con.append((classe, claim, falso))
        # lo store «senza» riceve TUTTO: e' la memoria di chi non ha il gate
        senza.add(claim, topic=f"vertice/{classe}")
        scritti_senza.append((classe, claim, falso))
        print(f"  {classe:<11} {'si' if falso else 'no':<6} {stato:<14} {ground:7.2f}   {previsto}")

    fal_con = sum(1 for _c, _q, f in ammessi_con if f)
    fal_senza = sum(1 for _c, _q, f in scritti_senza if f)
    ver_con = sum(1 for _c, _q, f in ammessi_con if not f)

    print("\n  " + "=" * 88)
    print(f"  FALSI che restano in memoria:   senza gate {fal_senza}/{len(CASI) - veri}"
          f"   ·   col gate {fal_con}/{len(CASI) - veri}")
    print(f"  VERI sopravvissuti col gate:    {ver_con}/{veri}"
          f"   <- se non e' pieno, il gate paga il suo tasso con dati buoni")
    if fal_senza:
        print(f"  riduzione del falso: {100 * (fal_senza - fal_con) / fal_senza:.0f}%"
              f"   (attesa dichiarata prima: PARZIALE, non totale)")
    print(f"  classi di falso che SOPRAVVIVONO al gate: "
          f"{[c for c, _q, f in ammessi_con if f] or 'nessuna'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
