# I 287 documenti di `docs/`, classificati

> ws8 (Corrado), 08/09/2026. **Questo file cresce**: ogni riga della tabella è un
> verdetto **letto**, non dedotto. Le righe che mancano non sono documenti sani:
> sono documenti **non ancora guardati**, e il contatore in fondo dice quanti.

## Il metodo, e perché non è automatico

Uno script raccoglie gli **indizi** (`classifica_documenti.py`): chi cita il
documento, quali dei path che nomina non esistono più, quando è stato toccato.
Il **verdetto no**: lo do leggendo.

🪞 **Il primo documento che ho letto mi ha dato ragione di non fidarmi dello
script.** `GRAVITA-DIFETTI.md` nomina `tests/test_due_fonti_dichiarate_non_si_ritirano.py`,
che non esiste: indizio di «contraddice». Letto il contesto, il documento dice
**«287 righe, 11 test, rimosso dal revert»** e racconta di averlo recuperato da
`05c26887^` per rieseguirlo. **Non contraddice il codice: lo racconta, ed è pure
preciso.** Classificarlo dall'indizio sarebbe stata una diffamazione.
⇒ Da lì un secondo strumento (`triage_path_rotti.py`) separa chi **afferma** da
chi **racconta** guardando le due righe attorno alla menzione. Non decide:
ordina la coda.

## I verdetti dati finora

