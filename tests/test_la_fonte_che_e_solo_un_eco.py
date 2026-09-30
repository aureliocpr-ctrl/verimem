"""Una fonte che ripete il claim e basta non compra il perdono di L1.13.

LA GUARDIA DEL 30/08 (`1a4b8635`) chiede che la provenienza non sia
`agent_claim`. Misurato il 19/09, alla funzione e poi dal dispatcher MCP: quel
criterio da solo si aggira dichiarando un ruolo. Stessa frase passata come
fonte di se' stessa, stesso punteggio del giudice (99.78126525878906):

    writer_role assente   ->  quarantined       (fermato)
    writer_role='user'    ->  model_claim       (SERVIBILE)

`user` e' dentro l'enum pubblico dello schema MCP, e sulla porta MCP chi
scrive e' sempre un agente: «user» li' significa «l'agente dice che l'ha
scritto l'utente».

IL CRITERIO SCELTO (decisione del 19/09, strada (b)): il perdono richiede
DUE cose — provenienza diversa da `agent_claim` **E** una fonte che aggiunga
qualcosa al claim. Una fonte che non dice nulla piu' del claim non e' una
testimonianza: e' un'eco.

⚖️ LIMITE DICHIARATO, e misurato dalla cella `test_il_limite_del_criterio`:
il confronto e' TESTUALE, quindi si aggira aggiungendo una parola alla fonte.
Non e' una svista: nessun criterio testuale regge a un avversario, e il
commit della guardia lo dice gia' («aggirabile per riformulazione, 3 su 3»).
Questa cura chiude l'ECO LETTERALE — il caso misurato 5 su 5 dal banco
indipendente — e lascia scritto quanto costa aggirarla.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

from tests._esito import esito
from verimem.gate_router import AGENT_CLAIM, USER_INPUT
from verimem.l1_completion_detector import detect_unsupported_completion_claim

# Il verbale di TERZI: la fonte dichiara svolgimento ED esito, il claim ne
# ricalca una parte. E' il caso legittimo e deve continuare a passare.
FONTE_TERZI = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito "
               "positivo e la linea e' stata approvata dalla commissione.")
CLAIM = "Il collaudo della linea 3 e' stato concluso il 12 marzo."


def _rileva(source, provenance):
    return detect_unsupported_completion_claim(
        proposition=CLAIM, verified_by=None, source=source,
        provenance=provenance,
    )


def test_l_eco_non_e_perdonata_con_nessun_ruolo():
    """D ed F: la fonte e' il claim. Nessun ruolo dichiarato la salva."""
    for ruolo in (USER_INPUT, "external_content", "trusted_hook"):
        assert _rileva(CLAIM, ruolo) is not None, (
            f"con provenance={ruolo!r} la fonte-eco ha comprato il perdono")


def test_il_verbale_di_terzi_passa_ancora():
    """B ed E: NON-REGRESSIONE. La cura del 28/08 deve restare viva."""
    assert _rileva(FONTE_TERZI, USER_INPUT) is None
    assert _rileva(FONTE_TERZI, "external_content") is None


def test_senza_ruolo_resta_fermato_come_prima():
    """La guardia del 30/08 non si tocca: agent_claim non e' perdonato."""
    assert _rileva(FONTE_TERZI, AGENT_CLAIM) is not None
    assert _rileva(CLAIM, AGENT_CLAIM) is not None


def test_il_verbale_fermato_dice_quale_leva_manca():
    """L'assenza ha un canale: chi ha un verbale vero deve sapere cosa fare.

    Il suggerimento si da' SOLO quando la leva funzionerebbe davvero — cioe'
    quando la fonte sostiene il participio. Darlo a chiunque venga fermato
    insegnerebbe l'aggiramento a chi non ha nessuna fonte.
    """
    fermato = _rileva(FONTE_TERZI, AGENT_CLAIM)
    assert fermato is not None
    assert "writer_role" in (fermato.advice or ""), fermato.advice

    # E a chi NON ha una fonte che lo sostiene, la leva non si nomina.
    senza_fonte = _rileva(None, AGENT_CLAIM)
    assert senza_fonte is not None
    assert "writer_role" not in (senza_fonte.advice or ""), senza_fonte.advice


