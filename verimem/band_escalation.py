"""CE-band -> llm-judge escalation: the moat's uncertain middle gets a real verdict.

The free local CE adjudicates every sourced write; scores in its REVIEW BAND
[threshold, tau_hi) are the sliver it is genuinely unsure about (measured
over-review 1/19). Instead of always parking those writes for human review,
this module escalates the band to ONE llm adjudication when a judge is
available with zero wiring:

* an explicitly injected ``Memory(llm=...)`` never reaches here (it already
  judges every write);
* with NO injected llm, the band escalates OFFLINE-FIRST: a local ollama
  judge (a validated small model, measured better than the CE on the OOD
  blind spot -- qwen2.5:7b AUROC 0.858, 2.3% escape @t70) is preferred so an
  air-gapped deployment gets the full moat with NO network; a ``claude`` CLI
  on PATH is the online fallback (flat subscription, no API key, O5);
* ``ENGRAM_BAND_LLM=0`` opts out; ``ENGRAM_BAND_LLM_TIMEOUT_S`` bounds the
  call (default 90s).

Fail-soft by construction: no CLI, a CLI error, a timeout or an UNREADABLE
verdict all return ``None`` -> the caller keeps today's held-for-review
behavior. An unparseable answer must never admit a write.

The prompt reuses the SAME rubric as the injected-llm judge
(``grounding_gate._FACT_SYSTEM``) so the score scale -- and therefore the
claude-scale admission threshold -- stays calibrated.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from functools import lru_cache

#: explicit verdict anywhere in the answer ("Score: 87") — the LAST one wins
#: (the rubric ends with "Score:", so the model's final line is the verdict).
_SCORE_LABELED_RE = re.compile(r"score\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)",
                               re.IGNORECASE)
#: bare-number answer ("87", " 92.5 is my verdict") — accepted ONLY at the very
#: start of the output. A digit embedded in prose ("the 100 words…") is NOT a
#: verdict: parsing it once ADMITTED a fact the judge had scored 5.
_SCORE_LEADING_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d+)?)\b")


def _mode() -> str:
    v = os.environ.get("ENGRAM_BAND_LLM", "").strip().lower()
    if v in ("0", "off", "false", "no"):
        return "off"
    return "auto"


def _timeout_s() -> float:
    try:
        v = os.environ.get("ENGRAM_BAND_LLM_TIMEOUT_S", "").strip()
        return float(v) if v else 90.0
    except ValueError:
        return 90.0


@lru_cache(maxsize=1)
def _resolve_cli() -> str | None:
    """Absolute path of a ``claude`` CLI, or ``None``. lru_cached per process;
    tests clear via ``_resolve_cli.cache_clear()``."""
    return shutil.which("claude")


def _parse_score(text: str) -> float | None:
    """Extract the judge's 0-100 verdict from free text. An explicit
    ``Score: N`` (LAST occurrence, case-insensitive) wins; else a bare number
    at the very START; else ``None`` — a prose digit is NEVER a verdict."""
    out = (text or "").strip()
    labeled = _SCORE_LABELED_RE.findall(out)
    if labeled:
        v = float(labeled[-1])
    else:
        m = _SCORE_LEADING_RE.match(out)
        if not m:
            return None
        v = float(m.group(1))
    return min(100.0, max(0.0, v))


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _ollama_judge_model() -> str:
    """The local judge model. Default is the measured-good qwen2.5:7b-instruct;
    override with ENGRAM_BAND_LOCAL_MODEL (e.g. a larger local model)."""
    return (os.environ.get("ENGRAM_BAND_LOCAL_MODEL", "").strip()
            or "qwen2.5:7b-instruct")


@lru_cache(maxsize=1)
def _local_ollama_available() -> bool:
    """True iff an ollama server is up AND the configured judge model is
    pulled — a fast HTTP check of /api/tags (~ms), lru_cached per process so
    a down server costs one probe, not one per write. Tests clear via
    ``_local_ollama_available.cache_clear()``. ENGRAM_BAND_LOCAL=0 forces off."""
    if os.environ.get("ENGRAM_BAND_LOCAL", "").strip().lower() in ("0", "off", "false", "no"):
        return False
    want = _ollama_judge_model()
    try:
        with urllib.request.urlopen(_ollama_host() + "/api/tags", timeout=2.0) as r:
            names = {m.get("name", "") for m in json.loads(r.read()).get("models", [])}
    except Exception:  # noqa: BLE001 -- no server / bad response -> not available
        return False
    # require the REQUESTED model, not a same-family sibling: a qwen2.5:1.5b
    # present must NOT report a qwen2.5:7b-instruct judge as available. Accept
    # an exact tag or ollama's ":latest" form; a bare "qwen2.5:7b-instruct"
    # request also matches "qwen2.5:7b-instruct" verbatim.
    return any(n == want or n == want + ":latest"
               or (":" not in want and n.split(":")[0] == want)
               for n in names if n)


def _score_via_ollama(source: str, fact: str) -> float | None:
    """Score with the local ollama judge, fully OFFLINE. Calls the ollama llm
    DIRECTLY with the SAME production rubric (_FACT_SYSTEM, claude 0-100 scale)
    -- NOT via fact_grounding_score_ex, whose backend resolution would swap in
    the CE instead of this judge when ENGRAM_GROUNDING_BACKEND=local is set.
    Channel separation as the claude path: rubric in the system prompt, only
    the tenant DATA in the user prompt. Fail-soft: any error -> None so the
    cascade falls through to claude, then review; an unreadable verdict never
    admits."""
    try:
        from .grounding_gate import _FACT_SYSTEM
        from .llm import _build
        model = _ollama_judge_model()
        llm = _build("ollama")
        llm.default_model = model
        user = f"Source: {source}\n\nCandidate fact: {fact}\n\nScore:"
        resp = llm.complete(_FACT_SYSTEM,
                            [{"role": "user", "content": user}],
                            model=model, max_tokens=16)
        return _parse_score(getattr(resp, "text", ""))
    except Exception:  # noqa: BLE001 -- offline judge failure degrades to fallback
        return None


def _score_via_claude(source: str, fact: str) -> float | None:
    """Score with an auto-discovered claude CLI (online, flat subscription, no
    key). Channel separation: the rubric rides as a SYSTEM prompt; only the
    tenant-controlled DATA goes in the user prompt. Fail-soft -> None."""
    cli = _resolve_cli()
    if not cli:
        return None
    from .grounding_gate import _FACT_SYSTEM
    user = f"Source: {source}\n\nCandidate fact: {fact}\n\nScore:"
    try:
        r = subprocess.run(
            [cli, "-p", "--output-format", "text",
             "--append-system-prompt", _FACT_SYSTEM],
            input=user, capture_output=True, text=True,
            timeout=_timeout_s(), encoding="utf-8", errors="replace",
        )
    except Exception:  # noqa: BLE001 -- ANY escalation failure degrades to review
        return None
    if r.returncode != 0:
        return None
    return _parse_score(r.stdout)


def escalate_band(source: str, fact: str) -> tuple[float, str] | None:
    """Adjudicate a band-parked write, OFFLINE-FIRST. Returns
    ``(score, judge)`` with ``judge`` in {"local-band", "claude-band"}, or
    ``None`` when escalation is off / no judge is reachable / every judge
    failed — the caller then holds the write for review, exactly as before.
    An unreadable verdict never admits."""
    if _mode() == "off":
        return None
    if _local_ollama_available():
        s = _score_via_ollama(source, fact)
        if s is not None:
            return (s, "local-band")
        # local judge present but failed this call -> try the online fallback
    s = _score_via_claude(source, fact)
    if s is not None:
        return (s, "claude-band")
    return None


def escalate_band_score(source: str, fact: str) -> float | None:
    """Back-compat float API over :func:`escalate_band` (score only)."""
    out = escalate_band(source, fact)
    return None if out is None else out[0]


__all__ = ["escalate_band", "escalate_band_score"]
