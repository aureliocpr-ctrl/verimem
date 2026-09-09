# `README.md` riga per riga — claim → codice → presidio → verdetto

> **@ws7 Iris**, mandato di Aurelio dell'08/09 20:33 («tutta la superficie
> mappata»). Base: `origin/main` **`20257636`**, `README.md` = **811 righe**.
> **Il README è la pagina di PyPI** (`pyproject.toml`: `readme = "README.md"`),
> quindi ogni riga qui è una promessa che un utente riceve.

## Come si legge una riga di questa tabella

| colonna | cosa contiene |
|---|---|
| **riga** | il numero di riga in `README.md` su `20257636` |
| **claim** | cosa promette a un utente — *prosa compresa*, non solo i comandi |
| **dove sta** | `file:riga` del codice che lo fa, o `—` se non c'è codice |
| **presidio** | il test che lo tiene fermo, o `—` |
| **verdetto** | **✅ FUNZIONA COME PROMESSO** · **❌ NON COME PROMESSO** · **⬜ NON MISURATO** |

⚠️ **`NON MISURATO` non è un'accusa e non è un'assoluzione**: dice che *da questa
mappa* non risulta né una prova né una smentita. È il verdetto più frequente e il
più utile: è la lista di cosa il prodotto promette **sulla fiducia**.

⚠️ **Cosa NON fa questa mappa**: non esegue il prodotto. Verifica che **il codice
esista** e che **un presidio lo nomini**. Un `✅` qui vuol dire *«la promessa ha
un'implementazione e qualcuno la guarda»*, non *«l'ho vista funzionare»* — quando
l'ho eseguita, la riga lo dice.

---

