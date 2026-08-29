r"""La cura dei verbali e' raggiungibile dalle porte che un utente usa davvero?

Paga il limite che ho dichiarato io mezz'ora fa chiudendo
`ws5-la-cura-che-esiste-salva-i-quattro-verbi.py`: la coppia
`writer_role='external_content'` + `provenance_trusted=True` salva **4 verbali
veri su 4**, ma quella misura e' su `run_validation_gate` - **una funzione, non
una porta**. ⇒ **Verde li' non vuol dire che un utente possa ottenerlo.**

LE TRE PORTE, sugli stessi quattro claim e la stessa fonte:
    porta  A  `run_validation_gate`   (gia' misurata: 4/4 con la coppia)
    porta  B  SDK `Client.add`        - quello che usa chi importa la libreria
    porta  C  MCP `hippo_remember`    - quello che usa un agente

E i DUE regimi che contano per un utente:
    base                        senza dire niente (il caso di default)
    advice                      solo `writer_role='external_content'`, cioe'
                                **cio' che la ricevuta consiglia di fare**

⚠️ **POPOLAZIONE DI CONTROLLO**: gli stessi tre falsi del banco precedente
(`respinto`, `rinviato`, `sospeso`) su ogni porta e ogni regime. Servono a due
cose: (1) dire se una porta e' piu' permissiva **in generale** invece che sulla
cura; (2) impedire che «4 veri salvi» venga letto come un miglioramento quando
e' un gate che ha smesso di guardare.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
MCP chiamato **in-process** via `_call_tool_impl`, **non** un client su stdio.
⚖️ PUNTI DEBOLI: MCP in-process (se qualcuna ha stdio, la sua misura batte
questa); una fonte sola; leggo lo stato finale (`status`/`action`), non tutti i
campi - e i campi **hanno nomi diversi fra le porte**.

ESITO - **lo stesso consiglio, seguito alla lettera, da' TRE esiti diversi su
tre porte: funziona, non fa nulla, e' rifiutato**::

    porta                  regime                 VERI salvi  FALSI fermati  note
    A run_validation_gate  base                   0/4         2/3
    A run_validation_gate  advice: writer_role    0/4         2/3
    B SDK Client.add       base                   0/4         2/3
    B SDK Client.add       advice: writer_role    4/4         2/3
    C MCP hippo_remember   base                   0/4         2/3
    C MCP hippo_remember   advice: writer_role    0/4         0/3            RIFIUTATO

🔑 **UN UTENTE CHE FA ESATTAMENTE CIO' CHE LA RICEVUTA GLI DICE OTTIENE**:
    sull'SDK          i suoi quattro verbali veri SALVI      (4/4)
    sulla porta gate  esattamente niente                     (0/4)
    su MCP            un errore                              (rifiutato)
E la differenza **non e' nel suo comportamento**: e' nella porta.

🪞 **E QUALIFICO AL RIBASSO QUELLO CHE HO SCRITTO IO MEZZ'ORA FA.** Avevo
consegnato: «*la ricevuta consiglia meta' della cura*». ⇒ **Vero sulla porta
diretta, FALSO sull'SDK**: li' l'advice e' **completo**, perche' il `Client`
aggiunge `provenance_trusted` per conto suo (`client.py:539`) e il risultato e'
**4 su 4**. Chi avesse letto la mia frase come «l'advice e' sbagliato» avrebbe
concluso male. ⇒ La formulazione che regge e': **l'advice e' completo solo se
la porta ci mette la meta' che non nomina**, e **due porte su tre non la
mettono**.

⚠️ **E LEGGO IO IL MIO 0/3 PRIMA CHE LO LEGGA MALE QUALCUN ALTRO.** Su
`C + advice` la colonna «FALSI fermati» dice **0/3**: NON vuol dire che MCP
lasci passare i falsi. Vuol dire che **tutte e sette le chiamate sono state
rifiutate dallo schema**, quindi nessun falso e' stato ne' fermato ne' ammesso.
La riga giusta da leggere per la permissivita' di MCP e' **`C base`: 2/3,
identica a tutte le altre.**

📌 Chiude il limite che avevo dichiarato io consegnando la cura: «*verde su
`run_validation_gate` non vuol dire raggiungibile da tutte le porte*». **Non lo
e': una porta su tre.**

REGIME: build corrente · store TEMPORANEO da `trap` · MCP **in-process** via
`_call_tool_impl`.
⚖️ PUNTI DEBOLI: MCP in-process, non stdio; una fonte sola; 4 veri + 3 falsi;
i **vocabolari delle porte non coincidono** (`persist` sul gate, `model_claim`
sull'SDK) e li normalizzo in `_passa()` - se quella normalizzazione fosse
sbagliata, tutta la tabella lo sarebbe.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-cura-e-raggiungibile-dalle-porte-vere.py <dir-temp>
"""
import asyncio
import json
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem import Client  # noqa: E402
from verimem import mcp_server as M  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

