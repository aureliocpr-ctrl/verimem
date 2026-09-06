# Il censimento dei 199 strumenti senza permesso — cosa fanno davvero

**ws4 «Paragone» / Nadia Ferro, ML Engineer. 06/09/2026, 06:20 → 08:01.**
**199 strumenti su 199 letti nel codice, uno per uno, ogni verdetto con la riga che
lo prova.** Nessuna euristica: il nome, le chiamate a due livelli e la firma erano già
cadute (§6), e un righello automatico aveva dato **36 falsi positivi su 36**.

---

## 1. I numeri, con la somma di controllo

```
   strumenti esposti (_list_tools_unfiltered, ESEGUITA)      249
   con permesso esplicito (REGISTRY.all(), ESEGUITA)          50
   senza permesso — «i 199»                                  199
   somma di controllo:  50 + 199 = 249  = totale  ✅

   dei 199, letti uno per uno:                               199   (nomi distinti, contati)

   READ                                                      155
   WRITE (scrivono sempre)                                     26
   CONDIZIONALI (scrivono solo con apply=True)                 16
   che passano un llm= (extract_entities; gli altri 2 sono già contati sopra)   1
   CONFIG (riscrivono os.environ)                               1
   ────────────────────────────────────────────────────────────────
                                                             199  ✅
```
⚠️ **Perimetro**: questo censimento dice **cosa fa il ramo del dispatcher**. Per gli
strumenti che delegano in una riga (`consolidate_light`) **il verdetto viene da dentro la
funzione chiamata, non dal ramo**, ed è dichiarato caso per caso nei messaggi dei lotti.

---

## 2. 🔴 Il reperto principale: la matrice classifica ciò che si riconosce DAL NOME

```
   scriventi verificati leggendo il codice        26
   di cui CON permesso esplicito                   0
   di cui SENZA (fra i 199)                       26        ← ventisei su ventisei
```
Le **14** scritture che il registro *conosce* sono `remember` · `forget` · `forget_scope` ·
`fact_forget` · `fact_forget_with_undo` · `fact_supersede` · `record_episode` ·
`consolidate` · `decay_run` · `skill_promote` · `skill_retire` · `anti_confab_apply` ·
`contradictions_scan` · `undo_destructive_op`. **Sono tutte scritture che si capiscono dal
nome.** Le 26 che mancano sono `dream_adopt` · `entity_link` · `transcript_promote` ·
`heal_contradictions` · `quarantine_restore` · `self_model_refresh` · … — **scritture che
dal nome non si vedono.**

🎯 **La prova più secca, due nomi a un carattere di distanza:**
```
   hippo_fact_supersede         NEL REGISTRO,  writes_memory=True
   hippo_fact_supersede_chain   FUORI, fra i 199
```
Fanno la stessa cosa. **Non è una scelta di rischio: è dove si è fermata la lettura.**

⚠️ **Non è una colpa di chi l'ha scritta**: il docstring di `build_default_registry()` dice
*«pre-populated with the 15 critical seeds»* — nasceva come **seme**. *(E dice 15 dove le
voci sono 50: un numero in un commento che è invecchiato mentre il codice cresceva.)*
**Il problema è che nel frattempo il seme è diventato la cosa che decide.**

✅ **Una cosa buona misurata nello stesso giro: zero voci orfane.** Tutte e 50
corrispondono a uno strumento vivo. **Il registro è incompleto, non sbagliato** — e per la
cura la differenza conta.

### Il nome mente in DUE direzioni

```
   promettono una scrittura e NON scrivono   facts_merge · facts_topic_merge ·
                                             rollup_old_episodes · smart_prune
   non la promettono e SCRIVONO              dream_adopt · entity_link ·
                                             transcript_promote · self_model_refresh
```
E **quattro strumenti con «merge» nel nome hanno quattro comportamenti**: `facts_merge`
calcola · `facts_topic_merge` calcola · `skill_merge_pair` è condizionale ·
**`skill_merge` scrive due volte** (fonde la destinazione **e ritira la sorgente**).

