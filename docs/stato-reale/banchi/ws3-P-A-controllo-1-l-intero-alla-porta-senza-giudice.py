"""IL CONTROLLO CHE MANCAVA A P-A: i 177 «veri composti ammessi che cambiano
verdetto con l'innesto» sono stati misurati alla porta con lo SPAN del giudice
come fonte (la fonte intera non e' conservata: muro M6), mentre il verdetto di
partenza (g_prima) veniva dalla scrittura originale con la fonte intera. Due
variabili in una: la fonte E la decomposizione. Qui l'INTERO, non decomposto,
passa dalla porta di main (nessun innesto) con lo stesso span come fonte e SENZA
giudice: cio' che si ferma qui si sarebbe fermato comunque — e' un artefatto
dello span, non un costo dell'innesto.

PREDIZIONI (depositate prima di eseguire, 06/09 14:28):
  P-K1  dei 39 record con L4.1 (senza L1), >= 35 si fermano anche sull'intero;
  P-K2  dei 34 «L1 coda nuda», 0 si fermano sull'intero (L1 non guarda la fonte:
        quel costo e' vero);
  P-K3  degli 11 «L4.2», >= 6 si fermano anche sull'intero.
Argomento 1: il worktree da cui importare verimem (deve essere SENZA innesto).
"""
import json
import pathlib
import sys
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent  # docs/stato-reale/banchi
WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else QUI.parents[2]  # la radice del repo: oggi senza innesto
sys.path.insert(0, str(WT))
import verimem  # noqa: E402

print("IMPORT DA", verimem.__file__)
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

SOGLIA = 40.0
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))


def causa(d: dict) -> str:  # la stessa del banco dei claim corti
    ly = set(d["layers"])
    cv = d["claims_verdict"]
    crollo = any((v or {}).get("score") is not None and float(v["score"]) < SOGLIA for v in cv)
    if any(w.startswith("L1") for w in ly):
        return "L1 coda nuda"
    if "L4-grounding" in ly and crollo:
        return "crollo giudice"
    if "L4.1" in ly:
        return "L4.1"
    if "L4-review" in ly:
        return "review"
    if "L4.2" in ly:
        return "L4.2"
    return "altro:" + ",".join(sorted(ly))


per_causa = Counter()
fermati_per_causa = Counter()
layer_intero = Counter()
esempi = {}
for d in det:
    c = causa(d)
    per_causa[c] += 1
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=False, verified_by=None, topic=None,
                            agent=None)
    layers = sorted({w.get("layer", "") for w in (r.warnings or [])})
    fermato = r.action != "persist"
    if fermato:
        fermati_per_causa[c] += 1
        for ly in layers:
            layer_intero[(c, ly)] += 1
        esempi.setdefault(c, []).append((d["id"][:12], layers, d["prop"][:80]))

print(f"\n{len(det)} record. Per causa (del banco): fermati ANCHE sull'intero, alla porta di main, span come fonte, senza giudice")
for c, n in per_causa.most_common():
    print(f"  {c:16s} {fermati_per_causa[c]:3d}/{n}")
print("\nlayer che fermano l'intero, per causa:")
for (c, ly), n in sorted(layer_intero.items()):
    print(f"  {c:16s} {ly:22s} {n}")
print("\nesempi (3 per causa):")
for c, ee in esempi.items():
    for e in ee[:3]:
        print(f"  {c:16s} {e[0]} {e[1]} «{e[2]}»")
n39 = sum(1 for d in det if "L4.1" in d["layers"] and not any(w.startswith("L1") for w in d["layers"]))
f39 = sum(1 for d in det if "L4.1" in d["layers"] and not any(w.startswith("L1") for w in d["layers"])
          and run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                                  ground_write=False, verified_by=None, topic=None,
                                  agent=None).action != "persist")
print(f"\nP-K1: dei {n39} con L4.1 (senza L1) fermati sull'intero {f39} -> {'REGGE' if f39 >= 35 else 'FALSIFICATA'}")
print(f"P-K2: L1 coda nuda fermati sull'intero {fermati_per_causa['L1 coda nuda']}/{per_causa['L1 coda nuda']} -> "
      f"{'REGGE' if fermati_per_causa['L1 coda nuda'] == 0 else 'FALSIFICATA'}")
print(f"P-K3: L4.2 fermati sull'intero {fermati_per_causa['L4.2']}/{per_causa['L4.2']} -> "
      f"{'REGGE' if fermati_per_causa['L4.2'] >= 6 else 'FALSIFICATA'}")
tot_art = sum(fermati_per_causa.values())
print(f"\nARTEFATTO DELLO SPAN: {tot_art}/177 si fermavano comunque; il costo dell'innesto misurabile senza giudice scende "
      f"da 177/800 = 22,1% a {177 - tot_art}/800 = {100 * (177 - tot_art) / 800:.1f}% (i crolli del giudice restano da rimisurare col giudice)")
