"""CE-band -> llm-judge escalation: the moat's uncertain middle gets a real verdict.

The free local CE adjudicates every sourced write; scores in its REVIEW BAND
[threshold, tau_hi) are the sliver it is genuinely unsure about (measured
over-review 1/19). Instead of always parking those writes for human review,
this module escalates the band to ONE llm adjudication when a judge is
available with zero wiring:

* an explicitly injected ``Memory(llm=...)`` never reaches here (it already
  judges every write);
* with NO injected llm, a ``claude`` CLI on PATH is auto-discovered and used
  in print mode -- flat subscription, no API key (O5);
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

import os
import re
import shutil
import subprocess
from functools import lru_cache

#: first number in the CLI answer, same convention as grounding_gate._SCORE_RE.
_SCORE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)")


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


def escalate_band_score(source: str, fact: str) -> float | None:
    """One llm adjudication of a band-parked write: score in [0, 100] on the
    claude scale, or ``None`` when escalation is off/unavailable/failed --
    the caller then holds the write for review exactly as before."""
    if _mode() == "off":
        return None
    cli = _resolve_cli()
    if not cli:
        return None
    from .grounding_gate import _FACT_SYSTEM
    prompt = (f"{_FACT_SYSTEM}\n\nSource: {source}\n\n"
              f"Candidate fact: {fact}\n\nScore:")
    try:
        r = subprocess.run(
            [cli, "-p", "--output-format", "text"],
            input=prompt, capture_output=True, text=True,
            timeout=_timeout_s(), encoding="utf-8", errors="replace",
        )
    except Exception:  # noqa: BLE001 -- ANY escalation failure degrades to review
        return None
    if r.returncode != 0:
        return None
    m = _SCORE_RE.search(r.stdout or "")
    if not m:
        return None  # unreadable verdict must never admit
    return min(100.0, max(0.0, float(m.group(1))))


__all__ = ["escalate_band_score"]
