"""Tre dubbi del giro precedente, ognuno col controllo che lo decide.

1. `_copula_parse` su una frase NEGATIVA: nel giro precedente
   «Questa non e' una copula…» è tornata `('questa non', …)` — la negazione
   finita DENTRO il soggetto. Se succede su una frase realistica, allora
   `subject_key` vede due soggetti diversi («il capannone 12» e «il capannone
   12 non») e due fatti che si contraddicono NON si incontrano mai.
2. `_is_call_telemetry_episode` ha detto False anche sul caso che dovrebbe
   riconoscere: prima di chiamarlo difetto leggo cosa cerca davvero.
3. `cluster_by_sr_similarity` ha dato lo stesso cluster unico con soglia 0,9 e
   0,1: o la soglia non morde, o quelle quattro skill sono davvero tutte
   simili. Il controllo è un caso con DUE gruppi separati per costruzione.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
from verimem import briefing as BR  # noqa: E402
from verimem import composer as CO  # noqa: E402
from verimem import successor_repr as SR  # noqa: E402

print("=== 1. la NEGAZIONE dentro il soggetto")
for t in ("Il capannone 12 e' in via Roma.",
          "Il capannone 12 non e' in via Roma.",
          "Rex is a labrador.",
          "Rex is not a labrador."):
    p = CO._copula_parse(t)
    print(f"  {t!r:38} -> {p}")
    if p:
        print(f"       subject_key -> {CO.subject_key(p[0])!r}")
print("  >>> due fatti opposti hanno lo STESSO soggetto?",
      CO.subject_key((CO._copula_parse("Rex is a labrador.") or ('',))[0])
      == CO.subject_key((CO._copula_parse("Rex is not a labrador.") or ('',))[0]))

print("\n=== 2. che cosa cerca davvero _is_call_telemetry_episode")
print(inspect.getsource(BR._is_call_telemetry_episode))


class _Ep:
    def __init__(self, t):
        self.task_text = t


for testo in ("cross-LLM call to gemini: ok", "ask_gemini", "[call] ask_claude",
              "ask_agy(prompt=...)", "ho scritto la mappa"):
    print(f"  {testo!r:34} -> {BR._is_call_telemetry_episode(_Ep(testo))}")

print("\n=== 3. la soglia del clustering morde?")
# due gruppi per costruzione: (a,b) si susseguono fra loro, (x,y) fra loro,
# e i due mondi non si toccano mai.
EP = [["a", "b", "a", "b"], ["b", "a", "b", "a"], ["x", "y", "x", "y"], ["y", "x", "y", "x"]]
ids, M = SR.build_successor_matrix(EP, gamma=0.9)
print("  ids:", ids)
for soglia in (0.99, 0.9, 0.5, 0.1, 0.0):
    print(f"  soglia {soglia:>4} -> {SR.cluster_by_sr_similarity(ids, M, threshold=soglia)}")

print("\n=== e la firma di forward_plan: `goal` è annotato come richiamabile?")
print(" ", inspect.signature(SR.forward_plan))
