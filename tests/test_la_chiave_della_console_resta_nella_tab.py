"""README:592-594 — «your API key stays in the tab and travels only as an
Authorization header».

IL CLAIM, testuale dal README pubblicato:

    Open `/ui` in a browser for the trust console (or `/dashboard` for the
    legacy minimal odometer) — static, dependency-free pages; your API key
    stays in the tab and travels only as an Authorization header.

Sono DUE promesse, e vanno tenute ferme tutte e due:
  ① **stays in the tab** — la chiave sta in `sessionStorage`, che muore con la
    scheda. Non in `localStorage` (sopravvive e viaggia fra le schede), non in
    un cookie (parte da solo a ogni richiesta, anche a quelle che non lo
    chiedono, e finisce nei log di chi sta in mezzo).
  ② **travels only as an Authorization header** — mai in una query string. Una
    chiave in una URL finisce nei log del reverse proxy che il README stesso
    consiglia due righe sotto («put it behind a TLS reverse proxy»), nella
    cronologia del browser e nel Referer.

E' VERO, verificato il 10/09: `gateway.py:212` manda
`fetch('/v1/stats', { headers: { 'Authorization': 'Bearer ' + tok } })`, e la
pagina lo dichiara da se' all'utente alla riga 159 — «(sessionStorage) and is
sent only as an Authorization header».

⚠️ NON confondere questa chiave con quella di `static/settings.js:128`
(`api_key: $('api_key').value`): quella e' la chiave del PROVIDER LLM, spedita
insieme a `provider`/`base_url`/`model` perche' il server deve usarla per
chiamare il modello. Il README parla della chiave del GATEWAY. Sono due cose
diverse e la prima non e' coperta da questa riga: cercare «api_key» e gridare
avrebbe prodotto un'accusa falsa.

PERCHE' UN TEST, SE E' VERO. Perche' e' una promessa di SICUREZZA e SILENZIOSA:
se domani la chiave passasse in una query string, nessuno se ne accorgerebbe —
la console continuerebbe a funzionare identica. Un difetto che non si vede non
ha nessuno che lo segnali.

⚠️ E SI GUARDA CIO' CHE IL SERVER SERVE, NON IL SORGENTE. Un presidio che
leggesse `verimem/static/*.js` proverebbe una cosa piu' debole: che quei file
sono puliti. La pagina che arriva al browser e' composta dalla porta, e questo
test la chiede alla porta — inclusi gli script che la pagina si tira dietro,
che sono anche loro serviti via HTTP e possono divergere dai file su disco.

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_la_chiave_della_console_resta_nella_tab.py -q -p no:randomly`
"""
from __future__ import annotations

import re

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.client import Memory  # noqa: E402
from verimem.gateway import GatewayKeys, create_app  # noqa: E402

PAGINE = ("/ui", "/dashboard")

# Una chiave dentro una URL: `?key=`, `&token=`, `?api_key=` … Cerca la forma,
# non il nome: un parametro nuovo che si chiamasse `k=` sfuggirebbe a un
# elenco di nomi, e per questo il riconoscitore ha sotto il suo controllo.
_IN_URL = re.compile(
    r"[?&](?:api[_-]?key|key|token|auth|access[_-]?token|bearer)=",
    re.I,
)
_SRC = re.compile(r"""(?:src|href)\s*=\s*["'](/[^"']+\.js)["']""", re.I)


@pytest.fixture()
def console(tmp_path):
    """Il gateway in modalita' personale, come `verimem console` lo apre."""
    mem = Memory(tmp_path / "store.db")
    mem.add("the office is in Milan", topic="hq", verified_by=["hr-doc"])
    app = create_app(data_dir=tmp_path / "gw",
                     keys=GatewayKeys(tmp_path / "gw" / "keys.db"),
                     local_tenant="local", local_memory=mem)
    return TestClient(app, base_url="http://127.0.0.1")


def _tutto_cio_che_arriva_al_browser(client) -> dict[str, str]:
    """Le pagine E gli script che si tirano dietro, presi DALLA PORTA."""
    pezzi: dict[str, str] = {}
    for via in PAGINE:
        r = client.get(via, headers={"Host": "localhost"})
        if r.status_code != 200:
            continue
        pezzi[via] = r.text
        for script in set(_SRC.findall(r.text)):
            s = client.get(script, headers={"Host": "localhost"})
            if s.status_code == 200:
                pezzi[script] = s.text
    return pezzi


