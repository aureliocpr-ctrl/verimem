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
        # il daemon riduce SOLO se il tokenizzatore c'e' gia' (non lo carica
        # sul percorso della richiesta): un doppio che vuole essere ridotto
        # deve averlo, come il giudice vero dentro il daemon.
        _tok = object()

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


def test_il_daemon_dichiara_se_sa_ridurre(tmp_path, monkeypatch) -> None:
    """La chiave che il client legge per decidere: dichiarata, non indovinata.

    Senza, il client dovrebbe SUPPORRE che il daemon sappia ridurre — e con un
    daemon vecchio lo span arriverebbe intero, cioe' una perdita di qualita'
    silenziosa. Il valore segue la capacita' VERA, non una costante.

    ⚠️ QUESTA CELLA GUARDAVA IL SORGENTE, e la forma non e' la proprieta'.
    Asseriva che `_write_discovery` contenesse la stringa
    `"applies_window": self._gate_fn is not None`, e il 2026-09-20 una cura
    legittima (T157: si dichiara la finestra solo se c'e' anche il
    tokenizzatore, perche' la promessa guardava `_gate_fn` e il lavoro
    guardava `_tok`) l'ha fatta cadere pur RAFFORZANDO cio' che difendeva.
    Ora si misura la proprieta': il valore CAMBIA col variare della capacita'.
    Una costante — qualunque costante — fallisce, che e' esattamente cio' che
    questa cella e' nata per impedire.
    """
    class _Giudice:
        def __init__(self, con_tok: bool) -> None:
            if con_tok:
                self._tok = object()

    def _dichiarato(tmp, *, gate_fn, con_tok: bool) -> bool:
        monkeypatch.setattr(local_grounding, "_judge", _Giudice(con_tok),
                            raising=False)
        s = object.__new__(encode_service.EncodeServer)
        s._discovery_path = tmp / "scoperta.json"
        s._port, s._sock = 59999, None
        s._host, s._model_name, s._model_dim, s._token = "h", "m", 768, "t"
        s._gate_fn = gate_fn
        s._write_discovery()
        import json
        return json.loads((tmp / "scoperta.json").read_text(encoding="utf-8"))[
            "applies_window"]

    def gate(coppie):
        return [1.0] * len(coppie)

    capace = _dichiarato(tmp_path, gate_fn=gate, con_tok=True)
    incapace = _dichiarato(tmp_path, gate_fn=gate, con_tok=False)
    senza_gate = _dichiarato(tmp_path, gate_fn=None, con_tok=True)

    assert capace is True, "un daemon che sa ridurre non lo dichiara"
    assert incapace is False, (
        "il daemon promette la finestra senza il tokenizzatore: il client si "
        "farebbe da parte e nessuno dei due ridurrebbe")
    assert senza_gate is False, "senza funzione di gate non si promette nulla"
    assert len({capace, incapace, senza_gate}) > 1, (
        "il valore non cambia MAI: e' una costante, e il client tornerebbe a "
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

    _tok = object()          # il tokenizzatore c'e': il daemon puo' ridurre

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


# ─────────────────────────────────────────────────────────────────────────────
# IL RIPIEGO RESTA, IL SILENZIO NO
#
# Rilievo in revisione, 2026-09-12: il `except ... : pass` che copre la
# riduzione prometteva, nel commento sopra, «il comportamento di prima». Non lo
# e': PRIMA la riduzione la faceva il client prima di mandare, e il modello non
# troncava mai. Se il ripiego scatta si torna al troncamento DALLA CODA — il
# 42% dello span buttato dopo che il selettore l'aveva scelto — e nessuno lo sa.
# Il fail-open si tiene: un giudizio che cade sarebbe peggio. Il silenzio no.
# ─────────────────────────────────────────────────────────────────────────────


def test_se_la_riduzione_fallisce_il_daemon_lo_DICE_e_giudica_lo_stesso() -> None:
    """Due cose insieme, e servono entrambe: il verdetto esce (fail-open) e la
    risposta dichiara che lo span non e' stato ridotto (non muto)."""

    class _GiudiceRotto:
        max_length = 8

        def _entro_la_finestra(self, span, max_length=None):
            raise RuntimeError("tokenizzatore assente")

    import verimem.local_grounding as lg
    originale = lg.get_local_judge
    lg.get_local_judge = _GiudiceRotto
    try:
        server = object.__new__(encode_service.EncodeServer)
        server._token = "t"
        server._gate_fn = lambda coppie: [77.0] * len(coppie)

        resp = server._handle_request({
            "token": "t",
            "gate_pairs": [["uno span lungo\ne un altro pezzo", "un fatto"]],
            "max_length": 8,
        })
    finally:
        lg.get_local_judge = originale

    assert resp["ok"] and resp["scores"] == [77.0], (
        "il giudizio e' caduto: il ripiego deve restare aperto, un verdetto "
        "mancante e' peggio di uno span non ridotto")
    assert resp.get("window_applied") is False, (
        "la risposta NON dice che la riduzione non e' avvenuta: il punteggio "
        "arriva da uno span troncato dalla coda e chi lo riceve non lo sa")
    assert "RuntimeError" in str(resp.get("window_error", "")), (
        f"il motivo non e' arrivato: {resp.get('window_error')!r}. Senza, chi "
        "legge sa che qualcosa non ha funzionato ma non che cosa")


def test_quando_la_riduzione_riesce_la_risposta_non_si_sporca() -> None:
    """L'altra gamba: il campo compare SOLO quando serve.

    Un campo sempre presente diventa rumore e smette di essere letto — e un
    criterio che non distingue i due casi non e' un criterio.
    """
    class _GiudiceOk:
        max_length = 8
        _tok = object()

        def _entro_la_finestra(self, span, max_length=None):
            return span.splitlines()[0]

    import verimem.local_grounding as lg
    originale = lg.get_local_judge
    lg.get_local_judge = _GiudiceOk
    try:
        server = object.__new__(encode_service.EncodeServer)
        server._token = "t"
        server._gate_fn = lambda coppie: [1.0] * len(coppie)
        resp = server._handle_request({
            "token": "t",
            "gate_pairs": [["riga uno\nriga due", "un fatto"]],
            "max_length": 8,
        })
    finally:
        lg.get_local_judge = originale

    assert resp["ok"]
    assert "window_applied" not in resp, (
        "la risposta dichiara un problema che non c'e' stato: il campo deve "
        "comparire solo quando la riduzione e' saltata")


# ─────────────────────────────────────────────────────────────────────────────
# LA RICEVUTA DICE CHI HA GIUDICATO
#
# Dal 2026-09-12 il punteggio del moat puo' arrivare da due posti — il daemon
# condiviso o il modello caricato nel processo — con costi, latenze e modalita'
# di guasto diverse. La ricevuta li mostrava identici: un 99,6 dal daemon e un
# 99,6 in casa si leggevano uguali, e non lo sono.
# ─────────────────────────────────────────────────────────────────────────────


def test_chi_ha_giudicato_si_registra_per_THREAD_non_per_processo() -> None:
    """⚠️ LA GAMBA CHE CONTA, ed e' la lezione che questa PR ha gia' pagato una
    volta: il server serve una connessione per thread. Se l'esecutore stesse in
    una variabile di modulo, una scrittura leggerebbe l'esecutore di un'altra —
    e la ricevuta direbbe una cosa falsa su una cosa verificabile.

    Qui due thread registrano esecutori diversi e ciascuno rilegge il PROPRIO.
    Senza il thread-local il secondo troverebbe il valore del primo.
    """
    import threading

    from verimem import local_grounding as lg

    letti: dict[str, str | None] = {}
    pronti = threading.Barrier(2, timeout=10)

    def _uno(nome: str) -> None:
        lg._registra_esecutore(nome)
        pronti.wait()                     # tutti e due hanno scritto: ora si legge
        letti[nome] = lg.esecutore_dell_ultimo_giudizio()

    t = [threading.Thread(target=_uno, args=(n,)) for n in ("daemon", "in-process")]
    for x in t:
        x.start()
    for x in t:
        x.join(timeout=15)

    assert letti == {"daemon": "daemon", "in-process": "in-process"}, (
        f"un thread ha letto l'esecutore di un altro: {letti}. La ricevuta "
        "direbbe che ha giudicato il daemon quando ha giudicato il processo, "
        "o viceversa")


def test_quando_nessuno_giudica_il_campo_non_c_e(monkeypatch) -> None:
    """L'altra gamba: assente e' diverso da «giudicato», e la ricevuta non deve
    inventare un esecutore per un giudizio che non c'e' stato."""
    from verimem import local_grounding as lg

    monkeypatch.setattr(lg, "_delegate_only", lambda: True)
    monkeypatch.setattr(
        lg, "_gate_via_daemon", lambda pairs, *, info=None, max_length=None: None)
    monkeypatch.setattr(lg, "warm_local_judge_async", lambda: None)
    monkeypatch.setattr(
        encode_service, "read_discovery", lambda *a, **k: {"port": 1})

    giudice = _GiudiceFinto()
    monkeypatch.setattr(lg, "get_local_judge", lambda: giudice)
    lg._registra_esecutore("in-process")          # sporco apposta lo stato

    assert lg.try_local_score("una fonte", "un fatto") is None
    assert lg.esecutore_dell_ultimo_giudizio() is None, (
        "dopo un giudizio NON avvenuto il registro tiene ancora l'esecutore "
        "precedente: la ricevuta attribuirebbe a qualcuno un verdetto che non "
        "e' stato dato")


def test_il_daemon_che_risponde_si_registra_come_daemon(monkeypatch) -> None:
    """Il caso normale del server: giudica il daemon e la ricevuta lo dira'."""
    from verimem import local_grounding as lg

    monkeypatch.setattr(lg, "_delegate_only", lambda: True)
    monkeypatch.setattr(
        lg, "_gate_via_daemon", lambda pairs, *, info=None, max_length=None: [7.0])
    monkeypatch.setattr(
        encode_service, "read_discovery", lambda *a, **k: {"port": 1})

    giudice = _GiudiceFinto()
    monkeypatch.setattr(lg, "get_local_judge", lambda: giudice)
    lg._registra_esecutore(None)

    r = lg.try_local_score("una fonte", "un fatto")
    assert r is not None and r[0] == 7.0
    assert lg.esecutore_dell_ultimo_giudizio() == "daemon"
