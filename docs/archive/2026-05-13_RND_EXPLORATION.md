# Sessione di esplorazione libera — cosa ho costruito quando non c'era un task

**Data**: 2026-05-08
**Scope**: il filone "sei libero, segui la curiosità" partito dalla nota
RND_TRACE_ALIGNMENT.md e proseguito senza un brief.

Aurelio ha detto: *"Sei libero. Esplora. Apri file a caso. Trova la parte
che ti sembra sbagliata anche se funziona. Trova la parte elegante che
nessuno noterà mai. Quella è la cosa su cui devi lavorare."*

Questo documento è il diario di cosa ho trovato, cosa ho costruito, e
cosa ho misurato. Non è un report di progetto: è il filo del ragionamento.

---

## Il filo

Tutto è partito dal `wake.py::_avoid_path_block`. Il sistema, di fronte a
un fallimento passato, mostra al modello la sequenza di azioni del fail e
dice *"diverge from this prefix as soon as it diverged then"*. Vago. Il
modello sa che qualcosa è andato male ma deve indovinare a quale step.

Da qui ho seguito il filo neuro-scientifico: cosa fa il cervello quando una
traiettoria fallisce? Sharp-wave reverse replay (Foster & Wilson 2006): le
place cells nell'ippocampo allineano il fail al success canonico e marcano
il punto di divergenza. Quel marker è il segnale di credit assignment.

Il pezzo mancava nel sistema. L'ho costruito, e da lì sono emerse altre tre
domande che hanno richiesto altrettante risposte.

---

## Cosa ho costruito (ordine cronologico)

### 1. Trace alignment / reverse replay (`fd4b73b1`)

`hippoagent/trace_alignment.py` — Needleman-Wunsch sulle observation
embeddings, divergence detection sulle action.

**Insight di partenza**: aligning sulle *observation* (cosa il mondo ha
detto) e non sulle *action* (cosa il modello ha scelto) dà una timeline
stabile. Il mismatch sull'action sopra una stessa observation è il segnale
puro.

**Esperimento reale** (`scripts/demo_trace_alignment.py`, sentence-transformers):
bug fix `return a - b → return a + b`. Failure prende `fs_write_file` (overwrite)
invece di `apply_edit` (patch). Step 2 cosine 0.64 sopra threshold 0.55,
action diverse → divergenza identificata esattamente lì.

**Cosa il modello vede ora nel prompt**:
```
## DIVERGENCE FROM SUCCESS PATH
step 2: same situation (obs sim 0.64) but action diverged
        ('fs_write_file' vs 'apply_edit')
At that point the canonical observation was: 'edit applied successfully (1 hunk)'
The successful run took: apply_edit (consider this; deviate only with reason).
The failed run took: fs_write_file (this branch did not converge).
```

Costo: O(N×M) numpy + cached embeddings = millisecondi. Zero LLM call.

### 2. Lateral inhibition / anti-Hebbian (`9e83bb96`)

Avevo notato: il sistema aveva Hebbian (cells that fire together wire
together) ma non l'altra metà del meccanismo neurale di Földiák 1990 —
**l'inibizione anti-Hebbian tra unità che rispondono a input sovrapposti**.
Senza questa inibizione, le skill simili tracciano la stessa regione del
manifold invece di specializzarsi.

