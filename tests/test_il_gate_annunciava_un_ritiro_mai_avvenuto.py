"""Il gate annunciava una supersessione che non era avvenuta.

TROVATO DAL CRITIC AVVERSARIALE (job 2635e23b, worker `counterexample`, conf
0.8) sulla cura della coesistenza fra autori diversi, e non da me:

    «residuo cosmetico: warning 'superseded' fuorviante quando tutte le coppie
     sono coesistenza (elif ev@1393), ma non ritira nulla (supersede_ids
     intatto)»

Non e' cosmetico. Quando TUTTE le coppie contraddittorie escono dalla terza
uscita — due autori dichiarati e diversi, nessuno ritira nessuno — la lista
`_conflicts` resta vuota e il codice cadeva nel ramo che annuncia::

    L3-supersession: «a newer same-source value supersedes a stored fact»
    advice: «the older value is superseded.»

con `supersede_ids` INTATTO. Nessun fatto era stato ritirato.

⚠️ PER UN PRODOTTO CHE VENDE MEMORIA VERIFICATA questo e' la stessa classe di
difetto che il gate esiste per fermare: un'affermazione che la realta' non
sostiene. Solo che stavolta a confabulare era il gate, sulla propria condotta.
E' anche la stessa forma di «3/3 imported, 0 rejected» che ws6 ha misurato
sull'import — una ricevuta positiva su un'azione che non e' successa.

La cura non aggiunge un controllo: guarda se `supersede_ids` e' CRESCIUTO, che
e' l'unico fatto osservabile su cui l'avviso possa poggiare.
"""
from __future__ import annotations

import sqlite3

from verimem.client import Memory


def _warn_layers(ricevuta) -> list[str]:
    return [str(w.get("layer")) for w in (ricevuta.get("warnings") or [])]


def _servibili(db) -> list[str]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return [r["proposition"] for r in con.execute(
        "SELECT status,superseded_by,proposition FROM facts")
        if r["superseded_by"] is None and (r["status"] or "") != "quarantined"]


def test_due_autori_non_fanno_annunciare_un_ritiro(tmp_path):
    """IL CUORE: nessuno e' stato ritirato, quindi non si annuncia un ritiro."""
    db = tmp_path / "team.db"
    Memory(str(db), principal="anna").add(
        "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    ric = Memory(str(db), principal="bruno").add(
        "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", topic="az/mag")

    assert len(_servibili(db)) == 2, "i due fatti devono restare entrambi vivi"
    layers = _warn_layers(ric)
    assert "L3-supersession" not in layers, (
        f"annuncia un ritiro che non e' avvenuto: {ric.get('warnings')}")


def test_e_dice_invece_cosa_e_successo_davvero(tmp_path):
    """Non basta togliere l'avviso falso: chi legge deve sapere che una
    contraddizione c'era e che i due fatti convivono. Un silenzio al posto di
    una bugia lascia lo stesso chi legge senza l'informazione."""
    db = tmp_path / "team.db"
    Memory(str(db), principal="anna").add(
        "Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    ric = Memory(str(db), principal="bruno").add(
        "Il magazzino Z-08 di Ancona ha 2600 metri quadrati.", topic="az/mag")

    coes = [w for w in (ric.get("warnings") or [])
            if str(w.get("layer")) == "L3-coexistence"]
    assert coes, f"nessun avviso di coesistenza: {_warn_layers(ric)}"
    assert "both" in str(coes[0].get("reason", "")).lower()


def test_una_supersessione_VERA_si_annuncia_ancora(tmp_path):
    """IL PRESIDIO. Se un ritiro avviene davvero, l'avviso deve esserci: la
    cura toglie l'annuncio FALSO, non l'annuncio."""
    db = tmp_path / "solo.db"
    m = Memory(str(db), principal="anna")
    m.add("Il magazzino K-77 di Rovigo ha 4200 metri quadrati.", topic="az/mag")
    ric = m.add("Il magazzino K-77 di Rovigo ha 5100 metri quadrati.",
                topic="az/mag")

    assert len(_servibili(db)) == 1, "l'aggiornamento deve ritirare il vecchio"
    assert "L3-supersession" in _warn_layers(ric), (
        f"un ritiro e' avvenuto e non viene annunciato: {ric.get('warnings')}")