---

## 3. 🔴 46 tagli silenziosi — e uno risponde «non esiste» a un fatto che esiste

```
   grep -oE "limit=[0-9]{3,}" mcp_server.py | sort | uniq -c
      40  limit=10000        3  limit=5000        3  limit=2000      → 46 righe

   fatti nello store di casa:  17.860   (misurato 06/09 06:20)
                               17.967   (rimisurato 06/09 08:18)
```
⚠️ **I due numeri sono lì apposta.** Il primo è quello con cui ho scritto questo documento;
il secondo è di **due ore dopo**, e li ho messi entrambi perché **il numero invecchia mentre
il documento resta** — la classe che questo censimento denuncia, applicata al censimento.

🔑 **E la differenza fra i due è un argomento in più, non un dettaglio**: **il limite è fisso
a 10.000 e lo store cresce.** La copertura era il **56,0%** alle 06:20 e il **55,7%** alle
08:18, **senza che nessuno abbia toccato una riga di codice**. ⇒ **Il difetto dei tagli
peggiora da solo**, e il giorno in cui qualcuno lo guarderà sarà peggiore di oggi.
**Due gravità diverse:**
- 🔴 **FALSO** — `assess_fact_freshness` cerca il fatto **scorrendo** `list_facts(limit=10000)`
  e restituisce `not found` se non lo trova. **Con quasi diciottomila fatti, uno oltre i primi diecimila
  riceve «non esiste» pur esistendo.** *(E quello strumento ha **zero chiamate in 3,9
  giorni**: un difetto in uno strumento che nessuno chiama non fa rumore.)*
- ⚠️ **IMPRECISO** — la famiglia `facts_*` che aggrega (`aggregate_overall`, `by_agent`,
  `by_confidence`, `cluster_by_topic`, `disagreement`, `find_duplicates`, `find_polluted`,
  `merge`, `topic_merge`) risponde **sul 56% del corpus** senza dichiararlo.

🎯 **Il modo più semplice di spiegarlo**, due strumenti nello stesso file:
```
   skills_export_all   →  export_all_skills(a.skills.all(), ...)          TUTTE
   facts_export_all    →  export_all_facts(list_facts(limit=10000), ...)  max 10.000
```
**Stesso nome, stessa promessa, e uno la mantiene mentre l'altro no.**

### E un taglio della forma opposta
`episodes_find_duplicates` restituisce `groups_count` e `total_duplicates_count`
**completi** e la lista **troncata a 30** (`groups[:30]`, `loser_ids[:20]`), **senza un
campo che lo dica**. Lì il numero era parziale e sembrava totale; **qui il numero è totale
e l'elenco sembra completo.**

---

## 4. 🎯 Le due cure sono GIÀ SCRITTE nel prodotto

**Non vanno inventate: vanno estratte e applicate dove mancano.**

```
   skill_exposure_audit:   "invisible_count_truncated": len(audit["invisible_all"])
   skill_retire_invisible: payload = { ..., "dry_run": not apply_changes }
```
- **Il primo campo** dichiara che una lista è tagliata, col conteggio vero accanto: è
  **esattamente** ciò che manca ai 46 tagli e a `episodes_find_duplicates`.
- **Il secondo** mette `dry_run` **nel payload**: chi riceve la risposta sa se ha simulato o
  agito, **senza doverselo ricordare dagli argomenti che ha mandato**. È la cura del difetto
  per cui **la matrice non sa esprimere i 16 condizionali** (il gate riceve gli argomenti e
  decide sul nome).

⚠️ **E la cura va fatta in UNA funzione, non in 46 righe copiate**: la duplicazione è la
prima delle classi di errore che ci costano.

---

## 5. Le caselle non bastano — due domande di design, non di lettura

