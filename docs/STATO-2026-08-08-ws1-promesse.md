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
| P16 | «ALWAYS: a lexical screen on every write. Unsupported "it works / verified / done" self-claims are quarantined, with no LLM call» | **VERO** | `m.add("La migrazione è stata completata e funziona perfettamente.")` → `status=quarantined` |
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
