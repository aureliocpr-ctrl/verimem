"""Uno store con vettori di un altro modello risponde ZERO, in silenzio.

ws5, 2026-08-07: un backup del corpus non è più interrogabile dopo un
cambio di modello — gli snapshot di maggio hanno vettori a 384 dimensioni,
il motore di oggi ne vuole 768, e la ricerca semantica restituisce **zero
risultati senza dire perché**. Stessa radice del crash 384/768 che ws1 sta
curando nel tier skill, ma qui non c'è nessun crash: c'è il silenzio, che
è peggio, perché «nessun risultato» si legge come «non c'era niente».

Il posto dove dirlo è il `doctor`, che esiste per rispondere a «perché non
funziona» prima che qualcuno lo scopra da una risposta vuota.

Tutto quello che il check confronta è LETTO, niente è assunto:
- le dimensioni stanno nei blob (lunghezza / 4 byte per float32);
- il modello dichiarato sta in `facts.embedding_model`, riga per riga;
- la dimensione ATTESA la pubblica il daemon di encode nel suo file di
  discovery (`dim: 768`) — e quando il daemon non c'è, il check lo dice
  invece di indovinare.

⚠️ Il check deve reggere su store ESTRANEI: è nato per guardare backup e
snapshot altrui, quindi una tabella incompleta o una colonna assente non
lo devono far cadere. Un referto che sparisce sullo store che doveva
diagnosticare è inutile due volte.
"""
from __future__ import annotations

import sqlite3
import struct

import pytest


def _store(tmp_path, righe, *, con_colonna_modello: bool = True):
    """Uno store MINIMO scritto a mano: nessun modello caricato, nessuna
    `Memory` costruita — il check deve funzionare su un file e basta."""
    d = tmp_path / "semantic"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "semantic.db"
    cols = "id TEXT PRIMARY KEY, embedding BLOB"
    if con_colonna_modello:
        cols += ", embedding_model TEXT"
    with sqlite3.connect(p) as con:
        con.execute(f"CREATE TABLE IF NOT EXISTS facts ({cols})")
        for i, (dim, modello) in enumerate(righe):
            blob = struct.pack(f"{dim}f", *([0.0] * dim))
            if con_colonna_modello:
                con.execute("INSERT INTO facts VALUES (?,?,?)",
                            (f"f{i}", blob, modello))
            else:
                con.execute("INSERT INTO facts VALUES (?,?)", (f"f{i}", blob))
    return p


def _check(nome: str = "embedding-model"):
    from verimem.doctor import run_doctor
    return next((c for c in run_doctor() if c["name"] == nome), None)


def test_uno_store_tutto_del_modello_corrente_non_allarma(tmp_path,
                                                          monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem.config import CONFIG
    _store(tmp_path, [(768, CONFIG.embedding_model)] * 3)

    c = _check()
    assert c is not None, "il check non esiste"
    assert c["status"] == "ok", c


def test_vettori_di_UN_ALTRO_modello_sono_un_FAIL_non_un_avviso(tmp_path,
                                                                monkeypatch):
    """Se ogni riga ha la dimensione sbagliata la ricerca semantica non
    restituisce NIENTE: non è un degrado, è uno store muto."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _store(tmp_path, [(384, "sentence-transformers/all-MiniLM-L6-v2")] * 4)

    c = _check()
    assert c["status"] == "fail", c
    assert "384" in c["detail"], c["detail"]
    assert c.get("fix"), "un fail senza rimedio non e' un referto"


def test_uno_store_MISTO_avvisa_e_conta_le_due_popolazioni(tmp_path,
                                                           monkeypatch):
    """Metà e metà non è «rotto»: è una parte del corpus invisibile, e il
    numero che serve è quante righe."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem.config import CONFIG
    _store(tmp_path, [(768, CONFIG.embedding_model)] * 3
           + [(384, "vecchio/modello")] * 2)

    c = _check()
    assert c["status"] == "warn", c
    assert "3" in c["detail"] and "2" in c["detail"], c["detail"]


def test_uno_store_senza_vettori_non_inventa_un_allarme(tmp_path,
                                                        monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _store(tmp_path, [])
    c = _check()
    assert c["status"] == "ok", c


def test_regge_una_tabella_SENZA_la_colonna_del_modello(tmp_path,
                                                        monkeypatch):
    """Il check nasce per guardare backup e store altrui: una colonna che
    non c'è non lo deve far sparire — la dimensione basta a rispondere."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _store(tmp_path, [(384, None)] * 2, con_colonna_modello=False)

    c = _check()
    assert c is not None, "il check e' sparito su uno store parziale"
    assert "384" in c["detail"], c["detail"]


def test_dichiara_da_dove_viene_la_dimensione_attesa(tmp_path, monkeypatch):
    """Confrontare con un numero inventato sarebbe la classe che questo
    file cura da stanotte: la dimensione attesa o viene dal daemon, o si
    dice che non si sa."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem.config import CONFIG
    _store(tmp_path, [(768, CONFIG.embedding_model)])

    testo = _check()["detail"].lower()
    assert ("daemon" in testo or "expected" in testo
            or "not known" in testo), testo


def test_SENZA_DAEMON_il_referto_non_dice_ok_a_uno_store_di_un_altro_modello(
        tmp_path, monkeypatch):
    """Il caso che mancava, ed e' quello in cui gira la CI.

    La dimensione attesa la dichiara il daemon di encoding: dove non gira —
    ogni runner di CI, e la macchina di chiunque non lo tenga acceso — il
    ripiego era prendere la dimensione PIU' FREQUENTE come se fosse quella
    giusta. Su uno store scritto INTERAMENTE da un altro modello quel massimo
    e' tutto il corpus, quindi zero righe cattive e verdetto `ok`, con il
    dettaglio che nella stessa riga dichiarava «expected dimension NOT known
    here». **Il referto diceva «non lo so» e lo stato diceva «va bene».**

    Gli altri banchi di questo file non lo vedevano perche' in locale il daemon
    C'E': lo stesso test passava in casa e falliva in CI, e la differenza non
    era il codice ma un processo acceso.

    ⚠️ Qui il daemon viene spento PER FINTA (`read_discovery` -> {}) invece di
    fermare quello vero: un banco non tocca i processi di chi lo esegue.
    """
    from unittest.mock import patch

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    _store(tmp_path, [(384, "sentence-transformers/all-MiniLM-L6-v2")] * 4)

    with patch("verimem.encode_service.read_discovery", return_value={}):
        c = _check()

    assert c["status"] == "fail", (
        "senza daemon il doctor promuove a 'ok' uno store che la ricerca "
        f"semantica non puo' leggere: {c}")
    assert c.get("fix"), "un fail senza rimedio non e' un referto"
