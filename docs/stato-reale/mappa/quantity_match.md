# verimem/quantity_match.py — mappa

**Owner**: ws4 (Nadia Ferro) · **2.551 righe · 47 fra funzioni e classi** · file 1 di 22.

**Claim del README che questo file serve**: «stops what the source does not
support» — è il layer che confronta i NUMERI fra claim e fonte, e una delle tre
misure del contratto di rilascio (`bc86e197`) passa di qui.

## Come è fatta questa tabella, e cosa NON dice

L'elenco delle funzioni è generato con l'**AST**, non con grep: unità intere,
righe di inizio e lunghezza esatte. Le colonne che richiedono di **leggere** e di
**eseguire** si riempiono a mano, una per una.

⚠️ **`NON MISURATO` è un verdetto, non un buco.** Una riga senza il comando che
la prova resta NON MISURATO anche se «si vede» che la funzione va: è la regola 1
del mandato, ed è quella che rende la tabella diversa da una lettura.

⚠️ **Un caso di prova fuori dal dominio della funzione non la falsifica.** Sotto
c'è un esempio: la mia aspettativa su `distinct_event_indices` era sbagliata (tre volte), non
la funzione. Quando succede si scrive NON MISURATO e si va a leggere, invece di
aprire un ticket contro il codice.

## Stato di stanotte (2026-09-08, 21:05)

```
  voci elencate con l'AST        47 / 47
  misurate con un comando         4
  di cui FUNZIONA COME PROMESSO   4
  di cui NON MISURATO             0
  restanti da fare                43
```

📌 **Alle 20:41 la quarta era NON MISURATO** — `distinct_event_indices` dava
`False` dove me lo aspettavo `True`. **Sciolta alle 21:02 leggendo, e la funzione
aveva ragione tre volte su tre**: gli ordinali a parole non sono indici, le
progressioni (`tentativo`, `attempt`) sono escluse di proposito, e «riga 12» vs
«colonna 12» *sono* due cose diverse. La cronaca sta nella riga della tabella,
perché il modo in cui un sospetto si è sgonfiato vale quanto il verdetto.

**Ordine scelto**: prima le **pubbliche** (20 su 47), perché sono la superficie
che il gate importa; dentro le pubbliche, prima quelle che `anti_confab_gate.py`
chiama esplicitamente (lette a `anti_confab_gate.py:940` e `:1155`).


## Nota di metodo (aggiornata alle 20:58)

Le prime due versioni di questo file usavano uno scheletro mio. **Sono state
rigenerate con `scripts/mappa_bozza.py`**, lo strumento comune pubblicato dal
lead alle 20:52: dà più informazione (chiamanti con `file:riga`, test che
nominano il simbolo, righe del README) ed è il formato che
`scripts/mappa_completa.py` sa leggere. Un formato mio avrebbe fatto una
tabella che l'aggregatore non vede.

**Le misure già fatte sono state RIPORTATE, non rifatte**, iniettandole **per
nome** e non per indice: se lo strumento cambia l'ordine delle righe, una
sostituzione per numero metterebbe la prova sulla funzione sbagliata.

⚠️ **I chiamanti in questa tabella vengono da `git grep` e sono CANDIDATI, non
conferme.** Vanno letti uno per uno prima di trasformarli in verdetto: il grep
serve a trovare. E prima di scrivere **MAI CHIAMATA** — che secondo il mandato
porta a proporre una rimozione — va cercato il **nome nudo**, non `nome(`: un
riferimento passato come callback (`head_at=sm.audit_head_at`) non ha parentesi
e non compare. È la trappola che @ws6 ha segnalato alle 20:45 dopo averla quasi
calpestata; su 2.973 funzioni produrrebbe proposte di rimuovere codice vivo.

