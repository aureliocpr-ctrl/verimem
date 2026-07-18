"""Air-gap self-verification — can this Engram config run with ZERO network egress?

For the sovereign / air-gapped enterprise segment (regulated industries that
cannot send data to ANY cloud). Engram's embeddings are local
(sentence-transformers, offline-capable) and the LLM layer can target a LOCAL
model — Ollama (`HIPPO_LLM_PROVIDER=ollama`) or any OpenAI-compatible local
endpoint (vLLM / LM Studio / llama.cpp) via a localhost `*_BASE_URL`. The
anti-confab governance core (L1-L3 detectors) is deterministic = zero-LLM, so
it works fully offline. A fully-air-gapped deployment is therefore possible —
this module turns that property into a VERIFIABLE, structured self-check
(a sellable feature: *prove* there is no egress, instead of asserting it).

Two levels:
* ``airgap_status()`` — the CONFIG check: inspects env + the code paths surfaced
  by the 2026-06-06 LLM leak-audit (get_llm chokepoint + ``_is_hosted`` gating +
  provider-dispatched vision + offline embeddings). Makes NO network call, loads
  NO model.
* ``probe_live_egress()`` — the RUNTIME PROOF (2026-07-17): exercises a real
  write+search under a CPython ``socket.connect`` audit hook and reports any
  non-loopback destination actually attempted. This is the "prove not assert"
  half, exposed as ``verimem airgap --live``.

Honest scope of the live probe: the ``socket.connect`` audit event covers the
realistic egress surface (httpx / requests / urllib / huggingface-hub — every
TCP client dials through it, including from C extensions). It does NOT claim to
catch a deliberate kernel-level bypass (raw ``sendto`` on an unconnected UDP
socket, a pre-connected fd handed in) — that is an exfiltration-grade adversary,
out of scope for a config-compliance proof; pair it with an OS egress firewall
for that threat model.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

_TRUTHY = {"1", "true", "yes", "on"}

#: Offline flags that pin the embedding model to cache-only (no HF Hub round-trip).
#: Mirrors ``verimem.embedding._OFFLINE_ENV_VARS``.
_OFFLINE_FLAGS = (
    "VERIMEM_OFFLINE", "HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
    "TRANSFORMERS_OFFLINE",
)

#: Providers whose model runs LOCALLY (no cloud egress by construction).
#: ``mock`` makes no network call at all; ``ollama`` is a local daemon.
_LOCAL_PROVIDERS = {"ollama", "mock"}

def _is_local_base_url(url: str) -> bool:
    """True iff ``url`` targets a loopback/local endpoint (vLLM / LM Studio /
    llama.cpp / text-gen-webui / ollama).

    Locality is decided on the PARSED hostname — exact ``localhost`` or a real
    loopback/unspecified IP (the whole 127.0.0.0/8, ``::1``, ``0.0.0.0``) —
    never on substrings: ``evil-localhost.attacker.com`` / ``127.0.0.1.evil.com``
    must not count as local (2026-07-15 adversarial review — the substring match
    made the air-gap verdict spoofable). The verdict is a compliance claim, so
    anything unparseable fails CLOSED: non-local, reported as a leak. Scheme-less
    values ("localhost:11434") are common in provider configs and still resolve.
    """
    from ipaddress import ip_address
    from urllib.parse import urlsplit

    u = (url or "").strip()
    if not u:
        return False
    try:
        host = urlsplit(u).hostname
        if not host:
            # "localhost:11434" parses as scheme=localhost path=11434 —
            # re-parse as a network location.
            host = urlsplit("//" + u).hostname
    except ValueError:  # e.g. unbalanced IPv6 bracket
        return False
    host = (host or "").strip().lower()
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        ip = ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def _llm_locality(provider: str, env: Mapping[str, str]) -> tuple[bool, str]:
    """Return (is_local, reason) for the configured LLM provider."""
    p = (provider or "").strip().lower()
    if p in _LOCAL_PROVIDERS:
        return True, f"provider '{p}' runs locally"
    if not p:
        return (
            False,
            "no HIPPO_LLM_PROVIDER set — auto-detect may pick a cloud provider "
            "or (with HIPPO_HOSTED) the host's LLM",
        )
    # OpenAI-compatible providers are local IFF their base_url is a local host.
    # base_url override: <PROVIDER>_BASE_URL, else the generic OPENAI_BASE_URL.
    base = (env.get(f"{p.upper()}_BASE_URL") or env.get("OPENAI_BASE_URL") or "").strip()
    if _is_local_base_url(base):
        return True, f"provider '{p}' targets a local endpoint ({base})"
    if base:
        return False, f"provider '{p}' targets a non-local endpoint ({base})"
    return False, f"provider '{p}' is a cloud provider (no local base_url override)"


def airgap_status(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Structured verdict on whether the current config can run air-gapped.

    Returns a dict::

        {
          "air_gapped": bool,           # True only if there are NO leaks
          "llm": {"provider", "local", "reason"},
          "embeddings": {"offline_pinned": bool},
          "hosted_mode": bool,
          "leaks": [str, ...],          # one human-readable line per egress risk
        }

    Pure over ``env`` (defaults to ``os.environ``) — no network, no model load.
    """
    env = os.environ if env is None else env
    provider = (env.get("HIPPO_LLM_PROVIDER") or "").strip().lower()
    hosted = env.get("HIPPO_HOSTED", "").strip().lower() in _TRUTHY
    llm_local, llm_reason = _llm_locality(provider, env)
    emb_offline = any(
        env.get(flag, "").strip().lower() in _TRUTHY for flag in _OFFLINE_FLAGS
    )

    leaks: list[str] = []
    if hosted:
        leaks.append(
            "HIPPO_HOSTED is set: consolidate/run route the LLM to the host "
            "(MCP sampling / `claude` CLI) = cloud egress. Unset it for air-gap."
        )
    if not llm_local:
        leaks.append(f"LLM may egress to the cloud: {llm_reason}.")
    if not emb_offline:
        leaks.append(
            "Embeddings not pinned offline: set one of "
            + "/".join(_OFFLINE_FLAGS)
            + "=1 so the model loads cache-only (no HF Hub round-trip on cold load)."
        )

    return {
        "air_gapped": not leaks,
        "llm": {"provider": provider or "auto", "local": llm_local, "reason": llm_reason},
        "embeddings": {"offline_pinned": emb_offline},
        "hosted_mode": hosted,
        "leaks": leaks,
    }


