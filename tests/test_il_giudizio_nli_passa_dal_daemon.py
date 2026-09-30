"""Il giudizio NLI di L3 passa dal daemon condiviso: il server MCP non carica il
modello.

MISURATO il 2026-09-26 in sola lettura (moduli caricati e nvidia-smi): il daemon
verimem, il daemon dei hook e un server MCP col giudice in casa tengono ciascuno
lo stack CUDA intero. Torch importato costa circa 1071 MB a processo, e un
giudice lo porta a 2126 MB sul processore e a 2412 sulla scheda (A/B del
12/09). Letto nel codice: `LocalRelationJudge` costruisce il classificatore NLI
nel processo che scrive (`make_nli_classifier`, `.to(device)`), e il daemon non
serve il giudizio NLI. Il giudice del moat (`gate_pairs`) e il reranker
(`rerank_pairs`) passano gia' dal daemon; il giudizio NLI no. Quindi ogni
sessione che scrive un fatto con un fratello simile si prende torch e il modello.

NESSUN MODELLO: il classificatore in casa e' finto e conta i caricamenti; il
daemon si simula sostituendo la domanda che la cura gli fa.
"""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
import threading

import pytest

from verimem import encode_service, local_relation
from verimem.semantic_conflict import Relation

_CONTRADDIZIONE = {"contradiction": 0.95, "entailment": 0.0, "neutral": 0.05}
_NEUTRO = {"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0}


@pytest.fixture
def caricamenti(monkeypatch):
    """Conta quante volte il modello NLI si costruisce IN QUESTO processo."""
    conta = {"n": 0}

    def _classificatore_finto(model_name, **k):
        conta["n"] += 1
        return lambda coppie: [dict(_NEUTRO) for _ in coppie]

    monkeypatch.setattr(local_relation, "make_nli_classifier", _classificatore_finto)
    # Il conftest spegne il servizio per ogni test: qui serve acceso.
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    return conta


def test_nel_server_mcp_il_giudizio_nli_va_al_daemon(caricamenti, monkeypatch):
    """LA CURA. RED sul tronco: il server costruisce il modello in casa."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(local_relation, "_nli_via_daemon",
                        lambda coppie, **k: [dict(_CONTRADDIZIONE) for _ in coppie],
                        raising=False)

    esito = local_relation.LocalRelationJudge().classify(
        "Il capannone misura 400 mq.", "Il capannone misura 250 mq.")

    assert caricamenti["n"] == 0, (
        "il server MCP ha costruito il modello NLI in casa: torch e il modello "
        "in ogni sessione che scrive")
    assert esito is Relation.CONTRADICTION, "il giudizio del daemon non e' arrivato"


def test_nel_server_mcp_senza_daemon_il_modello_non_si_carica(caricamenti, monkeypatch):
    """Delegate-only vuol dire mai il modello nel server, come per l'embedder:
    senza daemon il giudizio NLI non c'e', non se lo carica il server."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(local_relation, "_nli_via_daemon",
                        lambda coppie, **k: None, raising=False)

    esito = local_relation.LocalRelationJudge().classify(
        "Il capannone misura 400 mq.", "Il capannone misura 250 mq.")

    assert caricamenti["n"] == 0
    assert esito is Relation.NEUTRAL


def test_fuori_dal_server_senza_daemon_il_modello_si_carica_come_oggi(
        caricamenti, monkeypatch):
    """CLI e SDK senza delegate-only: il comportamento di oggi resta."""
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setattr(local_relation, "_nli_via_daemon",
                        lambda coppie, **k: None, raising=False)

    local_relation.LocalRelationJudge().classify(
        "Il capannone misura 400 mq.", "Il capannone misura 250 mq.")

    assert caricamenti["n"] == 1


def test_il_daemon_risponde_a_nli_pairs():
    """Il daemon conosce la richiesta. RED sul tronco: «request must contain...»."""
    server = encode_service.EncodeServer(encode_fn=lambda t: [0.0])
    server._nli_fn = lambda coppie: [dict(_CONTRADDIZIONE) for _ in coppie]

    # Il token del daemon, come lo manda un client che ha letto la scoperta:
    # senza, la risposta e' «unauthorized» e la cella non misurerebbe niente.
    risposta = server._handle_request(
        {"nli_pairs": [["a", "b"], ["b", "a"]], "token": server._token})

    assert risposta.get("ok") is True, risposta
    assert risposta.get("probs") == [_CONTRADDIZIONE, _CONTRADDIZIONE], risposta


