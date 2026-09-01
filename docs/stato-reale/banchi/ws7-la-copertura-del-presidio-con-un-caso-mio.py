"""Il presidio di `c539ab18` copre anche un caso che il suo test NON contiene?

PERCHE'. Alle 08:02 avevo provato il RED su quella cura: togliendola, il test
`test_una_quarantena_LESSICALE_non_si_attribuisce_al_moat` cade. Ma @ws4
(08:09) ha portato la forma positiva che mancava al criterio:

    🔑 IL CASO DEV'ESSERE SCELTO DA CHI VERIFICA, NON DA CHI E' VERIFICATO.

⇒ Il mio RED provava il COLLEGAMENTO (il sensore e' attaccato) e non la
COPERTURA (vede anche cio' che l'autore non ha pensato). **Un presidio puo'
essere perfettamente collegato e cieco su tutto cio' che sta fuori
dall'immaginazione di chi l'ha scritto — e il RED non lo mostra MAI, perche'
usa quell'immaginazione come metro.**

IL CASO MIO, scelto diverso dal suo su TRE assi:
  · il suo usa `L1.19` (attestazione di misura mancante); io uso un
    AUTO-AFFERMAZIONE generica, che passa da un altro screen lessicale
  · il suo e' in inglese; il mio in ITALIANO
  · il suo claim ha una fonte che NON lo implica; il mio ha una fonte che
    LO IMPLICA — cosi' il moat PASSA davvero e resta solo il layer lessicale

La domanda: il campo `moat` della ricevuta MCP dice ancora «does NOT entail»
quando a trattenere e' stato un altro strato?

Fuori pytest, store temporaneo, zero rete.

    python docs/stato-reale/banchi/ws7-la-copertura-del-presidio-con-un-caso-mio.py
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_copertura_")

#: un'AUTO-AFFERMAZIONE con una fonte che la sostiene alla lettera: il moat
#: non ha nulla da obiettare, e se il fatto viene trattenuto e' per un altro
#: motivo — che e' esattamente lo stato che il campo deve saper nominare.
FONTE = ("Esecuzione del 31/08 alle 08:45: la suite del modulo di cassa "
         "riporta 12 test superati e 0 falliti, exit code 0.")
CLAIM = "Ho verificato che il modulo di cassa funziona: 12 test superati su 12."


def main() -> int:
    from verimem import mcp_server as srv

    #: ⚠️ `proposition`, NON `content` (`mcp_server.py:12986`). Al primo giro
    #: avevo inventato il nome e la porta ha risposto `rejected_empty`: la
    #: chiamata non e' mai arrivata al gate.
    args = {"proposition": CLAIM, "source": FONTE, "topic": "banco/copertura"}
    res = asyncio.run(srv.call_tool("hippo_remember", args))
    testo = res[0].text if res and hasattr(res[0], "text") else str(res)
    try:
        d = json.loads(testo)
    except Exception:  # noqa: BLE001
        d = {"_grezzo": testo[:400]}

    moat = str(d.get("moat", "(campo assente)"))
    print(f"  claim   : {CLAIM}")
    print(f"  status  : {d.get('status')}")
    print(f"  layers  : {d.get('layers') or d.get('quarantined_by') or '—'}")
    print(f"  moat    : {moat[:150]}")
    print()

    #: 🔴 TRE STATI, non due. Al primo giro leggevo `status != "quarantined"`
    #: come «ammesso» — e `status` era **None**, perche' la chiamata era stata
    #: RIFIUTATA (`rejected_empty`) e non era mai arrivata al gate.
    #: ⇒ **Ho letto l'ASSENZA di un valore come un valore**, che e' la stessa
    #:   forma che documento da stanotte. Un banco deve distinguere
    #:   «ammesso» da «non ho scritto niente», o dichiara un verde su nulla.
    stato = d.get("status")
    if stato is None:
        print("  🔴 LA CHIAMATA NON E' ARRIVATA AL GATE (`status` assente).")
        print(f"     Risposta grezza: {str(d)[:200]}")
        print("     NON e' un esito del presidio: e' un banco rotto.")
        return 1
    trattenuto = str(stato) == "quarantined"
    accusa_la_fonte = "does NOT entail" in moat
    if not trattenuto:
        print(f"  ⚪ NON ESERCITATO: il fatto e' stato AMMESSO (status={stato!r}),")
        print("     quindi questo caso non raggiunge lo stato che il presidio")
        print("     deve nominare. Non e' un verde: e' un caso che non morde.")
        return 0
    if accusa_la_fonte:
        print("  🔴 IL PRESIDIO NON COPRE QUESTO CASO: trattenuto da un altro")
        print("     strato, e il campo accusa comunque la FONTE.")
        return 1
    print("  🟢 COPERTO: trattenuto da un altro strato e il campo NON accusa")
    print("     la fonte. Il presidio vede anche un caso che il suo test non ha.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
