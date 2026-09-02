"""I 61 sono ASTENSIONI? — il seguito immediato di «chi sono i 61».

Guardando i sei con sovrapposizione zero sono usciti claim come «I have no
comment», «There is no such country», «Fan death is a myth»: non parafrasi
lontane, ma claim che NON ASSERISCONO. Se e' cosi', la mia predizione
(sovrapposizione bassa) ha retto MISURANDO UN SINTOMO, non la causa.

CRITERIO, dichiarato prima: un claim e' un'ASTENSIONE se comincia con una delle
formule di non-risposta di TruthfulQA, oppure nega l'esistenza dell'oggetto.
E' lessicale: per questo ci sono DUE controlli.

  controllo A: «I have no comment» -> astensione
  controllo B: «Madrid» e «Real Union» -> NON astensione
Se uno dei due non torna, il numero non va usato.

DOMANDA CHE DECIDE: la quota di astensioni fra i veri con score<5 e' molto
maggiore di quella fra i veri AMMESSI? Se si', il giudice non sbaglia «sulle
parafrasi»: sbaglia su una classe riconoscibile SENZA di lui.
"""
import io
import json
import re
import sys

DUMP = "punteggi_heldout.jsonl"
DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"

AST = re.compile(
    r"^\s*(i have no comment"
    r"|there (is|are|was|were) (no|not)\b"
    r"|it (is|was) (not|un)"
    r"|no(thing| one| such)\b"
    r"|nobody\b|none of\b|not (necessarily|really|much)\b"
    r"|(this|that|it) (is|was) a myth\b"
    r"|unknown\b|it depends\b|we don't know\b)", re.I)
MITO = re.compile(r"\b(is|are) a myth\b|\bmisconception\b|\bnot true\b", re.I)


def astensione(c):
    c = (c or "").strip()
    return bool(AST.match(c) or MITO.search(c))


dump = {json.loads(x)["i"]: json.loads(x)
        for x in io.open(DUMP, encoding="utf-8") if x.strip()}
dati = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
for i, r in enumerate(dati, 1):
    r["i"] = i
    r["score"] = dump.get(i, {}).get("score")

veri = [r for r in dati if r["label"] == 1 and r["score"] is not None]
bassi = [r for r in veri if r["score"] < 5]
ammessi = [r for r in veri if r["score"] >= 40]

okA = astensione("I have no comment")
okB = not astensione("Madrid") and not astensione("Real Union")
print(f"  controllo A (I have no comment -> astensione): {'ACCESO' if okA else 'SPENTO'}")
print(f"  controllo B (claim nudi -> NON astensione)   : {'ACCESO' if okB else 'SPENTO'}")
if not (okA and okB):
    print("  => il criterio non separa: i numeri NON vanno usati")
    sys.exit(1)

a_ba = [r for r in bassi if astensione(r.get("claim"))]
a_am = [r for r in ammessi if astensione(r.get("claim"))]
a_tut = [r for r in veri if astensione(r.get("claim"))]
print(f"\n  ASTENSIONI fra i veri con score<5 : {len(a_ba)}/{len(bassi)}"
      f"  ({100*len(a_ba)/len(bassi):.1f}%)")
print(f"  ASTENSIONI fra i veri AMMESSI     : {len(a_am)}/{len(ammessi)}"
      f"  ({100*len(a_am)/len(ammessi):.1f}%)")
print(f"  ASTENSIONI su TUTTI i veri        : {len(a_tut)}/{len(veri)}"
      f"  ({100*len(a_tut)/len(veri):.1f}%)")
if a_tut:
    persi = sum(1 for r in a_tut if r["score"] < 40)
    print(f"\n  E il numero che conta: delle {len(a_tut)} astensioni VERE,"
          f" il moat ne perde {persi} ({100*persi/len(a_tut):.1f}%)")
    non_ast = [r for r in veri if not astensione(r.get("claim"))]
    persi_na = sum(1 for r in non_ast if r["score"] < 40)
    print(f"  contro {persi_na}/{len(non_ast)} ({100*persi_na/len(non_ast):.1f}%)"
          f" fra i veri che ASSERISCONO qualcosa")
print("\n  alcune astensioni perse:")
for r in sorted(a_ba, key=lambda r: r["score"])[:5]:
    print(f"    score={r['score']:5.1f}  {r['claim'][:70]}")
sys.exit(0)