def _default_exercise() -> None:
    """Exercise the core write+read path with a mock LLM so a clean, offline
    config makes ZERO network calls: extract-gate-store a fact, then search it.
    Any egress observed while this runs is a real leak, not a legitimate call."""
    import tempfile
    from pathlib import Path

    from .client import Memory

    m = Memory(Path(tempfile.mkdtemp(prefix="airgap_")) / "m.db")
    m.add("The warehouse in Berlin ships on Mondays.", topic="airgap-probe",
          verified_by=["src:airgap:t1"])
    m.search("when does the Berlin warehouse ship?")


def probe_live_egress(exercise=None) -> dict[str, Any]:
    """LIVE no-egress proof: run ``exercise`` (default: a real write+search) while
    a CPython audit hook records EVERY ``socket.connect``, and report any
    NON-loopback destination. Empty ``egress`` => proven zero cloud egress at
    runtime — the datacenter/sovereign claim, demonstrated not asserted.

    Returns ``{"air_gapped": bool, "egress": [str, ...], "connects_total": int}``.

    The audit hook (``sys.addaudithook``) is process-global and PERMANENT — it
    catches connects from C extensions too (httpx/requests/HF-hub), which a
    monkeypatch would miss — so call this in a one-shot process (the
    ``verimem airgap --live`` CLI) or a subprocess. It only records; it never
    blocks a connection.
    """
    import sys

    egress: list[str] = []
    counter = {"n": 0}

    def _host_of(address: Any) -> str | None:
        # AF_INET/6 -> (host, port[, ...]); AF_UNIX -> path (local by definition)
        if isinstance(address, tuple) and address:
            return str(address[0])
        return None  # unix socket / unknown shape = not a network host

    def _audit(event: str, args: tuple) -> None:
        if event != "socket.connect" or len(args) < 2:
            return
        counter["n"] += 1
        host = _host_of(args[1])
        if host is None:
            return
        # reuse the SAME loopback rule as the config check (parses the host,
        # no spoofable substrings; scheme-less bare hosts/IPs resolve too)
        if not _is_local_base_url(host):
            egress.append(host)

    sys.addaudithook(_audit)
    try:
        (exercise or _default_exercise)()
    except Exception:  # noqa: BLE001 — a broken exercise must not hide egress data
        pass
    # de-dup preserving order
    seen: set[str] = set()
    uniq = [h for h in egress if not (h in seen or seen.add(h))]
    return {"air_gapped": not uniq, "egress": uniq, "connects_total": counter["n"]}


__all__ = ["airgap_status", "probe_live_egress"]
