"""Il referto del gateway prometteva un comando pronto guardando un nome di file.

Fino al 17/08 il check era, per intero::

    if keys_db.exists():
        add("gateway", OK, "keys db present — `verimem gateway serve` ready")
    else:
        add("gateway", OK, "no gateway keys yet")

⇒ La stessa forma con cui `moat-judge` certificava un giudice che non c'era:
**un file che esiste non è un registro di chiavi leggibile**. Misurato quel
giorno, scrivendoci dentro del testo qualunque::

    verimem doctor   ✓ keys db present (gateway_keys.db) — `verimem gateway
                       serve` ready
    sqlite3          DatabaseError: file is not a database

cioè lo stato peggiore usciva con la riga più rassicurante del referto. E il
check non aveva **alcuno** stato negativo: OK con il file, OK senza — un
controllo che non può dire di no non misura niente.

⚠️ Ciò che questo banco NON pretende, e la ragione: non trasforma in allarme
uno stato benigno. Un `gateway_keys.db` che esiste senza la tabella dentro è
normale (`gateway keys create` la crea), e resta OK — con la strada scritta
accanto. La distinzione fra «non ancora inizializzato» e «illeggibile» è presa
dal tipo di errore che sqlite restituisce, non da un'euristica sul contenuto.

📌 Il gateway serve solo al server self-host di squadra, quindi il caso
illeggibile è un avviso e non un fallimento: il referto lo dice e non blocca
l'uscita di `doctor`.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.doctor import OK, WARN, run_doctor


def _gateway(checks):
    return next(c for c in checks if c["name"] == "gateway")


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Tutti e tre gli alias: `_compat.data_dir()` ne preferisce altri prima di
    `HIPPO_DATA_DIR`, e su una macchina di sviluppo `ENGRAM_DATA_DIR` punta al
    corpus reale — un test che ne pone uno solo leggerebbe lo store vero."""
    d = tmp_path / "store"
    d.mkdir()
    for _env in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_env, str(d))
    return d


def test_un_file_illeggibile_non_e_un_registro_di_chiavi(store):
    """Il caso: il file c'è, e non è un database."""
    (store / "gateway_keys.db").write_text("questo non è un database sqlite",
                                           encoding="utf-8")
    g = _gateway(run_doctor())
    assert g["status"] == WARN, (
        f"un file che sqlite non sa aprire esce come stato buono: {g}")
    assert "cannot be read" in g["detail"], g["detail"]


def test_le_chiavi_registrate_vengono_CONTATE(store):
    """⚠️ POPOLAZIONE OPPOSTA, ed è quella che rende il test sopra un presidio
    e non un interruttore: sul caso normale il referto deve dire il numero
    VERO, non una formula. Con due chiavi deve leggersi «2»."""
    db = store / "gateway_keys.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE gateway_keys (key_id TEXT PRIMARY KEY, "
                "key_hash TEXT, tenant_id TEXT, name TEXT, plan TEXT, "
                "created_at REAL, revoked_at REAL)")
    con.executemany("INSERT INTO gateway_keys (key_id, key_hash, tenant_id) "
                    "VALUES (?, ?, ?)",
                    [("k1", "h1", "t"), ("k2", "h2", "t")])
    con.commit()
    con.close()

    g = _gateway(run_doctor())
    assert g["status"] == OK, g
    assert "2 gateway key" in g["detail"], (
        f"il referto non conta le chiavi che ci sono: {g['detail']}")


def test_un_file_non_inizializzato_resta_benigno(store):
    """⚠️ L'ALTRA POPOLAZIONE, e serve a impedire la cura sbagliata: il modo
    più facile di far passare il primo test è chiamare «rotto» tutto ciò che
    non è un registro pieno. Un file senza la tabella dentro è normale, e deve
    restare OK — con scritto come si va avanti."""
    (store / "gateway_keys.db").write_bytes(b"")
    g = _gateway(run_doctor())
    assert g["status"] == OK, (
        f"un db non ancora inizializzato viene segnalato come guasto: {g}")
    assert "keys create" in (g.get("fix") or ""), g.get("fix")


def test_senza_file_il_referto_non_inventa_un_problema(store):
    """L'ultima delle quattro: il gateway è opzionale, e chi non lo usa non
    deve leggere niente di allarmante."""
    g = _gateway(run_doctor())
    assert g["status"] == OK, g
    assert "no gateway keys yet" in g["detail"], g["detail"]
