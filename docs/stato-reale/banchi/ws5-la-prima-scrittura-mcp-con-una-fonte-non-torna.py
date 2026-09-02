r"""Su `main` installato, la PRIMA scrittura MCP con una fonte non torna. Le successive si.

Nasce da un caso che avevo archiviato male **due volte**: `W5-8` (una scrittura con
source su stdio non tornava entro 190s, **causa dichiarata IGNOTA**), e poi la mia
rettifica «*non si riproduce in ambiente pulito*» — vera del **wheel**, falsa di `main`.

LA DOMANDA: e' **tutta** la porta MCP a bloccarsi, o solo la **prima** chiamata?
Cambia la gravita': «il primo write si pianta e poi va» e «MCP e' inutilizzabile» sono
due prodotti diversi.

LA MISURA — una sessione, tre scritture **con fonte**, cronometrate, timeout corto::

    pacchetto A   verimem 0.7.1   il wheel      (non chiede il giudice: CONTROLLO)
    pacchetto B   verimem 0.7.6   da `main`     (lo chiede: e' li' che si blocca)

⇒ Il **wheel e' la popolazione di controllo**: se si bloccasse anche lui, la causa non
sarebbe il giudice ma il trasporto.

🔴 ESITO — **si blocca SOLO la prima, e il fatto viene scritto lo stesso**::

    pacchetto          passo          durata   status        grounding
    CONTROLLO wheel    scrittura 1      3.3s   model_claim   None
    CONTROLLO wheel    scrittura 2      0.2s   model_claim   None
    CONTROLLO wheel    scrittura 3      0.1s   model_claim   None
    main installato    scrittura 1     90.0s   🔴 TIMEOUT     -
    main installato    scrittura 2      4.1s   model_claim   99.43
    main installato    scrittura 3      0.3s   model_claim   99.24

🔑 **LE DUE COLONNE VANNO LETTE INSIEME, e insieme dicono una cosa sola**::

    il wheel   RISPONDE SEMPRE e NON GIUDICA MAI      (grounding None, 3 volte su 3)
    main       GIUDICA DAVVERO (99.43 · 99.24) e la PRIMA chiamata supera i 90s

⇒ **Non e' un deadlock.** Nel journal di `main` compaiono, dopo il timeout del client,
`flow.write · audit_tool_call · fact_stored · coherence_warning · flow.write`: **il
server ha completato il lavoro e ha scritto il fatto** — la risposta e' arrivata quando
il client aveva gia' rinunciato. ⇒ **Il costo del primo caricamento e' pagato dalla
prima chiamata**, e le successive costano **0.3-4.1s**.

⚠️ **COSA VIVE UN UTENTE**: il suo primo `remember` con una fonte **sembra fallire**,
mentre il fatto **e' stato scritto e giudicato**. Se riprova, ne scrive due. ⇒ E' un
difetto di **prima impressione**, non di correttezza — ed e' l'opposto di quello del
wheel, che e' **silenzioso e permanente**.

📌 **Il journal del wheel e' VUOTO** mentre quello di `main` ha sei eventi: due
pacchetti, due livelli di osservabilita'. Su quello che risponde sempre non si vede
niente.

COSA E' GIA' ESCLUSO, e come::

    il trasporto / l'avvio     una scrittura SENZA fonte torna in 3.4s
                               (`audit_tool_call latency_ms=3357` nel journal)
    il daemon di encode        con ENGRAM_ENCODE_SERVICE=0 si blocca IDENTICO
                               ⇒ non e' il daemon condiviso dello stack principale,
                                 che pure NON e' isolato (`DISCOVERY_PATH` hardcoded,
                                 `encode_service.py:41`, mio reperto `fdd6df83`)
    il caricamento del modello CPU **0%** e RAM ferma a **357 MB** per oltre 4 minuti
                               ⇒ **aspetta, non calcola**; un cross-encoder caricato
                                 pesa 1-2 GB, non 357
    il download del modello    cache HuggingFace 23 GB, `sentence-transformers` 6.0.1
                               installato nel venv

📌 E il blocco e' **PRIMA del gate**: nel journal dello store non compare nemmeno
`flow.write` — l'ultimo evento e' `python_executor_backend backend=subprocess`.

⚠️ **E i server restano ORFANI**: al timeout del client i processi MCP non muoiono.
Ne ho contati **4 vivi** dopo due bracci, con connessioni loopback ancora `Established`.
Chi esegue questo banco chiuda ciò che apre — **a due gambe** (processo morto **e**
zero connessioni residue).

⚖️ PUNTI DEBOLI: un solo claim e una sola fonte; il client e' scritto da me con l'SDK
`mcp`, non e' Claude Code; e non ho isolato **cosa** aspetta il processo — so che
aspetta, non chi.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-la-prima-scrittura-mcp-con-una-fonte-non-torna.py <dir-con-i-venv>
"""
import json
import os
import subprocess
import sys
import textwrap

