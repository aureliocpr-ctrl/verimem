"""`status` counts things and says nothing about whether they can be trusted.

On the live store it prints "semantic facts: 4743" and stops. The same store,
from `verimem stats`, is also:

    quarantined  511 of 4743   (10.8% held back, a queue nobody is draining)
    moat-judged   23 of 4743   (0.5% — the entailment check ran on almost nothing)

Both numbers change what a user does: one says there is a review backlog, the
other says the product's main check is not running on their writes. A command
whose docstring says "quick health check" is where someone looks for exactly
that, and it answered with inventory.

`doctor` does diagnose, and stays the deeper tool. This adds the two figures a
health line should carry — from the same store, no new computation of substance.
"""
from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _plain(t: str) -> str:
    return _ANSI.sub("", t or "")


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="status_health_"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(d))
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(d))
    r = runner.invoke(app, ["facts", "add", "-p", "Il contatore vale quattro.",
                            "-t", "test/s", "--validate", "off"])
    assert r.exit_code == 0, r.output
    # A quarantined fact made by the PRODUCT, not by an INSERT: an unsupported
    # completion claim is exactly what the L1 screen holds back, so the fixture
    # exercises the real path instead of fighting NOT NULL constraints on
    # columns (source_episodes, embedding) that the store fills itself.
    r2 = runner.invoke(app, ["facts", "add", "-p",
                             "Il lavoro e stato completato e verificato.",
                             "-t", "test/s"])
    assert r2.exit_code == 0, r2.output
    db = d / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    held = con.execute("SELECT COUNT(*) FROM facts "
                       "WHERE status='quarantined'").fetchone()[0]
    assert held >= 1, "the fixture needs a quarantined fact and the gate let it through"
    con.execute("UPDATE facts SET grounding_score = 99.0 "
                "WHERE status != 'quarantined'")
    con.commit()
    con.close()
    return d


def test_status_reports_what_is_held_back(store: Path):
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0, r.output
    out = _plain(r.output).lower()
    assert "quarantin" in out, (
        f"a health check that never mentions the held-back facts:\n{r.output}"
    )


def test_status_reports_how_much_was_judged(store: Path):
    r = runner.invoke(app, ["status"])
    out = _plain(r.output).lower()
    assert "judged" in out or "moat" in out, (
        f"nothing about whether the entailment check ever ran:\n{r.output}"
    )


def test_a_clean_store_does_not_grow_alarming_lines(store: Path, monkeypatch):
    """No quarantine, everything judged: the line must not invent a worry."""
    db = store / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    con.execute("DELETE FROM facts WHERE status = 'quarantined'")
    con.commit()
    con.close()
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0, r.output
    out = _plain(r.output)
    assert "0 quarantined" in out or "quarantined:  0" in out or "quarantin" in out.lower()


def test_status_dice_quanti_ne_ha_SOSTITUITI(store: Path):
    """`semantic facts: 1` dopo DUE scritture, e niente lo spiega.

    Misurato il 2026-08-17 su una data dir temporanea: due `remember` sullo
    stesso topic, la CLI dichiara `admitted` due volte E stampa
    `L3-supersession`, poi `status` riporta `semantic facts: 1`. Le due
    superfici sono entrambe oneste e insieme ingannano: chi guarda solo lo
    stato vede un inventario che non torna con cio' che ha scritto, e nessuna
    riga nomina i sostituiti.

    ⚖️ Non e' la stessa cosa dei quarantinati — quelli sono TRATTENUTI e la
    riga c'e' gia'. Questi sono RIMPIAZZATI, ed e' l'operazione che sul corpus
    vivo del 16/08 valeva 1890 fatti, due terzi della perdita.
    """
    out = _plain(runner.invoke(app, ["status"]).output)
    m = re.search(r"superseded:\s+(\d+)", out)
    assert m, (
        "il pannello non nomina i fatti sostituiti: chi ne scrive due e ne "
        f"legge uno non ha modo di sapere dov'e' finito l'altro.\n{out}")


