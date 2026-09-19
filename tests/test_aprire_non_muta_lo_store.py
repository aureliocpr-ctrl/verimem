"""T120 — chi apre uno store non deve cambiarlo. Quattro porte, quattro celle.

⚠️ QUESTE CELLE SONO ROSSE OGGI, DI PROPOSITO, e non vanno committate finché la
cura non c'è: sono il RED di T120, tenuto fuori dal ramo per non spedire un
banco che fallisce. Misurato il 19/09 su copie di uno store a v16:

    adjudication_log.AdjudicationLog     CAMBIA  77.824 -> 102.400 byte  v16 -> 16
    decay_job._ensure_last_decay_column  CAMBIA  77.824 ->  81.920 byte  v16 -> 16
    gateway.GatewayKeys                  CAMBIA  77.824 ->  90.112 byte  v16 -> 16
    document_index.DocumentIndex         CAMBIA  77.824 ->  94.208 byte  v16 -> 16

Le quattro eseguono DDL fuori dalla scala delle migrazioni, quindi
`ensure_schema_version` non le vede e il rifiuto della fetta 3 non le tocca. E
la versione dichiarata NON cambia: lo schema si muove e il numero resta fermo —
T121 col segno rovesciato.

Il negativo di ogni cella è nella cella stessa: se il file NON cambia bisogna
prima escludere che il costruttore non sia stato invocato affatto, e per questo
ognuna verifica anche che qualcosa sia stato costruito.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest


def _store_a_versione(tmp_path: Path, versione: int = 16) -> Path:
    """Uno store con le tabelle del nucleo e una versione dichiarata.

    Costruito qui e non copiato da `~/.engram`: un banco non tocca lo store di
    nessuno, nemmeno in lettura. Il righello che misura sul campo vive nello
    studio (`strumenti/chi_muta_aprendo.py`) e lavora solo su copie.
    """
    p = tmp_path / "semantic.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
                "topic TEXT, created_at REAL)")
    con.execute("INSERT INTO facts (id, proposition, topic, created_at) "
                "VALUES ('uno', 'La soglia vale 19.0s.', 'prova/t120', 0.0)")
    con.execute("CREATE TABLE _schema_version (db_id TEXT PRIMARY KEY, "
                "version INTEGER NOT NULL)")
    con.execute("INSERT INTO _schema_version (db_id, version) VALUES ('semantic', ?)",
                (versione,))
    con.commit()
    con.close()
    return p


def _impronta(p: Path) -> tuple[int, str]:
    dati = p.read_bytes()
    return len(dati), hashlib.sha256(dati).hexdigest()


def _versione(p: Path) -> int | None:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        riga = con.execute(
            "SELECT version FROM _schema_version WHERE db_id = 'semantic'").fetchone()
        return int(riga[0]) if riga else None
    finally:
        con.close()


def _apre_senza_mutare(p: Path, apri) -> None:
    """Il contratto, uguale per tutte e quattro: aprire non cambia il file."""
    prima = _impronta(p)
    versione_prima = _versione(p)

    apri(p)

    dopo = _impronta(p)
    assert dopo == prima, (
        f"aprire ha cambiato il file: {prima[0]} -> {dopo[0]} byte, "
        f"sha {prima[1][:12]} -> {dopo[1][:12]}. Chi apre uno store per leggerlo "
        f"non deve riscriverne lo schema — e la versione dichiarata è passata da "
        f"{versione_prima} a {_versione(p)}, cioè il numero non racconta il cambio."
    )


def test_il_registro_delle_aggiudicazioni_apre_senza_mutare(tmp_path: Path) -> None:
    from verimem.adjudication_log import AdjudicationLog

    _apre_senza_mutare(_store_a_versione(tmp_path), lambda p: AdjudicationLog(p))


def test_la_potatura_apre_senza_mutare(tmp_path: Path) -> None:
    from verimem.decay_job import _ensure_last_decay_column

    def apri(p: Path) -> None:
        con = sqlite3.connect(p)
        try:
            _ensure_last_decay_column(con)
            con.commit()
        finally:
            con.close()

    _apre_senza_mutare(_store_a_versione(tmp_path), apri)


def test_le_chiavi_del_gateway_aprono_senza_mutare(tmp_path: Path) -> None:
    from verimem.gateway import GatewayKeys

    _apre_senza_mutare(_store_a_versione(tmp_path), lambda p: GatewayKeys(p))


def test_l_indice_dei_documenti_apre_senza_mutare(tmp_path: Path) -> None:
    from verimem.document_index import DocumentIndex

    _apre_senza_mutare(_store_a_versione(tmp_path), lambda p: DocumentIndex(db_path=p))


def test_la_scala_delle_migrazioni_non_migra_senza_che_glielo_chiedano(tmp_path: Path) -> None:
    """La predizione della fetta 3b, dove il cambio deve fermarsi (D-0009).

    È la cella principale: `ensure_schema_version` è il punto in cui la
    migrazione AVVIENE, e con il cablaggio deve rifiutare invece di applicare.
    Misurato oggi su una copia a v16 con `target=17`: la dimensione resta
    77.824 byte ma lo sha cambia (`7c6cd1c9869f` -> `c07482c27923`) e la
    versione passa a 17 — cioè il file è stato riscritto e il numero promosso
    senza che nessuno l'abbia chiesto.

    ⚠️ Il salto di UN passo è l'unico che ci arriva: due o più il codice li
    rifiuta già («migration ladder is not contiguous», misurato su 16->18 e
    16->25). La cura non deve riscrivere quella difesa, solo chiudere il passo
    che le sfugge.
    """
    from verimem.migrations import ensure_schema_version

    p = _store_a_versione(tmp_path, versione=16)
    prima = _impronta(p)

    con = sqlite3.connect(p)
    try:
        ensure_schema_version(con, db_id="semantic", target_version=17, migrations=[])
    finally:
        con.close()

    assert _impronta(p) == prima, (
        f"la scala ha migrato un file senza che nessuno lo chiedesse: la versione "
        f"è passata da 16 a {_versione(p)} e lo schema non è cambiato di "
        f"conseguenza — il numero promosso senza le colonne che lo sostengono"
    )


def test_la_versione_del_nucleo_ha_sempre_un_criterio() -> None:
    """Presidio: se il nucleo sale di versione, la mappa delle attese deve seguirlo.

    ⚠️ Questa cella è VERDE oggi e serve per domani. `schema_corrisponde` torna
    False quando non ha un criterio per una versione — scelta giusta — ma
    significa che alzare `VERSIONE_DEL_NUCLEO` a 18 senza aggiungere la voce 18
    ad `ATTESE_PER_VERSIONE` spegne `marca()` IN SILENZIO: rifiuterebbe sempre,
    con un messaggio corretto («non ho un criterio per la 18») che nessuno sta
    leggendo mentre cambia un numero.

    Il limite oggi è dichiarato e accettato — la mappa conosce solo la 17, per
    due colonne — e la fetta 3b lo estende quando sposta le DDL. Fino ad allora
    è questa cella a tenerlo fermo.
    """
    from verimem.schema import ATTESE_PER_VERSIONE, VERSIONE_DEL_NUCLEO

    assert VERSIONE_DEL_NUCLEO in ATTESE_PER_VERSIONE, (
        f"il codice dichiara la versione {VERSIONE_DEL_NUCLEO} ma "
        f"`ATTESE_PER_VERSIONE` conosce solo {sorted(ATTESE_PER_VERSIONE)}: "
        f"`marca()` rifiuterebbe ogni store, e il messaggio direbbe la verità "
        f"a nessuno")
    assert ATTESE_PER_VERSIONE[VERSIONE_DEL_NUCLEO], (
        "il criterio c'è ma è vuoto: un insieme vuoto è contenuto in qualunque "
        "schema, quindi `schema_corrisponde` direbbe sempre True")


def test_il_banco_guarda_un_file_che_esiste_davvero(tmp_path: Path) -> None:
    """CONTROLLO POSITIVO: se le quattro celle sopra diventassero verdi, questa
    dice che non è perché il banco ha smesso di guardare.

    Un file costruito male, o un'impronta che non cambia mai, farebbe passare
    tutto: qui si verifica che l'impronta SAPPIA cambiare."""
    p = _store_a_versione(tmp_path)
    prima = _impronta(p)

    con = sqlite3.connect(p)
    con.execute("CREATE TABLE prova_del_banco (x INTEGER)")
    con.commit()
    con.close()

    assert _impronta(p) != prima, (
        "l'impronta non è cambiata nemmeno creando una tabella: il misuratore è "
        "rotto, e le quattro celle sopra non provano niente")
    assert _versione(p) == 16, "e la versione si legge"


@pytest.mark.parametrize("nome", ["adjudication_log", "decay_job", "gateway",
                                  "document_index"])
def test_le_quattro_porte_esistono_ancora(nome: str) -> None:
    """Se un modulo sparisce o si rinomina, questo banco deve dirlo invece di
    diventare silenziosamente verde."""
    import importlib

    assert importlib.import_module(f"verimem.{nome}") is not None
