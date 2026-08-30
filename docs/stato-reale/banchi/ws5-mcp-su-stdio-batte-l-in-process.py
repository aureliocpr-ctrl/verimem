r"""MCP su STDIO - la porta HEADLINE: una scrittura CON source non risponde.

⚠️ Banco nato per **invalidare tre miei referti** e finito su qualcosa di piu'
grosso di quello che cercavo.

In tre banchi (`ws5-C3-le-stesse-operazioni-sulle-due-porte.py`,
`ws5-C3-la-lettura-quattro-vie-una-domanda.py`,
`ws5-la-cura-e-raggiungibile-dalle-porte-vere.py`) ho scritto lo stesso limite:

    «MCP chiamato in-process via `_call_tool_impl`, NON un client su stdio.
     Se qualcuna ha stdio, la sua misura batte questa.»

Nessuna l'ha preso in due giorni. ⇒ L'ho preso io, per rifare le stesse
operazioni da un client vero. **Il confronto non si e' potuto fare, e il motivo
per cui non si e' potuto fare vale piu' del confronto.**

⚠️ **PERCHE' QUESTA PORTA CONTA PIU' DELLE ALTRE**: `pyproject.toml` la chiama
«*MCP server - the HEADLINE use (`verimem mcp` for Claude Code / Cursor)*». E'
la porta da cui passa un agente, ed e' quella che Aurelio ha configurata.

ESITO, e la riga di CONTROLLO sta dentro la stessa tabella::

    scrittura       in-process                 STDIO (client vero)
    handshake       -                          5.1s
    SENZA source      3.7s  quarantined        3.8s  quarantined      ← IDENTICI
    CON source       28.9s  model_claim        NESSUNA RISPOSTA entro 190s

🔑 **LA PRIMA RIGA E' IL CONTROLLO, E CHIUDE TRE SPIEGAZIONI IN UN COLPO**:
senza source le due vie danno **3.7s contro 3.8s** e lo **stesso identico
esito** (`quarantined`). ⇒ Il trasporto stdio **funziona**, il client
**funziona**, il lancio del server **funziona**. Se il difetto fosse li',
cadrebbe anche questa riga.
⇒ **E' il percorso col GIUDICE a non tornare**: la stessa operazione che
in-process costa **28.9 secondi** su stdio non risponde entro **190**.

⚠️ **L'asimmetria e' quella che punisce l'utente diligente**: chi scrive
**senza** fonte ottiene la sua risposta in 4 secondi; chi passa **la fonte** -
cioe' chi fa la cosa che il prodotto chiede per verificare un fatto - aspetta.

📌 Altre osservazioni dello stesso giro: handshake 2.6s-5.1s · `list_tools`
risponde **249 tool** · il fenomeno si e' ripetuto in **3 prove su 3** (150s,
190s, 190s) in due regimi diversi.

🪞 **DUE MIE IPOTESI SULLA CAUSA, ENTRAMBE FALSIFICATE A VARIABILE SINGOLA.**
Le riporto perche' risparmiano il giro a chi viene dopo:
① **`HIPPO_ENCODE_DELEGATE_ONLY=1`** (e' nell'ambiente reale di Aurelio, e il
   server logga `encode daemon unavailable and in-process cold-load is disabled
   ... caller must degrade`). ⇒ A/B con l'unica variabile: **con la variabile
   NON risponde in 190s, senza la variabile NON risponde in 190s.** Il log era
   un depistaggio: riguarda il backfill dell'embedding, non il giudice.
② **Log del giudice su stdout che corrompono il framing JSON-RPC** (su stdio
   stdout E' il canale, e il giudice emette un `RuntimeWarning` noto). ⇒
   Leggendo il canale grezzo: **una sola riga su stdout, ed e' JSON valida** (la
   risposta all'handshake). **Nessuna riga non-JSON. Il protocollo e' pulito.**

⇒ **La causa resta IGNOTA**, e lo scrivo invece di sceglierne una terza: due
spiegazioni plausibili sono cadute, e una terza non misurata varrebbe come le
prime due prima di misurarle.

✅ **IL CONFONDENTE E' STATO TOLTO, E IL DIFETTO RESTA.** Avevo dichiarato:
«*tutte le prove girano su uno store temporaneo, dove il daemon di encoding non
esiste; non affermo che questo succeda in uso normale*». Il 30/08 alle 21:43 il
daemon e' **tornato su** (righello: gli ultimi 12 fatti dello store hanno tutti
il vettore) e ho **rieseguito questo stesso banco, senza cambiare una riga**::

    scrittura         in-process              STDIO
    handshake         -                       3.5s
    SENZA source      2.5s   model_claim      2.4s   model_claim
    CON source       20.9s   model_claim      NESSUNA RISPOSTA entro 190s

🔑 **E la prova che il daemon serviva davvero il processo figlio e' nella riga
in-process: da 28.9s a 20.9s** sulla stessa identica operazione. ⇒ Il daemon
c'era, in-process ne ha beneficiato, **e su stdio non e' cambiato niente**.
⇒ **Il difetto di stdio NON e' il daemon di encoding.** Il confondente che
avevo dichiarato come «il primo che chiunque deve provare» e' provato e cade.

📌 **CONSEGUENZA SUI MIEI TRE REFERTI**: il limite **non si chiude** - non posso
confrontare gli esiti, perche' su stdio l'esito non arriva. Restano misure
in-process, e ora si sa **perche'** nessuna le aveva rifatte su stdio. L'unico
confronto possibile e' sulla scrittura **senza** source, che risponde su
entrambe le vie.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · server lanciato
come processo figlio (`python -m verimem.mcp_server`) e ucciso alla fine ·
client: quello ufficiale del pacchetto `mcp`, piu' una prova a mano sul canale
grezzo.
⚖️ ALTRI PUNTI DEBOLI: non ho aspettato oltre 190s - **non so se risponda mai**,
e «non risponde entro 190s» e' tutto cio' che affermo; il client e' quello del
pacchetto, non Claude Code o Cursor.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-mcp-su-stdio-batte-l-in-process.py <dir-temp>
"""
import asyncio
import json
import os
import sys
import time

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
TEMP = sys.argv[1]
os.environ["HIPPO_DATA_DIR"] = TEMP

