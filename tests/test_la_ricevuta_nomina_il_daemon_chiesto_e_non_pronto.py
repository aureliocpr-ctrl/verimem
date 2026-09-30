"""Chi ha chiesto il servizio condiviso e non l'ha avuto legge PERCHE' nella ricevuta.

Riga 3 del tabellone, seconda cella: se l'utente ha chiesto il servizio condiviso
(`HIPPO_ENCODE_DELEGATE_ONLY=1`) e il giudizio non e' venuto da li', la ricevuta gli dice
perche'. Quando il daemon non ha giudicato e il giudice di casa stava ancora caricando,
la ragione del livello L4-skipped diceva solo «the grounding judge was still loading»:
il daemon chiesto lo nominava il consiglio, non la ragione. MISURATO dal wheel nel job
di accettazione del 29/09 (job 109551779207): `judged_by=None` e la ragione senza la
parola daemon. Su main la cella passava perche' le celle prima avevano gia' scaldato un
daemon nella home condivisa del job.

Il difetto sta nel ramo della delega fallita di `try_local_score`: registrava solo
«nessuno ha giudicato», senza dire che il daemon era stato chiesto ne' perche' non ha
giudicato, e la ragione del livello non aveva niente da raccontare.

NESSUN MODELLO: un giudice finto mai caricato, nessun daemon annunciato.
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate as gate
from verimem import encode_service
from verimem import local_grounding as lg

RAGIONE_DI_PRIMA = ("source provided but the grounding judge was still loading - "
                    "entailment NOT verified for THIS write")


class _GiudiceFreddo:
    """Il giudice di casa che non ha ancora caricato niente."""
    _scorer = None
    max_length = 512
    threshold = 40.0

    def coppia(self, source, fact, *, focus_budget=None, applica_finestra=True):
        return (source, fact)

    def normalizza(self, punteggio):
        return punteggio


@pytest.fixture
def delega_senza_daemon(monkeypatch):
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    # il servizio acceso, come per un utente: la suite lo spegne per tutti
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    monkeypatch.setattr(lg, "get_local_judge", lambda: _GiudiceFreddo())
    monkeypatch.setattr(lg, "warm_local_judge_async", lambda: None)
    monkeypatch.setattr(lg, "judge_state", lambda: "warming")
    monkeypatch.setattr(encode_service, "read_discovery", lambda *a, **k: None)
    yield
    # lo stato e' per thread: non si lascia ai test che girano dopo
    lg._registra_esecutore(None)
    lg._rifiuto_del_giudice.motivo = None


def test_la_delega_fallita_lascia_scritto_che_era_chiesta_e_perche(delega_senza_daemon):
    """RED sul tronco: il ramo registrava solo «nessuno ha giudicato»."""
    assert lg.try_local_score("We migrated to Postgres.", "Analytics runs on Postgres.") is None

    assert lg.la_delega_era_richiesta(), "la delega era chiesta e la ricevuta non lo sa"
    assert "daemon" in (lg.perche_ha_giudicato() or ""), lg.perche_ha_giudicato()


def test_la_ragione_del_livello_nomina_il_daemon_chiesto(delega_senza_daemon):
    """RED sul tronco: la ragione era la stessa di chi il daemon non l'ha mai chiesto."""
    lg.try_local_score("We migrated to Postgres.", "Analytics runs on Postgres.")

    ragione = gate._advisory_l4_skipped()["reason"]

    assert "daemon" in ragione.lower(), ragione
    assert "still loading" in ragione, ragione


def test_il_daemon_che_rifiuta_lo_dice_con_il_suo_motivo(delega_senza_daemon, monkeypatch):
    monkeypatch.setattr(encode_service, "read_discovery", lambda *a, **k: {"port": 1})

    def rifiuta(pairs, *, info=None, max_length=None):
        lg._rifiuto_del_giudice.motivo = "this daemon cannot judge"
        return None

    monkeypatch.setattr(lg, "_gate_via_daemon", rifiuta)

    lg.try_local_score("We migrated to Postgres.", "Analytics runs on Postgres.")

    assert "this daemon cannot judge" in gate._advisory_l4_skipped()["reason"]


def test_col_servizio_spento_lo_dice(delega_senza_daemon, monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")

    lg.try_local_score("We migrated to Postgres.", "Analytics runs on Postgres.")

    assert "ENGRAM_ENCODE_SERVICE=0" in gate._advisory_l4_skipped()["reason"]


def test_senza_delega_la_ragione_non_cambia(monkeypatch):
    """GUARDIA: chi il daemon non l'ha chiesto legge la ragione di sempre."""
    monkeypatch.setattr(lg, "judge_state", lambda: "warming")
    lg._registra_esecutore(None)

    assert gate._advisory_l4_skipped()["reason"] == RAGIONE_DI_PRIMA
