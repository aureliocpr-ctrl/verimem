# Mappa di `verimem/mcp_server.py` — ws2 «Varco» (Giano), 08/09

**Stato: 10 funzioni su 66.** Contatore vero, non stima: sotto c'è come l'ho ottenuto.

## Il denominatore, e perché me lo sono fatto dare due volte

`66` è il numero del mandato e l'ho verificato prima di usarlo, perché un
contatore con un denominatore sbagliato è peggio di nessun contatore.

- Con `ast.walk` su tutto l'albero: **66**.
- Con un mio visitatore che scendeva solo dentro funzioni e classi: **58**.
  Saltava le funzioni annidate che vivono dentro `if`/`try` di modulo.

I due non concordavano e ho confrontato invece di pubblicare il primo che avevo
in mano — l'errore che ho fatto due volte oggi (un parser che saltava righe in
silenzio; un `iterdir` non ricorsivo che ha dato 3513 KB dove `du` diceva 8,3 GB).

Composizione delle 66, che serve a leggere la mappa:

| dove vivono | quante |
|---|---|
| a livello di modulo | 55 |
| dentro `_call_tool_impl` (l'handler dei tool) | 8 |
| dentro la classe `_TokenBucket` | 2 |
| dentro `_apply_tool_namespace` | 1 |

⚠️ **`grep -c "def "` qui non è il numero**: conterebbe anche i `def` nelle
stringhe e nei commenti, e in questo file ce ne sono. Il mandato dice «niente
grep-conteggi» e questa è la ragione, misurata.

## Come leggere le righe

`promessa` è quello che la funzione dichiara di fare (docstring o nome).
`chiamata da` è chi la usa DAVVERO. `test` è il file che la esercita.
`claim README` dice se sta dietro una promessa pubblica. `verdetto` è mio.
`prova` è il comando che ho eseguito — se manca, la riga dice NON VERIFICATO.

---

## Parte 1 — le funzioni dietro un claim del README

Sono la strada dei tool `hippo_remember` / `hippo_facts_recall` /
`hippo_facts_search` / `hippo_recall_as_of`, cioè ciò che un agente tocca.

### `_ag` — riga 94
- **promessa**: «Process-wide agent, built exactly once, SENZA tenere il lock».
- **chiamata da**: quasi ogni handler di tool (`a = _ag()`).
- **claim README**: sì, indiretto — ogni promessa sui tool passa di qui.
- **verdetto**: ✅ fa quello che dice, ed è la superficie unica dell'agente.
- **prova**: `tests/test_il_build_dell_agent_non_tiene_il_lock.py` — 4 passed
  (misurato il 07/09, fatto `t1b-red-green-del-lock`).

### `_ok` — riga 270
- **promessa**: (nessuna docstring) impacchetta una risposta riuscita.
- **chiamata da**: tutti gli handler, alla fine del ramo felice.
- **claim README**: sì — è la forma di OGNI ricevuta che un agente legge.
- **verdetto**: 🟡 **senza docstring**, ed è la funzione che decide come appare
  ogni risposta del prodotto. Non è un difetto di comportamento: è che il punto
  più letto del file non dice cosa promette.
- **prova**: esercitata da ogni cella MCP; nessun test la nomina direttamente.

### `_conta_sostituiti` — riga 274
- **promessa**: «Quanti fatti sono stati RIMPIAZZATI da una scrittura successiva».
- **chiamata da**: il ramo di lettura, per l'avviso dei ritirati.
- **claim README**: sì — la supersessione è una promessa pubblica.
- **verdetto**: ✅.
- **prova**: `tests/test_ogni_superficie_di_lettura_dichiara_i_sostituiti.py`
  (dentro i 78 passed del 07/09).

### `_pavimento_di` — riga 296
- **promessa**: «Il pavimento calibrato, da QUALUNQUE forma di oggetto la
  lettura abbia reso».
- **chiamata da**: gli avvisi di lettura sulle porte MCP.
- **claim README**: sì — «abstention over hallucination» si regge sul pavimento.
- **verdetto**: ✅, ed è una superficie unica nata da una divergenza fra porte
  (il commento sopra la funzione la chiama «terza generazione della stessa cura»).
- **prova**: `tests/test_avviso_mcp_stessa_soglia_dell_sdk.py`,
  `tests/test_tre_porte_una_risposta_sul_pavimento.py`.

### `_avvisi_di_lettura` — riga 334
- **promessa**: «Gli avvisi che CLI e SDK danno già, portati alla porta [MCP]».
- **chiamata da**: gli handler di lettura.
- **claim README**: sì.
- **verdetto**: ✅ per gli avvisi che copre. ⚠️ **ma è il punto dove un avviso
  nuovo va aggiunto a mano**: è la giuntura che ha prodotto due cure di seguito
  (pavimento, ranking degradato — «⚠️ QUARTA GENERAZIONE DELLA STESSA CURA»).
- **prova**: `tests/test_l_avviso_non_usciva_dalla_porta_dell_agente.py`.

### `_err` — riga 532
- **promessa**: (nessuna docstring) la forma di un errore.
- **chiamata da**: ogni ramo di rifiuto.
- **claim README**: sì — un errore è la risposta che l'agente riceve quando
  qualcosa non va, e il prodotto promette di dire *perché*.
- **verdetto**: 🟡 senza docstring, come `_ok`.
- **prova**: NON VERIFICATO come funzione a sé.

### `_err_proposizione_vuota` — riga 546
- **promessa**: (dal nome) il rifiuto di una scrittura senza testo.
- **chiamata da**: `hippo_remember`.
- **claim README**: sì — è il primo errore che un agente incontra sbagliando.
- **verdetto**: ✅ nome che dice tutto.
- **prova**: NON VERIFICATO.

### `_auth_closed` — riga 207
- **promessa**: «Fail-closed receipt when the configured server rejected [the key]».
- **chiamata da**: il thin client, quando il server condiviso rifiuta la chiave.
- **claim README**: sì — il fail-closed è una promessa esplicita («refusing to
  fall back to a local store»).
- **verdetto**: ✅ e il nome dichiara la direzione del fallimento, che è la cosa
  che conta in un fail-closed.
- **prova**: NON VERIFICATO in questa sessione.

### `_remote_row` — riga 216
- **promessa**: «Shape a shared-server search hit like a local recall/search hit».
- **chiamata da**: il ramo delegato.
- **claim README**: sì — «N sessioni condividono il server» promette che la
  risposta sia la stessa.
- **verdetto**: ⚠️ **è una traduzione fra due forme**, cioè esattamente il punto
  dove una porta può dire una cosa diversa dall'altra senza che nessuno lo veda.
  Merita una cella sua: non l'ho trovata.
- **prova**: NON VERIFICATO.

### `_remote` — riga 181
- **promessa**: (nessuna docstring) il thin client verso il server condiviso.
- **chiamata da**: gli handler quando `VERIMEM_SERVER_URL` è impostata.
- **claim README**: sì.
- **verdetto**: 🟡 senza docstring su una funzione che decide se la lettura
  esce dal processo.
- **prova**: `tests/test_remote_memory.py` la esercita (34 passed il 07/09).

---

## Cosa resta

56 funzioni su 66: le 8 dentro `_call_tool_impl` (`_props`, `_cos`,
`_encode_skill`, `_cosine`, `_default_coherence_hook`, `_key_fitness`,
`_key_recency`, `_key_activity` — nessuna con docstring), le 2 di
`_TokenBucket`, quella dentro `_apply_tool_namespace`, e le restanti 45 del
modulo.

### Un dato che emerge già da dieci righe

**Sei funzioni su dieci non hanno docstring**, e fra queste ci sono `_ok` e
`_err` — cioè le due che danno forma a *ogni* risposta e *ogni* errore che un
agente riceve. Non è un difetto di comportamento e non propongo di curarlo qui
(il mandato dice niente cure): è che il punto più letto del file non dichiara
cosa promette. Lo segnalo perché una mappa serve anche a questo.
