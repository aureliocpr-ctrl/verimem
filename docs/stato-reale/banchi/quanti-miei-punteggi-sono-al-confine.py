"""Applico a me la regola di @ws2: un valore entro ~5 punti dal cut 40 non e' un
dato riproducibile e va scritto come «al confine».

Il conteggio grezzo (qualunque numero fra 35 e 45) da' 27 valori in 20 celle: e'
il criterio SBAGLIATO, cattura percentuali, conteggi, tutto. Sarebbe l'ottavo
criterio sintattico che mi sbaglia stanotte.

CRITERIO, dichiarato prima: un numero e' un PUNTEGGIO DEL GATE se sta fra 35 e 45
E nei 45 caratteri che lo precedono o seguono compare una parola del dominio del
punteggio. Le percentuali sono escluse esplicitamente (un «%» attaccato).

CONTROLLO CHE DEVE ACCENDERSI: W7-91 con 43,33 deve comparire — e' il caso che
@ws2 ha misurato. Se non compare, il criterio non misura cio' che dichiara.
"""
import io
import re
import sys

P = "docs/stato-reale/00-ESAME.md"
NUM = re.compile(r"(?<![\w.,])(3[5-9][.,]\d+|4[0-5][.,]\d+)(?![\w])")
DOMINIO = re.compile(
    r"grounding|punteggi|score|\bg\s*=|cut\b|soglia|threshold|moat|L4|"
    r"quarantin|ammess|admitted", re.I)

righe = [r for r in io.open(P, encoding="utf-8").read().splitlines()
         if r.startswith("| W7-")]
print(f"  celle mie: {len(righe)}")

grezzi, buoni = 0, []
for r in righe:
    ide = r.split("|")[1].strip()
    for m in NUM.finditer(r):
        grezzi += 1
        dopo = r[m.end():m.end() + 2]
        if dopo.strip().startswith("%"):
            continue
        ctx = r[max(0, m.start() - 45):m.end() + 45]
        if DOMINIO.search(ctx):
            buoni.append((ide, m.group(0), ctx.strip()[:95]))

print(f"  numeri grezzi nella banda 35-45      : {grezzi}")
print(f"  di cui PUNTEGGI del gate (criterio)  : {len(buoni)}")
for ide, v, ctx in buoni:
    print(f"    {ide:<8} {v:>7}   …{ctx}…")

acceso = any(ide == "W7-91" and v.startswith("43") for ide, v, _ in buoni)
print()
if not acceso:
    print("  CONTROLLO SPENTO: non ritrova il 43,33 di W7-91 => il criterio")
    print("  non misura cio' che dichiara, il numero NON va usato")
    sys.exit(1)
print("  CONTROLLO ACCESO: ritrova il caso che @ws2 ha misurato")
sys.exit(0)
