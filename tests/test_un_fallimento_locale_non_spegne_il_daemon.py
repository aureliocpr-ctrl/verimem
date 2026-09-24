"""Un caricamento fallito QUI non deve far smettere di chiedere a un ALTRO processo.

`try_local_score` chiedeva al daemon condiviso solo quando `judge._load_failed`
era falso. Ma quel campo dice che il caricamento e' fallito **in questo
processo** — RAM, file corrotto, torch assente, una macchina piccola — e il
daemon e' un processo separato col modello gia' in memoria: puo' stare
benissimo. Da quel momento il giudizio non veniva piu' chiesto a chi poteva
darlo.

E la riga sopra la condizione prometteva l'opposto: *«Se il daemon non c'e', non
sa giudicare o e' lento, si degrada ESATTAMENTE come prima»*. Li' non si
degradava: **si saltava il daemon a priori, senza avere alcuna informazione
sulla sua salute.**

MISURATO ALLA PORTA il 2026-08-30 alle 22:16 con il daemon VIVO (porta 61574),
A/B nella stessa esecuzione — banco
`docs/stato-reale/banchi/ws3-un-fallimento-locale-spegne-il-daemon-che-sta-bene.py`::

    _load_failed=False  ->  try_local_score  = (0.5561, 99.64)
    _load_failed=True   ->  try_local_score  = None          <- la clausola
    la STESSA strada a mano ->  _gate_via_daemon = [0.5561]   <- il daemon RISPONDE

⚠️ E IL BANCO SI ERA RIFIUTATO DI CONCLUDERE alle 20:43, quando il daemon era
giu': senza un daemon vivo non si distingue «la clausola spegne una strada» da
«non c'era una strada da spegnere». Il reperto e' rimasto una LETTURA del
sorgente per un'ora e mezza, e lo e' stato detto, finche' il daemon non e'
tornato.

PERCHE' IL COSTO NON E' SIMMETRICO, ed e' la ragione della cura: chiedere costa
una connessione locale con timeout; NON chiedere costa **una scrittura ammessa
senza giudizio** — che il docstring di `_gate_via_daemon` chiama *«precisamente
cio' che questo prodotto esiste per non fare»*.

⚠️ QUESTO FILE NON DIPENDE DAL DAEMON. Il daemon si simula sostituendo
`_gate_via_daemon`: il presidio verifica che la strada venga PERCORSA, non che
sul portatile di chi esegue ci sia un servizio acceso.
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest

from verimem import encode_service
from verimem import local_grounding as lg


@pytest.fixture
def giudice_freddo(monkeypatch):
    """Un giudice senza scorer, in delegate-only: il regime del server MCP."""
    j = lg.get_local_judge()
    monkeypatch.setattr(j, "_scorer", None, raising=False)
    monkeypatch.setattr(lg, "_delegate_only", lambda: True)
    return j


def _daemon_che_risponde(monkeypatch, punteggio: float = 0.42, *,
                         dichiara_finestra: bool = False) -> tuple[list, list]:
    """Sostituisce il daemon, registra se e' stato interrogato E CON CHE COSA.

    ⚠️ LA SCOPERTA SI FISSA QUI, e non e' un dettaglio: `read_discovery()` legge
    un file in `Path.home()`, cioe' STATO CONDIVISO DELLA MACCHINA. Senza
    fissarlo, queste celle chiedevano al portatile di chi esegue se per caso c'e'
    un daemon acceso, e rispondevano cose diverse a seconda della risposta.
    Misurato il 2026-09-13, stesso banco, stesso commit, A/B sulla sola `HOME`::

        nessun file di scoperta                -> 4 passed
        scoperta con applies_window: true      -> 2 failed   [512] != [None]

    In CI vinceva il secondo braccio — un altro test del giro avvia il servizio e
    lascia il file scritto — e il rosso sembrava della cura. Non lo era: era di
    QUESTO banco, che leggeva l'ambiente invece di dichiararlo.

    ⚠️ IL MANICHINO NOMINA CIO' CHE RICEVE, E LO DICHIARA. `max_length` e'
    esplicito perche' il client lo passa da quando la finestra la applica il
    daemon; e viene REGISTRATO, non buttato, perche' un manichino che riceve un
    argomento e lo ignora non verifica il cambio che quell'argomento E'.

    ⛔ E NON `**kwargs`: quello farebbe tornare verdi questi test in dieci
    secondi togliendo loro il contratto che verificano — la prossima firma che
    cambia non farebbe piu' rumore, e resterebbero verdi esercitando una
    chiamata che non esiste piu'. Il `TypeError` di prima era la prova che
    questo manichino e' fatto bene: severo per disegno, quindi ha protestato
    invece di ingoiare. (Rilievo in revisione, 2026-09-12.)
    """
    chiamate: list = []
    budget: list = []

    def _finto(pairs, *, info=None, max_length=None):
        chiamate.append(pairs)
        budget.append(max_length)
        return [punteggio]

    scoperta = {"pid": 1, "port": 1, "host": "127.0.0.1"}
    if dichiara_finestra:
        scoperta["applies_window"] = True
    monkeypatch.setattr(encode_service, "read_discovery",
                        lambda *a, **k: dict(scoperta))
    monkeypatch.setattr(lg, "_gate_via_daemon", _finto)
    return chiamate, budget


def test_con_il_caricamento_locale_fallito_si_chiede_lo_stesso_al_daemon(
        giudice_freddo, monkeypatch):
    """IL CUORE: e' la cella che dava None finche' la clausola c'era."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", True, raising=False)
    chiamate, budget = _daemon_che_risponde(monkeypatch)
    esito = lg.try_local_score("la fonte", "il claim")
    assert chiamate, (
        "il daemon NON e' stato interrogato con `_load_failed=True`: la "
        "clausola e' tornata, e un guasto locale spegne di nuovo una strada "
        "che funziona")
    assert esito is not None, esito
    # IL BUDGET E' ARRIVATO, e si dichiara: senza daemon che si annuncia capace
    # di ridurre e' `None`, ed e' il valore giusto — non l'assenza dell'argomento.
    assert budget == [None], (
        f"il client ha mandato una finestra a un daemon che non l'ha dichiarata: "
        f"{budget}")


