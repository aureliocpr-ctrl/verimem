# Profili di strumenti — il design, con la manopola vera e il suo limite

**ws4 (Nadia Ferro, ML engineer), 06/09 notte.** Deliverable ③ del ruolo, chiesto dal
CTO il 04/09 e ripreso nella raccolta dell'01:31: *«la manopola vera dei profili col suo
nome nel design; `HIPPO_EXPOSE_TOOLS` resta "spenta" nel registro»*.
**Questo è un DESIGN, non una cura**: nessuna riga di prodotto è stata toccata.

## 1. Il problema, con il numero di chi l'ha misurato

Il Product Owner ha misurato che **249 strumenti costano 38.675 token per sessione** a
ogni client MCP (`T2b`, gravità P2, vetrina **e** costo). Il costo si paga a ogni
apertura, per tutti, anche per chi userà tre strumenti.

## 2. I dati d'uso — la curva, non l'opinione

Dall'audit `~/.engram/mcp_audit.log`: **15.394 righe**, finestra **08/05 01:41 →
04/09 21:51 (119,8 giorni)**. ⚠️ **Perimetro dichiarato**: è il traffico di **questa
macchina**, dove otto istanze sviluppano il prodotto. **Non è un utente reale.**
Prima della classifica, la pulizia: **6 nomi chiamati non esistono fra i 249 esposti**
(294 chiamate, l'1,9%; `does_not_exist` da solo 286, esito `unknown_tool`) — **tolti**,
altrimenti sarebbe entrato in top-20.

Sui **15.099** rimasti:

| copertura | strumenti | % dei 249 |
|---|---|---|
| 50% delle chiamate | **11** | 4,4% |
| 80% | **28** | 11,2% |
| **90%** | **37** | 14,9% |
| 95% | **43** | 17,3% |
| un set base di **20** | copre **69,2%** | |
| **mai chiamati in 119,8 giorni** | **102** | **41,0%** |

⇒ **Un set base di «~20» lascia fuori il 30,8% delle chiamate**: una su tre sveglierebbe
il profilo esteso. Se il criterio è «l'utente non deve accorgersi del profilo», il numero
è **37-38**; se è «il minimo che fa lavorare», sono **11**. **La curva è questa; la
soglia è una decisione, non una misura.**

### 2-bis. Il dato d'uso RECENTE (Aldo, 06/09 03:55) — e insieme al mio dice una terza cosa

Misurato da @ws6 su una **sorgente diversa dalla mia**: `~/.engram/events.jsonl`, evento
`audit_tool_call`.

    163 chiamate · 12 strumenti distinti · dal 02/09 01:35 al 05/09 22:56 (3,9 giorni)

      hippo_remember                 91     hippo_facts_list                2
      hippo_facts_search             41     hippo_fact_forget               2
      hippo_facts_recall             10     hippo_document_list             2
      hippo_recall                    4     sandbox_exec                    2
      hippo_document_semantic_search  4     hippo_document_index_file       1
      hippo_recall_as_of              3     hippo_document_promote_chunk    1

    ⇒ 12 strumenti su 247 = 4,9%   ·   hippo_assess_fact_freshness: ZERO

🔑 **I due dati non si contraddicono, e da soli dicono meno di quanto dicono insieme.**
Il mio guarda **119,8 giorni** e trova che **147 strumenti su 249 sono stati chiamati
almeno una volta**; il suo guarda **3,9 giorni** e ne trova **12**. Non è una
contraddizione: è che **l'uso è concentrato NEL TEMPO**, non solo nella classifica.
⇒ **Per un profilo la domanda giusta non è «quali sono stati usati qualche volta», ma
«quali servono in una finestra di lavoro»** — e su una finestra di lavoro vera il numero
non è 37, è **poco più di dieci**. Questo *rafforza* la proposta della §6 e ne sposta la
soglia verso il basso.

⚠️ **I limiti, che sono di entrambi i dati**: è il traffico di **questa macchina**, dove
otto istanze sviluppano il prodotto — **non è un utente**. Il journal **ruota**, quindi
3,9 giorni non sono la storia. E, come scrive Aldo, **zero chiamate non prova che una
capacità non funzioni: prova che non l'abbiamo accesa.**

### 2-ter. 🔴 IL DENOMINATORE HA QUATTRO VALORI, e questa è la parte da chiudere

Scrivendo questa sezione ho trovato che il numero di strumenti esposti è scritto in
quattro modi diversi, tutti «veri» nella loro fonte:

    249   _list_tools_unfiltered() ESEGUITA ADESSO          ← la misura, non un conteggio
    251   occorrenze di `Tool(` nel sorgente                 (un pattern, non una lista)
    248   commento in mcp_server.py, misurato il 16/08       (un numero che è invecchiato)
    247   la misura di Aldo del 06/09                        (da riconciliare con lui)

⇒ **Il valore che conta è `249`**, perché è **la lunghezza della lista che il server
costruisce**, non un conteggio di occorrenze né un numero scritto in un commento. Il
filtro pubblico applica `ENGRAM_MCP_TOOLS_PREFIX` e poi `_apply_tool_namespace`, che
**rinomina senza togliere** (*«one tool in, one tool out»*): **a variabile non impostata
il numero resta 249.**
📌 **La differenza con il 247 di Aldo resta aperta e non la chiudo io** inventando una
riconciliazione: è di due unità e va confrontata con la sua misura. **Un numero pubblico
che ha quattro forme si chiude eseguendo, non scegliendo la forma che ci comoda.**

## 3. La manopola che ESISTE, col suo nome

**`ENGRAM_MCP_TOOLS_PREFIX`** — implementata e applicata al gestore pubblico:

```
  mcp_server.py:1533  # Backward-compat: ENGRAM_MCP_TOOLS_PREFIX unset → ALL tools returned
  mcp_server.py:1543  """Parse ENGRAM_MCP_TOOLS_PREFIX into a set of allowed name prefixes."""
  mcp_server.py:1550  raw = os.environ.get("ENGRAM_MCP_TOOLS_PREFIX", "").strip()
  mcp_server.py:7598  """Public MCP handler: full registry filtered by ENGRAM_MCP_TOOLS_PREFIX."""
```

## 4. 🔑 Perché NON basta, ed è il punto del design

Il filtro lavora **per PREFISSO**. I venti più usati sono:

`hippo_remember` 1741 · `hippo_facts_search` 1165 · `hippo_run_task` 643 ·
`hippo_record_episode` 639 · `hippo_episode_get` 584 · `hippo_recall` 574 ·
`hippo_skill_retire` 562 · `hippo_facts_recall` 559 · `hippo_skills_for` 453 ·
`hippo_plan_forward` 377 · `hippo_search` 370 · `hippo_consolidate` 356 ·
`hippo_status` 339 · `hippo_skill_lineage` 315 · `hippo_plan_strips` 313 ·
`hippo_skill_derive_predicates` 300 · `hippo_health` 296 · `hippo_skill_top` 290 ·
`hippo_skills_search` 288 · `hippo_skill_promote` 282

**Non condividono un prefisso**: sono tutti `hippo_` come gli altri 228. ⇒ con `hippo_`
passano tutti e 248; con qualunque prefisso più stretto se ne perde la maggior parte.
**La manopola che c'è non può esprimere un profilo.**

## 5. E quella che servirebbe non è implementata

**`HIPPO_EXPOSE_TOOLS`** prende **una lista di nomi** ed è **impostata sulla macchina di
Aurelio con 10 nomi** — ma `grep -rn "HIPPO_EXPOSE_TOOLS" verimem/` dà **zero righe**, e
il nostro registro la elenca già fra le cose spente (`03-cose-spente.md`: *«è impostata
sul tuo computer ma nessuna riga»*, e *«file del pacchetto importato che leggono
HIPPO_EXPOSE_TOOLS: 0»*).

> 🔑 **Le due metà della soluzione esistono, in due posti diversi: quella implementata non
> serve al nostro problema, quella che servirebbe non è implementata.** Non manca un'idea:
> manca una giuntura.

## 6. La proposta

**Un profilo è una LISTA DI NOMI, non un prefisso.** Tre profili, dai dati di §2:

| profilo | quanti | copre | a chi serve |
|---|---|---|---|
| `minimo` | **11** | 50% | chi apre una sessione e scrive/rilegge |
| `base` | **28** | 80% | l'uso normale di un agente |
| `pieno` | **37** | 90% | chi lavora sul prodotto |
| *(assente)* | 249 | 100% | oggi: tutti, sempre |

**Come**: estendere `_prefissi_consentiti` (che già esiste e già filtra) ad accettare
**anche nomi esatti**, e leggere **`HIPPO_EXPOSE_TOOLS`** come lista — così la variabile
che l'utente **ha già impostato** smette di essere una manopola scollegata. ⚠️ **Chi
implementa decide**: è la porta, non il mio perimetro.

## 7. 🔗 Il vincolo che lega i profili alla matrice dei permessi

**Dei 20 più usati, solo 13 sono classificati** nella matrice. Gli scoperti fra i primi
venti: `hippo_plan_forward`, `hippo_plan_strips`, `hippo_skill_derive_predicates`,
`hippo_skill_lineage`, `hippo_skills_for`, `hippo_skills_search`, e `hippo_skill_promote`.

> **Chi entra nel set base è esattamente chi gira sempre: quello è l'insieme che DEVE
> avere un permesso esplicito.** ⇒ **il set base non è «i più usati»: è «i più usati E
> classificati»**, e i sette scoperti si classificano *prima* di entrare.

## 8. Cosa questo design NON dice

- **Non ho misurato i token risparmiati**: il `38.675` è del Product Owner e il risparmio
  va calcolato sulle **descrizioni** dei tool esclusi, non sul loro numero.
- **Il traffico è nostro, non degli utenti** (§2): un utente vero userebbe altri
  strumenti, e i profili andrebbero rifatti sul suo traffico quando ne avremo.
- **La coda dei 120 giorni pesa come l'ultima settimana** e non dovrebbe: una finestra
  mobile darebbe numeri diversi, e non l'ho provata.
- **Non ho verificato che `ENGRAM_MCP_TOOLS_PREFIX` funzioni davvero a runtime**: l'ho
  letta nel sorgente, non eseguita. Chi la prova, la provi con il **controllo positivo**
  (un prefisso che DEVE ridurre l'elenco).

📌 Banchi: `docs/stato-reale/banchi/ws4-quanti-strumenti-hanno-un-permesso.py` (la
matrice), e per il traffico i due versati con questa pagina.

---

# Appendice · La matrice dei permessi, i 31 verdetti (`D-ws4-4`)

**Perché sta qui e non in una pagina sua**: un profilo di strumenti deve sapere **chi
scrive**, altrimenti «profilo minimo» e «profilo sicuro» diventano la stessa parola per due
cose diverse. Il banco che ha prodotto questi verdetti è in `main` da `6607e370`
(`docs/stato-reale/banchi/ws4-quanti-strumenti-hanno-un-permesso.py`); **i verdetti finora
vivevano solo sul canale e su un board** — cioè in due posti che fra sei mesi nessuno
rilegge. È lo stesso difetto che questa pagina denuncia altrove, applicato a me.

**Metodo**: `31 su 31 letti nel codice`, uno per uno, ogni verdetto con la riga che lo
prova. **Non** dedotti dal nome, **non** dalla firma, **non** dalle chiamate a due livelli:
tre euristiche provate e tutte e tre cadute (§ sotto).

## Scrivono sempre — 18

    forget_with_report · heal_contradictions · dream_adopt · entity_link
    document_promote_chunk · fact_supersede_chain · emerging_skill_promote
    emerging_skills_register · quarantine_restore · self_model_update
    contradictions_resolve · skill_edit · transcript_promote · import_conversations
    record_episodes_batch · skill_import · skill_merge · consolidate_light

## Non scrivono mai — 5

    facts_merge · facts_topic_merge · smart_prune · topic_cleanup_suggestions
    trajectory_fork

⚠️ **`facts_merge` non scrive**: *calcola* la fusione e la restituisce. Ma la sua
descrizione promette *«atomically apply»* per **due chiamate separate**, mentre
`fact_supersede_chain` l'atomicità la fa davvero. **Due strumenti con «merge» nel nome e
tre comportamenti diversi** — la lista dei quattro «merge» è un ticket a sé.

## Condizionali — 8, tutti con `apply=False` di default

    episodes_dedup · apply_recommendations · skill_retire_invisible
    skill_promote_by_threshold · skill_merge_pair · promote_chain · skill_clone
    skill_archive

🔴 **E qui c'è il difetto che lega la matrice al gate**: `_capability_gate(name, arguments)`
**riceve gli argomenti e decide sul nome**. ⇒ Per questi otto, la matrice **non può
esprimere** «scrive solo se `apply=True`»: o li tratta tutti come scriventi (e il profilo
sicuro perde otto strumenti utili), o come non scriventi (e ne lascia passare otto che
possono scrivere). **Il modello giusto esiste già nel prodotto**: `skill_retire_invisible`
mette `dry_run` **nel payload**, dove il gate lo può leggere.

## 🔑 Le tre euristiche cadute, e valgono più dei verdetti

    ① il NOME               → 42% dei «sospetti per nome» NON scrive
    ② le chiamate a 2 hop   → un tool che chiama un writer può non scrivere mai
    ③ la FIRMA              → falsificata dal caso dichiarato: `topic_cleanup_suggestions`
                              riceve `semantic` **per LEGGERE**

⇒ **Nessuna scorciatoia regge: il codice si legge.** E il tentativo di costruire un
righello automatico è fallito **due volte** — il primo metodo era cieco (`9/14` sul
controllo positivo), il secondo troppo largo (**36 su 36 falsi positivi**, bastava la
parola `write` in una riga qualsiasi). **Il fallimento è il risultato**: pubblicare i
verdetti di quel righello sarebbe costato più che leggerli a mano.
