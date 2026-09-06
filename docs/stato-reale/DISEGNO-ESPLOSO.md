# Il disegno esploso — componenti, giunture, e chi le presidia

*lead-audit con Aldo (dati) e Tara (piattaforma), iniziato il 05/09/2026 alle 20:55. Livello 3
dell'agenzia (`AGENZIA.md`): «l'architettura: strati del gate, porte, store, daemon, giudice, e le
giunture dove i difetti nascono». Regola del documento: ogni numero viene da un comando eseguito il
giorno indicato; un presidio vale solo se è stato ESEGUITO alla porta del prodotto, altrimenti è
scritto «da eseguire». Contare i file di test che nominano una giuntura NON è un presidio.*

## 1. Le parti, con il peso misurato (05/09, `wc -l`, main `5d7152d8`)

| parte | modulo | righe | cosa fa |
|---|---|---|---|
| porta MCP | `verimem/mcp_server.py` | 15.494 | 249 strumenti `hippo_*`; usa 196 moduli (inventario 04/09) |
| porta CLI | `verimem/cli.py` | 5.712 | `verimem remember/recall/save/doctor/warmup…` |
| porta SDK | `verimem/client.py` | 4.206 | `Memory.add/recall`, ricevuta, `chi_ha_quarantinato` |
| gate | `verimem/anti_confab_gate.py` | 3.272 | strati L1 (lessicali), L3 (contraddizione/supersessione), L4 (moat), L4.1 (numeri); `advisory_eligible` |
| giudice | `verimem/local_grounding.py` + `grounding_gate.py` | 922 + 670 | CE locale `local_gate_ce_v2` (711 MB), warming in thread, `judge_state()` |
| daemon | `verimem/encode_service.py` | 973 | encode condiviso, pool 4 worker (p95 0,801 s, Tara 03/09) |
| store | `verimem/memory.py`, `semantic.py`, `documents.py` | — | fatti, episodi, documenti (SQLite `~/.engram/semantic/semantic.db`) |
| promozione | `verimem/document_promote.py` | 212 | documento → fatto, passa dal gate |
| avvio | `verimem/preload.py`, `self_heal.py` | 235 + 121 | `_DAEMON_WARM_WAIT_S = 25.0` |

Totale: **391 moduli** in `verimem/`, **1.574 file di test** (05/09, `ls | wc -l`).

## 2. Gli ingressi al gate non sono tre: sono SEI

`grep -l "run_validation_gate("` (05/09): `cli.py`, `client.py`, `mcp_server.py`,
`document_promote.py`, `sleep.py`, `transcript_promote.py` (più il gate stesso). Le «tre porte»
del contratto sono CLI, SDK, MCP; **promozione di documenti, sonno (consolidamento) e promozione di
trascrizioni entrano dal gate per conto loro**. Ogni cura «sulle tre porte» che non guarda gli altri
tre ingressi lascia una via aperta: la promozione ha già prodotto il commit `a499afc8` (ascolta
L4.1 come il gate, non conta gli avvisi `*-observe`), cioè il gate rifatto una seconda volta in un
chiamante. **Giuntura da presidiare: un solo gate, sei chiamanti, stessa risposta.** Presidio: da
eseguire (un test che scrive lo stesso claim dai sei ingressi e confronta le ricevute).

Le tre vie secondarie, lette il 05/09: passano tutte `source=… ground_write=True` e poi **decidono
l'azione da sole** leggendo `verdetto.grounding_score` — `document_promote.py:88-94` («quarantina
quando il moat boccia»), `transcript_promote.py:89-95` (stesso commento, stessa copia),
`sleep.py:512-518` (`_v.action == "reject" or (…soglia…)`: legge la soglia del verdetto e RIPETE il confronto, non ne inventa una — Aldo, 06/09 00:07, impronta identica 1/1/1 sui tre ingressi). Tre copie della
decisione (classe ①): il gate calcola, tre chiamanti rifanno. Cura proposta a Nadia: un solo punto
che decide (`action` e `quarantined_by` nel verdetto), sei chiamanti che eseguono.
Aldo, 05/09 23:33: **il presidio delle scritture (tre porte, una risposta) copre due ingressi su sei**, non
«due porte su tre» come pubblicato il 04/09; e un giro d'uso reale carica 57 moduli su 391: la
raggiungibilità statica sovrastima di sei volte ciò che il prodotto esercita davvero.

## 3. Le giunture dove i difetti sono NATI (settembre), e il presidio

