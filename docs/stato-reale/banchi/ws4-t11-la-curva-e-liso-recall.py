"""T1.1 — la CURVA, che e' il confronto leale. Offline sui punteggi gia' salvati.

A soglia fissa 0,5 FactCG dava «veri persi 1,3%, falsi fermati 15,7%»: non e'
migliore del nostro moat, e' TARATO DIVERSAMENTE. Un confronto a soglia fissa fra
due modelli con calibrazioni diverse non dice niente.

IL NUMERO CHE DECIDE (chiesto da @lead-audit): A PARI VERI PERSI del nostro gate
(29,3% su TruthfulQA), quanti falsi ferma FactCG? Piu' l'AUROC, che non dipende
da nessuna soglia.

PREDIZIONE DEPOSITATA PRIMA (canale f6e42cbc, 02/09 20:22):
  · TruthfulQA a pari 29,3% di veri persi: FactCG ferma FRA 75% e 90% dei falsi
    (il nostro: 86,7%) => CIRCA UGUALE
  · AUROC fra 0,80 e 0,92
  · FALSIFICATA se fuori da 70-92%.

E IL CONTROLLO CHE SEPARA DUE SPIEGAZIONI DIVERSE: la mia teoria e' «le
astensioni non sono entailed per NESSUN modello NLI». Se FactCG le AMMETTE, la
teoria e' sbagliata; se le boccia come il nostro ma boccia poco tutto il resto,
la teoria regge e il modello e' solo permissivo. Si guarda dove cadono le 57
astensioni nella scala di FactCG.
"""
import io
import json
import re
import sys

FACT = "_ws4_factcg_heldout.jsonl"
DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
IDX = 1  # SUPPORTED, determinato dai dati: media 0,750 sui veri contro 0,647 sui falsi

AST = re.compile(
    r"^\s*(i have no comment|there (is|are|was|were) (no|not)\b"
    r"|it (is|was) (not|un)|no(thing| one| such)\b|nobody\b|none of\b"
    r"|not (necessarily|really|much)\b|(this|that|it) (is|was) a myth\b"
    r"|unknown\b|it depends\b|we don't know\b)", re.I)
MITO = re.compile(r"\b(is|are) a myth\b|\bmisconception\b|\bnot true\b", re.I)


def astensione(c):
    c = (c or "").strip()
    return bool(AST.match(c) or MITO.search(c))


f = {json.loads(x)["i"]: json.loads(x) for x in io.open(FACT, encoding="utf-8") if x.strip()}
dati = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
for i, r in enumerate(dati, 1):
    r["i"] = i
    r["p"] = f.get(i, {}).get("p", [0.5, 0.5])[IDX]

veri = [r for r in dati if r["label"] == 1]
falsi = [r for r in dati if r["label"] == 0]
print(f"  veri {len(veri)}  falsi {len(falsi)}  (punteggio = indice {IDX})")

# ── AUROC, senza soglie ───────────────────────────────────────────────────
coppie = sum(1 for v in veri for fa in falsi
             if v["p"] > fa["p"]) + 0.5 * sum(1 for v in veri for fa in falsi
                                              if v["p"] == fa["p"])
auroc = coppie / (len(veri) * len(falsi))
print(f"\n  AUROC FactCG (nessuna soglia): {auroc:.3f}")

# ── LA CURVA ──────────────────────────────────────────────────────────────
print(f"\n  {'soglia':>7}  {'veri persi':>12}  {'falsi fermati':>14}")
for s10 in range(5, 96, 5):
    s = s10 / 100.0
    vp = sum(1 for r in veri if r["p"] < s)
    ff = sum(1 for r in falsi if r["p"] < s)
    print(f"  {s:>7.2f}  {vp:>4}/300 {100*vp/300:>5.1f}%  {ff:>4}/300 {100*ff/300:>5.1f}%")

# ── IL NUMERO CHE DECIDE: a PARI veri persi ───────────────────────────────
BERSAGLIO = 88  # i veri persi del nostro gate su TruthfulQA
ordinati = sorted(veri, key=lambda r: r["p"])
soglia_iso = ordinati[BERSAGLIO - 1]["p"] + 1e-9
ff_iso = sum(1 for r in falsi if r["p"] < soglia_iso)
vp_iso = sum(1 for r in veri if r["p"] < soglia_iso)
print(f"\n  == ISO-RECALL: a PARI veri persi del nostro gate ==")
print(f"    soglia che perde {vp_iso} veri (bersaglio {BERSAGLIO}): {soglia_iso:.4f}")
print(f"    FactCG ferma  {ff_iso}/300 = {100*ff_iso/300:.1f}% dei falsi")
print(f"    il nostro moat        260/300 = 86,7%")
print(f"    => differenza {100*ff_iso/300 - 86.7:+.1f} punti")
pf = 100 * ff_iso / 300
print(f"\n  PREDIZIONE MIA (75-90%): {'REGGE' if 75 <= pf <= 90 else 'FALSIFICATA'}"
      f"  ·  AUROC 0,80-0,92: {'REGGE' if 0.80 <= auroc <= 0.92 else 'FALSIFICATA'}")

# ── IL CONTROLLO CHE SEPARA LE DUE SPIEGAZIONI ────────────────────────────
ast = [r for r in veri if astensione(r.get("claim"))]
non_ast = [r for r in veri if not astensione(r.get("claim"))]
m_ast = sum(r["p"] for r in ast) / len(ast) if ast else 0
m_non = sum(r["p"] for r in non_ast) / len(non_ast) if non_ast else 0
print(f"\n  == LE ASTENSIONI SECONDO FACTCG ==")
print(f"    punteggio medio: astensioni {m_ast:.3f} · altri veri {m_non:.3f}")
persi_ast = sum(1 for r in ast if r["p"] < soglia_iso)
persi_non = sum(1 for r in non_ast if r["p"] < soglia_iso)
print(f"    alla soglia iso-recall: astensioni perse {persi_ast}/{len(ast)}"
      f" ({100*persi_ast/len(ast):.1f}%) · altri {persi_non}/{len(non_ast)}"
      f" ({100*persi_non/len(non_ast):.1f}%)")
print(f"    [il nostro moat: 29/57 = 50,9% contro 44/243 = 18,1%]")
if persi_ast / len(ast) > persi_non / len(non_ast) * 1.5:
    print("    => ANCHE FactCG penalizza le astensioni: la teoria REGGE,")
    print("       il modello e' solo tarato piu' permissivo")
else:
    print("    => FactCG NON penalizza le astensioni: la mia teoria e' SBAGLIATA")
sys.exit(0)
