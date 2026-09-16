"""T90 — una chiamata alla porta non puo' NON tornare.

⚠️ IL DIFETTO, misurato alla porta MCP il 15-16/09, quattro volte su quattro::

    initialize                             5.73 s
    tools/list                             0.01 s
    prima chiamata (hippo_remember)      424.06 s -> {"CHIUSO": "Connection closed"}
    EXIT=124

E non e' lentezza, e' un ARRESTO: campionando l'albero, 35 s di lavoro vero
(RSS fino a 737,9 MB) e poi **0,34 s di CPU in 236 s** (0,1%). La causa
dell'arresto sta sotto Python e resta IGNOTA — sei candidati esclusi eseguendo
(il lavoro: 14,6 s in-process; il precarico; la gara a pausa zero; lo
scaricamento; due import concorrenti; worker anyio + anello asincrono). Quella
e' T90b, con un debugger nativo.

🔑 QUI SI PRESIDIA IL CONTRATTO, non la causa (I5/I7): **o il fatto e'
giudicato, o entra DICHIARANDO che non lo e' stato**. Il terzo caso — la
chiamata che non torna mai — non deve esistere.

⚠️ PERCHE' IL CANCELLO E' SOSTITUITO DA UNO CHE SI PIANTA: riprodurre l'arresto
vero costa 150 s e non e' deterministico (dipende da quando il thread si ferma).
Qui si sostituisce la CAUSA con una che si pianta a comando, e si misura
l'unica cosa che il contratto promette: che la porta risponda lo stesso. Senza
la cura questa cella non fallisce: **resta appesa** — ed e' esattamente il
difetto (per questo il RED vero e' la misura manuale qui sopra, con EXIT=124).
"""
from __future__ import annotations

import asyncio
import json
import threading
import time

import pytest

from verimem import _tetto_del_giudizio as tg
from verimem import anti_confab_gate as gate
from verimem import mcp_server

#: Basso apposta: la cella deve durare secondi, non un minuto. Il valore vero
#: (60 s) non e' in prova qui — in prova c'e' che il tetto ESISTA e scatti.
TETTO_DI_PROVA = 2.0


def _chiama(nome: str, args: dict) -> dict:
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)


@pytest.fixture
def cancello_che_si_pianta(monkeypatch, tmp_path):
    """Il cancello non torna piu'. Il thread resta appeso: e' il caso vero."""
    partito = threading.Event()
    #: ⚠️ IL FINTO SI LIBERA ALLA FINE, e non e' cosmesi: con un `time.sleep(600)`
    #: i thread del pool restano vivi e **l'interprete non esce** — la cella
    #: passava (4 passed in 12,84 s) e il processo moriva per timeout (EXIT=124).
    #: In CI sarebbe un job appeso. Un banco che lascia in giro thread non e'
    #: un banco: e' un secondo difetto.
    finita = threading.Event()

    def _piantato(**_kwargs):
        partito.set()
        finita.wait(600)         # non torna finche' la cella non e' finita
        raise TimeoutError("il cancello finto non e' mai tornato (per disegno)")

    monkeypatch.setattr(gate, "run_validation_gate", _piantato)
    monkeypatch.setattr(tg, "TETTO_S", TETTO_DI_PROVA)
    #: il marcatore del degradato va nella cartella della prova, mai in casa
    monkeypatch.setattr(tg, "_cartella", lambda: tmp_path)
    yield partito
    finita.set()                 # libera i thread abbandonati dal tetto


def test_la_chiamata_torna_anche_se_il_giudizio_non_torna(
        cancello_che_si_pianta, tmp_path):
    """IL CUORE. Senza la cura questa cella non fallisce: resta appesa."""
    t = time.perf_counter()
    r = _chiama("hippo_remember", {
        "proposition": "La chiave del cancello nord sta nella bacheca",
        "source": "Verbale: chiave del cancello nord -> bacheca.",
        "topic": "prova/tetto",
    })
    durata = time.perf_counter() - t

    assert cancello_che_si_pianta.is_set(), (
        "il cancello non e' stato nemmeno chiamato: la cella non misura il tetto")
    assert durata < TETTO_DI_PROVA + 30, (
        f"la chiamata ha impiegato {durata:.1f} s con un tetto di "
        f"{TETTO_DI_PROVA:.0f} s: il tetto non ha scattato")
    assert r.get("ok") is not False or r.get("rejected"), r


