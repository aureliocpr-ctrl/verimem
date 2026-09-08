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

# verimem/validate_claim.py — 17 fra funzioni e classi

| # | funzione (file:riga) | cosa promette | chiamata da | test | claim | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `class _FactLike` (verimem/validate_claim.py:80, 6 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 2 | `class _SemanticLike` (verimem/validate_claim.py:88, 4 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 3 | `def search_facts` (verimem/validate_claim.py:89, 3 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 4 | `class _AgentLike` (verimem/validate_claim.py:94, 2 righe) | (nessun docstring) |  |  |  | NON MISURATO |  |
| 5 | `def _unita_non_allineabili` (verimem/validate_claim.py:98, 34 righe) | Vero quando le due frasi misurano grandezze DIVERSE, non la stessa in |  |  |  | NON MISURATO |  |
| 6 | `def _extract_salients` (verimem/validate_claim.py:134, 10 righe) | Estrae (capitalized_names, years) dalla stringa. |  |  |  | NON MISURATO |  |
| 7 | `def _termine_presente` (verimem/validate_claim.py:146, 10 righe) | Il termine come PAROLA INTERA, non come sottostringa. |  |  |  | NON MISURATO |  |
| 8 | `def leggibile_a_maiuscole` (verimem/validate_claim.py:194, 36 righe) | Il riconoscimento dei nomi propri per MAIUSCOLA funziona su questa frase? | `_parole_di_contenuto` e il ciclo di `validate_claim` (letto: il segnale e' strutturale, non nomina lingue) | `tests/test_il_gate_puo_solo_bocciare_in_tre_lingue.py` | «stops what the source does not support» | **FUNZIONA COME PROMESSO** per il caso che cura | eseguita 08/09 20:46 con FRASI: it `True` · en `True` · de `False` (x2, uno e' l'esempio del docstring) · **zh `True`**. ⚠️ Il cinese risponde `True` a una domanda che li' non si applica (nessuna maiuscola da riconoscere): NON apro un T, il difetto e' gia' misurato e ha la causa alla riga in `test_il_gate_puo_solo_bocciare_in_tre_lingue.py` — `_CAPS_RE` guarda le maiuscole latine ASCII, quindi RU/ZH/JA danno `unknown`. **Questa riga ne e' una conseguenza, non una scoperta.** |
| 9 | `def similarita_semantica` (verimem/validate_claim.py:249, 41 righe) | Quanto due frasi parlano della stessa cosa, in QUALUNQUE lingua | fallback dove le liste di parole non arrivano (docstring letto: regge su UNA coppia gia' accoppiata, NON per selezionare) | `tests/test_le_lingue_non_coperte_hanno_un_motore.py` | «stops what the source does not support» | **FUNZIONA COME PROMESSO**, e il limite dichiarato e' CONFERMATO | eseguita 08/09 20:46 con `env -u HIPPO_ENCODE_DELEGATE_ONLY`: identiche `1.0000` · IT vs EN equivalenti `0.9211` · **scollegate («233 scritture» vs «oggi piove a Milano») `0.7905`**. La base alta e' il limite che il docstring gia' dichiara (soglia del banco 0.878; sul corpus il 91,3% dei fatti avrebbe un «rivale»): **la mia misura lo conferma invece di scoprirlo**. Tempi: 1a chiamata **57,36 s** (carica il modello), successive **0,02 s**. |
| 10 | `def _polarita` (verimem/validate_claim.py:292, 25 righe) | La frase e' NEGATA? — il segnale che distingue una frase dal suo |  |  |  | NON MISURATO |  |
| 11 | `def _parole_di_contenuto` (verimem/validate_claim.py:326, 55 righe) | Le parole che portano l'ASSERZIONE: né nomi, né parole vuote. |  |  |  | NON MISURATO |  |
| 12 | `def _testa_nominale` (verimem/validate_claim.py:383, 17 righe) | La prima parola di contenuto: in una frase SVO e' la testa del soggetto. |  |  |  | NON MISURATO |  |
| 13 | `def _qualcuno_asserisce` (verimem/validate_claim.py:402, 41 righe) | Almeno un fatto dice qualcosa DELLA claim, non solo dei suoi soggetti. |  |  |  | NON MISURATO |  |
| 14 | `def _subj_overlap` (verimem/validate_claim.py:445, 37 righe) | Frazione di nomi-claim presenti nel testo del fact (case-insensitive). |  |  |  | NON MISURATO |  |
| 15 | `def _content_overlap` (verimem/validate_claim.py:484, 41 righe) | Frazione di parole DISTINTIVE della claim presenti nel testo del fact. |  |  |  | NON MISURATO |  |
| 16 | `def _giudice_contraddice` (verimem/validate_claim.py:539, 21 righe) | Vero se il giudice nega sostegno a un claim che parla dello stesso tema. |  |  |  | NON MISURATO |  |
| 17 | `def validate_claim` (verimem/validate_claim.py:562, 433 righe) | Valida una claim factual contro la memoria semantica dell'agente | la PORTA PUBBLICA: chiamata da fuori (da mappare) | `tests/test_anti_confab_gate.py`, `tests/test_any_language_ha_un_numero.py` | «stops what the source does not support» | **NON MISURATO** | tentata 08/09 20:41: `TypeError: expected string or bytes-like object, got '_MemoriaVuota'`. **L'errore e' nel mio chiamante, non nella funzione**: le ho passato un oggetto dove vuole altro. Un'eccezione causata da me non e' un verdetto. Da rifare leggendo la firma — e' la funzione piu' grande della mia porzione (433 righe) e merita il suo giro. |
