"""G10 (RELEASE_GATE): the gate's span selection must work beyond a-z.

Found by the 2026-07-04 multilingual smoke: `_SPAN_WORD = [a-z0-9]+` produced
ZERO tokens on Russian/Chinese, so `select_relevant_span` degenerated to a
blind prefix — the gate then judged facts against a potentially irrelevant
window for every non-Latin language (silent over-rejection). Fix: Unicode
word tokens + CJK character-bigrams (Chinese/Japanese have no spaces, so
word-level overlap carries no signal there).

The RU/ZH cases here share ZERO Latin tokens between fact and source (the
first draft leaked "Python" into both, which the old a-z regex could match —
that would test nothing).
"""
from __future__ import annotations

from engram.grounding_gate import select_relevant_span


def _budgeted(source_lines: list[str], fact: str, budget: int = 120) -> str:
    return select_relevant_span("\n".join(source_lines), fact, budget=budget)


def test_russian_relevant_line_is_selected_not_prefix() -> None:
    filler = "Сегодня хорошая погода и мы говорили о разных вещах"
    relevant = "Пользователь сказал: мой любимый язык программирования Питон"
    span = _budgeted([filler, filler, relevant],
                     "Любимый язык программирования пользователя Питон")
    assert "Питон" in span and "любимый" in span.lower()


def test_chinese_relevant_line_is_selected_via_char_bigrams() -> None:
    filler = "今天天气很好我们聊了很多别的事情"
    relevant = "用户说他最喜欢的城市是北京经常回去"
    span = _budgeted([filler, filler, relevant], "用户最喜欢的城市是北京",
                     budget=40)
    assert "北京" in span


def test_english_behaviour_unchanged() -> None:
    filler = "the weather was nice and we chatted about many things"
    relevant = "the user said their favorite language is Python"
    span = _budgeted([filler, filler, relevant],
                     "user's favorite language is Python")
    assert "favorite language" in span


def test_finnish_diacritics_tokenize() -> None:
    filler = "Puhuimme monista muista asioista tänään pitkään"
    relevant = "Käyttäjä sanoi että hänen lempikaupunkinsa on Helsinki"
    span = _budgeted([filler, filler, relevant],
                     "Käyttäjän lempikaupunki on Helsinki")
    assert "Helsinki" in span and "lempikaupunki" in span
