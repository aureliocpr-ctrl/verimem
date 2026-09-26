"""Chi dichiara di ridurre lo span deve guardare la condizione che lo riduce.

IL DIFETTO, misurato il 2026-09-19. Il daemon scrive nel file di scoperta
``"applies_window": self._gate_fn is not None`` (encode_service.py), ma quando
deve ridurre davvero rinuncia se il TOKENIZZATORE non c'e':

    if getattr(_giudice, "_tok", None) is None:
        raise RuntimeError("tokenizzatore non ancora caricato ...")

Due condizioni diverse: si promette guardando la funzione di gate, si lavora
guardando il tokenizzatore. Il client legge la promessa
(``local_grounding.py``: ``il_daemon_riduce = bool(info.get("applies_window"))``)
e si fa da parte ⇒ NESSUNO dei due riduce, e la coda dello span la taglia il
modello.

Sul daemon vivo, letto in sola lettura senza riavviarlo: pid 2952,
``applies_window: True``, e il ``RuntimeWarning`` compare a ogni scrittura
giudicata, ``verimem save`` compreso.

⚠️ PERCHE' NON BASTA ``judge_state() == "ready"``, che sarebbe stata la cura
ovvia: quello guarda ``_scorer`` (assegnato alle righe 229/278/333) mentre la
riduzione guarda ``_tok`` (riga 505). Sono due caricamenti distinti: usare
``judge_state`` qui rifarebbe lo stesso errore con un nome piu' bello. La cura
e' UNA SUPERFICIE SOLA che dichiarante e lavoratore leggono entrambi.

⚠️ E non si costruisce il giudice per rispondere: si legge il singleton se
c'e' gia'. Se non c'e', la risposta e' «non riduco» — il verso sicuro, perche'
si paga la riduzione dal lato del client invece di perdere qualita' in
silenzio.

Il file di scoperta qui e' FISSATO nel banco: nessuna cella guarda la macchina.
"""
from __future__ import annotations

import json

from verimem import encode_service as svc
from verimem import local_grounding as lg


class _GiudiceFinto:
    def __init__(self, con_tokenizzatore: bool) -> None:
        if con_tokenizzatore:
            self._tok = object()


def _scoperta(tmp_path, monkeypatch, *, gate_fn, tok: bool | None):
    """Scrive il file di scoperta come lo scrive il daemon, e lo rilegge."""
    if tok is None:
        monkeypatch.setattr(lg, "_judge", None, raising=False)
    else:
        monkeypatch.setattr(lg, "_judge", _GiudiceFinto(tok), raising=False)
    s = object.__new__(svc.EncodeServer)
    s._discovery_path = tmp_path / "scoperta.json"
    s._port = 59999
    s._sock = None  # `port` e' una property e legge il socket
    s._host = "127.0.0.1"
    s._model_name = "intfloat/multilingual-e5-base"
    s._model_dim = 768
    s._token = "t"
    s._gate_fn = gate_fn
    s._write_discovery()
    return json.loads((tmp_path / "scoperta.json").read_text(encoding="utf-8"))


def test_senza_tokenizzatore_il_daemon_non_promette_la_finestra(
        tmp_path, monkeypatch):
    """RED: oggi promette True con la sola funzione di gate."""
    info = _scoperta(tmp_path, monkeypatch, gate_fn=lambda p: [1.0], tok=False)
    assert info["applies_window"] is False, info


def test_col_tokenizzatore_la_promessa_resta(tmp_path, monkeypatch):
    """NON-REGRESSIONE: dove il daemon riduce davvero, niente cambia."""
    info = _scoperta(tmp_path, monkeypatch, gate_fn=lambda p: [1.0], tok=True)
    assert info["applies_window"] is True, info


def test_senza_giudice_costruito_non_si_promette_e_non_si_costruisce(
        tmp_path, monkeypatch):
    """Il verso sicuro, e nessun caricamento causato dalla domanda."""
    costruzioni = []
    monkeypatch.setattr(lg, "get_local_judge",
                        lambda: costruzioni.append(1), raising=False)
    info = _scoperta(tmp_path, monkeypatch, gate_fn=lambda p: [1.0], tok=None)
    assert info["applies_window"] is False, info
    assert not costruzioni, "la domanda ha COSTRUITO il giudice"


