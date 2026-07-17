"""TDD — L1.10 works-detector: un bare `test:` prefix NON deve contare come
evidenza runtime (scan 68-Opus P2). Bug: `_has_runtime_evidence` accettava
qualunque `test:` col solo prefisso, mentre `pytest:`/`bash:`/`cmd:` richiedono
un marker di ESITO. `test:` e' usato pervasivamente come provenance-fixture
(`test:seed:...`) che NON prova che una claim "funziona" sia vera -> bucava il
gate A2 ANTI-HALL. Fix: `test:` richiede pass/ok/exit0/green (come pytest:)."""
from __future__ import annotations

from verimem.l1_works_detector import detect_unsupported_works_claim


def test_bare_test_fixture_provenance_does_not_suppress_works_warning():
    # test:seed:... = provenance-fixture, NON evidenza-che-funziona.
    out = detect_unsupported_works_claim(
        proposition="Il sistema funziona correttamente",
        verified_by=["test:seed:cluster-foo:3"],
    )
    assert out is not None, (
        "una claim 'funziona' con sola provenance-fixture (test:seed:...) "
        "deve ANCORA emettere il warning A2: non e' evidenza runtime")


def test_test_prefix_with_pass_outcome_still_suppresses():
    # test:..._PASS = esito reale -> resta accettato come evidenza.
    out = detect_unsupported_works_claim(
        proposition="Funziona", verified_by=["test:test_main_PASS"],
    )
    assert out is None, "test:..._PASS (esito reale) deve sopprimere il warning"


def test_runtime_and_smoke_bare_refs_still_suppress():
    # Regressione: runtime:/smoke_test: restano evidenza valida (contratto pinnato).
    assert detect_unsupported_works_claim(
        proposition="Tutto risolto", verified_by=["runtime:observed_5_iterations"],
    ) is None
    assert detect_unsupported_works_claim(
        proposition="Build ok", verified_by=["smoke_test:full_pipeline:PASS"],
    ) is None


def test_substring_outcome_in_word_is_not_evidence():
    # AUDIT agente: 'pass' come SUBSTRING (compass/bypass) o 'green' (greenfield)
    # NON deve contare come esito -> altrimenti ri-apre il buco che il fix chiudeva.
    for ref in ("test:compass-cluster-7", "test:bypass-check",
                "test:greenfield-init", "test:passenger-list"):
        out = detect_unsupported_works_claim(
            proposition="Il sistema funziona", verified_by=[ref])
        assert out is not None, (
            f"{ref!r}: un token che CONTIENE 'pass'/'green' non e' un esito "
            "di test -> il warning deve restare")


def test_real_outcome_tokens_still_suppress():
    # Gli esiti VERI (token delimitato) devono ancora sopprimere.
    for ref in ("test:test_main_PASS", "test:full:pass", "test:run:exit0",
                "test:ci:green", "test:suite_passing"):
        assert detect_unsupported_works_claim(
            proposition="Funziona", verified_by=[ref]) is None, (
            f"{ref!r}: esito reale, deve sopprimere il warning")


def test_sibling_prefixes_also_reject_substring_outcomes():
    # AUDIT round 2 (agente empirico): lo STESSO buco substring di 'test:' era
    # ancora aperto in pytest:/bash:/cmd: -> 'compass'/'block_okay'/'_okra'/
    # 'nonexit0fail' NON sono esiti reali e NON devono contare come evidenza.
    for ref in ("pytest:compass-suite", "pytest:bypass-x", "bash:block_okay",
                "bash:_okra_soup", "cmd:nonexit0fail"):
        out = detect_unsupported_works_claim(
            proposition="Il sistema funziona", verified_by=[ref])
        assert out is not None, (
            f"{ref!r}: substring (non token) non e' un esito -> warning resta")


def test_sibling_prefixes_real_outcomes_still_suppress():
    # Gli esiti VERI sui prefissi gemelli devono ancora sopprimere.
    for ref in ("pytest:test_main_PASS", "bash:python_run:exit0:5",
                "cmd:deploy_status:exit0", "pytest:suite_passing",
                "bash:checks:ok"):
        assert detect_unsupported_works_claim(
            proposition="Funziona", verified_by=[ref]) is None, (
            f"{ref!r}: esito reale, deve sopprimere")
