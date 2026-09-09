# Resoconto della mappa dell'intera superficie — 09/09 (bozza del lead, i numeri finali si aggiornano alla chiusura)

Mandato di Aurelio (08/09 20:27): «tutta l'intera superficie del codice mappata, tutte le funzioni, tutti i claim del readme collegati con la riga di codice corrispondente, documenti interni chiaramente… certezza matematica di aver guardato tutto». Il 09/09 12:05: «riprendete e finite questa attività e alla fine fermatevi tutti e vediamo cosa esce».

## 1. Il righello (cosa vuol dire «guardato tutto»)

`scripts/mappa_completa.py` (ramo `lead/mappa-indice`) confronta l'insieme delle funzioni e classi che l'AST trova sotto `verimem/` con l'insieme delle righe di tabella della mappa (`docs/stato-reale/mappa/*.md`), per owner e in totale; conta le righe del README collegate (811) e i documenti classificati (289, la mappa esclusa); stampa COMPLETA solo a zero mancanti. Superficie: 424 file, 129.986 righe, 3.200 definizioni; README 811 righe; docs 289 file.

**Stato alla fusione delle 12:30 (70e9d883)** — da aggiornare alla chiusura:

| owner | funzioni mappate | note |
|---|---|---|
| lead | 652 / 652 | i cinque file finali li ha chiusi Nadia (ws4) |
| ws1 Marie | 286 / 286 | 99 differenze di formato e 3 di sostanza dichiarate |
| ws2 Giano | 67 / 67 | |
| ws3 Galileo | 123 / 456 | client.py chiuso; gateway, tools_extra, code.py in corso |
| ws4 Nadia | 365 / 365 | 390 voci, 19 misurate sulla promessa |
| ws5 Tara | 8 / 551 | 551/551 sul suo checkout; ramo non ancora su origin |
| ws6 Aldo | 66 / 480 | semantic.py, memory.py, entity_kg, contradiction in corso |
| ws7 Iris | 0 / 176 | README 695/811 righe collegate (57 claim senza presidio); cli/tui/doctor per comandi, non per funzione |
| ws8 Corrado | 0 / 167 | documenti 255/289; i 31 moduli sono in prosa |
| **TUTTE** | **1567 / 3200** | verdetti: 1235 come promesso · 20 non come promesso · 335 non misurati · 128 mai chiamate |

## 2. Ticket aperti dalla mappa (tutti con la prova nel post sul canale o nella mappa)

