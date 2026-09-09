"""`skill_exposure_audit.py` (5) e `skill_emergence_detector.py` (5).

⚠️ La prima domanda nasce da un sospetto preciso: il docstring di
`_embeddings_for_ids` dice «(k, **384**) float32», la stessa dimensione legacy
che in `mesh_memory` fa restituire zero righe su ogni store attuale (T-MAP-9,
misurato: lo store scrive 768). Se il rilevatore di skill emergenti ha lo stesso
numero cablato, la stessa forma colpisce due moduli.

Si misura leggendo cosa torna su embedding VERI, non contando le occorrenze
di «384» nel sorgente.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-skm-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import numpy as np  # noqa: E402

from verimem import Memory  # noqa: E402
from verimem import skill_emergence_detector as SE  # noqa: E402
from verimem import skill_exposure_audit as SX  # noqa: E402

m = Memory(str(tmp / "s.db"))
FATTI = [
    ("Il canone del capannone 12 e' 5900 euro.", "affitti/canoni"),
    ("Il canone del capannone 7 e' 4200 euro.", "affitti/canoni"),
    ("Il canone del capannone 3 e' 3100 euro.", "affitti/canoni"),
    ("La consegna del capannone 12 e' il 3 marzo.", "affitti/consegne"),
    ("La consegna del capannone 7 e' il 9 aprile.", "affitti/consegne"),
    ("Il contratto di manutenzione costa 800 euro l'anno.", "servizi/manutenzione"),
    ("La manutenzione degli impianti e' trimestrale.", "servizi/manutenzione"),
    ("Il portiere lavora dal lunedi al venerdi.", "servizi/portineria"),
]
ids = []
for testo, topic in FATTI:
    r = m.add(testo, source=testo, topic=topic)
    if r.get("id"):
        ids.append(r["id"])
print("scritti", len(ids), "fatti in", len({t for _, t in FATTI}), "topic")

print("\n=== IL SOSPETTO: _embeddings_for_ids dice «(k, 384)». Cosa torna davvero?")
embs = SE._embeddings_for_ids(str(m.semantic.db_path), ids[:3])
print("  _embeddings_for_ids(3 id) ->",
      "None" if embs is None else f"array {embs.shape} dtype {embs.dtype}")
if embs is None:
    print("  >>> None: o le righe mancano, o la forma non e' quella attesa")
else:
    print("  >>> la dimensione vera e':", embs.shape[1],
          "· il docstring dice 384 ·", "COINCIDONO" if embs.shape[1] == 384
          else "NON COINCIDONO (docstring superato, ma i dati passano)")
print("  con un id inesistente:",
      SE._embeddings_for_ids(str(m.semantic.db_path), ["0" * 12]))

print("\n=== _topic_for_ids / _cohesion_score / _suggest_skill_name")
print("  _topic_for_ids(3 id dello stesso topic):",
      SE._topic_for_ids(str(m.semantic.db_path), ids[:3]))
if embs is not None:
    print("  _cohesion_score(3 fatti dello stesso tema):",
          round(float(SE._cohesion_score(embs)), 4))
    misti = SE._embeddings_for_ids(str(m.semantic.db_path), [ids[0], ids[5], ids[7]])
    if misti is not None:
        print("  _cohesion_score(3 fatti di temi DIVERSI):",
              round(float(SE._cohesion_score(misti)), 4))
        print("  >>> il gruppo coeso ha punteggio piu' alto:",
              float(SE._cohesion_score(embs)) > float(SE._cohesion_score(misti)))
print("  _suggest_skill_name({'affitti/canoni': 3, 'servizi/manutenzione': 1}):",
      SE._suggest_skill_name({"affitti/canoni": 3, "servizi/manutenzione": 1}))
print("  _suggest_skill_name({}):", repr(SE._suggest_skill_name({})))

print("\n=== detect_emerging_skills sul database vero")
try:
    out = SE.detect_emerging_skills(str(m.semantic.db_path), min_community_size=2,
                                    min_topic_purity=0.5, min_cohesion=0.1, max_n=5)
    print("  ->", str(out)[:300])
except Exception as e:  # noqa: BLE001
    print("  ->", type(e).__name__, str(e)[:150])

print("\n" + "=" * 74)
print("skill_exposure_audit.py")
print("=" * 74)
a = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
b = np.array([[1.0, 0.0], [0.7071, 0.7071]], dtype=np.float32)
print("_cosine_matrix(2x2, 2x2):", SX._cosine_matrix(a, b).round(4).tolist())

candidati = [
    # c1: VISTA (somiglia agli episodi) ma senza prove
    {"id": "c1", "name": "canoni", "trials": 0, "age_days": 40,
     "embedding": np.array([1.0, 0.0], dtype=np.float32)},
    # c2: INVISIBILE ma con 3 prove -> non deve essere ritirata
    {"id": "c2", "name": "portineria", "trials": 3, "age_days": 40,
     "embedding": np.array([0.0, 1.0], dtype=np.float32)},
    # c3: INVISIBILE, zero prove, vecchia -> e' la «morta alla nascita»,
    #     il controllo positivo che deve accendersi
    {"id": "c3", "name": "mai vista", "trials": 0, "age_days": 40,
     "embedding": np.array([0.0, -1.0], dtype=np.float32)},
]
episodi = [{"id": "e1", "embedding": np.array([1.0, 0.0], dtype=np.float32)},
           {"id": "e2", "embedding": np.array([0.99, 0.14], dtype=np.float32)}]
try:
    res = SX.audit_candidate_exposure(candidates=candidati, episodes=episodi, top_k=1)
    print("audit_candidate_exposure:", str(res)[:260])
    print("  CandidateExposure (campi):",
          sorted(vars(res["exposures"][0])) if isinstance(res, dict)
          and res.get("exposures") and hasattr(res["exposures"][0], "__dict__") else "-")
    morte = SX.select_invisible_for_retire(audit_result=res, min_age_days=30,
                                           require_zero_trials=True)
    print("select_invisible_for_retire (eta' >= 30, zero prove):", str(morte)[:200])
    morte2 = SX.select_invisible_for_retire(audit_result=res, min_age_days=999,
                                            require_zero_trials=True)
    print("  con min_age_days=999 (nessuna abbastanza vecchia):", str(morte2)[:120])
except Exception as e:  # noqa: BLE001
    print("audit_candidate_exposure ->", type(e).__name__, str(e)[:160])

print("\nload_audit_inputs_from_agent (serve un agente vivo):")
try:
    print(" ", str(SX.load_audit_inputs_from_agent(agent=None, recent_n=5))[:160])
except Exception as e:  # noqa: BLE001
    print(" ", type(e).__name__, str(e)[:140])