def test_il_lotto_passa_dal_daemon_in_una_richiesta(caricamenti, monkeypatch):
    """`classify_batch`, il percorso di `detect_semantic_conflicts` con piu'
    fratelli: una richiesta sola con le coppie nei due versi."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    richieste: list = []

    def _daemon(coppie, **k):
        richieste.append(list(coppie))
        return [dict(_CONTRADDIZIONE) for _ in coppie]

    monkeypatch.setattr(local_relation, "_nli_via_daemon", _daemon, raising=False)

    esiti = local_relation.LocalRelationJudge().classify_batch(
        [("A misura 4.", "A misura 2."), ("B vale 7.", "B vale 9.")])

    assert caricamenti["n"] == 0
    assert esiti == [Relation.CONTRADICTION, Relation.CONTRADICTION], esiti
    assert richieste == [[("A misura 4.", "A misura 2."), ("A misura 2.", "A misura 4."),
                          ("B vale 7.", "B vale 9."), ("B vale 9.", "B vale 7.")]], richieste


def test_un_classificatore_gia_in_casa_non_chiede_al_daemon(caricamenti, monkeypatch):
    """GUARDIA, verde anche sul tronco: chi inietta un classificatore (o l'ha
    gia' caricato) lo usa, il daemon non viene interrogato."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    domande = {"n": 0}

    def _daemon(coppie, **k):
        domande["n"] += 1
        return [dict(_CONTRADDIZIONE) for _ in coppie]

    monkeypatch.setattr(local_relation, "_nli_via_daemon", _daemon, raising=False)
    giudice = local_relation.LocalRelationJudge(
        classifier=lambda coppie: [dict(_NEUTRO) for _ in coppie])

    assert giudice.classify("x vale 1.", "x vale 2.") is Relation.NEUTRAL
    assert domande["n"] == 0
    assert caricamenti["n"] == 0


def _avvia(server):
    """`start()` apre il socket; il loop che risponde e' `serve_forever`."""
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t


def _daemon_vero(tmp_path, nli_fn):
    server = encode_service.EncodeServer(
        encode_fn=lambda t: [0.0, 1.0], nli_fn=nli_fn,
        discovery_path=tmp_path / "discovery.json", model_name="finto", model_dim=2)
    server.start()
    t = _avvia(server)
    # La scoperta si legge dal file di QUESTO daemon e si PASSA al client: senza
    # `info=` il client leggerebbe la scoperta vera della macchina e parlerebbe
    # col daemon vero.
    info = json.loads((tmp_path / "discovery.json").read_text(encoding="utf-8"))
    return server, t, info


def test_il_giudizio_fa_andata_e_ritorno_sul_socket(caricamenti, tmp_path):
    """Il protocollo intero, con un daemon vero: socket, token, JSON."""
    ricevute: list = []

    def _nli(coppie):
        ricevute.append(list(coppie))
        return [dict(_CONTRADDIZIONE) for _ in coppie]

    server, t, info = _daemon_vero(tmp_path, _nli)
    try:
        probs = local_relation._nli_via_daemon([("a", "b"), ("b", "a")], info=info)
    finally:
        server.stop()
        t.join(timeout=2)

    assert probs == [_CONTRADDIZIONE, _CONTRADDIZIONE], probs
    assert ricevute == [[("a", "b"), ("b", "a")]], ricevute


def test_un_daemon_che_non_sa_classificare_fa_degradare(caricamenti, tmp_path):
    """Client nuovo, daemon vecchio (`nli_fn=None`): None, non un'eccezione.

    None arriva anche da un client che non ha mai raggiunto il daemon: per questo
    si registra la risposta del daemon, e la cella chiede che ci sia stata.
    """
    server, t, info = _daemon_vero(tmp_path, None)
    risposte: list = []
    originale = server._handle_request
    server._handle_request = lambda req: risposte.append(originale(req)) or risposte[-1]
    try:
        probs = local_relation._nli_via_daemon([("a", "b")], info=info)
    finally:
        server.stop()
        t.join(timeout=2)

    assert risposte == [{"ok": False, "error": "this daemon cannot classify"}], risposte
    assert probs is None


def test_il_daemon_non_e_client_di_se_stesso_per_il_giudizio_nli():
    """Anti-ricorsione, come `_default_gate_fn`: la funzione che il daemon
    esegue non passa dal percorso che interroga il daemon.

    Con `ast` e non con le sottostringhe: la docstring della funzione NOMINA
    `_nli_via_daemon`, e una ricerca nel testo la leggerebbe come una chiamata.
    """
    albero = ast.parse(textwrap.dedent(inspect.getsource(encode_service._default_nli_fn)))
    chiamati = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                for n in ast.walk(albero) if isinstance(n, ast.Call)}
    # Controllo positivo: se il sensore non vede nemmeno questa, non vede niente.
    assert "_ensure_classifier" in chiamati, chiamati
    assert not chiamati & {"_nli_via_daemon", "_probabilita", "classify",
                           "classify_batch"}, chiamati
