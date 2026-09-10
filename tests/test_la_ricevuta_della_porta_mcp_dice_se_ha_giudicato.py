"""README:352 — la riga della tabella «it depends on the port» che ho scritto IO.

IL CLAIM, testuale dal README pubblicato (riga 352, tabella «What gets your
first write judged: it depends on the port»):

    | **MCP server** - `hippo_remember` | the server **delegates to a shared
    encode daemon by construction** and never loads the judge in its own process
    … It starts the daemon itself - but **if the daemon is missing or does not
    come up, the write is stored UNJUDGED**: `stored: true`, and the receipt
    carries `layers: ['L4-skipped']`. **Read that field.** `admitted` on its own
    does not mean judged. |

⚠️ QUESTA RIGA L'HO SCRITTA IO l'08/09 ed è entrata su main con `5ac8d9f1`
**senza nessun presidio**. È la forma che ho denunciato tutto il giorno — una
promessa che nessun test tiene ferma — applicata alla riga che ho aggiunto io.
La prendo prima delle altre per questo: chi mappa i debiti degli altri comincia
dal proprio.

E non è una riga qualsiasi: **dice all'utente quale campo leggere** per sapere
se ciò che ha appena scritto è stato giudicato o no. Se quel campo non arriva a
quella porta, l'utente legge `stored: true` e crede di avere un fatto
verificato mentre ha un `model_claim`.

COME SI PROVA. Non contando le occorrenze del nome: `grep '"layers"'
verimem/mcp_server.py` è **vuoto**, e non vuol dire niente — il payload del tool
è costruito con `_ok({**res, …})` e propaga ciò che gli passa il livello sotto.
Un'assenza si prova ESEGUENDO, e questo file invoca la porta e guarda la
ricevuta che ne esce.

⚠️ ZERO COPIE: `_invoke_tool` è importato da `tests.test_mcp_thin`.

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_la_ricevuta_della_porta_mcp_dice_se_ha_giudicato.py -q -p no:randomly`
"""
from __future__ import annotations

import json

import pytest

from tests.test_mcp_thin import _invoke_tool

#: Il nome del campo, come il README lo insegna all'utente.
CAMPO = "layers"
#: Il valore che quel campo deve portare quando il giudizio non è girato.
SALTATO = "L4-skipped"  # citato nel docstring, non piu asserito: vedi il test in fondo


async def _ricevuta_di_una_scrittura_con_fonte() -> dict:
    """Scrive dalla porta MCP con una `source` e rende la ricevuta.

    ⚠️ CREDEVO che in un test il giudice non girasse (nessun daemon, embedder
    stub) e che questa fosse la condizione «daemon assente» del README. **La
    misura mi ha smentita**: la ricevuta porta
    `adjudication.judge.model = local_gate_ce_v2` e `evidence_class =
    cross_encoder`, cioè **il giudizio gira davvero**. Lo scrivo qui perché era
    un'assunzione mia, comoda, e non l'avevo verificata: quello che questo file
    prova è l'ASSENZA DEL CAMPO, non il comportamento a daemon spento.
    """
    blocchi = await _invoke_tool(
        "hippo_remember",
        {"proposition": "il capannone 12 misura 400 metri quadri.",
         "topic": "note",
         "source": "Perizia del 2026-03-04: il capannone 12 misura 400 mq."},
    )
    return json.loads(blocchi[0])


# ── IL CONTROLLO POSITIVO PER PRIMO ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_CONTROLLO_la_porta_risponde_e_la_ricevuta_ha_un_corpo(tmp_data_dir):
    """Una ricevuta vuota o un errore soddisfano ogni asserzione «non c'è X»."""
    ricevuta = await _ricevuta_di_una_scrittura_con_fonte()
    assert isinstance(ricevuta, dict), f"la porta non ha reso un oggetto: {ricevuta!r}"
    assert ricevuta, "la porta ha reso una ricevuta VUOTA"
    assert not ricevuta.get("error"), (
        f"la scrittura dalla porta MCP è fallita: {ricevuta.get('error')!r}. "
        "Questo test non può dire niente sul campo della ricevuta se la "
        "scrittura non è avvenuta."
    )


# ── LA PROMESSA: «Read that field» ──────────────────────────────────────────