FONTE = "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo."
CLAIM = "Il collaudo della linea 3 si e' concluso il 12 marzo."

#: oltre questo non aspetto: il banco afferma «non risponde entro», non «mai»
ATTESA = 190


def _stato(txt):
    try:
        return str(json.loads(txt).get("status") or "?")
    except Exception:
        return "?"


async def in_process(con_source):
    from verimem import mcp_server as M
    args = {"proposition": CLAIM, "topic": "ip/%s" % con_source}
    if con_source:
        args["source"] = FONTE
    t = time.time()
    out = await M._call_tool_impl("hippo_remember", args)
    return time.time() - t, _stato(" ".join(getattr(o, "text", str(o)) for o in out))


async def su_stdio(ses, con_source):
    args = {"proposition": CLAIM, "topic": "st/%s" % con_source}
    if con_source:
        args["source"] = FONTE
    t = time.time()
    try:
        res = await asyncio.wait_for(ses.call_tool("hippo_remember", args), timeout=ATTESA)
    except asyncio.TimeoutError:
        return time.time() - t, "NESSUNA RISPOSTA"
    return time.time() - t, _stato(" ".join(getattr(c, "text", str(c)) for c in (res.content or [])))


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = TEMP
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    params = StdioServerParameters(command=sys.executable,
                                   args=["-m", "verimem.mcp_server"], env=env)

    print("  %-24s %-26s %s" % ("scrittura", "in-process", "STDIO (client vero)"))
    print("  " + "-" * 78)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as ses:
            t = time.time()
            await asyncio.wait_for(ses.initialize(), timeout=120)
            print("  %-24s %-26s %.1fs" % ("handshake", "-", time.time() - t))
            for con_source in (False, True):
                ta, sa = await in_process(con_source)
                tb, sb = await su_stdio(ses, con_source)
                print("  %-24s %-26s %s"
                      % ("CON source" if con_source else "SENZA source",
                         "%5.1fs  %s" % (ta, sa),
                         ("%5.1fs  %s" % (tb, sb)) if sb != "NESSUNA RISPOSTA"
                         else "NESSUNA RISPOSTA entro %ds" % ATTESA))

    print("\n=== COME SI LEGGE ===")
    print("  Le due righe vanno lette INSIEME: se anche 'SENZA source' non")
    print("  rispondesse, il difetto sarebbe il trasporto. Se risponde e l'altra")
    print("  no, il trasporto funziona ed e' il percorso col GIUDICE a non tornare.")
    print("  ✅ Il confondente del daemon E' STATO TOLTO (rieseguito il 30/08 col")
    print("     daemon su): in-process accelera 28.9s -> 20.9s, stdio non cambia.")


asyncio.run(main())
