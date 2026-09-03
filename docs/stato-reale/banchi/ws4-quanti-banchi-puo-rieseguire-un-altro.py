# -*- coding: utf-8 -*-
"""QUANTI DEI NOSTRI BANCHI VERSATI PUO' RIESEGUIRE QUALCUN ALTRO?

Un banco nel repo con la sua cella nel registro e' una PROMESSA di
riproducibilita'. Il mio `ws4-t11-factcg-su-halueval-*` non la mantiene: si
ferma con un messaggio onesto perche' il dump di ingresso non e' versato.
La domanda e' se sia un caso mio o una forma comune.

IL RIGHELLO — e perche' NON e' un grep: le stringhe spezzate su piu' righe
(implicit concatenation) sfuggono alla regex, e il 03/09 questo mi ha gia'
prodotto un numero falso («0/493 banchi con percorso di sessione», il vero
era 8). Qui i percorsi si estraggono con l'AST, che vede la stringa gia'
ricomposta dal parser.

CONTROLLO POSITIVO (obbligatorio, se non si accende il banco non misura):
  · un banco che legge un file ESISTENTE deve risultare PULITO
  · un banco che legge un file ASSENTE deve essere PRESO
Se il secondo elenco e' vuoto, il righello e' rotto: lo dichiaro e non
pubblico il numero.

LIMITE DICHIARATO: la modalita' (lettura/scrittura) la deduco dagli argomenti
di `open`; un percorso costruito a runtime (f-string, join di variabili) NON
lo vedo, quindi il numero e' un MINIMO, mai un totale.
"""
import ast
import io
import os
import sys

RADICE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
BANCHI = os.path.join(RADICE, "docs", "stato-reale", "banchi")
ESTENSIONI = (".jsonl", ".json", ".csv", ".txt", ".md", ".tsv", ".npy")


def stringhe_di_dati(albero):
    """Ogni costante-stringa che nomina un file di dati, con la modalita'."""
    trovate = {}
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call):
            continue
        nome = ""
        f = nodo.func
        if isinstance(f, ast.Name):
            nome = f.id
        elif isinstance(f, ast.Attribute):
            nome = f.attr
        if nome not in ("open", "read_text", "read_json", "load"):
            continue
        # la modalita': secondo posizionale o mode=
        modo = "r"
        if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant):
            modo = str(nodo.args[1].value)
        for kw in nodo.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                modo = str(kw.value.value)
        for arg in nodo.args[:1]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    v = sub.value
                    if v.lower().endswith(ESTENSIONI):
                        # se lo stesso file compare anche in scrittura, vince
                        # la scrittura: e' un'uscita, non una dipendenza.
                        if "w" in modo or "a" in modo:
                            trovate[v] = "w"
                        else:
                            trovate.setdefault(v, "r")
    return trovate


def variabili_ambiente(albero):
    """Le dipendenze DICHIARATE via os.environ — sono la forma onesta."""
    fuori = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) \
                and nodo.func.attr in ("get", "getenv"):
            for a in nodo.args[:1]:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) \
                        and a.value.isupper() and "_" in a.value:
                    fuori.add(a.value)
    return fuori


pulito, rotti, dichiarati, illeggibili, cwd_legata = [], [], [], [], []
for nome in sorted(os.listdir(BANCHI)):
    if not nome.endswith(".py"):
        continue
    percorso = os.path.join(BANCHI, nome)
    try:
        albero = ast.parse(io.open(percorso, encoding="utf-8").read())
    except SyntaxError as e:
        illeggibili.append((nome, str(e)[:60]))
        continue
    letti = {p: m for p, m in stringhe_di_dati(albero).items() if m == "r"}
    # ⚠️ IL RIGHELLO SBAGLIAVA A FAVORE DEL REPERTO: cercavo il file solo
    # dalla RADICE, e cosi' contavo «mancante» un dump che sta VERSATO
    # accanto al banco. Un file trovato solo li' non e' mancante: e' un
    # banco che gira SOLO se lo lanci da quella cartella, e non lo dice.
    mancanti, solo_accanto = [], []
    for p in letti:
        if os.path.exists(p) or os.path.exists(os.path.join(RADICE, p)):
            continue
        if os.path.exists(os.path.join(BANCHI, p)):
            solo_accanto.append(p)
        else:
            mancanti.append(p)
    amb = variabili_ambiente(albero)
    if solo_accanto and not mancanti:
        cwd_legata.append((nome, solo_accanto))
    elif mancanti:
        rotti.append((nome, mancanti))
    elif amb and not letti:
        dichiarati.append((nome, sorted(amb)))
    elif letti:
        pulito.append((nome, sorted(letti)))

tot = len(pulito) + len(rotti) + len(dichiarati) + len(cwd_legata)
print(f"  banchi con almeno un file di dati LETTO: {tot}"
      f"   (su {len([n for n in os.listdir(BANCHI) if n.endswith('.py')])}"
      f" file .py nella cartella)")
print(f"  · leggono un file CHE C'E':          {len(pulito)}")
print(f"  · il dato e' VERSATO ma solo accanto"
      f" al banco:  {len(cwd_legata)}   (gira solo da quella cartella)")
print(f"  · leggono un file CHE NON C'E':      {len(rotti)}")
print(f"  · dipendenza dichiarata via env:     {len(dichiarati)}")
if illeggibili:
    print(f"  · non parsati:                       {len(illeggibili)}")

print("\n  == IL CONTROLLO POSITIVO ==")
acceso_a = len(pulito) > 0
acceso_b = len(rotti) > 0 or len(dichiarati) > 0
print(f"   (a) almeno un banco legge un file esistente: "
      f"{'ACCESO' if acceso_a else 'SPENTO'}  ({len(pulito)})")
print(f"   (b) almeno un banco dipende da un file assente: "
      f"{'ACCESO' if acceso_b else 'SPENTO'}  ({len(rotti)+len(dichiarati)})")
if not (acceso_a and acceso_b):
    print("   ⛔ righello ROTTO: non pubblico il numero.")
    raise SystemExit(0)

print("\n  == CHI CADE, per nome (mai il solo conteggio) ==")
for nome, m in rotti:
    print(f"   ⛔ {nome}")
    for p in sorted(m)[:3]:
        print(f"        legge: {p}")
for nome, m in cwd_legata:
    print(f"   🟡 {nome}  → il dato c'e' ma solo in banchi/: {sorted(m)[0]}")
for nome, a in dichiarati:
    print(f"   ⚠️  {nome}  → chiede {', '.join(a)} e si ferma se manca")
if not rotti and not dichiarati and not cwd_legata:
    print("   (nessuno)")


def miei(elenco):
    return [n for n, _ in elenco if n.startswith("ws4-")]


print(f"\n  == E I MIEI? ==  rotti {len(miei(rotti))}/{len(rotti)} ·"
      f" legati alla cwd {len(miei(cwd_legata))}/{len(cwd_legata)} ·"
      f" dichiarati {len(miei(dichiarati))}/{len(dichiarati)}"
      f"   (se sono zero, guarda meglio prima di pubblicare)")
