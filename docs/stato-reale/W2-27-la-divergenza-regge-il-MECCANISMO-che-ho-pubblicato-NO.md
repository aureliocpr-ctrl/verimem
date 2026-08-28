# W2-27 — la divergenza regge, il **meccanismo** che ho pubblicato **no**

*ws3 (Galileo), 29/08 00:44. **Corregge il commit `621d9ab3`**, pubblicato 15 minuti prima.*

## Cosa avevo pubblicato

Che le due porte divergono (**vero, e regge**) **e** che la ragione fosse
`EVIDENCE-EXISTENCE`: «*MCP porta `repo_root` e ferma il riferimento fabbricato;
l'SDK è format-only*». **La seconda metà è falsa, e non l'avevo misurata.**

## Le due misure che l'hanno fatta cadere

**① A/B nella stessa esecuzione** — l'SDK **accetta** `repo_root`
(`client.py:400`, parametro di `Memory()`): se il meccanismo fosse
`EVIDENCE-EXISTENCE`, passarglielo dovrebbe riprodurre lo stop di MCP.

    SENZA repo_root (default)  -> model_claim   strati=-   evidence_existence=False
    CON   repo_root            -> model_claim   strati=-   evidence_existence=False

**Non cambia niente.** La cura che avevo indicato non produce l'effetto che le
avevo attribuito.

**② La ricevuta MCP, letta chiave per chiave** — e qui il difetto è **mio**:

    quarantined_by        L1
    anti_confab_warnings  [{"layer": "L1.19", "reason": "... lacks measurement evidence"}]

La ricevuta MCP espone **`anti_confab_warnings`**; il mio lettore leggeva
**`warnings`**. Il «`MCP ferma -`» — *zero strati* — su cui avevo costruito il
racconto era **una chiave sbagliata**, non un dato.

> 🪞 **Seconda volta stanotte che leggo la chiave sbagliata di una ricevuta**
> (la prima: `receipt["layers"]`, che non esiste). Il presidio che avevo estratto
> allora — *stampa le CHIAVI prima di contare* — **non l'ho applicato al mio
> stesso banco.** 🔑 Un presidio nato in un turno non protegge il turno dopo se
> resta un ricordo invece di diventare un **controllo dentro il banco**.

## Il meccanismo vero

`anti_confab_gate.py:1937`:

    _l1_ha_giurisdizione = (not provenance_trusted or _gr_l1x_applies(...))

`client.py:539` passa **`provenance_trusted=True`**; MCP **no** — e il commento
a `anti_confab_gate.py:1928` lo **prescrive**: «*i gestori MCP/gateway non devono
inoltrarlo MAI*». ⇒ Sull'SDK `L1` ha **giurisdizione ridotta perché il chiamante
è dichiarato fidato**; su MCP `L1.19` fira e ferma. **La prova fabbricata non
c'entra: su MCP non sopprime niente.**

## Cosa resta in piedi, e cosa no

**REGGE** — misurato due volte, ora anche dalla chiave giusta: lo **stesso
claim** con le **stesse prove** è **ammesso dall'SDK** e **quarantinato da MCP**
(`quarantined_by: L1`). **W2-27 cambia il verdetto.**

**CADE** — «l'SDK è format-only», «MCP è protetto da `EVIDENCE-EXISTENCE`», e
l'intera lettura da *difetto*: è un **modello di fiducia deliberato**, non una
dimenticanza. Se quella fiducia sia meritata è una **domanda di design per
Aurelio**, non un difetto che io possa dichiarare.

**NON MISURATO** — quanti fatti reali siano entrati per questa via. Il censimento
sul corpus è servito solo a dire che **532 fatti su 15245 (3,49%)** hanno un
`verified_by` popolato: la mia prima conta ne diceva **15245**, perché `'[]'` è
una stringa **non vuota**. Terzo misuratore difettoso della stessa nottata.

Agent: Galileo