| documento | verdetto | la prova |
|---|---|---|
| `docs/stato-reale/GRAVITA-DIFETTI.md` | **VIVO** | nomina un test inesistente ma dichiara «rimosso dal revert» e spiega di averlo recuperato da `05c26887^`: racconta, non afferma |
| `docs/recipes/corpus-bonifica.md` | **CONTRADDICE IL CODICE** | è una ricetta: alla riga 21 dice `python scripts/engram_bonifica.py`, e quel file non esiste. Chi la segue ottiene un errore |
| `docs/EPISTEMIC_FAILURES_STUDY.md` | 🔻 **corretto: VIVO, con un rimando rotto** | `verimem/grounding_gate.py:1` — la **prima riga** del modulo — dice «Grounding gate (**see docs/EPISTEMIC_FAILURES_STUDY.md**)»: è il documento di riferimento del gate. Il `benchmark/semantic_conflict.py` che non esiste sta alla riga 87, **dentro una bibliografia**, non nella tesi. E il documento dichiara i propri limiti («Honest caveat», riga 654) |
| `docs/CYCLE134-DESIGN.md` | **MORTO** | riga 65 specifica `tests/test_dashboard_sse_e2e.py` come test da scrivere: il test non è mai stato scritto, il design non è stato realizzato |
| `docs/bench/cycle-71-sampling-stub.md` | **MORTO** | verbale datato 15/05: dichiara «Run: `python scripts/bench_c71_sampling_consolidate.py`», comando sparito. Non inganna — porta la data — ma non si può rieseguire |
| `docs/cycle156_unique_index_cross_process_design.md` | **MORTO** | riga 136: «Step 1 — write failing tests first (~30 righe `tests/test_consolidation_cross_process.py`)»: piano mai realizzato |
| `docs/ricerca/2026-09-02-roadmap-estratto-grezzo.md` | **VIVO** | la tabella elenca `tests/test_llm_providers.py` in colonna «new»: sono test **da creare**, non dichiarati esistenti |
| `docs/archive/2026-05-13_QA_AUDIT.md` | **MORTO** | piano di QA del 13/05 archiviato: la tabella elenca test da scrivere con la copertura «da → a». Mai scritti |
| `docs/archive/2026-05-13_BENCH_VALIDATION.md` | **MORTO** | riga 221: «**Aggiungere** uno script `scripts/bench_active_memory.py`» — proposta archiviata. Cita anche una chiave API esterna e un costo in dollari: superato |
| `docs/stato-reale/i-28-rossi-classificati.md` | **VIVO** | cita `benchmark/lme_retrieval_bench.py` **dentro** la citazione di un marcatore che dice «non esiste nel repo»: racconta l'assenza |
| `docs/SECURITY_AUDIT_2026-07-11.md` | **VIVO**, ma il rimando che lo cita è rotto | `CHANGELOG.md:2344` dice «full report in `SECURITY_AUDIT.md`»: il file esiste col nome `SECURITY_AUDIT_2026-07-11.md`. Chi cerca il nome citato non lo trova |
| `docs/sota/multi-signal-fusion.md` | **VIVO** | citato dal CHANGELOG col percorso giusto (riga 1791) |
| `docs/sota/temporal-evolution-narrative.md` | **VIVO** | citato dal CHANGELOG col percorso giusto |
| `docs/archive/2026-05-13_FORGIA.md` | **VIVO come archivio** | il CHANGELOG lo cita come `FORGIA.md` in voci di versioni passate (righe 1975, 2027): è stato spostato in `archive/` col prefisso della data |
| `docs/archive/2026-05-13_RND_MEMORIE.md` | **VIVO come archivio** | stessa forma: spostato e rinominato, citato dal nome vecchio in voci storiche |
| `docs/stato-reale/README.md` | **VIVO** — ed è già una mappa | indice del corpus (08/08), con una **nota datata dichiarata** in cima: «il numero qui sotto è invecchiato… 375 commit → 994», e la conclusione che *si rafforza* invece di cadere. Dichiara l'età invece di nasconderla |
| `docs/stato-reale/ticket-sigsegv-hang-watchdog.md` | **VIVO** | dichiara la finestra della misura («2026-09-03 17:39 → 2026-09-04 19:54, ultimi 60 run») e conosce il seguito: alla riga 139 registra il `--deselect` entrato in `ci.yml`, che è alla riga 901 del workflow |
| `docs/stato-reale/03-cose-spente.md` | **VIVO** | dichiara in testa `SHA: 544d27bd`, i comandi per rifare le misure, il verdetto e **la copertura** («64 interruttori su 151, 42%»), e scrive «dove non ho eseguito c'è **NON VERIFICATO**». È il modello di come si scrive una misura |
| `docs/stato-reale/23-quanto-spesso-L4-1-ha-ragione.md` | **VIVO** | riga 3: «ws6 · **30/08 ore 16:20** · store in `mode=ro`, sole SELECT». Chiude un limite che il documento 22 aveva **dichiarato** invece di nascondere |
| `docs/stato-reale/39-le-finestre-cieche-della-memoria.md` | **VIVO** | «ws6/Aldo — **30/08, sera**. Perimetro: archivio, memoria, corpus, quarantena»: dichiara data e perimetro |
| `docs/JUSTIFIED_MEMORY.md` | **VIVO** | è la tesi del progetto («the 2027 thesis»), e il codice la cita come riferimento del design: `verimem/justified_memory.py:7` → «See docs/JUSTIFIED_MEMORY.md for the design + the verified SOTA gap». Documento e modulo si rimandano |
| `docs/CYCLE109_HANDOFF.md` | **MORTO (a scadenza)** | handoff del 16/05 per far ripartire una sessione, con `Branch: cycle109-provenance-fact-schema-v3` — e quel ramo **non esiste più** (`git branch -a --list '*cycle109*'` → vuoto). Ha esaurito il suo scopo il giorno dopo |
| `docs/CONVERSATIONAL_ENTITY_DESIGN.md` | **VIVO** | `verimem/conversation_ingest.py:48` lo cita come il disegno che implementa |
| `docs/DECISION_CHAIN_DESIGN.md` | **VIVO** | `verimem/decision_chain.py:20`: «Design doc: docs/DECISION_CHAIN_DESIGN.md» |
| `docs/TRUST_MAINTENANCE.md` | **VIVO** | citato da `verimem/client.py:1275` dentro il ragionamento sul prezzo di una cronologia sempre accesa |
| `docs/F1_VIRGIN_CORPUS_FINDINGS.md` | **VIVO** | `verimem/gate_router.py:4` ne porta il risultato (validazione su corpus vergine) nel proprio docstring |
| `docs/cycle174_active_learning_design.md` | **VIVO** | `verimem/active_learning.py:1-5`: «Implements the … loop the `docs/cycle174_active_learning_design.md` **proposed and that was approved on 2026-05-22**». Il design è stato approvato **e** implementato — il sospetto che fosse un piano abbandonato non regge |
| `docs/LIMITS.md` | **VIVO** — ma afferma una cosa che il README smentisce | *«Limits — measured, with the number and the date… **The README keeps one line and points here**»*. Il README **non ci punta**: rimanda a `BENCHMARKS`, `EVIDENCE-external`, `EVIDENCE-stress`, `GOVERNANCE`, e i tre limiti li elenca **in proprio** (riga 39). Il documento pubblico dei limiti esiste, ed è quello che il contratto chiede — **e la vetrina non ci manda nessuno** |
| `docs/MCP_QUICKSTART.md` | **VIVO, datato nel nome** | guida di integrazione in 5 minuti; parla di *«**Engram** (formerly HippoAgent)»* — **due nomi indietro**, il prodotto si chiama `verimem` dal 06/07. I comandi (`pip install -e .`) reggono perché generici, ma un lettore cerca un pacchetto che non si chiama più così |
| `docs/stato-reale/00-ESAME.md` | **VIVO** — è il registro | «Registro unico delle celle misurate», istituito dalla direttiva di Aurelio del 27/08: *«cosa dovrebbe avere teoricamente un progetto del genere? Le ha? Lo fa davvero?»*. **Non giudica il codice: registra le misure.** È l'unico documento di `stato-reale/` che il codice cita (`verimem/soggetto_valore.py`) |
| `docs/stato-reale/01-promesse-vs-realta.md` | **VIVO** | porta la nota datata fatta meglio del corpus: *«misura `main`, e `main` si è mosso di **756 commit**… non è datato perché sbagli, è datato perché il suo **bersaglio è mobile**… **non ho rimisurato il suo contenuto e non affermo che sia caduto**»*. Dichiara anche ciò che NON ha verificato |
| `docs/stato-reale/02-RISPOSTA-cosa-fa-chi-installa-oggi.md` | **VIVO** | SHA `afc6cf73`, 08/08, misurato sul pacchetto da PyPI con HOME dedicata e zero variabili. E una frase che vale per tutto il corpus: *«la mia fetta è cresciuta a quattordici file, **che sono un archivio e non una risposta**. Questa pagina è la risposta; ogni riga ha il file che la prova»* |
| `docs/stato-reale/02p-il-server-parte-su-main-e-dichiara-la-versione-sbagliata.md` | **VIVO, corretto in nota** | il titolo afferma un difetto **curato dal 09/08**, e una nota in cima lo dichiara: *«la seconda metà del titolo NON vale più… curato da `068a60d9`… verificato oggi: `mcp_server.py:1500` costruisce `Server("verimem", version=_verimem_version…)`»*. E distingue **quale metà** vale ancora: *«la PRIMA metà — il server parte — **non l'ho riverificata**: richiede un `initialize` vero su stdio, ed è l'anello che nessuno ha rifatto»* |
| `docs/stato-reale/01b-le-promesse-mancanti.md` | **VIVO, corretto in nota** | il **numero nel titolo** è superato, e la nota lo dice: *«il conteggio nel titolo è superato: **due delle tre sono state colmate**»*, con dove sono state colmate (`README.md`, sezione «What it costs on disk»). Nona forma applicata a un numero |
| `docs/stato-reale/02i-i-fatti-dei-primi-minuti-restano-non-verificati.md` | **VIVO** | SHA `332a2f73`, `git status` pulito, HOME fredda, cache vuota. Completa un passo che `02g` **dichiarava non fatto**: i documenti si passano il testimone sui limiti dichiarati |
| `docs/stato-reale/02l-l-astensione-e-spenta-nel-pacchetto.md` | **VIVO** | SHA, ora, store fresco per ogni braccio, zero variabili. E si apre con *«🔴 **Correggo una mia tesi di due ore fa**»*: l'autocorrezione è nel documento, non in un altro file |
| `docs/stato-reale/17-la-ricerca-ordina-per-data-non-per-pertinenza.md` | **VIVO** | 30/08, corpus reale in `mode=ro` (15.578 fatti alle 12:25). Riporta **verbatim la domanda di Aurelio** come criterio con cui giudicarlo. ⚠️ Il difetto che descrive **non risulta curato**: cercando fra i commit dal 30/08 termini come «ordin/pertinen/relevance» non ho trovato la cura — *cercato, non provato eseguendo* |
| `docs/stato-reale/11-la-quantita-vaga-non-viene-confrontata.md` | **VIVO** | ws4, 27/08 fra le 18:30 e le 19:10, con il perimetro delle celle dichiarato |
| `docs/stato-reale/12-il-rimedio-del-caso-difficile-non-arriva.md` | **VIVO** | 27/08 20:37-21:12, SHA `6cbeb283` — e lo dichiara come *«= il `build=` stampato nei log»*: **lo SHA è quello che il prodotto stesso stampa**, non uno copiato a mano |
| `docs/stato-reale/15-la-banda-decide-e-nessuno-decide-la-banda.md` | **VIVO** | 29/08 00:45-01:44, **SHA per cella** nel registro: non uno SHA per il documento, uno per ogni misura |
| `docs/stato-reale/21-le-due-porte-gemelle-non-si-somigliano.md` | **VIVO** | ws6, 30/08 15:10, misure alla porta MCP sullo store reale in sola lettura |
| `docs/stato-reale/25-tre-ordinamenti-a-confronto-e-nessuno-domina.md` | **VIVO** | ws6, 30/08 18:10, corpus servibile **12.429**, `mode=ro`, sole SELECT |
| `docs/stato-reale/48-ventitre-minuti-senza-daemon-hanno-spento-una-promessa-del-readme.md` | **VIVO — ed è T26a *e* T29, scritti il 30/08** | ws6/Aldo, 30/08 notte. Il titolo per intero: *«Ventitré minuti senza daemon hanno spento una promessa del README, **e resterà spenta**»*. La prima metà è T26a (daemon assente → promessa spenta), la seconda è **T29** (non si sana). Entrambi diventeranno ticket **a settembre** |
| `docs/stato-reale/31-la-porta-dei-documenti-dice-quello-che-quella-dei-fatti-tace.md` | **VIVO** | ws6, 30/08 20:40, e dichiara il metodo: *«porte MCP **interrogate davvero, non lette nel codice**»* |
| `docs/stato-reale/38-il-regime-lo-dice-alla-risposta-e-lo-tace-alla-telemetria.md` | **VIVO** | ws6/Aldo, 30/08 sera, perimetro dichiarato (archivio, memoria, corpus, recall) |
| `docs/stato-reale/70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente.md` | **VIVO** | ws6/Aldo, 2 settembre 00:02: *«chiude il filone “le letture non trovano”»* — **0 su 3** nel titolo |
| `docs/stato-reale/41-la-supersessione-sceglie-sei-volte-meglio-del-caso.md` | **VIVO** | ws6/Aldo, 30/08 notte, perimetro dichiarato. *«Questo pezzo è una **buona notizia**, ed è la prima della serata»*: il numero che dà ragione è scritto con la stessa cura di quelli che la tolgono |
| `docs/stato-reale/64-una-catena-di-quattro-ritiri-fa-sparire-una-misura-intera.md` | **VIVO** | 31/08 mattina, e dichiara **come è nato**: *«nasce leggendo i candidati al recupero, **non cercando questo**»* — la scoperta laterale dichiarata invece che spacciata per ricerca mirata |
| `docs/stato-reale/44-il-rilevatore-dichiara-in-conflitto-quasi-tutte-le-coppie.md` | **VIVO** | ws6/Aldo, 30/08 notte: *«il **99% delle coppie possibili** di un topic»*. Chiude esplicitamente la serie iniziata dal documento 42 — i documenti qui si citano fra loro per numero |
| `docs/stato-reale/75-ho-letto-otto-quarantene-e-due-strati-si-contraddicono-sullo-stesso-fatto.md` | **VIVO** — ed è il modello del ritiro | 02/09 01:51. Il titolo porta il ritiro per intero: *«…e **leggendo l'altra popolazione ho ritirato la mia stessa lettura**»*. La regola che questa mappa ha imparato sette volte stasera, qui era già applicata |
| `docs/stato-reale/22-un-quarto-dei-trattenuti-recenti-e-approvato-dal-giudice.md` | **VIVO** | ws6, 30/08 15:50, corpus **15.755** fatti, `mode=ro`, sole SELECT. È **T25** un mese prima del ticket: `L4.1` ferma e il giudice promuove, sullo stesso fatto. E dichiara il limite — *«non ho letto i 70»* — che il documento 23 chiude il giorno dopo |
| `docs/stato-reale/80-la-stessa-frase-con-otto-o-con-8-riceve-due-verdetti-opposti.md` | **VIVO** | 02/09 04:52, banco **nominato** (`banchi/ws6-la-cifra-e-la-parola.py`), store isolato. Cita *«una lezione di ws5 del 27/08»*: i documenti qui si citano fra loro **a settimane di distanza** |
| `docs/stato-reale/72-il-numero-perde-le-sue-condizioni-fra-il-changelog-e-la-vetrina.md` | **VIVO — ed è il precedente di tutta questa mappa** | 02/09 00:26. Titolo per intero: *«un numero perde le sue tre condizioni fra il CHANGELOG e la vetrina, **e i due criteri che ho scritto per misurarlo erano tutti e due sbagliati**»*. Intestazione: *«(**letta, non stimata**)… audit su un numero pubblico **non mio**, scelto perché è **l'unico della lista che nessun documento di `stato-reale` citava**»* |
| `docs/stato-reale/banchi/ws5-i-comandi-del-readme-pubblicato-funzionano.py` | **VIVO — ed è un presidio** | *«non “il README dice il vero”, ma **“se un utente fa quello che c'è scritto, succede quello che dice?”**»*. E la distinzione che conta: *«la vetrina che conta è quella **pubblicata**… i comandi li estraggo dal `METADATA` del wheel scaricato da PyPI, non dal repo»*. La classe «ricetta rotta» **è presidiata** |
| `docs/stato-reale/85-il-disegno-esploso-dello-store-le-giunture-e-chi-le-presidia.md` | **VIVO** | livello 3 del disegno esploso, 05/09, e dichiara il metodo: *«ogni riga porta **o la misura che presidia la giuntura, o la parola scoperta**»* — nessuna cella inventata |
| `docs/stato-reale/LA-FRASE-DELLA-0.7.7.md` | **VIVO** | ws7, 06/09, *«scritta alle 08:20 e **RIMISURATA alle 08:45**, base `v0.7.6..origin/main` = `460f230e` (alle 08:20 era `13fa323f`: **main si è mosso sotto la** …)»*. Dichiara che il bersaglio si è spostato **mentre scriveva**, e rimisura |
| `docs/sota/L0-L3-anti-confab-layers.md` | **VIVO** | agganciato a `verimem/l1_extended_detector.py` |
| `docs/sota/active-learning-bandit-vs-cron.md` | **VIVO** | agganciato a `verimem/dream_thompson_hook.py` |
| `docs/sota/community-detection-channel-pattern.md` | **VIVO** | agganciato a `verimem/community_detector.py` |
| `docs/sota/cross-encoder-reranking.md` | **VIVO** | agganciato a `verimem/cross_encoder_rerank.py` |
| `docs/sota/embedding-compression.md` | **VIVO** | agganciato a `verimem/embedding_quantize.py` |
| `docs/sota/highway-nodes-pagerank-cache.md` | **VIVO** | agganciato a `verimem/betweenness_cache.py` |
| `docs/sota/multi-signal-fusion.md` | **VIVO** | agganciato a `verimem/fuse_recall.py` |
| `docs/sota/temporal-evolution-narrative.md` | **VIVO** | agganciato a `verimem/snapshot_at_time.py` |
| `docs/sota/README.md` | **VIVO** | indice della cartella; il suo «← gateway.py» era il falso positivo del nome comune, verificato |
| `docs/specs/p2b-ppr-entity-neighbors.md` | **VIVO** | la cosa che specifica **esiste**: `verimem/ppr_seed.py`, `verimem/mcp_server.py`. Non è un piano morto |
| `docs/specs/p3-self-model-multi-anchor.md` | **VIVO** | implementata: `verimem/self_model.py`, `verimem/self_model_refresh.py` |
| `docs/specs/p1-hippo-validate-claim.md` | **VIVO** | agganciata a `verimem/mcp_server.py` |
| `docs/stato-reale/02-utente-che-installa.md` | **VIVO** | ws2 «Vega», 08/08 12:40-13:05: la fetta ② intera, dal nulla al primo fatto |
| `docs/stato-reale/02b-primo-avvio-gate-lingua.md` | **VIVO** | ws2, 08/08 13:50: *«il gate lessicale protegge l'inglese, non l'italiano»* — un difetto di lingua misurato al primo avvio |
| `docs/stato-reale/02c-il-numero-mostrato-e-chi-decide.md` | **VIVO, corretto in nota** | nota di ws7 del 27/08: *«misura `main`, e `main` si è mosso di **741 commit** da allora»* |
| `docs/stato-reale/02d-la-lista-dei-vanti-e-il-carve-out.md` | **VIVO, corretto in nota** | stessa forma: **740 commit** dichiarati nella nota. *«non è la grammatica, è una lista (e un carve-out)»* |
| `docs/stato-reale/02e-chi-installa-riceve-il-22-luglio.md` | **VIVO** | ws2, 08/08 14:40, SHA `3c4c2e1b`, `git status` pulito: *«chi installa oggi riceve il prodotto del 22 luglio, e **nessun numero glielo dice**»* |
| `docs/stato-reale/02f-la-tabella-delle-porte-dal-lato-utente.md` | **VIVO** | ws2, 08/08 14:35-14:45, SHA `2d64b7b7`, `git status` pulito: la tabella delle porte **eseguita dal lato di chi installa** |
| `docs/stato-reale/02g-il-primo-comando-a-freddo.md` | **VIVO** | ws2, 08/08 14:38-14:47, SHA `6d1080cf`, `git status` pulito: *«il primo comando su un'installazione fredda: **la cura è una riga**»* |
| `docs/stato-reale/02h-quali-promesse-reggono-sul-pacchetto.md` | **VIVO** | ws2, 08/08 14:48, SHA `810de530`, pulito: quali promesse reggono **sull'artefatto che l'utente installa** — non su `main` |
| `docs/stato-reale/02j-trust-il-punto-c.md` | **VIVO** | ws2, 08/08 14:58-15:05, SHA `a9969ccf`: *«due modi di dire TRUSTED, e **due esempi su tre che non funzionano**»* |
| `docs/stato-reale/02k-l41-il-verbo-diventa-unita.md` | **VIVO, corretto in nota** | nota di ws7 del 27/08 con **730 commit** dichiarati. *«quando “del 2019 risponde” diventa un valore da cercare nella fonte»* |
| `docs/stato-reale/02m-le-promesse-su-origin-main.md` | **VIVO, corretto in nota** | nota ws7 27/08: **767 commit**. *«la colonna che serve al rilascio»* |
| `docs/stato-reale/02n-il-server-mcp-e-morto-per-chi-installa.md` | **VIVO** | ws2, 08/08 15:44-15:50, SHA `3d47df46`, pacchetto `0.7.0` da PyPI: *«chi installa oggi ha il server MCP **morto**, e **la cura è nel repo dal 29 luglio**»* — il difetto pubblicato con la cura già scritta |
| `docs/stato-reale/02o-l41-e-bilingue-e-allargarlo-peggiora.md` | **VIVO, corretto in nota** | **761 commit**. *«sbaglia in due lingue su cinque, e **allargare la lista peggiorerebbe**»* — la cura ovvia misurata e scartata |
| `docs/stato-reale/04-percorso-di-lettura.md` | **VIVO, corretto in nota** | *«misura `main` a `544d27bd`, cioè **771 commit fa**»* |
| `docs/stato-reale/05-ingestione-documenti.md` | **VIVO, corretto in nota** | **756 commit** |
| `docs/stato-reale/06-parametri-metriche-telemetria.md` | **VIVO, corretto in nota** | *«misura `main` a `5edc0dfe`, cioè **768 commit fa**»* |
| `docs/stato-reale/07-percorso-di-scrittura.md` | **VIVO, corretto in nota** | **771 commit**, stesso SHA del 04: le due fette lette insieme |
| `docs/stato-reale/08-i-656-mb-le-quattro-strade.md` | **VIVO, corretto in nota** | *«il numero nel titolo è **superato di 90 MB**, e questo documento lo dichiara»* — la nona forma applicata a un numero **nel titolo** |
| `docs/stato-reale/09-i-cancelli-del-rilascio.md` | **VIVO** | misurato 26/08 fra le 19:25 e le 23:00: *«cosa impedisce **meccanicamente** di pubblicare»* — è l'antenato di `cancelli_del_tag.py` |
| `docs/stato-reale/10-il-contorno-cambia-il-verdetto.md` | **VIVO** | ws4, 26-27/08 21:30-00:10, celle dichiarate: *«il contorno cambia il verdetto — **e non sappiamo perché**»* |
| `docs/stato-reale/13-la-taglia-della-fonte-degrada-il-gate-nei-due-versi.md` | **VIVO** | 28/08 18:37-20:53: *«degrada **nei due versi** — e per una metà **la cura c'è già**»* |
| `docs/stato-reale/14-la-forma-della-fonte-decide-quale-layer-sbaglia.md` | **VIVO** | 28/08 22:35-23:18: *«su un output di strumento **uno dei due è rumore**»* |
| `docs/stato-reale/16-che-cosa-deve-contenere-un-corpus-tipo-cliente.md` | **VIVO** | ws6/Aldo, 29/08 sera, e dichiara il proprio stato: *«**specifica degli assi**, non del…»* — dice di essere una specifica, non una misura |
| `docs/stato-reale/18-quante-volte-scriviamo-per-ogni-volta-che-leggiamo.md` | **VIVO** | ws6, 30/08 13:36, journal `events.jsonl` + `.1` — e dichiara la trappola: ***«il journal ruota»***, che è la stessa scritta nelle nostre lezioni di casa |
| `docs/stato-reale/19-la-cura-del-ranking-peggiora-il-caso-reale.md` | **VIVO** | ws6, 30/08 13:49, corpus servibile **12.232**, `mode=ro`: **una cura misurata e scartata**, col difetto vero spostato a monte |
| `docs/stato-reale/20-l-archivio-vecchio-ha-gia-una-porta-e-si-chiama-auto-master.md` | **VIVO** | ws6, 30/08 14:22, corpus **12.247**: la porta c'era già e nessuno la usava |
| `docs/stato-reale/24-anche-il-gate-ha-ere.md` | **VIVO** | ws6, 30/08 16:40: *«**quattro ere in ventiquattro giorni**»* — il gate cambia sotto le misure che lo misurano |
| `docs/stato-reale/25-la-specifica-di-L1-cosa-ferma-e-cosa-lascia-passare.md` | **VIVO** | 29-30/08, **celle nominate** (`W7-60`…`W7-65`): e chiede *«quale dei due errori arriva all'utente»*, non quale è più grande |
| `docs/stato-reale/26-la-difesa-che-si-spegne-con-un-booleano.md` | **VIVO** | 30/08 14:12-15:49, celle `W7-69`…`W7-71`: *«su questo corpus è una **compensazione**, non un bug»* — la distinzione che salva una cura sbagliata |
| `docs/stato-reale/26-le-nove-trappole-della-copia-condivisa.md` | **VIVO** | ws6, 30/08: *«**nessuna è ipotizzata: le ho pagate tutte oggi, in prima persona**»*. È la fonte delle nove trappole della copia condivisa che usiamo tutti |
| `docs/stato-reale/27-la-porta-ignora-il-campo-che-dice-di-cosa-parla-un-fatto.md` | **VIVO** | ws6, 30/08 18:55, corpus **12.438** |
| `docs/stato-reale/28-cercare-nel-topic-costa-meno-non-di-piu.md` | **VIVO** | corpus **12.445**: un risultato **contro l'intuizione**, misurato — cercare nel topic costa meno |
| `docs/stato-reale/29-la-ricerca-lessicale-trova-solo-se-indovini-le-parole.md` | **VIVO** | corpus **12.449** |
| `docs/stato-reale/30-la-porta-dei-documenti-e-costruita-meglio-e-l-indice-e-fatto-di-scratchpad.md` | **VIVO** | 30/08 20:15, `document_index.db` in `mode=ro`: e trova che **l'indice è fatto di scratchpad** |
| `docs/stato-reale/32-il-rerank-sa-quando-non-ha-trovato-e-la-porta-serve-lo-stesso.md` | **VIVO** | 30/08 21:15, *«porte MCP **interrogate davvero**»*: il rerank sa di non aver trovato **e la porta serve lo stesso** |
| `docs/stato-reale/33-il-presidio-anti-injection-nasconde-la-roadmap.md` | **VIVO** | *«misure sul rilevatore vero, **non sul codice letto**»*: un presidio che nasconde PHASE 0 della roadmap |
| `docs/stato-reale/34-lo-stesso-fatto-con-una-lettera-greca-viene-quarantinato.md` | **VIVO** | store **temporaneo** in tempdir, **scritture vere**: lo stesso fatto con una lettera greca cade |
| `docs/stato-reale/35-il-rimedio-che-la-ricevuta-suggerisce-non-cambia-l-esito.md` | **VIVO** | 30/08 22:45, store temporaneo, **fuori da pytest**: il consiglio che il prodotto dà non funziona |
| `docs/stato-reale/36-la-promessa-di-astensione-esiste-funziona-ed-e-spenta.md` | **VIVO** | 31/08 00:25: *«esiste, **funziona**, ed è **spenta di default**»* — la forma «capacità spenta» in tre parole |
| `docs/stato-reale/37-il-mio-banco-e-caduto-e-il-prodotto-aveva-gia-la-guardia.md` | **VIVO** | 31/08 01:35, store di Aurelio in **sole letture**: il titolo è un **ritiro** — il banco è caduto e il prodotto aveva ragione |
| `docs/stato-reale/40-il-rerank-che-quasi-non-gira-e-il-banco-che-non-si-puo-rieseguire.md` | **VIVO** | ws6/Aldo, 30/08 notte: e dichiara che **il proprio banco non è rieseguibile** |
| `docs/stato-reale/42-il-presidio-consiglia-una-cura-che-ritirerebbe-mille-fatti.md` | **VIVO** | *«…per contraddizioni **che non lo sono**»*: apre la serie di D-1, chiusa dal 44 |
| `docs/stato-reale/43-le-contraddizioni-sono-log.md` | **VIVO** | *«il **94%** a quattro token di distanza»* |
| `docs/stato-reale/45-il-grounding-alto-non-protegge-dai-numeri-sbagliati.md` | **VIVO** | *«`L4.1` è **l'unico** che li vede»*: un punteggio alto non copre i numeri |
| `docs/stato-reale/46-gli-episodi-si-ricordano-di-essere-letti-e-nessuno-li-dimentica.md` | **VIVO** | *«e **nessuno li dimentica mai**»* |
| `docs/stato-reale/47-sa-fare-la-cosa-e-non-la-fa.md` | **VIVO** — ed è una SINTESI | *«sette misure, **un motivo solo**»*, dichiarata come *«sintesi dei documenti 36-46»*: il corpus si auto-organizza |
| `docs/stato-reale/49-il-prodotto-avvisa-a-ogni-scrittura-e-l-inerzia-e-nostra.md` | **VIVO** | *«avvisa a ogni scrittura **da un mese**, e l'inerzia è nostra»* — il difetto attribuito a noi, non al prodotto |
| `docs/stato-reale/50-il-pavimento-e-una-lama-a-due-tagli.md` | **VIVO** | *«…e **l'ho scoperto cercando altro**»*: scoperta laterale dichiarata |
| `docs/stato-reale/51-ho-scritto-settanta-fatti-e-col-nome-del-loro-argomento-ne-torna-il-nove-per-cento.md` | **VIVO** | **9%** su settanta fatti scritti da lui: si misura sul proprio lavoro |
| `docs/stato-reale/52-undici-dei-miei-fatti-si-sono-mangiati-fra-loro.md` | **VIVO** | *«e l'etichetta del ritiro dice una cosa che non ha ver…»* — la supersessione misurata **sui propri** fatti |
| `docs/stato-reale/53-il-pavimento-si-ripara-da-solo-fra-centocinque-fatti-e-taglia-il-98-percento.md` | **VIVO** | *«seguito diretto del [48]»*: i documenti si citano per numero **e con il link** |
| `docs/stato-reale/54-la-memoria-non-ha-un-tetto-di-lunghezza-ha-un-pavimento-a-cinque-parole.md` | **VIVO** | *«**chiude il limite dichiarato nel [51]**»* |
| `docs/stato-reale/55-non-e-la-forma-della-domanda-e-il-vocabolario.md` | **VIVO** | *«**chiude il limite dichiarato nel [54]**»* — terzo anello della catena |
| `docs/stato-reale/56-lo-zero-e-un-interruttore-in-quattro-punti-e-la-cura-la-chiama-solo-chi-l-ha-scritta.md` | **VIVO** | *«nasce dal **voto sulla proposta** “cura-pavimento” di @ws2»*: la decisione collegiale lascia traccia nel documento |
| `docs/stato-reale/57-la-memoria-attraversa-le-lingue-e-non-attraversa-i-sinonimi.md` | **VIVO** | *«chiude il limite dichiarato nel [55]»* — quarto anello |
| `docs/stato-reale/58-nell-altra-direzione-la-lingua-costa-uguale-e-il-livello-crolla-per-una-ragione-che-non-ho-isolato.md` | **VIVO** | *«chiude **due** limiti»*, e il titolo ritira mezza tesi: *«il “crollo di livello” **era il mio campione**»* |
| `docs/stato-reale/59-i-quarantinati-senza-layer-sono-autoclaim-e-il-prodotto-li-ferma-senza-chiamare-nessuno.md` | **VIVO** | *«chiude un limite che avevo lasciato aperto **per giorni**»* |
| `docs/stato-reale/60-la-transizione-del-pavimento-colta-mentre-avveniva.md` | **VIVO** | 31/08 **ore 02:52:23** — al secondo: *«colta **mentre avveniva**»*, e chiude il [48] |
| `docs/stato-reale/61-il-punteggio-separa-benissimo-e-per-questo-l-avviso-ha-ragione.md` | **VIVO** | *«risponde a una domanda che avevo posto **al canale** venti minuti prima»*: il canale entra nel documento |
| `docs/stato-reale/62-tagliare-la-source-costa-un-sesto-di-allungarla.md` | **VIVO** | *«**verifica indipendente** della cura di @ws2 su un caso mio già caduto»* |
| `docs/stato-reale/63-la-cura-che-il-quarantadue-proponeva-e-misurabile-e-toglie-l-ottantasei-per-cento.md` | **VIVO** | *«chiude il limite finale del [42]»*: la serie D-1 aperta e chiusa dallo stesso autore |
| `docs/stato-reale/65-quali-numeri-di-stanotte-reggono-ancora-stamattina.md` | **VIVO** | *«stessa domanda che @ws7 si è fatto sui suoi aggregati, **sui miei**»* — il metodo di un altro applicato a sé |
| `docs/stato-reale/66-il-criterio-scartava-proprio-i-casi-piu-comuni.md` | **VIVO** — ritiro col numero | *«…e **il tasso che avevo dato è sbagliato**»*. Chiude *capovolgendolo* il limite del [64] |
| `docs/stato-reale/67-la-data-nella-domanda-spegne-la-risposta.md` | **VIVO** | *«e **il silenzio non ha un avviso**»* — la classe «qualcosa tace», applicata al filtro temporale |
| `docs/stato-reale/68-il-numero-pubblico-non-si-riproduce-e-la-domanda-aperta-ha-risposta.md` | **VIVO** | *«audit matematico su **un numero non mio**»*: stessa scelta del 72 |
| `docs/stato-reale/69-la-cura-che-avevo-proposto-costa-sei-ancore-vere-su-diciotto.md` | **VIVO** — ritiro | *«**ritira la raccomandazione del [67]**»*, e il costo è misurato: sei ancore vere su diciotto |
| `docs/stato-reale/71-quando-il-filtro-temporale-agisce-toglie-tre-quarti-di-cio-che-ha-in-mano.md` | **VIVO** | *«seguito immediato del [70]»* |
| `docs/stato-reale/73-il-journal-registrava-duecentocinquantaquattro-zeri-inventati.md` | **VIVO** | *«**254 zeri che nessun risultato aveva**, e il difetto era scritto nel commento»*. **Cura in `8161ffe3`**: documento, difetto e commit nella stessa riga |
| `docs/stato-reale/74-chi-ha-fermato-un-fatto-adesso-si-sa-sempre-e-il-buco-e-tutto-storico.md` | **VIVO** | *«**chiude in positivo** un aperto»*: il 71% di buco è **debito storico**, non difetto vivo |
| `docs/stato-reale/76-la-via-che-raccomandiamo-per-i-fatti-lunghi-non-l-ha-mai-percorsa-nessuno.md` | **VIVO** | *«funziona, e **non l'ha mai percorsa nessuno**»* — la capacità pronta e mai esercitata |
| `docs/stato-reale/77-sei-capacita-pronte-che-nessun-uso-reale-esercita.md` | **VIVO** — SINTESI | *«sintesi di **sei misure indipendenti**»*: è il documento da cui viene il corollario *«l'assenza non ha un canale»* |
| `docs/stato-reale/78-la-precisione-di-l41-sta-fra-il-72-e-l-87-percento.md` | **VIVO** | 02/09 03:44, **banco nominato**, sola lettura: e dà un **intervallo**, non un numero secco |
| `docs/stato-reale/79-una-riga-di-vetrina-dichiara-8-su-10-e-oggi-il-prodotto-ne-ammette-10.md` | **VIVO** | **A/B fra il prodotto del 26/08 e quello di oggi**: la vetrina dichiara meno di quello che il prodotto fa |
| `docs/stato-reale/81-la-prova-conservata-e-abbastanza-per-rifare-il-giudizio.md` | **VIVO** | *«**Sì al tetto di oggi, no se lo si abbassa**»*: la risposta condizionata invece del sì secco |
| `docs/stato-reale/82-il-feedback-loop-non-ce-ma-il-percorso-che-lo-produrrebbe-si.md` | **VIVO** | muro M7, banco nominato: distingue **ciò che non c'è** da **ciò che lo produrrebbe** |
| `docs/stato-reale/83-il-gate-non-converte-i-numeri-scritti-in-parola.md` | **VIVO** | 03/09 20:12, banco `ws6-due-frasi-gemelle-due-verdetti.py`: **ferma 3 fatti veri su 4** |
| `docs/stato-reale/84-su-quali-porte-il-recall-dichiara-i-fatti-scaduti.md` | **VIVO** | 04/09, due banchi nominati: *«**e su quali no**»* — la domanda porta per porta |
| `docs/stato-reale/86-il-disegno-esploso-lo-store-tabelle-campi-e-chi-li-scrive.md` | **VIVO** | 05/09 23:10, *«tutto misurato con `sqlite3` **in sola lettura**»* |
| `docs/stato-reale/AGENZIA.md` | **VIVO** — è il mandato | il documento dei ruoli, dal mandato di Aurelio del 04/09 20:20. È la fonte di chi fa cosa, e il board ne è la versione viva |
| `docs/stato-reale/C2-tabella-classi-core.md` | **VIVO** | ws5, 29/08 20:10, **claim nominato**: le classi core di falsità in italiano **e** in inglese |
| `docs/stato-reale/C3-parita-porte.md` | **VIVO** | ws5, 30/08, claim `f7eca18c246f`: *«chiude il pezzo ② assegnato da `lead-audit`»* — il compito assegnato e chiuso, tracciato |
| `docs/stato-reale/CENSIMENTO-DEI-199-STRUMENTI.md` | **VIVO** | ws4, 06/09 06:20→08:01: *«cosa fanno **davvero** i 199 strumenti senza permesso»* |


