r"""T166 — «400 m3» è un volume, e il prodotto non lo leggeva.

IL BUCO, trovato mentre si misurava altro e finito nella pagina pubblica come
limite dichiarato: la cura di T105 legge l'unità composta in tutte le grafie
tranne quella con la CIFRA ASCII.

    «400 metri cubi»  -> ('m3', 400.0)     letta
    «400 m³»          -> ('m3', 400.0)     letta
    «400 mc»          -> ('mc', 400.0)     letta
    «400 m3»          -> ('',   400.0)     NON LETTA   <- il buco
    alla porta: «400 m3» contro una fonte che dice «400 mq» -> AMMESSO 91,95

Il gruppo dell'unità è `[^\W\d_]+`, che esclude le cifre: «m3» non è mai
un'unità, e volume-contro-area in quella grafia passa.

## ⛔ LA CURA OVVIA È FALSIFICATA, E IL NUMERO STA QUI PERCHÉ NON TORNI

«Lasciamo che l'unità finisca con una cifra» (`[^\W\d_]+\d?`), misurato su
tutte le 18 310 proposizioni dello store:

    proposizioni che cambiano lettura : 1311   (7,2%)
    unita' NUOVE piu' frequenti       : e2 103 · bdb6 82 · a7 63 · ad7 61 ·
                                        aefa1 61 · eec3 57 · ef9 54 ...

Sono **spezzoni di SHA** e sigle (`P0`, `v4`, `a2`): quella cura leggerebbe
peggio 1311 proposizioni per coprirne una classe che nel nostro corpus non
compare. ⇒ **Lista CHIUSA**, otto forme e basta. L'ultima cella di questo banco
conta che le forme degli SHA **non cambiano lettura**: è il presidio contro la
generalizzazione.

RAGGIO della lista chiusa: **zero** proposizioni dello store cambiano lettura —
e come per T105 il beneficio non è qui, è nelle perizie e nei capitolati, dove
quella grafia vive. Il limite si dichiara: zero per noi non è zero per l'utente.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict


def _unita(testo: str) -> set[str]:
    return {u for u, _ in extract_quantities(testo)}


@pytest.mark.parametrize("testo,attesa", [
    ("Il capannone misura 400 m3", "m3"),
    ("La superficie e' 400 m2", "m2"),
    ("Il locale misura 30 mm2", "mm2"),
    ("Il terreno e' di 2 km2", "km2"),
    ("The unit holds 400 ft3", "ft3"),
    ("The plate is 12 in2", "in2"),
])
def test_l_unita_con_la_cifra_viene_letta(testo: str, attesa: str):
    assert attesa in _unita(testo), (
        f"«{attesa}» non e' letta come unita': {sorted(_unita(testo))}")


def test_CONTROLLO_POSITIVO_le_grafie_che_gia_funzionavano_non_cambiano():
    """Se questa cella cade, la cura ha spostato il problema invece di
    chiuderlo: le tre grafie che T105 aveva coperto devono restare identiche."""
    assert _unita("Il capannone misura 400 metri cubi") == {"m3"}
    assert "m3" in _unita("Il capannone misura 400 m³")
    assert "mc" in _unita("Il capannone misura 400 mc")


def test_ALLA_PORTA_il_volume_scritto_con_la_cifra_non_passa_piu(tmp_path):
    """IL LIVELLO CHE CONTA. Prima: ammesso a 91,95 con nessun layer."""
    from verimem.client import Memory

    r = Memory(tmp_path / "m.db").add(
        "Il capannone 12 misura 400 m3.", topic="prova/t166",
        source="Perizia del 2026-09-01: il capannone 12 misura 400 mq.")
    strati = [w.get("layer") for w in (r.get("warnings") or [])]
    assert r.get("status") == "quarantined", (
        "volume contro area nella grafia con la cifra: alla porta passa "
        f"ancora.\n  status={r.get('status')} g={r.get('grounding_score')} "
        f"strati={strati}")
    assert "L4.2-grandezza" in strati, (
        f"trattenuto, ma non da chi doveva: {strati}")


def test_ALLA_PORTA_CONTROLLO_la_stessa_grandezza_resta_ammessa(tmp_path):
    """L'altra metà: «400 m2» contro «400 mq» è la STESSA grandezza scritta in
    due modi, e una cura che ferma anche quello è peggio del buco."""
    from verimem.client import Memory

    r = Memory(tmp_path / "m.db").add(
        "Il capannone 12 misura 400 m2.", topic="prova/t166",
        source="Perizia del 2026-09-01: il capannone 12 misura 400 mq.")
    assert r.get("status") != "quarantined", (
        f"la stessa grandezza in due grafie viene fermata: {r.get('status')} "
        f"{[w.get('layer') for w in (r.get('warnings') or [])]}")


def test_IL_CONFLITTO_VERO_in_questa_grafia_OGGI_NON_SCATTA():
    """⚠️ SECONDO EFFETTO DELLA CURA, scoperto scrivendo il banco e dichiarato
    invece di nascosto: l'avevo messo come «negativo che passa già», e cadeva.

        numeric_conflict(«400 m3», «500 m3»)  ->  None      PRIMA
                                              ->  conflitto DOPO

    Senza unità letta i due numeri restano **nudi**, e due numeri nudi non
    fanno conflitto — giustamente, sono ambigui. Quindi la cura non apre solo
    la strada a `L4.2-grandezza`: fa vedere allo scanner del corpus anche i
    conflitti «stessa unità, valore diverso» in questa grafia, che oggi non
    vede. Il raggio misurato resta zero (nessuna proposizione dello store
    cambia lettura), ma l'effetto è più largo di `L4.2` e va scritto.
    """
    assert numeric_conflict("Il capannone misura 400 m3",
                            "Il capannone misura 500 m3") is not None


#: Otto forme prese DALLO STORE (le proposizioni che la cura «una cifra
#: qualunque» avrebbe letto peggio), non inventate: sono SHA abbreviati e sigle
#: di progetto. Il banco non legge lo store — sarebbe irriproducibile — ma il
#: campione viene da lì, e le righe intere stanno nella nota di T166.
FORME_DEGLI_SHA = [
    "P0 #1.C FATTO 2026-05-11 commit 2df0211b: hook piu' store",
    "Progetto AiTraderCawBot e2 stato dopo Block 208",
    "omnex-mcp-suite round v4 hardening commits: dbbcbdb",
    "Roadmap Engram cycle #70 status a2 del 2026-05-15",
    "Critic-orchestrator round 1 P2.a job 918925b6fb81255f",
    "il commit bdb6 e il tag h6 non sono grandezze",
    "build ad7 e artefatto aefa1 nella stessa riga",
    "release ef9 con 3 moduli e 12 prove",
]


@pytest.mark.parametrize("testo", FORME_DEGLI_SHA)
def test_PRESIDIO_gli_spezzoni_di_SHA_non_diventano_unita(testo: str):
    """⛔ LA CELLA CHE TIENE CHIUSA LA GENERALIZZAZIONE.

    Ammettere «una cifra qualunque» in coda all'unità cambierebbe la lettura di
    **1311 proposizioni su 18 310**, leggendo `e2`, `bdb6`, `a7`, `ad7`,
    `aefa1` — spezzoni di commit — come grandezze. Con la lista chiusa nessuna
    di queste forme porta un'unità: se un giorno questa cella cade, qualcuno ha
    allargato la lista a una regola generale, e il prezzo è quel numero.
    """
    lette = _unita(testo)
    proibite = {u for u in lette if u and any(c.isdigit() for c in u)}
    ammesse = {"m2", "m3", "mm2", "mm3", "cm2", "cm3", "km2", "km3",
               "ft2", "ft3", "in2", "in3"}
    assert not (proibite - ammesse), (
        f"uno spezzone di SHA e' diventato un'unita': {sorted(proibite)} "
        f"in «{testo}»")
