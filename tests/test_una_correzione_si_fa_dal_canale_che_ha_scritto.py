"""Chi puo' scrivere dalla riga di comando deve poter correggere dalla riga di comando.

Trovato il 2026-07-31 **avendone bisogno**, non ispezionando: avevo appena
salvato un fatto passando come `--source` una versione riordinata di uno stack
trace invece dell'output verbatim, e volevo rimediare. La CLI ha `remember`,
`recall`, `stats`, `trust`, `ignorance`, `index`, `search-docs`, `doctor`,
`airgap`, `import`, `console`, `dashboard`, `telemetry`, `introspect`,
`agent-guide`, `backup-all`, `reset` — e nessun modo di **correggere un fatto
gia' scritto**. Come `recall --as-of` stamattina, la capacita' c'e' e la porta
no::

    MCP  hippo_fact_supersede                    dichiarato
    SDK  SemanticMemory.supersede(old, new, …)   completo (semantic.py:5151)
    CLI  verimem correct                         NO

E' la seconda occorrenza della stessa classe in un giorno, il che la rende una
classe e non un caso: una capacita' matura raggiungibile solo dai canali che gli
altri agenti usano, invisibile a chi usa il terminale.

Per un prodotto la cui tesi e' «scritture sorvegliate, provenienza su ogni
lettura», poter scrivere e non poter correggere e' il buco piu' scomodo: la
prima cosa che si vuole fare dopo aver capito di aver scritto male e' rimediare,
e se il canale non lo permette il fatto sbagliato resta la verita' dello store.

IL GESTO GIUSTO E' UNO SOLO. `supersede(old_id, new_id)` pretende che il nuovo
fatto esista gia': dalla riga di comando sarebbero due comandi e un id da
ricopiare, e soprattutto si potrebbe soprassedere un fatto buono con uno che il
gate non ha ammesso. `verimem correct <old_id> "<nuovo testo>" --source …`
scrive il nuovo fatto **attraverso il moat** e solo dopo dichiara la
supersessione.

L'INVARIANTE CHE VALE PIU' DEL COMANDO, ed e' la ragione per cui questo file
esiste: **se la correzione non passa il gate, la supersessione NON avviene.**
Altrimenti il vecchio fatto uscirebbe dal recall di default e il nuovo ci
resterebbe fuori perche' quarantinato — la conoscenza sparirebbe da entrambe le
parti, e sarebbe il prodotto stesso a farla sparire, usando il suo gate come
arma contro la sua memoria. Meglio due fatti in contesa che zero.
"""
from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _pulito(r) -> str:
    return _ANSI.sub("", r.output)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """La CLI legge da `CONFIG`, congelato all'import: i test che la invocano
    devono scrivere DOVE LA CLI LEGGE, non in una tmp_path che il comando non
    guarda. Trappola gia' pagata su `status` e su `recall --as-of`."""
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.config import CONFIG
    from verimem.semantic import SemanticMemory
    return SemanticMemory(db_path=CONFIG.semantic_db)


def _scrivi(store, testo: str, source: str) -> str:
    r = runner.invoke(app, ["remember", testo, "--topic", "prova/correzioni",
                            "--source", source])
    out = _pulito(r)
    assert r.exit_code == 0, out
    m = re.search(r"id=([0-9a-f]{6,})", out)
    assert m, f"remember non ha stampato un id: {out}"
    return m.group(1)


def test_la_cli_sa_correggere_un_fatto_che_ha_scritto(store):
    fonte = "Il database di produzione e' PostgreSQL versione 16."
    vecchio = _scrivi(store, "Il database di produzione e' PostgreSQL.", fonte)
    r = runner.invoke(app, ["correct", vecchio,
                            "Il database di produzione e' PostgreSQL versione 16.",
                            "--source", fonte,
                            "--reason", "la versione mancava"])
    out = _pulito(r)
    assert r.exit_code == 0, out
    assert "superseded" in out.lower() or "corretto" in out.lower(), out


def test_una_correzione_QUARANTINATA_non_supersede_niente(store):
    """L'invariante. Il vecchio fatto deve restare in piedi: due fatti in
    contesa sono recuperabili, zero no."""
    fonte = "Il rimborso avviene entro 7 giorni lavorativi."
    vecchio = _scrivi(store, "Il rimborso avviene entro 7 giorni lavorativi.", fonte)
    r = runner.invoke(app, ["correct", vecchio,
                            "Il rimborso avviene entro 24 ore.",
                            "--source", fonte])
    out = _pulito(r)
    assert r.exit_code != 0, (
        f"una correzione che il gate non ammette e' uscita con successo: {out}")
    assert "quarantin" in out.lower() or "not stored" in out.lower(), out
    rimasto = store.get(vecchio)
    assert rimasto is not None, "il fatto vecchio e' sparito"
    assert not getattr(rimasto, "superseded_by", None), (
        f"il fatto vecchio e' stato superato da una correzione che il gate ha "
        f"respinto: superseded_by={getattr(rimasto, 'superseded_by', None)}")


def test_un_id_che_non_esiste_lo_dice_invece_di_scrivere_e_basta(store):
    """Senza questo, `correct` su un id sbagliato lascerebbe nello store un
    fatto nuovo orfano e nessuna correzione — il peggiore dei due esiti,
    perche' sembra riuscito."""
    r = runner.invoke(app, ["correct", "0" * 12, "Un fatto qualunque.",
                            "--source", "Un fatto qualunque."])
    out = _pulito(r)
    assert r.exit_code != 0, out
    assert "non trovato" in out.lower() or "not found" in out.lower(), out


def test_dopo_la_correzione_il_recall_serve_la_versione_nuova(store):
    """La prova che la supersessione ha davvero effetto sul canale di lettura:
    senza questa, `correct` potrebbe scrivere una riga in una tabella che
    nessuno guarda."""
    fonte = "Il cluster gira su tre nodi in Irlanda."
    vecchio = _scrivi(store, "Il cluster gira su tre nodi.", fonte)
    r = runner.invoke(app, ["correct", vecchio,
                            "Il cluster gira su tre nodi in Irlanda.",
                            "--source", fonte])
    assert r.exit_code == 0, _pulito(r)
    letto = _pulito(runner.invoke(app, ["recall", "dove gira il cluster"]))
    assert "irlanda" in letto.lower(), letto