def test_senza_funzione_di_gate_resta_come_prima(tmp_path, monkeypatch):
    """L'altra meta' della condizione non si perde per strada."""
    info = _scoperta(tmp_path, monkeypatch, gate_fn=None, tok=True)
    assert info["applies_window"] is False, info


def test_quando_il_tokenizzatore_arriva_la_scoperta_si_riscrive(
        tmp_path, monkeypatch):
    """La meta' non riduttiva: senza di questa la delega non si sveglia MAI.

    Il file di scoperta si scrive all'avvio, e il tokenizzatore lo carica solo
    chi riduce uno span — cosa che un client chiede solo a un daemon che gli
    ha promesso la finestra. Con la sola promessa onesta il giro si chiude su
    se' stesso: `False` all'avvio, `False` per sempre, e la riduzione resta
    sempre a carico del client.

    Qui si esercita `_handle_request`, non si ricopia la sua riga.
    """
    giudice = _GiudiceFinto(con_tokenizzatore=False)
    monkeypatch.setattr(lg, "_judge", giudice, raising=False)
    info = _scoperta(tmp_path, monkeypatch, gate_fn=lambda p: [1.0], tok=False)
    assert info["applies_window"] is False, info

    s = object.__new__(svc.EncodeServer)
    s._discovery_path = tmp_path / "scoperta.json"
    s._port, s._sock = 59999, None
    s._host, s._model_name, s._model_dim = "127.0.0.1", "m", 768
    s._token = "t"
    s._finestra_dichiarata = False
    # il gate finto fa cio' che fa quello vero: porta il tokenizzatore
    def _gate(coppie):
        giudice._tok = object()
        return [1.0 for _ in coppie]
    s._gate_fn = _gate
    monkeypatch.setattr(lg, "_judge", giudice, raising=False)

    # ⚠️ il token serve: senza, `_handle_request` risponde «unauthorized»
    # e non arriva mai al gate — il banco lo ha detto subito.
    s._handle_request({"token": "t", "gate_pairs": [("a", "b")]})

    riletta = json.loads((tmp_path / "scoperta.json").read_text(encoding="utf-8"))
    assert riletta["applies_window"] is True, riletta


def test_un_server_senza_file_di_scoperta_non_esplode_nel_giudicare(monkeypatch):
    """IL PERCORSO SU CUI LA MIA FALSIFICAZIONE ERA CIECA.

    La riscrittura della scoperta vive dentro `_handle_request`. Un server
    costruito senza `_discovery_path` — cosa che fa il banco di T73 con
    `object.__new__` — non ha nulla da riscrivere, e la prima stesura lo
    faceva esplodere:

        AttributeError: 'EncodeServer' object has no attribute
        '_discovery_path'   (encode_service.py:450, in `_write_discovery`)

    Undici volte, su ubuntu, macos e windows. In locale il ramo non si
    attivava — il giudice iniettato dal banco non soddisfa la condizione — e
    il mio «tolgo e rimetto» ha misurato un percorso che sulla mia macchina
    non viene mai preso. La cella sta qui per farlo vivere dove non vivevo.
    """
    class _GiudicePronto:
        _tok = object()

    monkeypatch.setattr(lg, "_judge", _GiudicePronto(), raising=False)

    s = object.__new__(svc.EncodeServer)
    s._token = "t"
    s._gate_fn = lambda coppie: [1.0 for _ in coppie]
    s._rerank_fn = None
    s._encode_fn = None
    # ⚠️ NIENTE `_discovery_path`: e' esattamente il caso che cadeva.

    risposta = s._handle_request({"token": "t", "gate_pairs": [("a", "b")]})

    assert risposta.get("ok") is True, risposta
    assert risposta.get("scores") == [1.0], risposta
