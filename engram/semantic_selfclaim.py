"""L1.20 — multilingual semantic self-claim detector (the 8-of-10 hole fix).

Reproduced 2026-07-09 (Aurelio's finding): the L1 keyword family is EN/IT —
the same unsupported hype claim in es/fr/de/pt/ru/zh/ja/ar sailed through the
gate CLEAN (8/10 languages). The fix is not a different embedder: cross-lingual
ranking of the production e5 model is already perfect on our micro-bench
(benchmark/multilingual_recall.py, recall 1.00 in all 10 languages). The fix
is to USE that multilingual embedder as the detector itself.

Mechanism — dual-check, calibrated with data
(benchmark/selfclaim_threshold_calibration.py, e5 dual: recall 1.0 across all
10 languages @ 0 false positives, margin 0.037):

* ``score``  = max cosine of the claim vs HYPE exemplars (EN + 9 languages)
  must be >= ``t_hype`` (absolute closeness to hype), AND
* ``delta``  = score - max cosine vs NEUTRAL factual anchors must be
  >= ``t_delta`` (closer to hype than to plain facts).

The second condition is what a single threshold could not give: e5's
anisotropy packs everything into cosine ~0.75-0.9, so the best single
threshold had a 0.001 margin; the dual frontier has 0.037.

Safety properties (mirrors the rest of the L1 family):
* evidence disarms it — a claim WITH ``verified_by`` refs is never flagged;
* downgrade-only — it emits a warning (caller quarantines), never a reject;
* fail-open — any encoder error (daemon down, delegate-only cold) skips the
  detector rather than breaking the write;
* model-gated — thresholds are calibrated for the e5 family; with a different
  active encoder the detector disarms itself unless thresholds are explicitly
  provided via env (re-run the calibration script and set them).

Env: ``ENGRAM_L1_SEMANTIC=0`` kill-switch; ``ENGRAM_L1_SEMANTIC_T_HYPE`` /
``ENGRAM_L1_SEMANTIC_T_DELTA`` threshold overrides (also the opt-in for
non-e5 encoders).
"""
from __future__ import annotations

import os
import threading
from typing import Any

import numpy as np

#: Calibrated on intfloat/multilingual-e5-base — see
#: benchmark/results/selfclaim_calib_e5_dual.json (recall 1.0, fp 0, margin .037).
_DEFAULT_T_HYPE = 0.84
_DEFAULT_T_DELTA = 0.025

#: Hype exemplars: the claim families the keyword L1 chain catches in EN,
#: expressed in 10 languages so a same-language claim meets a same-language
#: exemplar (cross-lingual cosine is good; same-language is better).
EXEMPLARS: list[str] = [
    # en
    "the deployment works and is verified in production",
    "everything works correctly and has been confirmed",
    "all tests passed successfully",
    "the test suite is green, everything passes",
    "the feature is complete and production-ready",
    "the system is stable and ready for production",
    "the bug is fixed and the issue is resolved",
    "the patch works, problem solved and verified",
    "performance improved dramatically, much faster now",
    "the integration is done and fully functional",
    "everything has been deployed and runs perfectly",
    "this is ready to ship, fully validated",
    # it
    "è tutto deployato e gira perfettamente",
    "l'intera suite di test passa senza errori",
    "è pronto al rilascio, completamente validato",
    "lo abbiamo sistemato e confermato che funziona bene",
    # es
    "todo está desplegado y funciona perfectamente",
    "toda la batería de pruebas pasa sin errores",
    "está listo para publicar, totalmente validado",
    "lo arreglamos y confirmamos que funciona bien",
    # fr
    "tout est déployé et fonctionne parfaitement",
    "toute la suite de tests passe sans erreurs",
    "c'est prêt à livrer, entièrement validé",
    "nous l'avons réparé et confirmé que ça marche bien",
    # de
    "alles ist deployed und läuft einwandfrei",
    "die gesamte Testsuite läuft ohne Fehler durch",
    "es ist bereit zur Auslieferung, vollständig validiert",
    "wir haben es repariert und bestätigt, dass es gut funktioniert",
    # pt
    "está tudo implantado e funcionando perfeitamente",
    "toda a suíte de testes passa sem erros",
    "está pronto para lançar, totalmente validado",
    "consertamos e confirmamos que está funcionando bem",
    # ru
    "всё развернуто и работает отлично",
    "весь набор тестов проходит без ошибок",
    "готово к выпуску, полностью проверено",
    "мы это починили и подтвердили, что всё работает хорошо",
    # zh
    "一切都已部署并且运行完美",
    "整个测试套件全部通过，没有错误",
    "已准备好发布，完全验证过了",
    "我们修好了并确认它运行良好",
    # ja
    "すべてデプロイされ、完璧に動いています",
    "テストスイート全体がエラーなしで通ります",
    "リリース準備完了、完全に検証済みです",
    "修正して、正常に動くことを確認しました",
    # ar
    "كل شيء تم نشره ويعمل بشكل مثالي",
    "مجموعة الاختبارات كاملة تمر بدون أخطاء",
    "جاهز للإطلاق، تم التحقق منه بالكامل",
    "أصلحناه وتأكدنا أنه يعمل بشكل جيد",
]

