"""README:355 — la riga della tabella «it depends on the port» che ho scritto IO.

IL CLAIM, testuale dal README pubblicato (riga 355 il 13/09 — era la 352 quando
l'ho scritta il 10/09, e il numero si muove a ogni riga aggiunta sopra: il
presidio cerca il TESTO, mai il numero, tabella «What gets your
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
import pathlib

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


#: I nomi che README:355 insegna a LEGGERE nella ricevuta di `hippo_remember`,
#: presi dalla riga stessa: «`stored: true`, and the receipt carries
#: `layers: ['L4-skipped']`. **Read that field.** `admitted` on its own does not
#: mean judged.»
#:
#: ⚠️ `hippo_remember` sta nella stessa riga fra backtick ma e' il NOME DELLA
#: PORTA, non un campo della ricevuta: sta fuori di proposito.
NOMI_CHE_LA_RIGA_INSEGNA = frozenset({"stored", CAMPO, "admitted"})

#: Il README letto dalla radice del repo: serve al controllo positivo in fondo.
_README = pathlib.Path(__file__).resolve().parents[1] / "README.md"

#: 🔑🔑 LA CONDIZIONE STA NEL NOME, E NON E' PEDANTERIA.
#:
#: README:355 promette `layers: ['L4-skipped']` **solo quando il demone manca**:
#: «**if the daemon is missing or does not come up**, the write is stored
#: UNJUDGED: `stored: true`, and the receipt carries `layers: ['L4-skipped']`».
#: Qui il giudice GIRA (`adjudication.judge.model` = `local_gate_ce_v2`, visibile
#: nel messaggio d'errore), quindi questa misura NON e' nella condizione della
#: promessa e da sola **non dimostra che il README menta**.
#:
#: Senza la condizione nel nome, un elenco intitolato «i nomi che mancano» si
#: legge fra sei mesi come «la pagina promette e il prodotto non mantiene» — che
#: sarebbe un'accusa costruita misurando dove la promessa non si applica. E'
#: **l'errore che questo presidio esiste per denunciare**, commesso dal presidio.
#: Rilievo del pari (@Dati), 13/09, accettato: il titolo porta la condizione.
#:
#: CHE COSA MISURA ALLORA, e perche' vale: un utente che legge quella riga e poi
#: guarda una ricevuta qualunque — la stragrande maggioranza, col demone su —
#: cerca tre nomi e ne trova UNO SOLO, e non dove lo cerca. La riga non dice
#: «solo senza demone vedrai questi nomi», dice «Read that field».
#:
#: Misurato il 13/09/2026 invocando la porta, con la sonda dei percorsi che il
#: messaggio qui sotto rifa' a ogni esecuzione:
#:     stored    -> DA NESSUNA PARTE
#:     layers    -> DA NESSUNA PARTE
#:     admitted  -> presente come VALORE in `adjudication.disposition`
ASSENTI_COL_GIUDICE_ACCESO_IL_13_09 = frozenset({"stored", "layers"})

#: Presenti, ma non come chiave di primo livello: chi segue la riga non li trova
#: dove la riga gli fa credere che siano. Rilievo del pari, 13/09: «assente» e
#: «presente sotto un altro percorso» sono due cose diverse e vanno separate —
#: la prima e' un buco, la seconda e' un problema di NOME, e la cura non e' la
#: stessa.
ALTROVE_COL_GIUDICE_ACCESO_IL_13_09 = frozenset({"admitted"})


def _percorsi(nodo, bersaglio: str, qui: str = "") -> list[tuple[str, str]]:
    """Ogni punto dove `bersaglio` compare, come CHIAVE o come VALORE.

    Serve a non chiamare «assente» cio' che c'e' sotto un altro percorso: senza
    questo, `admitted` — che e' il valore di `adjudication.disposition` — finiva
    nello stesso mucchio di `layers`, che non c'e' da nessuna parte.
    """
    fuori: list[tuple[str, str]] = []
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            p = f"{qui}.{k}" if qui else str(k)
            if k == bersaglio:
                fuori.append(("chiave", p))
            fuori += _percorsi(v, bersaglio, p)
    elif isinstance(nodo, (list, tuple)):
        for i, v in enumerate(nodo):
            fuori += _percorsi(v, bersaglio, f"{qui}[{i}]")
    elif isinstance(nodo, str) and nodo == bersaglio:
        fuori.append(("valore", qui))
    return fuori


@pytest.mark.asyncio
async def test_quali_nomi_della_riga_la_ricevuta_non_rende(tmp_data_dir):
    """🔴 Il difetto e' APERTO e questo test lo REGISTRA. Cade nei DUE versi.

    ⚙️ ERA UN `xfail(strict=True)` su `layers` solo. Convertito il 13/09 alla
    forma decisa il 12/09 — «un test misura e resta, o si toglie con la ragione»
    — e nel convertirlo il difetto si e' rivelato piu' grande: un `xfail` chiede
    «il campo c'e'?» e si accontenta del no; un cricchetto chiede «quali
    mancano, e dove sono finiti?» e deve elencarli.

    ⚠️ **CON IL GIUDICE ACCESO** — la condizione e' nel nome delle due costanti
    e nel messaggio, perche' README:355 promette `layers` solo a demone assente.
    Quel caso e' di @Piattaforma (T26a/a) e la misura e' sua: un'asserzione su
    quella condizione, qui, proverebbe uno scenario che non ho riprodotto.

    🟢 Se un nome ARRIVA alla porta, qui diventa rosso: togli quel nome dalla
       costante nello stesso commit; a zero, il presidio diventa positivo e il
       docstring perde il paragrafo del difetto.
    🔴 Se un nome SPARISCE, o si sposta sotto un altro percorso, la ricevuta ha
       perso un campo che la pagina nomina e nessuno se ne accorgerebbe.

    PER L'UTENTE: chi segue README:355 cerca tre nomi nella ricevuta e ne trova
    uno solo, e non dove lo cerca — quindi non ha modo di sapere se la scrittura
    e' stata giudicata, che e' cio' che quella riga dice di NON fare.

    LA CURA E' SUL README, non sul prodotto: `judged` e' il campo giusto e c'e'
    gia' (lo presidia il test qui sotto). Ma la riga non si riscrive a occhio:
    serve la misura nella condizione che descrive. Una riga di documentazione
    corretta a occhio e' come e' nato questo difetto.
    """
    ricevuta = await _ricevuta_di_una_scrittura_con_fonte()

    # Controllo positivo: se la ricevuta tornasse vuota, ogni «manca» sarebbe
    # vero per la ragione sbagliata e questo test misurerebbe il nulla.
    assert ricevuta, "la porta non ha reso nessuna ricevuta: il presidio non misura"

    dove = {n: _percorsi(ricevuta, n) for n in NOMI_CHE_LA_RIGA_INSEGNA}
    assenti = frozenset(n for n, p in dove.items() if not p)
    altrove = frozenset(
        n for n, p in dove.items() if p and not any(t == "chiave" and "." not in q for t, q in p)
    )
    mappa = "\n".join(
        f"      {n:<10} -> {dove[n] if dove[n] else 'DA NESSUNA PARTE'}"
        for n in sorted(NOMI_CHE_LA_RIGA_INSEGNA)
    )

    assert assenti == ASSENTI_COL_GIUDICE_ACCESO_IL_13_09, (
        "i nomi di README:355 ASSENTI dalla ricevuta (giudice acceso) sono "
        "cambiati.\n"
        f"  oggi     : {sorted(assenti)}\n"
        f"  il 13/09 : {sorted(ASSENTI_COL_GIUDICE_ACCESO_IL_13_09)}\n"
        f"  arrivati : {sorted(ASSENTI_COL_GIUDICE_ACCESO_IL_13_09 - assenti)}\n"
        f"  spariti  : {sorted(assenti - ASSENTI_COL_GIUDICE_ACCESO_IL_13_09)}\n"
        f"  dove sta ciascuno, misurato adesso:\n{mappa}\n"
        f"  chiavi di primo livello: {sorted(ricevuta)}\n"
        "⚠️ Ricorda la condizione: `layers` la pagina lo promette **solo a "
        "demone assente**, e qui il giudice gira. Questo elenco non dimostra da "
        "solo che il README menta.\n"
        "**Guarda la riga e la porta, non aggiornare l'elenco.**"
    )

    assert altrove == ALTROVE_COL_GIUDICE_ACCESO_IL_13_09, (
        "i nomi di README:355 che esistono ma NON come chiave di primo livello "
        "sono cambiati.\n"
        f"  oggi     : {sorted(altrove)}\n"
        f"  il 13/09 : {sorted(ALTROVE_COL_GIUDICE_ACCESO_IL_13_09)}\n"
        f"  dove sta ciascuno, misurato adesso:\n{mappa}\n"
        "🟢 Se uno e' RISALITO a chiave di primo livello, la riga del README "
        "torna vera per quel nome: togli la sua riga da qui.\n"
        "🔴 Se uno e' SCESO sotto un percorso annidato, la pagina continua a "
        "nominarlo come se fosse li' in cima. Non e' un buco, e' un problema di "
        "NOME — e la cura e' diversa: o la riga cita il percorso vero, o il "
        "campo risale."
    )


def test_CONTROLLO_la_riga_del_readme_insegna_ANCORA_quei_tre_nomi():
    """Il presidio sopra confronta con una riga che potrebbe essere riscritta.

    Se il README cambia quella riga, gli elenchi qui sopra smettono di descrivere
    una promessa viva e il loro rosso non vorrebbe piu' dire niente. Questo lo
    dice invece di lasciarlo passare — ed e' la meta' che un `xfail` non poteva
    avere, perche' l'`xfail` guardava la porta e mai la pagina.
    """
    testo = _README.read_text(encoding="utf-8", errors="replace")
    i = testo.find("Read that field")
    assert i > 0, (
        "README:355 non contiene piu' «Read that field»: la riga presidiata e' "
        "stata riscritta o tolta. Se e' stata CURATA, riscrivi questo presidio; "
        "se e' stata solo spostata, aggiorna il frammento."
    )
    riga = testo[max(0, i - 700) : i + 120]
    mancanti = sorted(n for n in NOMI_CHE_LA_RIGA_INSEGNA if f"`{n}" not in riga)
    assert not mancanti, (
        f"la riga non nomina piu' {mancanti}: insegnava tre campi il 13/09 e gli "
        "elenchi qui sopra sono misurati su quei tre. Se la riga e' stata "
        "riscritta con i nomi giusti, il difetto e' curato e i presidi qui vanno "
        "girati insieme."
    )

    # E la CONDIZIONE, che e' la meta' che rende onesto tutto il resto: se la
    # pagina smettesse di legare `layers` al demone assente, le due costanti qui
    # sopra cambierebbero significato senza cambiare valore.
    assert "if the daemon is missing or does not come up" in riga, (
        "README:355 non lega piu' l'avviso al caso «demone assente». Le costanti "
        "qui sopra si chiamano COL_GIUDICE_ACCESO proprio perche' la promessa "
        "vale nell'altra condizione: se la riga e' cambiata, il nome di quelle "
        "costanti non descrive piu' niente e i presidi vanno riscritti."
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
