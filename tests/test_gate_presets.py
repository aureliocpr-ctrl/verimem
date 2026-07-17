"""Gate presets: strict / balanced / permissive (packaging, adozione Grok r2).

I parametri del gate esistono da mesi (validate off/fast/full, gate_mode
downgrade/reject, ground L4) ma richiedono di conoscerli: i preset li
confezionano in 3 modalità dichiarative sul costruttore. ``balanced`` =
default = comportamento storico byte-identico; ogni parametro esplicito
per-call vince sempre sul preset.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

#: un'asserzione di stato-lavoro non supportata: il caso che L1 quarantena
_UNSUPPORTED = "the deployment works and is verified in production"


def test_balanced_is_the_historic_default(tmp_path):
    default = Memory(tmp_path / "a.db")
    balanced = Memory(tmp_path / "b.db", preset="balanced")
    r1 = default.add(_UNSUPPORTED)
    r2 = balanced.add(_UNSUPPORTED)
    # storico: downgrade -> stored ma quarantined
    assert r1["stored"] is True and r1["status"] == "quarantined"
    assert r2["stored"] is True and r2["status"] == "quarantined"


class _LowScoreJudge:
    """Grounding judge stub: qualsiasi (source, fact) → score 5/100 = bocciato.
    Formato ``SCORE: N`` — è quello che ``_SCORE_RE`` parsa; una risposta senza
    marker cade al 50.0 neutro (verificato) e il gate non boccerebbe."""

    def complete(self, system, messages, **kw):
        class R:
            text = "SCORE: 5"
            total_tokens = 1
        return R()


def test_strict_activates_grounding_and_rejects_unsupported_by_source(tmp_path):
    """La semantica VERA di strict: attiva L4 (ground=True) e rifiuta
    (gate_mode=reject) quando la fonte NON supporta il fatto. Gli hit L1
    lessicali restano downgrade anche in strict — by design del gate
    (FP-safety: un falso positivo keyword non deve mai perdere dati)."""
    judge = _LowScoreJudge()
    src = "meeting notes: we discussed the weather"
    claim = "the contract was signed by both parties"

    strict = Memory(tmp_path / "s.db", preset="strict", grounding_llm=judge)
    r = strict.add(claim, source=src)
    assert r["stored"] is False and r["status"] == "rejected", (
        "strict: fonte che non supporta il fatto -> rifiuto, non quarantena"
    )

    balanced = Memory(tmp_path / "b.db", preset="balanced", grounding_llm=judge)
    r2 = balanced.add(claim, source=src)
    assert r2["stored"] is True, (
        "balanced: L4 non attivo di default -> comportamento storico"
    )

    # L1 unsupported resta quarantined ANCHE in strict (mai rejected):
    r3 = strict.add(_UNSUPPORTED)
    assert r3["stored"] is True and r3["status"] == "quarantined"


def test_permissive_stores_without_quarantine(tmp_path):
    m = Memory(tmp_path / "m.db", preset="permissive")
    r = m.add(_UNSUPPORTED)
    assert r["stored"] is True
    assert r["status"] != "quarantined", (
        "permissive = contesti creativi/low-stakes: niente quarantena L1"
    )


def test_per_call_override_beats_preset(tmp_path):
    m = Memory(tmp_path / "m.db", preset="strict")
    r = m.add(_UNSUPPORTED, gate_mode="downgrade", validate="fast")
    assert r["stored"] is True and r["status"] == "quarantined", (
        "il parametro esplicito per-call vince sul preset"
    )


def test_unknown_preset_raises(tmp_path):
    with pytest.raises(ValueError, match="preset"):
        Memory(tmp_path / "m.db", preset="yolo")
