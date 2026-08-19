"""Lo span va ridotto in CARATTERI, ma il giudice legge in TOKEN.

`LocalGroundingJudge` promette nel suo docstring «the CE window is 512 tokens»,
e riduce la fonte con un budget in CARATTERI (`focus_budget`, 1500). Le due
unita' coincidono solo sulla prosa: misurato il 2026-08-19 col tokenizzatore
del gate,

    prosa italiana      4.08 caratteri/token   ->  350 token   dentro
    tabella di misure   2.15                   ->  713 token   FUORI
    log applicativo     2.02                   ->  715 token   FUORI
    git diff --stat     1.70                   ->  879 token   FUORI

1500 caratteri stanno in 512 token solo sopra ~2.93 caratteri/token. Sotto, il
cross-encoder tronca con `longest_first`, cioe' DALLA CODA — e su un `git diff`
butta via il 42% dello span dopo che il selettore l'aveva scelto apposta.

Il difetto e' il gemello di quello curato in `select_relevant_span` (il budget
non veniva speso): li' lo span era troppo corto, qui e' troppo lungo per chi
deve leggerlo. Le due cure vanno insieme — allungare gli span senza questa
peggiora il troncamento (segnalato da ws6 il 19/08).
"""
from __future__ import annotations

import pytest

from verimem.local_grounding import LocalGroundingJudge, _resolve_model_dir

MAX_LEN = 512
FONTI_DENSE = {
    "tabella": "\n".join(
        f"riga{i:03d} | {1000 + i * 7} | {i * 3}.{i}% | {i * 11} | {i * 2}.{i}ms | ok"
        for i in range(1, 60)),
    "diff_stat": "\n".join(
        f" verimem/modulo_{i:02d}.py | {i * 3} ++++++++{'+' * (i % 9)}{'-' * (i % 5)}"
        for i in range(1, 60)),
    "log": "\n".join(
        f"2026-08-19T13:{i % 60:02d}:{i % 60:02d}.{i:03d}Z [INFO] req_id=a{i:04x}f "
        f"svc=gate lat_ms={i * 3} status=200" for i in range(1, 40)),
}
PROSA = "\n".join(
    f"La procedura numero {i} descrive la conservazione dei registri contabili "
    f"secondo le regole vigenti nell'ufficio competente della sede centrale."
    for i in range(1, 30))
CLAIM = "Il valore misurato e' 1077 e la percentuale 33.11 per cento."


def _tokenizer():
    d = _resolve_model_dir(None)
    if not (d / "tokenizer_config.json").exists() and not (d / "tokenizer.json").exists():
        pytest.skip(f"tokenizzatore del gate assente in {d}")
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(d))


@pytest.mark.parametrize("nome", sorted(FONTI_DENSE))
def test_su_fonti_dense_lo_span_sta_nella_finestra_del_cross_encoder(nome: str) -> None:
    """Il giudice non deve ricevere piu' di quanto puo' leggere."""
    tok = _tokenizer()
    giudice = LocalGroundingJudge(scorer=lambda batch: [0.0] * len(batch), max_length=MAX_LEN)
    span, _ = giudice.coppia(FONTI_DENSE[nome], CLAIM)
    n = len(tok.encode(span, add_special_tokens=False))
    assert n <= MAX_LEN, (
        f"{nome}: lo span e' {n} token e la finestra ne legge {MAX_LEN} — "
        f"il cross-encoder ne taglia {n - MAX_LEN} dalla coda"
    )


def test_sulla_prosa_lo_span_resta_quello_di_prima() -> None:
    """Il controllo che puo' fallire: la prosa e' gia' sotto la finestra, e la
    cura non deve accorciarla — sarebbe togliere contesto a chi non ne abusa."""
    tok = _tokenizer()
    giudice = LocalGroundingJudge(scorer=lambda batch: [0.0] * len(batch), max_length=MAX_LEN)
    span, _ = giudice.coppia(PROSA, CLAIM)
    n = len(tok.encode(span, add_special_tokens=False))
    assert 300 <= n <= MAX_LEN, f"la prosa dava ~350 token, ora {n}"


def test_la_riduzione_conserva_l_inizio_dello_span() -> None:
    """Tagliare DALLA CODA e' cio' che fa gia' il tokenizzatore. Se dobbiamo
    ridurre, che almeno resti un testo coerente e non una parola a meta'."""
    giudice = LocalGroundingJudge(scorer=lambda batch: [0.0] * len(batch), max_length=MAX_LEN)
    span, fatto = giudice.coppia(FONTI_DENSE["tabella"], CLAIM)
    assert fatto == CLAIM
    assert span.strip(), "lo span non puo' restare vuoto"
    assert not span.endswith("\n"), "niente riga tronca in coda"
