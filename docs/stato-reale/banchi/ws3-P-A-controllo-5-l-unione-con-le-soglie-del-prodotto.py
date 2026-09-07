"""Ricalcolo dell'unione dei controlli di P-A con le SOGLIE DEL PRODOTTO, non con
il «threshold» di gate_config (99,64) usato per errore il 06/09 nei controlli 3
e 4: il prodotto ammette a >= tau_hi (80), tiene in review fra 40 e 80 (banda
ON), quarantina sotto 40. L'intero con lo span «cade» davvero solo se sta
sotto 40 (quarantena) — o sotto 80 se si conta la review come non-ammissione.
Rilegge l'output del controllo 3 (giudice vero) e rifà il controllo 2
(deterministico, giudice finto a 95, RAM zero) sull'albero di main."""
import json
import os
import pathlib
import re
import sys

QUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parents[2]))  # la radice del repo (main, senza innesto)
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
ids = [d["id"][:12] for d in det]

deterministici = set()
for d in det:
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=True, verified_by=None, topic=None, agent=None)
    if r.action != "persist":
        deterministici.add(d["id"][:12])

g_intero = {}
rx = re.compile(r"^\s+(crollo giudice|review)\s+([0-9a-f]{12}) g_prima (\S+) -> (\S+)")
for line in open(QUI / "ws3-P-A-controllo-3-output-14-48.txt", encoding="utf-8"):
    m = rx.match(line)
    if m:
        try:
            g_intero[m.group(2)] = float(m.group(4))
        except ValueError:
            pass

for nome, soglia in (("quarantena (< 40, il moat)", 40.0), ("non ammesso (< 80, tau_hi con la banda)", 80.0)):
    giudice = {i for i, g in g_intero.items() if g < soglia}
    unione = deterministici | giudice
    residuo = [i for i in ids if i not in unione]
    print(f"{nome}: intero con lo span sotto soglia col giudice vero {len(giudice)}/{len(g_intero)} · "
          f"deterministici {len(deterministici)} · unione {len(unione)} · RESIDUO {len(residuo)}/800 = {100 * len(residuo) / 800:.1f}%")
print("(il 06/09 con la soglia sbagliata 99,64: giudice 45, unione 105, residuo 72 = 9,0%)")