## 🔑 Tre forme che l'indizio non distingue, e che cambiano il verdetto

Leggendo i primi dieci sono uscite tre forme diverse di «nomina un file che non
esiste», e **solo la prima contraddice il codice**:

1. **La ricetta** — dice al lettore *«esegui questo comando»*, e il comando non c'è.
   Chi la segue sbatte contro un errore: **CONTRADDICE IL CODICE**.
2. **Il piano** — elenca file *da scrivere* (« write failing tests first», colonna
   «new», «Aggiungere uno script»). Non afferma che esistano: se non sono mai stati
   scritti il documento è **MORTO**, non bugiardo.
3. **Il racconto** — nomina un file *dicendo* che è stato rimosso, o citando chi lo
   diceva. È **VIVO**, e spesso è il documento più preciso del mucchio.

⇒ Il conteggio «13 documenti nominano un path inesistente» **non è** «13 documenti
sbagliati»: dei primi dieci letti, **uno solo** è una ricetta rotta.


### 🆕 Quarta forma, e un mio righello che ha sbagliato nove volte su dieci

Cercando quali dei 39 documenti citati da README e CHANGELOG non esistono, il mio
grep ne ha dati **dieci**. Verificati uno per uno: **nove erano falsi positivi miei**.

· `multi-signal-fusion.md`, `temporal-evolution-narrative.md` → esistono in `docs/sota/`:
  il grep estraeva il **nome senza il percorso** con cui erano citati.
