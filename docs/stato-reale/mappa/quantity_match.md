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
c'è un esempio: la mia aspettativa su `distinct_event_indices` era sbagliata, non
la funzione. Quando succede si scrive NON MISURATO e si va a leggere, invece di
aprire un ticket contro il codice.

## Stato di stanotte (2026-09-08, 20:41)

```
  voci elencate con l'AST        47 / 47
  misurate con un comando         4
  di cui FUNZIONA COME PROMESSO   3
  di cui NON MISURATO (da leggere) 1  (distinct_event_indices)
  restanti NON MISURATO           43
```

**Ordine scelto**: prima le **pubbliche** (20 su 47), perché sono la superficie
che il gate importa; dentro le pubbliche, prima quelle che `anti_confab_gate.py`
chiama esplicitamente (lette a `anti_confab_gate.py:940` e `:1155`).

# verimem/quantity_match.py — 47 fra funzioni e classi

| # | funzione (file:riga) | cosa promette | chiamata da | test | claim | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `def _senza_coda_verbale_giapponese` (verimem/quantity_match.py:368, 44 righe) | «480パレット**あります**» e «320パレット**です**» misurano la stessa cosa. |  |  |  | NON MISURATO |  |
| 2 | `def norm_unit` (verimem/quantity_match.py:414, 67 righe) | Canonicalise a unit word (synonyms + plural/`-ies` singularisation). |  |  |  | NON MISURATO |  |
| 3 | `def _inside_brackets` (verimem/quantity_match.py:531, 16 righe) | True when *pos* sits inside a bracket opened earlier and not yet closed. |  |  |  | NON MISURATO |  |
| 4 | `def _opens_a_section` (verimem/quantity_match.py:549, 19 righe) | True when what precedes a marker ends a SECTION rather than a phrase. |  |  |  | NON MISURATO |  |
| 5 | `def claim_span` (verimem/quantity_match.py:570, 17 righe) | The asserting part of *text*: everything before a provenance marker that |  |  |  | NON MISURATO |  |
| 6 | `def _e_una_forma_elisa` (verimem/quantity_match.py:600, 33 righe) | La presunta unita' che finisce a *fine_unita* e' il moncone di una parola |  |  |  | NON MISURATO |  |
| 7 | `def _nomi_di_mese` (verimem/quantity_match.py:646, 20 righe) | I nomi di mese, PRESI DA `temporal_context` invece che ricopiati qui. |  |  |  | NON MISURATO |  |
| 8 | `def _introdotto_da_una_parola_temporale` (verimem/quantity_match.py:671, 36 righe) | Il numero a quattro cifre che comincia a *inizio_numero* e' una DATA |  |  |  | NON MISURATO |  |
| 9 | `def numeri_ambigui` (verimem/quantity_match.py:801, 43 righe) | I numeri del claim che NON abbiamo potuto misurare, come sono scritti. |  |  |  | NON MISURATO |  |
| 10 | `def _identificatori_disgiunti` (verimem/quantity_match.py:1003, 37 righe) | Entrambi i testi portano un codice di record, e non ne condividono nemmeno uno? |  |  |  | NON MISURATO |  |
| 11 | `def _senza_identificatori` (verimem/quantity_match.py:1042, 10 righe) | Il testo con i codici di record sostituiti da SPAZI. |  |  |  | NON MISURATO |  |
| 12 | `def _spans_dei_riferimenti` (verimem/quantity_match.py:1082, 9 righe) | Gli intervalli occupati dal NUMERO di un riferimento a una sezione. |  |  |  | NON MISURATO |  |
| 13 | `def _spans_delle_date` (verimem/quantity_match.py:1093, 10 righe) | Gli intervalli occupati da una data, per saltarli IN BLOCCO. |  |  |  | NON MISURATO |  |
| 14 | `def extract_quantities` (verimem/quantity_match.py:1105, 90 righe) | Extract ``(unit_norm, value)`` pairs from t | `anti_confab_gate.py:1155` (import letto) | `tests/test_contro_e_vs_non_sono_unita_di_misura.py`, `tests/test_due_grandezze_diverse_non_si_aggiornano.py` | «stops what the source does not support» | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: `"233 scritture … 43"` -> `{('scritture',233.0),('',43.0)}` · `"746 MB"` -> `{('mb',746.0)}` · testo senza numeri -> `set()` |
| 15 | `def _classe_dei_segni` (verimem/quantity_match.py:1231, 29 righe) | I combining mark, CHIESTI A UNICODE invece che elencati a mano. |  |  |  | NON MISURATO |  |
| 16 | `def _senza_diacritici` (verimem/quantity_match.py:1286, 43 righe) | «città» -> «citta»: la stessa parola, una grafia sola. |  |  |  | NON MISURATO |  |
| 17 | `def _bigrammi_cjk` (verimem/quantity_match.py:1358, 42 righe) | I bigrammi di caratteri delle scritture senza parole separate. |  |  |  | NON MISURATO |  |
| 18 | `def content_tokens` (verimem/quantity_match.py:1402, 29 righe) | Lower-cased alpha tokens >=4 chars minus fille | `anti_confab_gate.py:1155` (import letto) | `tests/test_gli_accenti_spezzavano_le_parole_italiane.py`, `tests/test_due_opposti_non_possono_vivere_insieme.py` | «stops what the source does not support» | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: `"Il gate ha ammesso 233 scritture"` -> `['ammesso','gate','scritture']` (numeri e parole <4 esclusi) · `"a be see"` -> `[]` |
| 19 | `def _min_shared_ratio` (verimem/quantity_match.py:1433, 59 righe) | Quanta parte della frase PIU' POVERA deve essere condivisa perche' due |  |  |  | NON MISURATO |  |
| 20 | `def _shared_enough` (verimem/quantity_match.py:1494, 13 righe) | I token condivisi sono una frazione sufficiente della frase piu' povera? |  |  |  | NON MISURATO |  |
| 21 | `def contrasting_attrs` (verimem/quantity_match.py:1509, 8 righe) | True if the two token sets describe DIFFERENT | `anti_confab_gate.py:1155` (import letto) | `tests/test_il_mensile_non_cancella_l_annuale.py`, `tests/test_due_opposti_non_possono_vivere_insieme.py` | «stops what the source does not support» | **FUNZIONA COME PROMESSO** | eseguita 08/09 20:40: grande/piccolo -> `True` · grande/grande -> `False` |
| 22 | `def distinctive_tokens` (verimem/quantity_match.py:1519, 4 righe) | Content tokens minus the statement's own unit words (the 'subject'). |  |  |  | NON MISURATO |  |
| 23 | `def conflict_from_parts` (verimem/quantity_match.py:1525, 39 righe) | Core numeric-conflict check on PRE-COMPUTED quantities/content tokens. |  |  |  | NON MISURATO |  |
| 24 | `def agreement_from_parts` (verimem/quantity_match.py:1566, 26 righe) | Twin of :func:`conflict_from_parts` — returns ``(unit, value)`` when a |  |  |  | NON MISURATO |  |
| 25 | `def numeric_conflict` (verimem/quantity_match.py:1594, 22 righe) | Return ``(unit, value_a, value_b)`` if *text_a* and *text_b* state a |  |  |  | NON MISURATO |  |
| 26 | `def extract_versions` (verimem/quantity_match.py:1675, 6 righe) | Version strings in *text*, normalised without the ``v`` prefix. |  |  |  | NON MISURATO |  |
| 27 | `def _nomi_propri` (verimem/quantity_match.py:1693, 55 righe) | Le parole maiuscole di *testo* che sono davvero NOMI PROPRI. |  |  |  | NON MISURATO |  |
| 28 | `def _named_subjects_disjoint` (verimem/quantity_match.py:1750, 7 righe) | True when BOTH statements name capitalized subjects and the two sets |  |  |  | NON MISURATO |  |
| 29 | `def version_conflict` (verimem/quantity_match.py:1759, 15 righe) | ``(version_a, version_b)`` if the two statements pin DIFFERENT versions |  |  |  | NON MISURATO |  |
| 30 | `def extract_dates` (verimem/quantity_match.py:1804, 33 righe) | ``(year, month, day)`` tuples from ISO dates and month names. |  |  |  | NON MISURATO |  |
| 31 | `def date_conflict` (verimem/quantity_match.py:1839, 26 righe) | A sub-year date move about the same subject: same (or unstated) year |  |  |  | NON MISURATO |  |
| 32 | `def _has_negator` (verimem/quantity_match.py:1950, 2 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 33 | `def _negated_tokens` (verimem/quantity_match.py:1954, 64 righe) | Content words in the negator's SCOPE: the first 1-2 alpha tokens right |  |  |  | NON MISURATO |  |
| 34 | `def _scope_a_ritroso` (verimem/quantity_match.py:2025, 43 righe) | Ciò che il negatore nega quando sta **in coda alla frase**. |  |  |  | NON MISURATO |  |
| 35 | `def _senza_negatori` (verimem/quantity_match.py:2070, 29 righe) | Il testo senza i negatori, per confrontare le due frasi «a parità di |  |  |  | NON MISURATO |  |
| 36 | `def _via` (verimem/quantity_match.py:2094, 4 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 37 | `def _e_prevalentemente_cjk` (verimem/quantity_match.py:2101, 8 righe) | Vero se il testo è per lo più han/kana, cioè privo di spazi fra le parole. |  |  |  | NON MISURATO |  |
| 38 | `def _token_di_confronto` (verimem/quantity_match.py:2115, 27 righe) | I token con cui :func:`negation_conflict` confronta DUE frasi. |  |  |  | NON MISURATO |  |
| 39 | `def negation_conflict` (verimem/quantity_match.py:2144, 107 righe) | The shared predicate token when *text_a*/*text_b* state the SAME thing |  |  |  | NON MISURATO |  |
| 40 | `def _piu_leggibile` (verimem/quantity_match.py:2253, 21 righe) | Il token da MOSTRARE quando il negatore non ha uno scope proprio. |  |  |  | NON MISURATO |  |
| 41 | `def lexical_conflict` (verimem/quantity_match.py:2276, 20 righe) | First lexical conflict between two statements as ``(kind, detail)`` — |  |  |  | NON MISURATO |  |
| 42 | `def _bare_numbers` (verimem/quantity_match.py:2363, 5 righe) | Numbers in *text* that carry NO unit — the ones eligible to be indices. |  |  |  | NON MISURATO |  |
| 43 | `def event_indices` (verimem/quantity_match.py:2370, 24 righe) | ``(kind, n)`` indices in the CLAIM part of *text*: ordinals ("day 4" -> |  |  |  | NON MISURATO |  |
| 44 | `def _indices_disjoint` (verimem/quantity_match.py:2410, 37 righe) | Core of :func:`distinct_event_indices` on PRE-COMPUTED index sets, so the |  |  |  | NON MISURATO |  |
| 45 | `def indexed_vs_unindexed` (verimem/quantity_match.py:2449, 17 righe) | True when ONE statement names indexed subjects and the other names none. |  |  |  | NON MISURATO |  |
| 46 | `def distinct_event_indices` (verimem/quantity_match.py:2468, 6 righe) | True when the two statements index DIFFE | `anti_confab_gate.py:940` (import letto) | `tests/test_quantity_match.py`, `tests/test_entity_index_not_measure.py` | «stops what the source does not support» | **NON MISURATO** | eseguita 08/09 20:40: «il primo tentativo» vs «il secondo tentativo» -> `False`, dove mi aspettavo `True`. ⚠️ L'ASPETTATIVA E' MIA E PUO' ESSERE FUORI DOMINIO: `anti_confab_gate.py:844` dice che gli indici di evento sono un elenco di 60+ parole, e non ho ancora letto se «primo/secondo» ci siano. Verdetto sospeso finche' non leggo `_EVENT_INDEX_RE`. |
| 47 | `def valori_scritti_a_parole` (verimem/quantity_match.py:2513, 14 righe) | I numeri che il testo scrive a PAROLE, non in cifra. |  |  |  | NON MISURATO |  |
