"""I 96 «crolli del giudice sui claim brevi» di P-A, in un file per Nadia (ws4):
fatti VERI composti gia' ammessi (provenance), decomposti alla porta con lo span
come fonte; il claim «breve» e' un pezzo della scrittura col soggetto ereditato,
non un claim scritto a mano. Per ogni record: l'intero, lo span, g_prima (alla
scrittura, fonte intera), l'intero rigiudicato oggi con lo span (controllo 3),
se un layer deterministico lo fermerebbe comunque (controllo 2), i claim con il
punteggio del giudice, i caduti. Il sottoinsieme PULITO (53): l'intero passa
oggi con lo stesso span e nessun layer deterministico lo ferma — stesso testo,
stessa fonte, cade solo il pezzo."""
import json
import os
import pathlib
import re
import statistics
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
SOGLIA_CLAIM = 40.0
SOGLIA_OGGI = 99.64130401611328
det = json.load(open(QUI / "ws3-P-A-i-177-veri-composti-che-cambiano-verdetto.json", encoding="utf-8"))

intero_oggi = {}
rx = re.compile(r"^\s+(crollo giudice|review)\s+([0-9a-f]{12}) g_prima (\S+) -> (\S+)")
for line in open(QUI / "ws3-P-A-controllo-3-output-14-48.txt", encoding="utf-8"):
    m = rx.match(line)
    if m:
        try:
            intero_oggi[m.group(2)] = float(m.group(4))
        except ValueError:
            intero_oggi[m.group(2)] = None

out = []
for d in det:
    ly = set(d["layers"])
    cv = d["claims_verdict"]
    caduti = [(c, float(v["score"])) for c, v in zip(d["claims"], cv, strict=False)
              if (v or {}).get("score") is not None and float(v["score"]) < SOGLIA_CLAIM]
    if any(w.startswith("L1") for w in ly) or not ("L4-grounding" in ly and caduti):
        continue
    r = run_validation_gate(proposition=d["prop"], source=d["span"] or "", grounding_llm=None,
                            ground_write=True, verified_by=None, topic=None, agent=None)
    deterministico = r.action != "persist"
    g_oggi = intero_oggi.get(d["id"][:12])
    pulito = (not deterministico) and (g_oggi is not None and g_oggi >= SOGLIA_OGGI)
    out.append({
        "id": d["id"], "intero": d["prop"], "span": d["span"], "g_prima": d["g_prima"],
        "intero_con_span_oggi": g_oggi, "fermato_da_layer_deterministico": deterministico,
        "pulito": pulito,
        "claims": [{"claim": c, "score": (v or {}).get("score"), "via": (v or {}).get("via")}
                   for c, v in zip(d["claims"], cv, strict=False)],
        "caduti": [{"claim": c, "score": s} for c, s in caduti],
    })

dest = QUI / "ws3-i-96-crolli-del-giudice-sui-claim-brevi.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
puliti = [o for o in out if o["pulito"]]
parole_caduti = [len(c["claim"].split()) for o in out for c in o["caduti"]]
parole_interi = [len(o["intero"].split()) for o in out]
print(f"record: {len(out)} · puliti (intero passa oggi con lo span, nessun layer deterministico): {len(puliti)}")
print(f"parole nei claim CADUTI: min {min(parole_caduti)} · mediana {statistics.median(parole_caduti)} · max {max(parole_caduti)} · n {len(parole_caduti)}")
print(f"parole negli INTERI:     min {min(parole_interi)} · mediana {statistics.median(parole_interi)} · max {max(parole_interi)}")
print(f"claim caduti sotto le 8 parole: {sum(p < 8 for p in parole_caduti)}/{len(parole_caduti)}")
print("scritto:", dest.name)
