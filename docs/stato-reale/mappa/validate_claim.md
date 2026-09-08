# verimem/validate_claim.py — mappa

**Owner**: ws4 (Nadia Ferro) · **995 righe · 17 fra funzioni e classi** · file 2 di 22.

**Claim del README che questo file serve**: «stops what the source does not
support». È **la porta pubblica** del gate di verifica: `validate_claim` è ciò
che un chiamante esterno invoca, e le sue 433 righe sono la funzione più grande
della mia porzione.

## Stato di stanotte (2026-09-08, 20:48)

```
  voci elencate con l'AST         17 / 17
  misurate con un comando          3
     FUNZIONA COME PROMESSO        2
     NON MISURATO (firma mia sbagliata)  1
  restanti NON MISURATO           14
```

## ⚠️ Due misure mie sono cadute prima di reggere, e sta scritto perché

**Primo giro, tre errori MIEI e nessuno del codice.** Li lascio scritti perché
sono la ragione per cui questa tabella richiede di *eseguire* e non di leggere:

1. a `leggibile_a_maiuscole(text: str)` passavo `"it"`, `"de"`, `"zh"` — **codici
   lingua a una funzione che vuole una FRASE**. Tornava `True` per tutti, e non
   voleva dire niente: il segnale è la **densità di maiuscole**, e il docstring
   dice in tondo che «non nomina nessuna lingua».
2. `similarita_semantica` dava `0.0` **anche su frasi identiche**. Non è un
   difetto: il docstring **promette** 0.0 quando l'encode non è disponibile, e in
   `HIPPO_ENCODE_DELEGATE_ONLY=1` non lo è. ⇒ **stavo misurando il nostro
   ambiente e stavo per attribuirlo al prodotto.** Rifatta con
   `env -u HIPPO_ENCODE_DELEGATE_ONLY`.
3. a `validate_claim` ho passato un oggetto al posto di una stringa: `TypeError`.
   La riga resta **NON MISURATO** finché non leggo la firma — un'eccezione
   causata dal chiamante non dice niente sulla funzione.

🔑 **La regola che ne esce, la terza volta oggi: un caso di prova fuori dominio
non falsifica la funzione.** Prima di scrivere NON COME PROMESSO va escluso che
l'errore sia nel banco.


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

