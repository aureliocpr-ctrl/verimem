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


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-31: IL CASO CHE MANCAVA — il pavimento SPENTO.
# Le celle qui sopra presidiano QUALE pavimento decide (cross-encoder con
# `auto`, coseno con un numero, e il default secondo l'ambiente). Nessuna
# chiede cosa dica il campo quando NESSUN pavimento e' in vigore, che e' una
# via legittima e dichiarata (`ENGRAM_MIN_RELEVANCE=off`, docstring di
# `env_floor`: «off/0 keeps the old permissive behaviour»).
# Misurato: vale ancora "cosine". ⇒ Il campo dice QUALE pavimento
# deciderebbe, non che uno ABBIA filtrato — e il participio del nome
# («applied») promette di piu'. Il valore NON e' stato cambiato: chi si dirama
# su queste due stringhe non deve trovarne una terza senza una decisione
# collegiale. Questa cella FISSA il comportamento e lo rende leggibile a chi
# arriva dopo, invece di lasciarlo scoprire come l'ho scoperto io.
# 📌 Chi vuole sapere se un pavimento abbia DAVVERO tagliato legge
# `min_relevance` nella stessa ricevuta.


def test_col_pavimento_SPENTO_il_campo_dice_ancora_coseno(listino):
    """Il comportamento fissato, e la ragione per cui non e' un difetto da
    curare qui: cambiarlo e' una decisione sul CONTRATTO della ricevuta."""
    rep = listino.explain("quanto costa il piano annuale", min_relevance=0.0)
    assert rep.get("floor_applied_by") == "cosine", sorted(rep)
    # ⚠️ LA META' CHE RENDE LEGGIBILE L'ALTRA: il numero accanto dice la
    # verita', ed e' li' che si legge se un pavimento abbia filtrato.
    assert float(rep.get("min_relevance") or 0.0) == 0.0, rep.get("min_relevance")


def test_con_un_pavimento_VERO_il_numero_accanto_lo_dice(listino):
    """⚠️ IL CONTROLLO CHE DEVE POTER FALLIRE: se `min_relevance` valesse zero
    anche con un pavimento in vigore, il rimando della cella qui sopra —
    «guarda il numero» — manderebbe il lettore su un campo che non distingue
    niente."""
    rep = listino.explain("quanto costa il piano annuale", min_relevance=0.42)
    assert float(rep.get("min_relevance") or 0.0) == pytest.approx(0.42), rep
