"""T115 — due frasi opposte sullo stesso numero, e una delle due promette troppo.

Sullo STESSO fatto ammesso, la porta MCP dice due cose incompatibili:

    scrittura   «… the source SCORES as supporting this fact: that is the
                 judge's score, NOT a check that the fact follows from it»
    storia      «[verificato: la fonte lo implica, 98.9]»

La prima è la verità misurata (il giudice dà un punteggio e non trova
contraddizioni); la seconda dichiara un'IMPLICAZIONE che nessuno ha verificato.
E non è una sfumatura: il commento in `cli.py:5526` misura il caso peggiore —
*«una fonte che NEGA il fatto prende 99.98 e si sente rispondere che la fonte lo
implica»*.

LA CONDIZIONE CHE L'ACCENDE, letta (`temporal_context.py:202`)::

    if isinstance(_gs, (int, float)) and not isinstance(_gs, bool):
        line += f" [verificato: la fonte lo implica, {float(_gs):.1f}]"

⇒ guarda che il punteggio sia **un numero**, non quale sia il **verdetto**. E
**il commento sopra quella riga dichiara l'intenzione opposta** — *«Si marca SOLO
quando il verdetto c'e'»* (`:194`): l'intenzione è scritta, l'implementazione no.

⚠️ PERCHÉ QUESTO BANCO NON PASSA DA `hippo_recall_history`, misurato e non
assunto. Su questo corpus le porte SEMANTICHE non restituiscono nulla, mentre
quelle lessicali trovano il fatto::

    hippo_remember        -> id c167ca72309b, disposition=admitted
    hippo_recall          -> []
    hippo_recall_history  -> {"context": [], "n": 0}
    hippo_facts_search    -> 1 item, grounding_score 98.86815643310547
    hippo_facts_recent    -> n_total 1

È l'embedder del banco, non il prodotto. Quindi la riga si ottiene chiamando
`history_line` sul fatto **che la porta ha davvero scritto** (`_ag().semantic`
è lo stesso store del tool MCP), non su un oggetto finto: il recupero non fa
parte di ciò che questo banco afferma.

Ticket T115. Registro: riga nuova, classe «copia invece di superficie unica» —
e qui la copia è DICHIARATA in un commento (`cli.py:5530`: «la formulazione è
allineata a quella di `mcp_server`»). Decisione: nessuna.
"""
from __future__ import annotations

import json

import pytest

TESTO = "Il capannone 12 misura 400 metri quadri."
FONTE = "Perizia del 2026-03-04: il capannone 12 misura 400 mq."
TOPIC = "note"

#: Le parole con cui un'uscita PROMETTE un'implicazione. Se compaiono, quella
#: uscita sta dicendo che la fonte implica il fatto — cosa che il giudice non
#: verifica.
PROMESSE = ("lo implica", "implies", "entails")


def _dice_implicazione(testo: str) -> bool:
    basso = (testo or "").lower()
    return any(p in basso for p in PROMESSE)


