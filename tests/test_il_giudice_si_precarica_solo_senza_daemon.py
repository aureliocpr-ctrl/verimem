"""Il giudice del moat si precarica in casa SOLO se il daemon non sa giudicare.

Con `ENGRAM_GROUNDING_WRITE=1` ogni server MCP caricava torch e il
cross-encoder all'avvio, senza chiedere al daemon condiviso. MISURATO il
2026-09-23 con `preload_embedding()` e i flag del server vero, un braccio per
processo: 140 MB senza il flag, 1002 MB con il flag — 862 MB per server solo
per il giudice. Con la cura e il daemon che giudica: 147 MB.

E non era solo memoria: una volta pieno `judge._scorer`, `try_local_score`
smetteva di chiedere al daemon per tutta la vita del server, anche con la
delega richiesta.

QUESTO FILE NON CARICA NESSUN MODELLO. Il giudice e' finto (conta le chiamate
a `_ensure_scorer`), e il daemon si simula sostituendo `_gate_via_daemon`, che
e' proprio la domanda che la cura fa: «sai giudicare?». Non
`encode_service.daemon_usable()`, che risponde a un'altra domanda — se il
daemon serve il nostro modello di embedding.
"""

from __future__ import annotations

import time

import pytest

from verimem import local_grounding, preload


class _GiudiceFinto:
    def __init__(self):
        self.caricamenti = 0

    def _ensure_scorer(self):
        self.caricamenti += 1


@pytest.fixture
def giudice(monkeypatch, tmp_path):
    # I TRE alias della cartella dati (verimem/_compat.py), non due: con uno
    # solo ereditato fuori, una scrittura finirebbe nello store vero.
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(alias, str(tmp_path))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(tmp_path / "eventi.jsonl"))
    # ⚠️ Il conftest spegne il servizio per ogni test (ENGRAM_ENCODE_SERVICE=0):
    # senza questa riga la sonda non partirebbe mai e la cella misurerebbe il
    # caso «servizio spento», non quello della cura.
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    # L'attesa del daemon e' di 25 s nel prodotto: qui non si aspetta.
    monkeypatch.setattr(preload, "_DAEMON_WARM_WAIT_S", 0.0)
    # ⛔ 28/09: e nessun daemon IN ARRIVO. Dopo l'attesa il precarico aspetta
    # ancora finche' `encode_service.daemon_in_arrivo()` dice che un daemon tiene
    # il lock, e quel lock e' il file VERO della home: su una macchina col daemon
    # acceso la cella si appendeva fino alla grazia del daemon (600 s), e sul
    # runner macOS di #162 l'ha fatto un daemon lasciato vivo da un altro test.
    # Le celle di questo file misurano «nessun daemon in arrivo»; il caso in
    # arrivo lo misura `test_la_sonda_aspetta_il_daemon_in_arrivo.py`.
    monkeypatch.setattr(preload, "_un_daemon_e_in_arrivo", lambda: False)
    finto = _GiudiceFinto()
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: finto)
    return finto


def test_se_il_daemon_giudica_il_giudice_non_si_carica_in_casa(giudice, monkeypatch):
    """LA CURA. RED sul tronco: li' il precarico non chiede niente al daemon."""
    monkeypatch.setattr(local_grounding, "_gate_via_daemon",
                        lambda *a, **k: [0.9])
    preload._warm_moat_judge(log=None)
    assert giudice.caricamenti == 0, (
        "il daemon sa giudicare e il server si e' caricato il giudice lo stesso: "
        "862 MB per server, e da li' niente piu' delega")


def test_se_il_daemon_non_giudica_il_precarico_resta(giudice, monkeypatch):
    """IL RIPIEGO E' IL COMPORTAMENTO DI OGGI. Verde sul tronco e sul ramo: se
    diventa rosso, la cura ha riaperto il buco della prima scrittura non
    giudicata, che il precarico esiste per chiudere."""
    monkeypatch.setattr(local_grounding, "_gate_via_daemon",
                        lambda *a, **k: None)
    preload._warm_moat_judge(log=None)
    assert giudice.caricamenti == 1, (
        "il daemon non sa giudicare e il giudice non si e' caricato: la prima "
        "scrittura resterebbe non giudicata")


def test_senza_servizio_nessuna_sonda_e_il_precarico_resta(giudice, monkeypatch):
    """Nessuna sonda se il servizio e' spento: il giudice si carica come oggi."""
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    sonde = []
    monkeypatch.setattr(local_grounding, "_gate_via_daemon",
                        lambda *a, **k: sonde.append(1) or [0.9])
    preload._warm_moat_judge(log=None)
    assert sonde == [], "con il servizio spento non si interroga il daemon"
    assert giudice.caricamenti == 1


def test_la_cella_non_dipende_dal_daemon_della_macchina(giudice, monkeypatch):
    """GUARDIA del 28/09: la macchina che esegue ha un daemon che tiene il lock
    (qui simulato, con l'attesa accorciata a 3 s), e la cella deve rispondere
    subito lo stesso. Senza la riga della fixture aspettava quel daemon."""
    from verimem import encode_service
    monkeypatch.setattr(encode_service, "daemon_in_arrivo", lambda *a, **k: True)
    monkeypatch.setattr(preload, "_tetto_dell_arrivo_s", lambda: 3.0)
    monkeypatch.setattr(local_grounding, "_gate_via_daemon", lambda *a, **k: None)

    inizio = time.monotonic()
    preload._warm_moat_judge(log=None)

    assert time.monotonic() - inizio < 2.0, (
        "la cella ha aspettato il daemon della macchina che la esegue")
    assert giudice.caricamenti == 1

