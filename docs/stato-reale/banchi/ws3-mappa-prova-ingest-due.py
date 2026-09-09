"""Due cose lasciate aperte dal giro precedente.

1. **IL REPERTO**: `_grounds` ha AMMESSO (80,47) un fatto che il dialogo non
   dice — «il capannone 12 e' stato venduto nel 2019» — mentre respinge (0,72)
   lo stesso fatto col numero sbagliato. Un caso solo non è una misura: ne provo
   sei, tre che il dialogo DICE e tre inventati ma plausibili, e conto.
2. `ingest_conversation` è morta sulla firma del mio LLM finto
   (`complete() takes 1 positional argument but 3 were given`): il chiamante lo
   invoca con argomenti posizionali. Rifatto il finto e ripetuto.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-ing2-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402
from verimem import conversation_ingest as CI  # noqa: E402

DIALOGO = ("user: Quanto costa il capannone 12?\n"
           "assistant: Il canone del capannone 12 e' 5900 euro al mese, "
           "e la consegna e' prevista per il 3 marzo.")

DETTI = ["Il canone del capannone 12 e' 5900 euro.",
         "La consegna del capannone 12 e' prevista per il 3 marzo.",
         "Il capannone 12 ha un canone mensile."]
NON_DETTI = ["Il capannone 12 e' stato venduto nel 2019.",
             "Il capannone 12 ha una superficie di 400 metri quadri.",
             "Il proprietario del capannone 12 si chiama Mario Rossi."]
CONTRADDETTI = ["Il canone del capannone 12 e' 9999 euro.",
                "La consegna del capannone 12 e' prevista per il 9 aprile."]

print("soglia dell'ingest:", CI._ingest_ground_threshold())
print("\nfatti che il dialogo DICE (devono passare):")
p_detti = 0
for p in DETTI:
    ok, s = CI._grounds(DIALOGO, p)
    p_detti += ok
    print(f"  {p[:52]!r:56} ammesso={ok} punteggio={round(float(s), 2)}")
print("\nfatti INVENTATI ma plausibili, che il dialogo NON dice (devono cadere):")
p_inventati = 0
for p in NON_DETTI:
    ok, s = CI._grounds(DIALOGO, p)
    p_inventati += ok
    print(f"  {p[:52]!r:56} ammesso={ok} punteggio={round(float(s), 2)}")
print("\nfatti CONTRADDETTI dal dialogo (devono cadere):")
p_contr = 0
for p in CONTRADDETTI:
    ok, s = CI._grounds(DIALOGO, p)
    p_contr += ok
    print(f"  {p[:52]!r:56} ammesso={ok} punteggio={round(float(s), 2)}")

print(f"\n>>> detti ammessi      {p_detti}/{len(DETTI)}  (devono essere tutti)")
print(f">>> inventati ammessi  {p_inventati}/{len(NON_DETTI)}  (devono essere ZERO)")
print(f">>> contraddetti ammessi {p_contr}/{len(CONTRADDETTI)}  (devono essere ZERO)")


class _Risposta:
    def __init__(self, text):
        self.text = text


class _LLM:
    """Il chiamante invoca `complete` con argomenti POSIZIONALI: il finto deve
    accettarli, o si prende «takes 1 positional argument but 3 were given» e il
    banco misura il proprio errore invece del prodotto."""

    def __init__(self, righe):
        self.righe = righe
        self.chiamate = 0

    def complete(self, *a, **kw):
        self.chiamate += 1
        return _Risposta(self.righe)


print("\n=== ingest_conversation con l'LLM finto corretto")
m = Memory(str(tmp / "i.db"))
llm = _LLM("- Il canone del capannone 12 e' 5900 euro.\n"
           "- La consegna del capannone 12 e' prevista per il 3 marzo.\n"
           "- Il capannone 12 e' stato venduto nel 2019.\n")
res = CI.ingest_conversation(
    m.semantic,
    [{"role": "user", "content": "Quanto costa il capannone 12?"},
     {"role": "assistant", "content": "Il canone del capannone 12 e' 5900 euro al mese, "
                                      "e la consegna e' prevista per il 3 marzo."}],
    llm=llm, conversation_id="conv-1", topic="ing/x")
print("  ->", {k: str(v)[:100] for k, v in res.items()})
print("  chiamate all'llm:", llm.chiamate)
for fid in (res.get("fact_ids") or []):
    f = m.get(fid) or {}
    print(f"   {fid[:12]} · {f.get('status')} · {str(f.get('text'))[:60]}")

print("\n=== e con ground=False (il moat spento sull'ingest)")
m2 = Memory(str(tmp / "j.db"))
llm2 = _LLM("- Il capannone 12 e' stato venduto nel 2019.\n")
res2 = CI.ingest_conversation(
    m2.semantic,
    [{"role": "assistant", "content": "Il canone del capannone 12 e' 5900 euro."}],
    llm=llm2, conversation_id="conv-2", topic="ing/y", ground=False)
print("  ->", {k: str(v)[:80] for k, v in res2.items()})

print("\n=== gapfill_facts con l'LLM corretto")
llm3 = _LLM("- Il contratto scade nel 2027.\n")
print("  aggiunge cio' che manca:",
      CI.gapfill_facts("user: il contratto scade nel 2027",
                       ["Il canone e' 5900 euro."], llm=llm3),
      "· chiamate:", llm3.chiamate)
llm4 = _LLM("- Il canone e' 5900 euro.\n")
print("  consolidate_facts su due quasi-duplicati:",
      CI.consolidate_facts(["Il canone e' 5900 euro.", "Il canone e' di 5900 euro."],
                           llm=llm4), "· chiamate:", llm4.chiamate)
