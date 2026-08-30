"""Controllo: il 98% regge togliendo gli zeri del regime degradato?
E regge su piu' soglie? (0.8797 misurato ora, 0.8881 misurato ieri)"""
import datetime
import json
import os

BANCO_DA = datetime.datetime(2026, 8, 31, 0, 50).timestamp()
base = os.path.expanduser("~/.engram")
pop = []
for f in (os.path.join(base, "events.jsonl.1"), os.path.join(base, "events.jsonl")):
    if not os.path.exists(f):
        continue
    for ln in open(f, encoding="utf-8", errors="replace"):
        if "flow.recall" not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("name") != "flow.recall":
            continue
        pl = d.get("payload") or {}
        b = pl.get("best")
        if b is None:
            continue
        try:
            b, t = float(b), float(d.get("ts") or 0)
        except Exception:
            continue
        if t >= BANCO_DA:
            continue
        pop.append((b, bool(pl.get("abstained")), int(pl.get("n") or 0)))

tot = len(pop)
zeri = [x for x in pop if x[0] <= 0.0]
vivi = [x for x in pop if x[0] > 0.0]
print(f"recall reali con best: {tot}")
print(f"  best == 0 (regime degradato / astensione): {len(zeri)} = "
      f"{100.0 * len(zeri) / tot:.1f}%")
print(f"  best  > 0 (la popolazione onesta):         {len(vivi)}")
ast = sum(1 for x in vivi if x[1])
print(f"  di quelle, con abstained=True: {ast}")
s = sorted(x[0] for x in vivi)
n = len(s)
print(f"\ndistribuzione dei best > 0:  min={s[0]:.3f} p05={s[int(n*0.05)]:.3f} mediana={s[n//2]:.3f} p95={s[int(n*0.95)]:.3f} max={s[-1]:.3f}")
print("\nquanto taglierebbe ogni soglia, sui best > 0:")
for pav, eti in ((0.8797, "ricalcolo di ADESSO, daemon caldo"),
                 (0.8881, "ricalcolo di ieri sera"),
                 (0.868,  "max dentro-dominio misurato da ws2"),
                 (0.850,  "la mediana del traffico stesso"),
                 (0.0,    "il valore degenere di oggi")):
    k = sum(1 for x in s if x < pav)
    print(f"   {pav:.4f}  {eti:<36s}  taglia {k:5d}/{n} = {100.0 * k / n:5.1f}%")
