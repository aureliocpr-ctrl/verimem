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
        chiamate: list[int | None] = []

        # ⚠️ LA FIRMA E' QUELLA VERA, col budget per parametro. Se un doppio
        # resta alla firma vecchia, il daemon lo chiama con due argomenti, il
        # `except Exception` del prodotto INGOIA il TypeError e lo span esce
        # intero: il sintomo e' «la finestra non e' stata applicata», non «hai
        # sbagliato la firma». Un `except` largo nasconde anche gli errori di
        # programmazione, e la cella qui sotto distingue i due casi apposta.
        def _entro_la_finestra(self, span: str, max_length=None) -> str:
            type(self).chiamate.append(max_length)
            return span.splitlines()[0]

    monkeypatch.setattr(local_grounding, "get_local_judge", _GiudiceCheRiduce)

    resp = server._handle_request(
        {"token": "t", "gate_pairs": [[lungo, "un fatto"]], "max_length": 8})

    assert resp["ok"], resp
    assert visti, "il giudice del daemon non e' stato chiamato affatto"
    assert _GiudiceCheRiduce.chiamate, (
        "il daemon non ha nemmeno PROVATO a ridurre: o non legge `max_length`, "
        "oppure ci ha provato e un'eccezione e' stata ingoiata dal best-effort")
    assert _GiudiceCheRiduce.chiamate == [8], (
        f"il daemon ha passato una finestra diversa da quella chiesta: "
        f"{_GiudiceCheRiduce.chiamate}")
    span_giudicato = visti[0][0]
    assert span_giudicato == "riga numero 0 del documento", (
        "il daemon ha giudicato lo span INTERO pur avendo chiamato la "
        f"riduzione. Span: {span_giudicato[:80]!r}")


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


# ─────────────────────────────────────────────────────────────────────────────
# IL BUDGET NON PUO' PASSARE DA UNO STATO CONDIVISO
#
# Rilievo in revisione, 2026-09-12: la prima versione di questa cura passava il
# budget al daemon scrivendolo su `giudice.max_length` e rimettendolo a posto
# nel `finally`. Ma il daemon fa UN THREAD PER CONNESSIONE, quindi quello e'
# stato condiviso mutato da piu' thread: due richieste con budget diversi si
# sovrascrivono il valore a vicenda, e il danno non e' un errore ma UNO SPAN
# TAGLIATO CON LA FINESTRA DI UN ALTRO — silenzioso, e nel giudizio.
# ─────────────────────────────────────────────────────────────────────────────


class _GiudiceCheRegistraLeScritture:
    """Riduce come quello vero, e URLA se qualcuno gli scrive `max_length`."""

    def __init__(self) -> None:
        object.__setattr__(self, "scritture_di_max_length", [])
        object.__setattr__(self, "max_length", 512)

    def __setattr__(self, nome: str, valore) -> None:
        if nome == "max_length":
            self.scritture_di_max_length.append(valore)
        object.__setattr__(self, nome, valore)

    def _entro_la_finestra(self, span: str, max_length=None) -> str:
        limite = int(max_length) if max_length else self.max_length
        return span[:limite]


def test_il_daemon_non_scrive_il_budget_su_uno_stato_condiviso(monkeypatch) -> None:
    """LA GAMBA COSTRUTTIVA: nessuna corsa, nessun timing — si guarda se
    qualcuno SCRIVE l'attributo. Vale su ogni macchina e non puo' passare per
    fortuna, che e' quello che una corsa riprodotta a caso farebbe."""
    giudice = _GiudiceCheRegistraLeScritture()
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: giudice)

    server = object.__new__(encode_service.EncodeServer)
    server._token = "t"
    server._gate_fn = lambda coppie: [1.0] * len(coppie)

    server._handle_request(
        {"token": "t", "gate_pairs": [["x" * 100, "un fatto"]], "max_length": 7})

    assert giudice.scritture_di_max_length == [], (
        "il daemon ha SCRITTO max_length sul giudice condiviso: con un thread "
        "per connessione due richieste con budget diversi si sovrascrivono il "
        f"valore. Scritture viste: {giudice.scritture_di_max_length}")


def test_due_richieste_insieme_con_budget_diversi_non_si_rubano_la_finestra(
        monkeypatch) -> None:
    """LA GAMBA CONCORRENTE, e la sovrapposizione e' GARANTITA da una barriera.

    Senza la barriera i due thread potrebbero non incrociarsi mai e la cella
    passerebbe anche col difetto — «una corsa riprodotta con un'altra corsa non
    prova niente». Qui nessuno dei due puo' uscire dalla riduzione finche' non
    ci sono entrati tutt'e due: se il budget passasse da uno stato condiviso,
    il secondo troverebbe il valore del primo SEMPRE, non per caso.
    """
    import threading

    dentro = threading.Barrier(2, timeout=10)

    class _GiudiceLento(_GiudiceCheRegistraLeScritture):
        def _entro_la_finestra(self, span: str, max_length=None) -> str:
            limite = int(max_length) if max_length else self.max_length
            dentro.wait()          # tutti e due dentro, poi si taglia
            return span[:limite]

    giudice = _GiudiceLento()
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: giudice)

    server = object.__new__(encode_service.EncodeServer)
    server._token = "t"
    visti: dict[int, str] = {}
    server._gate_fn = lambda coppie: [1.0] * len(coppie)

    def una_richiesta(budget: int) -> None:
        r = dict(server._handle_request({
            "token": "t",
            "gate_pairs": [["x" * 100, "un fatto"]],
            "max_length": budget,
        }))
        visti[budget] = r.get("_span_giudicato", "")

    # lo span giudicato si recupera dal gate_fn, che lo registra per budget
    def _registra(coppie):
        for s, _f in coppie:
            visti[len(s)] = s
        return [1.0] * len(coppie)

    server._gate_fn = _registra

    thread = [threading.Thread(target=una_richiesta, args=(b,)) for b in (7, 41)]
    for t in thread:
        t.start()
    for t in thread:
        t.join(timeout=15)

    assert 7 in visti and 41 in visti, (
        "uno dei due budget non e' arrivato al giudice: le due richieste si sono "
        f"rubate la finestra. Lunghezze viste: {sorted(visti)}")
    assert giudice.scritture_di_max_length == [], (
        f"scritture sullo stato condiviso: {giudice.scritture_di_max_length}")
