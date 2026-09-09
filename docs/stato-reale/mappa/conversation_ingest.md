# Mappa — `verimem/conversation_ingest.py`

*ws3 Galileo. 12 funzioni: da una **conversazione** ai fatti atomici, uno per
uno, ognuno attraverso un controllo. Banchi: `ws3-mappa-prova-ingest.py`,
`ws3-mappa-prova-ingest-due.py`, `ws3-mappa-prova-due-porte.py`
(09/09 14:03-14:07).*

🔴 **Il reperto del file, in una riga (T-MAP-11, in fondo)**: il controllo
dell'ingest **ferma le contraddizioni ma non le invenzioni**. Su un dialogo che
parla solo del canone e della consegna: 3 fatti **detti** ammessi su 3 (giusto),
2 fatti **contraddetti** respinti su 2 (giusto), e **3 fatti INVENTATI ammessi
su 3** — «il capannone è stato venduto nel 2019», «ha 400 metri quadri», «il
proprietario si chiama Mario Rossi». `ingest_conversation` li ha **memorizzati**,
e la ricerca poi li **serve**.

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/conversation_ingest.py:85` `split_entities_line` | «separa la riga finale `ENTITIES: type:Name; …` dal testo dei fatti. **Fail-safe**: nessuna riga ENTITIES → (testo invariato, []). Tipi fuori dal vocabolario…» | **FUNZIONA COME PROMESSO — tre casi** | con la riga → testo pulito + `[{'name': 'Mario', 'type': 'person'}, {'name': 'Acme', 'type': 'org'}]` · **senza** la riga → `(testo invariato, [])` · con un tipo inventato (`alieno:Zorg`) → **solo** `Mario` sopravvive: il vocabolario dei tipi filtra davvero |
| 2 | `verimem/conversation_ingest.py:234` `parse_extracted_lines` | «un fatto per riga non vuota, **UN SOLO** marcatore iniziale (elenco o numero) rimosso» | **FUNZIONA COME PROMESSO — provato col caso stretto** | `- Il canone…` → testo pulito · `1. La consegna…` → pulito · **`-- Due marcatori di fila.` → `'Due marcatori di fila.'`** (ne toglie uno, il secondo lo tratta come testo… e infatti il risultato conserva il senso) · riga vuota scartata · spazi iniziali tolti |
| 3 | `verimem/conversation_ingest.py:249` `strip_belief_marker` | «`(proposizione pulita, is_belief)`: una riga marcata `BELIEF:` è un'asserzione **non verificata**» | **FUNZIONA COME PROMESSO**, maiuscole comprese | `'BELIEF: il canone dovrebbe salire.'` → `('il canone dovrebbe salire.', True)` · una riga normale → `(testo, False)` · **`'belief: minuscolo'` → `('minuscolo', True)`**: il marcatore non è sensibile alle maiuscole |
| 4 | `verimem/conversation_ingest.py:261` `render_conversation` | «righe `role: content`, **con un tetto**… `with_flag=True` restituisce `(testo, troncato)` — audit mod.9: **il taglio era SILENZIOSO**» | **FUNZIONA COME PROMESSO — provato SUPERANDO il tetto** | con `cap_chars=80` → testo di **80** caratteri e **`truncated=True`**; con un tetto largo → `truncated=False`. Il flag **distingue i due casi**, che è esattamente ciò che mancava prima dell'audit |
| 5 | `verimem/conversation_ingest.py:220` `conversation_provenance_ref` | «riferimento di provenienza stabile e con spazio dei nomi» | **FUNZIONA COME PROMESSO** | `'conv-1'` → `'conversation:conv-1'`; stabile fra due chiamate (**True**) e diverso per conversazioni diverse (**True**) |
| 6 | `verimem/conversation_ingest.py:114` `extraction_system_for` | il prompt di estrazione, «esteso col nome utente fornito dall'app (i dialoghi non dicono quasi mai chi è l'utente)» | **FUNZIONA COME PROMESSO** | col nome → **1455** caratteri e contiene «Aurelio»; senza → **1191** e **non** lo contiene; con `typed_entities=True, tag_beliefs=True` → più lungo e nomina **ENTITIES** e **BELIEF**. Ogni interruttore cambia il prompt in modo verificabile |
| 7 | `verimem/conversation_ingest.py:190` `_ingest_ground_threshold` | la soglia del controllo sull'ingest | **FUNZIONA COME PROMESSO** | → **40.0**, cioè la stessa soglia del moat del CE locale (`LOCAL_CE_MOAT_THRESHOLD`) |
| 8 | `verimem/conversation_ingest.py:195` `_grounds` | «**il moat sulla via dell'ingest**: il DIALOGO implica il fatto estratto? Restituisce `(ammetti, punteggio)`. Usa il CE locale (gratis, nessuna chiamata LLM per fatto)» | 🔴 **NON COME PROMESSO sulle invenzioni** → **T-MAP-11** | tre gruppi sullo stesso dialogo: **detti** → 3/3 ammessi (99,58 · 99,64 · 96,84) ✅ · **contraddetti** → 0/2 ammessi (0,62 · 0,51) ✅ · **inventati ma plausibili** → **3/3 AMMESSI** (60,22 · 88,80 · 50,00) ❌. Il controllo distingue benissimo ciò che il dialogo **nega**, e non distingue ciò che il dialogo **non dice** |
| 9 | `verimem/conversation_ingest.py:281` `ingest_conversation` | «estrae fatti ATOMICI dai messaggi e **memorizza ognuno attraverso il gate**» | **FUNZIONA COME PROMESSO nel meccanismo; eredita il buco della riga 8** | con un LLM finto che estrae tre righe (due dette, una inventata) → `{'stored': 3, 'rejected': 0, 'extracted': 3, 'consolidated': 3, 'error': None, 'truncated': False, 'typed_entities': 0}` e **due** chiamate all'LLM (estrazione + consolidamento). I tre fatti finiscono nello store tutti come `model_claim`, **compreso** «Il capannone 12 e' stato venduto nel 2019», che il dialogo non dice. Con `ground=False` il controllo si spegne e passa comunque (1 su 1): l'interruttore c'è ed è onesto |
| 10 | `verimem/conversation_ingest.py:431` `gapfill_facts` (+ `verimem/conversation_ingest.py:448` `gapfill_facts._key`) | «restituisce i fatti durevoli che il dialogo DICE e che l'estrazione ha perso. **Solo additivo e fail-safe**: su qualunque errore dell'LLM, o se non c'è niente di nuovo, torna vuoto» | **FUNZIONA COME PROMESSO — entrambi i lati** | con un LLM che propone una riga nuova → `['Il contratto scade nel 2027.']` · con un LLM che risponde spazzatura → **`[]`** (fail-safe, nessuna eccezione) |
| 11 | `verimem/conversation_ingest.py:472` `consolidate_facts` | «fonde i quasi-duplicati e scarta le banalità non durevoli (la passata di precisione). **Fail-safe**» | **FUNZIONA COME PROMESSO — entrambi i lati** | due quasi-duplicati («Il canone e' 5900 euro.» e «Il canone e' di 5900 euro.») → **una sola** riga · con un LLM che risponde vuoto → la lista **originale** invariata, non una lista vuota |

## T-MAP-11 — sulla via dell'ingest il controllo ferma le contraddizioni, non le invenzioni

**La misura** (`ws3-mappa-prova-ingest-due.py`, soglia 40): un dialogo che dice
solo *«Il canone del capannone 12 è 5900 euro al mese, e la consegna è prevista
per il 3 marzo»*.

| gruppo | atteso | misurato |
|---|---|---|
| fatti **detti** dal dialogo (3) | tutti ammessi | **3/3 ammessi** — 99,58 · 99,64 · 96,84 ✅ |
| fatti **contraddetti** (2) | zero ammessi | **0/2 ammessi** — 0,62 · 0,51 ✅ |
| fatti **inventati** ma plausibili (3) | zero ammessi | **3/3 AMMESSI** — 60,22 · 88,80 · 50,00 ❌ |

**E le DUE porte non si comportano allo stesso modo** — controllo fatto apposta
(`ws3-mappa-prova-due-porte.py`), stessa fonte, stessi fatti:

| fatto | `Memory.add(source=…)` | `_grounds` (ingest) |
|---|---|---|
| «…è 5900 euro» (detto) | `model_claim` 99,9 | ammesso 99,9 |
| «…consegna il 3 marzo» (detto) | `model_claim` 99,4 | ammesso 99,4 |
| «…venduto nel 2019» (inventato) | **`model_claim` 84,0** | **ammesso** 71,7 |
| «…400 metri quadri» (inventato) | **`quarantined`** 89,2 | **ammesso** 87,9 |
| «…proprietario Mario Rossi» (inventato) | **`quarantined`** 74,5 | **ammesso** 63,1 |
| «…è 9999 euro» (contraddetto) | `quarantined` 0,7 | respinto 0,7 |

⇒ **Il gate della scrittura ordinaria ne ferma due su tre; quello dell'ingest
zero su tre.** E il fatto che *entrambi* lasciano passare — «il capannone 12 è
stato venduto nel 2019» — alla fine **viene servito dalla ricerca**: nello store
di prova, `search("capannone 12")` restituisce **3** fatti e uno dei tre è
l'invenzione.

⚠️ **Questo non è una scoperta nuova per il prodotto: è una misura nuova di una
cosa che il prodotto già dichiara.** `client._confidence_tier` scrive nero su
bianco che «un livello *high* dal CE locale può ANCORA essere una confabulazione
plausibile-ma-non-detta (misurato 86-99)». Qui la stessa cosa è misurata **sulla
porta dell'ingest conversazionale**, con tre casi su tre e col confronto fra le
due porte — e con la conseguenza visibile: il fatto inventato è **servito**.

**Non curato** (siamo in mappa). Le due domande da girare a chi possiede il
write path: (a) l'ingest deve usare la stessa catena di `Memory.add`, visto che
sugli stessi tre casi ne ferma due? (b) la soglia 40 sulla via dell'ingest è la
scelta giusta, dato che due delle tre invenzioni stavano sopra 60?
