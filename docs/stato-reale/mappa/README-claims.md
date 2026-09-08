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

## 📊 Contatore

```
righe lavorate:  400 / 811   (49,3%)
verdetti:  ✅ 58   ❌ 2   ⬜ 37   (una riga può portare due verdetti su due claim)
```

**I due ❌ sono la riga 24 e la 53-57**, e sono **lo stesso difetto**: la frase con
cui il prodotto si presenta, e la sua ripetizione dodici righe sotto.

**Il ⬜ dominante non è pigrizia mia**: è che **i numeri di punta della pagina non
hanno un presidio**. Hanno i banchi — dichiarati, con il nome del file — ma
nessun test rilegge il README contro di essi.