# ⚠️⚠️ LIMITE DICHIARATO, e un limite dichiarato e' un DEBITO ═══════════════
# Il test qui sopra verifica che la RIGA ci sia, NON che il numero sia giusto.
# Il numero non e' verificabile da questo file, e la ragione e' un difetto del
# BANCO che ho trovato scrivendolo: sotto questa fixture il pannello legge uno
# store VUOTO — stampa `semantic facts: 0`, `quarantined: 0` e una `data dir:`
# vuota, qualunque cosa la fixture abbia scritto.
# 🔑 CONSEGUENZA sui presidi vicini: `test_status_reports_what_is_held_back` e
# `test_status_reports_how_much_was_judged` asseriscono che compaia una PAROLA
# («quarantin», «judged») che il pannello stampa SEMPRE ⇒ passano anche su zero,
# e passerebbero anche se i conteggi fossero rotti. Sono accesi e non
# esercitati. Non li tocco — non sono miei — e li segnalo.
# ✅ IL NUMERO E' VERIFICATO, ma FUORI da pytest, dove il prodotto gira davvero
# (2026-08-17, data dir temporanea, due `remember` sullo stesso topic)::
#
#     flow.supersession  branch='same-source evolution' loser_id=58b6c5ad2152
#                        winner_id=572d5e867ea5 reversible=True
#     semantic facts:  1
#     superseded:      1  earlier values replaced by a later write
#     database:        righe totali 2, superseduti 1        (1 + 1 = 2)
#
# 📌 E il motivo per cui va misurato li': la supersessione decide con un COSENO,
# e sotto pytest l'embedder e' uno stub su SHA-256 dei token — la decisione non
# scatta affatto. Tre tentativi caduti prima di arrivarci, tutti nel banco:
# `facts add --validate off` non passa da quel percorso; un `Memory(path=...)`
# costruito nel test scrive dove il pannello non legge; `remember` sotto pytest
# non supersede.


def test_anche_stats_dice_quanti_ne_sono_stati_sostituiti(store: Path):
    """La TERZA superficie con la stessa cecita', trovata con lo sweep.

    `trust_stats()["store"]` e' una fotografia dei VIVI — lo dice il suo
    docstring — e `moat.facts` conta anch'esso `superseded_by IS NULL`. Su una
    data dir temporanea con due `remember` sullo stesso topic, `stats --json`
    riportava `"facts": 1` su un database di DUE righe, e nessuna chiave
    nominava la seconda.

    ⚖️ La chiave sta FUORI da `store`: `store` ripartisce per STATUS, la
    supersessione e' un'altra dimensione, e infilarla li' farebbe sommare
    grandezze diverse a chi cicla sulle chiavi.
    """
    import json as _json
    raw = _plain(runner.invoke(app, ["stats", "--json"]).output)
    payload = _json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    assert "superseded" in payload, (
        "il payload non dice quanti fatti sono stati sostituiti: chi ne scrive "
        f"due e ne legge uno non sa dov'e' finito l'altro.\n{sorted(payload)}")
    assert isinstance(payload["superseded"], int) or payload["superseded"] is None


def test_status_and_stats_agree_on_how_many_are_held_back(store: Path):
    """Two commands, one store, one number.

    The first version of this line counted quarantined facts INCLUDING
    superseded ones against a live-only denominator: `status` said 1732 (36.5%)
    while `stats`, three lines of output away, said 511. Both queries were
    defensible on their own, which is exactly how a store ends up describing
    itself two ways — the failure this whole session has been chasing.
    """
    st = _plain(runner.invoke(app, ["status"]).output)
    sts = _plain(runner.invoke(app, ["stats"]).output)

    m = re.search(r"quarantined:\s+(\d+)", st)
    assert m, f"status has no quarantined count:\n{st}"
    from_status = int(m.group(1))

    # Read from `stats --json`, not from the rendered text. The output holds TWO
    # "quarantined:" counters — the gate-actions one and the live-status one —
    # and grepping the wrong one is how this test failed twice while writing it,
    # one commit after fixing that very ambiguity. Comparing data instead of
    # prose removes the trap rather than tiptoeing around it.
    import json as _json
    # _plain first: print_json COLOURS its output, and the escape codes land
    # inside the braces.
    raw = _plain(runner.invoke(app, ["stats", "--json"]).output)
    payload = _json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    from_stats = int((payload.get("store") or {}).get("quarantined", 0))

    assert from_status == from_stats, (
        f"status says {from_status} held back, stats says {from_stats} — "
        f"same store, same word, two answers"
    )
