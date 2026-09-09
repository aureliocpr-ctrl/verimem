"""Quattro moduli della mia parte, esercitati funzione per funzione:
`successor_repr.py` (7), `composer.py` (8), `briefing.py` (3), `mesh_memory.py` (8).

Le firme sono state lette prima (`firme.py`), non indovinate. Dove una funzione
ha un'infrastruttura sotto (il bus dei vettori, un agente vivo) lo dico e scrivo
NON MISURATO col motivo, invece di chiamarla a caso e chiamare «difetto» il mio
TypeError.

Ogni prova ha il caso che deve accendersi accanto a quello che deve spegnersi.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-4mod-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)

print("=" * 74)
print("A. successor_repr.py — la matrice del successore sulle sequenze di skill")
print("=" * 74)
from verimem import successor_repr as SR  # noqa: E402

EPISODI = [["a", "b", "c"], ["a", "b", "d"], ["a", "c", "d"], ["b", "c"]]
ids = SR._collect_skills(EPISODI)
print("_collect_skills:", ids, "| ordinato e stabile:", ids == sorted(ids))
# le tre costruttrici tornano (ids, matrice), non la sola matrice: firma LETTA
ids_p, P = SR.build_transition_matrix(EPISODI)
print("build_transition_matrix: forma", P.shape, "| riga di 'a':",
      [round(float(x), 3) for x in P[ids_p.index("a")]],
      "| somma", round(float(P[ids_p.index("a")].sum()), 6))
ids_m, M = SR.build_successor_matrix(EPISODI, gamma=0.9)
print("build_successor_matrix: riga di 'a':",
      [round(float(x), 3) for x in M[ids_m.index("a")]])
print("predict_next('a'):", SR.predict_next("a", ids_p, P, top_k=3))
print("predict_next(skill ignota):", SR.predict_next("zzz", ids_p, P, top_k=3))
ids2, M2 = SR.update_from_sequence(M.copy(), ids_m, ["a", "b", "c"], alpha=0.5)
diverso = bool((abs(M2 - M) > 1e-9).any())
print("update_from_sequence: la matrice CAMBIA:", diverso)
# `goal` è un PREDICATO, non il nome di una skill: `goal="d"` solleva
# «'str' object is not callable». Il docstring lo chiama «goal» e basta.
print("forward_plan senza goal:",
      SR.forward_plan("a", ids_p, P, depth=3, beam_width=2))
print("forward_plan con goal predicato ('d' nel cammino):",
      SR.forward_plan("a", ids_p, P, depth=3, beam_width=2,
                      goal=lambda path: "d" in path))
try:
    SR.forward_plan("a", ids_p, P, depth=2, beam_width=2, goal="d")
except Exception as e:  # noqa: BLE001
    print("forward_plan(goal='d') ->", type(e).__name__, str(e)[:70])
print("cluster_by_sr_similarity(0.9):", SR.cluster_by_sr_similarity(ids_m, M, threshold=0.9))
print("cluster_by_sr_similarity(0.1):", SR.cluster_by_sr_similarity(ids_m, M, threshold=0.1))

print("\n" + "=" * 74)
print("B. composer.py — «lo stesso soggetto», una definizione sola per tutti")
print("=" * 74)
from verimem import composer as CO  # noqa: E402

print("_min_score():", CO._min_score())
for s in ("Il canone del capannone", "il  Canone   del capannone", "L'aula magna",
          "The dog", "a dog"):
    print(f"  subject_key({s!r:32}) -> {CO.subject_key(s)!r}")
print("normalizza_apostrofi(tre varianti):",
      [CO.normalizza_apostrofi(x) for x in ("l’aula", "lʼaula", "l'aula")])
for t in ("Rex is a labrador.", "Il canone e' 5900 euro.",
          "Rex e' nel capannone.", "Questa non e' una copula perche' manca il verbo"):
    print(f"  _copula_parse({t!r:48}) -> {CO._copula_parse(t)}")
print("_strip_article('the dog','en'):", CO._strip_article("the dog", "en"),
      "| ('il cane','it'):", CO._strip_article("il cane", "it"),
      "| ('a dog','it') [articolo di ALTRA lingua]:", CO._strip_article("a dog", "it"))
print("_apre_un_locativo('nel','it'):", CO._apre_un_locativo("nel", "it"),
      "| ('Nelson','it'):", CO._apre_un_locativo("Nelson", "it"),
      "| ('nelle','it'):", CO._apre_un_locativo("nelle", "it"))

print("\n  compose_once su uno store vero:")
from verimem import Memory  # noqa: E402

m = Memory(str(tmp / "c.db"))
F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
m.add("Il canone del capannone 12 e' 5900 euro.", source=F, topic="co/x")
m.add("Il capannone 12 e' in via Roma.", source="Il capannone 12 e' in via Roma.",
      topic="co/x")
print("   ", CO.compose_once(m, topic="co/x", run_id="ws3-mappa"))

print("\n" + "=" * 74)
print("C. briefing.py — il riassunto di sessione dai tre livelli di memoria")
print("=" * 74)
from verimem import briefing as BR  # noqa: E402


class _FintoEp:
    def __init__(self, testo):
        self.task_text = testo


print("_is_call_telemetry_episode('cross-LLM call ...'):",
      BR._is_call_telemetry_episode(_FintoEp("cross-LLM call to gemini: ok")))
print("_is_call_telemetry_episode('ho scritto la mappa'):",
      BR._is_call_telemetry_episode(_FintoEp("ho scritto la mappa di client.py")))


class _SenzaCount:
    pass


class _ConCount:
    def count(self):
        return 7


print("_safe_count(oggetto con count):", BR._safe_count(_ConCount(), "count"),
      "| senza count:", BR._safe_count(_SenzaCount(), "count"),
      "(None = il livello non sa rispondere, NON un numero)")
try:
    b = BR.get_briefing(agent=None, n_facts=2)
    print("get_briefing(agent=None) ->", str(b)[:120])
except Exception as e:  # noqa: BLE001
    print("get_briefing(agent=None) ->", type(e).__name__, str(e)[:110])

print("\n" + "=" * 74)
print("D. mesh_memory.py — la memoria condivisa fra istanze")
print("=" * 74)
import numpy as np  # noqa: E402

from verimem import mesh_memory as ME  # noqa: E402

a = np.zeros(384, dtype=np.float32)
a[0] = 1.0
b = np.zeros(384, dtype=np.float32)
b[0] = 1.0
c = np.zeros(384, dtype=np.float32)
c[1] = 1.0
print("_cosine(uguali):", ME._cosine(a.tobytes(), b.tobytes()),
      "| _cosine(ortogonali):", ME._cosine(a.tobytes(), c.tobytes()))
try:
    r = ME.local_topk_embeddings(str(m.semantic.db_path), a.tobytes(), 3)
    print("local_topk_embeddings: righe", len(r),
          "| la prima porta (id, embedding, score):",
          [type(x).__name__ for x in r[0]] if r else "vuoto")
except Exception as e:  # noqa: BLE001
    print("local_topk_embeddings ->", type(e).__name__, str(e)[:110])
try:
    print("_vec_bus():", ME._vec_bus().__name__)
except Exception as e:  # noqa: BLE001
    print("_vec_bus() ->", type(e).__name__, str(e)[:110])