· `FORGIA.md`, `RND_MEMORIE.md`, `RND_*` → esistono in `docs/archive/` col prefisso della
  data. Il CHANGELOG li cita col nome vecchio **in voci di versioni passate**: racconta.
· `emerging_skill_master-fact.md` → non è un documento del repo: è un file nella cartella
  dati dell'utente (`~/.engram/skill_drafts/…`), dentro un blocco «Disk audit». Il mio
  grep prende qualunque `*.md` nel testo, **anche i file di qualcun altro**.

**Il decimo è vero, ed è una forma nuova: il RIMANDO RINOMINATO.** Il documento esiste, ma
con un nome diverso da quello citato — `CHANGELOG.md:2344` promette «full report in
`SECURITY_AUDIT.md`», e il file si chiama `SECURITY_AUDIT_2026-07-11.md`. Non contraddice
il codice e non è morto: **è un rimando che non arriva**, e si cura con una riga.

🔎 Lezione per questa mappa: **il grep serve a trovare i candidati, mai a contarli.**
Nove su dieci sarebbero stati un allarme falso consegnato come misura.


## 🚨 Una mappa di questo corpus ESISTEVA GIÀ, e avverte delle trappole in cui sono caduto

`docs/stato-reale/README.md` non è un documento qualunque: è **l'indice del corpus**,
scritto il 26/08, e in cima porta tre avvertimenti che ho ritrovato stasera **sulla mia
pelle invece che leggendoli**:

