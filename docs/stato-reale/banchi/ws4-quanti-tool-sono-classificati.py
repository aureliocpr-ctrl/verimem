# -*- coding: utf-8 -*-
"""MATRICE DEI PERMESSI — ① quanti tool sono classificati e quanti no.

Il mandato dice «22 tool classificati su 251». Prima di costruirci sopra lo
VERIFICO: i numeri nel codice sono altri — il docstring di
`_capability_gate_mode` (27/05) parla di «175/215 tool bloccati», che e' una
terza coppia. Tre numeri diversi per la stessa cosa vogliono dire che nessuno li
ha ricontati da mesi.

NON IMPORTO `verimem.mcp_server`: importarlo costa ~682 MB di RAM (fatto in
memoria `verimem/pavimento-client-mcp`), e per contare i NOMI dei tool basta
leggere il sorgente. Il registro invece e' un modulo leggero e si importa.

⚠️ LIMITE DEL RIGHELLO, dichiarato prima del numero: conto i nomi che compaiono
come `Tool(name="…")` nel sorgente. Se un tool e' registrato per altra via (un
ciclo, una lista costruita altrove) questo conteggio lo perde ⇒ e' un LIMITE
INFERIORE sui tool esposti, e quindi un limite inferiore anche sugli
sconosciuti. Il controllo che lo tiene onesto: il numero di tool trovati deve
essere dello stesso ordine di quello dichiarato dal mandato (251); se e'
molto piu' basso, il righello non vede la forma vera e il resto non vale.
"""
import io
import re

src = io.open("verimem/mcp_server.py", encoding="utf-8").read()
nomi = set(re.findall(r'Tool\(\s*\n?\s*name="([a-zA-Z0-9_]+)"', src))
nomi |= set(re.findall(r'name="((?:hippo|verimem)_[a-z0-9_]+)"', src))
print(f"  tool trovati nel sorgente:      {len(nomi)}")

from verimem.tool_registry import REGISTRY  # noqa: E402

classificati = set(REGISTRY._caps)
print(f"  tool CLASSIFICATI nel REGISTRY: {len(classificati)}")

if len(nomi) < 100:
    print("\n  ⛔ CONTROLLO SPENTO: il righello trova troppo pochi tool"
          f" ({len(nomi)}) rispetto ai 251 dichiarati ⇒ non vede la forma vera"
          " con cui sono registrati, e i numeri sotto non valgono.")
else:
    sconosciuti = nomi - classificati
    print(f"  SCONOSCIUTI (fail-closed):      {len(sconosciuti)}"
          f" = {100*len(sconosciuti)/len(nomi):.1f}%")
    print(f"  classificati MA non esposti:    {len(classificati - nomi)}")
    print("\n  i primi 15 sconosciuti:")
    for n in sorted(sconosciuti)[:15]:
        print("   ", n)

print("\n  COSA DICE IL REGISTRO sui classificati:")
from collections import Counter  # noqa: E402
liv = Counter()
conf = 0
for n in sorted(classificati):
    c = REGISTRY._caps[n]
    liv[getattr(c, "level", None) or getattr(c, "capability", "?")] += 1
    if getattr(c, "requires_confirm", False):
        conf += 1
print(f"    per livello: {dict(liv)}")
print(f"    con requires_confirm: {conf}")
print("\n    l'elenco completo dei classificati:")
for n in sorted(classificati):
    c = REGISTRY._caps[n]
    print(f"      {n:<34} {getattr(c, 'level', '?')!s:<14}"
          f" confirm={getattr(c, 'requires_confirm', '?')}")
