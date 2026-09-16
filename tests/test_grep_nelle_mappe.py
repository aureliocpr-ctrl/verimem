"""Il righello che trova gli zeri finti nella mappa deve mordere — e TACERE dove non deve.

Un `|` in un pattern di `grep` senza `-E` è letterale: `grep -c "a|b"` cerca la
stringa «a|b», non trova niente, e la conclusione «nessuna occorrenza» sembra
misurata. Reperto di ws4 ML, 09/09/2026.

La metà che decide se il presidio verrà usato è l'altra: i casi in cui **NON**
deve suonare. Sui 403 documenti veri della mappa il primo criterio dava 8
candidati e i difetti veri erano 3 — sbagliava CONTRO chi lo usa, che è il modo
più rapido di far ignorare un controllo. Le tre classi che lo salvano:

  * `\\|` — in BRE (cioè senza `-E`) è l'alternanza CORRETTA;
  * `^|` e `a|` — un ramo vuoto: il `|` è la barra letterale che qualcuno cerca
    davvero, e aggiungere `-E` non ripara, ROMPE (misurato: 2 righe contro 3);
  * `\\|` dentro una riga di tabella markdown — lì `\\|` è l'escape del
    documento, quindi non si può decidere meccanicamente: AMBIGUO, lo legge una
    persona.

    python -m pytest tests/test_grep_nelle_mappe.py -q
"""
from __future__ import annotations

import importlib.util
import pathlib

RADICE = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "grep_nelle_mappe", RADICE / "scripts" / "grep_nelle_mappe.py"
)
gnm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gnm)


def _una_riga(tmp_path, riga: str) -> dict:
    (tmp_path / "prova.md").write_text(riga + "\n", encoding="utf-8")
    return gnm.cerca(tmp_path)


def test_un_pattern_con_alternative_senza_E_e_un_difetto(tmp_path):
    r = _una_riga(tmp_path, '`grep -c "a|b" README.md`')
    assert len(r["sospetti"]) == 1, r
    assert r["sospetti"][0][2] == "a|b"


def test_con_E_non_suona(tmp_path):
    assert _una_riga(tmp_path, '`grep -cE "a|b" README.md`')["sospetti"] == []


def test_la_pipe_della_shell_non_e_un_difetto(tmp_path):
    """Se suonasse qui, nessuno userebbe più questo controllo."""
    assert _una_riga(tmp_path, '`grep -n "solo" f | head -3`')["sospetti"] == []


def test_bre_con_barra_escapata_e_corretto(tmp_path):
    """`grep "a\\|b"` senza -E è alternanza VALIDA: accusarlo è un allarme falso."""
    r = _una_riga(tmp_path, '`grep -c "a\\|b" f`')
    assert r["sospetti"] == [], r["sospetti"]
    assert r["ambigui"] == [], "fuori da una tabella non c'è ambiguità"


def test_un_ramo_vuoto_significa_barra_letterale(tmp_path):
    """`^| \\`docs` cerca le righe di tabella: con -E il ramo vuoto matcherebbe TUTTO."""
    assert _una_riga(tmp_path, "`grep -c '^| \\`docs' f`")["sospetti"] == []
    assert _una_riga(tmp_path, "`grep -c 'a|' f`")["sospetti"] == []


def test_dentro_una_tabella_markdown_e_ambiguo_non_rosso(tmp_path):
    """Nel markdown il `|` di una cella si scrive `\\|`: il comando vero potrebbe
    avere la barra nuda. Non si decide meccanicamente."""
    r = _una_riga(tmp_path, '| domanda | `grep -c "a\\|b" f` | **4** |')
    assert r["sospetti"] == []
    assert len(r["ambigui"]) == 1, r


def test_tre_alternative_vere_restano_un_difetto(tmp_path):
    r = _una_riga(tmp_path, '`grep -rn "A|B|C" verimem/`')
    assert len(r["sospetti"]) == 1, r


def test_l_autotest_del_righello_e_verde():
    """IL CONTROLLO POSITIVO in blocco: 15 casi, e il righello esce 0 solo se tutti tornano."""
    assert gnm.autotest() == 0
