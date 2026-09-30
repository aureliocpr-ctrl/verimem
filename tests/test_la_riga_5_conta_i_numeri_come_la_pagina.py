"""La riga 5 del tabellone conta i numeri della pagina come la pagina li mostra.

DA DOVE VIENE (30/09, decisione del lead delle 22:02). La prova di accettazione della riga 5
contava come «generati» solo i numeri dentro blocchi `<!-- vetrina:inizio … -->`, che nel
README non esistono (0), mentre i numeri che il registro rende e `--check-docs` confronta con
l'artefatto stanno fra i marcatori g4 (`<!-- g4:<id> -->…<!-- /g4 -->`, #154). Due convenzioni
per la stessa promessa: la riga 5 non poteva diventare verde nemmeno coi numeri generati.
Contava anche i numeri dentro i commenti HTML, che PyPI non mostra: la promessa parla della
pagina che l'utente legge.

La prova di accettazione non gira nel pytest del repo (si ferma se `verimem` viene
dall'albero), quindi la sua regola sta in una funzione pura, `numeri_scritti_a_mano`, e
queste celle la caricano dal file per percorso: un posto solo per la regola.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_FILE = Path(__file__).resolve().parents[1] / "accettazione" / "test_riga_5_i_numeri_in_vetrina_sono_veri.py"


def _riga_5():
    spec = importlib.util.spec_from_file_location("riga_5", _FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_un_numero_fra_i_marcatori_g4_e_generato_non_scritto_a_mano():
    pagina = "matrix: <!-- g4:matrix -->5.4% escape (106/112 quarantined)<!-- /g4 --> today"
    tutti, fuori = _riga_5().numeri_scritti_a_mano(pagina)
    assert tutti == ["5.4%", "106/112"], tutti
    assert fuori == [], f"numeri resi dal registro contati come scritti a mano: {fuori}"


def test_un_numero_dentro_un_commento_html_non_e_sulla_pagina():
    pagina = "intro\n<!-- nota interna: 16/48 stantii il 21/09 -->\nfine"
    tutti, fuori = _riga_5().numeri_scritti_a_mano(pagina)
    assert (tutti, fuori) == ([], []), (tutti, fuori)


def test_CONTROLLO_un_numero_scritto_a_mano_resta_contato():
    pagina = "il giudice ammette **8/10** e sbaglia il 12% <!-- g4:x -->0.87<!-- /g4 -->"
    tutti, fuori = _riga_5().numeri_scritti_a_mano(pagina)
    assert fuori == ["12%", "8/10"] or sorted(fuori) == ["12%", "8/10"], fuori
