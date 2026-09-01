"""Il pavimento servito poteva essere vecchio, e nessuno lo diceva.

DA DOVE NASCE. La lettura non ricalcola piu' il pavimento: la stima costa
24169 ms sul corpus vero di 14382 fatti, e la chiamata che la innesca sta nel
percorso di OGNI `search` — l'avviso di rilevanza la chiede fuori da ogni `if`
— quindi la prima ricerca dopo una crescita del 5% pagava 24 secondi.

⚠️ MA QUELLA CURA HA UN PREZZO, ed e' scritto nero su bianco da chi ha fatto il
pavimento persistito, in un test che questa modifica ha reso rosso::

    «se il corpus cambia in modo sostanziale e il valore resta congelato,
     serviamo un pavimento sbagliato per sempre — che e' peggio di uno lento»

L'obiezione e' giusta. Per questo la cura non viaggia da sola: chi legge serve
il valore che ha, `doctor` DICE quando e' vecchio, `warmup` lo rinfresca. Senza
questa meta', «non ricalcolare in lettura» diventerebbe «congelato per sempre»,
che e' esattamente il disastro che quel test difendeva.

🔑 E il caso non e' teorico: sul corpus vero `{"floor": 0.0, "n_facts": 13795}`
e' rimasto dalle 20:32 del 30/08 alle 02:52 del 31/08 — SEI ORE su quasi
quattordicimila fatti — e nulla, da nessuna parte, diceva che quel valore fosse
vecchio. Peggio: `0.0` e' FALSY, quindi ogni `if` a valle lo legge come «nessun
pavimento» e l'astensione resta spenta in silenzio.

⚖️ PERCHE' IL DOCTOR SEGNALA E NON RINFRESCA: il comando promette «no model
load» e «~2s anche su un'installazione rotta». Ricalcolare vorrebbe dire
caricare il cross-encoder e aspettare 24 secondi — romperebbe entrambe le
promesse. Qui si legge un JSON e si fa un COUNT su una connessione `mode=ro`.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import verimem.relevance_floor as rf
from verimem.doctor import OK, WARN, run_doctor


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """⚠️ TUTTI E TRE GLI ALIAS, e non e' pedanteria: `_compat.data_dir()` ne
    preferisce altri prima di `HIPPO_DATA_DIR`, e su questa macchina
    `ENGRAM_DATA_DIR` punta al corpus REALE. Un test che ne imposta uno solo
    non isola niente: legge — e giudica — lo store vero di chi sviluppa."""
    d = tmp_path / "store"
    (d / "semantic").mkdir(parents=True)
    for _env in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_env, str(d))
    return d


def _corpus(store, n_servibili: int, n_quarantinati: int = 0):
    """Uno store minimo con la sola colonna che il check guarda."""
    db = store / "semantic" / "semantic.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, "
                "superseded_by TEXT, status TEXT)")
    con.executemany("INSERT INTO facts (superseded_by, status) VALUES (?, ?)",
                    [(None, None)] * n_servibili
                    + [(None, "quarantined")] * n_quarantinati)
    con.commit()
    con.close()
    return db


def _scrivi_pavimento(db, *, floor, n_facts, metrica="servibili"):
    d = {"floor": floor, "n_facts": n_facts}
    if metrica is not None:
        d["n_metric"] = metrica
    db.with_suffix(db.suffix + ".floor.json").write_text(
        json.dumps(d), encoding="utf-8")


def _check(nome="relevance-floor"):
    return next((c for c in run_doctor() if c["name"] == nome), None)


def test_la_premessa_il_check_esiste_e_guarda_lo_store_isolato(store):
    """Controllo positivo del banco: senza store il check c'e' e non si
    lamenta. Se questa cella cade, tutte le altre misurano un'altra cosa —
    o, peggio, lo store vero."""
    c = _check()
    assert c is not None, "il doctor non espone nessun check sul pavimento"
    assert c["status"] == OK, c


def test_col_pavimento_ALLINEATO_il_doctor_tace(store):
    """⚠️ LA POPOLAZIONE OPPOSTA, e viene prima: un avviso che si accende
    sempre non informa. Con 100 fatti e un pavimento calcolato su 100, non c'e'
    niente da dire."""
    db = _corpus(store, 100)
    _scrivi_pavimento(db, floor=0.8781, n_facts=100)
    c = _check()
    assert c["status"] == OK, c
    assert "0.8781" in c["detail"], c["detail"]


def test_il_pavimento_STANTIO_viene_dichiarato_col_rimedio(store):
    """IL CUORE. Il corpus e' cresciuto oltre la deriva del 5%: il valore
    servito e' vecchio, e chi lo usa deve saperlo — insieme al comando che lo
    rimette a posto."""
    db = _corpus(store, 200)
    _scrivi_pavimento(db, floor=0.8781, n_facts=100)
    c = _check()
    assert c["status"] == WARN, (
        f"il pavimento e' calcolato su 100 fatti e il corpus ne ha 200, e il "
        f"doctor non dice niente: {c}")
    assert "100" in c["detail"] and "200" in c["detail"], c["detail"]
    assert c.get("fix") == "verimem warmup", (
        f"un avviso senza il rimedio concreto non e' un referto: {c}")


def test_lo_ZERO_viene_dichiarato_perche_SPEGNE_l_astensione(store):
    """🔑 IL CASO REALMENTE ACCADUTO, e il piu' insidioso: il file e' coerente
    col corpus — nessuna deriva — ma il valore e' `0.0`, che essendo falsy ogni
    `if` a valle legge come «nessun pavimento». L'astensione risulta spenta
    senza che nulla sia rotto."""
    db = _corpus(store, 100)
    _scrivi_pavimento(db, floor=0.0, n_facts=100)
    c = _check()
    assert c["status"] == WARN, (
        f"un pavimento a zero passa per sano solo perche' e' allineato: {c}")
    assert "0.0" in c["detail"], c["detail"]


def test_un_file_della_METRICA_VECCHIA_non_e_confrontabile(store):
    """Un `n_facts` contato su tutte le righe e uno contato sui soli servibili
    sono due popolazioni: confrontarli e' il difetto, spostato di un passo."""
    db = _corpus(store, 100, n_quarantinati=40)
    _scrivi_pavimento(db, floor=0.8781, n_facts=140, metrica=None)
    c = _check()
    assert c["status"] == WARN, c
    assert "metric" in c["detail"], c["detail"]


