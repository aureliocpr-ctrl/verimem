"""Le 47 quarantene di P-T2 sul tip: quante sono del MOAT (il terzo stato non
scatta) e quante dei layer DETERMINISTICI (L1, L4.1), che si fermerebbero
comunque. Giudice finto a 95 su ogni coppia: nessun modello, RAM ~40 MB — cio'
che si ferma qui e' deterministico per costruzione."""
import json
import os
import pathlib
import sys
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent  # docs/stato-reale/banchi
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else str(QUI.parents[2]))
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import verimem.local_grounding as lg  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402


class _Si(lg.LocalGroundingJudge):
    def __init__(self):
        super().__init__()
        self._scorer = lambda batch: [95.0 for _ in batch]

    @property
    def threshold(self):
        return 40.0

    def _entro_la_finestra(self, span):
        return span


lg.set_local_judge(_Si())
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))
conti = Counter()
per_layer = Counter()
for d in det:
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=True, verified_by=None, topic=None, agent=None)
    layers = sorted({str(w.get("layer")) for w in (r.warnings or [])})
    fermato = r.action != "persist"
    conti["fermato dai deterministici" if fermato else "passa (dipende dal giudice)"] += 1
    if fermato:
        for ly in layers:
            if ly.startswith("L1") or ly in ("L4.1", "L4.2", "L4.3"):
                per_layer[ly] += 1
print(f"177 record sul TIP col giudice finto a 95 (tutto cio' che si ferma e' deterministico): {dict(conti)}")
print("layer deterministici che fermano:", dict(per_layer.most_common()))
