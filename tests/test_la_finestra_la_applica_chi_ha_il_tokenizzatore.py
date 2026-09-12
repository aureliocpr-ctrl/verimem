"""T73 — chi delega il giudizio non deve pagare il tokenizzatore.

IL FATTO, misurato alla porta il 2026-09-12 su un server che DELEGA:

    server importato                    171,9 MB
    dopo `try_local_score`             1464,0 MB   in 31,73 s
      scorer locale caricato = False   <- il giudizio l'ha fatto il daemon

Il giudizio era gia' delegato e funzionava. A costare 1292 MB e 31,7 secondi
era la PREPARAZIONE della domanda: `coppia()` riduce lo span alla finestra del
modello contando i TOKEN, e per contarli carica il tokenizzatore, che tira
dentro `transformers` e con lui `torch`.

⚠️ QUESTE CELLE NON MISURANO I MEGABYTE, e non e' una rinuncia: il commit
dipende dalla macchina, da cosa c'e' gia' importato e da chi altro gira, quindi
un banco che lo assertisse direbbe cose diverse su macchine diverse. Misurano
la CAUSA — se il tokenizzatore viene toccato — che e' deterministica e vale
ovunque.
"""
from __future__ import annotations

import pytest

from verimem import encode_service, local_grounding


class _GiudiceFinto:
    """Un giudice che REGISTRA se qualcuno gli chiede il tokenizzatore."""

    max_length = 512
    focus_budget = 1500
    threshold = 99.0
    normalizza = staticmethod(float)

    def __init__(self) -> None:
        self.richieste_del_tokenizzatore = 0
        self._scorer = None

    def _tokenizzatore(self):
        self.richieste_del_tokenizzatore += 1
        return None

    # le due vere, prese dalla classe di produzione
    coppia = local_grounding.LocalGroundingJudge.coppia
    _entro_la_finestra = local_grounding.LocalGroundingJudge._entro_la_finestra


def test_senza_finestra_il_tokenizzatore_non_viene_nemmeno_chiesto() -> None:
    """Il cuore: `applica_finestra=False` non tocca il tokenizzatore.

    E' la riga che toglie 1292 MB al processo che delega. Se qualcuno rimette
    la riduzione qui dentro, questo conteggio diventa 1 e la cella cade.
    """
    g = _GiudiceFinto()
    span, fatto = g.coppia("una fonte qualunque", "un fatto", applica_finestra=False)
    assert g.richieste_del_tokenizzatore == 0, (
        "costruire la coppia ha chiesto il tokenizzatore anche con "
        "applica_finestra=False: e' esattamente il costo che questa cura toglie")
    assert fatto == "un fatto"
    assert span, "lo span non deve sparire: si rimanda la riduzione, non il testo"


def test_col_default_la_finestra_si_applica_ancora() -> None:
    """L'altra gamba: il comportamento di prima non cambia per chi non delega.

    Senza questa cella la cura potrebbe aver semplicemente SPENTO la riduzione
    per tutti, e la prima cella passerebbe lo stesso.
    """
    g = _GiudiceFinto()
    g.coppia("una fonte qualunque", "un fatto")
    assert g.richieste_del_tokenizzatore == 1, (
        "con il default la riduzione non e' stata nemmeno tentata: la cura ha "
        "spento la finestra invece di spostarla")


def test_il_daemon_riduce_lo_span_se_gli_mandi_la_finestra(monkeypatch) -> None:
    """L'altro capo: il daemon applica la finestra quando riceve `max_length`.

    Se non lo facesse, lo span arriverebbe intero al modello, che tronca da se'
    DALLA CODA — la perdita che `_entro_la_finestra` esiste per rendere
    leggibile. Delegare senza questa riga sposterebbe il costo e butterebbe la
    qualita'.
    """
    visti: list[tuple[str, str]] = []

    server = object.__new__(encode_service.EncodeServer)
    server._token = "t"
    server._gate_fn = lambda coppie: (visti.extend(coppie) or [1.0] * len(coppie))
    server._rerank_fn = None
    server._encode_fn = None

    lungo = "\n".join(f"riga numero {i} del documento" for i in range(200))

    class _GiudiceCheRiduce:
        max_length = 8

        def _entro_la_finestra(self, span: str) -> str:
            return span.splitlines()[0]

    monkeypatch.setattr(local_grounding, "get_local_judge", _GiudiceCheRiduce)

    resp = server._handle_request(
        {"token": "t", "gate_pairs": [[lungo, "un fatto"]], "max_length": 8})

    assert resp["ok"], resp
    assert visti, "il giudice del daemon non e' stato chiamato affatto"
    span_giudicato = visti[0][0]
    assert span_giudicato == "riga numero 0 del documento", (
        "il daemon ha giudicato lo span INTERO: la finestra non e' stata "
        f"applicata di qua e nessuno l'ha applicata di la'. Span: {span_giudicato[:80]!r}")


