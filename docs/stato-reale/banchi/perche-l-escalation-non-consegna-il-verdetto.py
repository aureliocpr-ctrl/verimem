# -*- coding: utf-8 -*-
"""DOVE SI PERDE IL VERDETTO — la discovery riesce, il verdetto no.

Alle 21:09 avevo scritto che il rimedio «non arriva». Va precisato: **parte,
esegue, e il verdetto si perde**. Le funzioni di lookup rispondono, e nessuna
di queste righe esegue un LLM.

Il percorso, letto in `band_escalation.py:166-180`: se ollama non c'e', si va su
`_score_via_claude`, che invoca la CLI e passa il risultato a `_parse_score`.
Due modi di tornare None — la CLI fallisce, oppure la risposta non e' leggibile
— e il chiamante non li distingue: `escalate_band` torna None in entrambi i casi
e il write prosegue col punteggio del CE.

Questo banco misura la seconda meta': quanto e' stretto il parser. La sua
strettezza NON e' sciatteria, ed e' scritto nel modulo (`band_escalation.py:41`):
«A digit embedded in prose ("the 100 words…") is NOT a verdict: parsing it once
ADMITTED a fact the judge had scored 5». E' la cura di un incidente vero.
Il costo di quella cura non era misurato: e' quello che si misura qui.

⛔ Nessuna invocazione di CLI: si chiama solo `_parse_score` su stringhe.
Il comando che il prodotto costruirebbe lo LEGGO dal sorgente, non lo eseguo.

    python docs/stato-reale/banchi/perche-l-escalation-non-consegna-il-verdetto.py
"""

from __future__ import annotations

import shutil
import sys

# Risposte che una CLI puo' davvero dare. La prima riga di ogni gruppo e' la
# forma che il modulo dichiara di accettare.
CASI = [
    ("87", "numero nudo — la forma dichiarata"),
    (" 92.5 ", "numero nudo con spazi"),
    ("Score: 55", "etichetta esplicita — la seconda forma dichiarata"),
    ("Based on the source, the claim is not supported. Score: 12", "prosa + etichetta"),
    ("**55**", "numero in grassetto markdown"),
    ("The score is 55.", "«score is» invece di «score:»"),
    ("I would rate this 55 out of 100.", "prosa inglese"),
    ("Il punteggio e' 55.", "prosa italiana"),
    ("Sorry, I cannot help with that.", "rifiuto"),
    ("", "risposta vuota"),
]


def main() -> int:
    from verimem import band_escalation as be  # noqa: PLC0415

    print("  ① LA DISCOVERY — chi verrebbe interrogato su questa macchina")
    cli = shutil.which("claude")
    print(f"     shutil.which('claude') : {cli}")
    print(f"     _mode()                : {be._mode()}")
    print(f"     _timeout_s()           : {be._timeout_s()}")
    try:
        ollama = be._local_ollama_available()
    except Exception as e:  # noqa: BLE001
        ollama = f"{type(e).__name__}"
    print(f"     ollama locale          : {ollama}")
    if cli and ollama is False:
        print("     ⇒ il percorso preso e' _score_via_claude: la CLI c'e' e viene invocata.")
        print("       «non arriva» era impreciso: parte ed esegue.")

    print("\n  ② IL PARSER — quali risposte diventano un verdetto")
    print(f"  {'risposta':<58} {'esito':>8}   forma")
    print("  " + "-" * 96)
    persi = []
    for testo, forma in CASI:
        v = be._parse_score(testo)
        esito = "None" if v is None else f"{v:g}"
        if v is None:
            persi.append(forma)
        print(f"  {testo!r:<58} {esito:>8}   {forma}")

    letti = len(CASI) - len(persi)
    print(f"\n  letti {letti} su {len(CASI)}; persi: {len(persi)}")
    for f in persi:
        print(f"     - {f}")
    print("\n  ⇒ Il parser e' stretto per una ragione misurata e scritta nel modulo.")
    print("    Il costo e' che un verdetto ILLEGGIBILE e un giudice IRRAGGIUNGIBILE")
    print("    tornano entrambi None, e nessuno dei due lascia una traccia:")
    print("    un'astensione e un guasto producono lo stesso silenzio.")

    print("\n  ③ IL COMANDO, letto dal sorgente (band_escalation.py:153-157)")
    print("     [cli, '-p', '--output-format', 'text', '--append-system-prompt', _FACT_SYSTEM]")
    print("     ⇒ nessun '--model': il giudice che decide dipende da come e'")
    print("       configurata la CLI sulla macchina, e la ricevuta non lo registra.")
    print("       Un verdetto non riproducibile e' un verdetto che non si puo' citare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