> *«un criterio sintattico su una proprietà semantica sbaglia in **entrambe** le direzioni»*
> — e ne dà i due casi, visti «nello stesso censimento, a un'ora di distanza»: un titolo
> segnato «contiene un numero» perché `L4.1` ha dentro un 4 e un 1, e tre file dati per
> «senza SHA» perché lo dichiaravano in un blocco intestato invece che fra backtick.

> ⛔ *«**E aprite anche i casi che il righello non ha segnalato.**»*

> ⛔ *«Un documento che ha per contenuto un'assenza fallisce ogni `grep` che cerchi una
> presenza»* — l'esempio è `03-cose-spente.md`, che cita una variabile assente dal codice:
> l'assenza **è il suo finding**, e marcarlo scaduto sarebbe stato l'errore.

🔑 **I due allarmi falsi che ho fermato stasera sono la stessa forma, ed erano già scritti.**
Non ho cercato in casa prima di partire: è la regola O1, e non l'ho applicata. Da qui in
avanti questa mappa **continua quella**, non la rifà — e il prossimo giro apre i documenti
che il mio righello **non** ha segnalato, come quella pagina chiede.


## 🔍 La zona cieca, aperta — e non era cieca

L'indice del corpus chiede di **aprire i casi che il righello non ha segnalato**. In
`docs/stato-reale/` sono **62**: nessun path rotto, nessuno che li citi.

