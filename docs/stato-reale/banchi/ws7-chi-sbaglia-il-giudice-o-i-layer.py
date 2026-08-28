# -*- coding: utf-8 -*-
"""CHI SBAGLIA: IL GIUDICE (semantico) O I LAYER (lessicali)? — test dell'ipotesi

PERCHE' ESISTE. Alle 00:35 ho scritto in `LANT-34` un'ipotesi di lettura: **il gate
decide su segni superficiali**, e la stessa natura di criterio produce errori in
entrambe le direzioni (un verbo ferma il vero, un ordine di parole lascia passare
il falso). L'ho pubblicata **con le istruzioni per ucciderla**: *basta un layer
che sbagli su un criterio SEMANTICO e l'ipotesi cade.*

Questo banco esegue quelle istruzioni.

⚠️ PERCHE' NON USO I DATI CHE HO GIA'. Nei miei banchi di stanotte il giudice non
ha mai sbagliato e i layer hanno sbagliato 8 volte su 10 — sembra una conferma, e
**non vale niente**: quei banchi erano COSTRUITI per trovare i falsi positivi dei
layer. Contare a posteriori su dati raccolti per un altro scopo e' il modo piu'
comodo di confermarsi. Qui la popolazione e' nuova e bilanciata.

COSA MISURA, separando i due decisori sullo STESSO caso:
  - il GIUDICE (semantico): il `grounding_score` e' dalla parte giusta?
    vero -> alto, falso -> basso. Errore = un vero con punteggio basso o un
    falso con punteggio alto.
  - i LAYER (lessicali): l'elenco `layers` ha fermato il caso giusto?
    Errore = un vero fermato, o un falso non fermato da nessun layer mentre il
    giudice lo salvava.

DUE POPOLAZIONI, obbligatorie: 8 claim VERI (letteralmente nella fonte) e 8 FALSI
(cifra, negazione, aggiunta, ordine). Un conteggio sui soli veri direbbe che i
layer sono pessimi; sui soli falsi, che sono ottimi.

ESITI POSSIBILI, dichiarati PRIMA:
  giudice ~0 errori, layer molti   -> l'ipotesi REGGE su questa popolazione
  errori simili                    -> l'ipotesi CADE: sbagliano entrambi
  giudice piu' errori dei layer    -> l'ipotesi e' ROVESCIATA

    python docs/stato-reale/banchi/ws7-chi-sbaglia-il-giudice-o-i-layer.py

Store TEMPORANEO (`HIPPO_DATA_DIR`), **uno nuovo per ogni scrittura**. Fuori da
pytest. ⚠️ Sotto il floor di 50 (@ws6): non tocca la scrittura, che e' cio' che
questo banco misura.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FONTE = (
    "Verbale di collaudo del 12 aprile. L'impianto e' stato collaudato dal tecnico incaricato. "
    "La potenza misurata e' di 320 kW. Il costo dell'intervento e' di 48000 euro. "
    "Il responsabile del cantiere e' l'ingegner Bianchi. I lavori sono iniziati il 3 marzo. "
    "La garanzia dura ventiquattro mesi. La linea secondaria non e' stata collaudata."
)

#: (etichetta, claim, e' VERO?)
CASI = [
    # --- otto VERI, tutti letteralmente nella fonte ---
    ("v-potenza",   "La potenza misurata e' di 320 kW.", True),
    ("v-costo",     "Il costo dell'intervento e' di 48000 euro.", True),
    ("v-resp",      "Il responsabile del cantiere e' l'ingegner Bianchi.", True),
    ("v-inizio",    "I lavori sono iniziati il 3 marzo.", True),
    ("v-garanzia",  "La garanzia dura ventiquattro mesi.", True),
    ("v-collaudo",  "L'impianto e' stato collaudato dal tecnico incaricato.", True),
    ("v-linea",     "La linea secondaria non e' stata collaudata.", True),
    ("v-data",      "Il verbale di collaudo e' del 12 aprile.", True),
    # --- otto FALSI, quattro classi diverse ---
    ("f-cifra",     "La potenza misurata e' di 850 kW.", False),
    ("f-cifra2",    "Il costo dell'intervento e' di 12000 euro.", False),
    ("f-negaz",     "La linea secondaria e' stata collaudata.", False),
    ("f-negaz2",    "L'impianto non e' stato collaudato.", False),
    ("f-aggiunta",  "La potenza misurata e' di 320 kW, certificata dall'ente regionale.", False),
    ("f-aggiunta2", "Il responsabile del cantiere e' l'ingegner Bianchi, iscritto all'albo di Roma.", False),
    ("f-nome",      "Il responsabile del cantiere e' l'ingegner Rossi.", False),
    ("f-data",      "I lavori sono iniziati il 3 maggio.", False),
]

SOGLIA = 40.0  # la soglia che il prodotto usa davvero (sanity cap, grounding_gate.py:510)


def main() -> int:
    for tok in ("850", "12000", "ente regionale", "Rossi", "3 maggio", "albo di Roma"):
        if tok in FONTE:
            print(f"  CONTROLLO CADUTO: «{tok}» e' nella fonte")
            return 1
    veri = sum(1 for *_, v in CASI if v)
    print(f"  controllo retto: {veri} VERI e {len(CASI) - veri} FALSI, "
          "i dati inventati non sono nella fonte\n")

    from verimem.client import Memory  # noqa: PLC0415

    print(f"  {'caso':<13} {'atteso':<7} {'ground':>7}  {'giudice':<9} {'layer':<9} esito")
    print("  " + "-" * 68)
    err_giudice, err_layer = [], []
    for etichetta, claim, vero in CASI:
        mem = Memory(str(Path(tempfile.mkdtemp()) / "g.db"))
        ric = mem.add(claim, topic="g", source=FONTE, validate="full")
        g = float(ric.get("grounding_score") or -1)
        fermato = str(ric.get("status")) == "quarantined"
        # il GIUDICE ha ragione se il punteggio sta dalla parte giusta della soglia
        giudice_ok = (g >= SOGLIA) if vero else (g < SOGLIA)
        # i LAYER hanno ragione se hanno fermato il falso e lasciato passare il vero
        layer_ok = (not fermato) if vero else fermato
        if not giudice_ok:
            err_giudice.append(etichetta)
        if not layer_ok:
            err_layer.append(etichetta)
        print(f"  {etichetta:<13} {'VERO' if vero else 'FALSO':<7} {g:7.2f}  "
              f"{'ok' if giudice_ok else '🔴 SBAGLIA':<9} {'ok' if layer_ok else '🔴 SBAGLIA':<9} "
              f"{'fermato' if fermato else 'passa'}")

    n = len(CASI)
    print("\n  " + "=" * 68)
    print(f"  ERRORI DEL GIUDICE (semantico) : {len(err_giudice)}/{n}  {err_giudice or ''}")
    print(f"  ERRORI DEI LAYER  (lessicali)  : {len(err_layer)}/{n}  {err_layer or ''}")
    if len(err_giudice) < len(err_layer):
        print("  ⇒ l'ipotesi REGGE su questa popolazione: il criterio semantico sbaglia di meno.")
    elif len(err_giudice) == len(err_layer):
        print("  ⇒ l'ipotesi CADE: sbagliano nella stessa misura.")
    else:
        print("  ⇒ l'ipotesi e' ROVESCIATA: il giudice sbaglia PIU' dei layer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
