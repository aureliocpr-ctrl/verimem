"""Il giudice del moat deve vivere nel daemon, come gia' ci vivono gli altri due.

Il `doctor` di questo store lo dice in faccia::

    ! moat-judge  local CE gate model installed (state here: ready), but only
    107 of 4827 stored facts entailment-judged (2.2%) — the moat runs only on
    writes that carry a source, AND on the MCP channel the judge loads in the
    background: writes that arrive while it is warming are admitted unjudged

La seconda meta' di quella frase e' un buco nella tesi centrale del prodotto:
una scrittura che arriva mentre il giudice si scalda viene **ammessa senza
essere giudicata**. Non e' un caso di bordo — e' il caso NORMALE, perche' sul
canale MCP i processi sono effimeri: sull'audit log, 256 processi su 293 fanno
una sola chiamata e muoiono. Ogni respawn ricomincia il warm da zero, quindi
c'e' sempre una finestra iniziale in cui il moat non gira, e i processi che
vivono solo dentro quella finestra non lo eseguono mai.

E' la TERZA volta che lo stesso modello-nel-processo-effimero morde, e le prime
due sono gia' curate allo stesso modo:

  * l'embedder -> `encode_service` (da mesi);
  * il reranker della recall -> `rerank_pairs` nello stesso daemon (93cfdf28,
    ieri: da «applied alla settima chiamata, cioe' mai nel regime reale» a
    «applied dalla prima», 12 su 12);
  * il giudice del moat -> QUI. E' un CE diverso (il gate model
    `local_gate_ce_v2`, testa binaria) e per questo era rimasto fuori, ma il
    mestiere e' identico.

Lo stesso cambiamento chiude tre cose che sembravano separate:

1. le scritture ammesse non giudicate (sopra);
2. i worker `xdist` crashati in `make_finetuned_scorer` — N processi che
   caricano lo stesso modello insieme;
3. la fetta di suite che stasera si e' appesa 13 minuti dentro
   `transformers/core_model_loading.py:946 _materialize_copy`, mentre altre tre
   fette facevano lo stesso. Rilanciata DA SOLA, stessi 287 file: 2093 passed
   in 825 secondi, nessun intoppo. La causa e' la contesa, non il file.

CIO' CHE NON DEVE CAMBIARE, ed e' meta' del lavoro: il daemon resta
un'OTTIMIZZAZIONE, mai una dipendenza. Qualunque intoppo — daemon spento, daemon
vecchio che non conosce l'operazione, socket che cade — deve riportare al
comportamento di prima (carica in-process, oppure degrada onestamente), non a un
errore. E' la stessa regola gia' scritta per `_rerank_via_daemon`, e i test qui
sotto la inchiodano per il giudice.
"""
from __future__ import annotations

import threading

import pytest

from verimem import encode_service as svc


def _avvia(s):
    """`start()` apre il socket e annuncia la discovery; il LOOP che risponde e'
    `serve_forever`, e va messo in un thread. Senza, la connessione riesce e
    poi il client scade in attesa — un daemon che accetta e non parla."""
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    return t