Ho cercato quelli che **non dichiarano né SHA né data in testa** — perché una misura
senza data letta come attuale è la forma più dannosa in questa cartella. Primo giro:
**24**. Ne ho letti due, e **tutti e due la dichiaravano nella seconda riga**:
«ws6 · **30/08** ore 16:20», «ws6/Aldo — **30/08**, sera». Il mio regex conosceva
`2026-08-30` e non `30/08` — **il formato che questa casa usa davvero**.

```
  PRIMA (regex senza «30/08»):  38 con data · 24 senza
  DOPO  (formato di casa):      62 con data ·  0 senza
  controllo positivo: un testo senza alcuna data risulta «senza»  ✅
```

⇒ **62 documenti su 62 dichiarano quando sono stati scritti.** La classe più grossa di
`stato-reale/` non inganna sul tempo: si legge come fotografia, e la fotografia porta la
sua data.
⚠️ **Dichiarare la data non è essere veri**: dice solo che il documento non si spaccia per
attuale. Il verdetto su ciascuno resta da dare leggendolo.

🪞 **Terzo criterio mio sbagliato in un'ora** — e stavolta l'avviso era scritto nero su
bianco nell'indice del corpus: *«un criterio sintattico su una proprietà semantica sbaglia
in entrambe le direzioni»*. L'ho verificato inciampandoci invece che leggendolo.


### 🆕 Quinta forma: il documento A SCADENZA

Un **handoff** nasce per un uso singolo — far ripartire una sessione — ed è **morto per
costruzione** quando quell'uso è finito. Non è un difetto: è la sua natura. Ma occupa
spazio nella ricerca, e chi lo trova può crederlo attuale.

In `docs/` alla radice ce ne sono **7** col ciclo o l'handoff nel nome:
`CYCLE109_HANDOFF` · `CYCLE113-HANDOFF` · `CYCLE134-DESIGN` ·
`cycle156_unique_index_cross_process_design` · `cycle159_scaling_experiment` (×2) · …

⇒ **Non vanno cancellati e non vanno letti come attuali**: vanno riconosciuti per quello
che sono. Il segnale più forte non è la data — che c'è — ma il **riferimento a un ramo che
non esiste più**: `cycle109-provenance-fact-schema-v3` è sparito, e il documento lo nomina
come se ci si potesse tornare.


### 🧮 Sesta lezione: due indizi opposti si PESANO, non si sommano

`EPISTEMIC_FAILURES_STUDY.md` aveva **due** indizi contrari: un path `.py` inesistente
(→ sospetto «contraddice») e un aggancio al codice (→ «vivo»). Guardando **solo il primo**
gli ho dato CONTRADDICE, e l'ho scritto. Guardati insieme, non sono pari:

· l'aggancio è nella **prima riga** del modulo che il documento descrive;
· il path rotto è alla riga 87, **dentro una bibliografia** di banchi.

⇒ **Un rimando rotto in bibliografia non annulla un aggancio in cima a un modulo.** Il
verdetto giusto è *vivo, con un rimando rotto* — la stessa forma di `SECURITY_AUDIT`.
🔑 E il criterio più forte trovato finora è proprio quello: **il documento che un modulo
cita come proprio disegno è vivo**, perché se muore il modulo resta senza spiegazione.
Su 64 documenti di `docs/` alla radice, **10 sono agganciati così**.


## 📐 `docs/sota/` — la cartella dove ogni documento ha il suo modulo

**8 documenti su 9 sono agganciati uno a uno** al modulo che implementa la tecnica che
descrivono. Il nono è l'indice della cartella.