# Mappa di `verimem/validate_claim.py` — 17 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/validate_claim.py:80` `_FactLike` | classe: (nessun docstring) | `verimem/validate_claim.py:91`; `verimem/validate_claim.py:402`; `verimem/validate_claim.py:655` (+5) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/validate_claim.py:88` `_SemanticLike` | classe: (nessun docstring) | `verimem/anti_confab_gate.py:338`; `verimem/validate_claim.py:95` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/validate_claim.py:89` `_SemanticLike.search_facts` | funzione: (nessun docstring) | `verimem/cli.py:3358`; `verimem/client.py:1781`; `verimem/client.py:1789` (+26) | `tests/test_anchor_recall.py`; `tests/test_anti_confab_gate.py`; `tests/test_any_language_ha_un_numero.py` (+38) | - | NON MISURATO | - |
| 4 | `verimem/validate_claim.py:94` `_AgentLike` | classe: (nessun docstring) | `verimem/anti_confab_gate.py:1748`; `verimem/anti_confab_gate.py:1987`; `verimem/validate_claim.py:563` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/validate_claim.py:98` `_unita_non_allineabili` | funzione: Vero quando le due frasi misurano grandezze DIVERSE, non la stessa in | `verimem/validate_claim.py:881` | nessuno | - | NON MISURATO | - |
| 6 | `verimem/validate_claim.py:134` `_extract_salients` | funzione: Estrae (capitalized_names, years) dalla stringa. | `verimem/validate_claim.py:358`; `verimem/validate_claim.py:361`; `verimem/validate_claim.py:597` (+2) | `tests/test_il_codice_non_era_un_termine_di_ricerca.py`; `tests/test_trust_dichiara_cio_che_ha_girato.py`; `tests/test_una_negazione_urlata_non_e_un_nome_proprio.py` | - | NON MISURATO | - |
| 7 | `verimem/validate_claim.py:146` `_termine_presente` | funzione: Il termine come PAROLA INTERA, non come sottostringa. | `verimem/validate_claim.py:440`; `verimem/validate_claim.py:479`; `verimem/validate_claim.py:523` | nessuno | - | NON MISURATO | - |
| 8 | `verimem/validate_claim.py:194` `leggibile_a_maiuscole` | funzione: Il riconoscimento dei nomi propri per MAIUSCOLA funziona su questa frase? | `verimem/anti_confab_gate.py:556`; `verimem/anti_confab_gate.py:580`; `verimem/validate_claim.py:509` | `tests/test_il_gate_puo_solo_bocciare_in_tre_lingue.py` | - | **FUNZIONA COME PROMESSO** per il caso che cura | eseguita 08/09 20:46 con FRASI (non codici lingua): it `True` · en `True` · de `False` ×2 (uno è l'esempio del docstring) · **zh `True`**. ⚠️ Il cinese risponde `True` a una domanda che lì non si applica (nessuna maiuscola da riconoscere): **NON apro un T**, il difetto è già misurato con la causa alla riga in `test_il_gate_puo_solo_bocciare_in_tre_lingue.py` (`_CAPS_RE` guarda le maiuscole latine ASCII ⇒ RU/ZH/JA danno `unknown`). Questa riga ne è una conseguenza |
| 9 | `verimem/validate_claim.py:249` `similarita_semantica` | funzione: Quanto due frasi parlano della stessa cosa, in QUALUNQUE lingua. | `verimem/anti_confab_gate.py:557`; `verimem/anti_confab_gate.py:581` | `tests/test_le_lingue_non_coperte_hanno_un_motore.py` | - | **FUNZIONA COME PROMESSO**, limite dichiarato CONFERMATO | eseguita 08/09 20:46 con `env -u HIPPO_ENCODE_DELEGATE_ONLY`: identiche `1.0000` · IT vs EN equivalenti `0.9211` · **scollegate `0.7905`**. La base alta è il limite che il docstring già dichiara (soglia del banco 0.878; sul corpus il 91,3% dei fatti avrebbe un «rivale»): la misura lo conferma invece di scoprirlo. Tempi: 1ª chiamata **57,36 s** (carica il modello), successive **0,02 s** |
| 10 | `verimem/validate_claim.py:292` `_polarita` | funzione: La frase e' NEGATA? — il segnale che distingue una frase dal suo | `verimem/anti_confab_gate.py:554`; `verimem/anti_confab_gate.py:594`; `verimem/validate_claim.py:372` | `tests/test_una_negazione_urlata_non_e_un_nome_proprio.py` | - | NON MISURATO | - |
| 11 | `verimem/validate_claim.py:326` `_parole_di_contenuto` | funzione: Le parole che portano l'ASSERZIONE: né nomi, né parole vuote. | `verimem/anti_confab_gate.py:553`; `verimem/anti_confab_gate.py:596`; `verimem/anti_confab_gate.py:597` (+4) | `tests/test_gli_stessi_nomi_non_sono_la_stessa_cosa.py`; `tests/test_il_criterio_dichiara_quando_non_sa_leggere.py`; `tests/test_una_negazione_urlata_non_e_un_nome_proprio.py` | - | NON MISURATO | - |
| 12 | `verimem/validate_claim.py:383` `_testa_nominale` | funzione: La prima parola di contenuto: in una frase SVO e' la testa del soggetto. | `verimem/anti_confab_gate.py:555`; `verimem/anti_confab_gate.py:600`; `verimem/anti_confab_gate.py:601` | `tests/test_una_negazione_urlata_non_e_un_nome_proprio.py` | - | NON MISURATO | - |
| 13 | `verimem/validate_claim.py:402` `_qualcuno_asserisce` | funzione: Almeno un fatto dice qualcosa DELLA claim, non solo dei suoi soggetti. | `verimem/validate_claim.py:943`; `verimem/validate_claim.py:946` | `tests/test_gli_stessi_nomi_non_sono_la_stessa_cosa.py` | - | NON MISURATO | - |
| 14 | `verimem/validate_claim.py:445` `_subj_overlap` | funzione: Frazione di nomi-claim presenti nel testo del fact (case-insensitive). | `verimem/validate_claim.py:149`; `verimem/validate_claim.py:359`; `verimem/validate_claim.py:487` (+3) | `tests/test_il_gate_diceva_supported_alla_frase_negata.py`; `tests/test_il_gate_puo_solo_bocciare_in_tre_lingue.py`; `tests/test_trust_dichiara_cio_che_ha_girato.py` (+2) | - | NON MISURATO | - |
| 15 | `verimem/validate_claim.py:484` `_content_overlap` | funzione: Frazione di parole DISTINTIVE della claim presenti nel testo del fact. | `verimem/quantity_match.py:1318`; `verimem/truth_reconciliation.py:274`; `verimem/truth_reconciliation.py:315` (+3) | `tests/test_l_hangul_usciva_a_pezzi_dalla_normalizzazione.py`; `tests/test_la_guardia_dell_overlap_parlava_solo_inglese.py`; `tests/test_le_vocali_indiane_non_erano_lettere.py` (+1) | - | NON MISURATO | - |
| 16 | `verimem/validate_claim.py:539` `_giudice_contraddice` | funzione: Vero se il giudice nega sostegno a un claim che parla dello stesso tema. | `verimem/validate_claim.py:882` | nessuno | - | NON MISURATO | - |
| 17 | `verimem/validate_claim.py:562` `validate_claim` | funzione: Valida una claim factual contro la memoria semantica dell'agente. | `verimem/anti_confab_gate.py:4`; `verimem/anti_confab_gate.py:15`; `verimem/anti_confab_gate.py:551` (+19) | `tests/test_anti_confab_gate.py`; `tests/test_anti_confab_gate_l18_wire.py`; `tests/test_any_language_ha_un_numero.py` (+20) | - | **NON MISURATO** | tentata 08/09 20:41: `TypeError: expected string or bytes-like object, got '_MemoriaVuota'`. **L'errore è nel mio chiamante, non nella funzione**: un'eccezione causata da me non è un verdetto. Da rifare leggendo la firma — 433 righe, la porta pubblica del gate |