- **T42** import di `clp.agentos` senza dipendenza dichiarata (syscall_bridge, op_supervisor, mesh_memory) — chiuso da Marie: quinto esito fuori contratto.
- **T43** registro ombra a metà · **T44** `sos_compensator` opposto alla promessa (rimozione proposta) · **T45** `verify_pin` mai chiamata (Marie: «il modulo che funziona non è attaccato, quello attaccato ha il buco») · **T46** transcript tools su indice vuoto · **T47** classifica di fiducia senza il moat (`trust_score`, `fact_priority`, `trust_signal`: tre classifiche, nessuna legge il giudizio del gate) · **T48** `sign_head` firmata, mai verificata.
- **T49** sei tool MCP servono i fatti QUARANTENATI come risultati (`hippo_oracle_query`, `hippo_chain_facts`, `hippo_prompt_skeleton`, `hippo_cross_agent_consensus`, `hippo_find_duplicate_facts`, `hippo_facts_find_duplicates`; settimo, `hippo_forward_chain` li usa come PREMESSA, Giano): causa `list_facts(limit=10000)` senza `hide_low_trust`; sul DB di casa 1.403 quarantenati entrano e 5.675 fatti vivi non vengono mai scansionati (tetto silenzioso). Cura: copiare `briefing.py:136` (Tara), l'unico chiamante su 37 che passa `hide_low_trust`; campo `status` nei tool di pulizia. Promessa violata: «kept OUT of default recall».
- **T50** `compute_trust_signal` dà `trusted` a `quarantined`, `orphaned`, `user_belief`, `provisional` (conosce due status su sette); la metrica `hallucination_rate_at_k` eredita.
- **T51** (ex T-MAP-8, Galileo): `update` ritira il fatto vecchio anche quando il gate boccia il nuovo; P1 (l'undo ripara, la maniglia è nella ricevuta); cura: supersessione solo dopo l'ammissione, RED alla porta.
- **T52** `residual_copies` dice dove un fatto cancellato resta leggibile guardando `dreams/` e non `backups/` (visti con 32 e 8.476 fatti).
- **T53** l'iniezione proattiva (`proactive_step_injector`) non porta lo status né il verdetto del fatto iniettato.
- **T54** le SONDE ATTIVE promesse dal README (righe 317-319) non hanno nessuna porta: `active_probe.probe_fact` è testata e nessun tool, comando, metodo, hook o worker la chiama (grep vuoto sull'intero repo).
- Dalle otto: T33 (as_of usato e non dedotto), T38 (test a orologio), T39/T40/T41 (RAM, tokenizer 35 s, rosso Windows), T-MAP-3…7 (Galileo), T31 (il quickstart insegna `verimem health --tools` che non esiste, Iris), i 30/37 `list_facts` in `except: pass` muti (Tara), le cinque funzioni con test verde e nessuna porta (Aldo), la catena dei limiti pagati nei documenti (Corrado).

## 3. Le classi, contate

- **Moduli interi senza chiamante nel prodotto**: 17 nel pacchetto pubblicato (resource_monitor, hot_reload, sos_compensator, recall_usage, codebase_ingest, coding_reflection, betweenness_cache, embedding_quantize, self_curation, temporal_narrative, lab_longmemeval_adapter, parallel_drafter, decay, diversify, fuse_recall, llm_keywords_batch, snapshot_at_time) più `bench_corpus_scale`; più il percorso hopfield del recall e le funzioni pubbliche `is_set_operation`, `group_by_topic_family`, `tag_for_agent`, `filter_facts_by_agent`, `emitted_count`. Decisione da prendere insieme: cablare, spostare sotto `benchmark/`, o togliere.
- **Copie invece della superficie unica**: il filtro degli status nascosti in quattro posti (due senza `user_belief`); `_jaccard` in 18 moduli, `_tokens` in 20; cinque liste bilingui di parole vuote; `_signature` con tre definizioni; tre emivite di «freschezza»; due implementazioni di «vivo a T» (as_of e `snapshot_at_time`); due tool di dedup dei fatti con i nomi incrociati.
- **Docstring che dicono cosa credeva l'autore**: `betweenness_cache` («il worker la chiama»: mai), `decay` («usata dal daemon»: mai), `dentate_gyrus` («non cablata»: lo è), `anomaly_detection` (tre criteri promessi, due applicati), `schema_abstraction` (50% scritto, 40% nel codice), `agent_workload` (`n_episodes` sempre 0).
- **Numeri nei commenti da rimisurare** (Marie: «un numero in un docstring vale meno della metà 42 giorni dopo»): analogy 31/07, proactive_step_injector 19/05, adaptive_threshold (soglia «da rivedere a 5.000» superata tre volte).

## 4. Le tre misure del contratto del rilascio (invariate da ieri)

| misura | oggi | soglia |
|---|---|---|
| fatti scritti e mai serviti | 21% | ≤ 2% |
| composte vere quarantenate | 127 / 177 | ≤ 10 (con le 10 false ferme) |
| scritture MCP non giudicate | la cura di T26a è provata (3/3 con daemon fermo) | 0 |

Nessuna cura è entrata in main oggi; nessun tag. Le cure pronte sui rami aspettano la finestra (T33, T34/T35, T32, T39-T41, T48, T38) e le nuove (T49, T50, T51, T54) aspettano la decisione collegiale.

## 5. Cosa può fare l'utente oggi che ieri non poteva

Niente di nuovo in main oggi: la giornata è stata di mappa, non di cure. Ciò che l'utente ha ricevuto dalla giornata di ieri: as_of sulle porte ordinarie, la supersessione fra fonti diverse, il primo giudizio che parte (3/3), la CI che non riparte sui soli documenti.
