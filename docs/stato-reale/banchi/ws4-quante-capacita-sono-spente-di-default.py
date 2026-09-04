# -*- coding: utf-8 -*-
"""QUANTE CAPACITA' DEL PRODOTTO SONO SPENTE DI DEFAULT?

Non e' una domanda nuova, ed e' questo il punto: e' stata fatta DUE volte su
DUE casi diversi, da due istanze diverse, senza che nessuno contasse.
  · `W2-67`  — `ENGRAM_GRADED_ADMISSION`: «la cura esiste, funziona, ED E'
    SPENTA», default OFF.
  · `LANT-54` — la meta' di vetrina della stessa: «l'utente puo' SAPERE che
    esiste?»
  · `W7-139` (mia, oggi) — `ENGRAM_CAPABILITY_GATE`: `off` di default, e la
    scelta e' dichiarata solo nel docstring di una funzione privata.
Tre celle, due capacita', zero conteggi. In memoria c'e' anche la preferenza
di chi decide: «niente default OFF».

IL RIGHELLO — e perche' NON e' un grep di `FLAGS-AUDIT.md`: quel documento
elenca i nomi ma dichiara lui stesso, alla riga 99, che i default «NOT
individually verified». Il default si legge DOVE IL CODICE LO LEGGE: ogni
`os.environ.get("ENGRAM_...", <default>)` porta il suo valore di riposo. AST,
non regex, perche' una stringa spezzata su piu' righe sfugge alla regex.

CRITERIO DICHIARATO — «interruttore» e' un flag il cui default e' un valore
booleano riconoscibile ("0"/"1"/"on"/"off"/"true"/"false"/""), non una soglia
(`0.42`), non un percorso, non un nome di modello. Un interruttore e' SPENTO
se il default e' "0" / "off" / "false" / "" / None.

CONTROLLO OBBLIGATORIO: devono uscire anche interruttori ACCESI. Se il
conteggio dice «sono tutti spenti», il righello sta selezionando solo un lato
e il numero non si pubblica.

⚠️ LIMITE: un flag letto una volta sola con `os.environ[...]` (senza default)
non lo vedo; e un default calcolato a runtime nemmeno. Il numero e' un MINIMO.
"""
import ast
import io
import os
from collections import Counter

RADICE = os.environ.get("WS4_REPO", ".")
PKG = os.path.join(RADICE, "verimem")
# ⚠️ IL RIGHELLO SBAGLIAVA A FAVORE DEL REPERTO, terza volta oggi: contavo ''
# fra gli SPENTI e usciva 66. Ma per `ENGRAM_GROUNDING_THRESHOLD`,
# `ENCODE_IDLE_S`, `BAND_LOCAL_MODEL`, `DOC_ROOTS` la stringa vuota vuol dire
# «non impostato dall'utente, il valore lo decide il codice piu' sotto» — NON
# «capacita' disattivata». Un interruttore spento si riconosce da un default
# ESPLICITO. Il resto lo dichiaro non determinabile staticamente e NON lo
# conto: un numero gonfio a favore della tesi e' peggio di un numero piccolo.
SPENTI = {"0", "off", "false", "no", "disabled"}
ACCESI = {"1", "on", "true", "yes", "enabled"}
VUOTI = {"", "none"}


def letture(percorso):
    """Ogni os.environ.get / os.getenv su un nome ENGRAM_*, col suo default."""
    try:
        albero = ast.parse(io.open(percorso, encoding="utf-8").read())
    except SyntaxError:
        return []
    fuori = []
    for n in ast.walk(albero):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nome = f.attr if isinstance(f, ast.Attribute) else (
            f.id if isinstance(f, ast.Name) else "")
        if nome not in ("get", "getenv"):
            continue
        if not n.args or not isinstance(n.args[0], ast.Constant):
            continue
        chiave = n.args[0].value
        if not isinstance(chiave, str) or not chiave.startswith("ENGRAM_"):
            continue
        default = None
        if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
            default = n.args[1].value
        for kw in n.keywords:
            if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                default = kw.value.value
        fuori.append((chiave, default, os.path.basename(percorso)))
    return fuori


tutte = []
for radice, _, file in os.walk(PKG):
    if "__pycache__" in radice:
        continue
    for nome in file:
        if nome.endswith(".py"):
            tutte.extend(letture(os.path.join(radice, nome)))

# un flag puo' essere letto in piu' punti: tengo il default piu' comune
per_chiave = {}
for chiave, default, dove in tutte:
    per_chiave.setdefault(chiave, []).append((default, dove))

spenti, accesi, vuoti, non_interruttori = [], [], [], []
for chiave, letti in sorted(per_chiave.items()):
    valori = [str(d).strip().lower() if d is not None else "none"
              for d, _ in letti]
    comune = Counter(valori).most_common(1)[0][0]
    dove = letti[0][1]
    if comune in SPENTI:
        spenti.append((chiave, comune, dove, len(letti)))
    elif comune in ACCESI:
        accesi.append((chiave, comune, dove, len(letti)))
    elif comune in VUOTI:
        vuoti.append((chiave, comune, dove))
    else:
        non_interruttori.append((chiave, comune))

print(f"  flag ENGRAM_* letti con un default nel pacchetto:"
      f" {len(per_chiave)}   ({len(tutte)} letture in totale)")
print(f"  · interruttori SPENTI di default (esplicito) : {len(spenti)}")
print(f"  · interruttori ACCESI di default (esplicito) : {len(accesi)}")
print(f"  · default VUOTO — NON determinabile da qui   : {len(vuoti)}"
      f"   (li dichiaro, non li conto)")
print(f"  · non interruttori (soglie, path, modelli)   : "
      f"{len(non_interruttori)}")

print("\n  == IL CONTROLLO ==")
if not accesi:
    print("   ⛔ ROTTO: nessun interruttore acceso trovato — il righello")
    print("      sta guardando un lato solo. Non pubblico il numero.")
    raise SystemExit(0)
print(f"   ✅ ACCESO: escono anche {len(accesi)} interruttori ON"
      f" (es. {accesi[0][0]}={accesi[0][1]}) ⇒ il criterio non seleziona"
      " un lato solo.")

print("\n  == CHI E' SPENTO, per nome (mai il solo conteggio) ==")
for chiave, val, dove, n in spenti:
    print(f"   ⚫ {chiave:38s} default={val!r:8s} {dove} ({n} letture)")

print("\n  == E QUELLI ACCESI, per confronto onesto ==")
for chiave, val, dove, n in accesi:
    print(f"   🟢 {chiave:38s} default={val!r:8s} {dove}")
