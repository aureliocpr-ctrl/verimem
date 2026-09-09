"""`tools.py` (19): l'esecutore di codice e l'analizzatore statico.

Il codice eseguito qui è **mio e innocuo** (`print`, un ciclo, un `time.sleep`
per provare il timeout): l'esecutore gira in un sottoprocesso, e il docstring
dice chiaramente che «non è un sandbox di sicurezza completo».

Le tre domande che decidono:
  · il **timeout duro** si prova con un programma che non finisce;
  · il **taglio dell'uscita** (`max_chars`) si prova stampando più caratteri;
  · `DockerPythonExecutor.available()` e la fabbrica `make_python_executor`
    promettono un ripiego quando Docker non c'è: si misura **quale** esecutore
    torna davvero.
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
from verimem import tools as T  # noqa: E402

print("=== ToolResult / to_observation")
r = T.ToolResult(ok=True, output="5900 euro")
print("  ToolResult:", r, "| to_observation():", repr(r.to_observation()))
r2 = T.ToolResult(ok=False, output="", error="e' caduto")
print("  fallito   :", repr(r2.to_observation()))

print("\n=== PythonExecutor: il caso buono, il timeout, il taglio, l'errore")
ex = T.PythonExecutor(timeout_s=3, max_chars=200)
buono = ex.run("print(2 + 2)")
print("  print(2+2)      -> ok:", buono.ok, "| output:", repr(buono.output.strip()))
errore = ex.run("raise ValueError('rotto di proposito')")
print("  raise           -> ok:", errore.ok, "| error:", repr(str(errore.error)[:80]))
t0 = time.perf_counter()
lento = ex.run("import time\ntime.sleep(30)\nprint('non dovrei arrivare qui')")
dt = time.perf_counter() - t0
print(f"  sleep(30) con timeout 3s -> ok: {lento.ok} | tornato in {dt:.1f}s "
      f"| error: {str(lento.error)[:60]!r}")
lungo = ex.run("print('x' * 5000)")
print("  print('x'*5000) con max_chars=200 -> lunghezza uscita:",
      len(lungo.output), "| <= 200 (piu' l'avviso):", len(lungo.output) <= 260)
print("  stdin:", repr(ex.run("print(input())", stdin="ciao").output.strip()))

print("\n=== run_with_tests: il codice candidato e la sua verifica")
sorgente = "def somma(a, b):\n    return a + b\n"
test_ok = "assert somma(2, 3) == 5\nprint('OK')\n"
test_ko = "assert somma(2, 3) == 6\n"
print("  test che passa  -> ok:", ex.run_with_tests(sorgente, test_ok).ok)
esito_ko = ex.run_with_tests(sorgente, test_ko)
print("  test che fallisce -> ok:", esito_ko.ok, "| error contiene AssertionError:",
      "AssertionError" in str(esito_ko.error))

print("\n=== DockerPythonExecutor: c'e' Docker su questa macchina?")
dk = T.DockerPythonExecutor(timeout_s=5, max_chars=200)
# `available` è una @property (riga 136), non un metodo: `dk.available()` dà
# «'bool' object is not callable». L'`ast` la vede come `def`, il decoratore no.
disponibile = dk.available
print("  available (property):", disponibile)
if disponibile:
    print("  run(print(2+2)):", dk.run("print(2 + 2)").output.strip()[:60])
else:
    print("  (non misurato il ramo che esegue: Docker non risponde qui)")
    esito = dk.run("print(2 + 2)")
    print("  run comunque ->", "ok:", esito.ok, "| error:", str(esito.error)[:80])

print("\n=== make_python_executor: la fabbrica e il ripiego")
os.environ.pop("HIPPO_PYTHON_EXEC_BACKEND", None)
print("  senza variabile        ->", type(T.make_python_executor(3, 200)).__name__)
os.environ["HIPPO_PYTHON_EXEC_BACKEND"] = "docker"
print("  backend=docker         ->", type(T.make_python_executor(3, 200)).__name__,
      "(se Docker non c'e', il docstring promette il ripiego)")
os.environ["HIPPO_PYTHON_EXEC_BACKEND"] = "banana"
print("  backend=banana (ignoto)->", type(T.make_python_executor(3, 200)).__name__)
os.environ.pop("HIPPO_PYTHON_EXEC_BACKEND", None)

print("\n=== CodeAnalyzer: i controlli statici")
print("  syntax_check(valido)   :", T.CodeAnalyzer.syntax_check("def f():\n    return 1\n"))
print("  syntax_check(rotto)    :", T.CodeAnalyzer.syntax_check("def f(:\n"))
print("  find_function(presente):",
      str(T.CodeAnalyzer.find_function("def somma(a, b):\n    return a+b\n", "somma"))[:90])
print("  find_function(assente) :",
      T.CodeAnalyzer.find_function("def somma(a, b):\n    return a+b\n", "differenza"))
semplice = "def f(x):\n    return x\n"
complicata = ("def g(x):\n"
              "    if x > 0:\n        return 1\n"
              "    elif x < -10:\n        return 2\n"
              "    for i in range(3):\n"
              "        if i:\n            return 3\n"
              "    while x:\n        x -= 1\n"
              "    return 0\n")
print("  cyclomatic(semplice)   :", T.CodeAnalyzer.cyclomatic(semplice))
print("  cyclomatic(ramificata) :", T.CodeAnalyzer.cyclomatic(complicata))
print("  >>> la complessita' cresce col numero di rami:",
      T.CodeAnalyzer.cyclomatic(complicata).extra["complexity"]
      > T.CodeAnalyzer.cyclomatic(semplice).extra["complexity"])
print("  cyclomatic su codice ROTTO:",
      str(T.CodeAnalyzer.cyclomatic("def f(:\n"))[:88])

print("\n=== _ast_node_count / ToolSpec / default_tools")
import ast  # noqa: E402

print("  _ast_node_count(semplice):", T._ast_node_count(ast.parse(semplice)),
      "| (ramificata):", T._ast_node_count(ast.parse(complicata)))
strumenti = T.default_tools()
print("  default_tools():", len(strumenti), "strumenti ->",
      [getattr(s, "name", "?") for s in (strumenti.values() if isinstance(strumenti, dict)
                                          else strumenti)][:8])
uno = (list(strumenti.values()) if isinstance(strumenti, dict) else strumenti)[0]
print("  il primo ToolSpec:", {k: str(v)[:40] for k, v in vars(uno).items()}
      if hasattr(uno, "__dict__") else uno)