# Mappa di `verimem/quantity_match.py` — 47 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/quantity_match.py:368` `_senza_coda_verbale_giapponese` | funzione: «480パレット**あります**» e «320パレット**です**» misurano la stessa cosa. | `verimem/quantity_match.py:427` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/quantity_match.py:414` `norm_unit` | funzione: Canonicalise a unit word (synonyms + plural/`-ies` singularisation). | `verimem/quantity_match.py:240`; `verimem/quantity_match.py:392`; `verimem/quantity_match.py:1153` (+9) | `tests/test_il_gate_diceva_supported_alla_frase_negata.py`; `tests/test_l_unita_giapponese_si_portava_dentro_il_verbo.py`; `tests/test_la_versione_si_riconosceva_in_ogni_lingua_tranne_la_nostra.py` (+4) | - | NON MISURATO | - |
| 3 | `verimem/quantity_match.py:531` `_inside_brackets` | funzione: True when *pos* sits inside a bracket opened earlier and not yet closed. | `verimem/quantity_match.py:578` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/quantity_match.py:549` `_opens_a_section` | funzione: True when what precedes a marker ends a SECTION rather than a phrase. | `verimem/quantity_match.py:583` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/quantity_match.py:570` `claim_span` | funzione: The asserting part of *text*: everything before a provenance marker that | `verimem/quantity_match.py:822`; `verimem/quantity_match.py:1116`; `verimem/quantity_match.py:1139` (+5) | `tests/test_la_fonte_si_legge_intera.py`; `tests/test_proof_beats_opinion.py` | - | NON MISURATO | - |
| 6 | `verimem/quantity_match.py:600` `_e_una_forma_elisa` | funzione: La presunta unita' che finisce a *fine_unita* e' il moncone di una parola | `verimem/quantity_match.py:1148` | nessuno | - | NON MISURATO | - |
| 7 | `verimem/quantity_match.py:646` `_nomi_di_mese` | funzione: I nomi di mese, PRESI DA `temporal_context` invece che ricopiati qui. | `verimem/quantity_match.py:706` | nessuno | - | NON MISURATO | - |
| 8 | `verimem/quantity_match.py:671` `_introdotto_da_una_parola_temporale` | funzione: Il numero a quattro cifre che comincia a *inizio_numero* e' una DATA | `verimem/quantity_match.py:861`; `verimem/quantity_match.py:935`; `verimem/quantity_match.py:1172` | `tests/test_l_anno_di_una_data_non_e_una_quantita.py` | - | NON MISURATO | - |
| 9 | `verimem/quantity_match.py:801` `numeri_ambigui` | funzione: I numeri del claim che NON abbiamo potuto misurare, come sono scritti. | `verimem/anti_confab_gate.py:2696`; `verimem/anti_confab_gate.py:2697`; `verimem/evidence_requirement.py:24` (+4) | `tests/test_il_gate_certificava_un_numero_falso_di_mille_volte.py`; `tests/test_l41_confronta_i_numeri_come_testo.py` | - | NON MISURATO | - |
| 10 | `verimem/quantity_match.py:1003` `_identificatori_disgiunti` | funzione: Entrambi i testi portano un codice di record, e non ne condividono nemmeno uno? | `verimem/quantity_match.py:998`; `verimem/quantity_match.py:1609` | `tests/test_un_codice_non_e_una_quantita.py`; `tests/test_un_codice_non_e_una_quantita_in_nessuna_lingua.py` | - | NON MISURATO | - |
| 11 | `verimem/quantity_match.py:1042` `_senza_identificatori` | funzione: Il testo con i codici di record sostituiti da SPAZI. | `verimem/quantity_match.py:1007`; `verimem/quantity_match.py:1119`; `verimem/quantity_match.py:1139` | `tests/test_la_fonte_si_legge_intera.py`; `tests/test_un_codice_non_e_una_quantita.py`; `tests/test_un_codice_non_e_una_quantita_in_nessuna_lingua.py` | - | NON MISURATO | - |
| 12 | `verimem/quantity_match.py:1082` `_spans_dei_riferimenti` | funzione: Gli intervalli occupati dal NUMERO di un riferimento a una sezione. | `verimem/quantity_match.py:1122`; `verimem/quantity_match.py:1143` | nessuno | - | NON MISURATO | - |
| 13 | `verimem/quantity_match.py:1093` `_spans_delle_date` | funzione: Gli intervalli occupati da una data, per saltarli IN BLOCCO. | `verimem/quantity_match.py:1047`; `verimem/quantity_match.py:1085`; `verimem/quantity_match.py:1138` (+1) | nessuno | - | NON MISURATO | - |
| 14 | `verimem/quantity_match.py:1105` `extract_quantities` | funzione: Extract ``(unit_norm, value)`` pairs from the CLAIM part of *text* | `verimem/anti_confab_gate.py:1155`; `verimem/anti_confab_gate.py:1211`; `verimem/anti_confab_gate.py:1228` (+36) | `tests/test_contro_e_vs_non_sono_unita_di_misura.py`; `tests/test_due_fatti_che_si_contraddicono_non_si_confermano.py`; `tests/test_due_grandezze_diverse_non_si_aggiornano.py` (+28) | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: `"233 scritture … 43"` → `{('scritture',233.0),('',43.0)}` · `"746 MB"` → `{('mb',746.0)}` · testo senza numeri → `set()` |
| 15 | `verimem/quantity_match.py:1231` `_classe_dei_segni` | funzione: I combining mark, CHIESTI A UNICODE invece che elencati a mano. | `verimem/quantity_match.py:1283` | `tests/test_le_vocali_indiane_non_erano_lettere.py` | - | NON MISURATO | - |
| 16 | `verimem/quantity_match.py:1286` `_senza_diacritici` | funzione: «città» -> «citta»: la stessa parola, una grafia sola. | `verimem/quantity_match.py:430`; `verimem/quantity_match.py:1166`; `verimem/quantity_match.py:1291` (+3) | `tests/test_l_hangul_usciva_a_pezzi_dalla_normalizzazione.py` | - | NON MISURATO | - |
| 17 | `verimem/quantity_match.py:1358` `_bigrammi_cjk` | funzione: I bigrammi di caratteri delle scritture senza parole separate. | `verimem/quantity_match.py:1412`; `verimem/quantity_match.py:1429` | nessuno | - | NON MISURATO | - |
| 18 | `verimem/quantity_match.py:1402` `content_tokens` | funzione: Lower-cased alpha tokens ≥4 chars minus fillers, lightly singularised. | `verimem/anti_confab_gate.py:1155`; `verimem/anti_confab_gate.py:1203`; `verimem/anti_confab_gate.py:1206` (+33) | `tests/test_due_grandezze_diverse_non_si_aggiornano.py`; `tests/test_due_opposti_non_possono_vivere_insieme.py`; `tests/test_gli_accenti_spezzavano_le_parole_italiane.py` (+12) | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: `"Il gate ha ammesso 233 scritture"` → `['ammesso','gate','scritture']` (numeri e parole <4 esclusi) · `"a be see"` → `[]` |
| 19 | `verimem/quantity_match.py:1433` `_min_shared_ratio` | funzione: Quanta parte della frase PIU' POVERA deve essere condivisa perche' due | `verimem/quantity_match.py:1500` | nessuno | - | NON MISURATO | - |
| 20 | `verimem/quantity_match.py:1494` `_shared_enough` | funzione: I token condivisi sono una frazione sufficiente della frase piu' povera? | `verimem/anti_confab_gate.py:622`; `verimem/anti_confab_gate.py:628`; `verimem/anti_confab_gate.py:629` (+1) | `tests/test_su_prosa_lunga_due_parole_non_sono_un_aggiornamento.py` | - | NON MISURATO | - |
| 21 | `verimem/quantity_match.py:1509` `contrasting_attrs` | funzione: True if the two token sets describe DIFFERENT attributes — each holds | `verimem/anti_confab_gate.py:1155`; `verimem/anti_confab_gate.py:1199`; `verimem/anti_confab_gate.py:1203` (+10) | `tests/test_due_grandezze_diverse_non_si_aggiornano.py`; `tests/test_due_opposti_non_possono_vivere_insieme.py`; `tests/test_il_mensile_non_cancella_l_annuale.py` | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: grande/piccolo → `True` · grande/grande → `False` |
| 22 | `verimem/quantity_match.py:1519` `distinctive_tokens` | funzione: Content tokens minus the statement's own unit words (the 'subject'). | `verimem/quantity_match.py:1766`; `verimem/quantity_match.py:1849`; `verimem/quantity_match.py:2538` | `tests/test_un_token_su_cento_non_e_lo_stesso_soggetto.py` | - | NON MISURATO | - |
| 23 | `verimem/quantity_match.py:1525` `conflict_from_parts` | funzione: Core numeric-conflict check on PRE-COMPUTED quantities/content tokens. | `verimem/facts_conflict.py:49`; `verimem/quantity_match.py:1570`; `verimem/quantity_match.py:1611` (+5) | `tests/test_un_token_su_cento_non_e_lo_stesso_soggetto.py` | - | NON MISURATO | - |
| 24 | `verimem/quantity_match.py:1566` `agreement_from_parts` | funzione: Twin of :func:`conflict_from_parts` — returns ``(unit, value)`` when a | `verimem/corroboration.py:28`; `verimem/corroboration.py:110`; `verimem/validate_claim.py:28` | nessuno | - | NON MISURATO | - |
| 25 | `verimem/quantity_match.py:1594` `numeric_conflict` | funzione: Return ``(unit, value_a, value_b)`` if *text_a* and *text_b* state a | `verimem/quantity_match.py:128`; `verimem/quantity_match.py:376`; `verimem/quantity_match.py:955` (+7) | `tests/test_entity_index_not_measure.py`; `tests/test_exclusive_words_mean_other_subject.py`; `tests/test_l_hangul_usciva_a_pezzi_dalla_normalizzazione.py` (+12) | - | NON MISURATO | - |
| 26 | `verimem/quantity_match.py:1675` `extract_versions` | funzione: Version strings in *text*, normalised without the ``v`` prefix. | `verimem/facts_conflict.py:488`; `verimem/quantity_match.py:1763`; `verimem/quantity_match.py:2541` (+1) | `tests/test_la_versione_si_riconosceva_in_ogni_lingua_tranne_la_nostra.py`; `tests/test_quantity_match.py`; `tests/test_un_numero_attaccato_a_una_lettera_cinese.py` | - | NON MISURATO | - |
| 27 | `verimem/quantity_match.py:1693` `_nomi_propri` | funzione: Le parole maiuscole di *testo* che sono davvero NOMI PROPRI. | `verimem/quantity_match.py:1754`; `verimem/quantity_match.py:1755` | `tests/test_sul_e_dopo_non_sono_nomi_propri.py` | - | NON MISURATO | - |
| 28 | `verimem/quantity_match.py:1750` `_named_subjects_disjoint` | funzione: True when BOTH statements name capitalized subjects and the two sets | `verimem/quantity_match.py:1769`; `verimem/quantity_match.py:1851` | `tests/test_everyday_memory_survives.py`; `tests/test_sul_e_dopo_non_sono_nomi_propri.py` | - | NON MISURATO | - |
| 29 | `verimem/quantity_match.py:1759` `version_conflict` | funzione: ``(version_a, version_b)`` if the two statements pin DIFFERENT versions | `verimem/anti_confab_gate.py:1201`; `verimem/anti_confab_gate.py:1239`; `verimem/facts_conflict.py:479` (+5) | `tests/test_la_versione_si_riconosceva_in_ogni_lingua_tranne_la_nostra.py`; `tests/test_proof_beats_opinion.py`; `tests/test_quantity_match.py` | - | NON MISURATO | - |
| 30 | `verimem/quantity_match.py:1804` `extract_dates` | funzione: ``(year, month, day)`` tuples from ISO dates and month names. | `verimem/facts_conflict.py:487`; `verimem/quantity_match.py:1846`; `verimem/quantity_match.py:2543` (+1) | `tests/test_audit_peer_and_scan.py`; `tests/test_quantity_match.py` | - | NON MISURATO | - |
| 31 | `verimem/quantity_match.py:1839` `date_conflict` | funzione: A sub-year date move about the same subject: same (or unstated) year | `verimem/facts_conflict.py:480`; `verimem/facts_conflict.py:486`; `verimem/quantity_match.py:2289` (+2) | `tests/test_proof_beats_opinion.py`; `tests/test_quantity_match.py` | - | NON MISURATO | - |
| 32 | `verimem/quantity_match.py:1950` `_has_negator` | funzione: (nessun docstring) | `verimem/contradiction.py:239`; `verimem/contradiction.py:240`; `verimem/local_grounding.py:627` (+2) | `tests/test_due_opposti_non_possono_vivere_insieme.py`; `tests/test_il_gate_conferma_il_contrario_in_tre_lingue.py`; `tests/test_lo_scope_vuoto_non_e_un_via_libera.py` | - | NON MISURATO | - |
| 33 | `verimem/quantity_match.py:1954` `_negated_tokens` | funzione: Content words in the negator's SCOPE: the first 1-2 alpha tokens right | `verimem/quantity_match.py:2028`; `verimem/quantity_match.py:2215`; `verimem/quantity_match.py:2258` | nessuno | - | NON MISURATO | - |
| 34 | `verimem/quantity_match.py:2025` `_scope_a_ritroso` | funzione: Ciò che il negatore nega quando sta **in coda alla frase**. | `verimem/quantity_match.py:2017` | nessuno | - | NON MISURATO | - |
| 35 | `verimem/quantity_match.py:2070` `_senza_negatori` | funzione: Il testo senza i negatori, per confrontare le due frasi «a parità di | `verimem/quantity_match.py:2162`; `verimem/quantity_match.py:2163`; `verimem/quantity_match.py:2268` (+1) | `tests/test_il_flip_giapponese_passa_per_quindici_millesimi.py` | - | NON MISURATO | - |
| 36 | `verimem/quantity_match.py:2094` `_senza_negatori._via` | funzione: (nessun docstring) | `verimem/quantity_match.py:2098` | nessuno | - | NON MISURATO | - |
| 37 | `verimem/quantity_match.py:2101` `_e_prevalentemente_cjk` | funzione: Vero se il testo è per lo più han/kana, cioè privo di spazi fra le parole. | `verimem/quantity_match.py:1332`; `verimem/quantity_match.py:2138`; `verimem/quantity_match.py:2177` (+3) | nessuno | - | NON MISURATO | - |
| 38 | `verimem/quantity_match.py:2115` `_token_di_confronto` | funzione: I token con cui :func:`negation_conflict` confronta DUE frasi. | `verimem/quantity_match.py:2154`; `verimem/quantity_match.py:2162`; `verimem/quantity_match.py:2163` (+1) | `tests/test_il_flip_giapponese_passa_per_quindici_millesimi.py`; `tests/test_il_negatore_cinese_era_in_lista_e_non_scattava.py` | - | NON MISURATO | - |
| 39 | `verimem/quantity_match.py:2144` `negation_conflict` | funzione: The shared predicate token when *text_a*/*text_b* state the SAME thing | `verimem/contradiction.py:47`; `verimem/contradiction.py:339`; `verimem/contradiction.py:345` (+6) | `tests/test_due_opposti_non_possono_vivere_insieme.py`; `tests/test_il_flip_giapponese_passa_per_quindici_millesimi.py`; `tests/test_il_gate_conferma_il_contrario_in_tre_lingue.py` (+5) | - | NON MISURATO | - |
| 40 | `verimem/quantity_match.py:2253` `_piu_leggibile` | funzione: Il token da MOSTRARE quando il negatore non ha uno scope proprio. | `verimem/quantity_match.py:2250` | nessuno | - | NON MISURATO | - |
| 41 | `verimem/quantity_match.py:2276` `lexical_conflict` | funzione: First lexical conflict between two statements as ``(kind, detail)`` — | `verimem/quantity_match.py:1643`; `verimem/quantity_match.py:2546` | `tests/test_il_gate_diceva_supported_alla_frase_negata.py`; `tests/test_la_negazione_vale_anche_in_russo.py` | - | NON MISURATO | - |
| 42 | `verimem/quantity_match.py:2363` `_bare_numbers` | funzione: Numbers in *text* that carry NO unit — the ones eligible to be indices. | `verimem/quantity_match.py:2389` | nessuno | - | NON MISURATO | - |
| 43 | `verimem/quantity_match.py:2370` `event_indices` | funzione: ``(kind, n)`` indices in the CLAIM part of *text*: ordinals ("day 4" -> | `verimem/anti_confab_gate.py:928`; `verimem/quantity_match.py:1537`; `verimem/quantity_match.py:1614` (+4) | `tests/test_entity_index_not_measure.py`; `tests/test_il_posizionale_dipende_dalla_forma_non_dalla_parola.py`; `tests/test_index_regex_no_redos.py` (+1) | - | NON MISURATO | - |
| 44 | `verimem/quantity_match.py:2410` `_indices_disjoint` | funzione: Core of :func:`distinct_event_indices` on PRE-COMPUTED index sets, so the | `verimem/quantity_match.py:1543`; `verimem/quantity_match.py:2473` | `tests/test_entity_index_not_measure.py` | - | NON MISURATO | - |
| 45 | `verimem/quantity_match.py:2449` `indexed_vs_unindexed` | funzione: True when ONE statement names indexed subjects and the other names none. | `verimem/anti_confab_gate.py:2278`; `verimem/anti_confab_gate.py:2293`; `verimem/quantity_match.py:2549` | `tests/test_entity_index_not_measure.py` | - | NON MISURATO | - |
| 46 | `verimem/quantity_match.py:2468` `distinct_event_indices` | funzione: True when the two statements index DIFFERENT things of the same kind | `verimem/anti_confab_gate.py:921`; `verimem/anti_confab_gate.py:940`; `verimem/anti_confab_gate.py:944` (+4) | `tests/test_entity_index_not_measure.py`; `tests/test_identifier_only_as_subject.py`; `tests/test_quantity_match.py` | - | **FUNZIONA COME PROMESSO** | eseguita 08/09 21:02, **6 casi su 6 corretti** una volta capito il dominio: «tentativo 1» vs «tentativo 2» → `False` · «run 3» vs «run 4» → `True` · «riga 12» vs «colonna 12» → `True` · identici → `False`. ⚠️ **TRE MIE ATTESE ERANO SBAGLIATE, NON LA FUNZIONE**, e la lettura le ha chiuse: (a) `_EVENT_INDEX_RE` (:2316) vuole `<parola> <cifra>`, quindi «il PRIMO tentativo» (ordinale a parole) non è un indice — `event_indices` restituisce `set()`; (b) `tentativo` e `attempt` stanno in `_PROGRESSION_KINDS` e sono **esclusi di proposito** («a different stage number is the same subject moving on»), mentre `run` no — ecco perché i due casi divergevano; (c) «riga 12» vs «colonna 12» → `True` è corretto, sono due cose diverse. **Il primo giro (20:40) aveva dato un falso sospetto** |
| 47 | `verimem/quantity_match.py:2513` `valori_scritti_a_parole` | funzione: I numeri che il testo scrive a PAROLE, non in cifra. | `verimem/quantity_match.py:2534`; `verimem/valore_non_nella_fonte.py:53`; `verimem/valore_non_nella_fonte.py:342` | `tests/test_un_numero_che_la_fonte_scrive_a_parole.py` | - | NON MISURATO | - |