**① Serve una casella `CONFIG`.** `provider_switch` non legge e non scrive in memoria:
```
   os.environ["HIPPO_LLM_PROVIDER"] = provider
```
Cambia **il comportamento futuro di tutti gli altri**, e in particolare **quale chiave paga**
per i tre non classificati che possono chiamare un LLM (`extract_entities`,
`import_conversations`, `ingest_conversation`). ✅ Il presidio giusto c'è —
`_provider_is_configured` rifiuta un provider senza chiave — **ma `capability` non ha una
casella per «cambia la configurazione del processo»**, e un profilo «sola lettura» che lo
lasciasse passare non sarebbe di sola lettura.

**② «Scrive» va completato con DOVE.** Le scritture toccano **tre superfici**:
```
   memoria viva        consolidate_light · contradictions_resolve ·
                       document_promote_chunk · dream_adopt · …
   indice documenti    document_index_file
   file su disco       dream_create_shadow · dream_propose · dream_submit_result
```
⇒ Un profilo costruito su `capability` fermerebbe anche i tre che **non toccano la
memoria**. **Per i profili serve `writes_memory`, non `capability`.**

---

## 6. Perché a mano, e cosa è costato

```
   ① il NOME                 42% dei «sospetti per nome» NON scrive
   ② le chiamate a due hop   un tool che chiama un writer può non scrivere mai
   ③ la FIRMA               falsificata dal caso dichiarato:
                            topic_cleanup_suggestions riceve `semantic` per LEGGERE
   ④ un righello automatico  36 falsi positivi su 36 (bastava la parola «write»)
```
**Nessuna scorciatoia regge: il codice si legge.**

### Cinque errori miei, tutti trovati e corretti prima che li trovasse un altro
1. **`import_conversations` non «scrive sempre»**: è **condizionale** (*«consent-first:
   default = list only»*). ⇒ i 18 della notte sono **17 + 1 condizionale**.
2. **«`extract_entities` è l'unico che passa un `llm=`»**: falso — il grep cercava
   `llm=llm`, cioè **una forma**.
3. **«Sono cinque rami»**: falso anche quello — il secondo grep attribuiva **per
   prossimità** (`-B40`). **I rami veri sono quattro**, di cui **tre fra i 199** e uno
   (`trust_report`) **fra i 50 classificati**; `transcript_promote` **non chiama nessun LLM**.
4. Una **somma sbagliata** (141 invece di 140) corretta dentro il messaggio stesso.
5. Il **conteggio dei condizionali** (11 → 16).

🪞 **La lezione, e vale oltre questo documento**: due volte su tre l'errore è venuto da un
**grep che cercava una forma o una vicinanza invece della cosa**. La misura giusta era
**estrarre i rami con l'AST e cercare dentro ciascuno** — la stessa disciplina che questo
censimento applica agli strumenti, applicata agli strumenti con cui lo si fa.

---

## 7. ✅ E sette cose che il prodotto fa bene

- `document_semantic_search` **dichiara i chunk nascosti** (`hidden_chunks` + nota che i
  risultati sono PARZIALI) — l'opposto esatto dei tagli silenziosi.
- `prepare_task` dichiara **`"llm_called": False`**.
- `screen_content` dichiara **«No corpus mutation»**.
- `quarantine_log` porta scritto **«DELEGA, non copia»** e usa l'SDK invece di duplicare.
- `quarantine_restore` **aggira il difetto noto di `get()`** leggendo dallo store, e il
  commento spiega perché.
- `document_index_file` prende l'identità **dal server** (`principal=_MCP_PRINCIPAL`), mai
  dagli argomenti, perché *«è il vettore poison-then-cite»*.
- `forget_with_report` **dichiara che la cancellazione è reale ma PARZIALE** (il worker dei
  dream tiene copie del DB, alcune per sempre). ⚠️ **Questa è la riga da portare in
  scheda**: chi risponde a una richiesta di cancellazione deve saperlo.

**Quando l'abitudine di dichiarare c'è, funziona. Il difetto dei tagli è la stessa
abitudine che manca altrove.**
