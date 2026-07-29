"""I tab della console si dichiarano tab e non lo sono, per uno screen reader.

Ispezionato dal vivo il 2026-07-30 sulla console (`verimem console`, /ui):

    tablist: 1     tabpanel: 0
    4 x role="tab"  ->  aria-selected: null, aria-controls: null, tabindex: null

Un `role="tab"` senza `aria-selected` non dice quale scheda è attiva; senza
`aria-controls` non dice cosa apre; senza `role="tabpanel"` sul contenitore la
scheda non è associata al suo contenuto. Chi naviga con uno screen reader sente
"tab, Knowledge graph, tab, Search & ask…" e non sa dove si trova.

Le sezioni ESISTONO già (`id="tab-graph"`, `tab-search`, `tab-blocked`,
`tab-layers`) e il JS le mostra togglando una classe CSS: manca solo il
collegamento dichiarato.

E la pratica corretta è già nel repo — `templates/episodes.html` e
`templates/skills.html` scrivono `aria-selected="true"/"false"` sui loro tab.
Stessa forma di tutto il resto di questa sessione: la cosa giusta esiste, e non è
applicata su una delle superfici.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

HTML = Path(__file__).resolve().parents[1] / "verimem" / "webui" / "index.html"
JS = Path(__file__).resolve().parents[1] / "verimem" / "webui" / "app.js"


def _tab_buttons(html: str) -> list[str]:
    return re.findall(r"<button[^>]*role=\"tab\"[^>]*>", html)


def test_every_tab_declares_whether_it_is_selected():
    html = HTML.read_text(encoding="utf-8")
    tabs = _tab_buttons(html)
    assert tabs, "nessun role=tab trovato: il markup è cambiato"
    senza = [t for t in tabs if "aria-selected" not in t]
    assert not senza, (
        f"{len(senza)} tab su {len(tabs)} non dicono se sono attivi:\n"
        + "\n".join(senza)
    )


def test_every_tab_names_the_panel_it_opens():
    html = HTML.read_text(encoding="utf-8")
    tabs = _tab_buttons(html)
    senza = [t for t in tabs if "aria-controls" not in t]
    assert not senza, (
        f"{len(senza)} tab non dichiarano cosa aprono:\n" + "\n".join(senza)
    )


def test_the_named_panels_exist_and_are_tabpanels():
    html = HTML.read_text(encoding="utf-8")
    for t in _tab_buttons(html):
        m = re.search(r"aria-controls=\"([^\"]+)\"", t)
        assert m, t
        target = m.group(1)
        # la section esiste...
        sec = re.search(rf"<section[^>]*id=\"{re.escape(target)}\"[^>]*>", html)
        assert sec, f"aria-controls={target!r} non punta a nessuna section"
        # ...ed è dichiarata come pannello di tab
        assert 'role="tabpanel"' in sec.group(0), (
            f"la section {target} non è un tabpanel: {sec.group(0)}"
        )


def test_exactly_one_tab_is_selected_at_load():
    html = HTML.read_text(encoding="utf-8")
    tabs = _tab_buttons(html)
    attivi = [t for t in tabs if 'aria-selected="true"' in t]
    assert len(attivi) == 1, f"{len(attivi)} tab attivi al caricamento: {attivi}"


def test_the_switch_updates_aria_and_not_only_the_css_class():
    """Il markup statico può essere giusto e la UI restare muta: al click il JS
    togglava solo la classe `on`, quindi dopo la prima interazione
    aria-selected sarebbe rimasto sul tab sbagliato."""
    js = JS.read_text(encoding="utf-8")
    assert "aria-selected" in js, (
        "il gestore dei tab non aggiorna aria-selected: dopo un click lo stato "
        "dichiarato e quello reale divergono"
    )


@pytest.mark.parametrize("f", ["episodes.html", "skills.html"])
def test_the_other_templates_stay_correct(f):
    """Non-regressione sulle superfici che già lo facevano bene."""
    p = Path(__file__).resolve().parents[1] / "verimem" / "templates" / f
    if not p.exists():
        pytest.skip(f"{f} assente")
    html = p.read_text(encoding="utf-8")
    tabs = _tab_buttons(html)
    if tabs:
        assert all("aria-selected" in t for t in tabs), f