# ── IL CONTROLLO POSITIVO PER PRIMO: la porta ha risposto DAVVERO ───────────


def test_CONTROLLO_le_pagine_della_console_arrivano_dalla_porta(console):
    """Senza questo, «non contiene la chiave» sarebbe verde su una pagina vuota.

    Un 404, un redirect o una pagina di errore soddisfano alla perfezione ogni
    asserzione della forma «non c'e' X»: e' il sensore scollegato.
    """
    pezzi = _tutto_cio_che_arriva_al_browser(console)
    assert pezzi, "nessuna delle pagine della console ha risposto 200"
    corpo = "\n".join(pezzi.values())
    assert len(corpo) > 400, f"la console ha servito solo {len(corpo)} caratteri"
    assert "Authorization" in corpo, (
        "in tutto cio' che la console serve non compare la parola "
        "`Authorization`: o la pagina e' cambiata, o questo test sta guardando "
        f"la cosa sbagliata. Vie lette: {sorted(pezzi)}"
    )


# ── ① STAYS IN THE TAB ──────────────────────────────────────────────────────


def test_la_chiave_sta_in_sessionStorage_e_non_esce_dalla_scheda(console):
    """README:592-594 — «stays in the tab»: sessionStorage, non localStorage."""
    for via, corpo in _tutto_cio_che_arriva_al_browser(console).items():
        assert "localStorage" not in corpo, (
            f"{via} usa `localStorage`: sopravvive alla chiusura della scheda e "
            "vale per tutte le schede della stessa origine. Il README promette "
            "«your API key stays in the tab»."
        )
        assert "document.cookie" not in corpo, (
            f"{via} scrive un cookie: un cookie parte da solo a ogni richiesta "
            "verso l'origine, anche a quelle che non lo chiedono. Il README "
            "promette che la chiave viaggia SOLO come Authorization header."
        )


# ── ② TRAVELS ONLY AS AN AUTHORIZATION HEADER ───────────────────────────────


def test_la_chiave_non_viaggia_mai_in_una_query_string(console):
    """README:592-594 — «travels only as an Authorization header»."""
    for via, corpo in _tutto_cio_che_arriva_al_browser(console).items():
        colpi = _IN_URL.findall(corpo)
        assert not colpi, (
            f"{via} mette una credenziale in una URL ({colpi}). Finisce nei log "
            "del reverse proxy che il README consiglia due righe sotto, nella "
            "cronologia del browser e nel Referer — e nessuno se ne accorge, "
            "perche' la console continua a funzionare identica."
        )


# ── E IL CONTROLLO CHE PUO' SMENTIRMI ───────────────────────────────────────


@pytest.mark.parametrize(
    "frammento, deve_accendersi",
    [
        ("fetch('/v1/stats', {headers: {'Authorization': 'Bearer ' + tok}})", False),
        ("fetch('/v1/stats?limit=10')", False),
        ("fetch('/v1/stats?api_key=' + tok)", True),
        ("fetch('/v1/stats?limit=10&token=' + tok)", True),
        ("fetch('/v1/events?access_token=' + tok)", True),
    ],
)
def test_CONTROLLO_il_riconoscitore_PRENDE_la_chiave_in_una_url(frammento, deve_accendersi):
    """Saprebbe accorgersene, se ci fosse?

    Senza questa faccia, «nessuna credenziale in URL» potrebbe voler dire
    soltanto che la regex non combacia con niente. Qui le si mettono davanti
    tre URL che perdono la chiave e due che non la perdono — fra cui una con
    un parametro innocuo, perche' un riconoscitore che si accende su ogni `?`
    e' rumore, non un presidio.
    """
    assert bool(_IN_URL.search(frammento)) is deve_accendersi, (
        f"su «{frammento}» il riconoscitore "
        f"{'doveva' if deve_accendersi else 'non doveva'} accendersi"
    )

# FALSIFICATO, non solo scritto. Difetto simulato per un minuto a
# `gateway.py:212` — l'`Authorization` header sostituito con
# `fetch('/v1/stats?api_key=' + tok)` — e il file eseguito sullo stesso difetto:
#
#     EXIT=1   1 failed, 7 passed
#     AssertionError: /dashboard mette una credenziale in una URL (['?api_key='])
#
# Senza il difetto: EXIT=0, 8 passed. `gateway.py` ripristinato con
# `git checkout --` e verificato identico al backup.
