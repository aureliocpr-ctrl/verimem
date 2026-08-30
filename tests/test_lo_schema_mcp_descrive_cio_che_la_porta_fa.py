"""Lo schema che un agente legge PRIMA di scegliere deve descrivere la porta.

MISURATO ATTRAVERSO IL HANDLER `hippo_remember` il 2026-08-30, store
temporaneo, due popolazioni e i tre livelli::

    popolazione              validate  status        gs     strati
    SELF-CLAIM nudo          off       quarantined   None   L1.10,L1.15,L1.20
    SELF-CLAIM nudo          fast      quarantined   None   L1.10,L1.15,L1.20
    SELF-CLAIM nudo          full      quarantined   None   L1.10,L1.15,L1.20
    claim + FONTE che nega   off       quarantined   0.53   L4.1,L4-grounding
    claim + FONTE che nega   fast      quarantined   0.58   L4.1,L4-grounding
    claim + FONTE che nega   full      quarantined   0.58   L4.1,L4-grounding

    latenza, stesso handler:  primo write a freddo 32.724 ms · a caldo 187-340 ms

DUE COSE CHE LO SCHEMA DICEVA E LA PORTA NON FA:

① «'off' = **bypass**». Non bypassa: `off` e' **neutralizzato di proposito**
   (`mcp_server.py:12878`), perche' gli argomenti MCP sono untrusted e una
   manopola che INDEBOLISCE il gate richiede l'opt-in dell'operatore
   (`VERIMEM_MCP_TRUST_GATE_KNOBS`).
   🟢 **Il prodotto si comporta bene e lo dichiara**: la ricevuta porta
   `gate_knobs_denied: ['validate=off']`. ⚠️ **Ma lo dichiara DOPO.** L'agente
   sceglie leggendo lo schema, e li' c'era scritto il contrario.
   ⇒ Il difetto non e' il comportamento: e' che la verita' arriva a valle della
   decisione che doveva informare.

② «'fast' … **sub-ms**». Quel numero e' dei soli detector lessicali. Con una
   `source` il moat gira a OGNI livello, e il primo write di un processo freddo
   paga anche il caricamento del giudice: **32,7 secondi**, cioe' quattro ordini
   di grandezza sopra «sub-ms». Chi dimensiona un timeout su quella riga lo
   dimensiona sbagliato.

E UNA TERZA, sulla manopola accanto: `gate_mode='downgrade'` prometteva
`status='provisional'`. Misurato: **`quarantined`**, su entrambe le popolazioni.
E' la terza superficie del prodotto con quella stessa prosa vecchia — le altre
due (`anti_confab_gate:24` e `:296`) sono state curate stamattina; questa e'
quella che leggono **gli agenti**.

⚠️ QUESTO FILE NON MISURA CHE `fast` E `full` SIANO EQUIVALENTI. Le mie due
popolazioni non contengono il caso che li separa (una contraddizione `L3`), e
dedurre l'equivalenza da un pareggio su due casi sarebbe leggere un'assenza di
misura come un verdetto. Qui si presidia solo la PROSA.
"""

from __future__ import annotations

import pytest

from verimem import mcp_server


def _schema_di(nome_tool: str) -> dict:
    """Lo schema che il server ANNUNCIA, non una costante ricopiata qui.

    ⚠️ `list_tools` e non una costante del test: se un giorno la
    descrizione vive altrove, questo presidio segue la porta. (Alla prima
    stesura avevo chiamato `_list_tools_impl`, che non esiste:
    l'`AttributeError` diceva «non gliel'ho chiesto», non «il server non
    espone gli strumenti».)
    """
    import asyncio
    strumenti = asyncio.run(mcp_server.list_tools())
    for s in strumenti:
        if s.name in (nome_tool, "verimem_" + nome_tool[len("hippo_"):]):
            return dict(getattr(s, "inputSchema", {}) or {})
    raise AssertionError(f"{nome_tool} non e' fra gli strumenti annunciati")


@pytest.fixture(scope="module")
def proprieta() -> dict:
    return dict(_schema_di("hippo_remember").get("properties", {}) or {})


def test_validate_dice_che_off_e_neutralizzato_su_questa_porta(proprieta):
    """IL CUORE: l'agente sceglie leggendo QUESTA riga, non la risposta."""
    testo = str(proprieta["validate"]["description"])
    assert "NEUTRALIZED" in testo or "neutralized" in testo, testo
    assert "VERIMEM_MCP_TRUST_GATE_KNOBS" in testo, testo
    assert "gate_knobs_denied" in testo, (
        "lo schema non nomina il campo in cui la risposta dichiara il rifiuto: "
        f"{testo}")


def test_validate_non_promette_piu_sub_ms_a_chi_passa_una_fonte(proprieta):
    """«sub-ms» misurava i detector; con una source il primo write costa 32,7 s."""
    testo = str(proprieta["validate"]["description"])
    assert "source" in testo and "32.7" in testo, testo


def test_gate_mode_non_promette_piu_provisional(proprieta):
    """La terza superficie con la prosa vecchia, e la sola che legga un agente."""
    testo = str(proprieta["gate_mode"]["description"])
    assert "quarantined" in testo, testo
    assert "status='provisional'" not in testo, testo


def test_i_tre_livelli_restano_annunciati(proprieta):
    """⚠️ LA POPOLAZIONE OPPOSTA: una descrizione onesta non deve diventare una
    descrizione che TOGLIE un livello. `off` resta un valore legale — e' la
    POLITICA della porta a neutralizzarlo, non lo schema a vietarlo."""
    assert set(proprieta["validate"]["enum"]) == {"off", "fast", "full"}
    assert proprieta["validate"]["default"] == "fast"