```
  L0-L3-anti-confab-layers.md            <- verimem/l1_extended_detector.py
  active-learning-bandit-vs-cron.md      <- verimem/dream_thompson_hook.py
  community-detection-channel-pattern.md <- verimem/community_detector.py
  cross-encoder-reranking.md             <- verimem/cross_encoder_rerank.py
  embedding-compression.md               <- verimem/embedding_quantize.py
  highway-nodes-pagerank-cache.md        <- verimem/betweenness_cache.py
  multi-signal-fusion.md                 <- verimem/fuse_recall.py
  temporal-evolution-narrative.md        <- verimem/snapshot_at_time.py
  README.md                              <- (indice: il «<- gateway.py» era il falso
                                             positivo del nome comune, verificato)
```
⇒ **VIVI tutti e nove.** È il modello di come una cartella di ricerca resta viva: ogni
pagina ha un modulo che la cita, e ogni modulo ha una pagina che lo spiega.

## 🧪 `docs/specs/` — e il settimo righello sbagliato, che era il più pericoloso

Tre specifiche su otto sono agganciate per nome (`p1` ← `mcp_server.py`, `p2` ←
`entity_kg.py`, `p2c` ← `openie.py`). Le altre cinque no — e stavo per chiamarle **piani
mai realizzati**. Prima ho cercato **il contenuto invece del nome**:

```
  primo tentativo (grep -E con «\|» invece di «|» — sintassi mia sbagliata):
     p2b-ppr-entity-neighbors    ->  NESSUN modulo con quei simboli
     p3-self-model-multi-anchor  ->  NESSUN modulo con quei simboli

  rifatto con l'alternanza giusta:
     p2b-ppr-entity-neighbors    ->  verimem/ppr_seed.py · verimem/mcp_server.py
     p3-self-model-multi-anchor  ->  verimem/self_model.py · self_model_refresh.py
```
⇒ **Sono implementate tutte e due.** Il documento non è citato dal codice, ma la cosa che
descrive **esiste**: sono **VIVE**, non piani morti.

🔑 **Settima lezione, e chiude il cerchio delle altre sei: il falso negativo di un grep è
più pericoloso del falso positivo.** Un «NESSUNO» **non fa attrito** — sembra una
risposta, non un errore — e lo si consegna senza controllarlo. Un falso positivo urta
contro il primo documento che apri; un falso negativo resta invisibile per costruzione.


## 🔬 `docs/ricerca/` — sedici documenti, tutti di questa settimana

Nessuno è vecchio: il più antico è del **02/09**, il più recente del **06/09**. Non è
archeologia, è **ricerca corrente**, e per questa cartella la domanda «vivo o morto» non
è quella giusta. Quella giusta è: **la decisione che propongono è stata presa?**

### 🆕 Ottava forma: il documento di DECISIONE APERTA

Quattro documenti formano un gruppo solo — `il-giudice-della-0.8.0-tre-opzioni` più le tre
pagine `opzione-a`, `opzione-b`, `opzione-c`. Il documento madre è **VIVO** e fa una cosa
che vale la pena copiare:

> *«Le tre opzioni hanno una pagina ciascuna. **Qui non si ripete il loro contenuto**: qui
> c'è solo ciò che serve a **sceglierle**, e sta in un posto solo perché un criterio
> ricopiato in tre file diverge — è la prima delle classi di errore che ci costano.»*

⇒ **Il criterio di scelta sta in un posto solo, per costruzione.** È la classe ① del
nostro metodo applicata mentre si scrive, non dopo l'incidente.

⚠️ **Il rischio di questa forma**, e va scritto: un documento di decisione aperta resta
vivo finché la scelta non è fatta. Se la scelta viene presa **altrove** — sul canale, in un
commit — e il documento non la registra, **chi legge non sa che è chiusa** e riapre una
discussione già conclusa. Cercando «opzione» sul canale non ho trovato una decisione
dichiarata: allo stato, **aperta**.


## ⚖️ Le due metà del corpus si giudicano con DUE criteri diversi

Il criterio più forte trovato — *il documento che un modulo cita come proprio disegno è
vivo* — **non funziona su `docs/stato-reale/`**, e la misura lo dice:

```
  su 162 file di docs/stato-reale/:  agganciati al CODICE  2
     00-ESAME.md   <- verimem/soggetto_valore.py     (aggancio vero)
     README.md     <- verimem/gateway.py             (falso positivo del nome comune)
  ⇒ un solo aggancio vero su 162.
```

**Non è un difetto: è la natura della cartella.** `stato-reale/` è una **cronaca** — misure,
esami, ticket, risposte a domande di Aurelio — e una cronaca il codice non la cita mai.

⇒ **Due criteri, uno per metà:**
· `docs/` radice, `sota/`, `specs/`, `ricerca/` → **l'aggancio al codice**: 21 documenti
  agganciati al modulo che descrivono, e `sota/` è 8 su 9.
· `docs/stato-reale/` (164, il **57%** del corpus) → **la dichiarazione di data e SHA**,
  perché lì il pericolo non è essere scollegati, è **essere letti come attuali**. Misurato
  nella zona cieca: **62 su 62 la dichiarano**.

🔑 **Applicare un criterio solo avrebbe dato 162 falsi «morti» su una cartella sana.**


### 🆕 Nona forma: il documento CORRETTO IN NOTA — e la catena che si chiude

`02p` porta nel **titolo** un difetto che non esiste più. Non è stato riscritto né
cancellato: gli è stata messa in cima una **nota datata** che dice *quale metà* del titolo
è caduta, **con il commit che l'ha curata** (`068a60d9`, il giorno dopo la misura) e la
riga di codice verificata oggi. E dichiara l'altra metà come **non riverificata**, dicendo
perché: *«richiede un `initialize` vero su stdio, ed è l'anello che nessuno ha rifatto»*.

🔑 **E qui la catena si chiude**, ed è il modello migliore che ho trovato in tutto il corpus:
```
  il documento registra il difetto   docs/stato-reale/02p…md
  il commit lo cura                  068a60d9  «il server diceva agli agenti la versione di mcp»
  lo smoke lo presidia a ogni tag    smoke_wheel_pre_tag.sh:222
                                       riga 9 «serverInfo dichiara la versione di verimem, non di mcp»
```
⇒ **Misura → cura → presidio.** Un difetto documentato che non torna perché qualcosa lo
controlla a ogni rilascio. È il contrario del documento che invecchia in silenzio.


## 🔎 Un difetto documentato il 08/08 è diventato un ticket un mese dopo

`02i` si intitola *«`warmup` risolve per il futuro; i fatti dei primi minuti restano non
verificati **per sempre**»* — ed è datato **08/08**.

È **T26a/T29**: la scrittura che entra non giudicata e che nessuna cura successiva sana.
Il ticket è nato a settembre; **la misura c'era da un mese**.

⇒ Per la domanda del contratto — *quanti dei difetti noti hanno tutti e tre gli anelli
(documento · cura · presidio)?* — qui il **primo anello esisteva prima del ticket**, e
nessuno l'aveva collegato. Non è un documento morto: è un documento **che aveva ragione
presto**, e la mappa serve anche a questo — a far trovare la misura che c'era già.


## 📢 «Una porta che tace» è stata misurata TRE volte prima di diventare un ticket

```
  08/08  02i   «i fatti dei primi minuti restano non verificati PER SEMPRE»
  30/08  21    «le due porte gemelle non si somigliano, e QUELLA SBAGLIATA TACE»
  09/26  T26a  la porta MCP delega: se il daemon non c'è, la scrittura entra non
               giudicata IN SILENZIO
```
Tre documenti, tre date, **la stessa forma**: una porta che non dice quello che non ha
fatto. Il ticket è arrivato per ultimo.

⇒ Non è che mancasse la misura: **mancava il filo che le lega**. È il valore che questa
mappa può aggiungere al contratto — non «quali documenti sono morti», ma **quali misure
dicevano già la stessa cosa e nessuno le ha messe in fila**.

🔍 **E una cosa sulla qualità del corpus**, misurata leggendo: gli SHA qui non sono
decorativi. `12` dichiara il suo come *«= il `build=` stampato nei log»* — cioè quello che
**il prodotto stampa di sé**, non uno copiato a mano; `15` porta **uno SHA per cella**, non
uno per documento. Chi ha scritto queste pagine sapeva che un numero senza il suo istante
non vale.