@pytest.fixture()
def daemon_finto(monkeypatch, tmp_path):
    """Un daemon vero (socket, protocollo, token) con una `gate_fn` INIETTATA:
    verifica il protocollo senza caricare mezzo giga di modello. Stesso schema
    gia' usato per `encode_fn` e `rerank_fn`."""
    # Il conftest spegne il daemon per tutti («tests must use the stub, never a
    # live shared encode daemon»), e dice che chi ESERCITA quel path lo
    # riaccende: e' questo il caso.
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    chiamate: list = []

    def _gate(pairs):
        chiamate.append(list(pairs))
        return [42.0 for _ in pairs]

    s = svc.EncodeServer(encode_fn=lambda t: [0.0, 1.0],
                         gate_fn=_gate,
                         discovery_path=tmp_path / "discovery.json",
                         model_name="finto", model_dim=2)
    s.start()
    t = _avvia(s)
    # `read_discovery()` non si limita a leggere il file: scarta un daemon che
    # annuncia un modello diverso da quello di CONFIG (anti corpus-poisoning,
    # scan68b). Un daemon finto lo e' per definizione, quindi il test legge il
    # file annunciato e lo inietta — come fanno gia' i test del daemon.
    import json
    info = json.loads((tmp_path / "discovery.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(svc, "read_discovery", lambda *_a, **_k: info)
    try:
        yield s, chiamate, info
    finally:
        s.stop()
        t.join(timeout=2)


def test_il_daemon_sa_giudicare_le_coppie(daemon_finto):
    """Il protocollo, speculare a `rerank_pairs`."""
    _s, chiamate, info = daemon_finto
    assert info and info.get("port"), "il daemon non si e' annunciato"

    from verimem.local_grounding import _gate_via_daemon
    punteggi = _gate_via_daemon([("la fonte dice X", "X")], info=info)
    assert punteggi == [42.0], punteggi
    assert chiamate == [[("la fonte dice X", "X")]], chiamate


def test_un_daemon_che_non_sa_giudicare_fa_degradare_non_rompere(monkeypatch,
                                                                 tmp_path):
    """Il caso dell'aggiornamento non atomico: client nuovo, daemon vecchio.

    `gate_fn=None` e' il daemon che NON sa giudicare — distinto da «non
    passato», che userebbe il default. Senza questa distinzione il caso non si
    puo' nemmeno costruire in un test."""
    s = svc.EncodeServer(encode_fn=lambda t: [0.0, 1.0], gate_fn=None,
                         discovery_path=tmp_path / "d.json", model_name="vecchio")
    s.start()
    t = _avvia(s)
    monkeypatch.setattr(svc, "DISCOVERY_PATH", tmp_path / "d.json")
    try:
        from verimem.local_grounding import _gate_via_daemon
        assert _gate_via_daemon([("a", "b")]) is None, (
            "contro un daemon che non sa giudicare il client deve tornare None "
            "e far caricare in-process, non sollevare")
    finally:
        s.stop()
        t.join(timeout=2)


def test_senza_daemon_il_client_torna_None_invece_di_sollevare(monkeypatch,
                                                              tmp_path):
    """Nessun daemon annunciato: il chiamante deve poter proseguire com'era."""
    monkeypatch.setattr(svc, "DISCOVERY_PATH", tmp_path / "non-esiste.json")
    from verimem.local_grounding import _gate_via_daemon
    assert _gate_via_daemon([("a", "b")]) is None


def test_il_moat_GIUDICA_alla_prima_scrittura_invece_di_ammettere_al_buio(
        daemon_finto, monkeypatch):
    """Il punto di tutto il file.

    In delegate-only (il regime del server MCP) `try_local_score` tornava None
    finche' il warm in background non atterrava, e il chiamante ammetteva senza
    giudizio. Col daemon il punteggio c'e' dalla PRIMA chiamata, nello stesso
    processo effimero che prima non faceva in tempo."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    from verimem import local_grounding as lg
    lg.reset_local_judge()

    esito = lg.try_local_score("la fonte dice X", "X")
    assert esito is not None, (
        "in delegate-only la prima scrittura non e' stata giudicata: e' "
        "esattamente il caso che il doctor segnala come «admitted unjudged»")
    punteggio, _soglia = esito
    assert punteggio == 42.0, punteggio


def test_il_daemon_non_e_client_di_se_stesso():
    """Anti-ricorsione, la stessa guardia di `_default_rerank_fn`: la funzione
    che il daemon esegue non deve richiedere il punteggio al daemon."""
    import inspect
    src = inspect.getsource(svc._default_gate_fn)
    assert "consenti_daemon=False" in src or "_gate_via_daemon" not in src, (
        "la gate_fn del daemon puo' ricadere sul daemon: e' una ricorsione "
        f"in attesa di accadere\n{src}")
