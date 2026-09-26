"""Il README deve puntare a `docs/LIMITS.md`, e i limiti non devono divergere.

`docs/LIMITS.md:3` promette: «The README keeps one line and points here». Il
09/09/2026 quella frase era **falsa**: `grep -n LIMITS README.md` non trovava
niente. Un documento che dichiara come lo si raggiunge, e non è raggiungibile,
è la forma più silenziosa di limite non pagato — chi legge il README crede di
aver letto i limiti.

Qui il puntatore diventa un presidio invece di una promessa.

    python -m pytest tests/test_i_limiti_sono_puntati_dal_readme.py -q
"""
from __future__ import annotations

import pathlib
import re

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
README = RADICE / "README.md"
LIMITS = RADICE / "docs" / "LIMITS.md"


def _nomi_dei_limiti(testo: str) -> set[str]:
    """I limiti si nominano `**Nome**:` — la forma usata da entrambi i file."""
    return set(re.findall(r"\*\*([A-Z][a-z]+)\*\*:", testo))


def test_il_readme_punta_a_limits():
    testo = README.read_text(encoding="utf-8")
    assert "docs/LIMITS.md" in testo, (
        "docs/LIMITS.md dichiara «The README keeps one line and points here»: "
        "se il README non ci punta, quella riga è una promessa non mantenuta e "
        "chi legge crede di aver letto i limiti."
    )


def test_il_puntatore_e_un_link_cliccabile_e_non_una_menzione():
    """Un percorso nominato in mezzo a un paragrafo non porta da nessuna parte."""
    testo = README.read_text(encoding="utf-8")
    assert re.search(r"\]\(https?://[^)]*docs/LIMITS\.md\)", testo), (
        "il README nomina LIMITS.md ma non come link: un lettore su PyPI non ci arriva"
    )


def test_limits_esiste_e_dichiara_il_patto_col_readme():
    """Se un giorno LIMITS.md smette di promettere il puntatore, questo test va tolto
    insieme alla promessa — non lasciato a presidiare una regola che non c'è più."""
    testo = LIMITS.read_text(encoding="utf-8")
    assert "README" in testo, "LIMITS.md non nomina più il README: rivedi questo presidio"


@pytest.mark.xfail(
    strict=True,
    reason="il limite **Order** (il self-claim ammesso dopo una frase vera di terzi, "
           "7 formulazioni su 7, misurato il 2026-09-04) è in docs/LIMITS.md e NON nel "
           "README. La cura è di ws7 Product Owner (i 57 claim del README): quando entra, questo "
           "test diventa verde e va tolto l'xfail.",
)
def test_ogni_limite_di_limits_e_nominato_anche_nel_readme():
    mancanti = _nomi_dei_limiti(LIMITS.read_text(encoding="utf-8")) - _nomi_dei_limiti(
        README.read_text(encoding="utf-8")
    )
    assert not mancanti, f"limiti presenti in LIMITS.md e assenti dal README: {sorted(mancanti)}"