## 🔗 La catena completa: CINQUE documenti prima del ticket

Cercando i titoli che parlano di **silenzio** e di **daemon**, la catena di T26a si allunga
da tre a cinque, e comprende anche **T29**:

```
  08/08   02i   «i fatti dei primi minuti restano non verificati PER SEMPRE»
  30/08   39    «le finestre cieche della memoria: ventitré minuti, cinquantaquattro fatti»
  30/08   48    «ventitré minuti senza daemon hanno spento una promessa del README,
                 E RESTERÀ SPENTA»          <- T26a nella prima metà, T29 nella seconda
  30/08   21    «le due porte gemelle non si somigliano, e QUELLA SBAGLIATA TACE»
  09/26   T26a e T29, aperti come ticket
```

🔑 **`48` è il documento che li contiene tutti e due, e ha quasi un mese più del ticket.**
La frase «e resterà spenta» è T29 — *il giudizio mancante non si sana* — scritta il 30
agosto in un titolo.

⇒ **Questo è il filone che rende, e non è «quali documenti sono morti».** È: **le misure
c'erano, sparse in cinque pagine, e nessuno le aveva messe in fila.** Un indice per
*difetto* — non per data, non per autore — le avrebbe fatte incontrare, e la 0.7.6 non
sarebbe uscita con dentro un difetto che tre documenti avevano già descritto.

📌 **Altri titoli della stessa famiglia, ancora da leggere**:
`31-la-porta-dei-documenti-dice-quello-che-quella-dei-fatti-tace` ·
`38-il-regime-lo-dice-alla-risposta-e-lo-tace-alla-telemetria` ·
`70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente`. **La forma «qualcosa tace» è
ricorrente in questo corpus**, e vale la pena contarla per intero.


### 🆕 Decima forma: il documento che afferma una RELAZIONE che non c'è

`LIMITS.md` non sbaglia un numero e non è scaduto: sbaglia **su un altro file**. Dice che
il README *«tiene una riga e punta qui»*, e il README punta altrove.

```
  link a docs/ nel README:  BENCHMARKS.md · EVIDENCE-external · EVIDENCE-stress · GOVERNANCE
  LIMITS.md:                assente
  README.md:39              «Three limits belong next to those numbers…» — elencati in proprio
```

⇒ **Non si scopre leggendo il documento**: si scopre solo andando a guardare l'altra
superficie. È la forma più difficile da trovare di tutte e dieci, e la più facile da
curare — **una riga nel README**.
🔑 E vale per il rilascio: il contratto chiede i limiti dichiarati per nome col numero.
**Quel documento esiste ed è fatto bene. Nessuno lo trova.**


## 🚨 Il documento 72 è il precedente di questa intera mappa, e l'ho trovato per ultimo

Il titolo di `72`, per intero:
> *«Un numero perde le sue tre condizioni fra il CHANGELOG e la vetrina, **e i due criteri
> che ho scritto per misurarlo erano tutti e due sbagliati**»*

Tre cose, in un documento del **2 settembre**:
1. **Dichiara nel titolo che i propri criteri erano sbagliati** — è la mia stessa serata
   (sette righelli caduti), scritta cinque giorni prima da un altro.
2. *«(letta, non stimata)»* — **l'ora è letta**, non ricostruita.
3. Ha scelto quel numero **perché nessun documento lo citava**: ha cercato **la zona cieca**,
   che è esattamente il metodo che questa mappa ha adottato stasera come scoperta propria.

E il tema — *un numero che perde le sue condizioni passando dal CHANGELOG alla vetrina* — è
**la decima forma**, un mese prima che io la chiamassi così.

🔄 **È la seconda volta stasera che trovo il mio metodo già scritto qui dentro** (la prima
è l'indice del corpus, `stato-reale/README.md`). O1 dice di cercare in casa **prima**: non
l'ho fatto, e ho ricostruito da zero — comprese le trappole — quello che c'era.
🔑 Per chi continua: **le lezioni di questa mappa non sono nuove. Sono ritrovate.** Il
valore non è averle scoperte, è **averle messe in un posto solo** — che è precisamente il
difetto che il documento 72 descrive per i numeri.


## 🧪 574 banchi — e la mappa li aveva ignorati

```
  ls docs/stato-reale/banchi/*.py | wc -l   ->  574
  nei loro nomi:  mcp 17 · cli 5 · sdk 2 · doctor 1 · warmup 1 · readme 3 · as_of 12
```

**Tutte e sei le superfici del contratto hanno banchi**, e l'`as_of` ne ha dodici.

🔻 **Correzione a quello che avevo scritto stasera**: è vero che **lo smoke pre-tag** prova
una superficie su sei (letto nel file, non dedotto). **Non è vero** che quelle prove non
esistano: **ho guardato lo strumento del rilascio e ho concluso sul prodotto.**
⇒ La prova da utente **non è da costruire, è da assemblare**.

⚠️ **E non ripeto l'errore opposto**: 574 banchi col nome giusto **non sono 574 prove**. Un
nome non dice che il banco gira, né che provi il criterio del contratto. **Il grep trova i
candidati e non li conta** — è la lezione che questa mappa ha pagato sette volte.

## Quello che gli indizi dicono di tutti e 287

```
  documenti totali                                 287
  citati da README, CHANGELOG, codice, test o
    da un altro documento                          187
  che nominano un path .py INESISTENTE              13   <- la coda dei candidati
     di cui «probabile racconto» (triage)            5
     di cui «probabile affermazione»                18   (un documento puo' averne piu' d'uno)
```
Dove stanno: `docs/stato-reale/` **164** · `docs/` (radice) ~67 · `docs/ricerca/` 16 ·
`docs/archive/` 11 (tutti citati) · `docs/sota/` 9 · `docs/specs/` 8 · il resto sparso.



## 🔗 Una catena di limiti PAGATI, uno dopo l'altro

```
  51  dichiara un limite  («ne torna il 9%»)
  54  «CHIUDE IL LIMITE DICHIARATO NEL 51»   -> il pavimento è a cinque parole
  55  «CHIUDE IL LIMITE DICHIARATO NEL 54»   -> non è la forma, è il vocabolario
```
Tre documenti in due notti, e ognuno **si apre dichiarando quale debito sta pagando**.
Con `47`, che è una **sintesi dichiarata** dei documenti 36-46, e `53`, *«seguito diretto
del 48»*, il quadro è chiaro: **questo corpus si auto-organizza**, e i legami sono scritti
**nel documento**, non lasciati alla memoria di chi legge.

🔑 È il contrario del difetto che la mappa cercava. Dove i legami sono scritti, la catena
regge; dove non lo sono — T26a in quattro pagine sparse — il ticket arriva un mese dopo.

## 🧮 Il numero DEVE essere contabile da questa tabella

🔻 **Correzione, 09/09.** Ieri ho dichiarato **68 documenti letti** mentre la tabella ne
conteneva **56**: la differenza erano i documenti classificati **dentro le sezioni**
(`docs/sota/` in blocco, due di `specs/`) senza una riga propria.

**Non erano inventati** — l'aggancio al codice era verificato per ognuno — ma **chi legge
la tabella ne contava 56**, e il numero che davo sul canale era 68. Un contatore che non si
può ricostruire dal documento **è un numero fidato sulla parola**, ed è la cosa che questa
mappa passa la giornata a segnalare negli altri.

⇒ **Regola per questo file**: ogni documento con un verdetto ha **una riga**. Il numero in
fondo si conta con `grep -c '^| \`docs'` e deve coincidere. Se non coincide, **vince la
tabella**.

## Contatore

**Classificati con verdetto letto: 150 su 287** (e uno **corretto**: `EPISTEMIC_FAILURES_STUDY`). Con gli indizi raccolti: 287 su 287.
Triati sui path rotti: 13 su 13, e **dei dieci letti uno solo contraddice davvero**.
*Il numero che conta è il primo: gli indizi non sono un verdetto, e non li conto come tale.*

---

🔗 **L'indice per DIFETTO sta in [`difetti.md`](difetti.md)**: lega ogni ticket alle pagine che lo descrivevano già, in ordine di data. È nato qui, dalla catena di T26a.
