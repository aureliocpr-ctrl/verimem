"""Il gateway legge `as_of` come l'SDK: «auto» e' il default, non un errore.

TROVATO DALLA RIGA 8 DEL TABELLONE (accettazione dal wheel di #182, 30/09, ubuntu e
windows): con `VERIMEM_SERVER_URL` impostato, come dice il README («the CLI (`verimem
remember` / `recall`) … route through the shared server»), `verimem recall` esce 1::

    RuntimeError: verimem server error 422
    {"type":"float_parsing","loc":["query","as_of"],"msg":"Input should be a valid number…"}

La CLI passa `as_of="auto"` APPOSTA (il commento in `recall_cmd`: «"auto" e non
None» — con None la data non si deduce piu' dalla domanda), il client remoto lo
inoltra, e il gateway dichiara `as_of: float | None`. Due difetti in uno:
  · un comando del README che si rompe appena lo si instrada;
  · e anche quando non si rompe, il gateway usa None come default, cioe' SPEGNE la
    deduzione della data: dal server condiviso una domanda sul passato riceve il
    presente, che e' la classe gia' curata sulla CLI.

IL CONTRATTO GIUSTO e' quello della firma pubblica, `Memory.search(as_of="auto")`: il
gateway accetta «auto» o un istante, e se `as_of` manca usa «auto». La cosa veloce —
far scartare «auto» al client remoto — riparava il 422 e lasciava la deduzione spenta.

IL BANCO: la modalita' personale del gateway (loopback, nessuna chiave) davanti a un
finto store che registra con quale `as_of` viene chiamato; niente modelli.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402


class _StoreCheRegistra:
    """Un Memory finto: risponde vuoto e ricorda gli argomenti di ogni lettura."""

    def __init__(self) -> None:
        self.chiamate: list[tuple[str, dict]] = []

    def search(self, q, **kw):
        self.chiamate.append(("search", kw))
        return []

    def explain(self, q, **kw):
        self.chiamate.append(("explain", kw))
        return {"facts": [], "abstained": True, "reason": "store finto"}


@pytest.fixture()
def gateway(tmp_path):
    store = _StoreCheRegistra()
    app = create_app(data_dir=tmp_path / "gw", keys=GatewayKeys(tmp_path / "keys.db"),
                     local_tenant="me", local_memory=store)
    cliente = TestClient(app, client=("127.0.0.1", 51000))
    return cliente, store


@pytest.mark.parametrize("percorso", ["/v1/search", "/v1/explain"])
def test_as_of_auto_non_e_un_errore(gateway, percorso):
    cliente, store = gateway
    r = cliente.get(percorso, params={"q": "what does analytics run on", "as_of": "auto"},
                    headers={"Host": "localhost"})
    assert r.status_code == 200, (
        f"{percorso}?as_of=auto -> {r.status_code}: {r.text[:300]} — «auto» e' il "
        f"default della firma dell'SDK, e `verimem recall` instradato lo manda")
    assert store.chiamate[-1][1].get("as_of") == "auto", store.chiamate


@pytest.mark.parametrize("percorso", ["/v1/search", "/v1/explain"])
def test_senza_as_of_il_gateway_usa_il_default_dell_sdk(gateway, percorso):
    cliente, store = gateway
    r = cliente.get(percorso, params={"q": "cosa risultava sul canone al 1 giugno 2024"},
                    headers={"Host": "localhost"})
    assert r.status_code == 200, r.text[:300]
    assert store.chiamate[-1][1].get("as_of") == "auto", (
        f"{percorso} senza as_of chiama lo store con {store.chiamate[-1][1].get('as_of')!r}: "
        f"None spegne la deduzione della data dalla domanda, che l'SDK ha accesa di default")


# ───────────────────────────  i CONTROLLI  ───────────────────────────

@pytest.mark.parametrize("percorso", ["/v1/search", "/v1/explain"])
def test_un_istante_passa_come_numero(gateway, percorso):
    cliente, store = gateway
    r = cliente.get(percorso, params={"q": "x", "as_of": "1717200000"},
                    headers={"Host": "localhost"})
    assert r.status_code == 200, r.text[:300]
    assert store.chiamate[-1][1].get("as_of") == 1717200000.0, store.chiamate


@pytest.mark.parametrize("percorso", ["/v1/search", "/v1/explain"])
def test_un_as_of_illeggibile_resta_un_errore(gateway, percorso):
    cliente, store = gateway
    r = cliente.get(percorso, params={"q": "x", "as_of": "ieri sera"},
                    headers={"Host": "localhost"})
    assert r.status_code == 422, (r.status_code, r.text[:300])
    assert not store.chiamate, "un as_of illeggibile non deve arrivare allo store"
