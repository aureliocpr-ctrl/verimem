"""IL CONTROLLO DI P-A, seconda gamba: L4.1/L4.2 girano SOLO se un giudice c'e'
(anti_confab_gate: `if source and _ground_on and _have_judge`), quindi il
controllo senza giudice (controllo 1) ha misurato solo L1. Qui il
giudice e' FINTO e dice 95 a ogni coppia (nessun modello caricato, RAM zero): il
moat passa tutto e restano solo i layer deterministici. L'INTERO, non decomposto,
alla porta di main (5e61d333, nessun innesto) con lo SPAN come fonte: cio' che si
ferma qui si fermava comunque — artefatto dello span, non costo dell'innesto.

PREDIZIONI (depositate prima di eseguire, 06/09 14:32):
  P-K1'  dei 23 record «L4.1» (causa del banco), >= 20 si fermano anche
         sull'intero (valori_non_nella_fonte(intero, span) e' non vuoto in 39/39);
  P-K4   dei 96 «crollo giudice», quelli che si fermano sull'intero per L4.1/L4.2
         sono >= 10 (il crollo copriva un L4.1 sottostante);
  P-K5   dei 24 «review», 0 si fermano (la banda CE e' spenta qui).
Argomento 1: il worktree SENZA innesto da cui importare verimem.
"""
import json
import os
import pathlib
import sys
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent  # docs/stato-reale/banchi
WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else QUI.parents[2]  # la radice del repo: oggi senza innesto
sys.path.insert(0, str(WT))
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ.pop("ENGRAM_GROUNDING_WRITE_THRESHOLD", None)
import verimem  # noqa: E402

print("IMPORT DA", verimem.__file__)
import verimem.grounding_gate as gg  # noqa: E402
import verimem.local_grounding as lg  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

gg._ce_band_enforced = lambda: False


class _GiudiceCheDiceSempreSi(lg.LocalGroundingJudge):
    def __init__(self) -> None:
        super().__init__()
        self.coppie = 0
        self._scorer = self._finto

    @property
    def threshold(self) -> float:
        return 40.0

    def _finto(self, batch):  # noqa: ANN001
        self.coppie += len(batch)
        return [95.0 for _ in batch]

    def _entro_la_finestra(self, span: str) -> str:
        return span


giudice = _GiudiceCheDiceSempreSi()
lg.set_local_judge(giudice)

SOGLIA = 40.0
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))


def causa(d: dict) -> str:  # la stessa del banco dei claim corti (L4.3 compreso)
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
    if "L4.3" in ly:
        return "L4.3"
    return "altro:" + ",".join(sorted(ly))


per_causa = Counter()
fermati = Counter()
layer_intero = Counter()
esempi: dict[str, list] = {}
for d in det:
    c = causa(d)
    per_causa[c] += 1
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=True, verified_by=None, topic=None, agent=None)
    layers = sorted({w.get("layer", "") for w in (r.warnings or [])})
    if r.action != "persist":
        fermati[c] += 1
        for ly in layers:
            layer_intero[(c, ly)] += 1
        esempi.setdefault(c, []).append((d["id"][:12], layers, r.action, d["prop"][:70]))

print(f"\ngiudice finto: {giudice.coppie} coppie viste, tutte a 95 (il moat non ferma niente)")
print(f"{len(det)} record. Per causa del banco: fermati ANCHE sull'intero (porta di main, span come fonte, giudice a 95)")
for c, n in per_causa.most_common():
    print(f"  {c:16s} {fermati[c]:3d}/{n}")
print("\nlayer che fermano l'intero, per causa:")
for (c, ly), n in sorted(layer_intero.items()):
    print(f"  {c:16s} {ly:22s} {n}")
print("\nesempi (2 per causa):")
for c, ee in esempi.items():
    for e in ee[:2]:
        print(f"  {c:16s} {e[0]} {e[1]} {e[2]} «{e[3]}»")
print(f"\nP-K1': L4.1 fermati sull'intero {fermati['L4.1']}/{per_causa['L4.1']} -> "
      f"{'REGGE' if fermati['L4.1'] >= 20 else 'FALSIFICATA'}")
print(f"P-K4 : crollo giudice fermati sull'intero {fermati['crollo giudice']}/{per_causa['crollo giudice']} -> "
      f"{'REGGE' if fermati['crollo giudice'] >= 10 else 'FALSIFICATA'}")
print(f"P-K5 : review fermati sull'intero {fermati['review']}/{per_causa['review']} -> "
      f"{'REGGE' if fermati['review'] == 0 else 'FALSIFICATA'}")
tot = sum(fermati.values())
print(f"\nARTEFATTO DELLO SPAN (L1 + L4.1 + L4.2 + L4.3, giudice escluso): {tot}/177 si fermavano comunque; "
      f"il costo residuo dell'innesto e' al massimo {177 - tot}/800 = {100 * (177 - tot) / 800:.1f}% "
      f"(i crolli del giudice non fermati qui restano da rimisurare col giudice vero sull'intero con lo span)")
try:
    import psutil
    print(f"RSS di questo processo: {psutil.Process().memory_info().rss / 2**20:.0f} MB")
except ImportError:
    pass