## Righe 1-30 — il banner e la frase di apertura

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 1 | il prodotto si chiama **Verimem** | `pyproject.toml:name` | `test_il_readme_insegna_il_nome_del_prodotto.py` | ✅ |
| 3 | `mcp-name: io.github.aureliocpr-ctrl/verimem` — l'identità sul registro MCP | `server.json` | `test_il_pacchetto_ha_cio_che_promettiamo.py` | ⬜ *(la coerenza col registro pubblico non è verificata da qui)* |
| 5 | «**la prima scrittura giudicata è lenta — e puoi spostare il costo**» | — *(è la tesi del blocco)* | `test_il_banner_in_cima_al_readme_non_puo_dire_che_il_moat_e_spento.py` | ✅ **il presidio esiste ed è acceso**: vieta la frase contraria in **tutto** il README (esteso da me l'08/09, RED→GREEN falsificato) |
| 7 | esiste il comando `verimem warmup` | `cli.py` | `test_i_comandi_che_il_readme_insegna_esistono.py` | ✅ **eseguito**: `python -m verimem.cli warmup --help` → `EXIT=0` |
| 9-10 | «**non sei obbligato a eseguirlo**: la prima `remember --source` si procura il giudice da sé» | `anti_confab_gate.py:2538` — `ensure_gate_model()` chiamata **fuori** da `warmup` | `test_ws5_giudice_si_procura_da_solo.py` | ✅ **il codice c'è e il commento accanto racconta il difetto curato** (`:2508`: *«era chiamata SOLO da `verimem warmup` (`cli.py:594`)»*) |
| 11-13 | la misura del **2026-09-06** sulla 0.7.6 pubblicata: **85,7 s**, `grounding_score 99.97`, `moat: judged 100.0` | — *(è una misura, non codice)* | `test_ws5_giudice_si_procura_da_solo.py` (registra la misura) | ⬜ **il numero non è ri-misurato da questa mappa**: la riga dichiara data, versione e condizioni, che è la forma giusta — ma nessun presidio lo rifà |
| 14-16 | il modello pesa **711 MB / 746 MB decimali**, **13-27 s** su una connessione normale, **nessun account** | — | `test_il_readme_e_la_cli_dicono_lo_stesso_peso.py` · `test_la_vetrina_nomina_i_modelli_che_scarica.py` | ✅ **sul peso** (il presidio confronta README e CLI) · ⬜ **sui 13-27 s** e sul «no account»: nessun presidio li tocca |
| 16-17 | dopo, «ogni scrittura è giudicata in **~0,2 s**, offline» | — | **nessuno** (`grep "0.2 s" tests/` → vuoto) | ⬜ **NON MISURATO** — e la mia misura del 07/09 sulla **prima** scrittura (22 s CLI) *non* riguarda questa riga, che parla delle **successive** |
| 19-22 | la nota storica: «questo riquadro diceva che il moat era OFF; era vero della **0.7.1**; la cura è entrata e il testo non l'ha seguita» | `anti_confab_gate.py:2508` (il commento) | `test_ws5_giudice_si_procura_da_solo.py` | ✅ **verificabile e verificata**: il file citato esiste, il codice citato esiste |
| 24-26 | 🔑 **la frase centrale**: «ogni scrittura passa un cancello di ammissione, ogni lettura porta la provenienza, e un claim che la fonte **apertamente contraddice** non torna come verità» | `anti_confab_gate.py` (gate) · `client.py:735` (la chiamata dalla porta) | `test_all_write_channels_judge_a_source.py` | ❌ **NON COME PROMESSO, e questo è il numero più duro che abbiamo**: dalla porta `Memory.add`, **6 self-claim su 7** preceduta da un fatto vero entrano `judged=True` con `grounding` 99,9x (banco `ws7-d1-dalla-porta-sdk.py`, 07/09). Chiamando il gate a mano sono **7/7 fermate**. ⚠️ E il presidio della parità **non poteva vederlo**: usa un giudice **finto** e verifica `judge.calls >= 1`, cioè che il canale *consulti*, non che l'esito sia giusto |
| 28-30 | «ogni cifra qui sotto viene da un banco in `docs/stato-reale/banchi/`, su fonti corte, dalla porta pubblica `remember --source`» | `docs/stato-reale/banchi/` (esiste, ~120 file) | **nessuno** | ⬜ **NON MISURATO come promessa universale**: nessun presidio verifica che *ogni* cifra del README abbia un banco. *È esattamente la classe che il 07/09 ho misurato a mano: su 52 identificatori della vetrina, uno non aveva codice sotto* |

---

## Righe 31-90 — i numeri di punta: le due garanzie e i due dataset pubblici

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 32-37 | la tabella delle **contraddizioni ammesse come vere**: negazione **0/10 IT, 0/10 EN** · entità scambiata **1/10 IT, 2/10 EN** · inferenza **0/10 EN, 3/10 IT** · claim non menzionato **8/10 IT, 9/10 EN** | — *(numeri di banco)* | **nessuno** | ⬜ **NON MISURATO**: nessun test lega questi numeri a un file di risultati. *Sono i numeri che descrivono la prima garanzia del prodotto.* |
| 39-46 | i **tre limiti** accanto a quei numeri: **lunghezza** (un caso 9,6 → 35,9 contro un taglio di 40) · **scrittura** (ZH/JA come EN, KO 3, AR 5, HI 7, **Thai 10/10**) · **cifre** (con un numero **0/18** passa, senza **16/18** passa) | `docs/stato-reale/banchi/ws3-la-seconda-garanzia-fuori-da-it-en.py` — **il file esiste** | **nessuno** | ✅ **sul fatto che il banco citato esista** · ⬜ **sui numeri**: nessun presidio li rilegge. 🔑 **Ma la riga 46 è scritta come va scritta**: dice *«leggi quella riga come "quasi sempre fermato se c'è un numero, quasi mai se non c'è", non come 2 su 10"»* — **una media che dichiara di essere una media su due metà opposte** |
| 48-51 | i quattro **badge**: PyPI, CI, licenza AGPL-3.0, sito | — | `test_i_collegamenti_della_vetrina_reggono_fuori_dal_repository.py` | ✅ **sui link** *(che il badge PyPI mostri la versione giusta dipende da PyPI, non da noi)* |
| 53-57 | «i fatti sono ammessi da un cancello anti-confabulazione, conservati con le fonti, rivisti per **supersessione esplicita (mai sovrascritture silenziose)**, e risposti **con le citazioni** — o con un onesto *"non lo so"*» | `anti_confab_gate.py` · `supersession_policy.py` · `client.py` | `test_la_promessa_della_citazione_vale_su_ogni_superficie.py` | ⚠️ **verdetto SPEZZATO, e va spezzato**: ✅ sulla citazione (presidiata su ogni superficie) · ✅ sulla supersessione (`superseded_by`, verificato da @ws2 il 06/09 su entrambe le porte) · ❌ **sul cancello**, per la riga 24: dalla porta le self-claim in coda entrano giudicate |
| 59-66 | «**sul recupero siamo competitivi**»: LongMemEval_s **recall@5 = 0.87** (500 domande, senza giudice) · LoCoMo **QA-accuracy = 0.81** (n=150, giudice Claude) — dichiarati *«nostre run interne, non riprodotti da terzi, non il giudice GPT-4 delle classifiche pubbliche»* | `docs/BENCHMARKS.md` — **il file esiste** | **nessuno** *(il `grep` di `0.87` trova due test che parlano d'altro: omonimia, non presidio)* | ⬜ **NON MISURATO** · ✅ **sulla forma**: la riga **dichiara da sé** che non è un confronto alla pari, ed è la cosa più difficile da scrivere quando un numero fa gola |
| 68-77 | la tabella dei **due dataset pubblici**: TruthfulQA **15,9%** (40/252) con baseline cieca **51,3** · HaluEval **35,7%** (90/252) con baseline **70,8** | — | **nessuno** | ⬜ **NON MISURATO** — 🔑 **e sono i numeri più citabili della pagina**: se qualcuno li riprende, non abbiamo un test che dica che il README riporta ciò che il banco ha misurato |
| 78-86 | «**leggi la seconda colonna o non leggere la prima**»: la baseline cieca dice quanta parte del punteggio è raggiungibile **dalla forma** del claim, e per questo 35,7 e 15,9 **non** vanno letti come «siamo il doppio peggio su HaluEval» | — | **nessuno** | ✅ **come metodo, ed è la riga migliore della pagina**: mette accanto al numero la cosa che lo rende leggibile, invece che in appendice. ⬜ **come misura**: la baseline non è ri-verificata da un presidio |
| 88-90 | «**i due denominatori sono uguali per coincidenza, non per costruzione**»: 162+90 = 252 su HaluEval, 212+40 = 252 su TruthfulQA, da popolazioni di 600 e 400 | — | **nessuno** | ✅ **come metodo**: dichiarare che due numeri identici *non* significano la stessa cosa è esattamente ciò che impedisce a un lettore di dedurre un rapporto che non c'è |

### 📌 Il reperto di questo blocco

**Nessuno dei numeri di punta del README ha un presidio che lo leghi al suo
banco.** Il solo presidio di quel tipo — `test_la_tabella_metric_regge_le_sue_fonti.py`
— copre la **tabella «Metric»**, che sta altrove. ⇒ Se un banco cambia esito, il
README **non lo scopre da solo**: la sua correttezza dipende da chi si ricorda di
aggiornarlo. *È la stessa forma della nota del 26/08 sui numeri della release:
**una nota non è un presidio**, e oggi quella lezione è costata un numero
sbagliato a un passo dal tag.*

---

## Righe 91-150 — riproducibilità e la sezione «Features»

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 91-93 | «il tasso di falsità e la quota servita **si leggono insieme o non si leggono**» (42% contro 63%) | — | **nessuno** | ✅ **come metodo**: impedisce di confrontare due tassi con denominatori diversi. ⬜ come misura |
| 95-100 | **«riprodulo tu stesso, un comando per dataset, nessuna rete per i dati»**: `bash scripts/repro_c10.sh truthfulqa\|halueval`, con gli exit code dichiarati (`0` tiene · `3` diverge · `2` manca un prerequisito) | `scripts/repro_c10.sh` — **il file esiste** | **nessuno** | ✅ **sul file** · ⬜ **sul comportamento**: nessun presidio esegue lo script o verifica che gli exit code siano quelli. 🔑 **È la promessa più forte della pagina** — *«non fidarti, rifallo»* — e **nessun test la tiene ferma** |
| 102-103 | «il modello del giudice (746 MB) è un **prerequisito**, e lo script **lo dice e si ferma** invece di produrre un numero che somiglia a questo senza di esso» | `scripts/repro_c10.sh` | **nessuno** | ⬜ **NON MISURATO** — *ed è la riga che protegge tutte le altre: se lo script non si fermasse davvero, i numeri riprodotti sarebbero falsi e sembrerebbero veri* |
| 107-122 | **«scritture con il moat ON per default»**: ogni fatto entra come claim a bassa fiducia · con un giudice llm iniettato **AUROC 0,96-0,97** (sonnet, SNLI held-out; fuori distribuzione **~0,81-0,90**, il CE libero **~0,82**) · funziona **senza llm e in qualunque lingua** col modello locale · **solo** se mancano sia l'llm sia il modello il gate **fail-open**, e lo dice con `L4-skipped` | `anti_confab_gate.py` · `docs/EVIDENCE-external-2026-07-19.md` **esiste** | `test_verimem_l4_no_source_advisory.py` (per `L4-skipped`) | ✅ **sul fail-open dichiarato** (l'avviso esiste ed è presidiato) · ⬜ **sugli AUROC**: nessun presidio li rilegge · ⚠️ **il «per default» è quello che la riga 24 smentisce alla porta** |
| 123-127 | **«ambito onesto del giudice CE-only»**: prende le contraddizioni di **valore/numero** e i confab fuori tema, **ma non tutte** — la run del **18/07** dava **0** fughe numeriche, la stessa il **25/08** ne dà **4** ed **esce 1**. *«Rieseguilo tu prima di fidarti di uno dei due numeri.»* | `benchmark/moat_multilingual_matrix.py` — **esiste** | **nessuno** | ✅ **e questa è la riga più onesta del README**: dichiara che **due esecuzioni dello stesso comando danno numeri diversi**, e non sceglie quello che conviene. ⬜ come misura |
| 128-142 | il **buco più grande, quantificato**: un'inferenza aggiunta plausibile che la fonte non enuncia passa — **25 su 48** ammesse (IT 54,2%, EN 50,0%), e **8 delle 48 coppie IT/EN prendono il verdetto OPPOSTO nelle due lingue, in entrambe le direzioni** · sostituzione di entità: **25% di fuga in spagnolo** (7 su 28), **7,1%** sull'intera matrice | `docs/stato-reale/banco-osservatore-il-tasso.py` **esiste** · `docs/EVIDENCE-stress-2026-07-18.md` **esiste** | **nessuno** | ✅ **sul metodo, ed è la cosa più difficile da scrivere**: la riga dice *«questo README lasciava senza numero proprio il buco più grande, mentre quantificava tutti i minori»*, e poi lo quantifica. Il verdetto per l'utente è scritto: *«su falsità per omissione il CE da solo è vicino a un lancio di moneta»* · ⬜ come misura |
| 143-150 | la **banda a due soglie**, **accesa per default** (`VERIMEM_CE_BAND_ENFORCE=0` la spegne): taglia la fuga spagnola **6,2% → 1,8%**, **zero** nuovi blocchi falsi, al costo di **1 su 19** di over-review · e **scala a una aggiudicazione llm OFFLINE-FIRST** (ollama, `qwen2.5:7b-instruct`, **AUROC 0,858** contro **0,829** del CE) | `grounding_gate.py` · `doctor.py` (la leva esiste in **2 punti ciascuno**) | `test_le_leve_che_il_readme_insegna_hanno_effetto.py` | ✅ **la leva esiste e un presidio verifica che le leve del README abbiano effetto** · ⬜ **sui numeri della banda** (6,2 → 1,8, 1/19, 0,858 vs 0,829): nessun presidio li rilegge |

### 📌 Il reperto di questo blocco

**La promessa più forte della pagina non ha un presidio.** Le righe 95-103
dicono *«non fidarti: rifallo tu, un comando per dataset»* — ed è la forma
migliore in cui un prodotto può dare un numero. Ma **nessun test esegue
`repro_c10.sh` né verifica che si fermi davvero** quando manca il modello: se un
giorno smettesse di fermarsi, produrrebbe un numero *plausibile e falso*, che è
esattamente il danno che quella riga esiste per impedire.

🔑 **E il blocco contiene la riga più onesta del README** (123-127): dichiara che
**la stessa run dà 0 fughe il 18/07 e 4 il 25/08**, e invece di scegliere il
numero comodo dice *«rieseguilo prima di fidarti di uno dei due»*. *Un prodotto
che pubblica la propria varianza è più credibile di uno che pubblica il minimo.*

---

## Righe 151-215 — la banda, l'evoluzione della stessa fonte, la ricevuta

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 151-156 | la **scala di aggiudicazione**: ollama locale (preferito, offline) → `claude` CLI su PATH (abbonamento, nessuna chiave) → altrimenti **held for review**; *«un verdetto illeggibile non ammette mai»*; `VERIMEM_BAND_LLM=0` esce | `band_escalation.py` (`ENGRAM_BAND_LLM`) + l'alias `_compat.init_env_aliases()` | `test_le_leve_che_il_readme_insegna_hanno_effetto.py` | ✅ **e l'ho verificato dopo aver quasi sbagliato**: vedi il riquadro sotto |
| 156-158 | *«quel residuo — **lo stesso 1,8%** di sopra, non una seconda misura»* | — | **nessuno** | ⚠️ **⬜ e con un avvertimento**: **venti righe sotto** (165-166) lo stesso README dice che **oggi lo stesso comando riporta 5,4%**, e che l'1,8% era la run del **18/07**. ⇒ *chi legge la riga 145 o la 156 e si ferma lì prende un numero che il testo stesso dichiara superato.* Il README **non mente** — la riga 166 lo dice — ma **il numero comodo sta in cima e la sua scadenza venti righe sotto** |
| 159-162 | **terzo limite misurato**: il CE **rifiuta fatti veri** che richiedono aritmetica o conversione di unità/date (`0.5 g ⊢ 500 mg`, `two weeks before March 20 ⊢ March 6`) o una lingua a bassa risorsa | — | **nessuno** | ✅ **come dichiarazione** (è un limite scritto, non taciuto) · ⬜ come misura |
| 163-172 | **certificazione esterna**: 0% false-block (**112/112** ammessi, ri-misurato 25/08) · **5,4% escape** · su **TruthfulQA heldout AUROC 0,829**, e al taglio di default **~24%** dei veri parafrasati rifiutati e **~18%** delle misconception plausibili passano | `docs/EVIDENCE-external-2026-07-19.md` **esiste** | **nessuno** | ✅ **sulla forma — ed è la riga più utile per chi deve scegliere**: *«il giudice CE-only è un filtro di contraddizioni strutturate ad alta precisione, non un rilevatore universale di verità»* · ⬜ sui numeri |
| 173-175 | `tag_beliefs=True` classifica un'asserzione non verificata come `user_belief`: **conservata ma fuori dal recall di default** finché non la chiedi (`search(..., include_beliefs=True)`) | `tag_beliefs` in **2** file · `include_beliefs` in **5** | **nessuno di specifico** | ✅ **il codice c'è su entrambi i lati** (scrittura e lettura) · ⬜ sul comportamento |
| 176-194 | **contraddizione fra fatti + evoluzione della stessa fonte, ON per default**: `100 € → 150 €` e il recall dà **solo il corrente**, il vecchio `superseded_by` il nuovo, *«mai una sovrascrittura silenziosa: la riga vecchia resta per la genealogia»* · il rilevatore **lessicale** copre numeri/versioni/date/negazioni · gli **scambi di entità** richiedono il livello **NLI semantico**, che **si accende da sé se il modello è già installato** | `supersession_policy.py` · `anti_confab_gate.py` · `benchmark/evolution_moat_vs_mem0.py` | `test_le_leve_che_il_readme_insegna_hanno_effetto.py` (per le leve) | ✅ **sulla supersessione** (verificata da @ws2 il 06/09 su SDK e MCP: `superseded_by` valorizzato, la lettura serve solo il nuovo) · ⬜ sui numeri della matrice |
| 195-207 | 🔑 **«limite noto, misurato sul NOSTRO corpus, non su un banco»**: quando due fatti sotto un topic misurano **cose diverse**, il più nuovo ritira uno che era vero — **171 coppie** con entrambi ≥90 dal giudice, **55 lette a mano, nessuna era un aggiornamento legittimo**; le guardie di *forma* coprono **70 su 171**, le altre **101 non hanno forma sintattica**; mitigazione: **un topic per misura**, con il numero — sopravvivenza **2348/2444** su topic usati una volta contro **230/338** su topic riusati | `supersession_policy.py` (le guardie) | **nessuno** | ✅ **ed è il paragrafo più onesto del prodotto**: un limite trovato **sul proprio corpus in produzione**, con quante coppie sono state **lette a mano**, quante la cura copre (**70**) e quante **no** (**101**), e una mitigazione con la sua misura. *Dichiara anche il proprio confine: «ciò che le separa è il significato, e una regola lessicale non lo vede»* |
| 209-215 | **ogni scrittura torna una ricevuta di aggiudicazione**: `{disposition, evidence_class, judge, score, threshold, margin, reason, confidence_tier}`; *«una quarantena è un verdetto motivato, mai una caduta silenziosa»*; il `confidence_tier` è **la fiducia dello strumento, non un'affermazione di verità** | `confidence_tier` in **6** file · `evidence_class` in **3** | `test_verimem_l4_no_source_advisory.py` | ✅ **i campi esistono** · ⚠️ **ma vedi la riga 24**: sulla porta, `admitted` con `grounding` 99,9x su una self-claim **è** un verdetto motivato… e motivato male |

### 🪞 Il riquadro: quasi consegnavo un allarme falso, e la difesa era nel presidio

Il `grep` diceva che **tre leve insegnate dal README non esistono nel codice**:
```
grep -rn "VERIMEM_BAND_LLM|VERIMEM_SEMANTIC_CONFLICT|VERIMEM_SUPERSEDE_SAME_SOURCE" verimem/
   ->  nessuna riga
```
Sembrava il reperto della serata: *«l'utente imposta la leva del README e non spegne niente»*.

**È falso.** `verimem/_compat.py` espone `init_env_aliases()`, chiamata da
`__init__.py:45`, che **rispecchia `VERIMEM_*` / `HIPPO_*` ↔ `ENGRAM_*`**: nel
codice le leve si chiamano `ENGRAM_…` e **la forma del README funziona**.

🔑 **E il presidio che lo prova è scritto meglio di come l'avrei scritto io**:
`test_le_leve_che_il_readme_insegna_hanno_effetto.py` dichiara in testa che la
verifica ovvia — *imposta `VERIMEM_X`, guarda se compare `ENGRAM_X`* — **passa
sempre e non prova niente**, e lo dimostra con
`VERIMEM_QUESTA_NON_ESISTE_DAVVERO=7777`. Quindi misura **l'effetto**
(`_mode_con(VERIMEM_BAND_LLM="0") == "off"`), non la presenza della stringa.

⇒ **Cercare un nome nel codice non basta quando c'è un livello di alias.** Se
avessi pubblicato il grep, avrei consegnato un allarme falso su tre righe della
vetrina — *ed è la seconda volta oggi che la difesa era già scritta da qualcun
altro, prima della mia accusa.*

---

## Righe 216-275 — quarantena reversibile, provenienza, astensione, documenti

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 217-231 | **«un blocco sbagliato è visibile e reversibile»**: `Memory.quarantine_log()` elenca i trattenuti · con `explain=True` ogni riga dice **quale schermo l'ha fermata e cosa la farebbe passare**, **ricalcolato sul momento** *(quindi vale anche per claim fermati molto prima)* · `Memory.restore(fact_id, reason=…)` la rimette nel recall · stessa coppia su MCP | `quarantine_log` (1 file) · `restore` (7) | **nessuno di specifico** | ✅ **le API esistono su entrambe le superfici** · ⬜ sul comportamento |
| 224-226 | 🔑 **il limite dichiarato dentro la funzione**: un claim fermato dal controllo di **entailment sulla fonte** è **l'unico che non si può spiegare a posteriori** — *«la fonte non è conservata»* — e **lo dice invece di non restituire nulla** | — | **nessuno** | ✅ **come forma**: è un «non lo so» scritto nel posto giusto, cioè **dentro la risposta**, non in una nota. *(È la stessa mancanza che @ws6 ha in carico come T32: «la fonte non si conserva».)* |
| 227-231 | **restore è un override guardato, non una porta di servizio**: rifiuta un fatto **superato** (*«non resuscita mai un valore ritirato»*) e **ri-esamina proposizione E topic** per prompt-injection — *«un payload di esfiltrazione quarantinato resta quarantinato anche se un chiamante ne passa l'id»* | `supersession_policy.py` · il ri-esame | **nessuno di specifico** | ⬜ **NON MISURATO, e questa è la riga che vorrei presidiata per prima**: è l'unica del blocco che descrive una **difesa contro un attaccante**, e una difesa senza presidio è una promessa |
| 232-241 | **provenienza a ogni lettura**: le risposte citano da dove viene ogni fatto · `TrustReport` spiega *come il sistema sa* · **il ranking si dichiara**: `hippo_facts_recall` torna un campo `ranking` (`{"rerank": "timeout_cold", "fusion": "timeout"}` quando un processo freddo ha tenuto l'ordine del bi-encoder) · *«ogni stadio degrada sotto un budget invece di appendere il chiamante, quindi la stessa domanda può legittimamente dare un insieme diverso a freddo — e quella differenza adesso è dichiarata, non silenziosa»* | `TrustReport` (6 file) | `test_la_promessa_della_citazione_vale_su_ogni_superficie.py` | ✅ **sulla citazione** · ✅ **come metodo sul `ranking`**: *dichiarare che un risultato può cambiare a freddo, invece di lasciarlo scoprire, è la stessa onestà del banner del warmup* · ⬜ sul campo `ranking` (nessun presidio lo rilegge) |
| 242-244 | **storia bi-temporale**: quando è accaduto e quando l'abbiamo saputo; `as_of`, le transizioni, l'audit di ogni revisione | `temporal_context.py` · `as_of` sulle porte | i presidi di `as_of` (dalla 0.7.7) | ✅ — *e la 0.7.7 ha aggiunto proprio che `as_of` morde sulle porte ordinarie* |
| 245-266 | **astensione per disegno**, e **le tre porte fanno cose diverse**: gateway/console **filtrano** · MCP **serve e segnala** (`sotto_il_pavimento`, `trattenuti`) · l'SDK espone gli stessi due segnali ed è **permissivo di default** perché uno store nuovo non si astenga troppo · *«solo `explain`/`trust_report` rifiutano di rispondere: `recall` e `search` tornano sempre i fatti più vicini — la segnalazione è come distingui "più vicino" da "giusto"»* | `sotto_il_pavimento` (4 file) · `trattenuti` (4) · `MIN_RELEVANCE` (6) | **nessuno di specifico** | ✅ **i campi esistono su tutte e tre** · ✅ **come metodo, ed è raro**: il README **non dice «il prodotto si astiene»**, dice **cosa fa ciascuna porta**, che è la sola forma utile a chi deve scegliere la porta |
| 260-266 | **«l'astensione ha due livelli e il secondo ha una dipendenza»**: il pavimento di rilevanza gira ovunque; il giudice di **sufficienza** — quello che prende il fatto in tema che **non risponde** — richiede un provider LLM. Senza, `get_llm()` torna un mock, `verify.sufficiency` riporta **`no_provider`**, e il dossier torna senza | `no_provider` (1 file) | **nessuno** | ✅ **ed è un limite dichiarato bene**: dice **cosa perdi** (*«la presa dell'in-tema-ma-sbagliato»*) e **cosa resta** (*«il pavimento continua ad astenersi fuori dominio»*) |
| 267-275 | **memoria documentale citata sul testo indicizzato**: `indexed_text[start:end] == passage` · promozione a memoria **attraverso il gate** · *«gli offset sono esatti sull'indice… non sono la promessa che il file originale si apra ancora, perché i percorsi sono conservati come dati»* · raggiungibile da **tutte e tre** le superfici | `index_document` (2 file) · `search_documents` (1) · `verimem index` / `search-docs` sulla CLI | **nessuno di specifico** | ✅ **le API esistono su tutte e tre** · ✅ **il limite sui percorsi è dichiarato al punto giusto** |

### 📌 Un'avvertenza di leggibilità (non un difetto): due nomi per la stessa cosa

La riga 274 nomina i tool MCP come **`verimem_document_*`**. Nel codice, **di
default**, sono **`hippo_document_*`** (`mcp_server.py:1945`): il prefisso
`verimem_` esiste **solo** con `VERIMEM_TOOL_NAMESPACE=verimem`
(`mcp_server.py:7748`).

**Non è un errore**: alla riga **484** la configurazione d'esempio del README
**imposta quella variabile**, e alla **492** dice *«togli l'entry per tenere i
`hippo_*` legacy»*. Chi segue il README dall'inizio ottiene davvero i nomi
`verimem_*`.

⚠️ **Ma la spiegazione sta 210 righe dopo il primo uso**, e nel frattempo la
pagina usa **entrambi i prefissi** (`hippo_*` alle righe 227, 235, 353, 611-612,
749; `verimem_*` in cinque punti). ⇒ **stessa forma dell'1,8% contro il 5,4%: la
chiave che rende leggibile un nome sta lontana dal punto in cui serve.**

🪞 *Terza volta oggi che stavo per scrivere un ❌ e la difesa era già nel testo:
qui bastava leggere 210 righe più avanti.*

---

## Righe 276-340 — la coda delle «Features»

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 277-279 | **import col consenso**: le conversazioni sono **elencate prima**, niente entra senza una selezione esplicita | `import` sulla CLI | **nessuno di specifico** | ⬜ *(il codice c'è; il «niente senza selezione» non è presidiato)* |
| 280-283 | **auto-memoria opt-in**: `AutoMemory(memory).observe(role, text)` passa dalla **stessa** pipeline delle scritture esplicite · *«opt-in per costruzione: se non la istanzi, non esiste»* | `AutoMemory` (1 file) | **nessuno** | ✅ **la classe esiste** · ✅ **come forma**: «opt-in per costruzione» è verificabile leggendo — non c'è un default che la accende |
| 284-288 | **contachilometri della fiducia**: `m.trust_stats()` / `verimem stats`, contatori persistenti di ciò che il gate **ha fatto davvero** · *«azioni osservabili, non affermazioni di marketing; nessun testo di fatto finisce nel contatore»* | `trust_stats` (2 file) | **nessuno di specifico** | ✅ **l'API esiste su SDK e CLI** · ✅ **come forma**: la riga dichiara anche **cosa il contatore NON contiene** (il testo), che è una promessa di riservatezza verificabile |
| 289-291 | **oblio vero**: `delete(purge_history=True)` toglie il fatto **e la sua catena di supersessione**; il dato non riemerge da storia o time-travel | `purge_history` (6 file) | `test_fact_forget_scope_r3.py` | ✅ |
| 292-299 | **fiducia per fonte, due canali** *(dietro flag)*: reputazione da accordo fra fonti e da esito; **decide il canale più debole** · il clustering di indipendenza **collassa copie e colluders a un solo testimone** · riprodotto su HaluEval, 3/3 semi: un **cartello di 4 id** che si autoconferma a **0,90** scende a **0,20**, le fonti oneste risalgono a **0,95** | `source_trust.py` | **nessuno** *(il grep di `0.90` trova 109 file: è rumore, non presidio)* | ⬜ **NON MISURATO** · ⚠️ **e c'è un fatto che questa mappa deve dire**: `client.py:783-796` documenta che il **gate su source-trust è stato RIMOSSO il 02/09**, misurato *«0 scritture marcate su 17 279, tabella `source_trust` con 0 righe»*. ⇒ **la riga dice «(flag-gated)» e non dice che il registro che la alimenta è vuoto in produzione** |
| 300-303 | **etichette epistemiche**: `proven` (prova verificabile a macchina) · `unbeaten` (retto fino a un limite dichiarato, **che solo cresce**) · `refuted` (controesempio nominato, assorbente) · *«"retto fino a 10^6" e "provato" non si confondono mai»* | `unbeaten` (7 file) | **nessuno di specifico** | ✅ **le tre etichette esistono nel codice** · ✅ **come forma**: la distinzione fra *provato* e *non ancora smentito* è la cosa che quasi nessun prodotto scrive |
| 304-313 | **conoscenza derivata, dallo stesso cancello**: l'anello di composizione deriva fatti nuovi dai verificati, li passa **dallo stesso gate**, e ammette i sopravvissuti **firmati** (`actor:composer` — *«le scritture del motore non testimoniano mai per sé stesse»*), **tracciati** (`derives_from`, ritrattabili se un genitore cade) · il demone **rifiuta di comporre** quando le scritture del motore dominano già il flusso recente (*guardia contro l'auto-eco*) | `actor:composer` (3 file) · `derives_from` (7) · `compose_daemon` (1) | **nessuno di specifico** | ✅ **tutti e tre i pezzi esistono** · ✅ **come forma**: *«il motore non testimonia per sé»* e la guardia contro l'auto-eco sono due difese **contro noi stessi**, ed è raro che un prodotto le scriva |
| 314-326 | **guardiano in lettura**: quando lo store ha una verità meglio garantita sullo stesso soggetto, la lettura **corregge** citando entrambi i fatti (`correct_read` → ACCEPT / CORRECT / ABSTAIN) · con **sonde attive** che costruiscono la domanda che **falsificherebbe** un fatto — *«lo store falsifica sé stesso invece di aspettare che arrivi una contraddizione»* | `correct_read` (2 file) | **nessuno** | ✅ **il codice esiste** · 🔑 **e la riga si limita da sé, con il numero**: *«"lo stesso soggetto" si risolve leggendo una copula, quindi il confronto avviene solo su fatti con quella forma — **7 su 5194 fatti vivi** sul nostro corpus, che è prosa»*, e sul resto la lettura torna **`not comparable — no conflict search ran`**, cioè *«il guardiano dice quando non ha guardato»*. **Una capacità di punta che dichiara di applicarsi allo 0,13% dei casi**: `grep 5194 tests/` → **0 file**, quindi il numero non è presidiato, **ma è scritto** |
| 327-330 | **mappa dell'ignoranza**: «non lo so» diventa «ecco **cosa** mi manca» — ogni domanda senza risposta è classata (niente prove / sotto il pavimento / prove in quarantena / conflitto vivo) con la fonte concreta che la chiuderebbe | `ignorance_map` (5 file) | **nessuno di specifico** | ✅ **il codice c'è** · ✅ **come forma**: è l'astensione che diventa **azionabile** |
| 331-335 | **firma di provenienza** *(opt-in)*: un HMAC infalsificabile di **chi parla** dentro il ref di provenienza — *«autenticità del contenuto E del canale, le due metà che nessun filtro deterministico di contenuto può certificare da solo contro un avversario adattivo»* | `provenance` / HMAC | **nessuno di specifico** | ⬜ · ⚠️ **stessa famiglia della riga 227**: descrive una **difesa contro un avversario** e non ha un presidio |
| 336-338 | **local-first**: SQLite, embedding locali, LLM iniettabile; gira **air-gapped** (`verimem airgap` verifica la configurazione a zero uscite) | `cli.py` (`airgap`) | `test_cli_airgap.py` | ✅ **eseguibile e presidiato** |

### 📌 Il reperto di questo blocco

**La riga 292-299 vende una capacità il cui registro è vuoto in produzione.** Il
README la marca *(flag-gated)* — corretto — ma **non dice** ciò che il codice
dichiara di sé a `client.py:783-796`: il gate su source-trust **è stato rimosso
il 02/09**, con la misura accanto — *«0 scritture marcate su 17 279, `source_trust`
con 0 righe, `source_trust_observe` chiamata da 4 banchi e 5 test e da **zero
porte del prodotto**»*. ⇒ **La capacità non è spenta da un flag: non ha mai avuto
materiale.** *Un lettore che sceglie il prodotto per quel paragrafo compra una
cosa che nel suo store non succederà.*

🔑 **E il contrappeso, che vale la stessa attenzione**: la riga 322-326 **dichiara
da sé che il guardiano in lettura si applica a 7 fatti su 5194** — lo **0,13%** —
e che sul resto risponde *«not comparable — no conflict search ran»*. **Una
capacità di punta che scrive il proprio ambito con il numero, invece di lasciarlo
intendere.** *È il modello a cui la riga 292 dovrebbe assomigliare.*

---

## Righe 341-400 — Install, la tabella per porta, il blocco PyPI, il costo su disco

> ⚠️ **Le righe 348-359 e 361-387 le ho scritte io oggi.** Le mappo con lo stesso
> metro delle altre — anzi, con un po' più di severità: *chi scrive una riga non
> è il giudice migliore di quella riga, ed è il motivo per cui la mappa dichiara
> chi ha scritto cosa.*

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 341-346 | `pip install verimem` + `verimem warmup` **facoltativo**, con scritto che senza *«la scrittura è giudicata lo stesso — paga solo il download una volta»* | `cli.py` (`warmup`) | `test_il_banner_in_cima_al_readme_non_puo_dire_che_il_moat_e_spento.py` | ✅ **presidiata dall'08/09**: il presidio vieta in **tutto** il README la frase contraria (esteso oggi da me, RED→GREEN falsificato) |
| 348-353 | **la tabella per porta** — **CLI**: giudicata in processo in **~22 s** senza daemon (misura del 07/09) · **MCP**: delega per costruzione, e **se il daemon manca la scrittura è memorizzata NON GIUDICATA** (`stored: true`, `layers: ['L4-skipped']`), *«leggi quel campo: `admitted` da solo non vuol dire giudicato»* | `preload.py` (delegate-only) · `mcp_server.py:15764` | **nessuno** | ⬜ **NON MISURATO da un presidio** — *ed è una riga mia: l'ho scritta stamattina e **non le ho dato un test**. La stessa lezione che ho scritto tre volte oggi («una nota non è un presidio») vale per la riga che ho appena aggiunto io.* ✅ sui fatti: entrambi i comportamenti sono misurati (@ws1 07/09; il codice delegate-only) |
| 355-359 | **sull'SDK non abbiamo una risposta stabile**: la stessa `Memory().add(..., source=…)` è tornata **giudicata** (`99.9`) e più tardi **non giudicata**, col daemon **verificato raggiungibile** in entrambi i casi. *«Lo stiamo misurando. T26a e T29.»* | — | **nessuno** | ✅ **come forma, ed è il pezzo di cui vado più sicura**: è un **non-sapere scritto in vetrina**, con la misura che lo prova e il ticket che lo insegue. ⬜ come misura *(la causa non è isolata: quattro spiegazioni escluse)* |
| 361-376 | il **commento HTML di rilascio**: dice che questo file **è la pagina di PyPI**, che i due numeri invecchiano, che **non vanno aggiornati a mano** perché `test_la_vetrina_dice_l_ultima_release_giusta.py` li lega ai tag — e racconta l'errore dell'08/09 (la release di luglio) **e la mia correzione** (le soglie non erano false) | `tests/test_la_vetrina_dice_l_ultima_release_giusta.py` | **sé stesso** | ✅ **ed è la riga più utile che ho scritto oggi**: prima lì c'era una **nota** che chiedeva di ricordarsene, e non è bastata. *Adesso al suo posto c'è un test che diventa rosso da solo — e il commento dice perché.* |
| 377-382 | **cosa serve PyPI oggi**: ultima release **0.7.6 (2026-09-04)**, `main` **più di 150 commit** avanti (misurato: `git rev-list --count v0.7.6..main` = **189**) · *«la cifra è scritta come pavimento apposta — un pavimento diventa solo più vero, un conteggio esatto è scaduto entro l'ora»* | — | `test_la_vetrina_dice_l_ultima_release_giusta.py` (versione = ultimo tag) · `test_la_soglia_in_commit_del_readme_e_ancora_vera` (soglia sotto il vero) | ✅ **due presidi, uno per la versione e uno per la soglia** — *e il secondo è quello che oggi mi ha corretta* |
| 384-387 | *«`docs/stato-reale/` misura lo scarto fra questa pagina e l'artefatto pubblicato… **leggi lo SHA in testa a ogni nota**: alcune misurano `main`, che si muove»* | `docs/stato-reale/` (esiste) | **nessuno** | ✅ **come forma**: dice al lettore **come** leggere un documento datato, invece di lasciargli credere che valga oggi |
| 388-400 | **cosa costa su disco**: `pip install` **~1,0 GB** (74 pacchetti, torch più della metà) · primo `warmup` **~2,3 GB** · **totale ~3,3 GB** · misurato su Windows/Python 3.13, *«su Linux la wheel di torch è diversa, quindi la prima riga cambia»* · *«sono dimensioni **su disco dopo l'installazione**, non di download — il download è più piccolo (221 MB compressi) e per i modelli **circa** lo stesso, **anche se quest'ultima parte non è stata misurata**»* | — | `test_il_readme_e_la_cli_dicono_lo_stesso_peso.py` · `test_la_vetrina_nomina_i_modelli_che_scarica.py` | ✅ **presidiato, e con una storia che vale**: quel test nasce perché README e CLI davano **due numeri diversi per lo stesso modello** — *«656 MB» / «711 MB» / «~746 MB»* — e **nessuno dei due era sbagliato**: `746 058 368 byte` sono **746,1 MB** in base 10 e **711,5 MiB** in base 2. **Stesso byte, due unità.** ✅ **e l'ultima frase dichiara ciò che NON è stato misurato** (i 221 MB non hanno presidio: `grep` → nessuno) |

### 📌 Il reperto di questo blocco, e riguarda me

**La riga per porta che ho scritto stamattina (348-353) non ha un presidio.**
È entrata su `main` con `5ac8d9f1`, dice una cosa vera e misurata, e **nessun
test la tiene ferma**: se domani la porta MCP smettesse di delegare, quella riga
resterebbe lì a dire il contrario e **nessuno se ne accorgerebbe**.

⇒ *È esattamente la forma che ho scritto tre volte oggi — «una nota non è un
presidio» — applicata alla riga che ho appena aggiunto io.* **Cerca su di te la
forma che hai appena trovato**: quarta volta che paga.

🔑 **E il contrappeso, nello stesso blocco**: il commento di rilascio (361-376)
è il caso opposto. Lì una **nota** c'era dal 26/08 e non è bastata; oggi al suo
posto c'è **un test che diventa rosso da solo**, e il commento spiega perché.
*La differenza fra le due righe non è la buona volontà: è un file di test.*

---

## Righe 401-465 — tempi, terzo modello, e il **Quickstart**

| riga | claim | dove sta | presidio | verdetto |
|---|---|---|---|---|
| 402-404 | **quanto ci mette**: `verimem warmup --no-gate` **2 min 45 s** su cache pulita · *«il warmup completo scarica circa tre volte tanto e **non è stato cronometrato**, quindi tratta il totale come ignoto, non come tre volte quello»* | `cli.py` (`--no-gate`, 1 file) | **nessuno** | ✅ **come forma, ed è una riga che vale citare**: misura una parte, dichiara di **non** aver misurato l'altra, e **vieta esplicitamente l'estrapolazione** che il lettore farebbe da solo. *«Tratta il totale come ignoto» è più utile di un numero inventato per simmetria.* |
| 406-408 | il modello del giudice è **746 MB** e ne occupa **746** su disco — *«lo stesso numero che stampa la CLI»* · e la spiegazione: **decimali (10⁶)**, `746 058 368` byte, che uno strumento in **MiB (2²⁰)** mostra come **711** — *«stessi byte, unità diverse»* | `cli.py` (`warmup --help`) | `test_il_readme_e_la_cli_dicono_lo_stesso_peso.py` | ✅ **presidiato, e nato da un difetto vero**: README e CLI davano tre numeri (`656` / `711` / `746`) e **nessuno era sbagliato** |
| 410-412 | il **reranker è un terzo modello, acceso di default**: `warmup` scarica i suoi **470 MB** salvo `VERIMEM_RECALL_RERANK=0` · *«è la leva di recall di stadio 2, **non fa parte del moat** — spegnerlo costa qualità di ranking sulle query corte e nient'altro»* | `RECALL_RERANK` (1 file) | `test_le_leve_che_il_readme_insegna_hanno_effetto.py` | ✅ **la leva esiste ed è presidiata per effetto** · ✅ **come forma**: dice **cosa costa spegnerla** e **cosa non tocca** |
| 421-427 | il commento del Quickstart: senza giudice le scritture entrano **con un `L4-skipped` esplicito, mai in silenzio**, *«e l'assert qui sotto fallirebbe — `doctor` ti dice esattamente perché»* · e il costo vero: *«senza nulla che le giudichi, **la seconda scrittura ritira la prima**, quindi la confabulazione resta l'unico fatto vivo»* | `anti_confab_gate.py` · `supersession_policy.py` | `test_verimem_l4_no_source_advisory.py` | ✅ **e questa è la riga meglio scritta del Quickstart**: non dice «serve il giudice», dice **cosa succede senza** — *e la conseguenza (la confabulazione sopravvive alla verità) è il danno vero, non la mancanza della spunta* |
| 428-436 | `Memory()` **senza argomento apre lo STESSO store** di CLI e MCP · passare un percorso è **relativo alla directory corrente** e lo riceve **solo l'SDK**, quindi `verimem recall` da altrove risponde *«no facts found» con exit 0* — **ma adesso dice dove ha guardato** · *«per puntare la CLI a un secondo store: `remember`, `recall`, `search`, `get` e `list` prendono tutti `--db`»* | `client.py` · `cli.py` | `test_la_cartella_dati_promessa_dal_readme.py` · `test_le_porte_aprono_lo_store_che_indichi.py` | ✅ **ed è T16 curato**: la riga racconta il difetto (*«trasforma un mistero in un refuso»*) e la sua cura · ⚠️ **ma vedi T30**: i cinque comandi elencati sono giusti, **e `save` non è fra loro** — il README **non dice** che il comando che insegna alla riga 352 e alla 510 **non accetta `--db`** |
| 438-444 | **il moat dal vivo**, tre righe eseguibili: stessa fonte, due scritture; `"Analytics runs on Postgres."` **ammessa**, `"Analytics runs on MongoDB."` **quarantinata**, con `assert r["status"] == "quarantined"` e il commento *«conservata ma FUORI dal recall di default — il tuo agente non la ripeterà mai come verità»* | `anti_confab_gate.py` | `test_moat_on_by_default.py` · `test_gateway_moat_default.py` · `test_adjudication_receipt.py` · `test_il_referto_del_moat_spento_dice_cosa_si_perde.py` | ✅ **quattro presidi nominano questo caso** — *è il claim più presidiato della pagina, ed è giusto che sia questo: è l'unico pezzo di README che un lettore può **incollare ed eseguire** per vedere la promessa centrale accadere* |
| 446-452 | `Memory(llm=my_llm)` per il giudice di qualità massima · i **preset** `balanced` / `strict` / `permissive` con la descrizione di ciascuno | `preset` (2 file) · `grounding_llm` (4) | **nessuno di specifico** | ✅ le API esistono · ⬜ sul comportamento dei preset |
| 454-458 | **memorizza una conversazione**: i fatti sono estratti **atomicamente** e passano dal gate · *«l'estrazione da dialogo grezzo richiede l'llm; `user_name` rende l'identità fornita dall'app il soggetto dei fatti»* | `user_name` (7 file) | **nessuno di specifico** | ✅ **il codice c'è** · ✅ **come forma**: dichiara **la dipendenza** (serve l'llm) nel punto in cui mostra l'esempio, non in fondo |
| 460-464 | **provenienza senza LLM**: `verified_by` registra **da dove** viene il claim, *«è mostrato a ogni lettura e **non può essere falsificato in uno stato di fiducia più alto** — una ricevuta auto-citata non diventa mai "verified": il segnale di fiducia è l'esito del gate + la provenienza, non un distintivo auto-asserito»* | `verified_by` (**65** file) | le istruzioni del server MCP lo ripetono | ✅ **ed è una difesa contro l'utente stesso**, scritta bene: dice cosa `verified_by` **non** compra. *(⚠️ E il gate lo sa: nel messaggio del server MCP c'è la stessa frase — «`verified_by` registra CHI garantisce e non fa girare questo controllo».)* |

### 📌 Il reperto di questo blocco

**Il claim più presidiato della pagina è quello giusto.** Le tre righe del
Quickstart (438-444) — *stessa fonte, due scritture, la seconda quarantinata* —
sono nominate da **quattro** file di test. È l'unico pezzo di README che un
lettore può **incollare ed eseguire** per vedere la promessa centrale accadere, e
qualcuno ha deciso che quello dovesse reggere più di tutto il resto. *Nel resto
della pagina i ⬜ sono 37; qui ci sono quattro presidi su tre righe.*

⚠️ **E l'avvertenza che ne discende**: quelle tre righe usano la **porta SDK**.
La riga 24 — *«un claim che la fonte apertamente contraddice non torna come
verità»* — è **falsa alla stessa porta** per una **forma diversa** di falso: la
self-claim in coda a un fatto vero (6 su 7 ammesse). ⇒ **Il Quickstart mostra la
metà della promessa che funziona.** *Non è una bugia: è una scelta di esempio —
ma la forma che passa non compare da nessuna parte in questa pagina.*

---

## Righe 466-530 — la coda del Quickstart SDK, il Quickstart MCP, la CLI, la governance

| righe | il claim | dove sta nel codice | chi lo guarda | verdetto |
|---|---|---|---|---|
| 466-467 | *«Search — optionally with history context»* → `m.search(...)` | `verimem/client.py` | `tests/test_client_sdk.py` | ✅ |
| 468 | `m.search(..., as_of=<epoch>)` — la ricerca **a un momento passato** | `as_of` in `client.py`, `gateway.py`, `continuity.py`, `cli.py` | `test_as_of_sulle_porte_ordinarie.py`, `test_deep_recall_asof.py`, `test_il_dato_cancellato_non_riemerge.py` | ✅ |
| 470-471 | *«Ask HOW the system knows: evidence dossier or an explicit abstention»* → `m.explain(...)` | `def explain` in `client.py`, `gateway.py`, `remote.py` — **tre porte** | `.explain(` in 6 file; l'astensione ha i suoi: `test_abstention_is_on_by_default.py`, `test_abstention_ce_gate.py` | ✅ |
| 474-488 | il blocco `.mcp.json` da incollare: `"command": "verimem"`, `"args": ["mcp"]`, `VERIMEM_HOSTED`, `VERIMEM_TOOL_NAMESPACE` | il sottocomando esiste: `verimem/cli.py:2524` `def mcp()` | `test_mcp_tool_namespace_brand.py`, `test_verimem_offline_flag.py`, `test_config_data_dir.py` | ✅ |
| 490-493 | i quattro tool nominati (`verimem_remember`, `verimem_facts_recall`, …) e *«Drop the entry to keep the legacy `hippo_*` names — both dispatch to the same tools»* | `mcp_server.py` (rinomina a runtime) | 🌟 `test_mcp_tool_namespace_brand.py:19` si chiama **`test_verimem_tool_namespace_from_readme_renames`** e asserisce `{"verimem_remember", "verimem_facts_recall"}`; `:36` asserisce che senza la variabile il nome torna `hippo_remember` | ✅ |
| 495-496 | *«every MCP client receives a usage guide on connect (the `instructions` field of the initialize response)»* | `mcp_server.py:1683` `instructions=VERIMEM_AGENT_GUIDE` | 🌟 `test_agent_guide_single_source.py:12` — **un'uguaglianza**, non una parola cercata: `create_initialization_options().instructions == VERIMEM_AGENT_GUIDE` | ✅ |
| 497-498 | *«`verimem agent-guide` prints **the same** guide»* | `verimem/agent_guide.py`, `cli.py` | il presidio c'è ma è **più debole di un anello**: `test_cli_agent_guide_prints_the_guide` cerca **quattro token** nell'output (`moat`, `verimem_remember`, `mcpServers`, `abstention`), non l'uguaglianza | ⬜ *(vedi reperto ①)* |
| 503 | `verimem index contract.pdf` | `cli.py` | `test_i_comandi_che_il_readme_insegna_esistono.py` | ✅ |
| 504 | `verimem search-docs "…"` — *«passages with file + offset citations»* | `cli.py`, `client.py` | `test_cli_docs.py`, `test_i_documenti_non_passavano_dal_reranker.py`, `test_i_comandi_che_il_readme_insegna_esistono.py` | ✅ |
| 505-506 | `verimem import conversations.json` — *«imports nothing until you pass `--ids` or `--all`»* | `cli.py`, `import_conversations.py` | il comando sì; **`--ids` non compare in nessuna asserzione** di `test_import_ux.py` (solo `--all-matching`, nel docstring e nel corpo) | ⬜ |
| 507-508 | `--project` · `--since` · `--all-matching` | `cli.py`, `import_conversations.py` | `test_import_ux.py` | ✅ |
| 509 | `verimem trust "…" --verified-by ci:main:green` | `cli.py`, `l1_tested_detector.py` | `test_cli_trust.py`, `test_cli_facts_add.py`, `test_il_quarto_canale_di_scrittura.py` | ✅ |
| 510-513 | `verimem save --asserted-at` e la prosa che spiega **perché**: *«WHEN the fact is true, distinct from when you wrote it — this is what `as_of` travels over»* | `cli.py` | `test_save_puo_dire_quando_e_vero.py` e — col nome del difetto — `test_la_porta_principale_ignora_il_tempo_dell_evento.py` | ✅ |
| 514 | `verimem airgap` — verifica una **configurazione** a zero uscite | `verimem/airgap.py`, `cli.py`, `doctor.py` | `test_airgap.py`, `test_cli_airgap.py`, `test_airgap_no_egress.py` | ✅ |
| 515-517 | `verimem airgap --live` — *«PROVE it: audit every socket during a real write+search, exit 0 iff no egress»* | `airgap.py` | `test_airgap_live_probe.py` — **il nome del test è il nome della promessa** | ✅ |
| 521-524 | *«A fact disappears in TWO ways … the governance surface makes every decision visible and the wrong ones reversible, on every port (SDK, CLI, MCP, HTTP)»* | `cli.py`, `gateway.py` | 🌟 tre presidi, e sono **per porta**: `test_control_room_porte.py`, `test_il_breakdown_esce_da_ogni_porta.py`, `test_mismatch_su_ogni_porta.py` | ✅ |
| 526-527 | `facts retirement-log --counts` — *«the honest quartet: written / servable / retired / quarantined, formula included»* | `cli.py` | `--counts` compare in **un solo** file: `test_control_room_porte.py` | ✅ |
| 528-530 | `facts retirement-log` — *«who was retired, by whom, why — with the undo handle when reversible»* | `cli.py` | i presidi del comando ci sono; **la manopola di undo non l'ho seguita fino al comando che la consuma** | ⬜ |

### ① Il presidio più forte della pagina finora — e la ragione per cui è forte

`test_agent_guide_single_source.py:12` non cerca una parola nel testo: **asserisce
un'uguaglianza fra due oggetti**.

```
assert m.server.create_initialization_options().instructions == VERIMEM_AGENT_GUIDE
```

La promessa della riga 495 («ogni client MCP riceve la guida connettendosi») e la
promessa della 497 («la CLI stampa la stessa guida») non possono divergere in
silenzio, perché **sono lo stesso oggetto Python**. È la forma che ho chiesto
tutto il giorno — *una nota non è un presidio* — nella sua versione migliore.

⚠️ **E però l'anello CLI è più debole.** Il ramo `verimem agent-guide` è tenuto
da `test_cli_agent_guide_prints_the_guide`, che verifica la presenza di **quattro
token** nell'output. Un comando che stampasse una guida *diversa* contenente
`moat`, `verimem_remember`, `mcpServers` e `abstention` passerebbe. La parola del
README è **«the same»**: sul campo MCP è provata, sul ramo CLI è *sorvegliata*.
*(E c'è una seconda sfumatura: `AGENT_GUIDE_FULL.startswith(VERIMEM_AGENT_GUIDE)`
dice che la guida della CLI **estende** quella MCP — quindi «the same» è, alla
lettera, «la stessa più altro».)*

### ② Il quarto allarme falso che non pubblico — e stavolta cercavo il MIO difetto

Avevo il sospetto pronto, e aveva una forma già nota: **il presidio dei comandi
del README misura al livello del COMANDO, non dell'OPZIONE.** Si legge nel
codice —

```
citati = set(re.findall(r"`verimem\s+([a-z][a-z0-9-]{2,})", testo))
```

— cattura `save`, `import`, `airgap`; **non** cattura `--asserted-at`. Ed è
**esattamente il livello dove ieri ho trovato T30**: `verimem save … --db` →
`Error: No such option: --db`. Comando presente, opzione assente: un presidio
fermo al comando avrebbe detto verde.

Ho contato le opzioni che queste sedici righe insegnano, e sono cinque:
`--all-matching` → `test_import_ux.py` · `--verified-by` → `test_cli_trust.py` ·
`--asserted-at` → `test_save_puo_dire_quando_e_vero.py` · `--live` →
`test_airgap_live_probe.py` · `--counts` → `test_control_room_porte.py`.
**Cinque su cinque hanno un presidio proprio.** Il buco che stavo per annunciare
non c'è: la copertura è distribuita, non centralizzata.

Resta **una** riga scoperta e la scrivo perché è vera: `--ids` (riga 505) non
compare in nessuna asserzione. Un'opzione su sei, non un sistema senza difese.

🔑 **Quarta volta oggi su quattro: la difesa era già scritta.** E stavolta il
sospetto veniva da un difetto **mio**, trovato ieri, applicato a un presidio
altrui — cioè dal lato in cui l'errore costa di più: *avrei accusato con
l'autorità di chi «l'ha già visto succedere».*

### ③ Il blocco è il più sano della pagina, e ha una spiegazione

Quindici ✅ su diciotto claim. Non è che questa parte sia scritta meglio: è che
**qui il README insegna comandi**, e un comando è una cosa che un test può
invocare. I ❌ e i ⬜ della prima metà stanno dove il README fa **affermazioni sul
mondo** — un tasso, un confronto, una garanzia. La differenza fra le due metà
della pagina non è la cura di chi scrive: è che *una promessa eseguibile si
presidia da sola, una promessa numerica no.*

---

## Righe 531-595 — la governance, la console della fiducia, il self-host

| righe | il claim | dove sta nel codice | chi lo guarda | verdetto |
|---|---|---|---|---|
| 531-533 | `verimem facts undo <op_id>` — annulla un ritiro | `cli.py:3719` `@facts_app.command("undo", help="Reverse a destructive op by its handle: a forget OR a retirement.")` — **l'help dice la stessa cosa del README** | i presidi del ritiro sono nove file, fra cui `test_il_ritiro_non_diceva_chi_e_stato.py` | ✅ |
| 531-532 | *«the lost fact comes back SERVABLE **and the newer one stays alive**»* — cioè **entrambi vivi** dopo l'undo | — | non ho seguito un presidio fino a questa coesistenza | ⬜ |
| 535 | *«Write receipts carry the handles too (`superseded_undo_ops` on `add()`)»* | `client.py`, `gateway.py` | un solo file lo nomina, e per un altro scopo: `test_flow_isolamento_tenant.py` | ✅ |
| 536 | *«every retirement emits a `flow.supersession` event»* | `anti_confab_gate.py`, `client.py`, `semantic.py` | `test_flow_forget.py`, `test_il_governo_e_acceso_di_default.py`, `test_flow_manutenzione_notturna.py` | ✅ |
| 536-537 | l'Engine Room `/ui/engine` mostra le coppie **con undo/restore a un clic** | `cli.py`, `flow_events.py`, `webui/engine.css` | la pagina sì (`test_gateway_flow_events.py`); **il clic di undo no** | ⬜ |
| 538 | il link a `docs/GOVERNANCE.md` | il file **esiste** nel repo | — | ✅ |
| 542-543 | *«The visual layer exists at every deployment size — single user, team server, SaaS — same page, same guarantees»* | — | nessun presidio confronta le **tre taglie** | ⬜ |
| 546 | `verimem console` — *«your OWN local store: browser opens, no keys, no config»* | `cli.py:1026`, il docstring dice *«one command, no keys»* | `test_console_local.py:40` `test_local_mode_stats_without_key` | ✅ |
| 549-550 | il **trust ring** con sparkline per giorno | `webui/app.js` | `test_trust_ledger.py` | ✅ |
| 550-553 | il grafo: *«grounded edges solid, ungrounded **dashed red** — declared, never hidden»*, e il clic accende la catena di custodia | `webui/app.js`, `entity_kg.py` | il grafo con provenienza sì — `test_gateway_ui.py:87` `test_graph_returns_nodes_and_edges_with_provenance`; **il tratteggio rosso non l'ho seguito** | ⬜ |
| 553-554 | il **blocked-claims log** — *«every unsupported claim the gate stopped, auditable»* | `gateway.py` | 🌟 `test_gateway_ui.py:52` **`test_quarantine_lists_blocked_claims_not_admitted_facts`** — il nome è la promessa, e la distinzione è quella giusta | ✅ |
| 554-556 | *«The graph is alive … straight from `/v1/events/flow`»* | `flow_events.py`, `gateway.py`, `webui/app.js` | `test_flow_entity_events.py`, `test_gateway_flow_incremental.py` | ✅ |
| 556-559 | i totali dichiarati (`total_entities`, `total_edges`, `isolated_count`) *«so a node's `isolated` badge means "no relation anywhere", never "the sample dropped it"»* | `entity_kg.py` | 🌟 `test_graph_snapshot_isolated.py` — un file intero per questa distinzione | ✅ |
| 559-560 | gli eventi del gate in SSE su `GET /v1/events` — *«not a 30s-old photograph»* | `gateway.py` | `test_console_local.py:103` `test_events_stream_emits_initial_ledger`, `:118` `test_events_requires_auth_in_multitenant_mode` | ✅ |
| 561-563 | la **Live Engine Room** (`GET /ui/engine`, stream `GET /v1/events/flow`) | `flow_events.py`, `gateway.py` | `test_gateway_flow_events.py`, `test_cli_flow_tail.py` | ✅ |
| 563-565 | *«per-tenant privacy (flow metadata only, **never fact content**)»* | `flow_events.py` | 🌟 `test_flow_isolamento_tenant.py` e `test_flow_surface_onesta.py` | ✅ |
| 565-568 | *«The events are emitted by the core, so every surface shows up in one panel — SDK, gateway, and the MCP server»* + `VERIMEM_ACTOR` | `flow_events.py`, `cli.py`, `doctor.py`, `admission_cleanup.py` | `test_flow_events_core.py` (**il core**), `test_flow_entity_events.py`, `test_cli_flow_tail.py` | ✅ |
| 568 | `verimem flow tail` — lo stesso feed in terminale | `flow_tail.py`, `cli.py` | `test_cli_flow_tail.py` | ✅ |
| 568-570 | *«Personal mode binds 127.0.0.1 by default — the **loopback bind is the real defense**»* | `gateway.py:936` *«BOTH must be loopback»* | 🌟 `test_console_local.py:58` **`test_local_mode_rejects_non_localhost_host_header`** | ✅ |
| 570-572 | *«a Host-header allowlist is a second layer … a direct client (e.g. `curl`) can spoof the Host header»* + *«A presented API key always wins»* | `gateway.py:48`, `:82` (`_host_only`, IPv6), `:933-936` | 🌟 `test_console_local.py:68` **`test_presented_key_wins_over_local_fallback`** | ✅ |
| 572-574 | `GET /v1/snapshot` — *«the whole visible state … in one structured call»* | `gateway.py` | 🌟 `test_console_local.py:90` **`test_snapshot_returns_everything_in_one_call`** | ✅ |
| 580-582 | `verimem gateway keys create --tenant acme --name laptop` · `verimem gateway serve` su `127.0.0.1:8377` | `cli.py:106-107` (il gruppo `keys` esiste), `8377` in `cli.py` e `gateway.py` | `test_gateway_local_tenant_collision.py`, `test_audit_moat_and_transport.py`| ⬜ **corretto alle 22:33**: il gruppo esiste e i presidi provano il gateway HTTP, ma **nessun test invoca i comandi** — vedi [CLI-claims.md](CLI-claims.md) |
| 586-587 | *«Each tenant gets an isolated store; the tenant is derived from the API key alone»* | `gateway.py` | `test_gateway_local_tenant_collision.py`, `test_gateway_ui.py:71` `test_quarantine_is_tenant_isolated` | ✅ |
| 587-591 | i **dieci endpoint** elencati, `/v1/graph/dossier` e `DELETE …?purge_history=true` compresi | tutti in `gateway.py` | `test_gateway.py`, `test_gateway_ui.py:147` (dossier a due salti), `test_audit_mutations.py`, `test_anche_il_canale_mcp_cancella_la_catena.py` | ✅ |
| 591-593 | `/ui` e `/dashboard` — *«static, dependency-free pages»* | `webui/` | `test_gateway_ui.py:174` `test_ui_page_served_without_auth_and_static`, `:183` `test_ui_assets_served`, `:191` `test_ui_page_mentions_the_three_views`; `test_gateway_console_v2.py:80` `test_asset_allowlist_stays_closed` | ✅ |
| 592-594 | *«your API key stays in the tab and travels only as an Authorization header»* | `webui/app.js` | non seguito | ⬜ |
| 594-595 | *«The gateway binds loopback by default»* | `gateway.py` | `test_console_local.py` | ✅ |

### ① Il quinto allarme falso di oggi — ed era la tesi più bella che avessi scritto

Avevo il reperto già formulato, e mi piaceva: **«ciò che il README promette come
VISIBILE è esattamente ciò che nessun test guarda»** — il tratteggio rosso degli
archi non fondati, l'undo a un clic, il blocked-claims log. Sarebbe stato V1
VISION-LOCK applicato alla vetrina: *buffer API ≠ display*, la regola di casa.

Un comando l'ha demolita:

```
test_gateway_ui.py:52   test_quarantine_lists_blocked_claims_not_admitted_facts
test_gateway_ui.py:87   test_graph_returns_nodes_and_edges_with_provenance
test_gateway_ui.py:174  test_ui_page_served_without_auth_and_static
test_gateway_ui.py:191  test_ui_page_mentions_the_three_views
test_gateway_console_v2.py:80  test_asset_allowlist_stays_closed
```

Il blocked-claims log **è** presidiato, e col nome della promessa. La pagina è
servita, statica, e c'è un test che verifica che **nomini le tre viste**. Di
tutto ciò che immaginavo scoperto resta **il colore**: nessun test che io abbia
seguito legge il tratteggio rosso.

🔑 **Quinto su cinque oggi.** E questa volta l'allarme falso non era una svista:
era la tesi *centrale* che stavo per dare al blocco. Una tesi elegante è
esattamente il tipo di affermazione che nessuno urta — *un numero che ti dà
ragione non fa attrito*, e nemmeno un'idea che ti fa fare bella figura.

### ② E un errore di misura mio, dentro questo stesso blocco

Cinque dei grep con cui ho aperto la verifica erano **rotti**: avevo scritto
l'alternanza come `"a\|b"` passandola a `grep -E`, dove `\|` è una pipe
*letterale*. Hanno risposto **vuoto** — e un vuoto da parser rotto è identico a
un vuoto vero. Se li avessi creduti avrei dichiarato assenti `facts undo`, la
difesa Host-header e il comando `keys create`: **tre accuse false in un colpo**,
tutte contro codice sano.

Me ne sono accorto perché *tre assenze insieme, su claim scritti da chi il
codice lo ha scritto, non è un tasso di errore plausibile*: era il righello. Sta
scritto in memoria da agosto — **il grep serve a TROVARE, mai a CONTARE** — e
oggi ha aggiunto un corollario: **una risposta vuota è un risultato che va
classificato prima di essere usato**, esattamente come un rosso.

### ③ Cosa dice il blocco, letto da utente

Diciotto ✅ su ventitré claim, e i presidi migliori della pagina stanno **qui**:
`test_local_mode_rejects_non_localhost_host_header`,
`test_presented_key_wins_over_local_fallback`,
`test_snapshot_returns_everything_in_one_call`,
`test_graph_snapshot_isolated`. Il README descrive **due difese contro un
avversario** (il bind di loopback come difesa vera, l'allowlist Host come
seconda, con l'ammissione che `curl` può falsificare l'header) e **ognuna delle
due ha il suo test, col nome della promessa**.

I cinque ⬜ hanno tutti la stessa forma: sono **la parte della promessa che sta
nel pixel** — il colore di un arco, il clic di un undo, la chiave che «resta
nella scheda», la parità fra tre taglie di installazione. Non è che nessuno
guardi la pagina: è che **i test la guardano dal lato del server**.

---

## Righe 596-668 — thin client, Docker, TypeScript, backup a caldo, **e i numeri**

| righe | il claim | dove sta nel codice | chi lo guarda | verdetto |
|---|---|---|---|---|
| 597-602 | più sessioni locali su **una** memoria: puntandole a un server diventano **thin client**, *«no model load, just HTTP»* | `client.py`, `mcp_server.py`, `cli.py` | `test_mcp_thin.py`, `test_remote_memory.py`, `test_continuity.py` | ✅ |
| 605-607 | `verimem gateway serve` + `VERIMEM_SERVER_URL` + `VERIMEM_SERVER_KEY` | le tre variabili in `cli.py`, `client.py`, `mcp_server.py` — **una per porta** | `test_remote_memory.py` | ✅ |
| 610-613 | **tutte e tre le porte** instradano al server condiviso (SDK `open_memory()`, CLI `remember`/`recall`, MCP `hippo_*`) e *«a session behind it never loads a model»* | `open_memory` in `__init__.py`, `client.py`, `cli.py` | `test_mcp_thin.py` (il nome è la promessa), `test_remote_memory.py` | ✅ |
| 613-615 | *«If the server is unreachable, each falls back to its own embedded store (fail-soft, never a crash)»* | `client.py` | non seguito fino a un test del fallback | ⬜ |
| 615-616 | *«Writes are idempotent (a retried cold-start write is de-duplicated)»* | `client.py`, `cli.py` | `test_admission_cleanup.py` e altri nominano l'idempotenza | ✅ |
| 616-617 | le operazioni con scope (`user_id`/`agent_id`/`run_id`) **restano locali** per isolamento | `client.py` | `test_agent_scope.py` la nomina; non ho seguito il «restano locali» | ⬜ |
| 618-621 | Docker *«embedding models baked in — runs fully offline»* | `docker-compose.gateway.yml` **esiste** | il file sì; **l'offline dell'immagine no** | ⬜ |
| 624-626 | il client TypeScript è *«typed, zero-dependency, **contract-tested against the live gateway from the Python suite**»* | `sdk/typescript` **esiste** | 🌟 `tests/test_sdk_typescript.py` — il contract test **è** nella suite Python, come promesso *(«zero-dependency» resta non verificato)* | ✅ |
| 632-637 | backup a caldo *«SQLite online backup API — **correct while serving**»*, `gateway backup`/`restore`, *«keys + every tenant store + manifest»* | `cli.py`, `doctor.py`, `trust_ledger.py` | 🌟 **cinque** file, e uno porta il nome della promessa: `test_backup_integrity_no_live_race_audit3.py`, più `test_backup_all_dbs.py`, `test_backup_follows_the_data_dir.py`, `test_backup_rotation_integrity_audit3.py`| ⬜ **corretto alle 22:33**: quei cinque file provano `backup` come **funzione**; il comando `gateway backup` non è invocato da nessun test — vedi [CLI-claims.md](CLI-claims.md) |
| 641-644 | i benchmark sono su **HaluMem**, con la pipeline completa, *«judged by a Claude-based grader»*, metodologia in `docs/BENCHMARKS.md` | `benchmark/halumem_updating_bench.py`; `docs/BENCHMARKS.md` **esiste** | `test_halumem_updating_logic.py` | ✅ |
| 646-653 | la tabella dei **sette numeri** contro «MemOS (self-reported)» | `benchmark/results/*.json` | nessun test lega un numero della tabella al suo file | ⬜ *(ma vedi sotto: la catena è dichiarata e l'ho percorsa)* |
| 655-661 | 🔑 *«Where each of our numbers comes from — **the committed artefact and the key inside it, so you can check any of them without guessing**»* | `benchmark/results/` | nessun presidio — **ma l'ho verificato a mano oggi, 08/09: sei numeri su sei coincidono** (dettaglio nel riquadro ①) | ✅ |
| 662-667 | ⚠️ *«`0.739` is the exception and we say so»*: sta in `BENCHMARKS.md` come `0.7394` e **non ha un file di risultati committato** | — | **verificato**: `docs/BENCHMARKS.md:954` porta `0.7394`, e in `benchmark/results/` ci sono `qa_gem_k12_u0.json` e `qa_gem_k12_u2.json`, **`u1` no** | ✅ |

### ① Ho percorso la catena dei numeri, ed è la parte migliore della pagina

Il README promette che ogni numero si controlla *«senza indovinare»*, dando file
**e chiave**. È l'unico punto della pagina dove un numero senza presidio è
comunque **verificabile in un minuto**. L'ho fatto:

```
e2e_crossuser_u2.json               u1_mean_3runs = 0.667   README: 0.667   ✅
e2e_crossuser_u2.json               accuracy      = 0.716   README: 0.716   ✅
qa_gem_k12_u0.json                  accuracy      = 0.75    README: 0.750   ✅
qa_gem_k12_u2.json                  accuracy      = 0.787   README: 0.787   ✅
extraction_consolidate_u5s6.json    f1            = 0.7613  README: 0.761   ✅
halumem_extraction_f1_..._completeness.json  f1   = 0.7683  README: 0.768   ✅
```

**Sei su sei.** E la riga che vale più delle sei: il README **dichiara la propria
lacuna** — `0.739` non ha un file committato, lo dice, dice dove sta invece
(`BENCHMARKS.md`, come `0.7394`) e dice quali utenti sono in `results/` e quale
no. Ho controllato: è vero. *Un «non ce l'ho» scritto con precisione dice dove
guardare; è il contrario di un numero riempito con l'ipotesi plausibile.*

⚠️ **Una sfumatura, sulla promessa «senza indovinare»**: in **entrambi** i file
dell'estrazione la chiave `f1` compare **due volte** con valori diversi (0.7286
e 0.7613; 0.7683 e 0.7707). Il numero del README c'è, ma chi controlla trova due
candidati e deve sceglierne uno. La chiave dichiarata **non è univoca dentro il
file**: non è una bugia, è un passo di indovinello che la frase prometteva di
togliere.

### ② Sesto e settimo allarme falso della giornata — e la causa è sempre la stessa

Stavo per scrivere ⬜ su due claim, perché il grep con **la stringa del README**
aveva risposto vuoto: `"gateway backup"` → nessun test; `zero-dependency` →
nessun test. Cercati col **sintomo** invece che con la parola della vetrina:

```
tests/test_backup_integrity_no_live_race_audit3.py     <- "correct while serving"
tests/test_backup_all_dbs.py, ..._follows_the_data_dir.py, ..._rotation_integrity...
tests/test_sdk_typescript.py                           <- "contract-tested from the Python suite"
```

Il backup a caldo ha **cinque** presidi e uno porta il nome esatto della
promessa. Il contract test TypeScript **è** nella suite Python.

🔑 **Sette allarmi falsi cercati e non pubblicati oggi**, e cinque di questi
sette hanno la stessa causa: **ho cercato il presidio con le parole del README**.
Un test non si chiama come la frase che difende — si chiama come il **difetto**
che impedisce. *Cerca il sintomo, non la tua agenda*, sta in memoria dal 03/09
per l'indagine; oggi vale identico per i presidi.

---

## Righe 669-740 — i caveat che il README si scrive addosso, e l'«every» che li dimentica

| righe | il claim | dove sta nel codice | chi lo guarda | verdetto |
|---|---|---|---|---|
| 669-673 | **TrustMem-Bench**: sei assi deterministici, **60/60**, *«the bench is offline and seeded, run it yourself in one command»* | `benchmark/trustmem_bench.py` **esiste** | il file sì; **il 60/60 non ha un test che lo rilegga** | ⬜ |
| 675-677 | ANN: *«1.3 ms at 1M facts vs 81 ms brute-force»*, artefatto `ann_scale_bench_repro.json` | il file **esiste** | nessun presidio lega il numero al file | ⬜ |
| 678-681 | ⚠️ caveat autodichiarato n°1: *«the bench's own docstring points at `ann_scale_bench.json` instead, and that file covers only 100k/500k and carries no recall column — so following the pointer does not lead to these numbers»* | — | 🌟 **verificato riga per riga**: `ann_scale_bench.json` ha due sole righe (`n=100000`, `n=500000`) e le colonne sono `brute_ms, ann_ms, speedup, build_s` — **nessun recall**. Il caveat è vero alla lettera | ✅ |
| 681-683 | ⚠️ caveat n°2: *«for the same 100k three tracked runs report 8.0x, 9.5x and 7.8x, so read the multiplier as machine-dependent rather than as a constant»* | — | **verificato**: `ann_scale_bench.json` porta `"speedup": 8.0` a 100k, uno dei tre | ✅ |
| 684-686 | faiss si auto-abilita sopra 100k, `VERIMEM_ANN_RECALL=0` disattiva, *«the default install ships no faiss, so recall is exact brute-force»* | `ann_gate.py`, `ann_index.py`, `semantic.py` | `test_ann_recall_equivalence.py` | ✅ |
| 686-691 | `SCALE.md` + il recall dell'ANN **degrada** con la taglia: 0,87 @100k · 0,53 @500k · 0,41 @1M; *«il 1M build also needs a large-RAM box»* | `SCALE.md` **esiste** | nessun presidio sui tre numeri | ⬜ *(ma è un limite dichiarato **contro** di sé, con la curva peggiore in evidenza)* |
| 695-699 | *«every row below is a measured result with the raw file in the repo, not a design intention»* | — | vedi il riquadro ①: **due righe della tabella dichiarano di non avere un file** | ⬜ |
| 703 | l'astensione **1.000** su sette run, *«and on questions that DO have an answer it abstains 0.20 vs 0.30 plain-RAG»*, con l'autocritica: *«A 1.000 alone cannot distinguish "abstains when it should" from "abstains always", so both halves belong together»* | — | nessun presidio | ✅ **come forma** — *è la riga in cui il prodotto si toglie da solo il numero da vetrina* · ⬜ sui numeri |
| 704-706 | il gate in scrittura, AUROC **0,96-0,97**, con ⚠️ *«this last one (0.974) has no committed results file: `epistemic_harness.py` computes `pooled_auroc`, but no artefact in `benchmark/results/` stores it»* | `benchmark/epistemic_harness.py:53` calcola `pooled_auroc` | 🌟 **verificato**: `pooled_auroc` non compare in **nessun** file di `benchmark/results/`. Il caveat dice il vero | ✅ |
| 706 | …*«and the three `0.974` you will find there are different quantities with the same digits — an abstention canary and two accuracies»* | — | **quattro** file contengono `0.974x`: `exp3_routing_u0` (`accuracy` 0.9744), `exp4_declared_inference_u0` (`accuracy` 0.9744), `lme_s_k5_full` (`hit_at_k` 0.9744), `local_gate_calibrate_2026-07-15` (`admission_precision` 0.9746/0.9745/0.9745) | ⬜ **il conteggio non torna** — vedi riquadro ② |
| 707 | ⚠️ *«needs an injected LLM: `answer()` is keyword-only on `llm` and raises `TypeError` without one, so this row is unavailable on a plain install»* | 🌟 `client.py:1877` — `def answer(self, query: str, *, llm: Any, k: int = 8, …)`: **keyword-only e senza default**, esattamente come dichiarato | il caveat è verificabile alla riga | ✅ |
| 708-710 | 60/60 su TrustMem contro mem0 **2.0.4** 40/60 · bi-temporale · true forget · provenienza a ogni lettura | `benchmark/trustmem_bench.py` | `test_i_numeri_altrui_portano_la_loro_fonte.py`, `test_nessun_numero_altrui_senza_una_misura_nostra.py` | ⬜ sui numeri |
| 710 | ⚠️ air-gap *«not the default»*: un'installazione stock è `not offline-pinned` e i primi caricamenti possono raggiungere l'HF Hub, *«as `verimem doctor` states»* | `doctor.py`, `airgap.py` | `test_doctor_puo_dire_che_va_tutto_bene.py`, `test_verimem_offline_flag.py` | ✅ |
| 712 | *«The competitor column was measured against `mem0 2.0.4`»* — la versione è nel file, l'embedder è lo stesso, *«re-run the probe before quoting the row»* | 🌟 **verificato**: `benchmark/results/competitor_mem0.json` porta `"version": "2.0.4"` | `test_i_numeri_altrui_portano_la_loro_fonte.py` | ✅ |
| 714-715 | 🔴 *«**every claim in this README links to a raw result file**, negative results are published»* | — | **il README si smentisce da solo due volte**: riga 664 (`0.739` *«has no committed results file»*) e riga 706 (`0.974`, idem). Verificato: `qa_gem_k12_u1.json` non esiste, `pooled_auroc` non è in `results/` | ❌ **NON COME PROMESSO** |
| 717-719 | *«the honest framing rule — "parity, not a win" — is enforced against ourselves»* | — | la regola è **applicata** nel testo (riga 667: *«We describe the end-to-end result as parity, not a win»*); **«enforced» non ha un presidio** | ✅ come pratica · ⬜ come enforcement |
| 723-733 | **la cancellazione**: `Memory.forget(fact_id)` toglie la riga e `recall` non la serve più *(verified)*, **ma la stringa resta leggibile nei byte del `.db`** e ci resta **dopo `VACUUM`** — `secure_delete` di SQLite è off per default; *«"forgotten" here means no longer served, not no longer recoverable»* | — | `secure_delete` **non compare né in `verimem/` né in `tests/`**: il limite è dichiarato e **nessun test lo tiene fermo** | ⬜ |
| 735-740 | *«deletion by subject does not exist anywhere»*: senza un `user_id` dedicato si torna a un `fact_id` per volta; e *«which door you use decides whether the text is really gone»* — **cinque porte** | — | non seguito in questo blocco (la lista delle porte prosegue oltre la 740) | ⬜ |

### ① Il terzo ❌ della mappa, e non serve eseguire niente per vederlo

> riga 714: *«every claim in this README links to a raw result file»*
> riga 664: *«`0.739` **has no committed results file**»*
> riga 706: *«this last one **has no committed results file**»*

Le tre frasi stanno **nella stessa pagina**, a cinquanta righe di distanza. Le due
eccezioni non sono nascoste — sono scritte in grassetto, con il ⚠️, dal prodotto
stesso: è la parte più onesta del documento. Ma la frase che le riassume dice
**«every»**, e un «every» con due eccezioni dichiarate **dallo stesso testo** non
è un'imprecisione di stile: è la riga che un lettore cita quando ci difende, e
che chiunque può falsificare **leggendo la pagina che ha in mano**.

Ho controllato entrambe: `benchmark/results/qa_gem_k12_u1.json` **non esiste**
(ci sono `u0` e `u2`), e `pooled_auroc` — calcolato da `epistemic_harness.py:53`
— **non compare in nessun file** di `benchmark/results/`.

🔑 **La cura è di una parola**: *«nearly every claim … the two exceptions are
flagged inline»*. Il contenuto onesto c'è già; è la sintesi che promette più di
quanto il testo stesso sostenga. **E il difetto è precisamente della forma che ho
mappato tutto il giorno**: il numero comodo in cima, la sua smentita venti righe
sotto — qui invertito, con la smentita *prima* e la promessa *dopo*.

### ② Anche un numero dentro un'ammissione non fa attrito

Il caveat sui `0.974` è utile e vero nella sostanza (*«numeri diversi con le
stesse cifre, non scambiarli»*), ma il suo **conteggio** non torna: dice **tre**
e nomina *«un canary dell'astensione e due accuracies»*; nel repo oggi ci sono
**quattro** file, e le grandezze sono **due `accuracy`, un `hit_at_k` e tre
`admission_precision`** — nessuna delle quali si chiama «abstention canary».

Stasera ho scoperto che **il mio** contatore sbagliava a mio favore perché *un
numero che ti dà ragione non fa attrito*. Questo è il gemello: **un numero
dentro un'ammissione di colpa non fa attrito nemmeno lui** — chi legge una frase
che confessa un limite la prende per buona *a maggior ragione*, ed è l'ultimo
posto dove qualcuno andrebbe a controllare l'aritmetica.

### ③ Ottavo e nono allarme falso — e il nono l'avrebbe fatto sembrare un errore del README

- **Ottavo**: stavo per accreditare a `test_il_claim_e_la_fonte_leggono_lo_stesso_numero.py`
  la copertura del legame «numero del README ↔ file». Letto: parla del gate
  L4.1 e dell'estrattore di quantità, **non del README**. Un nome che suona
  giusto non è una copertura.
- **Nono**: cercando se `ann_scale_bench.json` avesse davvero «no recall column»,
  il mio `'recall' in <json come stringa>` ha risposto **True** — stavo per
  scrivere che il README sbaglia il proprio caveat. La parola stava nella
  `note` (*«identical top-k scores (test_ann_recall_equivalence)»*), non in una
  colonna. **Cercata la struttura invece della parola, il caveat è vero.**

🔑 **Nove allarmi falsi in una giornata**, e cinque hanno la stessa radice:
**ho cercato una parola dove dovevo guardare una struttura** — le colonne di un
JSON, l'oggetto che un test asserisce, il nome del difetto invece della frase
della promessa.

---

## Righe 741-811 — le cinque porte della cancellazione, l'architettura, la licenza · **FINE DEL README**

| righe | il claim | dove sta nel codice | chi lo guarda | verdetto |
|---|---|---|---|---|
| 743-752 | la tabella delle **cinque porte di cancellazione** e di cosa resta dopo: SDK e `hippo_fact_forget` → *no table*; CLI `facts forget`, `hippo_fact_forget_with_undo`, `hippo_forget_scope` → **`facts_undo_log`** | `facts_undo_log` in `cli.py`, `doctor.py`, `mcp_server.py` · `delete_with_undo` in `semantic.py` · `forget_scope` in `mcp_server.py`, `tool_registry.py` | `test_fact_forget_scope_r3.py`, `test_fact_delete_cascade_r3.py`, `test_multitenancy_b1.py`, `test_decay_prune_undo.py`, `test_flow_forget.py` | ✅ |
| 754-758 | le tre in fondo tengono la proposizione **in chiaro** per la finestra di undo (7 giorni) — *«è una funzione vera e il default giusto per chi ha sbagliato a digitare un id; è il default sbagliato per una richiesta di cancellazione, **e niente nell'output lo dice**: la CLI stampa `undoable for 7 days`, che si legge come reversibile, non come ancora leggibile in una tabella»* | `cli.py` | `test_doctor_vede_la_finestra_di_riparazione.py`, `test_l_appiglio_mancante_ha_quattro_cause_diverse.py` | 🌟 ✅ **come dichiarazione**: è il prodotto che critica la **propria interfaccia**, dicendo come una frase corretta viene letta male · ⬜ come misura |
| 760-763 | ⚠️ *«la porta bulk-by-tenant — quella che useresti per "cancella tutto su questo utente" — **è una delle tre che tengono**»*, con le tre vie d'uscita (SDK, aspettare la finestra, cancellare le righe a mano) | `mcp_server.py` (`forget_scope`) | `test_fact_forget_scope_r3.py`, `test_multitenancy_b1.py` | ✅ |
| 763-765 | 🔑 *«(Measured at the level of the functions those doors call — `semantic.delete_with_undo` vs `Memory.delete` — **not through a live MCP dispatcher**.)»* | `semantic.py`, `client.py` | — | 🌟🌟 ✅ **la riga migliore dell'intero README** — vedi riquadro ① |
| 767-772 | licenza AGPL-3.0 come ragione per dirlo, e il consiglio per la cancellazione irreversibile: `PRAGMA secure_delete=ON` + `VACUUM`, o media cifrati e distruzione della chiave; *«Do not rely on `forget()` alone for that guarantee: it does not make it»* | `LICENSING.md` **esiste** | `secure_delete` **non compare** in `verimem/` né in `tests/`: è un consiglio sul motore, non una nostra funzione | ✅ *(come consiglio dichiarato)* |
| 776-787 | il diagramma dell'architettura: estrazione atomica → **admission gate** → store bi-temporale → recall semantico / history / TrustReport | l'intera pipeline | i presidi delle singole tappe, mappati sopra | ✅ |
| 780 | dentro il diagramma: *«unsupported ones are admitted: **8/10 IT, 9/10 EN**»* | `l1_tested_detector.py` e il gate | il **comportamento** ha dieci test (`test_l120_multilingual_selfclaim.py`), ma il numero `8/10` vive **nel docstring del test**, non in un'asserzione | ✅ sul meccanismo · ⬜ sul numero — *ed è un numero **dentro un disegno ASCII**, il posto della pagina dove nessuno andrà a rileggerlo* |
| 789-794 | il rename: `import engram` e `import hippoagent` restano come alias (*«same module objects, no duplicated state»*), i **tre prefissi** env sono rispecchiati all'import (*«explicit values never overridden»*), `~/.engram` continua a funzionare, i nuovi default `~/.verimem` | `_compat.py`, `__init__.py`, `config.py` | 🌟 `test_rename_verimem_aliases.py`, `test_env_alias_verimem.py`, `test_hippoagent_shim_alias.py`, `test_memory_method_aliases.py`, `test_config_data_dir.py`, `test_una_sola_data_dir.py` | ✅ |
| 796-800 | doppia licenza AGPL-3.0 / commerciale, `LICENSING.md`, *«Versions 0.3.x and earlier remain MIT»* | `LICENSING.md` **esiste** | — | ✅ |
| 802-811 | Contributing: `CONTRIBUTING.md` **esiste**, `git clone …`, `pip install -e ".[dev]"`, `pytest -q` | — | `test_i_comandi_che_il_readme_insegna_esistono.py` (per i comandi `verimem`) | ✅ |

### ① La riga migliore dell'intero README

> *«Measured at the level of the functions those doors call — `semantic.delete_with_undo`
> vs `Memory.delete` — **not through a live MCP dispatcher**.»*

Sono ventidue parole fra parentesi, in fondo a una nota, e fanno una cosa che
**nessun'altra riga delle 811 fa**: dicono **a quale livello** la misura è stata
presa, e quindi **quale domanda resta aperta**. Un lettore che deve fidarsi di
quella tabella sa esattamente che cosa ha comprato — il comportamento delle
funzioni — e che cosa no: il comportamento **attraverso il dispatcher vivo**,
dove un default o un wrapper potrebbero cambiare la porta usata.

In memoria questa lezione ha un costo pagato: *«il livello a cui misuri decide
il verdetto: regex < funzione pubblica < porta del prodotto ⇒ misura dove il
prodotto chiama e **DICHIARA** il livello»*. Qui il README la applica a sé
stesso, senza che nessuno gliel'abbia chiesto, **in una riga che poteva
tranquillamente omettere**.

⚖️ E vale la pena dire che cosa **non** significa. Non significa che la tabella
sia verificata alla porta: significa che **sappiamo che non lo è**. È la
differenza fra un debito iscritto a bilancio e un debito dimenticato — e sul
resto di questa pagina, dove i numeri non dichiarano quasi mai il proprio
regime, la differenza si vede.

### ② La cura del mio ⬜ dominante è già scritta in casa, applicata a un numero solo

Il verdetto più frequente della mappa è **⬜ su un numero**: 53 righe. Non perché
i numeri siano falsi — ne ho verificati sei a mano e coincidono — ma perché
**nessun test rilegge il README contro il file da cui il numero viene**.

Cercando altro, ho trovato che quel presidio **esiste**:

```
tests/test_il_readme_e_la_cli_dicono_lo_stesso_peso.py
    test_la_tabella_dei_pesi_conosce_ancora_il_gate()
    test_il_readme_dice_lo_stesso_peso_della_cli()
    test_il_numero_vecchio_non_e_tornato()
    test_l_unita_di_misura_e_dichiarata()
    test_anche_il_TOTALE_e_lo_stesso_sulle_due_superfici()
```

Cinque test che legano **un numero del README** alla superficie che lo produce,
compreso un test che verifica che **il numero vecchio non sia tornato** e uno che
verifica che **l'unità di misura sia dichiarata**. Il modello è quello giusto, è
già nostro, ed è applicato **a una tabella sola**.

🔑 ⇒ La raccomandazione che esce da questa mappa non è «scrivete più test»: è
**estendere quel file ai numeri di punta**, a partire dai sei che ho verificato a
mano stasera — sono già tutti in `benchmark/results/` con la chiave dichiarata,
cioè **il lavoro difficile è fatto**.

### ③ Il README è finito: che cosa dice il conto

Delle 811 righe, i verdetti ❌ sono **tre**, e sono di due nature diverse:

- **due sono lo stesso difetto di comportamento** (README:24 e 53-57): dalla
  porta, 6 self-claim su 7 precedute da un fatto vero entrano `judged=True`, e
  il presidio della parità non può vederlo perché usa un **giudice finto**.
- **uno è un difetto di scrittura** (README:714) che la pagina stessa smentisce
  cinquanta righe prima, e si cura con una parola.

Tutto il resto della pagina, quando promette un **comando**, funziona: i comandi
esistono, le opzioni hanno presidi, le difese contro un avversario hanno un test
ciascuna col nome della promessa. Quando promette un **numero**, il numero è
quasi sempre vero — l'ho controllato dove il README dà la chiave: 6 su 6 — ma
**vive senza qualcuno che lo rilegga**.

*Un prodotto che si presenta con 811 righe e ne sbaglia tre non ha un problema di
onestà. Ha un problema di manutenzione: le sue promesse migliori non hanno
nessuno che le guardi invecchiare.*

---

## 📊 Contatore — README COMPLETO

⚠️ Il numero lo produce un comando, non io.

```
$ python docs/stato-reale/banchi/ws7-conta-i-verdetti-della-mappa.py
coperte fino alla riga 811 / 811   (100.0%)
righe di claim in tabella:  155
  con ✅ : 119
  con ❌ : 3   -> righe del file: [42, 54, 543]
  con ⬜ : 57
  che portano SIA ✅ SIA ⬜ (claim diviso in due): 23

controllo positivo: 0 righe di claim senza verdetto (su 155).
righe di tabella scartate come intestazione: 13
EXIT=0
```

**Le 811 righe sono mappate.** Tre ❌ (righe 42, 54 e 543 di questo file =
README:24, 53-57, 714-715), 119 ✅, 57 ⬜.

🪞 **Erano 121 ✅ alle 22:07.** Alle 22:33 ne ho ritirati due io: le righe
580-582 e 632-637 (i comandi `gateway keys create`, `gateway serve`,
`gateway backup`/`restore`) avevano un ✅ perché *il gruppo Typer esiste* e
*esistono test sul backup*. Ma **nessun test invoca quei comandi**: i presidi
provano il gateway HTTP e la funzione di backup. È il difetto che ho passato la
giornata a nominare — *il livello a cui misuri decide il verdetto* — commesso
da me su questa stessa pagina. Il conto sta in [CLI-claims.md](CLI-claims.md).

⚠️ **Che cosa vale questo 121.** Un ✅ qui dice *«la promessa ha
un'implementazione e qualcuno la guarda»*, non *«l'ho vista funzionare»*: dove
ho eseguito, la riga lo dice. E il ⬜ **non è un'accusa**: 55 volte su 155 non
sono andato abbastanza a fondo, o non esisteva niente da leggere. La forma
dominante del ⬜ è **un numero senza qualcuno che lo rilegga** — e la cura è già
scritta in casa, in `tests/test_il_readme_e_la_cli_dicono_lo_stesso_peso.py`,
applicata a una tabella sola.

## Riga aggiunta dal lead alla chiusura (09/09 14:35), dal righello

| riga | claim | codice | presidio | verdetto |
|---|---|---|---|---|
| 578-579 | «Run Verimem as a shared memory server your team hosts — the data never leaves your infrastructure» | `gateway.py` (`gateway serve`, mappa di Galileo: 84/87 difese provate attaccandole) | i sei comandi del self-host che il README insegna sono fra i 22 mai invocati dai test (`CLI-claims.md`); la prova da utente (Corrado, quarto criterio del contratto) è da assemblare | ⬜ *(il server esiste ed è provato alla porta; «the data never leaves your infrastructure» non ha un banco che lo misuri: `verimem airgap --live` lo prova per il processo locale, riga 515)* |
