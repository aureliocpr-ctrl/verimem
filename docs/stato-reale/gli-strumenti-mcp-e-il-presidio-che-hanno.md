# I 249 strumenti MCP e il presidio che hanno — 2026-09-12

Censimento di lettura: quali strumenti esposti dal server MCP hanno un test che
li **invoca**, e quali no. Righello: `scripts/presidio_strumenti.py` (AST sul
sorgente e sui test, nessuna esecuzione del prodotto).

    python scripts/presidio_strumenti.py --tsv /tmp/presidio.tsv

## I numeri

    strumenti dichiarati              249   (248 hippo_ + sandbox_exec)
    INVOCATI da almeno un test        109
      di cui SOLO dentro una spazzata  14   (test_mcp_server.py, 27 strumenti)
      invocati da un file MIRATO       95
    MAI invocati                      140

    ⇒ SENZA UN TEST MIRATO           154 su 249

Tutte e 249 le dichiarazioni `Tool(name=…)` stanno dentro
`_list_tools_unfiltered`, nessuna altrove, e **nessuna dentro un `if` o un
`try`**: la lista è incondizionata nel sorgente.

### Le famiglie scoperte — dove conviene cominciare

    hippo_skill      20/35      hippo_dream        7/7   ← famiglia INTERA
    hippo_skills     14/16      hippo_corpus       4/4   ← famiglia INTERA
    hippo_facts       9/17      hippo_trajectory   4/4   ← famiglia INTERA
    hippo_episode     7/11      hippo_briefing     3/3   ← famiglia INTERA
                                hippo_outcome      3/3   ← famiglia INTERA

Cinque famiglie non hanno **nessun** test che le invochi. Le skill da sole
fanno 34 scoperti su 51.

## Il numero che questo documento non riporta era 42

La prima versione del righello cercava le invocazioni con **cinque regex**, una
per ogni forma nota a chi l'ha scritto, e dava «42 invocati, 207 solo
nominati». A smascherarla è stata una riga non credibile della lista —
`hippo_audit_tail`, 11 occorrenze nei test, «mai invocato»:

    tests/test_mcp_export_import_test_audit.py:297
        blocks = await _invoke_tool("hippo_audit_tail", {"n": 3})

`_invoke_tool` era la sesta forma, e i dati dicono che è la più usata del repo:
286 chiamate contro le 6 di `_call_tool_impl`, che era la prima delle cinque
regex. **Il numero era falso al ribasso di 67.**

⚠️ **Il controllo positivo era passato lo stesso, 3 su 3.** I tre strumenti
scelti erano quelli dei banchi di chi scriveva il righello, e quei banchi usano
le forme che lui aveva scritto. *Un controllo positivo pescato dal proprio
lavoro non controlla niente*: conferma che il righello vede ciò che già sapevi.

Le tre regole che ne sono uscite, scritte nel file:

1. **Non si cercano le forme note, si cercano i nomi.** Qualunque chiamata che
   riceve un nome-di-tool come stringa; i wrapper escono *dai dati* e il
   programma li stampa, così il righello non può mancare una forma nuova.
2. **Il controllo positivo contiene il caso che ha rotto la versione prima**,
   non casi scelti dal proprio lavoro.
3. **E un controllo negativo**: un nome inventato non deve mai risultare
   invocato. Senza, «più largo» è indistinguibile da «più giusto» — il difetto
   che il controllo positivo da solo non vede mai, perché passa *meglio* quanto
   più il criterio è largo.

Il conteggio regge sotto due regole indipendenti: quella larga (qualunque
chiamata) e quella stretta (solo i wrapper che eseguono davvero). Stesso 109, e
zero strumenti raggiunti solo da forme che *ispezionano* (`_StubTool`,
`_schema_di`) invece di invocare.

## Un limite dichiarato: «invocato» non è «presidiato»

Un test che invoca uno strumento può limitarsi a controllare che non esploda.
La colonna `SOLO SPAZZATA` misura la forma strutturale del problema — un file
che tocca 27 strumenti diversi non li presidia — ma non dice niente sulla
qualità degli assert dei 95 mirati. **Quel giudizio non è in questo documento**
e va dato strumento per strumento, provandoli dal pacchetto.

## Quello che il censimento ha fatto trovare

La deny-list delle mutazioni (`_THIN_UNSUPPORTED_WRITES`, 15 nomi;
`_THIN_UNSUPPORTED_READS`, 14) copre i **fatti**; gli episodi sono esclusi per
disegno, e il README lo dichiara. Tutti e 29 i nomi esistono fra i 249: nessuna
voce morta.

Ma la lista è nata da una spazzata **a mano** — lo dice il suo stesso commento
(`mcp_server.py:257`) — e non si ripete: il nome della costante compare cinque
volte in tutto il repo, quattro in `mcp_server.py` e una in un banco *dentro
una stringa di messaggio*. **Nessun test la importa**, quindi uno strumento che
muta i fatti aggiunto domani entra senza guardia e senza rosso. Che la spazzata
a mano possa mancare un bersaglio è già misurato: `hippo_quarantine_restore`
era fuori.

Derivare la lista dal codice **non funziona**, e il perché è misurato: tre
criteri provati, l'ultimo con l'ancora sulla scrittura SQL, e il controllo
negativo lo boccia (1 lettura certa su 6 non marcata). La causa è che la
risoluzione per nome fonde funzioni diverse — nel pacchetto ci sono 13 `get`,
13 `_connect`, 5 `store` (4 con SQL di scrittura), 4 `delete`, 2 `resolve`;
**158 nomi su 2548 sono definiti più di una volta**. Per distinguerli servirebbe
il tipo del ricevitore.

⇒ La cura non è derivare, è **dichiarare**: nessuna delle 249 dichiarazioni
`Tool(...)` usa `annotations` — hanno `name`, `description`, `inputSchema` e
basta — mentre il protocollo MCP prevede già `readOnlyHint` e
`destructiveHint`. Con l'annotazione la deny-list diventa derivabile
meccanicamente, lo sweep è un confronto fra due cose che stanno entrambe nel
prodotto, e anche il client sa distinguere una lettura da una cancellazione
senza leggere la prosa della descrizione.
