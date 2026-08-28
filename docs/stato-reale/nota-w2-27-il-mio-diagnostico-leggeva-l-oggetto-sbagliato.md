# W2-27 — l'asimmetria **c'è**, e il mio diagnostico precedente leggeva l'oggetto sbagliato

*ws3 (Galileo), 29/08 00:20. Corregge la nota di `6bfe9fae`.*

## Il diagnostico che avevo pubblicato, e perché era sbagliato

Nel banco `6bfe9fae` avevo stampato

    repo_root visto dall'SDK ... None
    repo_root visto da MCP ..... None

e concluso che **le due porte non erano in regimi diversi**.

**Quel diagnostico era sbagliato.** Leggevo `.semantic` su `mcp_server._ag`,
che **non è l'agente ma una FUNZIONE**:

    type(mcp_server._ag)  ->  builtins.function

⇒ `getattr(_ag, "semantic", None)` è `None` **perché le funzioni non hanno
quell'attributo**, non perché `repo_root` sia assente.

> 🪞 **La stampa che avevo elogiato per avermi salvato dal pubblicare un falso
> «nessuna divergenza» misurava a sua volta l'oggetto sbagliato.** Mi ha salvato
> dal primo errore e ne conteneva un secondo.
> 🔑 **La tecnica «stampa le clausole della condizione» aiuta solo se stampi
> l'OGGETTO GIUSTO: va accompagnata dal TIPO di ciò che leggi, non solo dal
> valore.** Una riga in più — `type(x)` — e il difetto si vedeva subito.

## Il dato corretto

Chiamando l'**accessore** invece di leggerlo come attributo:

    _ag()  ->  verimem.agent.VerimemAgent
      .semantic            : verimem.semantic.SemanticMemory
      .semantic.repo_root  : C:\Users\aurel\Code\HippoAgent
    Memory() di default    : None
    CONFIG.project_root    : C:\Users\aurel\Code\HippoAgent

⇒ **L'asimmetria di W2-27 è REALE**: l'agente che serve la porta **MCP**
costruisce lo store **con** `repo_root` (`agent.py:72`,
`SemanticMemory(repo_root=_CONFIG.project_root)`), mentre un `Memory()` di
default ha `repo_root = None`. La porta MCP **inoltra** quel valore al gate
(`mcp_server.py:9112`), l'SDK **no**.

## E perché le celle non divergevano lo stesso

La condizione (`anti_confab_gate.py:1960`) è

    if (repo_root is not None and not warnings and verified_by is not None …

Richiede **`not warnings`** — cioè che la prova abbia **ripulito** il claim. Il
mio claim (`«Il fix funziona ed è verificato.»`) fa scattare **`L1.10` e
`L1.15` anche CON** la prova fabbricata ⇒ quella clausola è **falsa**, e la cura
non poteva entrare **comunque**. **Non era il regime: era ancora la forma del
claim.**

## Cosa resta

Serve un claim in cui la prova fabbricata **sopprima `L1` completamente**,
lasciando **zero** warning — nel caso di @ws2 restava solo `L1.19`, che è il
warning **della cura stessa**. Da cercare fra i detector quantitativi
(`l1_quantitative_detector`), **non da indovinare**: è la terza volta su questo
fronte che indovinare la forma del claim mi costa un giro.

## Limiti

⚠️ Nessuna scrittura sullo store di Aurelio; store temporaneo per l'SDK.
⚠️ L'agente MCP è quello **vero** e porta il `repo_root` del repo corrente: su
una macchina con un altro `project_root` il valore cambia.
⚠️ **Non ho ancora misurato una divergenza di verdetto**: ho misurato che le due
porte stanno in **due regimi diversi**, che è la premessa — non la conclusione.
