"""Total-rename contract (0.7.0): the flagship classes ARE verimem-named.

The package rename to `verimem` (0.6.0) left the two central orchestrator
classes still carrying old brands — `HippoAgent` (verimem/agent.py) and
`EngramCode` (verimem/code.py). 0.7.0 finishes the rename: the CANONICAL name
is verimem-branded, and the old name survives ONLY as a backward-compat alias
(same object, so `from verimem.agent import HippoAgent` and any third-party
`HippoAgent(...)` keep working — no breakage).
"""
from __future__ import annotations


def test_verimem_agent_is_the_canonical_class() -> None:
    from verimem.agent import VerimemAgent
    assert VerimemAgent.__name__ == "VerimemAgent"
    assert callable(VerimemAgent.build)


def test_hippoagent_is_a_backward_compat_alias() -> None:
    from verimem.agent import HippoAgent, VerimemAgent
    assert HippoAgent is VerimemAgent, "old name must alias the SAME object"


def test_verimem_code_is_the_canonical_class() -> None:
    from verimem.code import VerimemCode
    assert VerimemCode.__name__ == "VerimemCode"


def test_engramcode_is_a_backward_compat_alias() -> None:
    from verimem.code import EngramCode, VerimemCode
    assert EngramCode is VerimemCode, "old name must alias the SAME object"
