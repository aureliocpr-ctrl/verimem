"""`verimem doctor` must not report a moat that judged nothing as simply "ON".

The moat-judge check answers "is a grounding judge installed?" and prints
"the grounding moat is ON with no llm". True of the JUDGE — and read by an
operator as "my store is protected". Measured on the real corpus 2026-07-28:
the judge was installed and 0 of 6414 stored facts had ever been judged,
because the moat only runs on writes that carry a source.

An installed judge with an unjudged corpus is exactly the state worth flagging:
nothing is broken, and nothing is being checked either. doctor is the command
people run to find out whether their install is healthy, so it is where that
belongs.

Cheap by construction: doctor promises to finish in ~2s and does presence
checks only, so this adds two SQL COUNTs over a column already persisted on
every write — no model load, no judge call.
"""
from __future__ import annotations

from pathlib import Path


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    """Point the config at a temp corpus BEFORE anything reads it.

    Order matters and cost me a red run: importing Memory first resolves
    verimem.config against the operator's real data dir, and doctor then reports
    on that store instead of the test's.
    """
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(tmp_path))
    (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
    return tmp_path / "semantic" / "semantic.db"


def _run():
    from verimem.doctor import run_doctor
    return run_doctor()


def _find(report, name):
    rows = report.get("checks") if isinstance(report, dict) else report
    for row in rows or []:
        got = row.get("name") if isinstance(row, dict) else getattr(row, "name", "")
        if got == name:
            return row
    return None


def _text(row) -> str:
    if row is None:
        return ""
    if isinstance(row, dict):
        return " ".join(str(row.get(k, "")) for k in ("detail", "fix", "status"))
    return " ".join(str(getattr(row, k, "")) for k in ("detail", "fix", "status"))


def test_doctor_flags_a_corpus_the_moat_never_judged(monkeypatch, tmp_path):
    db = _isolate(monkeypatch, tmp_path)
    from verimem.client import Memory
    m = Memory(db)
    m.add("The staging cluster was rebuilt on Tuesday.", topic="ops")
    m.add("Payroll exports moved to the new bucket.", topic="ops")
    row = _find(_run(), "moat-judge")
    assert row is not None, "the moat-judge check must still be reported"
    body = _text(row).lower()
    assert "0 of" in body and "judged" in body, (
        f"doctor must say how much of the corpus was judged, got: {body}")


def test_doctor_says_so_when_writes_were_judged(monkeypatch, tmp_path):
    db = _isolate(monkeypatch, tmp_path)
    from verimem.client import Memory
    m = Memory(db)
    m.add("Rex is a labrador.", topic="pets",
          source="The kennel registry lists Rex as a labrador.")
    row = _find(_run(), "moat-judge")
    body = _text(row).lower()
    assert "judged" in body, body


def test_an_empty_store_does_not_trip_the_warning(monkeypatch, tmp_path):
    """Nothing stored yet is not an unjudged corpus — a fresh install must not
    be told it has a problem."""
    _isolate(monkeypatch, tmp_path)
    row = _find(_run(), "moat-judge")
    assert row is not None
    body = _text(row).lower()
    assert "0 of 0" not in body


def _is_ok(row) -> bool:
    """doctor's statuses are lowercase ('ok' / 'warn' / 'fail').

    Comparing against "OK" made both tests below pass while checking nothing —
    the assertion was true for every possible status. Read the value, don't
    assume its shape.
    """
    got = row.get("status") if isinstance(row, dict) else getattr(row, "status", "")
    return str(got).strip().lower() == "ok"


def test_a_barely_judged_corpus_is_not_reported_as_healthy(monkeypatch, tmp_path):
    """The alarm fired only at EXACTLY zero: one judged write out of thousands
    flipped the check to OK with the ratio buried in prose. Measured on the real
    store the same evening — 3 of 4723 judged, status OK. An operator (or any
    automation keying on status) reads green while the corpus is ungated."""
    db = _isolate(monkeypatch, tmp_path)
    from verimem.client import Memory
    m = Memory(db)
    m.add("Rex is a labrador.", topic="pets",
          source="The kennel registry lists Rex as a labrador.")   # judged
    for i, text in enumerate([
            "The staging cluster was rebuilt on Tuesday.",
            "Payroll exports moved to the new bucket.",
            "Nadia joined the platform team in March.",
            "The invoice run now starts at 03:00.",
    ]):
        m.add(text, topic=f"ops/{i}")                              # unjudged
    row = _find(_run(), "moat-judge")
    assert not _is_ok(row), (
        f"1 judged of 5 must not read as healthy: {_text(row)}")


def test_a_store_it_cannot_read_is_not_reported_as_ON(monkeypatch, tmp_path):
    """The check exists to surface an unjudged corpus. Swallowing a read failure
    into zero made it print the reassuring "the grounding moat is ON" exactly
    when it could not look — a broken or schema-drifted store then looks
    identical to a healthy empty one."""
    _isolate(monkeypatch, tmp_path)
    db = tmp_path / "semantic" / "semantic.db"
    db.write_bytes(b"this is not a sqlite database at all")
    row = _find(_run(), "moat-judge")
    assert row is not None
    body = _text(row).lower()
    assert not _is_ok(row) or "could not" in body or "unreadable" in body, (
        f"an unreadable store must not report the moat as ON: {_text(row)}")
