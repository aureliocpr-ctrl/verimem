"""La guardia di `trust_report.py:251` scatta con LazyLLM? A/B nello stesso processo.

Fino a ora avevo il pezzo LETTO, non misurato: dichiaravo «unreadable alla porta
e' misurato, che la causa sia LazyLLM e' letto in tre file». Se lo affermo a
qualcun altro come base per la sua tabella, devo misurarlo.

  A  llm = get_llm()   (cio' che passa l'SDK senza provider)  -> MockLLM
  B  llm = LazyLLM()   (cio' che passa la porta MCP, agent.py:81)

PREDIZIONE scritta prima: A -> "no_provider" · B -> "unreadable".
Se B desse "no_provider" la guardia NON e' inerte e la mia riga a @ws4 cade.
"""
from __future__ import annotations

import os
import pathlib
import tempfile

for _k in list(os.environ):
    if _k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_")):
        del os.environ[_k]
CASA = pathlib.Path(tempfile.mkdtemp(prefix="guardia_"))
os.environ["HIPPO_DATA_DIR"] = str(CASA)

from verimem.client import Memory                    # noqa: E402
from verimem.llm import LazyLLM, get_llm             # noqa: E402
from verimem.trust_report import build_trust_report  # noqa: E402

SORG = "Verbale: il ripetitore di Ancona ha inoltrato 4200 messaggi."
m = Memory(CASA / "m.db")
m.add("Il ripetitore di Ancona ha inoltrato 4200 messaggi.",
      topic="g/uno", source=SORG)
sm = getattr(m, "semantic", None) or getattr(m, "_semantic", None) or m
Q = "quanti messaggi ha inoltrato il ripetitore di Ancona"

for nome, llm in (("A  get_llm()  (SDK)", get_llm()),
                  ("B  LazyLLM()  (porta MCP)", LazyLLM())):
    d = build_trust_report(sm, Q, k=3, llm=llm)
    print(f"  {nome:<28} type={type(llm).__name__:<10} "
          f"sufficiency={d.get('verify', {}).get('sufficiency')!r}")
print("\n  la guardia cerca  type(llm).__name__ == 'MockLLM'")
print(f"  get_llm() ->  {type(get_llm()).__name__:<10} scatta: {type(get_llm()).__name__ == 'MockLLM'}")
print(f"  LazyLLM() ->  {type(LazyLLM()).__name__:<10} scatta: {type(LazyLLM()).__name__ == 'MockLLM'}")