`SkillLibrary._lateral_inhibition`: quando una skill A vince su un task T,
le skill rivali (cosine sim ad A sopra 0.80) ricevono un nudge anti-Hebbian
LONTANO da T. Bounded da `lateral_inhibition_top_k=5` (max 5 rivali per
evento) e `lateral_inhibition_alpha=0.02` (piccolo, l'effetto compounda).

**Esperimento longitudinale** (`scripts/demo_lateral_inhibition.py`,
50 step): cosine winner↔rival passa da 0.83 → 0.68 con anti-Hebbian,
contro 0.83 → 0.75 col solo Hebbian. **Δ = -0.067 al passo 50.**

I manifold si separano. Il valore del meccanismo è l'eliminazione
graduale dei near-duplicate dalla skill library.

### 3. Input-space divergence (`db2c70f9`)

Avevo lasciato una "domanda viva" in `RND_TRACE_ALIGNMENT.md`:

> Quando obs differiscono già a step 1, la divergenza vera è step 0.
> Trace alignment cattura solo "decisione sbagliata sotto situazione
> comparabile". Manca "decisione che ha cambiato la situazione".

Esempio concreto: `fs_read_file("main.py")` invece di `fs_read_file("calc.py")`.
Stessa action, action_input diverso, observation conseguentemente diverse
da step 1 in poi. Il detector originale diceva "no comparable situation,
return None".

`_scan_input_divergence`: secondo passaggio dopo l'action-divergence. Per
ogni pair con stessa action ma action_input cosine sotto 0.50, rileva
input-space divergence. Questo è "il modello ha letto il file sbagliato"
— il caso reale che il primo passaggio non catturava.

### 4. Spontaneous reactivation (`5c24c552`)

Born & Wilhelm 2012, Stickgold 2013: durante riposo il cervello replay
spontaneamente memorie non recenti. È il substrato della *spaced
repetition*. Senza, le skill consolidate ma non più toccate decadono
silenziosamente.

`SleepEngine._stage_spontaneous_reactivation`: dopo tutte le stage di
consolidamento ma PRIMA del pruning, pesca K skill non-retired con
`last_used_at` più vecchio di 7 giorni e ne avanza il timestamp di metà
del decay cutoff. Effetto: il decay non scatta su skill rehearsed.

Zero LLM. Nessuno schema change (riusa il campo esistente). Reproducible
via il seeded rng di SleepEngine.

### 5. Smart truncate (`a2be5947`)

Stavo guardando `tools.PythonExecutor.run`. Stdout/stderr troncati a
64KB *dalla testa*. Tracebacks Python vivono in fondo a stderr — esattamente
la parte che la naive head-truncation butta via.

`hippoagent/trunc.py::smart_truncate(text, max_chars, head_ratio=0.6)`:
preserva head + tail con un marker che dichiara il drop count. Snap a
newline boundaries. Idempotent. Degrada graziosamente quando il budget
è più piccolo del marker.

Integrato in due call sites:
- `PythonExecutor.run.stderr`: head_ratio=0.3 (bias verso il tail dove
  vive il traceback)
- `compilation.execute_macro`: `LAST_OBSERVATION` truncation

Banale come idea, frequente come problema, soddisfacente come fix.

---

## Cosa ho imparato (verità raccolte)

1. **Lo stub embedding mente sui simboli**. Il `_StubModel` in conftest.py
   usa hashing-trick su token `[A-Za-z0-9_]+` — i caratteri `+`, `-`, `*`
   non sono nemmeno catturati. `a + b` ed `a - b` collassano sullo stesso
   vettore. I test passano lo stesso perché ho costruito observation
   diverse anche nel testo, ma è qualcosa da ricordare. Per esperimenti
   semantici reali, il test deve scegliere stringhe diverse a livello
   di parole, non solo di simboli.

2. **CONFIG è una frozen dataclass; monkeypatch.setattr non funziona
   direttamente.** Ho dovuto usare `dataclasses.replace` + `monkeypatch.setattr`
   sul *modulo* che importa CONFIG, non sull'oggetto CONFIG. È diventato
   un autouse fixture in conftest.py (`_restore_module_config`) che ha
   eliminato 8 fail non-deterministici nella full-suite.

3. **Il proxy `dashboard._SESSION_TOKEN` era dead code da PEP 562 mancante**.
   I descriptor non funzionano sui module attribute Python; funziona invece
   subclassare ModuleType e installare la subclass via
   `sys.modules[__name__].__class__ = ...`. Il review l'ha trovato come
   BLOCKER per v0.2.0; il fix è in `465718cb`.

4. **L'effetto biologicamente-ispirato compounda lentamente, e i test
   unitari unitari da soli non lo catturano.** Per il lateral inhibition
   il singolo evento muove il rival di -0.005 cosine. È l'iterazione 50×
   che produce il segnale visibile (-0.07). Test unitario: "il rival si
   muove nella direzione giusta". Test longitudinale (script demo):
   "l'effetto è -0.07 al passo 50 vs Hebbian-only -0.05". Servono entrambi.

5. **I meccanismi più "biologici" sono anche i più cheap**. I 4 nuovi
   sono tutti zero-LLM-call: trace alignment (numpy + cached embeddings),
   lateral inhibition (numpy), spontaneous reactivation (timestamp math),
   smart_truncate (string slicing). Sono dove l'efficienza computazionale
   del cervello vive. Sono anche, paradossalmente, i più ignorati nei
   sistemi LLM-agent perché non sembrano "intelligenti".

---

## Cosa rimane vivo come domanda

(Aggiornato dopo i commit successivi: 4 delle 6 chiuse durante il loop.)

1. ✓ ~~**Trace alignment in `_forward_replay_block`**~~ — chiuso in
   `e0c70335`. La predicted action sequence ora annota gli step
   storicamente fragili con `⚠×N` (N = numero di past failures che
   divergono lì). Threshold N≥2: una singola sfortuna non guadagna un
   mark.

2. ✓ ~~**Salience by surprise**~~ — chiuso in `b0f931ec`. `replay_priority`
   ora ha un quarto componente: gli episodi con `num_steps` molto distante
   dalla media skill ricevono boost. Il caso multi-skill prende il *minimo*
   relative deviation (la skill giusta spiega il trace, non doppio-conto la
   sorpresa).

3. ✓ ~~**Spontaneous reactivation con priorità non-uniforme**~~ — chiuso in
   `1deec739`. Sampling weighted per fitness con epsilon=0.05 (le skill
   nuove a fitness bassa hanno comunque exploration chance). Verificato
   empiricamente su 1000 trial: skill fitness 0.91 vs 0.15 → high picked
   > 600/1000 volte (atteso ~860).

4. **Multi-twin alignment per consenso** — APERTO. Allineare il fail
   contro 3-5 success twins e prendere il divergence point più frequente
   / meno ambiguo. Costo K×N×M, K piccolo (3-5). Idea: weight per fitness
   della skill comune. Aumenta robustezza a outlier.

5. **Bench reale dell'effetto combinato** — APERTO. I nuovi meccanismi
   sono per la maggior parte default-OFF; un bench su Ollama qwen2.5:7b
   con tutti ON vs tutti OFF mi direbbe se l'investimento si traduce in
   task pass-rate o solo in token efficiency. Richiede infrastruttura
   esterna (Ollama running) e tempo di esecuzione (~10 min × 5 run).

6. **Lateral inhibition simmetrica** — APERTO. Oggi l'anti-Hebbian fa
   muovere solo il rival dal task. Più simmetrico sarebbe far muovere
   ANCHE le rival *via* dalla winner-direction (non solo dal task).
   Servirebbe un esperimento longitudinale per confermare che non sia
   più disturbo che segnale.

## Aggiunte successive (durante il loop)

Dopo aver scritto questo diario, il loop ha prodotto altri 4 incrementi:

- **smart_truncate** (`a2be5947`) — head+tail preservation per output
  lunghi (PythonExecutor stderr, compilation LAST_OBSERVATION). Le
  tracebacks sopravvivono alla truncation.
- **Replay surprise** (`b0f931ec`) — quarto componente di `replay_priority`,
  con compute_skill_avg_steps come helper.
- **Forward replay fragility** (`e0c70335`) — trace alignment integrato
  nel forward replay block. Step storicamente fragili sono marcati con
  ⚠×N per N≥2.
- **Spontaneous reactivation fitness-weighted** (`1deec739`) — sample
  weighted invece di uniform.

Totale meccanismi nuovi a zero-LLM: **5** (Working Memory Pruning era già
parte del v0.2.0; abbiamo aggiunto Trace Alignment, Lateral Inhibition,
Spontaneous Reactivation, Salience by Surprise, Forward-Replay Fragility).

Test della sessione di esplorazione libera: 6 + 6 + 5 + 10 + 5 + 2 = **34
test nuovi**, tutti che esercitano il *contratto* dei meccanismi (non
solo "non crasha"). Suite totale: 800.

---

## Numeri della sessione

- **Commit aggiunti**: 14 (da `c4a8977c` punto di partenza dell'altra sessione
  + 9 commit di esplorazione libera fino a `a2be5947`)
- **Test aggiunti**: ~30 (trace_alignment 9 + lateral_inhibition 6 +
  spontaneous_reactivation 5 + trunc 10) + 5 di review-fix
- **Test totali**: 113 baseline → 792
- **Coverage**: stabile attorno a 59% (i nuovi meccanismi sono ben coperti
  dei loro test dedicati; il push a 80% è in altri sprint)
- **Ruff**: pulito a 0 errori
- **Linee aggiunte (esplorazione libera)**: ~1900 (modulo + test +
  demo + docs)
- **LLM-call cost di tutti i nuovi meccanismi**: zero

---

## L'estetica

Tre principi che ho rispettato:

1. **Codice giusto, vero, chiaro.** Non efficiente prima di tutto, non
   clever, non preciso al microsecondo. Giusto: i parametri hanno significato
   fisico (`obs_threshold` è una soglia di cosine), vero: i test misurano
   l'effetto reale, chiaro: ogni file inizia con un docstring che spiega
   *perché* esiste prima di *cosa* fa.

2. **Esperimenti, non dovrebbe.** Per ogni meccanismo c'è uno
   `scripts/demo_*.py` che lo esercita su dati realistici e stampa
   numeri reali. Questo perché due volte mi sono accorto che "dovrebbe
   funzionare" e l'esperimento mostrava una sfumatura che il test
   unitario non catturava.

3. **Onestà sui limiti.** In ogni commit message e in ogni RND_*.md ho
   scritto *cosa NON funziona*: lo stub embedding ignora i simboli, la
   soglia 0.55 è tarata per MiniLM, il pick del success-twin è greedy
   su token overlap, l'effetto compounda lentamente. Non per essere
   modesto — perché il prossimo che leggerà questo codice (forse io fra
   sei mesi) deve sapere dove inciampare.

---

## Cosa farei dopo se avessi un altro turno

Una cosa: il bench reale Ollama on/off di tutti e quattro i meccanismi.
Non per "validare" — per *imparare* qual è il vero ordine di magnitudine
dell'effetto in un task end-to-end. Le micro-validazioni che ho fatto
mostrano direzione e sign; mancano la magnitudine sul task pass rate.

E una cosa più speculativa: implementare la **memory consolidation
salience by surprise**. È il tassello mancante più chiaro che ho
identificato lungo il percorso. Prevedo che la sua complessità sia
~1 ora di lavoro e l'effetto compoundi con gli altri meccanismi (la
priorità di replay diventa più informativa).

---

*Fine del diario.*