def test_il_limite_del_criterio():
    """Quanto costa aggirarlo: UNA PAROLA. Misurato, non dichiarato.

    Cella che documenta il limite invece di lasciarlo come debito: se domani
    qualcuno la vede rossa, il criterio e' diventato piu' forte, non piu'
    debole.
    """
    eco_piu_una_parola = CLAIM + " Confermato."
    assert _rileva(eco_piu_una_parola, USER_INPUT) is None, (
        "il criterio testuale ora regge anche a una parola in piu': "
        "aggiorna questa cella, il limite e' cambiato")


def test_alla_porta_mcp_l_eco_con_user_resta_fuori_dal_recall():
    """Condizione del lead: D ed F dal DISPATCHER, non dalla funzione.

    In un processo pulito, perche' le variabili dello store vanno impostate
    PRIMA dell'import: il 14/09 il server MCP ha scritto nello store VERO con
    le tre variabili puntate a quello di prova.
    """
    # ⚠️ stringa RAW e nessun escape annidato: la prima stesura aveva
    # `\s` dentro una stringa non-raw e Python ha alzato
    # «SyntaxWarning: invalid escape sequence». Qui i testi si uniscono con
    # uno spazio, cosi' non serve nemmeno un a-capo.
    codice = textwrap.dedent(r"""
        import asyncio, os, re, tempfile
        d = tempfile.mkdtemp()
        for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
            os.environ[v] = d
        os.environ["ENGRAM_EVENT_LOG"] = os.path.join(d, "eventi.jsonl")
        from verimem import mcp_server as M
        CLAIM = "Il collaudo della linea 3 e' stato concluso il 12 marzo."
        async def uno():
            b = await M.call_tool("hippo_remember", {
                "proposition": CLAIM, "source": CLAIM,
                "topic": "prova/t144", "writer_role": "user"})
            t = " ".join(" ".join(getattr(x, "text", "").split()) for x in b)
            m = re.search(r'"status":\s*"([^"]+)"', t)
            print("STATUS=%s" % (m.group(1) if m else "?"))
        asyncio.run(uno())
    """)
    # ⚠️ L'ESITO DEL PROCESSO SI GUARDA, e non e' una formalita': un processo
    # ucciso lascia un output TRONCO, e allora ogni assert qui sotto direbbe
    # «manca la stringa STATUS=» invece di «il processo e' morto», con la causa
    # tagliata via dalla piattaforma. `tests/_esito.py` esiste per questo, e la
    # prima stesura di questo banco non lo usava: me l'ha detto il presidio.
    risultato = subprocess.run([sys.executable, "-c", codice],
                               capture_output=True, text=True, timeout=600)
    testo = esito(risultato)
    riga = [r for r in testo.splitlines() if r.startswith("STATUS=")]
    assert riga, f"la porta non ha risposto: {testo}"
    assert riga[0] == "STATUS=quarantined", (
        f"alla porta l'eco con writer_role=user e' entrata SERVIBILE: {riga[0]}")


def test_chi_non_dichiara_la_provenienza_non_viene_irrigidito():
    """La compatibilita' del 30/08 vale anche per la condizione nuova.

    `test_senza_provenienza_dichiarata_il_perdono_resta_come_prima` (banco
    della guardia) dichiara che chi chiama il detector SENZA provenienza
    ottiene il comportamento del 28/08. La prima stesura di questa cura lo
    irrigidiva e quel banco e' diventato rosso: la decisione non e' mia e non
    la scavalco. Il prodotto resta coperto perche' il gate la provenienza la
    calcola sempre — `None` qui vuol dire «chiamata diretta al detector».
    """
    assert _rileva(CLAIM, None) is None
