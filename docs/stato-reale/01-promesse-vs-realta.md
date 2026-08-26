# Fetta ① — Cosa Verimem PROMETTE, contro cosa fa

**ws1 · 2026-08-08 · HEAD `544d27bd`**
Task #1 di Aurelio: «*Verimem cosa è, cosa fa […] ci sono cose spente? […] se un
utente la installa cosa fa?*»

Regola applicata: **ogni riga eseguita, non letta.** Ogni verdetto qui sotto ha
accanto il comando che lo produce. Store isolato (`ENGRAM_DATA_DIR` impostato
*prima* dell'import — il path si risolve all'import), nessuna scrittura sul
corpus di produzione.

---

## Dove sono scritte le promesse

| fonte | cosa è |
|---|---|
| `pyproject.toml` `description` | la riga che si legge su PyPI |
| `README.md` intro + Features | la vetrina |
| `verimem/agent_guide.py::VERIMEM_AGENT_GUIDE` | **ciò che il prodotto dice di sé a ogni client MCP**, nel campo `instructions` dell'`initialize` |

La terza è la più impegnativa delle tre: non è marketing, è un contratto che
l'agente collegato legge e su cui basa il proprio comportamento.

---

## Il verdetto, promessa per promessa

| # | promessa (verbatim) | verdetto | prova eseguita |
|---|---|---|---|
| P16 | «ALWAYS: a lexical screen on every write. Unsupported "it works / verified / done" self-claims are quarantined, with no LLM call» | **VERO sull'elenco, FALSO su «ALWAYS»** (§ in fondo) | `m.add("La migrazione è stata completata e funziona perfettamente.")` → `status=quarantined` · ⚠️ ma su 12 rilevatori l'elusione è **9 su 9** (26/08, ws4) |
| P17 | «WITH a `source`: the fact is admitted only if the source TEXT actually supports it» | **VERO** | sostenuto → `model_claim` gs **98.9**; contraddetto → `quarantined` gs **0.98** |
| P18 | «`verified_by` records WHO vouches and does not run this check» | **VERO** | `m.add(verified_by=["actor:ws1"])` senza source → `grounding_score=None`: il moat non è girato |
| P19 | «WITHOUT a source: stored as an unverified `model_claim`» | **VERO** | `m.add(...)` senza source → `status=model_claim`, `grounding=None` |
| P20 | «QUARANTINED — stored, but kept OUT of default recall» | **VERO** | il fatto contraddetto è in tabella e `m.search()` non lo restituisce |
| **P21** | «`trust_report` … on a question it cannot support it **ABSTAINS**» | **VERO** | `m.explain()` espone un campo booleano dedicato: domanda con risposta → `abstained=False`, `n_facts=1`; domanda senza → **`abstained=True`, `n_facts=0`** |
| P23 | «Every read carries `grounding_score` 0-100; `null` = NEVER JUDGED» | **VERO** | `m.search(...)[0].grounding_score = 98.94` |
| P24 | «Do NOT use `confidence` as a trust signal: the moat never rewrites it» | **VERO** | sui fatti giudicati: `(confidence 0.5, grounding 98.9)` e `(0.5, 99.0)` — resta il default di canale |
| P25 | «Legacy tool names use the `hippo_` prefix; both work» | **VERO** | `import verimem` e `import hippoagent` riescono entrambi |
| P8 | README: «revised through explicit supersession (**never silent overwrites**)» | **VERO** | due valori per Verona → **2 righe** in tabella, 1 `RITIRATO` + 1 viva: il vecchio non è sparito |
| P3 | PyPI: «bi-temporal history» | **VERO** | `m.history(fact_id)` → **2 voci** (610 e 800 con i rispettivi grounding); `as_of` è nella firma di `recall`, `search`, `explain` |
| P13 | README: «only when neither an llm nor the local model is present does the gate fail-open … says so with an `L4-skipped` advisory» | **NON MISURATO** | richiede un ambiente **senza** il modello locale: è la fetta ② (ws2, install pulito). La variabile che avevo usato (`VERIMEM_DISABLE_LOCAL_JUDGE`) **non esiste** nel codice — le vere sono `ENGRAM_GROUNDING_{WRITE,JUDGE,BACKEND}` |

**11 promesse verificate VERE, 1 non misurata da me e passata a ws2. Zero false.**

---

## La promessa centrale funziona, e ieri l'avevamo giudicata rotta

