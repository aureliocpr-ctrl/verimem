"""Quanti presidi ha ogni layer del gate — la mappa, rigenerabile.

    esecuzione:  python docs/stato-reale/banchi/quanti-presidi-ha-ogni-layer.py

Nasce da una segnalazione di ws3 (27/08): «`L4.1` ferma il numerico 18 su 18 e
SEMPRE da solo — se cade, nessun altro layer la raccoglie: è un punto singolo».
Il rischio è reale, ma per pesarlo serve sapere QUANTO è presidiato, e nessuno
lo aveva mai contato.

MISURATO IL 27/08 ALLE 19:57 (21 layer, `git grep -lF` su `tests/`):

    L4.1              25 file      <- il PIÙ presidiato di tutti
    L4-grounding      23
    L4-skipped        19
    L1.13             20
    L1.15             18
    L1.10             17
    L4.2              11
    L1.9               9
    L3-coexistence     8
    L1.11              8
    L1.20              7
    L1.12              6
    L1.16              6
    L4-review          6
    L1.18              5
    L1.19              4
    L1.14              3
    L4-negazione       3
    L1.17              2
    L1.21              2
    L4-relazione       1        <- il meno presidiato

    layer senza NESSUN file di test: 0 su 21

⇒ Due letture, ed entrambe servono:
  · il punto singolo di ws3 esiste come proprietà FUNZIONALE (sul numerico con
    cifre nessun altro raccoglie) ma ha il contrappeso più forte del sistema:
    25 file, e `L4.1` non ha nemmeno un interruttore d'ambiente che possa
    spegnerlo per configurazione — può cadere solo per regressione, e una
    regressione la prendono 25 file;
  · l'esposizione vera sta dall'altra parte della classifica.

⚠️ IL LIMITE DEL RIGHELLO, e va letto prima dei numeri: conta i FILE che
NOMINANO il layer, non le asserzioni su di esso. Un file dedicato e tre
menzioni di passaggio valgono uguale. Verificato a mano sui tre in fondo: tutti
e tre hanno un file DEDICATO —

    L4-relazione  ->  test_una_relazione_non_verificata_avvisa_invece_di_trattenere.py
    L1.17         ->  test_l1_monitored_detector.py
    L1.21         ->  test_l1_quality_detector.py

⇒ «presidio esile» non vuol dire «scoperto». La mappa dice che la copertura è
  DISOMOGENEA, non che ci siano buchi: buchi non ce ne sono.

📌 Perché lasciarlo come banco e non come numero in un documento: questa mappa
invecchia a ogni test aggiunto. Rieseguirlo costa un secondo; fidarsi del numero
scritto qui sopra fra un mese costa un errore.
"""

from __future__ import annotations

import subprocess

LAYER = [
    "L1.9", "L1.10", "L1.11", "L1.12", "L1.13", "L1.14", "L1.15", "L1.16",
    "L1.17", "L1.18", "L1.19", "L1.20", "L1.21", "L3-coexistence",
    "L4.1", "L4.2", "L4-grounding", "L4-negazione", "L4-relazione",
    "L4-review", "L4-skipped",
]


def _file_che_nominano(pattern: str, dove: str) -> list[str]:
    """`git grep -lF` — ignora per costruzione i file non tracciati e `build/`."""
    out = subprocess.run(
        ["git", "grep", "-lF", pattern, "--", dove],
        capture_output=True, text=True,
    )
    return [r for r in out.stdout.splitlines() if r.strip()]


def main() -> int:
    righe = [
        (lay, len(_file_che_nominano(lay, "tests/")), len(_file_che_nominano(lay, "verimem/")))
        for lay in LAYER
    ]
    if not any(t for _, t, _ in righe):
        print("⚠️  zero presidi ovunque: `git grep` non ha girato (sei in un repo git?).")
        print("   Questo NON e' una misura: e' un comando che non ha funzionato.")
        return 2
    righe.sort(key=lambda r: -r[1])
    print(f"  {'layer':<16} {'file di TEST':>13} {'file in verimem/':>17}")
    for lay, t, p in righe:
        nota = "  <- nessun presidio" if t == 0 else ""
        print(f"  {lay:<16} {t:>13} {p:>17}{nota}")
    scoperti = [lay for lay, t, _ in righe if t == 0]
    print(f"\n  layer senza NESSUN file di test: {len(scoperti)} su {len(righe)}"
          f"{'  ' + str(scoperti) if scoperti else ''}")
    print(f"  piu' presidiato: {righe[0][0]} ({righe[0][1]})"
          f"   ·   meno: {righe[-1][0]} ({righe[-1][1]})")
    print("\n  ⚠️ conta i FILE che NOMINANO il layer, non le asserzioni: un file dedicato")
    print("     e tre menzioni di passaggio valgono uguale. «Esile» != «scoperto».")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