def test_i_QUARANTINATI_da_soli_non_fanno_scattare_l_avviso(store):
    """⚖️ IL REPERTO DEL PEZZO (iv), dall'altro lato: il pavimento e' stimato
    su cio' che il recall SERVE, quindi la crescita dei soli quarantinati non
    lo invecchia. Se questa cella diventasse rossa, il doctor conterebbe una
    popolazione diversa da quella che il valore descrive."""
    db = _corpus(store, 100, n_quarantinati=90)
    _scrivi_pavimento(db, floor=0.8781, n_facts=100)
    c = _check()
    assert c["status"] == OK, (
        f"90 quarantinati non cambiano cio' che il recall serve, e il doctor "
        f"dichiara il pavimento vecchio: {c}")


# ═══════════════════════════════════════════════════════════════════════════
# L'ALTRA META': chi rinfresca davvero.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def conta(monkeypatch):
    n = {"chiamate": 0}
    vera = rf.estimate_relevance_floor

    def _spia(*a, **k):
        n["chiamate"] += 1
        return vera(*a, **k)

    monkeypatch.setattr(rf, "estimate_relevance_floor", _spia)
    return n


def test_il_rinfresco_ricalcola_SOLO_se_serve(tmp_path, monkeypatch, conta):
    """⚠️ «Rinfresca» non vuol dire «ricalcola sempre»: su un pavimento
    allineato la stima non va pagata due volte. E su uno stantio si', altimenti
    il comando non serve a niente."""
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    from verimem.client import Memory
    mem = Memory(str(tmp_path / "s.db"))
    mem._floor_cache = None
    mem._auto_relevance_floor()
    assert conta["chiamate"] == 1

    rifatto, _ = rf.rinfresca_se_stantio(mem)
    assert rifatto is False, "ha ricalcolato un pavimento gia' allineato"
    assert conta["chiamate"] == 1, conta

    f = mem._floor_file()
    f.write_text(json.dumps({"floor": 0.4242, "n_facts": 99999,
                             "n_metric": "servibili"}), encoding="utf-8")
    mem._floor_cache = None

    rifatto, _ = rf.rinfresca_se_stantio(mem)
    assert rifatto is True, "il pavimento era stantio e non e' stato rifatto"
    assert conta["chiamate"] == 2, conta
    assert getattr(mem, "_floor_stantio", None) is False