@pytest.mark.asyncio
async def test_la_scrittura_e_la_storia_non_si_contraddicono(isolated_corpus):
    """IL CUORE: stesso fatto, stesso punteggio, due frasi opposte."""
    from tests.test_mcp_thin import _invoke_tool
    from verimem.mcp_server import _ag
    from verimem.temporal_context import fact_history, history_line

    ricevuta = json.loads((await _invoke_tool(
        "hippo_remember",
        {"proposition": TESTO, "topic": TOPIC, "source": FONTE}))[0])
    #: ⚠️ NON `ricevuta["stored"]`: **la porta MCP quel campo non lo rende**, e
    #: l'avevo misurato io stessa scrivendo la proprietà delle tre ricevute
    #: («MCP non rende: layers, stored, warnings»). Qui si guarda il verdetto,
    #: che è il campo che esiste su questa porta.
    ammesso = (ricevuta.get("adjudication") or {}).get("disposition")
    assert ricevuta.get("ok") and ammesso == "admitted", (
        "il fatto non e' entrato: questo banco misura la contraddizione sugli "
        f"AMMESSI, e qui non c'e' niente da leggere. ok={ricevuta.get('ok')!r} "
        f"disposition={ammesso!r}")

    sm = _ag().semantic
    fatto = sm.get(ricevuta["id"])
    #: CONTROLLO POSITIVO: senza, un confronto fra due «nessuno promette» resta
    #: verde anche quando non c'è niente da leggere — sensore scollegato
    #: travestito da assenza di contraddizione. È già successo su questo banco
    #: con `recall_history` (n=0) e l'ha preso solo questa riga.
    assert fatto is not None, (
        f"lo store non rende il fatto {ricevuta['id']!r} che ha appena "
        "ammesso: non c'e' niente da confrontare.")

    riga = history_line(fatto, fact_history(sm, fatto.id))
    scrittura_promette = _dice_implicazione(json.dumps(ricevuta, default=str))
    storia_promette = _dice_implicazione(riga)

    assert scrittura_promette == storia_promette, (
        "le due uscite dicono cose opposte sullo STESSO punteggio.\n"
        f"  la scrittura promette un'implicazione? {scrittura_promette}\n"
        f"  la storia promette un'implicazione?    {storia_promette}\n"
        f"  status del fatto:    {getattr(fatto, 'status', None)!r}\n"
        f"  grounding_score:     {getattr(fatto, 'grounding_score', None)!r}\n"
        f"  la storia, per esteso:\n    {riga}\n"
        f"  la scrittura, per esteso:\n    {ricevuta.get('moat')}\n"
        "⇒ il giudice dà un PUNTEGGIO e non trova contraddizioni; «implica» è "
        "una garanzia che nessuno ha verificato."
    )


def test_CONTROLLO_POSITIVO_senza_punteggio_la_riga_non_promette_NIENTE():
    """L'unica cella che deve essere VERDE ANCHE PRIMA della cura.

    Rilievo di un pari, accolto: le altre due cadono entrambe su main, e una
    si chiama «CONTROLLO» ma **caratterizza il difetto**, non fa da controllo
    positivo. Se domani qualcosa di ambientale rompesse tutto il banco — un
    import, una firma cambiata, un modulo spostato — due rossi su due non si
    distinguerebbero dal difetto che il banco esiste per mostrare.

    Questa regge da entrambe le parti, perché misura la proprietà che le due
    versioni CONDIVIDONO: senza punteggio non si marca niente. Se cade, il
    guasto è nell'ambiente o nella funzione, non nella frase.
    """
    from verimem.temporal_context import history_line

    class _FattoMaiGiudicato:
        proposition = TESTO
        grounding_score = None
        status = "model_claim"
        id = "f-senza"

    riga = history_line(_FattoMaiGiudicato(), [])
    assert riga.strip() == TESTO, (
        f"un fatto MAI giudicato ha ricevuto un marcatore: {riga!r}. "
        "La riga deve portare la sola proposizione: `grounding_score` None "
        "vuol dire che nessuno ha guardato la fonte, e dirlo su ogni riga "
        "sommergerebbe il segnale (temporal_context.py:194-201).")
    assert not _dice_implicazione(riga)


def test_CONTROLLO_la_riga_si_accende_col_NUMERO_non_col_VERDETTO():
    """Il controllo che spiega il difetto invece di limitarsi a vederlo.

    Un fatto finto con un punteggio e NESSUN verdetto: se la riga si accende
    lo stesso, la condizione guarda il tipo del campo e non l'esito — ed è
    esattamente ciò che la cura deve cambiare.
    """
    from verimem.temporal_context import history_line

    class _FattoSenzaVerdetto:
        proposition = TESTO
        grounding_score = 99.6
        status = "model_claim"
        id = "f-prova"

    riga = history_line(_FattoSenzaVerdetto(), [])
    assert not _dice_implicazione(riga), (
        f"la riga promette un'implicazione su un fatto senza verdetto: {riga!r}. "
        "La condizione guarda solo che `grounding_score` sia un numero "
        "(temporal_context.py:202), non che il giudice abbia deciso qualcosa."
    )
