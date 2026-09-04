# -*- coding: utf-8 -*-
"""Quanti dei 249 strumenti esposti hanno una classificazione di rischio?

Misura per AST, zero import: importare il server e' proprio cio' che nel
ticket 1 resta fermo minuti, e un'altra istanza sta cronometrando quella strada.

DUE CONTROLLI POSITIVI, uno per lato, e se non si accendono il righello e'
rotto e il numero non si pubblica:
  · esposti     deve dare 249  (misura indipendente di un'altra istanza, oggi)
  · classificati deve dare  50  (mia misura per import, len(REGISTRY._caps))
"""
import ast
import io
import re
import sys
from collections import Counter
from pathlib import Path

# la radice del repo si deriva dalla posizione del banco
# (banchi -> stato-reale -> docs -> repo): cosi gira da chiunque.
W = str(Path(__file__).resolve().parents[3]) + "/"

SRV = W + "verimem/mcp_server.py"
REG = W + "verimem/tool_registry.py"


def nome_kw(chiamata):
    """Il name= di una chiamata, se e' una stringa letterale."""
    for kw in chiamata.keywords:
        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                return kw.value.value
    return None


def chiamate(albero, nomi_funzione):
    """Tutte le ast.Call il cui callee finisce con uno dei nomi dati."""
    fuori = []
    for n in ast.walk(albero):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        etichetta = getattr(f, "attr", None) or getattr(f, "id", None)
        if etichetta in nomi_funzione:
            fuori.append(n)
    return fuori


# ── ① gli strumenti ESPOSTI dal server ─────────────────────────────────────
src = io.open(SRV, encoding="utf-8").read()
alb = ast.parse(src)
tutte = chiamate(alb, {"Tool"})
esposti = [nome_kw(c) for c in tutte]
senza_nome = sum(1 for x in esposti if x is None)
esposti = [x for x in esposti if x]

dentro = None
for n in ast.walk(alb):
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if n.name == "_list_tools_unfiltered":
            dentro = [nome_kw(c) for c in chiamate(n, {"Tool"})]
            dentro = [x for x in dentro if x]

print("=== ① STRUMENTI ESPOSTI (ast, zero import) ===")
print(f"  chiamate Tool(...) nel file        : {len(tutte)}")
print(f"    di cui con name= letterale       : {len(esposti)}"
      f"   (senza name letterale: {senza_nome})")
print(f"  dentro _list_tools_unfiltered      : "
      f"{len(dentro) if dentro is not None else 'FUNZIONE NON TROVATA'}")
print(f"  nomi distinti                      : {len(set(esposti))}")
c1 = len(set(esposti)) == 249
print(f"  🎯 CONTROLLO POSITIVO 1 (== 249)   : "
      f"{'ACCESO' if c1 else 'SPENTO -> il righello o il perimetro non torna'}")
pref = Counter(n.split("_")[0] for n in esposti)
print(f"  prefissi: {dict(pref.most_common(5))}")

# ── ② gli strumenti CLASSIFICATI nel registro dei permessi ─────────────────
srcr = io.open(REG, encoding="utf-8").read()
albr = ast.parse(srcr)
caps = chiamate(albr, {"ToolCapability"})
classificati = [nome_kw(c) for c in caps]
classificati = [x for x in classificati if x]

# i campi che dicono la GRAVITA', letti dalla chiamata stessa
def kw_vero(chiamata, campo):
    for kw in chiamata.keywords:
        if kw.arg == campo and isinstance(kw.value, ast.Constant):
            return kw.value.value is True
    return False


scrivono = sum(1 for c in caps if kw_vero(c, "writes_memory"))
eseguono = sum(1 for c in caps if kw_vero(c, "executes_command"))
confermano = sum(1 for c in caps if kw_vero(c, "requires_confirm"))
bypass = sum(1 for c in caps if kw_vero(c, "gating_bypass"))

print()
print("=== ② STRUMENTI CLASSIFICATI (registro dei permessi) ===")
print(f"  ToolCapability(...) con name=      : {len(classificati)}"
      f"   distinti: {len(set(classificati))}")
c2 = len(set(classificati)) == 50
print(f"  🎯 CONTROLLO POSITIVO 2 (== 50)    : "
      f"{'ACCESO' if c2 else 'SPENTO -> non e la stessa popolazione di prima'}")
print(f"  writes_memory=True   {scrivono:3d}"
      f"   ·  executes_command=True {eseguono:3d}")
print(f"  requires_confirm=True {confermano:3d}"
      f"   ·  gating_bypass=True    {bypass:3d}")

# ── ③ la copertura, che e' la domanda ──────────────────────────────────────
E, C = set(esposti), set(classificati)
scoperti = sorted(E - C)
classificati_non_esposti = sorted(C - E)
print()
print("=== ③ LA COPERTURA ===")
print(f"  esposti          {len(E)}")
print(f"  classificati     {len(C)}")
print(f"  COPERTI          {len(E & C):4d}  = {100 * len(E & C) / len(E):.1f}%"
      f" degli esposti")
print(f"  SCOPERTI         {len(scoperti):4d}"
      f"  = {100 * len(scoperti) / len(E):.1f}%")
print(f"  classificati che NON risultano esposti: "
      f"{len(classificati_non_esposti)}  {classificati_non_esposti[:6]}")

# ── ④ fra gli SCOPERTI, chi ha un nome che PROMETTE una scrittura ──────────
#     e' un sospetto per NOME, non una classificazione: lo dico.
VERBI = ("forget", "delete", "retire", "merge", "edit", "promote", "import",
         "remember", "record", "save", "prune", "supersede", "resolve",
         "heal", "apply", "adopt", "register", "link", "update", "consolidate",
         "cleanup", "dedup", "restore", "archive", "clone", "fork", "run")
# il confine a DESTRA e' obbligatorio: senza, «heal» si mangia «health» e il
# righello gonfia i sospetti — sbagliando, come sempre, a favore del reperto.
sospetti = [n for n in scoperti
            if any(re.search(rf"(^|_){v}(_|$)", n) for v in VERBI)]
gonfi = [n for n in scoperti
         if any(re.search(rf"(^|_){v}", n) for v in VERBI)
         and not any(re.search(rf"(^|_){v}(_|$)", n) for v in VERBI)]
print()
print("=== ④ FRA GLI SCOPERTI, QUANTI HANNO UN NOME DA SCRITTURA ===")
print(f"  ⚠️ sospetto per NOME, non classificazione (il mio righello a"
      f" finestra fissa una volta ha detto episode_list=DESTRUCTIVE)")
print(f"  scoperti con verbo di scrittura nel nome: {len(sospetti)}"
      f"  su {len(scoperti)}")
for n in sospetti[:14]:
    print(f"      {n}")
if len(sospetti) > 14:
    print(f"      … e altri {len(sospetti) - 14}")
sys.stdout.flush()
