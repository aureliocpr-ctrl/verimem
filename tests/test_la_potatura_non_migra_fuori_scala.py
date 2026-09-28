"""La potatura aggiunge una colonna al nucleo fuori dalla scala (ticket da dare).

⚠️ QUESTA CELLA È ROSSA OGGI, DI PROPOSITO, e non va committata finché la cura
non c'è: è il RED del difetto, tenuto fuori dal ramo per non spedire un banco
che fallisce.

MISURATO il 19/09, ed è il motivo per cui NON sta nel banco della fetta 3b:

    _ensure_last_decay_column  ha UN SOLO chiamante in tutto il prodotto
    verimem/decay_job.py:168   dentro run_decay_pass

Quindi non è un'apertura: è la potatura. Metterla insieme alle celle di
«aprire non muta lo store» avrebbe detto «aprire» di una cosa che apertura non
è — e un banco che chiama le cose con il nome sbagliato fa curare il punto
sbagliato.

Il difetto vero, e perché conta: la colonna SERVE — senza, ogni passata
ricalcola da `created_at` sulla confidenza già decaduta, componendo
exp(-age_total/tau) e portando il corpus al pavimento in O(numero di passate)
invece che nel tempo reale. Non è la colonna a essere sbagliata: è che nasce
fuori dalla scala, quindi `_schema_version` non la racconta e due store che
dichiarano la stessa versione possono avere schemi diversi.

LA CURA, quando il ticket arriva: portare `facts.last_decay_at` dentro la scala
delle migrazioni, cioè versione 18 e voce nuova in `ATTESE_PER_VERSIONE` — che
il presidio `test_la_versione_del_nucleo_ha_sempre_un_criterio` (già in main
con la fetta 3) obbliga a scrivere nello stesso commento in cui si alza il
numero.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from verimem.schema import TABELLE_DEL_NUCLEO


def _store_a_versione(tmp_path: Path, versione: int = 16) -> Path:
    """Uno store con una tabella del nucleo e una versione dichiarata.

    La tabella delle versioni si crea col DDL DEL PRODOTTO e non a mano: una
    copia qui dentro diverge in silenzio dall'originale, ed è già costata un
    rosso per colpa del banco invece che del prodotto (`no such column:
    upgraded_at`, 19/09).
    """
    from verimem.migrations import _VERSION_TABLE_DDL

    p = tmp_path / "semantic.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
                "topic TEXT, created_at REAL)")
    con.execute(_VERSION_TABLE_DDL)
    con.execute("INSERT INTO _schema_version (db_id, version) VALUES ('semantic', ?)",
                (versione,))
    con.commit()
    con.close()
    return p


def _impronta_del_nucleo(p: Path) -> dict[str, tuple[str, ...]]:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        presenti = {
            nome for (nome,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")
            if nome in TABELLE_DEL_NUCLEO
        }
        return {
            nome: tuple(r[1] for r in con.execute(f'PRAGMA table_info("{nome}")'))
            for nome in sorted(presenti)
        }
    finally:
        con.close()


def _versione(p: Path) -> int | None:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        riga = con.execute(
            "SELECT version FROM _schema_version WHERE db_id = 'semantic'").fetchone()
        return int(riga[0]) if riga else None
    finally:
        con.close()


def test_la_potatura_non_aggiunge_colonne_al_nucleo_fuori_dalla_scala(
        tmp_path: Path) -> None:
    """ROSSO: `facts.last_decay_at` compare, e la versione dichiarata non cambia."""
    from verimem.decay_job import _ensure_last_decay_column

    p = _store_a_versione(tmp_path)
    prima = _impronta_del_nucleo(p)
    versione_prima = _versione(p)

    con = sqlite3.connect(p)
    try:
        _ensure_last_decay_column(con)
        con.commit()
    finally:
        con.close()

    dopo = _impronta_del_nucleo(p)
    assert dopo == prima, (
        f"la potatura ha cambiato il nucleo: "
        f"{set(dopo.get('facts', ())) - set(prima.get('facts', ()))} in più su "
        f"`facts`, mentre la versione dichiarata è rimasta {versione_prima} -> "
        f"{_versione(p)}. Due store alla stessa versione possono quindi avere "
        f"schemi diversi, e chi legge il numero per decidere si fida di "
        f"un'etichetta")


def test_il_righello_vede_una_colonna_vera(tmp_path: Path) -> None:
    """CONTROLLO POSITIVO: se la cella sopra diventasse verde, questa dice che
    non è perché il righello ha smesso di guardare."""
    p = _store_a_versione(tmp_path)
    base = _impronta_del_nucleo(p)

    con = sqlite3.connect(p)
    con.execute("ALTER TABLE facts ADD COLUMN prova_del_banco TEXT")
    con.commit()
    con.close()

    assert _impronta_del_nucleo(p) != base, (
        "l'impronta non è cambiata nemmeno aggiungendo una colonna a `facts`: "
        "il righello è cieco e la cella sopra non prova niente")


def test_la_potatura_ha_ancora_un_solo_chiamante() -> None:
    """Il presupposto del ticket, tenuto fermo invece che ricordato.

    La cella sopra vive in un banco separato PERCHÉ la funzione è chiamata solo
    da `run_decay_pass`. Se un domani la chiamasse anche un'apertura, quella
    separazione diventerebbe falsa — e nessuno se ne accorgerebbe rileggendo
    questo file, perché il docstring resterebbe convincente.

    ⚠️ Il conteggio esclude la riga della `def`: alla prima scrittura questa
    cella riportava due «chiamanti» (`decay_job.py:109` e `:168`) e il primo
    era la definizione. Contare le occorrenze di un nome non è contare le
    chiamate — è lo stesso errore che oggi ha prodotto «30 ALTER fuori dalle
    migrazioni» quando le esecuzioni vere erano 5.
    """
    import pathlib
    import re

    radice = pathlib.Path(__file__).resolve().parent.parent / "verimem"
    chiamata = re.compile(r"(?<!def )_ensure_last_decay_column\s*\(")
    chiamanti: list[str] = []
    for f in radice.rglob("*.py"):
        for n, riga in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if chiamata.search(riga):
                chiamanti.append(f"{f.relative_to(radice)}:{n}")

    assert chiamanti == ["decay_job.py:168"], (
        f"i chiamanti non sono più quello che il ticket presuppone: "
        f"{chiamanti}. Se la potatura non è più l'unico punto, questo banco va "
        f"riunito a quello di «aprire non muta lo store» invece di restare "
        f"separato")