#: Neutral factual anchors — the "plain facts" pole of the dual check,
#: same 10 languages for parity.
ANCHORS: list[str] = [
    # en
    "the meeting is scheduled for Thursday at 9 AM",
    "the contract expires at the end of December",
    "she moved to a new city for her job in 2024",
    "the password is rotated every 90 days by the team",
    "his favourite dish is his mother's couscous",
    "the appointment is on Monday afternoon at the clinic",
    "the project is written in Rust with a PostgreSQL layer",
    "the trip is planned for the last week of August",
    "the deadline for the quarterly filing is the 16th",
    "the daughter starts primary school in September",
    # it / es / fr / de / pt / ru / zh / ja / ar
    "la riunione è fissata per giovedì alle 9",
    "il progetto è scritto in Rust con PostgreSQL",
    "il processo prevede due approvazioni prima del rilascio",
    "la reunión está programada para el jueves a las 9",
    "el proceso requiere dos aprobaciones antes del lanzamiento",
    "la réunion est prévue jeudi à 9 heures",
    "le processus exige deux approbations avant la mise en production",
    "das Meeting ist für Donnerstag um 9 Uhr angesetzt",
    "der Prozess erfordert zwei Freigaben vor dem Release",
    "a reunião está marcada para quinta-feira às 9",
    "o processo exige duas aprovações antes do lançamento",
    "встреча назначена на четверг на 9 утра",
    "процесс требует двух одобрений перед выпуском",
    "会议定于周四上午9点",
    "流程要求发布前需要两次批准",
    "会議は木曜日の朝9時に予定されています",
    "リリース前に2回の承認が必要です",
    "الاجتماع مقرر يوم الخميس الساعة التاسعة صباحا",
    "العملية تتطلب موافقتين قبل الإصدار",
]
# NOTE (adversarial review 2026-07-09): failure admissions ("does NOT work")
# and reported speech ("the vendor CLAIMS it works") are NOT anchored — e5 is
# nearly blind to negation and attribution markers, so same-vocabulary
# "honest" anchors only compressed the hype delta (zh/ja) without separating.
# Both are SYNTACTIC phenomena → deterministic guards below, before any
# embedding. Anchors stay purely neutral-factual.

#: Question marks across the supported scripts — a QUESTION is never a
#: self-claim (review 2026-07-09: "does the deployment work?" was flagged).
_QUESTION_MARKS = ("?", "？", "؟")

#: Negation guard (review 2026-07-09, negation-blindness): an honest failure
#: admission — "the deployment does NOT work" — sits at cosine ~0.95 from the
#: hype claim for e5, so NO threshold separates them in embedding space.
#: Negation is a SYNTACTIC phenomenon → deterministic pre-embedding guard.
#: FP-safety-first like the whole L1 family: a negated claim skips the
#: semantic detector (worst case an odd hype slips; quarantining honesty is
#: the worse error).
import re as _re

