"""Quante celle CRONOMETRANO ancora: `sleep` REALE contro una soglia.

🔴 PERCHE' CONTA, misurato il 2026-09-10 alle 21:43 su questa macchina::

    py -3.11  ->  3.11.9   monotonic = GetTickCount64()           0.015625 s
    python    ->  3.13.12  monotonic = QueryPerformanceCounter()  1e-07
    py -3.14  ->  3.14.3   monotonic = QueryPerformanceCounter()  1e-07

**Il cambio di orologio e' avvenuto fra 3.12 e 3.13**, e la matrice della CI
gira `windows-latest / py3.12`: li' `time.monotonic()` scatta ogni **15,625
ms**. Una cella che dorme 60 ms contro un cooldown di 50 ha **10 ms di
margine** — meno di un tick — e cade a caso. E' la causa del rosso T38, trovata
da @ws3 il 10/09 dopo che io l'avevo diagnosticata l'08/09 e **RITIRATA a
torto**: avevo misurato con 3.13 e concluso per 3.12.

⇒ Ogni riga di questo elenco e', su py3.12, una caduta che aspetta. I margini
contano in TICK, non in millisecondi: 50 ms sono tre tick, 100 ms sei.

⚠️ La v1 usava un regex e ha contato `time.sleep(0.06)` **dentro un docstring**
— la riga in cui @Tara CITA la vecchia forma per spiegarla. Stavo per portarle
un rilievo falso sulla cella che aveva appena curato.
🔑 Un `grep` non distingue il codice dalla prosa che parla del codice: qui
servono i nodi (`ast.Call` su `time.sleep`), non le stringhe.
"""
from __future__ import annotations

import ast
import pathlib
import sys

albero = ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))

print("celle con uno `sleep` REALE (nodo, non testo):")
totale = 0
for n in albero.body:
    if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    sleeps: list[str] = []
    soglie: list[str] = []
    for figlio in ast.walk(n):
        if isinstance(figlio, ast.Call):
            f = figlio.func
            if isinstance(f, ast.Attribute) and f.attr == "sleep" and figlio.args:
                a = figlio.args[0]
                sleeps.append(str(a.value) if isinstance(a, ast.Constant) else "?")
            #: `monkeypatch.setenv("…COOLDOWN_S", "0.05")`
            if isinstance(f, ast.Attribute) and f.attr == "setenv" and len(figlio.args) >= 2:
                chiave = figlio.args[0]
                val = figlio.args[1]
                if isinstance(chiave, ast.Constant) and "COOLDOWN" in str(chiave.value) \
                   and isinstance(val, ast.Constant):
                    soglie.append(str(val.value))
    if sleeps and soglie:
        totale += 1
        margini = []
        for s in sleeps:
            for c in soglie:
                try:
                    margini.append(round((float(s) - float(c)) * 1000))
                except ValueError:
                    pass
        print(f"   {n.name[:54]:54s} cooldown={soglie} sleep={sleeps} "
              f"margine={margini} ms")
    elif sleeps:
        print(f"   {n.name[:54]:54s} sleep={sleeps} (nessuna soglia di cooldown)")
print(f"\n   celle che cronometrano contro una soglia: {totale}")
