"""Il backup dei fatti deve portarsi dietro anche i QUARANTINATI.

Un fatto quarantinato e' fuori dal recall di default ma NON e' cancellato: e'
l'archivio, ed e' cio' che rende la quarantena reversibile (`facts
requalify-quarantined` esiste apposta). Un backup che salvasse i soli ammessi
distruggerebbe quella reversibilita' SENZA DIRLO: il conteggio tornerebbe
plausibile, il restore riuscirebbe, e la perdita si scoprirebbe solo il giorno
in cui qualcuno cerca un fatto trattenuto.

MISURATO il 2026-08-29 alla porta CLI (`facts backup` / `facts restore`), store
temporaneo, modello vero: il round-trip regge su tutti e tre i punti che
potevano cedere — i quarantinati sono DENTRO il file di backup, il restore
ripristina esattamente lo stato salvato, e la copia pre-restore conserva cio'
che il restore ha sostituito. Questo presidio fissa il primo dei tre, che e'
quello che cadrebbe in silenzio.

PERCHE' LO STUB NON FALSA QUESTO TEST: non si misura un giudizio ma la presenza
di una riga in un file SQLite. Lo status viene imposto direttamente, senza
passare dal gate, proprio per non dipendere da come il gate giudica oggi.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.backup import create_backup


def _store(tmp_path):
    """Uno store minimo con un ammesso e un quarantinato, scritti a mano.

    Non passa dal gate di proposito: qui interessa che il backup copi le righe
    QUALUNQUE sia il loro status, non che il gate le classifichi in un modo."""
    db = tmp_path / "semantic.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, topic TEXT, "
        "status TEXT, created_at REAL)")
    con.executemany(
        "INSERT INTO facts VALUES (?,?,?,?,?)",
        [("aaaa0000", "La sede di Verona ha 480 pallet.", "t/ammesso", "model_claim", 1.0),
         ("bbbb1111", "La sede di Verona ha 999 pallet.", "t/quarantinato", "quarantined", 2.0)])
    con.commit()
    con.close()
    return db


def _per_status(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return dict(con.execute("SELECT status, COUNT(*) FROM facts GROUP BY status"))
    finally:
        con.close()


def test_il_backup_contiene_anche_i_quarantinati(tmp_path):
    """IL PRESIDIO. Se un giorno il backup filtrasse per status, qui diventa rosso."""
    db = _store(tmp_path)
    atteso = _per_status(db)
    assert atteso == {"model_claim": 1, "quarantined": 1}, atteso

    info = create_backup(db, tmp_path / "backups", tier="manual", verify_integrity=True)
    ottenuto = _per_status(info.path)

    assert info.fact_count == 2, (
        "la ricevuta del backup dichiara un conteggio che non comprende i "
        f"quarantinati: dice {info.fact_count}, le righe sono 2")

    assert ottenuto.get("quarantined") == 1, (
        "il backup non si e' portato dietro il fatto quarantinato: l'archivio "
        f"si perde in silenzio. Nel backup: {ottenuto}")
    assert ottenuto == atteso, f"atteso {atteso}, nel backup {ottenuto}"


def test_la_guardia_e_discriminante(tmp_path):
    """LA PROVA CHE IL PRESIDIO SERVE — un backup che filtrasse gli ammessi
    deve far fallire il controllo sopra. Si simula il filtro, non si tocca il
    prodotto: senza questa riga il test sopra passerebbe anche se non misurasse
    nulla."""
    db = _store(tmp_path)
    finto = tmp_path / "backup_che_filtra.db"
    con = sqlite3.connect(finto)
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
                "topic TEXT, status TEXT, created_at REAL)")
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    righe = src.execute("SELECT * FROM facts WHERE status != 'quarantined'").fetchall()
    src.close()
    con.executemany("INSERT INTO facts VALUES (?,?,?,?,?)", righe)
    con.commit()
    con.close()

    assert _per_status(finto).get("quarantined") is None, (
        "il backup finto doveva perdere i quarantinati: se non li perde, questo "
        "banco non sta dimostrando niente")
