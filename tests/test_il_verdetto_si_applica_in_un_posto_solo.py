"""Il verdetto di supersessione si applica in UN posto solo.

Il 12 settembre 2026 il campo `supersede_fact_ids` — i fatti che una scrittura
ritira — era letto e applicato in DUE punti, con guardie gia' divergenti, e in
un terzo (la riga di comando) **non era letto affatto**: misurato, zero
occorrenze in `cli.py`. Il gate stampava «the older value is superseded» e nel
database `superseded_by` restava nullo, quindi la stessa coppia di scritture
lasciava un fatto vivo dall'SDK e due dal terminale.

La cura non e' stata una terza copia: l'applicazione sta in
`supersession_policy.applica_verdetto` e le tre porte la chiamano. Questo file
impedisce alla quarta di nascere per conto suo — ed e' un difetto che il tempo
produce da solo: una porta nuova si scrive guardandone una vecchia, e se la
vecchia porta il ciclo dentro di se', la nuova lo ricopia.

🔴 E QUESTO PRESIDIO HA CAUSATO UN ROSSO, il 13 settembre, e sta scritto qui
perche' chi lo legge domani lo sappia. Per soddisfarlo ho tolto dal server di
strumenti il termine `and getattr(_gate, "supersede_fact_ids", None)` di una
condizione — sembrava ridondante, la funzione unica fa lo stesso controllo. Non
era ridondante: faceva da INTERRUTTORE al termine successivo, `semantic.get(...)`,
che senza niente da ritirare non veniva mai chiamato. Tolto quello, `get`
partiva a ogni scrittura ammessa e quattro test sono diventati rossi sulla
gamba macos, perche' il loro doppio del semantic ha `store` e `count` e non
`get`.
⇒ La lezione non e' «il presidio e' sbagliato»: e' che un presidio che vieta di
NOMINARE qualcosa spinge a cancellare la riga invece di spostarla, e in una
condizione l'ordine dei termini E' logica. La prova di raggiungibilita' ora sta
dentro la funzione unica, dopo il controllo degli id: stesso ordine, un posto
solo.

⚠️ E' un presidio TESTUALE, e il suo limite va detto: legge il sorgente, non il
comportamento. Non si accorgerebbe di una porta che applica il verdetto in modo
sbagliato — quella la prende `test_una_versione_non_e_un_ritiro.py`, che misura
l'effetto alla porta. Qui si sorveglia una sola cosa: che la decisione di
COME si applica resti in un posto solo.
"""

from __future__ import annotations

import pathlib

import pytest

RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"

#: Chi puo' nominare il campo, e perche'.
AMMESSI = {
    "anti_confab_gate.py": "lo PRODUCE: e' il gate che decide chi va ritirato",
    "supersession_policy.py": "lo APPLICA: la superficie unica",
}

#: Le tre porte di scrittura. Possono CHIAMARE la funzione unica; non devono
#: leggere il campo per conto loro, che e' il modo in cui nasce una copia.
PORTE = ("cli.py", "client.py", "mcp_server.py")


def _occorrenze(nome: str) -> int:
    """Quante volte il file NOMINA il campo, fuori dai commenti.

    I commenti si contano a parte di proposito: un presidio che vietasse di
    PARLARE del campo impedirebbe di spiegare perche' questa cura esiste, e il
    commento che racconta un difetto vale piu' del difetto evitato. Qui si
    sorveglia il CODICE che lo legge.
    """
    testo = (RADICE / nome).read_text(encoding="utf-8", errors="replace")
    codice = chr(10).join(r.split("#", 1)[0] for r in testo.splitlines())
    return codice.count("supersede_fact_ids")


@pytest.mark.parametrize("porta", PORTE)
def test_nessuna_porta_legge_il_campo_per_conto_suo(porta):
    n = _occorrenze(porta)
    assert n == 0, (
        f"{porta} nomina `supersede_fact_ids` {n} volte: sta applicando il "
        "verdetto per conto suo invece di chiamare "
        "`supersession_policy.applica_verdetto`. E' la classe «una copia "
        "invece della superficie unica»: le due copie che c'erano prima di "
        "questa cura erano gia' divergenti su una guardia, e la terza porta "
        "non applicava il verdetto affatto.")


@pytest.mark.parametrize("porta", PORTE)
def test_CONTROLLO_ogni_porta_chiama_davvero_la_superficie_unica(porta):
    """⚠️ SENZA QUESTO il file sopra e' soddisfatto da una porta che il
    verdetto non lo applica PER NIENTE — che e' esattamente lo stato da cui
    veniamo. Zero occorrenze del campo e zero chiamate alla funzione danno lo
    stesso verde, e sono la cosa buona e la cosa cattiva."""
    testo = (RADICE / porta).read_text(encoding="utf-8", errors="replace")
    assert "applica_verdetto" in testo, (
        f"{porta} non chiama `applica_verdetto`: il verdetto del gate non "
        "viene applicato da questa porta, e chi scrive da qui perde la "
        "versione vecchia senza saperlo.")


def test_CONTROLLO_la_superficie_unica_esiste_e_nomina_il_campo():
    """Se la funzione sparisse o cambiasse nome, i due test sopra
    resterebbero verdi sorvegliando il nulla."""
    testo = (RADICE / "supersession_policy.py").read_text(
        encoding="utf-8", errors="replace")
    assert "def applica_verdetto(" in testo, (
        "la superficie unica non c'e' piu': questo file sta sorvegliando il "
        "nulla")
    assert "supersede_fact_ids" in testo, (
        "la superficie unica non legge piu' il campo del gate")
    assert 'reason="same-source evolution"' in testo, (
        "il motivo del ritiro non e' piu' scritto nella superficie unica: un "
        "ritiro senza motivo non e' leggibile nel registro dei ritiri")
