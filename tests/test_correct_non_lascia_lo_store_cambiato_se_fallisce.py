"""T156 — un `correct` che fallisce non lascia lo store cambiato.

IL DIFETTO, trovato mentre si curava T154: `correct` scrive il fatto nuovo e
POI chiama la supersessione. Se quella fallisce, il comando esce con errore e
lo store **e' gia' cambiato**: dentro c'e' un fatto nuovo che non corregge
niente — orfano — e l'utente ha letto «fallito». Il file avvisava gia' di
questa forma («un fatto nuovo orfano E nessuna correzione sarebbe il peggiore
dei due esiti, perche' sembra riuscito»): la guardia era prima della scrittura,
e il difetto si era spostato di un passo piu' in la'.

LA STRADA SCELTA, e perche' non l'altra (misurato prima di scrivere):
· «una transazione sola» NON e' praticabile a costo ragionevole: `_connect()`
  apre una connessione nuova a ogni chiamata e `store()` non ci passa nemmeno —
  l'INSERT parte da un worker (`semantic.py:_work`) con la sua connessione.
· disfare SI', ma con la via del prodotto: `delete_with_undo()` fa
  `snapshot_pre_op(conn, "forget", ...)` PRIMA di togliere la riga, quindi il
  fatto non e' perso, e' ripristinabile. Nessun meccanismo nuovo.

⚠️ IL GUASTO QUI E' FORZATO, E VA DETTO: dopo T154 nessuna delle quattro
`SupersedeError` di `supersede()` puo' scattare con un fatto appena creato (la
catena di un fatto nuovo e' vuota, il suo id non e' quello vecchio, e c'e'
perche' e' stato appena scritto). Il fallimento residuo e' un errore inatteso —
disco, DB, la corsa concorrente che il prodotto dichiara. Aspettarlo sarebbe
aspettare un caso che non so provocare: qui si **provoca**, e la cella misura
la RISPOSTA al guasto, non la sua probabilita'.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.semantic import SemanticMemory, SupersedeError

TOPIC = "prova/t156"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Store usa-e-getta; quattro variabili perche' qui si e' in-process."""
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _memoria():
    from verimem import Memory
    return Memory()


def _fuori_dallo_store_vero(ricevuta: dict) -> bool:
    vero = str(Path.home() / ".engram")
    return vero.lower() not in str(ricevuta.get("store") or "").lower()


def _scrivi(testo: str) -> tuple[str, str]:
    """Rende (id del fatto, percorso del db) — il db lo dice il prodotto."""
    m = _memoria()
    r = m.add(testo, topic=TOPIC)
    assert _fuori_dallo_store_vero(r), f"scritto nello store VERO: {r.get('store')!r}"
    return str(r["id"]), str(m.semantic.db_path)


def _conta(db: str, sql: str, *args) -> int:
    """Conta SULLA TABELLA: lo stato dello store non lo racconta l'output."""
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return int(conn.execute(sql, args).fetchone()[0])


def _fatti_nel_topic(db: str) -> int:
    return _conta(db, "SELECT COUNT(*) FROM facts WHERE topic = ?", TOPIC)


def _snapshot_di_disfacimento(db: str) -> int:
    return _conta(
        db, "SELECT COUNT(*) FROM facts_undo_log WHERE op_type = 'forget'")


def test_se_la_supersessione_fallisce_il_fatto_nuovo_non_resta_nello_store(
        store, monkeypatch):
    """Il caso del difetto: guasto forzato, store che deve tornare com'era."""
    vecchio, db = _scrivi("Il totale della fattura e' 500 euro.")
    prima = _fatti_nel_topic(db)
    assert prima == 1, f"il banco non parte da uno stato noto: {prima}"

    def esplodi(self, old_id, new_id, **kw):
        raise SupersedeError("guasto forzato dal banco T156")

    monkeypatch.setattr(SemanticMemory, "supersede", esplodi)

    esito = CliRunner().invoke(
        app, ["correct", vecchio, "Il totale della fattura e' 900 euro."])

    assert esito.exit_code != 0, esito.output
    dopo = _fatti_nel_topic(db)
    assert dopo == prima, (
        f"lo store e' cambiato malgrado il fallimento: {prima} -> {dopo}. "
        f"Il fatto nuovo e' rimasto orfano.\n{esito.output}")
    assert _snapshot_di_disfacimento(db) >= 1, (
        "il fatto nuovo e' stato tolto SENZA snapshot: non e' ripristinabile")
    assert vecchio[:8] in esito.output, (
        f"il messaggio non nomina il fatto che si voleva correggere:\n{esito.output}")


def test_se_anche_il_disfacimento_fallisce_il_messaggio_dice_QUALE_passo(
        store, monkeypatch):
    """Il caso peggiore: due passi falliti, e chi legge deve sapere dove sta.

    Qui lo store RESTA sporco — e' il limite dichiarato della strada scelta.
    Quello che non puo' restare e' il silenzio: un comando che fallisce due
    volte senza dire a che punto e' arrivato lascia l'utente senza la sola
    informazione che gli serve per rimettere a posto.
    """
    vecchio, _ = _scrivi("Il totale della fattura e' 500 euro.")

    def esplodi(self, old_id, new_id, **kw):
        raise SupersedeError("guasto forzato dal banco T156")

    def esplodi_anche_il_disfacimento(self, fact_id, *, principal):
        raise sqlite3.OperationalError("disfacimento impedito dal banco T156")

    monkeypatch.setattr(SemanticMemory, "supersede", esplodi)
    monkeypatch.setattr(SemanticMemory, "delete_with_undo",
                        esplodi_anche_il_disfacimento)

    esito = CliRunner().invoke(
        app, ["correct", vecchio, "Il totale della fattura e' 900 euro."])

    assert esito.exit_code != 0, esito.output
    testo = esito.output.lower()
    assert "non" in testo and ("disfa" in testo or "tolto" in testo), (
        f"il messaggio non dice che il disfacimento NON e' riuscito:\n{esito.output}")