_NEGATION_RE = _re.compile(
    r"(?:\bnot\b|n't\b|\bnever\b|\bno longer\b"
    r"|\bnon\b|\bné\b"                     # it
    r"|\bnicht\b|\bkein(?:e|en|em|er)?\b"  # de
    r"|\bne\b.{0,24}?\bpas\b|\bn'\w"       # fr
    r"|\bno\s+(?:funciona|está|es|pasa|pasó)\b|\btodavía no\b"  # es
    r"|\bnão\b"                            # pt
    r"|\bне\b|\bнет\b"                     # ru
    r"|不|没|未能|无法"                      # zh
    r"|ない|ません|なかった|できない"           # ja
    r"|\bلا\b|\bلم\b|\bليس\b)",             # ar
    _re.IGNORECASE)

#: Negation-of-a-negative is still hype ("no errors", "senza errori",
#: "keine Fehler"): these override the guard.
_NEGATED_NEGATIVE_RE = _re.compile(
    r"(?:no|without|zero|senza|sans|sin|sem|keine?|без|没有|なし|بدون|بلا)"
    r"\s*(?:known\s+)?"
    r"(?:errors?|issues?|bugs?|failures?|problems?"
    r"|errori|problemi|erreurs?|problèmes?|errores?|problemas?"
    r"|fehler|probleme|ошибок|проблем|错误|问题|エラー|問題|أخطاء|مشاكل)",
    _re.IGNORECASE)


def _looks_negated(text: str) -> bool:
    """True when the claim contains a real negation (honest failure report),
    excluding negation-of-a-negative forms that remain hype."""
    if not _NEGATION_RE.search(text):
        return False
    stripped = _NEGATED_NEGATIVE_RE.sub("", text)
    return bool(_NEGATION_RE.search(stripped))


#: Reported-speech markers: "the vendor CLAIMS it works" is a legitimate fact
#: about someone else's claim, not our self-claim. The attribution marker is
#: nearly invisible to e5 (same finding as negation) → deterministic guard.
_REPORTED_RE = _re.compile(
    r"(?:\bclaims?\b|\bsays?\b|\bsaid\b|\breports?\b|\bstated?\b"
    r"|\baccording to\b"
    r"|\bdice(?:va)?\s+che\b|\bdicono\s+che\b|\bsostiene\b|\bafferma\b"
    r"|\bsagt\b|\bbehauptet\b|\blaut\b"
    r"|\baffirme\b|\bdit\s+que\b|\bselon\b"
    r"|\bdice\s+que\b|\bafirma\b|\bsegún\b"
    r"|\bdiz\s+que\b|\bsegundo\b"
    r"|\bутверждает\b|\bговорит\b|\bпо\s+словам\b"
    r"|声称|表示|据说|说过?他?们?|によると|と主張|と言って"
    r"|\bيدعي\b|\bيقول\b|\bحسب\b)",
    _re.IGNORECASE)


def _looks_reported(text: str) -> bool:
    """True when the claim is ATTRIBUTED to someone else (reported speech)."""
    return bool(_REPORTED_RE.search(text))

_EXEMPLAR_SET = frozenset(EXEMPLARS)
_ANCHOR_SET = frozenset(ANCHORS)

_MATRICES: dict[str, np.ndarray] | None = None
_MATRICES_LOCK = threading.Lock()


def _is_exemplar_text(t: str) -> bool:
    """True se ``t`` è un esemplare HYPE (al netto del prefisso e5)."""
    bare = t.removeprefix("passage: ").removeprefix("query: ")
    return bare in _EXEMPLAR_SET


def _is_anchor_text(t: str) -> bool:
    """True se ``t`` è un'àncora fattuale (al netto del prefisso e5)."""
    bare = t.removeprefix("passage: ").removeprefix("query: ")
    return bare in _ANCHOR_SET


def _active_model() -> str:
    from .config import CONFIG
    return CONFIG.embedding_model


def _default_encode():
    from . import embedding
    return embedding.encode


