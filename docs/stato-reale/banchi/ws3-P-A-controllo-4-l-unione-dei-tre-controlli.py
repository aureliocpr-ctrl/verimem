"""L'UNIONE dei tre controlli di P-A: per ciascuno dei 177, si fermava comunque
sull'intero con lo stesso span (deterministico: controllo 2 ricalcolato qui col
giudice finto a 95) OPPURE l'intero con lo span cade sotto la soglia del giudice
vero (controllo 3, letto dal suo output). Il residuo e' il costo VERO
dell'innesto. In piu': fra gli interi che oggi cadono, quanti avevano g_prima
sotto la soglia di oggi (99,64): sono una deriva di soglia/modello, non lo span."""
import json
import os
import pathlib
import re
import sys

QUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parents[2]))  # la radice del repo, senza innesto
os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
os.environ.pop("ENGRAM_GROUNDING_WRITE_THRESHOLD", None)
import verimem.grounding_gate as gg  # noqa: E402
import verimem.local_grounding as lg  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

gg._ce_band_enforced = lambda: False


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
SOGLIA_OGGI = 99.64130401611328

deterministici = set()
for d in det:
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=True, verified_by=None, topic=None, agent=None)
    if r.action != "persist":
        deterministici.add(d["id"][:12])

giudice = set()
deriva = 0
rx = re.compile(r"^\s+(crollo giudice|review)\s+([0-9a-f]{12}) g_prima (\S+) -> (\S+)\s*(SOTTO)?")
for line in open(QUI / "ws3-P-A-controllo-3-output-14-48.txt", encoding="utf-8"):
    m = rx.match(line)
    if m and m.group(5):
        giudice.add(m.group(2))
        try:
            if float(m.group(3)) < SOGLIA_OGGI:
                deriva += 1
        except ValueError:
            pass

ids = [d["id"][:12] for d in det]
unione = deterministici | giudice
residuo = [i for i in ids if i not in unione]
print(f"177 record · deterministici (controllo 2): {len(deterministici)} · intero sotto soglia col giudice (controllo 3, "
      f"crolli+review): {len(giudice)} · UNIONE: {len(unione)} · RESIDUO (costo dell'innesto): {len(residuo)}/800 = "
      f"{100 * len(residuo) / 800:.1f}%")
print(f"fra i {len(giudice)} interi che cadono col giudice, con g_prima gia' sotto la soglia di oggi ({SOGLIA_OGGI:.2f}): "
      f"{deriva} (deriva di soglia/modello, non span)")
from collections import Counter  # noqa: E402

cause = Counter()
for d in det:
    if d["id"][:12] in residuo:
        ly = set(d["layers"])
        cv = d["claims_verdict"]
        crollo = any((v or {}).get("score") is not None and float(v["score"]) < 40.0 for v in cv)
        c = ("L1" if any(w.startswith("L1") for w in ly) else "crollo giudice" if ("L4-grounding" in ly and crollo)
             else "L4.1" if "L4.1" in ly else "review" if "L4-review" in ly else "altro")
        cause[c] += 1
print("residuo per causa:", dict(cause))
print("NB: L1 (2) e L4.1 (3) sotto soglia col giudice non hanno gli id nell'output del controllo 3: il residuo puo' calare di al massimo 5.")
