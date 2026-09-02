"""La carve-out storica di L1 legge come ANNO qualunque numero fra 1000 e 2099.

Letto nel codice dopo W7-112 (dove il pattern era solo INFERITO da 3 cadute
contro 2 passaggi). anti_confab_gate.py:1766-1789:

  _HISTORICAL_COMPLETION  verbo di completamento in forma PASSIVA
  _CALENDAR_YEAR          r"\\b(?:1[0-9]|20)\\d{2}\\b"
  _is_historical_completion = ENTRAMBI

Cioe' la cura ai falsi positivi di L1 si attiva solo su "X was completed in
<anno>". Due conseguenze da misurare, e sono regex pure: nessun modello, nessuna
RAM, funzioni pubbliche del modulo.

  1. un fatto vero ATTIVO senza anno non e' coperto  -> "The suite finished in 42 seconds"
  2. QUALUNQUE numero fra 1000 e 2099 fa da anno     -> 1500 secondi, 1200 pagine

Il controllo che deve fallire: 998 e 4200 sono fuori range e NON devono passare.
"""
import sys

from verimem.anti_confab_gate import _is_historical_completion as storico
from verimem.anti_confab_gate import _CALENDAR_YEAR, _HISTORICAL_COMPLETION

CASI = [
    ("il caso voluto: ponte + anno", "The bridge was completed in 1998.", True),
    ("suite passiva, 42 secondi", "The suite was finished in 42 seconds.", False),
    ("suite passiva, 1500 SECONDI", "The suite was finished in 1500 seconds.", True),
    ("suite attiva, 1500 secondi", "The suite finished in 1500 seconds.", False),
    ("italiano: 1200 PAGINE", "Il rapporto fu completato in 1200 pagine.", True),
    ("italiano: 12 pagine", "Il rapporto fu completato in 12 pagine.", False),
    ("controllo: 998 fuori range", "The bridge was completed in 998.", False),
    ("controllo: 4200 fuori range", "The suite was finished in 4200 seconds.", False),
]

print(f"  {'caso':32s} {'storico?':9s} atteso  passiva  anno")
ko = 0
for nome, testo, atteso in CASI:
    v = storico(testo)
    p = bool(_HISTORICAL_COMPLETION.search(testo))
    a = _CALENDAR_YEAR.search(testo)
    if v != atteso:
        ko += 1
    print(f"  {nome:32s} {str(v):9s} {str(atteso):6s}  {str(p):7s}  {a.group(0) if a else '-'}")

print()
if ko:
    print(f"  {ko} casi non come attesi: l'ipotesi sul codice va riscritta")
    sys.exit(1)
print("  Tutti come attesi. Le due conseguenze sono nel codice, non inferite:")
print("   - un fatto VERO in forma attiva senza anno non e' coperto dalla cura")
print("   - un numero qualunque fra 1000 e 2099 vale come anno: 1500 secondi,")
print("     1200 pagine -> la cura si attiva su fatti che NON sono storici")