@pytest.mark.xfail(
    strict=True,
    reason=(
        "APERTO — ws7, 10/09, E LA RIGA È MIA. README:352 insegna all'utente a "
        "leggere `layers` nella ricevuta di `hippo_remember`, e quella porta NON "
        "rende quel campo. Misurato invocando il tool: le chiavi sono "
        "['adjudication', 'anti_confab_warnings', 'confidence', 'deferred', "
        "'gate_knobs_denied', 'grounding_score', 'id', 'judged', 'moat', 'ok', "
        "'proposition', 'replaced', 'source_signature', 'status', 'topic', "
        "'verified_by'] — c'è `judged`, c'è `adjudication`, `layers` no.\n"
        "PER L'UTENTE: chi segue il README cerca un campo che non arriva, e "
        "resta con `stored: true` senza sapere se il fatto è stato giudicato — "
        "che è esattamente ciò che quella riga dice di NON fare.\n"
        "LA CURA È MIA e va sul README, non sul prodotto: `judged` è il campo "
        "giusto e c'è già. Ma prima serve la misura nella condizione che la riga "
        "descrive — daemon assente — che qui NON ho riprodotto: in questo test "
        "il giudice gira (adjudication.judge.model = local_gate_ce_v2). Si lega "
        "a T26a/a di ws5. Riscrivo la riga quando ho quel dato, non prima: una "
        "riga di documentazione corretta a occhio è come è nato questo difetto.\n"
        "`strict=True`: il giorno che `layers` torna alla porta, questo passa e "
        "obbliga a togliere l'xfail."
    ),
)
@pytest.mark.asyncio
async def test_la_ricevuta_porta_il_campo_che_il_readme_insegna_a_leggere(tmp_data_dir):
    """README:352 — «the receipt carries `layers: [...]`. **Read that field.**»

    Un utente che segue il README cerca `layers` nella ricevuta di
    `hippo_remember`. Se non c'è, non ha modo di sapere se la sua scrittura è
    stata giudicata: `stored: true` da solo non lo dice, e il README stesso
    avverte che «`admitted` on its own does not mean judged».
    """
    ricevuta = await _ricevuta_di_una_scrittura_con_fonte()
    assert CAMPO in ricevuta, (
        f"README:352 insegna a LEGGERE il campo `{CAMPO}` nella ricevuta di "
        f"`hippo_remember`, e la ricevuta non ce l'ha. Chiavi presenti: "
        f"{sorted(ricevuta)}.\n"
        "Per l'utente: non ha modo di sapere se la scrittura è stata giudicata. "
        "O il campo torna alla porta, o quella riga del README va riscritta con "
        "il nome del campo che c'è davvero."
    )


# ── E IL CAMPO CHE C'È DAVVERO, perché il README possa essere riscritto ─────


@pytest.mark.asyncio
async def test_la_ricevuta_dice_SE_HA_GIUDICATO_con_il_campo_judged(tmp_data_dir):
    """La porta MCP la risposta ce l'ha: si chiama `judged`, non `layers`.

    Questo test non presidia una riga del README — presidia il campo su cui
    quella riga andrà RISCRITTA. Serve a due cose: che `judged` non sparisca
    mentre aspetto la misura per correggere il testo, e che chi riscrive la riga
    abbia il nome giusto misurato invece che scelto a occhio.

    ⚠️ Qui NON asserisco il valore. In questo test il giudice gira davvero
    (`adjudication.judge.model` = `local_gate_ce_v2`), quindi `judged` è vero e
    non dice niente sul caso «daemon assente» che il README descrive. Quel caso
    e' di ws5 (T26a/a) e la misura è sua: un'asserzione sul valore, qui,
    proverebbe una condizione che non ho riprodotto.
    """
    ricevuta = await _ricevuta_di_una_scrittura_con_fonte()
    assert "judged" in ricevuta, (
        "la porta MCP non rende nemmeno `judged`: allora l'utente non ha NESSUN "
        f"campo per sapere se la scrittura è stata giudicata. Chiavi: {sorted(ricevuta)}"
    )
    assert isinstance(ricevuta["judged"], bool), (
        f"`judged` non è un booleano ma {type(ricevuta['judged']).__name__}: "
        "un campo che si legge come sì/no deve essere sì/no."
    )
