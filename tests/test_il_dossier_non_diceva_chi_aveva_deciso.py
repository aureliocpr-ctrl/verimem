"""Il dossier riportava un pavimento che non era quello che aveva deciso.

FINDING DI ws4, misurato e consegnato senza cura::

    min_relevance=None (default) -> abstained=False  floor RIPORTATO 0.872
                                    servito con relevance 0.8337
    min_relevance=0.872 (a mano) -> abstained=True   n_facts=0

**Copiare il numero che il prodotto ti ha appena dato cambia la risposta.**

La causa (client.py:1069-1076): con ``auto`` la decisione passa al CROSS-ENCODER
(``ce_gate=True``) e il float serve solo da riferimento; con un float esplicito
il ce_gate è spento e a filtrare è il coseno.

⚠️ LA LOGICA NON È SBAGLIATA e non la tocco: il CE è più accurato del coseno,
quindi lasciargli l'ultima parola è la scelta giusta — e ws4 lo ha misurato
(«dimezza i falsi silenzi rispetto al pavimento numerico»). Il difetto è che il
dossier riporta come `min_relevance` un numero che NON è la soglia che ha
deciso, e lo mette accanto a un `relevance` più basso. Chi legge conclude una
delle due cose sbagliate: «il filtro è rotto» oppure «il numero è sbagliato».

🔑 È LA STESSA CLASSE della cura sul ranking degradato: un numero che ha la
forma di una misura e significa un'altra cosa. Lì lo `0.0` del fallback keyword
non era «nessuna somiglianza» ma «somiglianza non misurata»; qui lo `0.872` non
è «la soglia applicata» ma «la soglia che si sarebbe applicata col coseno».

⚠️ NON HO RIPRODOTTO IL CASO LIMITE DI ws4 (serve un fatto la cui relevance
stia FRA il verdetto del CE e il pavimento del coseno; sul mio banco i fatti
stanno a 0.73, ben sotto). Curo ciò che ho verificato io: il dossier non dice
chi ha deciso. Il caso di ws4 è la manifestazione visibile di quel silenzio.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def listino(tmp_path):
    m = Memory(str(tmp_path / "listino.db"))
    for t in ["La prova gratuita dura 14 giorni.",
              "Il piano Annuale costa 1200 euro l'anno.",
              "L'assistenza risponde entro due giorni lavorativi."]:
        m.add(t, topic="listino")
    return m


def test_col_pavimento_auto_il_dossier_dice_che_decide_il_cross_encoder(listino):
    """IL CUORE: con `auto` il numero riportato è un RIFERIMENTO, non la
    soglia applicata — e finora niente nel dossier lo diceva."""
    rep = listino.explain("Quale database usa il cluster?", k=3,
                          min_relevance="auto")
    assert rep.get("floor_applied_by") == "cross_encoder", sorted(rep)


def test_con_un_numero_esplicito_decide_il_coseno(listino):
    """L'altro verso: un float è il pavimento bi-encoder di chi chiama, e
    viene onorato come tale."""
    rep = listino.explain("Quale database usa il cluster?", k=3,
                          min_relevance=0.9)
    assert rep.get("floor_applied_by") == "cosine"
    assert rep.get("min_relevance") == 0.9


@pytest.mark.parametrize("env,atteso", [
    ("auto", "cross_encoder"),
    ("0.85", "cosine"),
    ("off", "cosine"),
])
def test_il_DEFAULT_lo_dice_secondo_l_ambiente(listino, monkeypatch, env, atteso):
    """IL CASO CHE ws4 HA MISURATO era il default, non `auto` esplicito: il
    valore arriva da `ENGRAM_MIN_RELEVANCE`, e chi legge il dossier non ha
    modo di sapere quale delle due strade sia stata presa."""
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", env)
    rep = listino.explain("Quale database usa il cluster?", k=3)
    assert rep.get("floor_applied_by") == atteso, (
        f"ENGRAM_MIN_RELEVANCE={env}: {rep.get('floor_applied_by')}")


def test_il_numero_riportato_resta_quello_di_prima(listino):
    """IL PRESIDIO: la cura AGGIUNGE un campo e non cambia né la logica né il
    valore che il dossier riportava — chi già lo legge non si accorge di
    nulla."""
    rep = listino.explain("Quale database usa il cluster?", k=3,
                          min_relevance="auto")
    assert isinstance(rep.get("min_relevance"), float)
    assert rep.get("min_relevance") > 0.0