def test_il_fatto_entra_QUARANTINATO_e_la_ricevuta_nomina_il_livello(
        cancello_che_si_pianta, tmp_path):
    """⚠️ NON basta che torni: deve DIRE che non ha giudicato, e con QUALE
    livello. «judged=false» generico non basta — la ricevuta deve nominare L4 e
    la ragione, o chi legge non sa che cosa e' saltato."""
    r = _chiama("hippo_remember", {
        "proposition": "La chiave del cancello sud sta nella bacheca",
        "source": "Verbale: chiave del cancello sud -> bacheca.",
        "topic": "prova/tetto",
    })

    testo = json.dumps(r, ensure_ascii=False)
    assert "quarantined" in testo or r.get("status") == "quarantined", (
        f"il fatto non e' entrato quarantinato: ammetterlo come pulito senza "
        f"averlo giudicato sarebbe peggio dell'attesa infinita. Ricevuta: {testo[:400]}")
    assert tg.LIVELLO in testo, (
        f"la ricevuta non nomina il livello saltato ({tg.LIVELLO}): {testo[:400]}")
    assert "tetto" in testo, f"la ricevuta non dice PERCHE': {testo[:400]}"


def test_la_seconda_scrittura_non_ripaga_il_tetto(
        cancello_che_si_pianta, tmp_path):
    """⚠️ LA CELLA CHE MISURA IL RISPARMIO, e senza la quale «si segna
    degradato» sarebbe una parola: la seconda chiamata deve dichiarare SUBITO.

    Misurato alla porta: 150,15 s la prima, 0,87 s la seconda."""
    _chiama("hippo_remember", {
        "proposition": "La chiave del cancello est sta nella bacheca",
        "source": "Verbale: chiave del cancello est -> bacheca.",
        "topic": "prova/tetto"})
    assert tg.questo_processo_e_degradato(), (
        "dopo il tetto il processo non si e' segnato degradato: la seconda "
        "scrittura ripagherebbe l'attesa per riscoprire la stessa cosa")

    t = time.perf_counter()
    _chiama("hippo_remember", {
        "proposition": "La chiave del cancello ovest sta nella bacheca",
        "source": "Verbale: chiave del cancello ovest -> bacheca.",
        "topic": "prova/tetto"})
    seconda = time.perf_counter() - t

    assert seconda < TETTO_DI_PROVA, (
        f"la seconda scrittura ha ripagato il tetto ({seconda:.1f} s): il "
        f"processo degradato deve dichiarare subito")


def test_il_marcatore_non_sopravvive_al_processo_che_lo_ha_scritto(tmp_path,
                                                                   monkeypatch):
    """⚠️ IL CONTROLLO NEGATIVO del marcatore: un allarme che resta acceso dopo
    che il guasto e' finito si smette di leggerlo. Un marcatore di un processo
    MORTO non deve contare."""
    monkeypatch.setattr(tg, "_cartella", lambda: tmp_path)
    tg.segna_degradato("prova")
    assert tg.stato_degradato() is not None
    assert tg.questo_processo_e_degradato()

    import json as _json
    p = tg.percorso_del_marcatore()
    dati = _json.loads(p.read_text(encoding="utf-8"))
    dati["pid"] = 999999          # un pid che non esiste
    p.write_text(_json.dumps(dati), encoding="utf-8")

    assert tg.stato_degradato() is None, (
        "un marcatore di un processo morto viene ancora contato: doctor "
        "segnalerebbe un degrado che non c'e' piu'")