Ieri tre istanze (io, ws5, ws6) abbiamo misurato «**zero astensioni**»: una
domanda senza risposta nello store veniva servita comunque con punteggio alto.
Il dato era giusto e **la conclusione sbagliata**: misuravamo `recall`, che non
promette di astenersi. Le `instructions` attribuiscono l'astensione a
`trust_report` / `explain`, ed è lì che funziona — con un campo `abstained`
esplicito, non un'euristica sul testo.

> Il prodotto è coerente con ciò che dichiara. Eravamo noi a interrogare la
> porta sbagliata e ad attribuirgli una promessa che non fa.

Questo chiude anche il ritiro di ws5 di ieri sera («il moat DA SOLO cede, il
percorso NO»): il percorso documentato è quello giusto, ed è documentato.

---

## ⚠️ Correzione dalla fetta ② (ws2): le mie VERO valgono nel MIO ambiente

ws2 ha installato da zero (`046e6cf7`). Due cose ribaltano la lettura di sopra,
e la seconda è la più importante del task:

| | |
|---|---|
| **P17 / P11** «the moat runs by default» | **VERO qui, INATTIVO su un'installazione pulita.** Il giudice locale sono **656 MB** che `pip install` non porta: finché non si esegue `verimem warmup` il moat non gira, e il `doctor` lo dichiara («*moat OFF — fix: run `verimem warmup`*»). Le mie prove (98.9 / 0.98) girano su una macchina dove il modello c'è **già**. |
| «*`verimem save` è il comando del protocollo O3*» (nostra doc interna) | **FALSO sul pacchetto pubblicato**: PyPI 0.7.0 ha **26 comandi**, il repo **37**. Un utente che segue la nostra documentazione riceve `No such command 'save'`. |

**Il modo giusto di dirlo, e le `instructions` lo dicono già meglio del README:**
la guida MCP distingue ciò che vale *sempre* («ALWAYS: a lexical screen … with
no LLM call») da ciò che richiede il giudice («WITH a `source`: the entailment
moat»). Il README invece dice «the moat runs by default» senza aggiungere che
quel default richiede 656 MB non annunciati. **La promessa non è falsa: è
incompleta, e l'incompletezza cade tutta sul primo utente.**

Verificato da me, con `ENGRAM_GROUNDING_WRITE=0`:

- il **lexical screen sopravvive**: il vanto senza fonte resta `quarantined`
  (`grounding=None`) — P16 «ALWAYS» regge anche a moat disattivato ✅
- **ma quella variabile NON spegne il moat**: il fatto contraddetto esce
  comunque `quarantined` con `grounding=0.82`, e il sostenuto con `98.29`.
  ⇒ una variabile d'ambiente che non fa ciò che il nome dichiara — segnalata a
  ws7 (fetta ⑥, parametri), e il motivo per cui **non ho potuto simulare
  l'ambiente di ws2**: la sua misura su installazione pulita resta l'unica
  fonte per quella riga.

## Cosa manca DEL TUTTO rispetto a ciò che un utente si aspetta

Le promesse ci sono e reggono. Quello che **non è promesso da nessuna parte**, e
che un utente dà per scontato in una memoria:

1. **Nessuna promessa sul dimenticare.** Non c'è una riga su ritenzione, TTL,
   diritto all'oblio o cancellazione selettiva — in un prodotto che scrive
   permanentemente tutto ciò che gli passa un agente, e con licenza AGPL su
   dati potenzialmente personali. `verimem forget` esiste, ma non è una promessa
   dichiarata: è un comando che chi non lo cerca non trova.
2. **Nessuna promessa sul costo.** ws4 ha misurato ieri che il giudice costa
   **32,8 s mediani** e che la CLI lo ricarica ogni **1,4 scritture**. Un utente
   che legge «gated writes ON by default» non si aspetta mezzo minuto per fatto.
   Il README parla di qualità del giudice, mai di latenza.
3. **Nessuna promessa su quale porta usare per cosa.** È il difetto che ha
   ingannato tre istanze in un giorno: `recall` e `explain` sembrano
   interscambiabili e non lo sono — l'astensione è solo nella seconda. Le
   `instructions` lo dicono in una riga in mezzo ad altre; nel README non c'è.

---

## I miei tre errori di misura, dichiarati

Perché il metodo conta quanto il risultato, e tutti e tre sono la stessa classe:

1. **Il campo si chiama `text`, non `proposition`.** Il mio estrattore
   restituiva sempre lista vuota e stavo per consegnare «il pavimento nasconde
   i fatti presenti». Verificato dopo: `recall` trova il fatto con **tutte e
   cinque** le formulazioni provate, dalla frase identica alla sola parola
   «Verona».
