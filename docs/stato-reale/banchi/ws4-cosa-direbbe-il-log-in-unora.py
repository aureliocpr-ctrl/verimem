# -*- coding: utf-8 -*-
"""MATRICE DEI PERMESSI ② — cosa direbbe il log su un'ora di uso REALE.

Il mandato chiede di accendere il gate in modalita' AVVISO e misurare cosa
direbbe il log. Ma il log si puo' misurare PRIMA di accendere qualunque cosa:
il journal registra gia' ogni chiamata di tool (`audit_tool_call`), e il
registro dice gia' quali tool sono classificati. Il prodotto delle due cose e'
esattamente cio' che il gate scriverebbe.

⇒ questo banco NON accende niente e NON tocca il server: risponde alla domanda
con i dati che ci sono. Se il numero e' insostenibile, l'accensione va
ripensata PRIMA, non dopo aver riempito il journal.

⚠️ LIMITE DICHIARATO: il journal registra le chiamate passate dalla porta MCP.
Le chiamate fatte dalla CLI o da dentro il codice non ci sono ⇒ e' un limite
INFERIORE sul traffico, e quindi sul numero di righe che il gate scriverebbe.
"""
import io
import json
from collections import Counter

J = ["C:/Users/aurel/.engram/events.jsonl",
     "C:/Users/aurel/.engram/events.jsonl.1"]

from verimem.tool_registry import REGISTRY  # noqa: E402

classificati = set(REGISTRY._caps)

chiamate = Counter()
ore = Counter()
n = 0
for f in J:
    try:
        righe = io.open(f, encoding="utf-8", errors="replace")
    except OSError:
        continue
    for riga in righe:
        riga = riga.strip()
        if not riga:
            continue
        try:
            d = json.loads(riga)
        except Exception:
            continue
        if d.get("name") != "audit_tool_call":
            continue
        p = d.get("payload") or {}
        if not isinstance(p, dict):
            continue
        nome = p.get("tool") or p.get("name") or p.get("tool_name") or "?"
        chiamate[nome] += 1
        ts = str(d.get("ts") or "")[:13]
        ore[ts] += 1
        n += 1

print(f"  chiamate di tool nel journal: {n}")
if n == 0:
    print("  ⛔ CONTROLLO SPENTO: zero chiamate trovate — o il nome dell'evento")
    print("     non e' `audit_tool_call`, o il payload non porta il nome del tool.")
    print("     Il numero sotto non si puo' dare.")
    raise SystemExit(0)

print(f"  tool distinti chiamati:      {len(chiamate)}")
sconosciuti_chiamati = {k: v for k, v in chiamate.items() if k not in classificati}
q = sum(sconosciuti_chiamati.values())
print(f"\n  == COSA SCRIVEREBBE IL GATE IN MODALITA' «warn» ==")
print(f"    chiamate a tool SCONOSCIUTI: {q}/{n} = {100*q/n:.1f}%")
print(f"    tool distinti sconosciuti:   {len(sconosciuti_chiamati)}")
if ore:
    print(f"    ore distinte nel journal:    {len(ore)}")
    print(f"    ⇒ righe di audit PER ORA:    {q/len(ore):.1f}"
          f"   (media su tutto il journal)")
    picco = ore.most_common(1)[0]
    print(f"    l'ora piu' intensa: {picco[0]} con {picco[1]} chiamate")

print("\n  i 12 tool sconosciuti PIU' CHIAMATI (da classificare per primi):")
for k, v in Counter(sconosciuti_chiamati).most_common(12):
    print(f"    {v:>5}  {k}")

coperti = sum(v for k, v in chiamate.items() if k in classificati)
print(f"\n  🔑 IL NUMERO CHE DECIDE L'ORDINE DEL LAVORO:")
print(f"    i 20 tool gia' classificati coprono {coperti}/{n} = {100*coperti/n:.1f}%"
      f" del traffico reale")
top12 = sum(v for _, v in Counter(sconosciuti_chiamati).most_common(12))
print(f"    classificando i 12 sconosciuti piu' chiamati si coprirebbe"
      f" un altro {100*top12/n:.1f}%")