| giuntura | il difetto che ci è nato | livello della misura | presidio |
|---|---|---|---|
| porta MCP ↔ giudice in warming | T1: la prima scrittura con fonte senza daemon torna dopo 313–903 s in silenzio; la CLI lo dice in 1,2 s (Corrado 04/09 21:59) | porta del prodotto, client vero | **da eseguire** dopo la cura A' di Tara (05/09): tempo, `judged`, `layers`, finestra dichiarata |
| ricevuta SDK ↔ chi legge | `Memory.add` non porta `judged`: si deduce da `grounding_score` (Galileo 04/09 22:07) | funzione pubblica | da eseguire alla porta: il campo che distingue «giudicato» da «mai giudicato» |
| promozione ↔ gate | `a499afc8`: la promozione contava gli avvisi `*-observe` e non scriveva `quarantined_by` (56/56 vuoti, Nadia 04/09) | funzione | ramo `promozione-a499`, ticket in corso; presidio da eseguire |
| `as_of` ↔ scope (agent_id, run_id) | pezzo 3: le porte pescano `k` e filtrano dopo, il tool dedicato pesca `k*6`; con `as_of` agent_id e run_id perdono TUTTO (Marie H3, 04/09) | porta | da eseguire: RED vero di Giano, finestra ② |
| scaduti ↔ `facts_recall` / `ask` FIND | il pezzo 2 dichiara la scadenza su SDK e CLI recall; `facts_recall` e `ask` restano muti; `facts_search` serve lo scaduto (Aldo 04/09) | porta | da eseguire: cura ③ con controllo positivo |
| README ↔ pacchetto pubblicato | un link relativo a `docs/` (mio, `75a768c6`): su PyPI dà 404; 6 job rossi | porta (la vetrina) | **ESEGUITO 05/09**: `test_il_readme_pubblicato_non_addita_il_nulla.py` 8 passed, `test_i_collegamenti_della_vetrina_reggono_fuori_dal_repository.py` 3 passed, RED 1 failed con la riga vecchia |
| publish ↔ artefatto provato | `publish.yml` ricostruisce il wheel: impronta diversa dall'artefatto smoke-testato, contenuto identico 465/465 (LANT-175) | porta | debito Corrado (design in corso 05/09) |
| daemon ↔ prima scrittura | senza daemon il giudice si scalda in un thread e un processo breve finisce prima: il fatto entra `L4-skipped` dichiarato | porta | eseguito da CLI (1,2 s, dichiarato); da MCP è T1 |
| cancelli ↔ sha corto | con sha corto l'API risponde vuoto senza errore; i cancelli leggevano l'albero di lavoro invece del commit | strumento | curato da Corrado (`2bb13bd7`), eseguito 04/09: 11/11 |
| percorso dello store ↔ chi lo apre | nove file alla radice dello store possono essere scambiati per la memoria, e il peggiore ha lo schema giusto con zero fatti: chi lo apre riceve una memoria valida e vuota, indistinguibile da una nuova (Aldo 06/09 01:53; la trappola «due DB, quello alla radice è vuoto» era già in memoria dal 24/07) | porta | da eseguire: la ricevuta dichiara il path effettivo e il conteggio dei fatti; aprire uno store vuoto dove ne esiste uno pieno accanto avvisa |
| risoluzione dello store ↔ le tre porte | T16 (Iris 06/09 02:00, P0): `Memory("memoria.db")` (la riga del Quickstart) scrive nella CWD, la CLI legge il data dir e risponde «no facts found» con exit 0: l'SDK usa il percorso, la CLI il data dir, e la risposta non dice dove ha guardato | porta (ambiente pulito, U-C) | da eseguire: una funzione sola risolve lo store per tutte le porte; la CLI dichiara path e totale, `--db`; il Quickstart insegna una riga che funziona su entrambe |
| ordinamento dello store ↔ filtro temporale alla porta | `search_facts` ordina per `created_at DESC` e non ha parametro temporale: con `as_of` la porta pesca i più nuovi, li scarta tutti e rende 0 anche se il fatto giusto è in archivio; cresce col corpus (Giano 05/09 21:16, confermato da Marie 21:21) | porta, `k=1`, 6 nati dopo + 1 ritirato | da eseguire: cura (A) nello store (Aldo), RED = il test di Giano già rosso, finestra ②+③ |

## 4. Le cinque classi, riviste su queste giunture

① una copia invece della superficie unica (promozione che rifà il gate; il tool dedicato che pesca
diversamente dalle porte) · ② manca lo sweep (la scadenza dichiarata su due porte su cinque) ·
④ il bug è la giuntura (MCP↔giudice, README↔pacchetto, publish↔artefatto) · ⑤ un marcatore non marca
chi non lo conosce (`*-observe` letto come decisore dalla promozione). La classe ③ (liste
monolingue) non compare in questa tabella: non perché sia chiusa, ma perché nessun difetto di
settembre è nato lì. Da misurare, non da dichiarare.

## 5. Cosa manca a questo documento (debiti dichiarati)

- La mappa delle importazioni, misurata da Aldo il 05/09 (AST, non regex; il righello a regex aveva
  dato 17 e poi 0 prima del 2): dei 391 moduli, **60 non sono raggiungibili dalle porte**: 6 sono entry
  point (`__main__`), 52 li importano solo test o script, **2 non li importa nessuno**
  (`orchestration` 58 righe, `syscall_bridge` 383 righe: 441 righe in tutto). Il «~40 mai importati»
  del 04/09 era il perimetro sbagliato (solo dentro `verimem/`).
- Per ogni riga «da eseguire»: il test alla porta, con il livello scritto nel nome.
- Lo store: FATTO da Aldo il 05/09, `86-il-disegno-esploso-lo-store-tabelle-campi-e-chi-li-scrive.md` (21 tabelle di cui 5 vuote per costruzione; 31 colonne in `facts` di cui 6 sotto l'1%; `status` e chi ferma i fatti; chi scrive i campi chiave, in ordine; il difetto del misuratore dichiarato).
- Il daemon e il giudice sotto carico (otto client): Tara, `ws5-daemon-del-giudice-disegno-per-la-0.8.0.md`.
