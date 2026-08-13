"""Un fatto ripristinato si portava dietro il motivo per cui era stato ritirato.

⚠️ IL FATTO TORNAVA VIVO E DICEVA IL FALSO SU SE STESSO. Lo script che rimette
in circolo i fatti ritirati per sbaglio azzerava `superseded_by` e
`superseded_at` — due campi su tre — lasciando `superseded_reason` valorizzato.
Chi poi leggeva quel record trovava un fatto servito dal recall, senza
successore e senza data di ritiro, che però portava scritto **perché era stato
ritirato**.

Misurato sul corpus vero prima della cura::

    vivi (superseded_by NULL) con superseded_reason valorizzato:   38
      29  «same-source evolution»          ⎫ 34 — e il numero coincide con il
       5  «heal_contradictions: …»         ⎭ totale che lo script si dichiara
       2  «memory-poisoning-shape: kept as research evidence»
       2  «auto-mode … test 2026-05-18»

⚖️ LE ULTIME QUATTRO NON SONO RESIDUI, ED È IL MOTIVO PER CUI LA CURA STA NELLO
SCRIPT E NON IN UNA QUERY DI PULIZIA. Sono marcature **intenzionali**: fatti
tenuti apposta come materiale di ricerca, con scritto perché. Il campo serve a
due cose diverse — «perché è stato ritirato» e «perché è tenuto pur essendo
strano» — e una pulizia sul database non le distingue. **Solo chi ripristina sa
quali righe ha toccato.**

═══ E LA RIPARAZIONE ORA SI REGISTRA ═══

L'altra metà del difetto, segnalata da un'altra istanza: lo script scriveva sul
database **senza lasciare traccia**. Il giorno dopo nessuno poteva distinguere
un fatto mai ritirato da uno ripristinato, né sapere per quale motivo fosse
stato ritirato prima — perché la cura stessa lo cancellava.

Ora il motivo si legge PRIMA di azzerarlo e finisce in `ripristini.log` accanto
allo store. Su file e non a video: **un output di terminale non sopravvive alla
sessione**, e un'operazione che modifica dati e non lascia traccia è la stessa
famiglia dell'`outcome=ok` su un'operazione che non atterra.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]
_SCRIPT = _RADICE / "scripts" / "ripristina_i_ritiri_sbagliati.py"

#: Due frasi che parlano di cose diverse: il criterio odierno NON le considera
#: un'evoluzione, quindi il ritiro del primo è uno di quelli da annullare.
VECCHIA = "Il magazzino di Verona contiene 480 pallet."
NUOVA = "La cache scade dopo 30 minuti."


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    db = tmp_path / "semantic.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, "
        "superseded_by TEXT, superseded_at TEXT, superseded_reason TEXT)")
    con.execute(
        "INSERT INTO facts VALUES ('vecchio', ?, 'nuovo', '2026-08-01', "
        "'same-source evolution')", (VECCHIA,))
    con.execute("INSERT INTO facts VALUES ('nuovo', ?, NULL, NULL, NULL)",
                (NUOVA,))
    con.commit()
    con.close()
    return db


def _esegui(db: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--db", str(db), *extra],
        capture_output=True, text=True, cwd=str(_RADICE), timeout=180,
    )


def _riga(db: Path, fid: str) -> tuple:
    con = sqlite3.connect(db)
    try:
        return con.execute(
            "SELECT superseded_by, superseded_at, superseded_reason "
            "FROM facts WHERE id = ?", (fid,)).fetchone()
    finally:
        con.close()


def test_il_ripristino_azzera_TUTTI_E_TRE_i_campi(store: Path):
    """Il cuore: due campi su tre lasciano il record incoerente, e un record
    incoerente è una bugia che nessuno ha scritto apposta."""
    esito = _esegui(store, "--apply")
    assert esito.returncode == 0, esito.stderr[-600:]
    by, at, reason = _riga(store, "vecchio")
    assert by is None, "il puntatore al successore è rimasto"
    assert at is None, "la data di ritiro è rimasta"
    assert reason is None, (
        "IL MOTIVO DEL RITIRO È RIMASTO: il fatto è vivo e porta scritto "
        f"perché era stato ritirato — {reason!r}")


def test_la_riparazione_lascia_una_traccia_su_file(store: Path):
    """⚠️ Il registro esiste perché la cura CANCELLA l'informazione: senza,
    il motivo per cui il fatto era stato ritirato sparirebbe con esso."""
    _esegui(store, "--apply")
    traccia = store.parent / "ripristini.log"
    assert traccia.exists(), "nessun registro della riparazione"
    righe = traccia.read_text(encoding="utf-8").strip().splitlines()
    assert righe, "il registro è vuoto"
    assert "vecchio" in righe[0], f"il fatto toccato non è nominato: {righe[0]!r}"
    assert "same-source evolution" in righe[0], (
        f"il motivo che è stato cancellato non è stato registrato: {righe[0]!r}")


def test_IL_DRY_RUN_non_tocca_niente(store: Path):
    """⚠️ IL PRESIDIO. Lo script gira di default senza `--apply`, e chi lo
    prova per vedere cosa farebbe non deve trovarsi il database modificato —
    né un registro che dichiara riparazioni mai avvenute."""
    esito = _esegui(store)
    assert esito.returncode == 0, esito.stderr[-600:]
    by, at, reason = _riga(store, "vecchio")
    assert (by, at, reason) == ("nuovo", "2026-08-01", "same-source evolution"), (
        "il dry-run ha modificato il database")
    assert not (store.parent / "ripristini.log").exists(), (
        "il dry-run ha scritto un registro di riparazioni mai avvenute")
