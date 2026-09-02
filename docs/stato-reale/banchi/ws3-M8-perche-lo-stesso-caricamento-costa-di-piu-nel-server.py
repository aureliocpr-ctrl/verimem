"""M8 — perche' lo STESSO caricamento costa un ordine di grandezza in piu' nel
server MCP? Tre regimi, una variabile per volta.

    python docs/stato-reale/banchi/ws3-M8-perche-lo-stesso-caricamento-costa-di-piu-nel-server.py

I NUMERI CHE APRONO LA DOMANDA:
    caricamento del giudice        mediana  2,4 s   (n=70, ricevute flow.warmup CLI)
    timeout del client osservato          240 s     (altra istanza)
    stesso caricamento nel server      >240 s       (altra istanza: >=11x la CLI)
⇒ Il caricamento ci starebbe **cento volte** dentro il timeout. Quindi la
domanda NON e' «quanto dura», e' **perche' la stessa operazione cambia costo
cambiando processo**. Chi l'ha misurato l'ha dichiarato non isolato.

L'IPOTESI: nel server il caricamento avviene **in un thread secondario mentre
l'event loop asyncio gira**; nel dump del watchdog il frame di
`anyio/_backends/_asyncio.py` sta accanto a quello dell'import. Contesa fra il
loop e l'import (GIL + loop attivo).

I TRE REGIMI, in PROCESSI SEPARATI — separati perche' dopo il primo import il
modulo e' in `sys.modules` e la seconda misura sarebbe un'altra cosa::

    A   nessun event loop, import nel thread principale        <- baseline
    B   event loop ATTIVO, import nel thread principale        <- isola il loop
    C   event loop ATTIVO, import in un THREAD SECONDARIO      <- come il server

🔮 PREDIZIONE depositata sul canale PRIMA di eseguire (02/09 21:05):
    **A ≈ B, e C >= 5x A.**
🔴 COME MUORE: se **C ≈ A**, la contesa col loop non c'entra, la causa e'
altrove, e la cura «caricare all'avvio» NON basterebbe.

⚠️ Si misura l'import di `transformers`+`torch` (quello che il dump mostra come
frame bloccante), NON il modello: bastano l'import e una `nn.Linear`, e cosi'
il banco gira ovunque senza scaricare pesi ne' toccare alcuno store.
⚠️ Il carico del loop e' UNA `asyncio.sleep(0)` in ciclo stretto: e' il caso
peggiore ragionevole (un loop che non dorme mai). Un server reale sta in mezzo
fra questo e il regime A — il banco misura il VERSO e l'ordine di grandezza,
non il numero del server.
"""
import subprocess
import sys
import textwrap

REGIMI = {
    "A senza loop": """
import time
t0 = time.perf_counter()
import torch, transformers          # noqa: F401
from transformers import AutoTokenizer   # noqa: F401
print(round(time.perf_counter() - t0, 2))
""",
    "B loop, principale": """
import asyncio, threading, time

def gira(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def occupa():
    while True:
        await asyncio.sleep(0)      # loop che non dorme mai: caso peggiore

loop = asyncio.new_event_loop()
threading.Thread(target=gira, args=(loop,), daemon=True).start()
asyncio.run_coroutine_threadsafe(occupa(), loop)
time.sleep(0.3)                      # il loop e' partito davvero

t0 = time.perf_counter()
import torch, transformers          # noqa: F401
from transformers import AutoTokenizer   # noqa: F401
print(round(time.perf_counter() - t0, 2))
""",
    "C loop, thread secondario": """
import asyncio, threading, time

def gira(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def occupa():
    while True:
        await asyncio.sleep(0)

loop = asyncio.new_event_loop()
threading.Thread(target=gira, args=(loop,), daemon=True).start()
asyncio.run_coroutine_threadsafe(occupa(), loop)
time.sleep(0.3)

fuori = {}

def carica():
    t0 = time.perf_counter()
    import torch, transformers      # noqa: F401
    from transformers import AutoTokenizer   # noqa: F401
    fuori['t'] = time.perf_counter() - t0

th = threading.Thread(target=carica)   # come il server: import NON nel main
th.start()
th.join()
print(round(fuori['t'], 2))
""",
}


def misura(codice):
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(codice)],
                       capture_output=True, text=True, timeout=900)
    for riga in reversed(r.stdout.strip().splitlines()):
        try:
            return float(riga.strip())
        except ValueError:
            continue
    return None


print("M8 — lo stesso import in tre regimi, processi separati\n")
print("%-28s %12s" % ("regime", "secondi"))
print("-" * 42)
tempi = {}
for nome, codice in REGIMI.items():
    t = misura(codice)
    tempi[nome] = t
    print("%-28s %11.2fs" % (nome, t) if t is not None
          else "%-28s %12s" % (nome, "errore"))

a = tempi.get("A senza loop")
b = tempi.get("B loop, principale")
c = tempi.get("C loop, thread secondario")
print()
if a and b and c:
    print("  B/A  %.2fx   (isola il loop da solo)" % (b / a))
    print("  C/A  %.2fx   (loop + thread secondario, come il server)" % (c / a))
    print()
    if c / a >= 5:
        print("  ⇒ PREDIZIONE CONFERMATA: C >= 5x A — la contesa col loop pesa,")
        print("     e caricare all'AVVIO (loop ancora scarico) ha una ragione misurata.")
    elif c / a <= 1.5:
        print("  ⇒ PREDIZIONE FALSIFICATA: C ≈ A — il loop NON c'entra.")
        print("     La causa del >240s sta altrove, e «caricare all'avvio» non basta.")
    else:
        print("  ⇒ PARZIALE: C/A fra 1,5 e 5. Il loop pesa ma non spiega un 11x:")
        print("     serve un'altra variabile, e non la invento qui.")
print("\n⚠️  un solo giro per regime; il carico del loop e' il caso peggiore")
print("   (sleep(0) in ciclo stretto), non il carico di un server reale.")
