"""La quota di avvisi converge, o cambia ogni volta che la guardo?

Storia di questo banco: ho pubblicato "l'avviso si accende sull'87,5% delle
letture" con n=72 e mezz'ora di traffico, DICHIARANDO che andava rifatto. Mezz'ora
dopo, con n=111, era 71,2% - sedici punti in meno. Il limite dichiarato si e'
avverato nel giro di trenta minuti.

Dare un terzo numero sarebbe ripetere l'errore. Qui misuro invece SE il numero
converge: la quota calcolata su finestre crescenti, dalla piu' vecchia in avanti.
Se la curva si appiattisce, il numero e' misurabile e si puo' citare. Se
continua a muoversi, va detto che NON e' ancora misurabile - il che e' un
risultato, non un fallimento.

Stampa anche i BUCHI del traffico: la finestra coperta e' risultata piu' corta
del tempo trascorso, quindi le letture non sono distribuite in modo uniforme e
una media su tutto il periodo sarebbe ingannevole.

SOLA LETTURA.
"""
import datetime
import json
import os

PAV = 0.8781
DA = datetime.datetime(2026, 8, 31, 2, 52, 23).timestamp()   # il ricalcolo
base = os.path.expanduser("~/.engram")

serie = []
for f in (os.path.join(base, "events.jsonl.1"), os.path.join(base, "events.jsonl")):
    if not os.path.exists(f):
        continue
    for ln in open(f, encoding="utf-8", errors="replace"):
        if "flow.recall" not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:      # noqa: BLE001 - righe non JSON si saltano
            continue
        if d.get("name") != "flow.recall":
            continue
        pl = d.get("payload") or {}
        b = pl.get("best")
        if b is None:
            continue
        try:
            b, t = float(b), float(d.get("ts") or 0)
        except Exception:      # noqa: BLE001
            continue
        if t >= DA and b > 0.0:
            serie.append((t, b))

serie.sort()
n = len(serie)
print("recall con best>0 dopo il ricalcolo: %d" % n)
if not n:
    raise SystemExit(0)

t0, t1 = serie[0][0], serie[-1][0]
print("prima %s   ultima %s   arco %.0f minuti"
      % (datetime.datetime.fromtimestamp(t0).strftime("%H:%M:%S"),
         datetime.datetime.fromtimestamp(t1).strftime("%H:%M:%S"),
         (t1 - t0) / 60.0))

print("\nLA STIMA SU FINESTRE CRESCENTI (dalla piu' vecchia in avanti)")
print("%8s %10s %10s %s" % ("n", "sotto", "quota", "mediana"))
tappe = [x for x in (20, 40, 60, 80, 100, 120, 150, 200, 300) if x < n] + [n]
for k in tappe:
    g = [b for _t, b in serie[:k]]
    sotto = sum(1 for x in g if x < PAV)
    med = sorted(g)[k // 2]
    print("%8d %10d %9.1f%% %8.4f" % (k, sotto, 100.0 * sotto / k, med))

print("\nSE LA QUOTA SI MUOVE ANCORA fra le ultime due righe, il numero non e'")
print("ancora misurabile e va detto cosi'.")

print("\nI BUCHI: quante letture per intervallo di 10 minuti")
passo = 600.0
inizio = t0
etichette = []
while inizio <= t1:
    k = sum(1 for t, _b in serie if inizio <= t < inizio + passo)
    etichette.append((datetime.datetime.fromtimestamp(inizio).strftime("%H:%M"), k))
    inizio += passo
for e, k in etichette:
    print("  %s  %3d  %s" % (e, k, "#" * min(60, k)))