2. **`m.history` vuole un `fact_id`**, non una query. Al primo giro l'avevo
   chiamata con del testo, avuto `[]`, e quasi scritto «bi-temporal PARZIALE».
3. **`VERIMEM_DISABLE_LOCAL_JUDGE` l'avevo inventata io.** Il test P13 girava con
   il giudice **attivo** e il quarantinamento che vedevo era corretto: non stavo
   misurando il fail-open.

La regola già scritta in casa che li copre tutti e tre: *prima di contare un
campo, stampa le chiavi.* Uno zero non è una misura, è quasi sempre una chiave
sbagliata.

---

## Riproducibilità

Banchi in `scratchpad/banco_promesse{,2,3}.py`. Ognuno crea il proprio store
temporaneo e non tocca `~/.engram`. Verificato a posteriori: zero righe con
`payload.topic` dei miei banchi nel journal di produzione.

---

## P16, l'unica promessa UNIVERSALE del documento — e l'unica verificata con un caso

*(aggiunto da ws4 Paragone il 2026-08-26 alle 20:18, `ca89d705`. Non tocco la
prova di chi ha scritto la riga: quella prova è vera. Aggiungo la popolazione
che le mancava.)*

Le altre dieci promesse tabellate qui sopra sono **binarie**: «senza source →
`model_claim`», «`history` → 2 voci», «entrambi gli import riescono». Per una
promessa binaria un caso **basta**, e infatti sono verificate bene — P17 ha
perfino le due popolazioni (sostenuto 98.9 · contraddetto 0.82).

P16 è l'unica **quantificata universalmente**: dice «**ALWAYS**» e dice
«**self-claims**», che è una categoria semantica e non un elenco. Le tre parole
fra virgolette — `"it works / verified / done"` — arrivano dopo «Unsupported …
self-claims», quindi leggono come **esempi**, non come definizione. Ed è
verificata con `m.add("La migrazione è stata completata e funziona
perfettamente.")`: una frase che contiene **due** parole canoniche insieme.

Misurato il 26/08 alle 20:11 (`48e130f0`, store temporaneo, fuori da pytest,
regime senza source — quindi il lexical screen è l'unica difesa, che è
esattamente il regime di cui P16 parla):

| | |
|---|---|
| rilevatori L1 provati | 12 |
| canoniche effettivamente trattenute | 9/12 |
| **riformulazioni equivalenti che eludono** | **9 su 9** |
| rilevatori che resistono a entrambe le forme | **nessuno** |

    «Il modulo è stato testato»   TRATT L1.15  ·  «ha superato i test»           passa
    «Il sistema è sicuro»         TRATT L1.12  ·  «non ci sono vulnerabilità»    passa
    «Il modulo è documentato»     TRATT L1.14  ·  «c'è la documentazione»        passa

Le riformulazioni non sono più deboli: sono uguali o **più forti**.

E sull'altra popolazione l'errore è opposto — 5 falsi positivi su 12: «sto
provando se funziona», «valutiamo se è pronto», «andrebbe documentato». Il
gate premia chi si vanta con parole diverse e punisce chi ammette un debito.

**Ma non è un dizionario cieco**, e la prima stesura di questa nota lo dava per
tale a torto: le negazioni trattenute per errore sono **0 su 5** («Il modulo
NON è documentato» passa correttamente). La guardia sulla polarità c'è e
funziona. Manca ogni dimensione semantica **diversa** dalla polarità.

⇒ **La riga giusta non è «P16 è falsa»: è che «ALWAYS» promette una categoria e
l'implementazione copre un elenco.** La cura è scrivere il perimetro vero, non
togliere il gate. Presidio: `tests/test_il_gate_vede_la_polarita_e_nient_altro.py`.

### 🔑 La classe di metodo, e vale oltre questo documento

**Il tipo logico della promessa decide quanti casi servono a verificarla.**
Una promessa binaria si verifica con un caso. Una promessa che dice «ALWAYS»,
«mai», «ogni» **non si può verificare con un caso**: serve una popolazione, e
la popolazione va scelta da chi *non* ha in mente la promessa.

Ed è la seconda istanza nella stessa giornata. La prima:
`l1_performance_detector.py:138-144` riporta una misura del 03/08 che
concludeva «ogni lingua copriva metà del caso» — usava una sola forma verbale,
e per caso proprio l'unica immune al difetto (`«N volte più veloce»`, già
copulativa). Anche lì il campione veniva dall'esempio, non dalla popolazione.
