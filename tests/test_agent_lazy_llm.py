"""HippoAgent.build() must construct with NO usable LLM resolved up-front.

Real bug (2026-06-06): the dashboard pages /episodes, /skills, /active-memory
returned HTTP 500 with "ANTHROPIC_API_KEY not set" because building the agent
EAGERLY constructed the LLM (wake.py / sleep.py `llm or get_llm()`). The memory
layer + read-only views do ZERO inference, so build must install a deferred
proxy (verimem.llm.LazyLLM) and only resolve the real backend on first access.

Hermetic: asserts the structural fix (proxy installed) — independent of whether
the env resolves to a mock/anthropic/hosted backend. Pre-fix, `agent.wake.llm`
was a concrete backend (MockLLM under HIPPO_OFFLINE), NOT a LazyLLM, so this is
a genuine red->green.
"""
from __future__ import annotations

from verimem.agent import HippoAgent
from verimem.llm import LazyLLM


def test_build_installs_lazy_llm_proxy_no_key_needed():
    agent = HippoAgent.build()  # no llm arg, no API key required

    # read-only memory layer is usable without any LLM
    assert agent.memory is not None
    assert agent.skills is not None
    # build installed the DEFERRED proxy, not an eagerly-resolved backend
    assert isinstance(agent.wake.llm, LazyLLM)
    assert isinstance(agent.sleep.llm, LazyLLM)


def test_explicit_llm_is_not_wrapped():
    # When the caller passes a concrete llm, build must use it verbatim (no proxy).
    from verimem.llm import MockLLM

    real = MockLLM()
    agent = HippoAgent.build(llm=real)
    assert agent.wake.llm is real
    assert agent.sleep.llm is real


def test_lazy_llm_delegates_to_resolved_backend():
    # First attribute access resolves get_llm() and delegates transparently.
    proxy = LazyLLM()
    resp = proxy.complete(system="s", messages=[{"role": "user", "content": "hi"}])
    assert resp is not None and hasattr(resp, "text")