def test_senza_max_length_il_daemon_non_tocca_lo_span() -> None:
    """Il contrario, perche' un criterio vale solo se puo' non applicarsi:
    un client vecchio manda la coppia gia' ridotta e il daemon non ci mette mano."""
    visti: list[tuple[str, str]] = []
    server = object.__new__(encode_service.EncodeServer)
    server._token = "t"
    server._gate_fn = lambda coppie: (visti.extend(coppie) or [1.0] * len(coppie))

    resp = server._handle_request(
        {"token": "t", "gate_pairs": [["gia' ridotto dal client", "un fatto"]]})

    assert resp["ok"], resp
    assert visti[0][0] == "gia' ridotto dal client"


def test_il_daemon_dichiara_se_sa_ridurre() -> None:
    """La chiave che il client legge per decidere: dichiarata, non indovinata.

    Senza, il client dovrebbe SUPPORRE che il daemon sappia ridurre — e con un
    daemon vecchio lo span arriverebbe intero, cioe' una perdita di qualita'
    silenziosa. Il valore segue la capacita' vera (`_gate_fn`), non una costante.
    """
    import inspect

    sorgente = inspect.getsource(encode_service.EncodeServer._write_discovery)
    assert '"applies_window": self._gate_fn is not None' in sorgente, (
        "il daemon non dichiara piu' se sa ridurre, o lo dichiara con una "
        "costante invece che dalla capacita' vera: il client tornerebbe a "
        "indovinare")


@pytest.mark.parametrize("il_daemon_riduce", [True, False])
def test_il_client_chiede_la_riduzione_solo_a_chi_l_ha_dichiarata(
        monkeypatch, il_daemon_riduce: bool) -> None:
    """La giuntura: il client manda `max_length` SOLO al daemon che si e'
    dichiarato capace, e negli altri casi riduce di qua come sempre."""
    chiamate: dict = {}

    def _finto_gate_via_daemon(pairs, *, info=None, max_length=None):
        chiamate["max_length"] = max_length
        chiamate["span"] = pairs[0][0]
        return [42.0]

    monkeypatch.setattr(local_grounding, "_gate_via_daemon", _finto_gate_via_daemon)
    monkeypatch.setattr(local_grounding, "_delegate_only", lambda: True)
    monkeypatch.setattr(
        local_grounding.encode_service if hasattr(local_grounding, "encode_service")
        else encode_service, "read_discovery",
        lambda *a, **k: {"port": 1, "applies_window": il_daemon_riduce})

    giudice = _GiudiceFinto()
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: giudice)

    r = local_grounding.try_local_score("una fonte", "un fatto")

    assert r is not None and r[0] == 42.0
    if il_daemon_riduce:
        assert chiamate["max_length"] == giudice.max_length, (
            "il daemon sa ridurre ma il client non gli ha mandato la finestra")
        assert giudice.richieste_del_tokenizzatore == 0, (
            "il client ha caricato il tokenizzatore pur delegando la riduzione")
    else:
        assert chiamate["max_length"] is None, (
            "il client ha chiesto la riduzione a un daemon che non l'ha dichiarata")
        assert giudice.richieste_del_tokenizzatore == 1, (
            "col daemon vecchio nessuno ha ridotto lo span: la qualita' cala "
            "in silenzio, che e' il caso che questa cura NON deve creare")
