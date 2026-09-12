# `verimem/anti_confab_gate.py` — 3.380 righe, 42 funzioni

**Il file più grande della superficie che presidio, e quello dietro la frase di copertina.**
Mappato sul commit `7b9e8ca1` (origin/main). Ogni numero qui sotto viene da un comando
eseguito su quell'albero; dove il numero è di qualcun altro, è attribuito.

---

## 1. Cosa promette il README, e cosa risponde il codice

Il README vende questo file come *«stops what the source does not support»*. La domanda
che ne nasce è: **chi ferma cosa?** Il codice risponde con **tre famiglie di layer**, non
una:

| famiglia | quanti | cosa guarda | come decide |
|---|---|---|---|
| **L1.x** | 14 sigle (`L1`, `L1.5`, `L1.7`…`L1.21`) | **le parole del claim** | pattern lessicali/semantici — **non guarda la fonte** |
| **L3.x** | 6 sigle (`L3`, `L3-semantic`, `L3-supersession`, `L3-coexistence`, + 2 `-observe`) | **il claim contro i fatti già in memoria** | contraddizione / supersessione |
| **L4.x** | 8 sigle (`L4-grounding`, `L4-negazione`, `L4-relazione`, `L4-review`, `L4-skipped`, `L4.1`, `L4.1-ambiguo`, `L4.2`) | **il claim contro la SUA fonte** | il giudice CE (il «moat») |

🔑 **Solo L4 fa ciò che la frase di copertina descrive.** L1 ferma un claim **senza aver
mai letto la fonte**: giudica come è scritto, non se è sostenuto. Questa non è una critica
al design — L1 esiste per intercettare l'auto-affermazione di un agente, che è la
confabulazione tipica — ma **la frase del README descrive L4 e il lavoro lo fa in
maggioranza L1**.

> Misurato da @ws4 (non riverificato qui): **il 90,2% della quarantena del corpus viene
> dallo screen lessicale e non dal moat — 1728 su 1915.**

---

