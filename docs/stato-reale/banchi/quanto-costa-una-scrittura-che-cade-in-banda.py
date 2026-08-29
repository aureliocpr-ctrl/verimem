"""QUANTO COSTA UNA SCRITTURA CHE CADE IN BANDA — cronometrata alla porta.

Un'altra istanza ha salvato alle 20:25 un fatto finito a **71.945** (dentro la
banda `[40, 80)`) e ha scritto una cosa onesta: *«la mia impressione e' che sia
stato rapido, ma "mi e' sembrato veloce" non e' una misura e non la spaccio per
tale»*. ⇒ Qui la misura si fa.

**PERCHE' IL TEMPO E' LA DOMANDA GIUSTA.** `W7-52` ha misurato che l'escalation
della banda, chiamata **direttamente**, torna `None` dopo **15,2 s**
(`returncode 1`, sessione OAuth scaduta). Se quel ramo venisse davvero percorso
a ogni scrittura in banda, **ogni scrittura in banda costerebbe ~15 s**.

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE, e le due uscite sono distinguibili:
  · **>= 10 s** -> l'escalation VIENE invocata, fallisce, e il costo e' reale:
    l'utente paga 15 secondi per un verdetto che non arriva.
  · **< 5 s**   -> l'escalation NON viene invocata affatto. Il ramo esiste nel
    codice ma non viene percorso, e allora il difetto non e' l'OAuth: e' che
    la banda **non escala** nemmeno quando dovrebbe.
  · fra 5 e 10 -> non decido, e lo dico.

CONTROLLI CHE POSSONO FALLIRE:
 (1) il caso deve cadere DAVVERO in banda: se il punteggio esce fuori da
     `[40, 80)` non sto cronometrando una scrittura in banda e il numero non
     risponde alla domanda.
 (2) **CONTROLLO POSITIVO**: cronometro anche una scrittura normale (fatto vero,
     punteggio alto). Serve la BASE: senza, «15 secondi» non si distingue da
     «questa macchina e' lenta». La differenza fra i due tempi e' il dato.
 (3) store TEMPORANEO: non scrivo nel corpus di nessuno.

    python -u docs/stato-reale/banchi/quanto-costa-una-scrittura-che-cade-in-banda.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
# ⚠️ ESATTAMENTE DUE caratteri (spazio + L). La prima stesura ne metteva TRE
# (" Le") e il punteggio usciva a **80.7**, fuori dalla banda: il controllo (1)
# ha fermato il banco. 🔑 Un carattere in piu' sposta il punteggio di **2,1
# punti** attraverso il confine — che e' `W7-42` confermato piu' nettamente di
# quanto volessi, e per sbaglio.
CODA = " L"
IN_BANDA = "La cauzione definitiva e' pari a 148000 euro."
NORMALE = "La cauzione definitiva e' pari a 22000 euro."


def main() -> int:
    try:
        from verimem.client import Memory
        from verimem.grounding_gate import (
            _ce_band_tau_hi,
            resolve_write_threshold_for,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    CUT, TAU = resolve_write_threshold_for("local"), _ce_band_tau_hi()
    print(f"  banda: [{CUT}, {TAU}]")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "costo.db"))
    fonte = NUDA + CODA

    # 🪞 RISCALDAMENTO, e senza non c'era misura. La prima stesura cronometrava
    # subito: NORMALE 22,54s contro 0,24s della seconda scrittura. Quei 22
    # secondi sono il CARICAMENTO DEL MODELLO, non il costo di una scrittura —
    # cioe' la "base" misurava l'inizializzazione e avrebbe reso invisibile
    # qualunque differenza fra i due rami.
    t_warm = time.monotonic()
    mem.add("Il termine di consegna e' fissato al 12 marzo 2027.",
            topic="costo/riscaldamento", source=fonte, validate="full")
    print(f"  riscaldamento (scartato): {time.monotonic() - t_warm:.2f}s"
          "   <- e' il caricamento del modello, non il costo di una scrittura")

    misure = {}
    for nome, claim, src in (("NORMALE (sopra soglia)", NORMALE, fonte),
                             ("IN BANDA", IN_BANDA, fonte)):
        t0 = time.monotonic()
        ric = mem.add(claim, topic=f"costo/{nome[:8]}", source=src, validate="full")
        dt = time.monotonic() - t0
        g = ric.get("grounding_score")
        st = ric.get("status")
        misure[nome] = (dt, g, st)
        gs = "n/d" if g is None else f"{float(g):.1f}"
        print(f"  {nome:<24} {dt:>6.2f}s   score {gs:>7}   {st}")

    dt_b, g_b, _st = misure["IN BANDA"]
    dt_n = misure["NORMALE (sopra soglia)"][0]

    print("\n  -- CONTROLLO (1): il caso e' DAVVERO in banda?")
    if g_b is None or not (CUT <= float(g_b) < TAU):
        print(f"     CADUTO - {g_b} e' fuori da [{CUT}, {TAU}]: non sto")
        print("     cronometrando una scrittura in banda, e il numero non")
        print("     risponde alla domanda che ho posto.")
        return 1
    print(f"     retto - {float(g_b):.1f} e' dentro la banda")

    print("\n  -- CONTROLLO (2): la BASE, cioe' quanto costa una scrittura normale")
    print(f"     normale {dt_n:.2f}s   in banda {dt_b:.2f}s"
          f"   differenza {dt_b - dt_n:+.2f}s")

    print("\n  == LA RISPOSTA, con la predizione dichiarata prima")
    if dt_b >= 10.0:
        print(f"     🔴 {dt_b:.2f}s: L'ESCALATION VIENE INVOCATA e fallisce.")
        print("     ⇒ Chi scrive un fatto in banda PAGA il tentativo — e per")
        print("     W7-52 quel tentativo finisce in `returncode 1` (OAuth")
        print("     scaduta) senza che nessun campo della ricevuta lo dica.")
    elif dt_b < 5.0:
        print(f"     🟡 {dt_b:.2f}s: L'ESCALATION NON VIENE INVOCATA.")
        print("     ⇒ Il ramo esiste nel codice ma **non viene percorso**: il")
        print("     fatto e' trattenuto senza che nessuno provi a giudicarlo.")
        print("     Il difetto non e' l'autenticazione: e' a monte di essa.")
    else:
        print(f"     ⚪ {dt_b:.2f}s: fra le due soglie che avevo dichiarato.")
        print("     NON decido: la misura non separa le due ipotesi.")

    print("\n  ⚠️ COSA NON DICE: una scrittura per ramo, su UNA macchina, con la")
    print("  CLI di questa installazione (la cui sessione risulta scaduta in")
    print("  W7-52). Non e' un tasso, e su una macchina autenticata il tempo")
    print("  del ramo in banda potrebbe essere un altro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
