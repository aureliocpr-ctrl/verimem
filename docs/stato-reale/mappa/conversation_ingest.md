# Mappa — `verimem/conversation_ingest.py`

*ws3 Galileo. 13 funzioni: da una **conversazione** ai fatti atomici, uno per
uno, ognuno attraverso un controllo. Banchi: `ws3-mappa-prova-ingest.py`,
`ws3-mappa-prova-ingest-due.py`, `ws3-mappa-prova-due-porte.py`
(09/09 14:03-14:07) e, per il ticket, `ws3-t-map-11-la-soglia-non-separa-halueval.py`
+ `ws3-t-map-11-controllo-delle-etichette.py` (09/09 23:13-23:26).*

🔴 **Il reperto del file, in una riga (T-MAP-11, in fondo)**: il controllo
dell'ingest **ferma le contraddizioni ma non le invenzioni**. Su un dialogo che
parla solo del canone e della consegna: 3 fatti **detti** ammessi su 3 (giusto),
2 fatti **contraddetti** respinti su 2 (giusto), e **3 fatti INVENTATI ammessi
su 3** — «il capannone è stato venduto nel 2019», «ha 400 metri quadri», «il
proprietario si chiama Mario Rossi». `ingest_conversation` li ha **memorizzati**,
e la ricerca poi li **serve**.

