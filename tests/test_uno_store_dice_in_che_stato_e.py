"""Fetta 3 — i tre stati di uno store, il rifiuto, e la marcatura dopo backup.

Le cinque condizioni dell'approvazione (18/09): (a) tre stati distinti e
nominati; (b) un non marcato si marca SOLO dopo un backup verificato contando le
righe; (c) uno più nuovo del codice viene rifiutato nominando le DUE versioni;
(d) solo copie, mai uno store vero; (e) il codice parte a T90b fusa.

⚠️ (d) è rispettata per costruzione: ogni cella qui costruisce il proprio file
in `tmp_path`. Nessun percorso di questo banco nomina `~/.engram`.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verimem.schema import (
    NON_MARCATO,
    VERSIONE_DEL_NUCLEO,
    Marcatura,
    SchemaNonCorrisponde,
    StoreDaMigrare,
    StoreTroppoNuovo,
    leggi_stato,
    marca,
    riguarda_il_nucleo,
    schema_corrisponde,
    verifica_apribile,
)


def _store(tmp_path: Path, nome: str = "semantic.db", pragma: int | None = None,
           colonne_della_17: bool = True) -> Path:
    """Un file sqlite vero, con una riga dentro: le righe servono al conteggio.

    `colonne_della_17` costruisce lo schema che la versione 17 dichiara: senza,
    `marca` rifiuta — ed è il punto di T121."""
    p = tmp_path / nome
    con = sqlite3.connect(p)
    extra = ", quarantined_by TEXT, grounding_span TEXT" if colonne_della_17 else ""
    con.execute(f"CREATE TABLE facts (id TEXT PRIMARY KEY{extra})")
    con.execute("INSERT INTO facts (id) VALUES ('uno')")
    if pragma is not None:
        con.execute(f"PRAGMA user_version = {pragma}")
    con.commit()
    con.close()
    return p


def test_zero_non_e_una_versione(tmp_path: Path) -> None:
    """Il difetto che il modulo esiste per evitare: 0 letto come «versione 0»."""
    stato = leggi_stato(_store(tmp_path))

    assert stato.marcatura is Marcatura.NON_MARCATO
    assert stato.versione is None, (
        "un non marcato con `versione=0` finirebbe in un confronto numerico e "
        "risulterebbe più vecchio del codice: verrebbe migrato senza averlo "
        "mai chiesto")
    assert "non è la versione 0" in str(stato)


def test_i_tre_stati_sono_distinti(tmp_path: Path) -> None:
    non_marcato = leggi_stato(_store(tmp_path, "a.db"))
    marcato = leggi_stato(_store(tmp_path, "b.db", pragma=3))
    (tmp_path / "c.db").write_text("questo non e' un database", encoding="utf-8")
    ignoto = leggi_stato(tmp_path / "c.db")
    assente = leggi_stato(tmp_path / "mai-esistito.db")

    assert non_marcato.marcatura is Marcatura.NON_MARCATO
    assert (marcato.marcatura, marcato.versione) == (Marcatura.VERSIONE, 3)
    assert ignoto.marcatura is Marcatura.IGNOTO, (
        "un file illeggibile NON è «non marcato»: «non lo so» e «nessuno l'ha "
        f"marcato» sono due risposte diverse. {ignoto}")
    assert assente.marcatura is Marcatura.IGNOTO


def test_uno_store_piu_nuovo_viene_rifiutato_con_le_due_versioni(tmp_path: Path) -> None:
    """Condizione (c): il messaggio porta il numero, non «non supportato»."""
    stato = leggi_stato(_store(tmp_path, pragma=999))

    with pytest.raises(StoreTroppoNuovo) as caduta:
        verifica_apribile(stato, versione_del_codice=1)

    messaggio = str(caduta.value)
    assert "999" in messaggio and "1" in messaggio, messaggio
    assert str(stato.percorso) in messaggio, "e il messaggio nomina QUALE file"


def test_un_non_marcato_e_un_marcato_al_pari_del_codice_si_aprono(tmp_path: Path) -> None:
    """CONTROLLO NEGATIVO della cella sopra, ed è il rischio vero della fetta.

    Se questa diventa rossa, la cura ha reso illeggibili gli store esistenti:
    al 18/09 TUTTI e 41 quelli sotto `~/.engram` sono non marcati."""
    verifica_apribile(leggi_stato(_store(tmp_path, "a.db")), versione_del_codice=1)
    verifica_apribile(leggi_stato(_store(tmp_path, "b.db", pragma=1)), versione_del_codice=1)


def test_senza_backup_riuscito_non_si_marca(tmp_path: Path) -> None:
    """Condizione (b): la marcatura è una scrittura, e non si fa al buio."""
    p = _store(tmp_path)
    chiamate: list[Path] = []

    def backup_fallito(percorso: Path) -> bool:
        chiamate.append(percorso)
        return False

    with pytest.raises(RuntimeError, match="backup non riuscito"):
        marca(p, backup_fallito)

    assert chiamate == [p], "il backup deve essere stato TENTATO, non saltato"
    assert leggi_stato(p).marcatura is Marcatura.NON_MARCATO, (
        "lo store è stato marcato lo stesso: la condizione (b) non morde")


def test_con_backup_verificato_si_marca(tmp_path: Path) -> None:
    p = _store(tmp_path)

    def backup_contando_le_righe(percorso: Path) -> bool:
        copia = percorso.with_suffix(".backup.db")
        con = sqlite3.connect(percorso)
        try:
            con.execute("VACUUM INTO ?", (str(copia),))
            attese = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        finally:
            con.close()
        con = sqlite3.connect(f"file:{copia}?mode=ro", uri=True)
        try:
            # Si contano le RIGHE, non l'impronta del file: `VACUUM INTO`
            # compatta, quindi lo sha256 cambia mentre il contenuto è identico
            # (misurato il 15/09 sullo store vero: 18169 -> 18169, sha diverso).
            return con.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == attese
        finally:
            con.close()

    stato = marca(p, backup_contando_le_righe)

    # Il numero si legge dalla costante, non si ricopia: `VERSIONE_DEL_NUCLEO`
    # vale 17 (continua la numerazione di `_schema_version`, non riparte da 1),
    # e un `1` scritto a mano qui sarebbe diventato falso senza avvisare.
    assert (stato.marcatura, stato.versione) == (Marcatura.VERSIONE, VERSIONE_DEL_NUCLEO)
    assert leggi_stato(p).versione == VERSIONE_DEL_NUCLEO, "e resta marcato dopo la riapertura"


def _con_schema_version(tmp_path: Path, nome: str, versione: int) -> Path:
    """Uno store come quelli veri: pragma a 0 e `_schema_version` valorizzata."""
    p = _store(tmp_path, nome)
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE _schema_version (db_id TEXT PRIMARY KEY, "
                "version INTEGER NOT NULL)")
    con.execute("INSERT INTO _schema_version (db_id, version) VALUES ('semantic', ?)",
                (versione,))
    con.commit()
    con.close()
    return p


def test_un_non_marcato_allineato_al_codice_si_apre(tmp_path: Path) -> None:
    """Condizione (2): sono i 41 store di oggi — pragma 0, `_schema_version` 17.

    Se questa cella diventa rossa la cura ha chiuso fuori tutti gli store che
    esistono, che è il modo più rapido di trasformare una protezione in un
    guasto."""
    stato = leggi_stato(_con_schema_version(tmp_path, "oggi.db", VERSIONE_DEL_NUCLEO))

    assert stato.marcatura is Marcatura.NON_MARCATO
    assert stato.versione_applicativa == VERSIONE_DEL_NUCLEO
    verifica_apribile(stato)  # non solleva: allineato, anche se non marcato


def test_uno_piu_vecchio_e_rifiutato_anche_in_lettura_col_comando(tmp_path: Path) -> None:
    """Condizione (1): il rifiuto vale anche per il VECCHIO, ed è la lettura
    stessa a fare il danno — misurato: v1 diventa v17 alla prima apertura."""
    vecchia = VERSIONE_DEL_NUCLEO - 4
    stato = leggi_stato(_con_schema_version(tmp_path, "ieri.db", vecchia))

    with pytest.raises(StoreDaMigrare) as caduta:
        verifica_apribile(stato)

    messaggio = str(caduta.value)
    assert str(vecchia) in messaggio and str(VERSIONE_DEL_NUCLEO) in messaggio
    assert str(stato.percorso) in messaggio, "il messaggio nomina QUALE file"
    assert "in lettura" in messaggio, "e dice che il rifiuto vale anche leggendo"
    assert "verimem store migrate" in messaggio, (
        "e dice COME uscirne: un rifiuto senza comando manda chi legge ad "
        "aprire il file a mano, cioè a fare esattamente il danno. " + messaggio)


def test_un_file_di_un_altro_sottosistema_non_e_un_verde(tmp_path: Path) -> None:
    """«Non l'ho guardato» non è «l'ho guardato e va bene».

    Sui file veri sono 45 su 76: store di episodi, competenze, grafo, e file
    vuoti. `verifica_apribile` li lascia passare — giusto, non sono del nucleo —
    ma contarli fra i «si apre» darebbe a chi legge una promessa che nessuno ha
    fatto."""
    del_nucleo = _store(tmp_path, "nucleo.db")            # ha `facts`
    altro = tmp_path / "episodi.db"
    con = sqlite3.connect(altro)
    con.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY)")
    con.commit()
    con.close()

    assert riguarda_il_nucleo(del_nucleo) is True
    assert riguarda_il_nucleo(altro) is False
    assert riguarda_il_nucleo(tmp_path / "mai-esistito.db") is False
    # e comunque non solleva: non è compito di questo modulo giudicarlo
    verifica_apribile(leggi_stato(altro))


def test_il_numero_non_si_scrive_senza_lo_schema_che_lo_sostiene(tmp_path: Path) -> None:
    """T121: la versione non si dichiara, si verifica.

    Misurato il 18/09 su una copia: `ensure_schema_version(target_version=17,
    migrations=[])` porta un file da 16 a 17 con `colonne: 28 -> 28, aggiunte:
    NESSUNA`. Lo store dichiara la 17 con lo schema della 16 — e la fetta 3, che
    su quel numero vuole decidere chi si apre, leggerebbe una garanzia che
    nessuno ha dato."""
    vecchio = _store(tmp_path, "senza-colonne.db", colonne_della_17=False)
    prima = vecchio.read_bytes()
    backup_mai_chiamato: list[Path] = []

    assert schema_corrisponde(vecchio, VERSIONE_DEL_NUCLEO) is False
    with pytest.raises(SchemaNonCorrisponde, match="non è quello di quella versione"):
        marca(vecchio, lambda p: backup_mai_chiamato.append(p) or True)

    assert backup_mai_chiamato == [], (
        "il rifiuto deve venire PRIMA del backup: un backup fatto e poi buttato "
        "è lavoro sprecato e un file in più sul disco dell'utente")
    assert vecchio.read_bytes() == prima, "e il file resta identico byte a byte"
    assert leggi_stato(vecchio).marcatura is Marcatura.NON_MARCATO


def test_una_versione_senza_criterio_non_si_marca(tmp_path: Path) -> None:
    """«Non ho un criterio per la 42» non è «la 42 va bene»: è la stessa classe
    di «non l'ho guardato» contato fra i promossi, un livello più sotto."""
    p = _store(tmp_path, "futura.db")

    assert schema_corrisponde(p, 42) is False
    with pytest.raises(SchemaNonCorrisponde, match="criterio"):
        marca(p, lambda _p: True, versione=42)


def test_leggere_lo_stato_non_cambia_lo_store(tmp_path: Path) -> None:
    """La misura non consuma l'oggetto misurato.

    Misurato il 18/09 su copie: aprire uno store con `SemanticMemory` lo porta a
    v17 sul posto, senza avviso e senza backup. La funzione che serve a decidere
    *se* migrare non può essere quella che migra."""
    p = _store(tmp_path, pragma=7)
    prima = (p.stat().st_size, p.read_bytes())

    for _ in range(3):
        leggi_stato(p)

    assert (p.stat().st_size, p.read_bytes()) == prima
    assert leggi_stato(p).versione == 7
    assert NON_MARCATO == 0  # il nome esiste perché il numero non si legge da solo
