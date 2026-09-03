"""R1 — quanto costa davvero una cella di porta che accende il giudice.

    python docs/stato-reale/banchi/ws3-R1-quanto-costa-una-cella-di-porta-col-giudice.py

⚠️ Carica modelli. Il vincolo «un banco alla volta» per la RAM e' stato
revocato da Aurelio il 2026-09-03 alle 19:15.

PERCHE' ESISTE. La regola proposta — «ogni cura ha una cella che passa dalla
PORTA del prodotto, non solo dalla funzione» — vale solo se costa poco: una
regola che rallenta la suite non viene applicata, e una regola non applicata
vale zero. La predizione depositata da chi l'ha proposta era «≤1 s a caldo con
una fixture di sessione, 30-50 s a freddo».

MISURATO IL 2026-09-03, due giri identici, stesse frasi nello stesso ordine:

    scrittura                          giro 1    giro 2
    1  fonte A, prima in assoluto      27,25s    28,82s     <- freddo
    2  fonte A di nuovo                 5,71s     6,42s
    3  fonte B, PRIMA fonte nuova       0,51s     1,10s
    4  fonte B di nuovo                 2,87s     3,84s
    5  fonte C, SECONDA fonte nuova     0,43s     0,52s
    6  fonte C di nuovo                 0,35s     0,48s

(un terzo giro: 26,32 / 5,98 / 0,52 / 3,04 / 0,44 / 0,45 — stessa forma.)

⇒ IL CALDO conferma la predizione: regime 0,4-0,5 s, sotto 1 s.
⇒ IL FREDDO la manca, **di poco e verso il basso**: 26,3-28,8 s su tre giri
   contro una fascia predetta 30-50. Non e' «dentro»: e' sotto. Lo scrivo
   perche' arrotondare uno scarto a favore della predizione e' il modo piu'
   economico di rendere una predizione inconfutabile — e allora non misura
   piu' niente. Lo scarto e' piccolo e non cambia nessuna decisione, ma il
   verdetto sul braccio freddo e' «fuori fascia», non «confermata».

E fra i due c'e' una **coda di riscaldamento** che nessuno aveva previsto:
~6 s, ~1 s, ~3 s prima di assestarsi, riproducibile IDENTICA nei tre giri.

⇒ CONTO PER VENTI CELLE DI PORTA: 30 s + ~10 s di coda + 20 x 0,5 s ≈ 50 s.
Non e' un costo da CI-soltanto: gira anche in locale.

LE DUE IPOTESI CHE QUESTO BANCO HA UCCISO, e la seconda era mia:
  ⓐ «si paga a ogni FONTE NUOVA» — falsa: la 3a scrittura porta una fonte
     nuova e costa 0,5-1,1 s.
  ⓑ «e' un SECONDO modello che si carica una volta, sulla 3a» — falsa: la 3a
     e' veloce e la 4a (stessa fonte della 3a) e' lenta.
  ⇒ Il costo dipende dalla POSIZIONE nella sequenza, non dalla fonte. Che cosa
     si stia scaldando fra la 2a e la 5a scrittura NON e' stabilito, e non lo
     riempio con un'ipotesi.

⚠️ UN NUMERO PRECEDENTE CHE QUESTO BANCO RITIRA. Il 03/09 alle 18:58, dentro
un'esecuzione di `pytest --durations=0` su un altro file, la terza cella costo'
**22,58 s** e ne avevo dedotto un costo per-fonte, avvisando che venti celle
sarebbero costate ~4 minuti. Con un disegno che isola la variabile quel valore
NON si riproduce: quel giro aveva claim diversi e un altro banco pesante girava
in parallelo sulla stessa macchina. La stima dei 4 minuti era sbagliata di due
ordini di grandezza, e l'errore era mio: avevo letto una differenza fra due
celle come se una sola variabile le separasse.

🔮 SE QUALCUNO RIESEGUE: la forma attesa e' 27-30 / ~6 / ~1 / ~3 / ~0,5 / ~0,5.
🔴 COME MUORE: se il regime finale supera 1 s, la fixture di sessione non basta
e la regola va ripensata; se il freddo supera 50 s, va spostata in CI soltanto.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from verimem.client import Memory

F1 = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
F2 = "Referto: il paziente e' deceduto il 30 luglio in terapia intensiva."
F3 = "Bilancio: la societa' ha chiuso l'esercizio 2025 con un utile di 12.400 euro."

SCRITTURE = [
    ("1  fonte A, prima in assoluto (freddo)", F1,
     "Il direttore si e' dimesso il 4 maggio."),
    ("2  fonte A di nuovo (stessa fonte)", F1,
     "Le dimissioni sono del 4 maggio."),
    ("3  fonte B, PRIMA fonte nuova", F2,
     "Il paziente e' deceduto il 30 luglio."),
    ("4  fonte B di nuovo (stessa fonte)", F2,
     "Il decesso e' del 30 luglio."),
    ("5  fonte C, SECONDA fonte nuova", F3,
     "L'esercizio 2025 ha chiuso con un utile."),
    ("6  fonte C di nuovo (stessa fonte)", F3,
     "L'utile 2025 e' di 12.400 euro."),
]


def main() -> None:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "r1.db"))
    print("QUANTO COSTA UNA CELLA DI PORTA COL GIUDICE\n")
    print(f"{'scrittura':42s} {'secondi':>9s}   esito")
    tempi = []
    for etichetta, fonte, claim in SCRITTURE:
        t = time.perf_counter()
        ric = mem.add(claim, topic="t/r1-costo", source=fonte, validate="full")
        dt = time.perf_counter() - t
        tempi.append(dt)
        print(f"{etichetta:42s} {dt:>8.2f}s   {ric.get('status')} "
              f"g={ric.get('grounding_score')}", flush=True)

    freddo, regime = tempi[0], sum(tempi[4:]) / 2.0
    print()
    # ⚠️ La fascia stampata e' QUELLA DEPOSITATA (30-50), non una allargata a
    # posteriori per farci stare la misura: 26-29 s sta SOTTO, e il verdetto
    # deve dirlo.
    print(f"  freddo (1a scrittura)      : {freddo:.2f}s   "
          + ("✅ dentro la fascia predetta 30-50" if 30 <= freddo <= 50
             else f"🔴 FUORI dalla fascia predetta 30-50 (di {30 - freddo:+.1f}s)"
             if freddo < 30 else "🔴 sopra 50"))
    print(f"  regime (media 5a e 6a)     : {regime:.2f}s   "
          f"{'✅ sotto 1 s' if regime < 1.0 else '🔴 sopra 1 s'}")
    print(f"  coda di riscaldamento (2-4): {sum(tempi[1:4]):.2f}s")
    print(f"  venti celle di porta       : ~{freddo + sum(tempi[1:4]) + 20 * regime:.0f}s")
    print()
    print("  ⚠️ il costo dipende dalla POSIZIONE, non dalla fonte: le due")
    print("     ipotesi contrarie sono falsificate nel docstring, con i numeri.")


if __name__ == "__main__":
    main()
