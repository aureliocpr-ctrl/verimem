"""Local write-gate judge — the distilled CE backend for the grounding gate.

Why this exists: the write-gate's judge (``grounding_gate.fact_grounding_score``)
costs one ``claude -p`` call per candidate fact; headless subscription calls are
moving to paid, so the gate needs a subscription-independent backend. The model is a
cross-encoder fine-tuned on HaluMem ground truth (``benchmark/local_gate_finetune.py``)
with a binary head: sigmoid(logit)*100 on (source_span, fact) — same 0-100 scale as
the claude judge, thresholded by the gate.

Selection is env-gated and OFF by default (``ENGRAM_GROUNDING_BACKEND=local`` to opt
in; anything else = the injected-llm claude path, unchanged). The model directory is
``ENGRAM_LOCAL_GATE_MODEL`` or ``~/.engram/models/local_gate_ce`` and may carry a
``gate_config.json`` written by the fine-tune run ({threshold, focus_budget, ...});
env thresholds always beat the config (see ``grounding_gate.should_store_fact``).

Injection-only testability (house style, like cross_encoder_rerank): the judge takes
an optional ``scorer`` callable so unit tests never load transformers or download a
model; the real model is lazy-loaded on first use, behind a lock (the write path can
be called from multiple threads).
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from verimem.grounding_gate import select_relevant_span

Scorer = Callable[[list[tuple[str, str]]], list[float]]

_ENV_MODEL_DIR = "ENGRAM_LOCAL_GATE_MODEL"
# v2 (2026-07-02) is the shipped model: same HaluMem skill as v1 (heldout AUROC 0.99,
# false-memory admit 0.042 vs v1's 0.086) PLUS the real-corpus register (real-fact
# admit 0.82→0.98, agreement vs claude 0.76→0.88). Trained by distilling the claude
# DECISION on a mixed HaluMem-GT + real-corpus set (benchmark/local_gate_distill_v2.py).
# v1 (local_gate_ce) is kept on disk for comparison. Override with ENGRAM_LOCAL_GATE_MODEL.
DEFAULT_MODEL_DIR = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
_DEFAULT_FOCUS_BUDGET = 1500


def _resolve_model_dir(model_dir: str | Path | None) -> Path:
    env = os.environ.get(_ENV_MODEL_DIR, "").strip()
    return Path(env or model_dir or DEFAULT_MODEL_DIR).expanduser()


def make_finetuned_scorer(model_dir: str | Path, *, max_length: int = 512,
                          batch_size: int = 32) -> Scorer:
    """Production scorer over the saved binary-head CE: sigmoid(logit)*100 per
    (premise, hypothesis) pair. Imports transformers lazily."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir)).to(device).eval()

    @torch.no_grad()
    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        out: list[float] = []
        for i in range(0, len(batch), batch_size):
            chunk = batch[i:i + batch_size]
            enc = tok([p for p, _ in chunk], [h for _, h in chunk],
                      truncation="longest_first", max_length=max_length,
                      padding=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits.squeeze(-1)
            out.extend((torch.sigmoid(logits) * 100.0).float().cpu().tolist())
        return out

    return scorer


class LocalGroundingJudge:
    """Scores source ⊢ fact in [0, 100] with the local CE. The source is reduced to
    its fact-relevant span (production selector) before scoring — the CE window is
    512 tokens."""

    def __init__(self, model_dir: str | Path | None = None, *,
                 scorer: Scorer | None = None, max_length: int = 512,
                 focus_budget: int | None = None):
        self.model_dir = _resolve_model_dir(model_dir)
        self._scorer = scorer
        self._lock = threading.Lock()
        self.max_length = max_length
        self._focus_budget = focus_budget
        self._config: dict[str, Any] | None = None
        self._load_failed = False

    @property
    def config(self) -> dict[str, Any]:
        """gate_config.json from the model dir ({} when absent/corrupt)."""
        if self._config is None:
            try:
                self._config = json.loads(
                    (self.model_dir / "gate_config.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._config = {}
        return self._config

    @property
    def threshold(self) -> float | None:
        t = self.config.get("threshold")
        return float(t) if isinstance(t, (int, float)) else None

    @property
    def focus_budget(self) -> int:
        if self._focus_budget:
            return int(self._focus_budget)
        b = self.config.get("focus_budget")
        return int(b) if isinstance(b, (int, float)) and b > 0 else _DEFAULT_FOCUS_BUDGET

    def _ensure_scorer(self) -> Scorer:
        if self._scorer is None:
            if self._load_failed:
                raise RuntimeError(f"local gate model unavailable: {self.model_dir}")
            with self._lock:
                if self._scorer is None:
                    t0 = time.time()
                    try:
                        self._scorer = make_finetuned_scorer(
                            self.model_dir, max_length=self.max_length)
                    except Exception:
                        # cache the failure: a broken/absent model must not re-pay
                        # the load attempt on every gated write
                        self._load_failed = True
                        raise
                    self.load_s = round(time.time() - t0, 1)
        return self._scorer

    def score(self, source: str, fact: str, *,
              focus_budget: int | None = None) -> float:
        budget = int(focus_budget) if focus_budget else self.focus_budget
        span = select_relevant_span(source or "", fact or "", budget=budget)
        val = self._ensure_scorer()([(span, fact or "")])[0]
        return min(100.0, max(0.0, float(val)))


_judge: LocalGroundingJudge | None = None
_judge_lock = threading.Lock()


def get_local_judge() -> LocalGroundingJudge:
    """Process-wide lazy singleton (model loads once)."""
    global _judge
    if _judge is None:
        with _judge_lock:
            if _judge is None:
                _judge = LocalGroundingJudge()
    return _judge


def set_local_judge(judge: LocalGroundingJudge | None) -> None:
    """Inject a judge (tests) — pass None to clear."""
    global _judge
    _judge = judge


def reset_local_judge() -> None:
    global _bg_warm_started
    set_local_judge(None)
    _bg_warm_started = False   # tests: allow a fresh background warm


def get_local_threshold() -> float | None:
    """The fine-tune-calibrated admission threshold, if the model ships one."""
    return get_local_judge().threshold


def local_ce_available() -> bool:
    """True when the local CE moat judge can score WITHOUT an injected llm — an
    injected scorer (tests) or a model dir present on disk. Cheap by design:
    it NEVER loads the model, so the gate can ask "is there a judge?" on the hot
    write path without paying the cold-start. Used to turn the entailment moat ON
    by default for a user who passed no llm (the CE is multilingual)."""
    j = get_local_judge()
    if getattr(j, "_scorer", None) is not None:
        return True
    if getattr(j, "_load_failed", False):
        return False
    try:
        return j.model_dir.exists()
    except OSError:
        return False


# --- gate-model acquisition (2026-07-18, PUBLISHED) ----------------------------
# The fine-tuned gate CE (local_gate_ce_v2) is what makes the moat judge-less.
# On a FRESH machine the model dir does not exist and — demonstrated 2026-07-18 —
# the README quickstart's `assert status == "quarantined"` fails (the write is
# admitted with an L4-skipped advisory). `verimem warmup` calls ensure_gate_model
# to close that gap: it downloads the PUBLISHED model (a public GitHub release
# tarball — no auth), verifies its sha256, and extracts it. The claim is now
# true end-to-end for any downloader.
_ENV_GATE_HUB_ID = "VERIMEM_GATE_MODEL_HUB_ID"
_ENV_GATE_URL = "VERIMEM_GATE_MODEL_URL"

#: Published gate model: a public GitHub release tarball (config.json,
#: gate_config.json, model.safetensors, tokenizer*). No auth, no HF account.
DEFAULT_GATE_MODEL_URL = (
    "https://github.com/aureliocpr-ctrl/verimem/releases/download/"
    "gate-ce-v2/verimem-gate-ce-v2.tar.gz")
DEFAULT_GATE_MODEL_SHA256 = (
    "58255842348553f6b14c2463c795f3a40b951751166838c519916553fc0b2810")
#: Alternative source (HF Hub repo id) — used only if explicitly set.
DEFAULT_GATE_MODEL_HUB_ID: str | None = None


def _download_and_extract_tar(url: str, dest: Path, *,
                              sha256: str | None = None, opener=None) -> None:
    """Stream ``url`` to a temp file (verifying sha256), then extract the tar.gz
    into ``dest``. stdlib-only; extraction uses the ``data`` filter (py3.12+) to
    refuse path-traversal members."""
    import hashlib
    import tarfile
    import tempfile
    import urllib.request
    opener = opener or urllib.request.urlopen
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        h = hashlib.sha256()
        with opener(url) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
        if sha256 and h.hexdigest() != sha256:
            raise ValueError(
                f"gate model sha256 mismatch: got {h.hexdigest()[:16]}… "
                f"expected {sha256[:16]}… — refusing to install")
        with tarfile.open(tmp, "r:gz") as tar:
            _safe_tar_extract(tar, dest)
    finally:
        tmp.unlink(missing_ok=True)


def _safe_tar_extract(tar, dest: str | Path) -> None:
    """Extract *tar* into *dest*, refusing any member that would escape it —
    the tar-slip guard (CodeQL py/tarslip). Python 3.12+ has the built-in
    ``filter="data"`` for exactly this; on 3.10/3.11 (no filter kwarg) we
    validate every member against the resolved destination ourselves and
    extract only the ones that stay inside — never a bare ``extractall``.
    """
    try:
        tar.extractall(dest, filter="data")   # py3.12+ hardened built-in filter
        return
    except TypeError:                          # py<3.12 — no filter kwarg
        pass
    dest_r = Path(dest).resolve()
    for m in tar.getmembers():
        if m.issym() or m.islnk() or m.isdev():
            continue  # the published gate-model tar is plain files only
        target = (dest_r / m.name).resolve()
        if target != dest_r and dest_r not in target.parents:
            raise ValueError(
                f"refusing tar member that escapes {dest_r}: {m.name!r}")
        tar.extract(m, dest)


def ensure_gate_model(model_dir: str | Path | None = None, *,
                      url: str | None = None, hub_id: str | None = None,
                      download=None) -> tuple[bool, str]:
    """Ensure the local gate CE exists at ``model_dir``; download+verify+extract
    the published model if absent. Returns ``(present, message)``.

    Source precedence: explicit ``url`` / ``VERIMEM_GATE_MODEL_URL`` → explicit
    ``hub_id`` / ``VERIMEM_GATE_MODEL_HUB_ID`` → the built-in public release URL.
    ``download`` is injectable for tests (called as ``download(source, dest)``).
    """
    dest = _resolve_model_dir(model_dir)
    if (dest / "config.json").exists():
        return True, f"gate model present at {dest}"
    the_url = url or os.environ.get(_ENV_GATE_URL, "").strip()
    hub = hub_id or os.environ.get(_ENV_GATE_HUB_ID, "").strip()
    if download is not None:
        download(the_url or hub or DEFAULT_GATE_MODEL_URL, dest)
    elif the_url:
        _download_and_extract_tar(the_url, dest)
    elif hub:  # pragma: no cover — HF path exercised via injected download
        from huggingface_hub import snapshot_download
        dest.mkdir(parents=True, exist_ok=True)
        snapshot_download(repo_id=hub, local_dir=str(dest))
    else:  # the default: the published public release tarball
        _download_and_extract_tar(DEFAULT_GATE_MODEL_URL, dest,
                                  sha256=DEFAULT_GATE_MODEL_SHA256)
    ok = (dest / "config.json").exists()
    return ok, (f"gate model installed at {dest}" if ok else
                f"download left no config.json in {dest}")


_warned_fallback = False

# --- delegate-only: keep the CE cold-load OFF the request thread ---------------
# MCP-server processes run with HIPPO_ENCODE_DELEGATE_ONLY=1 (mirror of
# embedding._delegate_only, kept env-local so this module stays import-light).
# The moat CE cold-load (~30s measured 2026-07-18: import + model build under the
# judge lock) blocked the FIRST gated write of every fresh server — same class as
# the 2026-06-05 embedding hang, new site. In delegate-only mode the load runs on
# a background thread instead; until warm, try_local_score returns None and the
# caller degrades honestly (injected llm, or the L4-skipped advisory admit).
# Deliberately NOT a boot-time preload: that would charge every server ~400 MB
# whether it ever writes or not (the 2026-07-10 rerank RAM incident) — warming on
# first USE bills only processes that actually run the moat.
_DELEGATE_TRUTHY = {"1", "true", "yes", "on"}
_bg_warm_started = False
_bg_warm_lock = threading.Lock()


def _delegate_only() -> bool:
    return (os.environ.get("HIPPO_ENCODE_DELEGATE_ONLY", "").strip().lower()
            in _DELEGATE_TRUTHY)


def warm_local_judge_async() -> None:
    """Warm the CE off the request thread (once per process). Load failure is
    cached on the judge, so the advisory path keeps working either way."""
    global _bg_warm_started
    with _bg_warm_lock:
        if _bg_warm_started:
            return
        _bg_warm_started = True

    def _warm() -> None:
        try:
            get_local_judge()._ensure_scorer()
        except Exception:  # noqa: BLE001 — cached on the judge; advisory continues
            pass

    threading.Thread(target=_warm, daemon=True, name="verimem-ce-warm").start()


def try_local_score(source: str, fact: str, *,
                    focus_budget: int | None = None,
                    ) -> tuple[float, float | None] | None:
    """(score, config_threshold) via the local judge, or None when the local model is
    unavailable (the caller falls back to its injected llm at the CLAUDE-scale
    threshold — the config cut must never be applied to a claude-scale score). The
    load failure is cached; the fallback warning fires once per process."""
    global _warned_fallback
    judge = get_local_judge()
    # DELEGATE-ONLY (MCP server): never pay the CE cold-load on this thread —
    # kick the background warm and degrade until it lands (see block above).
    if judge._scorer is None and not judge._load_failed and _delegate_only():
        warm_local_judge_async()
        return None
    # LOAD phase — a missing / unloadable model is a legitimate "no local judge":
    # fail over to None (caller uses its injected llm, or emits the L4-skipped
    # advisory). Only load failure is swallowed here.
    try:
        judge._ensure_scorer()
    except Exception:  # noqa: BLE001 — model absent/unloadable -> fail over
        if not _warned_fallback:
            _warned_fallback = True
            import warnings
            warnings.warn(
                f"ENGRAM_GROUNDING_BACKEND=local but the model at {judge.model_dir} "
                f"is unavailable — falling back to the injected llm judge",
                RuntimeWarning, stacklevel=2)
        return None
    # The model IS loaded. An inference failure now (torch shape mismatch, CUDA
    # OOM) is a REAL fault, NOT an absent judge — let it PROPAGATE rather than
    # laundering it into "no judge -> admit" (opus re-review 2026-07-18, finding B:
    # this is the default out-of-the-box path, where the earlier fix did not reach).
    score = judge.score(source, fact, focus_budget=focus_budget)
    return score, judge.threshold


__all__ = ["LocalGroundingJudge", "make_finetuned_scorer", "get_local_judge",
           "set_local_judge", "reset_local_judge", "get_local_threshold",
           "try_local_score", "local_ce_available", "warm_local_judge_async",
           "ensure_gate_model", "DEFAULT_GATE_MODEL_URL",
           "DEFAULT_GATE_MODEL_SHA256", "DEFAULT_GATE_MODEL_HUB_ID",
           "DEFAULT_MODEL_DIR"]
