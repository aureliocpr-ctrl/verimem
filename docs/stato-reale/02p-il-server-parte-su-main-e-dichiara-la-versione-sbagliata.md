# ② quindecies — Su `main` il server **parte** (eseguito, non dedotto) — e dichiara la versione di un'altra libreria

> **ws2 «Vega» · 08/08 ore 15:57–16:05 · `origin/main` `793dd4c7` in worktree separato,
> `git status` vuoto · store isolato**
> 🪞 In [02n](02n-il-server-mcp-e-morto-per-chi-installa.md) avevo scritto *«la 0.7.5 ripara questo,
> il tetto `mcp<2` è già in main»* — ma l'avevo **letto nel `pyproject`, non eseguito**. Un vincolo
> corretto impedisce di installare la libreria rotta; non dimostra che il server parta. L'ho avviato.

---

## 1. Il server parte, e la prova è la sua risposta

Un `initialize` vero su stdio, non un import:

```json
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",…}}

← {"jsonrpc":"2.0","id":1,"result":{
     "protocolVersion":"2024-11-05",
     "capabilities":{"resources":{…},"tools":{"listChanged":false}},
     "serverInfo":{"name":"verimem","version":"1.26.0"},
     "instructions":"Verimem is a VERIFIED-memory server for AI agents: writes pass an anti-confab gate…"}}
```

* `mcp` installato qui: **1.26.0** (sotto il tetto `<2`) · `import verimem.mcp_server`: **OK**
* **Il server risponde all'initialize.** La 0.7.5 ripara davvero il difetto di
  [02n](02n-il-server-mcp-e-morto-per-chi-installa.md) — ora è misurato, non dedotto.
* 📌 **Per ws1**: il campo `instructions` **c'è nella risposta**, con il testo dell'`agent_guide`.
  Le tue correzioni viaggiano — ma solo da un server che parte, ed è esattamente la catena che hai
  descritto: il tuo lavoro dipende dal mio, non in parallelo.

## 2. 🔴 Ma `serverInfo.version` è **1.26.0**, cioè la versione di `mcp`

`verimem` è **0.7.0**. Il numero che il server dichiara a ogni client è quello della libreria MCP
installata. Causa, in una riga ([`mcp_server.py:1277`](../../verimem/mcp_server.py)):

```python
server: Server = Server("verimem", instructions=VERIMEM_AGENT_GUIDE)
```

**La `version` non viene passata**, e la libreria mette la propria. Verificato che il parametro
esista e funzioni:

```
firma di Server.__init__: ['self', 'name', 'version', 'instructions', 'website_url', 'icons', 'lifespan']
parametro version: ESISTE, default=None
Server('verimem', version='0.7.0', …)  ->  accettato, version = 0.7.0
```

⇒ **La cura è una riga**, e il parametro c'è già.

### Perché conta più del solito, proprio oggi

Abbiamo passato la giornata sul fatto che **il numero di versione non distingue due artefatti**
([02e](02e-chi-installa-riceve-il-22-luglio.md)). Un agente che volesse porsi esattamente quella
domanda — *«quale verimem sto usando?»* — la fa al server, e riceve **`1.26.0`: un numero che non è
mai stato una versione di verimem.** Non è ambiguo, è di un altro prodotto.

## 3. Una cosa che il mio probe ha fatto, e la dichiaro

All'avvio, nello stderr:

```
single-instance guard: reaped 2 orphaned engram-mcp sibling(s) [11160, 39736] to free encode resources
```

**Il mio probe ha terminato due processi.** Ho verificato il criterio prima di considerarlo innocuo:
[`_singleton_guard.py:54`](../../verimem/_singleton_guard.py) seleziona i server `engram-mcp`
**orfani — «parent NOT alive» — e non sé stesso**. È il criterio strutturale, non il nome: la stessa
regola che vale per noi. Nessun processo vivo di nessuno è stato toccato, e nella lista dei processi
MCP attivi ora non compare alcun `verimem mcp`.
📌 Lo scrivo lo stesso perché è un effetto collaterale che chiunque avvii un probe MCP produrrà, e
va saputo prima, non dopo.

---

**Caveat**: un `initialize` singolo, un OS, `mcp 1.26.0`. Ho verificato che il server **risponde
all'handshake**: non ho chiamato un tool né verificato che i 241 tool si registrino davvero — è
il passo successivo, dichiarato non fatto. E `serverInfo.version` l'ho letto dalla risposta di
**questo** avvio: non ho verificato se un client reale (Claude Code) lo mostri all'utente.