CLIENT = r'''
import asyncio, json, os, sys, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE, TMO = sys.argv[1], float(sys.argv[2])
CODA = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
        "e 3 run in corso.")
CLAIM = ["Nella coda ci sono 149 run in attesa.",
         "Nella coda ci sono 3 run in corso.",
         "Nella coda ci sono 2557 run completati."]

env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    t0 = time.time()
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            print("RIGA|handshake|%.1f|-|-" % (time.time() - t0), flush=True)
            for i, claim in enumerate(CLAIM, 1):
                t = time.time()
                try:
                    res = await asyncio.wait_for(
                        s.call_tool("hippo_remember",
                                    {"proposition": claim, "source": CODA}), TMO)
                    testo = "".join(str(getattr(c, "text", "")) for c in (res.content or []))
                    d = json.loads(testo)
                    print("RIGA|scrittura %d|%.1f|%s|%s"
                          % (i, time.time() - t, d.get("status"), d.get("grounding_score")),
                          flush=True)
                except asyncio.TimeoutError:
                    print("RIGA|scrittura %d|%.1f|TIMEOUT|-" % (i, time.time() - t), flush=True)
                except Exception as e:
                    print("RIGA|scrittura %d|%.1f|errore %s|-"
                          % (i, time.time() - t, type(e).__name__), flush=True)

asyncio.run(main())
'''


def versione(venv):
    r = subprocess.run([os.path.join(venv, "Scripts", "pip.exe"), "show", "verimem"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for riga in (r.stdout or "").splitlines():
        if riga.lower().startswith("version:"):
            return riga.split(":", 1)[1].strip()
    return "?"


def sessione(venv, store, tmo):
    os.makedirs(store, exist_ok=True)
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script,
                            store, str(tmo)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=tmo * 4 + 300, env=env,
                           cwd=os.path.dirname(venv))
        return [x[5:].split("|") for x in (r.stdout or "").splitlines() if x.startswith("RIGA|")]
    except subprocess.TimeoutExpired:
        return []


def journal(store):
    """La fonte NON bufferizzata: lo stdout di un sottoprocesso mente, il journal no."""
    p = os.path.join(store, "events.jsonl")
    if not os.path.exists(p):
        return []
    fuori = []
    for riga in open(p, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(riga)
            fuori.append(d.get("name", ""))
        except Exception:
            pass
    return fuori


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-con-i-venv>" % sys.argv[0])
        raise SystemExit(2)
    base = sys.argv[1]
    tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    bracci = [("CONTROLLO wheel", os.path.join(base, "venv_utente")),
              ("main installato", os.path.join(base, "venv_main"))]

    print("  timeout per scrittura: %.0fs   (tre scritture CON fonte, una sessione)\n" % tmo)
    print("  %-18s %-12s %-14s %10s  %-14s %s"
          % ("pacchetto", "versione", "passo", "durata", "status", "grounding"))
    print("  " + "-" * 88)
    esiti = {}
    for nome, venv in bracci:
        if not os.path.exists(os.path.join(venv, "Scripts", "python.exe")):
            print("  %-18s 🔴 venv assente" % nome)
            continue
        ver = versione(venv)
        store = os.path.join(base, "prima_" + ver.replace(".", ""))
        righe = sessione(venv, store, tmo)
        if not righe:
            print("  %-18s %-12s (nessuna riga: la sessione non ha prodotto output)" % (nome, ver))
        for r in righe:
            passo, dur, stato, g = (r + ["-", "-", "-", "-"])[:4]
            print("  %-18s %-12s %-14s %9.1fs  %-14s %s"
                  % (nome, ver, passo, float(dur), stato, g))
            esiti[(nome, passo)] = stato
        ev = journal(store)
        print("  %-18s %-12s journal: %s" % ("", "", ", ".join(ev[:6]) or "(vuoto)"))
        print()

    print("=== VERDETTO ===")
    primo = esiti.get(("main installato", "scrittura 1"))
    dopo = [esiti.get(("main installato", "scrittura %d" % i)) for i in (2, 3)]
    ctrl = esiti.get(("CONTROLLO wheel", "scrittura 1"))
    if ctrl == "TIMEOUT":
        print("  ⚠️ ANCHE IL CONTROLLO SI BLOCCA: la causa non e' il giudice ma il")
        print("     trasporto o l'avvio. Il verdetto su main non e' leggibile.")
    elif primo == "TIMEOUT" and any(d and d != "TIMEOUT" for d in dopo):
        print("  🔴 SI BLOCCA SOLO LA PRIMA: le successive rispondono ⇒ un client vero")
        print("     (Claude Code) vede il PRIMO `remember` con fonte andare in timeout,")
        print("     e il resto della sessione funzionare. Il wheel non si blocca affatto.")
    elif primo == "TIMEOUT":
        print("  🔴 SI BLOCCA E NON RIPARTE entro questa finestra: la porta MCP con fonte")
        print("     e' inutilizzabile su questo pacchetto.")
    elif primo:
        print("  🟢 la prima scrittura torna (%s): il blocco NON si riproduce con" % primo)
        print("     timeout %.0fs ⇒ era piu' lento della finestra, non fermo." % tmo)
    else:
        print("  ⚠️ esito non classificabile — leggi il journal riga per riga.")


main()
