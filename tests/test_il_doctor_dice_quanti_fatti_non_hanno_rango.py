"""La cura di prima ha creato un arretrato: questa superficie lo dice.

Fermare il ritiro automatico dei fatti a rango ignoto (`4d8c48a0`) era la cosa
giusta — ma ha un rovescio, e va detto invece che lasciato succedere: le coppie
in cui almeno un lato ha uno stato che ``_STATUS_RANK`` non conosce **non si
risolveranno mai da sole**. Sullo store vero sono **65515**, contro 14679 a
rango davvero pari.

⚠️ **Una cura che crea un arretrato silenzioso non e' finita.** Il posto in cui
dirlo e' `doctor`, che e' cio' che un operatore esegue quando qualcosa non
torna — e la riparazione e' concreta e in mano sua: o gli stati si normalizzano,
o si aggiungono alla tabella dei ranghi.

Cio' che il check deve dire, e sono TRE cose distinte perche' mandano a tre
azioni diverse:
  1. QUANTI fatti vivi hanno uno stato fuori tabella (la dimensione),
  2. QUALI sono quegli stati (cio' che si aggiunge alla tabella),
  3. che quei fatti NON vengono piu' ritirati in automatico (il perche' la
     cosa e' tollerabile mentre la si sistema).

Senza (3) il check leggerebbe come un allarme; senza (2) l'operatore non
saprebbe cosa fare; senza (1) non saprebbe se importa.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem import doctor


def _store(d, righe: list[tuple[str, str]]) -> None:
    """`righe` = [(fact_id, status)] — scritte a mano: il banco misura il
    check, non il percorso di scrittura (che riporta tutto a `model_claim`)."""
    p = d / "semantic" / "semantic.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT,"
                " topic TEXT, superseded_by TEXT, status TEXT,"
                " grounding_score REAL, created_at REAL, embedding BLOB,"
                " embedding_model TEXT, last_verified_at REAL)")
    con.executemany(
        "INSERT INTO facts (id, proposition, topic, superseded_by, status,"
        " created_at) VALUES (?,?,?,NULL,?,0)",
        [(fid, "x", "t/x", st) for fid, st in righe])
    con.commit()
    con.close()


def _check(monkeypatch, d, nome="trust-rank-coverage"):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.delenv("ENGRAM_DATA_DIR", raising=False)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    for ch in doctor.run_doctor():
        if ch["name"] == nome:
            return ch
    return None


@pytest.fixture
def con_stati_ignoti(tmp_path):
    d = tmp_path / "ignoti"
    _store(d, [("a", "model_claim"), ("b", "model_claim"),
               ("c", "user_manual"), ("d", "user_manual"),
               ("e", "bootstrap_rule"), ("f", "quarantined")])
    return d


@pytest.fixture
def tutti_noti(tmp_path):
    d = tmp_path / "noti"
    _store(d, [("a", "model_claim"), ("b", "provisional"),
               ("c", "quarantined"), ("d", "verified")])
    return d


class TestIlCheckEsiste:

    def test_il_check_c_e(self, monkeypatch, con_stati_ignoti):
        assert _check(monkeypatch, con_stati_ignoti) is not None, (
            "nessuna superficie dice che esistono fatti senza rango")

    def test_dice_QUANTI(self, monkeypatch, con_stati_ignoti):
        ch = _check(monkeypatch, con_stati_ignoti)
        assert "3" in ch["detail"], ch["detail"]     # c, d, e
        assert "6" in ch["detail"], ch["detail"]     # su 6 vivi

    def test_dice_QUALI_stati(self, monkeypatch, con_stati_ignoti):
        """Senza i nomi degli stati l'operatore non sa cosa aggiungere."""
        ch = _check(monkeypatch, con_stati_ignoti)
        assert "user_manual" in ch["detail"], ch["detail"]
        assert "bootstrap_rule" in ch["detail"], ch["detail"]

    def test_dice_che_NON_vengono_piu_ritirati(self, monkeypatch,
                                               con_stati_ignoti):
        """La conseguenza, che e' cio' che rende l'avviso leggibile: non e' un
        allarme, e' un arretrato che non fa danno mentre lo si sistema."""
        testo = (_check(monkeypatch, con_stati_ignoti)["detail"] + " "
                 + (_check(monkeypatch, con_stati_ignoti).get("fix") or ""))
        assert "ritir" in testo.lower() or "retir" in testo.lower(), testo

    def test_porta_una_riparazione(self, monkeypatch, con_stati_ignoti):
        assert _check(monkeypatch, con_stati_ignoti).get("fix")

    def test_non_e_un_FAIL(self, monkeypatch, con_stati_ignoti):
        """Un avviso, non un guasto: i fatti ci sono e si leggono, semplicemente
        nessuno li ritira da solo. Un FAIL qui manderebbe a cercare un danno
        che non c'e'."""
        assert _check(monkeypatch, con_stati_ignoti)["status"] != doctor.FAIL


class TestPresidio:

    def test_con_tutti_gli_stati_noti_il_check_e_ok(self, monkeypatch,
                                                   tutti_noti):
        """PRESIDIO: su uno store sano il check c'e' e dice ok. Un check che
        avvisa sempre non e' un check."""
        ch = _check(monkeypatch, tutti_noti)
        assert ch is not None
        assert ch["status"] == doctor.OK, ch

    def test_la_lista_degli_stati_ignoti_non_e_infinita(self, monkeypatch,
                                                        tmp_path):
        """FALSIFICAZIONE: uno store con 40 stati diversi non deve stampare 40
        nomi in una riga di diagnosi."""
        d = tmp_path / "molti"
        _store(d, [(f"f{i}", f"stato_{i}") for i in range(40)])
        ch = _check(monkeypatch, d)
        assert len(ch["detail"]) < 400, len(ch["detail"])