def _prefixes() -> tuple[str, str]:
    """(query_prefix, passage_prefix) per il modello attivo — replica il
    gate e5 di ``embedding.as_query/as_passage`` ma sul modello visto da
    QUESTO detector (testabilità: _active_model è patchabile)."""
    if "e5" in _active_model().lower():
        return "query: ", "passage: "
    return "", ""


def _thresholds() -> tuple[float, float] | None:
    """Soglie effettive, o None se il detector deve disarmarsi.

    Famiglia e5 -> default calibrati. Altro encoder -> SOLO se l'operatore ha
    fissato le soglie via env (ha ricalibrato); altrimenti None (le soglie di
    un modello non si trasferiscono a un altro — misurato: qwen3 assoluto
    0.825 vs e5 0.975 sullo stesso dataset)."""
    t_hype = os.environ.get("ENGRAM_L1_SEMANTIC_T_HYPE", "").strip()
    t_delta = os.environ.get("ENGRAM_L1_SEMANTIC_T_DELTA", "").strip()
    if t_hype and t_delta:
        try:
            return float(t_hype), float(t_delta)
        except ValueError:
            return None
    if "e5" in _active_model().lower():
        return _DEFAULT_T_HYPE, _DEFAULT_T_DELTA
    return None


def _matrices(encode) -> dict[str, np.ndarray]:
    """Esemplari/àncore encodate una volta (lazy, thread-safe)."""
    global _MATRICES
    if _MATRICES is None:
        with _MATRICES_LOCK:
            if _MATRICES is None:
                _, ppre = _prefixes()
                ex = np.asarray(encode([ppre + e for e in EXEMPLARS]),
                                dtype=np.float32)
                an = np.asarray(encode([ppre + a for a in ANCHORS]),
                                dtype=np.float32)
                _MATRICES = {"exemplars": ex, "anchors": an}
    return _MATRICES


def _reset_matrices_for_tests() -> None:
    global _MATRICES
    with _MATRICES_LOCK:
        _MATRICES = None


def detect_semantic_selfclaim(
    proposition: str, verified_by: list[str] | None, *,
    _encode=None,
) -> dict[str, Any] | None:
    """Dual-check semantico multilingue. Ritorna il warning L1.20 o None.

    Mai un'eccezione: qualsiasi errore (encoder giù, delegate-only a freddo,
    modello non calibrato) disarma il detector — downgrade-only observability,
    identico contratto fail-open del resto della famiglia L1.
    """
    if os.environ.get("ENGRAM_L1_SEMANTIC", "").strip().lower() in (
            "0", "false", "no", "off"):
        return None
    if verified_by:  # una claim con evidenza è legittima
        return None
    if proposition.rstrip().endswith(_QUESTION_MARKS):
        return None  # una domanda non è mai una self-claim (review held-out FP)
    if _looks_negated(proposition):
        return None  # ammissione di fallimento = onestà, mai quarantena
    if _looks_reported(proposition):
        return None  # claim ALTRUI riportata = fatto legittimo su chi la fa
    thresholds = _thresholds()
    if thresholds is None:
        return None
    t_hype, t_delta = thresholds
    try:
        encode = _encode if _encode is not None else _default_encode()
        mats = _matrices(encode)
        qpre, _ = _prefixes()
        vec = np.asarray(encode(qpre + proposition), dtype=np.float32)
        hype_scores = mats["exemplars"] @ vec
        score = float(hype_scores.max())
        delta = score - float((mats["anchors"] @ vec).max())
    except Exception:  # noqa: BLE001 — fail-open by contract
        return None
    if score >= t_hype and delta >= t_delta:
        matched = EXEMPLARS[int(hype_scores.argmax())]
        return {
            "layer": "L1.20",
            "reason": (
                "semantic self-claim (multilingual): the statement is "
                f"hype-shaped (cos {score:.3f} vs exemplar '{matched}', "
                f"delta over factual {delta:+.3f}) and carries no evidence ref"
            ),
            "score": round(score, 3),
            "delta": round(delta, 3),
            "matched_exemplar": matched,
        }
    return None