🩹 **09/09 sera — curato in parte, e la parte scoperta è dichiarata**: dalla
porta MCP il moat **non veniva chiamato affatto** (`ground` non passato, default
`False`: 0 interrogazioni su 3 fatti — commit `ab8e8e6f`), e l'ingest ammetteva
la **fascia [40, 80)** che `Memory.add` trattiene (commit `dda0e301`). Dopo:
inventati ammessi **1/3** invece di 3/3, detti **3/3**. Quello che resta vale
88,80 e non lo copre nessuna soglia — la misura su HaluEval e la proposta con i
numeri stanno in fondo.

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/conversation_ingest.py:85` `split_entities_line` | «separa la riga finale `ENTITIES: type:Name; …` dal testo dei fatti. **Fail-safe**: nessuna riga ENTITIES → (testo invariato, []). Tipi fuori dal vocabolario…» | **FUNZIONA COME PROMESSO — tre casi** | con la riga → testo pulito + `[{'name': 'Mario', 'type': 'person'}, {'name': 'Acme', 'type': 'org'}]` · **senza** la riga → `(testo invariato, [])` · con un tipo inventato (`alieno:Zorg`) → **solo** `Mario` sopravvive: il vocabolario dei tipi filtra davvero |
| 2 | `verimem/conversation_ingest.py:263` `parse_extracted_lines` | «un fatto per riga non vuota, **UN SOLO** marcatore iniziale (elenco o numero) rimosso» | **FUNZIONA COME PROMESSO — provato col caso stretto** | `- Il canone…` → testo pulito · `1. La consegna…` → pulito · **`-- Due marcatori di fila.` → `'Due marcatori di fila.'`** (ne toglie uno, il secondo lo tratta come testo… e infatti il risultato conserva il senso) · riga vuota scartata · spazi iniziali tolti |
| 3 | `verimem/conversation_ingest.py:278` `strip_belief_marker` | «`(proposizione pulita, is_belief)`: una riga marcata `BELIEF:` è un'asserzione **non verificata**» | **FUNZIONA COME PROMESSO**, maiuscole comprese | `'BELIEF: il canone dovrebbe salire.'` → `('il canone dovrebbe salire.', True)` · una riga normale → `(testo, False)` · **`'belief: minuscolo'` → `('minuscolo', True)`**: il marcatore non è sensibile alle maiuscole |
| 4 | `verimem/conversation_ingest.py:290` `render_conversation` | «righe `role: content`, **con un tetto**… `with_flag=True` restituisce `(testo, troncato)` — audit mod.9: **il taglio era SILENZIOSO**» | **FUNZIONA COME PROMESSO — provato SUPERANDO il tetto** | con `cap_chars=80` → testo di **80** caratteri e **`truncated=True`**; con un tetto largo → `truncated=False`. Il flag **distingue i due casi**, che è esattamente ciò che mancava prima dell'audit |
| 5 | `verimem/conversation_ingest.py:249` `conversation_provenance_ref` | «riferimento di provenienza stabile e con spazio dei nomi» | **FUNZIONA COME PROMESSO** | `'conv-1'` → `'conversation:conv-1'`; stabile fra due chiamate (**True**) e diverso per conversazioni diverse (**True**) |
| 6 | `verimem/conversation_ingest.py:114` `extraction_system_for` | il prompt di estrazione, «esteso col nome utente fornito dall'app (i dialoghi non dicono quasi mai chi è l'utente)» | **FUNZIONA COME PROMESSO** | col nome → **1455** caratteri e contiene «Aurelio»; senza → **1191** e **non** lo contiene; con `typed_entities=True, tag_beliefs=True` → più lungo e nomina **ENTITIES** e **BELIEF**. Ogni interruttore cambia il prompt in modo verificabile |
| 7 | `verimem/conversation_ingest.py:190` `_ingest_ground_threshold` | la soglia del controllo sull'ingest | **FUNZIONA COME PROMESSO** | → **40.0**, cioè la stessa soglia del moat del CE locale (`LOCAL_CE_MOAT_THRESHOLD`) |
| 8 | `verimem/conversation_ingest.py:195` `_grounds` | «**il moat sulla via dell'ingest**: il DIALOGO implica il fatto estratto? Restituisce `(ammetti, punteggio)`. Usa il CE locale (gratis, nessuna chiamata LLM per fatto)» | 🟡 **CURATO IN PARTE il 09/09 (T-MAP-11), e il resto è dichiarato** | misura del 09/09 14:03, stesso dialogo: **detti** 3/3 ammessi (99,58 · 99,64 · 96,84) ✅ · **contraddetti** 0/2 (0,62 · 0,51) ✅ · **inventati ma plausibili 3/3 AMMESSI** (60,22 · 88,80 · 50,00) ❌. **Dopo la cura delle 23:26** (la fascia [40, 80) del write path vale anche qui, `_ammette`): stesso banco rieseguito → **inventati ammessi 1/3**, **detti 3/3**, contraddetti 0/2. Quello che resta vale **88,80**: il docstring di `grounding_gate._ce_band_enforced` dice già che per i «plausible-inference confabs (97-99)» serve un giudice llm |
| 9 | `verimem/conversation_ingest.py:310` `ingest_conversation` | «estrae fatti ATOMICI dai messaggi e **memorizza ognuno attraverso il gate**» | **FUNZIONA COME PROMESSO nel meccanismo; eredita il buco della riga 8** | con un LLM finto che estrae tre righe (due dette, una inventata) → `{'stored': 3, 'rejected': 0, 'extracted': 3, 'consolidated': 3, 'error': None, 'truncated': False, 'typed_entities': 0}` e **due** chiamate all'LLM (estrazione + consolidamento). I tre fatti finiscono nello store tutti come `model_claim`, **compreso** «Il capannone 12 e' stato venduto nel 2019», che il dialogo non dice. Con `ground=False` il controllo si spegne e passa comunque (1 su 1): l'interruttore c'è ed è onesto. 🔴 **09/09 22:56 — quella riga della mia misura era col moat SPENTO e non me n'ero accorto**: il banco chiamava senza `ground`, e il **default della firma è `False`**. È la stessa cosa che faceva la porta MCP (`mcp_server.py:8322`, curata alle 23:0x): «3/3 ammessi» non voleva dire «il giudice li ammette», voleva dire **«nessuno ha chiesto»** |
| 10 | `verimem/conversation_ingest.py:460` `gapfill_facts` (+ `verimem/conversation_ingest.py:477` `gapfill_facts._key`) | «restituisce i fatti durevoli che il dialogo DICE e che l'estrazione ha perso. **Solo additivo e fail-safe**: su qualunque errore dell'LLM, o se non c'è niente di nuovo, torna vuoto» | **FUNZIONA COME PROMESSO — entrambi i lati** | con un LLM che propone una riga nuova → `['Il contratto scade nel 2027.']` · con un LLM che risponde spazzatura → **`[]`** (fail-safe, nessuna eccezione) |
| 11 | `verimem/conversation_ingest.py:501` `consolidate_facts` | «fonde i quasi-duplicati e scarta le banalità non durevoli (la passata di precisione). **Fail-safe**» | **FUNZIONA COME PROMESSO — entrambi i lati** | due quasi-duplicati («Il canone e' 5900 euro.» e «Il canone e' di 5900 euro.») → **una sola** riga · con un LLM che risponde vuoto → la lista **originale** invariata, non una lista vuota |
| 12 | `verimem/conversation_ingest.py:220` `_ammette` | NUOVA il 09/09 (T-MAP-11): «ammette o no, alla soglia dell'ingest **E con la fascia del write path**» — la fascia si importa da `grounding_gate`, non si ricopia (R3) | **FUNZIONA COME PROMESSO — RED falsificato** | RED con la cura tolta (`git stash` della sola cura): «un punteggio nella fascia [40, 80) — 60,22 — è entrato come `'model_claim'`, mentre `Memory.add` lo tratterrebbe» → `2 failed, 1 passed`; rimessa → **5 passed** insieme al banco della porta. Il terzo test è l'A/B nella stessa esecuzione: con `VERIMEM_CE_BAND_ENFORCE=0` la porta torna a prima — verde in entrambi i mondi apposta, altrimenti la fascia non starebbe decidendo niente |

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

---

### 09/09 sera — le due domande sono diventate un esperimento, e la risposta non era quella che avevo scritto

**(a) La catena.** No, non è la stessa: l'ingest scrive con `semantic.store()`
diretto, non con `Memory.add`. Ma la differenza che conta non è nemmeno quella,
ed è **misurata**: le due porte usano **lo stesso numero** —
`grounding_gate.py:73` `LOCAL_CE_MOAT_THRESHOLD = 40.0`, e la riga 550 di quel
file dice testualmente «same as the conversation-ingest path». La differenza è
che il write path **trattiene la fascia [40, 80)** (`_ce_band_enforced`, attiva
di default dal 2026-07-19) e l'ingest sopra 40 ammetteva e basta. Due dei tre
inventati valgono 60,22 e 50,00: **stanno nella fascia**. È la spiegazione
esatta del «due su tre da una porta, zero su tre dall'altra».

**(b) La soglia.** No, e la misura è su dati che non abbiamo scritto noi —
HaluEval QA (MIT, RUCAIBox, `benchmark/data/external/`), banco
`ws3-t-map-11-la-soglia-non-separa-halueval.py` del 09/09 23:13-23:18. NEGATIVI
= la frase plausibile che il contesto non dice; POSITIVI = la prima frase del
contesto, cioè il caso **più facile**, scelto contro la mia tesi apposta:

| campione | invenzioni ammesse a 40 | AUROC | sovrapposizione |
|---|---|---|---|
| HaluEval dev n=100 (ispezionabile) | **46/100 = 46,0%** | 0,9543 | 14/100 negativi sopra il positivo più basso |
| HaluEval heldout n=200 (**mai letto**) | **94/200 = 47,0%** | 0,9590 | 56/200 sopra il positivo più basso |

E **nessuna soglia le separa**: a 99 restano dentro **72/200 invenzioni (36%)**.
Il controllo che poteva smentirmi (`ws3-t-map-11-controllo-delle-etichette.py`,
fatto **prima** di pubblicare): quelle frasi a 99,98 potevano essere «dette dal
contesto e sbagliate solo come risposta». Non lo sono — copertura lessicale 100%
ma **relazione inventata** (il contesto dice che la scuola è a Hollis e che
*Brookline* ospita il santuario; la frase dice che la scuola è **dentro** il
santuario).

**La cura, e cosa NON copre.** Entrata alle 23:26 (`_ammette`, riga 12 della
tabella): la fascia del write path vale anche qui. Effetto misurato: sul banco
del capannone **inventati ammessi da 3/3 a 1/3, detti 3/3** (nessun vero perso);
su HaluEval heldout le invenzioni fermate passano da 106 a 112 su 200 (**+3
punti**). Il resto — le invenzioni che valgono 97-99 — **non è coperto**, e non
lo prometto: il docstring di `_ce_band_enforced` lo dice già («plausible-inference
confabs (97-99) still need an llm judge»). La proposta con i numeri (un terzo
passaggio llm sull'ingest, costo **una chiamata per conversazione**, non per
fatto) è sul canale come decisione D-1.

**E l'errore mio, dove stava**: «l'ingest ammette 3 invenzioni su 3» misurava
una chiamata **senza `ground`**, cioè col moat **spento** — non un giudice
indulgente. Sulla porta MCP era anche peggio, perché `ground` non era proprio
passabile: 0 interrogazioni su 3 fatti (curato, commit `ab8e8e6f`).