FONTE = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
         "e la linea e' stata approvata dalla commissione.")
CLAIM = "Il collaudo della linea 3 e' stato %s il 12 marzo."
VERI = ["completato", "approvato", "validato", "verificato"]
FALSI = ["respinto", "rinviato", "sospeso"]

REGIMI = [("base", {}), ("advice: writer_role", {"writer_role": "external_content"})]


def _porta_a(claim, extra, _topic):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=FONTE, grounding_llm=None,
                            ground_write=True, **extra)
    return str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")


def _porta_b(claim, extra, topic):
    d = Client().add(claim, topic=topic, source=FONTE, **extra)
    d = d if isinstance(d, dict) else getattr(d, "__dict__", {})
    return str(d.get("status") or d.get("action") or "?")


async def _porta_c(claim, extra, topic):
    args = {"proposition": claim, "topic": topic, "source": FONTE}
    args.update(extra)
    out = await M._call_tool_impl("hippo_remember", args)
    txt = " ".join(getattr(o, "text", str(o)) for o in out)
    try:
        d = json.loads(txt)
    except Exception:
        return "PARSE-FAIL"
    return "RIFIUTATO" if "error" in d else str(d.get("status") or "?")


#: cosa conta come «passato» su ciascuna porta: i vocabolari NON coincidono
def _passa(stato):
    return stato in ("persist", "model_claim", "verified")


async def main():
    print("  %-22s %-22s %-13s %-15s %s"
          % ("porta", "regime", "VERI salvi", "FALSI fermati", "note"))
    print("  " + "-" * 96)
    for pnome, fn in (("A run_validation_gate", _porta_a),
                      ("B SDK Client.add", _porta_b),
                      ("C MCP hippo_remember", _porta_c)):
        for rnome, extra in REGIMI:
            salvi = fermati = 0
            nota = ""
            for i, v in enumerate(VERI):
                st = fn(CLAIM % v, extra, "p/%s%d" % (rnome[:4], i))
                st = await st if asyncio.iscoroutine(st) else st
                if st in ("RIFIUTATO", "PARSE-FAIL"):
                    nota = st
                elif _passa(st):
                    salvi += 1
            for i, f in enumerate(FALSI):
                st = fn(CLAIM % f, extra, "q/%s%d" % (rnome[:4], i))
                st = await st if asyncio.iscoroutine(st) else st
                if st in ("RIFIUTATO", "PARSE-FAIL"):
                    nota = st
                elif not _passa(st):
                    fermati += 1
            print("  %-22s %-22s %-13s %-15s %s"
                  % (pnome, rnome, "%d/%d" % (salvi, len(VERI)),
                     "%d/%d" % (fermati, len(FALSI)),
                     nota or ""))

    print("\n=== COME SI LEGGE ===")
    print("  La domanda NON e' «quale porta e' migliore»: e' se l'utente possa")
    print("  OTTENERE la cura seguendo cio' che il prodotto gli dice di fare.")
    print("  Un RIFIUTATO nella colonna note e' la risposta piu' netta possibile:")
    print("  li' l'advice non e' insufficiente, e' ineseguibile.")
    print("  ⚠️ I vocabolari delle porte NON coincidono (persist / model_claim):")
    print("     senza normalizzarli si conterebbero passaggi che non ci sono.")


asyncio.run(main())
