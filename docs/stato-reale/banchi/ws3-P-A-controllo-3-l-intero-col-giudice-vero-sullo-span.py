"""IL CONTROLLO DI P-A, terza gamba (GIUDICE VERO: slot, RAM sopra 6 GB letti):
dei 177 «veri composti che cambiano verdetto con l'innesto», 69 si fermavano
comunque per i layer deterministici con lo span come fonte (controlli 1 e 2).
Restano 108: 4 code che L1 ferma da sole (costo vero), 80 «crolli del giudice»
e 24 «review». Qui l'INTERO, non decomposto, viene giudicato dal giudice vero
con lo STESSO span come fonte: se anche l'intero cade sotto soglia (o nella banda
di review), il cambio di verdetto era lo span, non la decomposizione.

PREDIZIONI (depositate PRIMA di eseguire, 06/09 14:36, ora letta):
  P-K6  degli 80 crolli non ancora separati, l'intero con lo span cade sotto
        soglia in <= 15: P-D (identita' 120/120) dice che rigiudicare l'intero
        e' stabile, quindi il crollo e' del claim BREVE da solo (M5), non dello
        span;
  P-K7  dei 24 review, l'intero con lo span cade nella banda in <= 8;
  P-K8  quindi il costo VERO dell'innesto e' fra 85/800 = 10,6% e 108/800 =
        13,5%: la causa e' il giudice sui claim brevi, e la cura sta nel giudice
        (candidato di Nadia) o nel terzo stato, non nella decomposizione.
Argomento 1: il worktree da cui importare verimem (default: la radice del repo).
Costo: 104 coppie + warmup ~22 s; un solo processo; chiuso a fine banco.
"""
import json
import os
import pathlib
import sys
import time
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent
WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else QUI.parents[2]
sys.path.insert(0, str(WT))
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import verimem  # noqa: E402

print("IMPORT DA", verimem.__file__)
from verimem.grounding_gate import _ce_band_enforced  # noqa: E402
from verimem.local_grounding import get_local_judge, try_local_score  # noqa: E402

SOGLIA = 40.0
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))


def causa(d: dict) -> str:
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
    return "altro"


t0 = time.perf_counter()
get_local_judge()._ensure_scorer()
print(f"warmup: {time.perf_counter() - t0:.1f} s · banda CE: {'ON' if _ce_band_enforced() else 'OFF'}")
soglia = float(get_local_judge().threshold)
print(f"soglia del giudice: {soglia}")

# i 69 gia' separati dai controlli 1 e 2 non si rigiudicano: qui contano gli altri
# (80 crolli, 24 review, 4 L1 vere). Gli id dei 69 stanno nell'output dei due
# controlli; per non dipendere da quell'output si rigiudica tutto e si riporta per causa.
sotto = Counter()
tot = Counter()
righe = []
for d in det:
    c = causa(d)
    tot[c] += 1
    r = try_local_score(d["span"] or "", d["prop"])
    g = None if r is None else float(r[0])
    cade = g is not None and g < soglia
    sotto[c] += cade
    righe.append((c, d["id"][:12], d["g_prima"], g, cade))
print(f"\n{len(det)} interi rigiudicati con lo span come fonte (giudice vero)")
for c, n in tot.most_common():
    print(f"  {c:16s} intero sotto soglia {sotto[c]:3d}/{n}")
print(f"\nP-K6: crolli con l'intero sotto soglia {sotto['crollo giudice']}/{tot['crollo giudice']} "
      f"(fra questi 16 erano gia' separati da L4.1/L4.2) -> {'REGGE' if sotto['crollo giudice'] <= 15 + 16 else 'FALSIFICATA'}")
print("dettaglio (causa, id, g_prima, intero-con-span):")
for c, fid, gp, g, cade in righe:
    if c in ("crollo giudice", "review"):
        print(f"  {c:14s} {fid} g_prima {gp!s:.6} -> {g!s:.6} {'SOTTO' if cade else ''}")
