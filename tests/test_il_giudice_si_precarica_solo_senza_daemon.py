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