## 2. ⚠️ `L2` NON ESISTE in questa scala — e il nome è occupato altrove

    grep -rn '"L2' verimem/ --include=*.py
      verimem/anti_confabulation.py:485   f"L2 reconciler: {total} orphan facts found"
      verimem/cli.py:4227                 """L2 reconciler scan: ...
      verimem/mcp_server.py:14422         reason=f"L2 reconciler {cat}: ..."

**Nessuna ricevuta porterà mai `layer: "L2"`.** La numerazione L1→L4 sembra una scala
continua e non lo è: il gradino 2 vive in **un altro modulo** (`anti_confabulation.py` —
nome quasi identico a questo file) e significa **un'altra cosa** (una scansione del corpus
a posteriori, non un layer di scrittura).

⇒ Chi legge `L1.19` e `L3-semantic` in una ricevuta e cerca «cos'è L2» non trova un layer:
trova un reconciler. **Due file omonimi e una scala con un buco al centro** sono due
inciampi per chi legge, e non costano niente da documentare.

---

## 3. I 14 detector di L1 — riga per riga, cosa fermano

Tutti nella stessa funzione (righe 1477-1690), tutti sulla **forma del claim**:

| layer | riga | ferma un claim che dice… |
|---|---|---|
| `L1.8` | 1477 | parola-spia generica (struttura Warning con `advice`) |
| `L1.9` | 1492 | **prestazione** senza bench (`lacks bench evidence`) |
| `L1.10` | 1509 | «funziona / confermato» |
| `L1.11` | 1524 | «production-ready / stabile» |
| `L1.12` | 1540 | «sicuro / hardened» |
| `L1.13` | 1557 | «completato» |
| `L1.14` | 1573 | «documentato» |
| `L1.15` | 1588 | «testato / verificato» |
| `L1.16` | 1603 | «approvato» |
| `L1.17` | 1619 | «monitorato / osservato» |
| `L1.18` | 1635 | «automatizzato / schedulato» |
| `L1.19` | 1653 | **numero assoluto** senza fonte di misura (`lacks measurement`) |
| `L1.20` | ~1690 | auto-affermazione **semantica multilingue** (chiude il buco «8 lingue su 10» delle famiglie EN/IT) |
| `L1.21` | 1677 | (da mappare nel giro 2) |

📌 **La forma di dodici di questi è la stessa** — «cycle 2026-05-27 round 1..11»: sono
nati in un pomeriggio come famiglia di parole chiave. `L1.20` è l'unico semantico, ed è
nato perché la famiglia lessicale **non copriva 8 lingue su 10**.

---

## 4. I quattro `L4-skipped`, cioè i quattro modi di NON giudicare

Righe 1907, 1944, 1954, 1963 — e le loro `reason` sono diverse di proposito:

    1907  source provided but the grounding judge was still …   (warming)
    1944  source provided but the grounding judge failed to …   (failed, in processo)
    1954  source provided but the grounding judge failed to load - …
    1963  source provided but no grounding judge is available - …

⇒ **Quattro stati distinti**, perché mandano chi legge a fare cose diverse. È l'unico punto
del file dove l'assenza di un verdetto viene raccontata invece che taciuta — e nella
ricevuta della porta MCP quella distinzione arriva (vedi `mcp_server` nel giro 2).

---

## 5. Le 42 funzioni — dove sono e cosa presidiano

Il conteggio della superficie combacia col mandato: **3.380 righe, 42 funzioni**
(`ast`, non grep). Il dettaglio funzione-per-funzione è il **giro 2** di questo file:
qui è mappata la struttura che serve a leggere una ricevuta.

---

## 6. Quello che questa mappa NON dice ancora — dichiarato

- **`L1.21` e `L1.5`/`L1.7`**: le sigle esistono, la riga `L1|L1.5|L1.7|L3` a 356 le
  raggruppa, ma **non ho ancora letto cosa fermano**. Giro 2.
- **La precisione di ciascun detector**: non misurata qui. Il team ha un numero
  complessivo per L1 (~40%, @ws1/@ws4) ma **non per singolo layer**, e senza quello non si
  sa quale dei 14 produce i falsi positivi.
- **Se ogni layer emesso sia raggiungibile**: nessuna prova che tutti e 28 possano
  accendersi davvero su un input reale. Un layer irraggiungibile sarebbe indistinguibile
  da uno che non scatta mai.

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`. I comandi che producono ogni tabella sono nel testo.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/anti_confab_gate.py` — 45 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/anti_confab_gate.py:175` `_graded_admission` | funzione: Env switch ``ENGRAM_GRADED_ADMISSION`` (DEFAULT OFF — design bf5d322 | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/anti_confab_gate.py:191` `_l1_domain_precision` | funzione: Env ``ENGRAM_L1_DOMAIN_PRECISION`` — **DEFAULT ON** (flipped 2026-07-22 by | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 3 | `verimem/anti_confab_gate.py:209` `_is_domain_professional_fact` | funzione: Thin, fail-soft wrapper: a classifier import/logic fault must never crash | `verimem/anti_confab_gate.py` | `tests/test_il_soggetto_IT_senza_aprire_le_selfclaim.py` | NON MISURATO |
| 4 | `verimem/anti_confab_gate.py:223` `_is_advisory_layer` | funzione: An ``*-observe`` layer (``L3-semantic-observe``, ``SOURCE_TRUST-observe``) is an | `verimem/anti_confab_gate.py`; `verimem/client.py` (+1) | `tests/test_graded_admission_supersession.py`; `tests/test_l1_domain_advisory_receipt.py` (+2) | NON MISURATO |
| 5 | `verimem/anti_confab_gate.py:258` `advisory_eligible` | funzione: True iff EVERY warning is from the L1 lexical family. | `verimem/anti_confab_gate.py` | `tests/test_gate_independence_observe.py`; `tests/test_un_marcatore_di_osservazione_non_chiude_la_via_di_ammissione.py` | NON MISURATO |
| 6 | `verimem/anti_confab_gate.py:281` `_p0_independence_enforced` | funzione: ENGRAM_P0_INDEPENDENCE — DEFAULT OFF (observe-first). | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 7 | `verimem/anti_confab_gate.py:294` `_l1_domain_advisory` | funzione: SERVER-SIDE, deployment-level switch (env ``ENGRAM_L1_DOMAIN_ADVISORY``, | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 8 | `verimem/anti_confab_gate.py:331` `_SemanticLike` | classe | `verimem/anti_confab_gate.py`; `verimem/validate_claim.py` | **nessuno** | NON MISURATO |
| 9 | `verimem/anti_confab_gate.py:332` `_SemanticLike.search_facts` | funzione | `verimem/cli.py`; `verimem/client.py` (+3) | `tests/test_anti_confab_gate.py`; `tests/test_due_domande_diverse_stessa_risposta.py` (+13) | NON MISURATO |
| 10 | `verimem/anti_confab_gate.py:337` `_AgentLike` | classe | `verimem/anti_confab_gate.py`; `verimem/validate_claim.py` | **nessuno** | NON MISURATO |
| 11 | `verimem/anti_confab_gate.py:342` `GateResult` | classe: Outcome of one gate evaluation. | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` | `tests/test_abstention_hybrid.py`; `tests/test_grounding_gate.py` (+3) | NON MISURATO |
| 12 | `verimem/anti_confab_gate.py:394` `GateResult.to_dict` | funzione | `verimem/cli.py`; `verimem/compilation.py` (+7) | `tests/test_bayesian_gates.py`; `tests/test_compilation.py` (+10) | NON MISURATO |
| 13 | `verimem/anti_confab_gate.py:407` `_resolve_level` | funzione: Normalize the requested level, falling back to env then ``"fast"``. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 14 | `verimem/anti_confab_gate.py:423` `_resolve_mode` | funzione: Normalize the requested gate mode; unknown values → ``"downgrade"``. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 15 | `verimem/anti_confab_gate.py:432` `_grounding_write_on` | funzione: Whether the opt-in SEMANTIC write-path grounding check (L4) is enabled. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 16 | `verimem/anti_confab_gate.py:439` `_semantic_conflict_mode` | funzione: Mode of the opt-in NLI semantic-contradiction moat (L3-semantic): one of | `verimem/anti_confab_gate.py` | `tests/test_nli_auto_enable.py` | NON MISURATO |
| 17 | `verimem/anti_confab_gate.py:474` `_semantic_conflict_on` | funzione: Back-compat: the L3-semantic moat is active (observe OR enforce). | **nessuno** | **nessuno** | MAI CHIAMATA |
| 18 | `verimem/anti_confab_gate.py:479` `_l3_subject_filter` | funzione: ENGRAM_L3_SUBJECT_FILTER — **DEFAULT ON** (flipped 2026-07-22 with the | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 19 | `verimem/anti_confab_gate.py:493` `_puo_essere_una_evoluzione` | funzione: Due fatti possono essere l'uno l'aggiornamento dell'altro? | `verimem/anti_confab_gate.py` | `tests/test_due_misure_diverse_non_sono_un_aggiornamento.py`; `tests/test_il_criterio_dichiara_quando_non_sa_leggere.py` (+3) | NON MISURATO |
| 20 | `verimem/anti_confab_gate.py:632` `_supersede_same_source_on` | funzione: When a clash is a same-source EVOLUTION (the source restating its own value with a | `verimem/anti_confab_gate.py` | `tests/test_il_nome_del_prodotto_funziona_davvero.py`; `tests/test_supersession_multiwriter.py` | NON MISURATO |
| 21 | `verimem/anti_confab_gate.py:673` `_senza_source_contro_groundato` | funzione: GATE (a) del tag 0.7.5 — mandato del 2026-08-20 19:48: | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 22 | `verimem/anti_confab_gate.py:702` `_route_evolutions` | funzione: Partition contradicting OLD fact ids into EVOLUTIONS (same canonical source + | `verimem/anti_confab_gate.py` | `tests/test_gate_semantic_conflict_wire.py`; `tests/test_reference_not_evolution.py` | NON MISURATO |
| 23 | `verimem/anti_confab_gate.py:859` `_record_numerati` | funzione: ``{etichetta: {numeri}}`` per le sole parole di ``vocabolario``. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 24 | `verimem/anti_confab_gate.py:869` `_numeri_disgiunti` | funzione: Le due frasi usano le stesse etichette di ``vocabolario`` con numeri che | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 25 | `verimem/anti_confab_gate.py:877` `_stesso_scheletro` | funzione: Le due frasi sono identiche una volta tolti i numeri. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 26 | `verimem/anti_confab_gate.py:886` `_stesso_scheletro._s` | funzione | `verimem/anti_confab_gate.py`; `verimem/mcp_server.py` (+2) | `tests/security/test_encode_service_auth.py`; `tests/test_causal_extract.py` (+3) | NON MISURATO |
| 27 | `verimem/anti_confab_gate.py:891` `_record_numerati_diversi` | funzione: Le due frasi numerano lo STESSO tipo di record con numeri DISGIUNTI. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 28 | `verimem/anti_confab_gate.py:997` `_parole_vuote_iniziali` | funzione | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 29 | `verimem/anti_confab_gate.py:1053` `_proposizione_di` | funzione: La proposizione di un fatto, o la stringa stessa se ne riceve una. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 30 | `verimem/anti_confab_gate.py:1087` `_entita_diverse` | funzione: I due fatti nominano record DIVERSI: non c'è un codice in comune. | `verimem/anti_confab_gate.py` | `tests/test_aperture_e_lato_solo.py`; `tests/test_due_grandezze_diverse_non_si_aggiornano.py` (+7) | NON MISURATO |
| 31 | `verimem/anti_confab_gate.py:1295` `_entita_diverse._proper` | funzione: Le ISTANZE nominate dal fatto, piu' il soggetto che apre la frase. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 32 | `verimem/anti_confab_gate.py:1371` `_live_topic_siblings` | funzione: Same-topic, LIVE facts to compare a new write against for semantic | `verimem/anti_confab_gate.py` | `tests/test_live_topic_siblings.py` | NON MISURATO |
| 33 | `verimem/anti_confab_gate.py:1412` `_is_honest_reported` | funzione: True iff the proposition is BOTH third-party-attributed reported speech | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 34 | `verimem/anti_confab_gate.py:1424` `_l1_warnings` | funzione: Run the L1 family detectors; return one warning dict per positive. | `verimem/admission_cleanup.py`; `verimem/anti_confab_gate.py` | `tests/test_la_negazione_vale_per_tutti_i_detector.py` | NON MISURATO |
| 35 | `verimem/anti_confab_gate.py:1736` `_e_una_smentita` | funzione: Il warning nasce da una parola che nel testo e' NEGATA? | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 36 | `verimem/anti_confab_gate.py:1747` `_l3_check` | funzione: Run cycle #70 ``validate_claim`` against ``agent.semantic``. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 37 | `verimem/anti_confab_gate.py:1817` `_has_dev_context` | funzione: True if the proposition carries a software/dev artifact signal. | `verimem/admission_cleanup.py`; `verimem/anti_confab_gate.py` (+1) | `tests/test_gate_large_input_perf.py`; `tests/test_redos_sweep.py` | NON MISURATO |
| 38 | `verimem/anti_confab_gate.py:1847` `_has_personal_context` | funzione: True if the proposition reads as a personal/everyday fact (first-person or a | `verimem/admission_cleanup.py`; `verimem/anti_confab_gate.py` | `tests/test_gate_large_input_perf.py`; `tests/test_personal_context_homonyms.py` (+1) | NON MISURATO |
| 39 | `verimem/anti_confab_gate.py:1873` `_is_historical_completion` | funzione: True if the proposition is a passive completion/creation statement anchored to a | `verimem/anti_confab_gate.py` | `tests/test_gate_large_input_perf.py` | NON MISURATO |
| 40 | `verimem/anti_confab_gate.py:1887` `_advisory_l4_skipped` | funzione: L'avviso che finisce nella provenance di un write sourced NON giudicato. | `verimem/anti_confab_gate.py` | `tests/test_due_righe_della_stessa_ricevuta_si_contraddicevano.py`; `tests/test_il_giudice_dice_se_sta_scaldando.py` | NON MISURATO |
| 41 | `verimem/anti_confab_gate.py:1982` `run_validation_gate` | funzione: Evaluate the anti-confab gate; return a ``GateResult``. | `verimem/cli.py`; `verimem/client.py` (+4) | `tests/test_anti_confab_gate_l110_wire.py`; `tests/test_anti_confab_gate_l18_wire.py` (+47) | NON MISURATO |
| 42 | `verimem/anti_confab_gate.py:2240` `run_validation_gate._keep` | funzione | `verimem/anti_confab_gate.py`; `verimem/auto_dream_worker.py` | **nessuno** | NON MISURATO |
| 43 | `verimem/anti_confab_gate.py:2588` `run_validation_gate._emit_l4_skipped` | funzione | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 44 | `verimem/anti_confab_gate.py:3283` `run_validation_gate._attribuzione_da_suggerire` | funzione: La strada che il gate CONOSCE e non diceva a chi ne ha bisogno. | `verimem/anti_confab_gate.py` | **nessuno** | NON MISURATO |
| 45 | `verimem/anti_confab_gate.py:3308` `run_validation_gate._mk` | funzione | `verimem/anti_confab_gate.py` | `tests/test_auto_dream_retention.py`; `tests/test_document_index.py` (+7) | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





