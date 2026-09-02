"""La potatura degli anni mangia anche le DURATE di quattro cifre?

Collega due reperti che finora vivono separati:
  · W7-113 (mio, 02:15): la deroga storica di L1 usa `_CALENDAR_YEAR`, che e'
    `1[0-9]\\d{2}|20\\d{2}` ⇒ legge come ANNO qualunque numero fra 1000 e 2099:
    «1500 seconds» e «1200 pagine» attivano la deroga.
  · W5-11 / W2-411 (ws5+ws2, 03:35): `extract_quantities` POTA le date complete,
    quindi una data inventata CON anno passa e una senza anno viene fermata.
    E il commento del modulo dice che gli anni nudi hanno il loro `YEAR_RE`.

DOMANDA: `YEAR_RE` ha lo stesso difetto di `_CALENDAR_YEAR`? Se si', una DURATA
di quattro cifre viene potata da `extract_quantities` e L4.1 non la vede piu'.

CONTROLLO CHE DEVE ACCENDERSI: devo riprodurre i valori misurati da @ws2 —
`10/08/2026` -> nessuna quantita', `28/08` -> 8 e 28. Se non li riproduco, il
mio banco non sta misurando la stessa funzione e i suoi numeri non valgono.
"""
import sys

from verimem.quantity_match import extract_quantities

CASI = [
    ("controllo @ws2: data completa ISO", "il 2026-08-10", "vuoto"),
    ("controllo @ws2: data completa barre", "il 10/08/2026", "vuoto"),
    ("controllo @ws2: data breve", "il 28/08", "8 e 28"),
    ("durata piccola", "the suite finished in 42 seconds", "42"),
    ("DURATA di 4 cifre", "the suite finished in 1500 seconds", "1500?"),
    ("DURATA nel range alto", "the suite finished in 2026 seconds", "2026?"),
    ("pagine di 4 cifre", "il rapporto ha 1200 pagine", "1200?"),
    ("fuori range basso", "the suite finished in 998 seconds", "998"),
    ("fuori range alto", "the suite finished in 4200 seconds", "4200"),
    ("euro di 4 cifre", "il compenso e' di 1800 euro", "1800?"),
]


def valori(t):
    q = extract_quantities(t)
    out = set()
    for x in q:
        out.add(x[1] if isinstance(x, (tuple, list)) else x)
    return sorted(out)


print(f"  {'caso':34s} {'atteso':10s} ottenuto")
ris = {}
for nome, testo, atteso in CASI:
    v = valori(testo)
    ris[nome] = v
    print(f"  {nome:34s} {atteso:10s} {v}")

ok_ws2 = (not ris["controllo @ws2: data completa ISO"]
          and not ris["controllo @ws2: data completa barre"]
          and 8.0 in ris["controllo @ws2: data breve"]
          and 28.0 in ris["controllo @ws2: data breve"])
print()
if not ok_ws2:
    print("  CONTROLLO SPENTO: non riproduco i valori di @ws2 => il banco non")
    print("  misura la stessa funzione, i numeri sopra NON vanno usati")
    sys.exit(1)
print("  CONTROLLO ACCESO: riprodotti i valori di @ws2")

mangiate = [n for n in ("DURATA di 4 cifre", "DURATA nel range alto",
                        "pagine di 4 cifre", "euro di 4 cifre")
            if not ris[n]]
salve = [n for n in ("fuori range basso", "fuori range alto") if ris[n]]
print(f"  grandezze di 4 cifre POTATE (nessuna quantita'): {len(mangiate)}/4 {mangiate}")
print(f"  fuori range che restano visibili: {len(salve)}/2")
if mangiate and len(salve) == 2:
    print("  ESITO: la potatura degli anni mangia anche le grandezze di 4 cifre")
    print("  => una durata, un importo, un conteggio in quel range sono INVISIBILI a L4.1")
elif not mangiate:
    print("  ESITO: YEAR_RE NON ha il difetto di _CALENDAR_YEAR - il collegamento CADE")
else:
    print("  ESITO: misto, leggere la tabella")
sys.exit(0)
