"""T160 — `lineage_parents` è una colonna piena che non esce da nessuna porta.

Misurato sullo store vivo (su copia, mai quello vero), 18169 fatti:

    lineage_parents NON NULL        : 32
    lineage_parents con contenuto   : 29
    status di quei 29               : 21 user_manual, 6 model_claim, 2 quarantined
    genitori referenziati           : 39, tutti VIVI, zero ritirati
    esempio                         : ["bdca254f7458", "03e8c1d129af"]

Non è una colonna morta: è **piena e muta**. Il `Fact` non ha il campo e
`semantic.py` non lo nomina mai — zero occorrenze in tutto il modulo — quindi
quelle 29 genealogie esistono nel database e nessuno può leggerle dal prodotto.
Ventuno delle 29 sono `user_manual`: non le ha generate una pipeline, le ha
scritte una persona a mano dichiarando da quali fatti nasceva quel fatto.

⚠️ E UN CONSUMATORE C'È GIÀ, il che rende la colonna muta un difetto e non una
scelta: `justified_memory.py` legge `.lineage_parents` dal fatto come alias di
`derives_from` / `depends_on`. Siccome il `Fact` non porta il campo, quella
lettura risponde vuoto **sempre** — il valore sta nel database, arriva fino alla
riga che lo cerca e si ferma una chiamata prima. È la stessa giuntura di
`writer_principal` e di `source_signature`: non un criterio sbagliato, un campo
che non viene passato.

La cura decisa è **leggerla**: la deserializzazione la mappa e il `Fact` la
porta. La scrittura non si tocca — chi popola quella colonna continua a farlo
come oggi.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from verimem import Memory

TOPIC = "banco/t160"
GENITORI = ["bdca254f7458", "03e8c1d129af"]


def _scrivi_la_colonna(percorso, fact_id: str, colonna: str, valore,
                       *, formato: str) -> None:
    """Scrive direttamente nel database, come ha fatto chi ha popolato i 29.

    Il prodotto oggi non offre una porta per farlo, ed è esattamente il punto:
    il dato è nel file e il banco deve poterlo mettere lì senza passare da
    un'API che non esiste.

    ⚠️ IL `formato` NON È UN DETTAGLIO DEL BANCO: le colonne gemelle nello store
    vivo sono scritte in due modi diversi, e la cura deve saperlo.

        derives_from     'd81c3857712a'                        lista separata da virgole
        lineage_to       'bdca254f7458'                        lista separata da virgole
        lineage_parents  '["bdca254f7458", "03e8c1d129af"]'    JSON

    La prima stesura di questo banco scriveva JSON ovunque, e il controllo
    positivo l'ha colto: `derives_from` tornava indietro come
    `['["bdca254f7458"', ' "03e8c1d129af"]'], cioè il JSON spezzato sulla
    virgola. Chi leggerà `lineage_parents` con il deserializzatore delle altre
    due otterrà la stessa spazzatura sui 29 fatti veri.
    """
    testo = json.dumps(valore) if formato == "json" else ",".join(valore)
    con = sqlite3.connect(str(percorso))
    try:
        con.execute(f"UPDATE facts SET {colonna} = ? WHERE id = ?",
                    (testo, fact_id))
        con.commit()
    finally:
        con.close()


@pytest.fixture()
def fatto_con_genealogia(tmp_path):
    """Un fatto vero, con la genealogia scritta nella colonna dopo."""
    percorso = tmp_path / "sem" / "sem.db"
    mem = Memory(path=percorso)
    ric = mem.add("Il magazzino contiene 100 pezzi.", topic=TOPIC, ground=False)
    return mem, percorso, ric["id"]


# ------------------------------------------------------------- il bersaglio --
def test_la_genealogia_scritta_nel_database_arriva_al_fatto(
        fatto_con_genealogia) -> None:
    """I 29 devono uscire dalle porte: oggi il fatto letto non li porta."""
    mem, percorso, fid = fatto_con_genealogia
    _scrivi_la_colonna(percorso, fid, "lineage_parents", GENITORI, formato="json")

    letto = mem.semantic.get(fid)

    assert letto is not None, "il fatto deve esistere"
    assert getattr(letto, "lineage_parents", None) == GENITORI, (
        f"la genealogia è nel database e non arriva al fatto: "
        f"lineage_parents={getattr(letto, 'lineage_parents', '<campo assente>')!r}, "
        f"attesi {GENITORI}. Sono le 29 genealogie dello store vivo, 21 delle "
        f"quali scritte a mano da una persona, che nessuno può rileggere")


# --------------------------------------------- controllo positivo / anti-cache --
def test_una_colonna_che_il_fatto_porta_esce_davvero(fatto_con_genealogia) -> None:
    """Se il bersaglio fosse rosso perché il banco non sa scrivere nel database
    o perché rilegge da una cache, questa cella lo direbbe: la stessa manovra
    su una colonna che il `Fact` porta già deve arrivare fino in fondo."""
    mem, percorso, fid = fatto_con_genealogia
    _scrivi_la_colonna(percorso, fid, "derives_from", GENITORI, formato="csv")

    letto = mem.semantic.get(fid)

    assert letto is not None
    assert letto.derives_from == GENITORI, (
        f"nemmeno una colonna che il Fact dichiara arriva fuori: "
        f"derives_from={letto.derives_from!r}. Il banco sta misurando la "
        f"propria scrittura o una cache, non la deserializzazione")


# --------------------------------------------------------- il consumatore ----
def test_il_modulo_che_la_cerca_la_trova(fatto_con_genealogia) -> None:
    """`justified_memory` legge `.lineage_parents` dal fatto: finché il campo
    non c'è, quella lettura risponde vuoto qualunque cosa dica il database."""
    mem, percorso, fid = fatto_con_genealogia
    _scrivi_la_colonna(percorso, fid, "lineage_parents", GENITORI, formato="json")
    letto = mem.semantic.get(fid)

    visti = getattr(letto, "lineage_parents", None) or getattr(letto, "derives_from", None) or ()

    assert list(visti) == GENITORI, (
        f"chi cerca la provenienza sul fatto vede {list(visti)!r}: la colonna "
        f"è piena nel database e il modulo che la interroga non la incontra mai")