def test_senza_fallimento_locale_il_daemon_si_chiede_come_prima(
        giudice_freddo, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA: la cura non deve cambiare il caso sano. Se
    passasse solo la prima, avrei «curato» spostando il problema."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", False, raising=False)
    chiamate, budget = _daemon_che_risponde(monkeypatch)
    assert lg.try_local_score("la fonte", "il claim") is not None
    assert chiamate
    assert budget == [None], budget


def test_al_daemon_che_DICHIARA_la_finestra_il_budget_arriva(
        giudice_freddo, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA DEL BUDGET, senza la quale le due celle sopra
    passerebbero anche se il client non mandasse MAI la finestra a nessuno.

    `None` e' il valore giusto solo finche' esiste un caso in cui il valore e'
    un altro: qui il daemon dichiara `applies_window`, e allora il budget deve
    ARRIVARE — altrimenti la riduzione non la fa nessuno e la coppia viene
    giudicata intera, che e' il difetto che questa PR cura.
    """
    monkeypatch.setattr(giudice_freddo, "_load_failed", False, raising=False)
    chiamate, budget = _daemon_che_risponde(monkeypatch, dichiara_finestra=True)

    assert lg.try_local_score("la fonte", "il claim") is not None
    assert chiamate
    assert budget == [giudice_freddo.max_length], (
        f"il daemon ha DICHIARATO di applicare la finestra e il client non gli "
        f"ha mandato il budget: {budget}. La coppia arriva intera e il "
        f"tokenizzatore lo paga di nuovo chi delega")


def test_se_il_daemon_non_risponde_si_degrada_come_sempre(
        giudice_freddo, monkeypatch):
    """⚠️ IL DEGRADO DICHIARATO, che la cura non deve toccare: daemon assente o
    muto -> None, e il chiamante fa esattamente cio' che faceva prima. Senza
    questa cella, «si chiede sempre al daemon» potrebbe voler dire «e si
    rimane appesi»."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", True, raising=False)
    monkeypatch.setattr(
        lg, "_gate_via_daemon", lambda pairs, *, info=None, max_length=None: None)
    monkeypatch.setattr(lg, "warm_local_judge_async", lambda: None)
    assert lg.try_local_score("la fonte", "il claim") is None


def _la_condizione_della_delega(funzione) -> str:
    """Il testo della condizione che decide l'ingresso nel ramo del daemon,
    RICOSTRUITO da dove vive: il test dell'`if` che consulta la delega, piu'
    OGNI assegnazione ai nomi che quel test usa.

    La prima stesura di questo presidio leggeva una riga di testo: quella che
    iniziava con `if` e conteneva `_delegate_only()`. Il 21/09 (T179) le due
    condizioni sono state lette UNA volta, nell'istante della decisione, in due
    assegnazioni prima dell'`if`: la proprieta' e' rimasta vera, la FORMA e'
    cambiata, e il presidio non trovava piu' niente. Qui si legge l'oggetto.

    ⚠️ Si confronta il TESTO ricostruito (`ast.unparse`), non i soli nomi:
    `_load_failed` nel prodotto compare come attributo (`judge._load_failed`)
    e come STRINGA (`getattr(j, "_load_failed", False)`). Raccogliere solo gli
    `ast.Name` le perderebbe entrambe, e il presidio nuovo sarebbe piu' debole
    del vecchio, che cercava la sottostringa.
    """
    albero = ast.parse(textwrap.dedent(inspect.getsource(funzione)))
    alimenta: dict[str, list[ast.expr]] = {}
    for nodo in ast.walk(albero):
        if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                and isinstance(nodo.targets[0], ast.Name)):
            # TUTTE le assegnazioni a quel nome, non l'ultima: una mutazione
            # non deve poter sfuggire perche' «sovrascritta» nel dizionario.
            alimenta.setdefault(nodo.targets[0].id, []).append(nodo.value)
    trovate = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.If):
            continue
        nomi = {n.id for n in ast.walk(nodo.test) if isinstance(n, ast.Name)}
        pezzi = [nodo.test] + [v for n in sorted(nomi) for v in alimenta.get(n, [])]
        testo = " ; ".join(ast.unparse(p) for p in pezzi)
        if "_delegate_only" in testo:
            trovate.append(testo)
    # PIU' FORTE, NON PIU' LARGO: il vecchio prendeva la PRIMA riga che
    # combaciava e ignorava le altre. Due condizioni di delega vogliono dire che
    # qualcuno ha aggiunto una strada che questo presidio non guarderebbe.
    assert len(trovate) == 1, (
        f"attesa UNA condizione che consulta la delega, trovate {len(trovate)}: "
        f"{trovate}")
    return trovate[0]


def test_la_condizione_non_nomina_piu_il_fallimento_locale():
    """Il presidio strutturale, che dice al prossimo PERCHE' la clausola non
    c'e': un campo che descrive QUESTO processo non decide di un ALTRO."""
    condizione = _la_condizione_della_delega(lg.try_local_score)
    assert "_load_failed" not in condizione, condizione
