"""`doctor` si accorge che la confidenza ordina al contrario della verifica.

Misurato sul corpus vivo il 2026-07-30 (4755 fatti vivi):

    giudicati dal moat      35   confidenza 0.5 esatta (min 0.5, max 0.5)
    mai giudicati         4720   confidenza media 0.866 — 293 stanno a 1.0

e per canale di scrittura:

    system_hook     41 fatti   confidenza media 0.954   giudicati 0
    agent_inference 4416       0.876                    giudicati 0
    user             296       0.652                    giudicati 35

Chi ordina per confidenza — cosa che `facts_by_confidence` fa e che chiunque
farebbe — mette i fatti verificati SOTTO quelli che si sono auto-dichiarati
certi. La confidenza non e' una scala comune: e' un numero che ogni canale
assegna a modo suo, e `verimem save` usa 0.5 di default proprio perche' non se
lo inventa.

Non si ricalibra la confidenza — significherebbe cambiare il senso di un campo
su 4755 righe per far tornare un ordinamento, cioe' tarare. Il prodotto lo DICE:
`doctor` e' il posto dove si autodiagnostica, e un corpus in cui la metrica
visibile e' anti-correlata con la verifica e' un problema di salute, non di
codice.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _store(d: Path, righe: list[tuple[float, float | None]]) -> None:
    """(confidence, grounding_score) — uno store minimo, scritto a mano.

    Passare dal write-path vero costerebbe il caricamento del giudice e
    misurerebbe quello, invece del check.
    """
    (d / "semantic").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(d / "semantic" / "semantic.db"))
    con.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, "
                "proposition TEXT, topic TEXT, confidence REAL, "
                "created_at REAL, superseded_by TEXT, grounding_score REAL)")
    for i, (conf, gs) in enumerate(righe):
        con.execute("INSERT INTO facts (id, proposition, topic, confidence, "
                    "created_at, superseded_by, grounding_score) "
                    "VALUES (?,?,?,?,?,NULL,?)",
                    (f"f{i:04d}", f"prop {i}", "t", conf, 1.0, gs))
    con.commit()
    con.close()


def _check(d: Path, monkeypatch: pytest.MonkeyPatch) -> dict | None:
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    from verimem.doctor import run_doctor
    for c in run_doctor():
        if c["name"] == "confidence-vs-verifica":
            return c
    return None


def test_avverte_quando_la_confidenza_e_anticorrelata(tmp_path, monkeypatch):
    _store(tmp_path, [(0.5, 99.0)] * 10 + [(0.95, None)] * 40)
    c = _check(tmp_path, monkeypatch)
    assert c is not None, "il check non esiste"
    assert c["status"] != "ok", c
    assert "0.5" in c["detail"] and "0.95" in c["detail"], (
        f"l'avviso non porta i due numeri che lo motivano: {c['detail']}")


def test_tace_quando_l_ordine_e_giusto(tmp_path, monkeypatch):
    _store(tmp_path, [(0.95, 99.0)] * 10 + [(0.5, None)] * 40)
    c = _check(tmp_path, monkeypatch)
    assert c is not None and c["status"] == "ok", c


def test_non_grida_senza_nessun_giudicato(tmp_path, monkeypatch):
    """Un corpus dove il moat non ha mai girato non ha una confidenza
    anti-correlata: non ha proprio la misura. Dirlo come allarme sarebbe
    inventare un confronto che non e' stato fatto."""
    _store(tmp_path, [(0.9, None)] * 30)
    c = _check(tmp_path, monkeypatch)
    assert c is not None and c["status"] == "ok", c
    assert "mai" in c["detail"].lower() or "0" in c["detail"]


def test_un_campione_minuscolo_non_fa_scattare_l_allarme(tmp_path, monkeypatch):
    """Con due fatti giudicati il confronto e' rumore."""
    _store(tmp_path, [(0.1, 99.0)] * 2 + [(0.99, None)] * 40)
    c = _check(tmp_path, monkeypatch)
    assert c is not None and c["status"] == "ok", c


def test_uno_store_illeggibile_non_rompe_il_doctor(tmp_path, monkeypatch):
    (tmp_path / "semantic").mkdir(parents=True)
    (tmp_path / "semantic" / "semantic.db").write_text("non un database")
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.doctor import run_doctor
    checks = run_doctor()
    assert isinstance(checks, list) and checks, "doctor non deve mai crollare"
