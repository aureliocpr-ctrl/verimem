# mappa — `verimem/semantic.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 20:43

**6.690 righe · 155 funzioni · 4 classi.** Misurato con `ast`, non con grep:
`scratchpad/inventario.py verimem/semantic.py` — l'albero sintattico conta le
definizioni, `grep "def "` conterebbe anche le stringhe e i commenti.

## Metodo, e i suoi limiti dichiarati

- «chiamata da» è **letta**, non grepata: il grep trova il punto, poi si apre il
  file a quella riga e si guarda che sia una chiamata vera.
- «prova» è un comando **eseguito** con il suo esito. Dove non l'ho eseguito il
  verdetto è **NON MISURATO** e la casella dice cosa mancherebbe per misurarlo.
- Un test che passa prova **ciò che quel test asserisce**, non tutto il claim:
  dove il test copre una parte del claim, il verdetto lo dice.

## Le righe

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `store` (semantic.py:2843) | «Insert or replace a fact. Backwards-compatible default returns None.» | `client.py:873` — `self.semantic.store(fact, embed="sync", purpose=purpose, …)`, unica via di scrittura dell'SDK | `tests/test_client_sdk.py` | riga 179: «the old row stays for lineage» (parziale: qui solo l'inserimento) | **FUNZIONA COME PROMESSO** (limitato a: la scrittura entra e la ricevuta torna) | `pytest -q tests/test_client_sdk.py` → `23 passed, 23 warnings in 94.91s` EXIT=0 (20:17, base 7b9e8ca1) |
| 2 | `recall` (semantic.py:4008) | «Semantic recall over facts (cosine on embeddings).» | `client.py:1343` — `hits = self.semantic.recall(query, k=k, deep=deep, …)`; `client.py:2891-2892` per il confronto normali/profondi | `tests/test_i_due_rami_di_search_portano_le_stesse_cose.py` | riga 466: «Search — optionally with history context or as of a past moment» | **FUNZIONA COME PROMESSO** (limitato a: i due rami tornano le stesse cose) | `pytest -q tests/…due_rami…py` → `4 passed, 1 warning in 12.38s` EXIT=0 (20:20, base 7b9e8ca1) |
| 3 | `supersede` (semantic.py:5806) | «Cycle #78 — declare `old_id` superseded by `new_id`.» | `client.py:979` — `_sup_res = self.semantic.supersede(…)` nel ramo same-source evolution; `client.py:3976` nella riconciliazione | `tests/test_entity_supersede_leak.py::test_get_live_only_excludes_superseded` · `tests/test_deep_recall_asof.py` · `tests/test_audit_mutations.py` | riga 179: «`superseded_by` the new (never a silent overwrite — the old row stays for lineage)» · riga 521: «A fact disappears in TWO ways — retired (superseded) or quarantined» | **FUNZIONA COME PROMESSO** sul claim «the old row stays» — ⚠️ ma il presidio più diretto NON passa dalla funzione: vedi la nota sotto la tabella | `pytest -q tests/test_entity_supersede_leak.py` → `4 passed in 7.40s` EXIT=0 · `tests/test_deep_recall_asof.py` → `6 passed in 10.65s` EXIT=0 · `tests/test_audit_mutations.py` → `27 passed in 15.15s` EXIT=0 (tutti 20:35, base 7b9e8ca1) |
| 4 | `recall_hybrid` (semantic.py:5101) | «Hybrid recall: semantic cosine + keyword overlap re-rank.» | `proactive_step_injector.py:115` — `scored = semantic.recall_hybrid(…)`, **unico** chiamante in `verimem/` | `tests/test_recall_hybrid.py` | riga 466: «Search — optionally with history context or as of a past moment» | **FUNZIONA COME PROMESSO**, limitato a ciò che il test asserisce | `pytest -q tests/test_recall_hybrid.py` → `4 passed, 1 warning in 9.45s` EXIT=0 |
| 5 | `supersede_chain` (semantic.py:6146) | «Cycle #81 — declare a multi-hop supersession» | `mcp_server.py:15086` — `result = a.semantic.supersede_chain(…)`, **unico** chiamante: è esposta solo dalla porta MCP | `tests/test_freshness_check.py` · `tests/test_audit_mutations.py` | riga 179 (lineage) | **FUNZIONA COME PROMESSO**, limitato a ciò che i test asseriscono | `pytest -q tests/test_freshness_check.py` → `10 passed, 1 warning in 13.58s` EXIT=0 · `test_audit_mutations.py` → `27 passed` EXIT=0 |
| 6 | `store_within_budget` (semantic.py:437) | «Persist `fact` via `memory.store` without letting the INTERACTIVE call …» | `mcp_server.py:9402` (episodi), `:9551` (fatti), `:13624` — tre chiamate, tutte dalla porta MCP | `tests/test_deferred_write_durability.py` | nessun claim README diretto (è il budget di latenza, non una promessa di vetrina) | **FUNZIONA COME PROMESSO**, limitato a: la scrittura differita è durevole | `pytest -q tests/test_deferred_write_durability.py` → `3 passed in 9.32s` EXIT=0 |
| 7 | `audit_head_at` (semantic.py:6573) | «Stored head of the `count`-th chained mutation row (1-indexed), or …» | `cli.py:5778`, `cli.py:5907`, `client.py:2731` — ⚠️ passata come **CALLBACK** (`head_at=sm.audit_head_at`), mai chiamata con le parentesi | `tests/test_tamper_anchor_receipt.py` | riga 244: «audit every revision» | **FUNZIONA COME PROMESSO**, limitato a ciò che il test asserisce | `pytest -q tests/test_tamper_anchor_receipt.py` → `23 passed, 1 warning in 15.39s` EXIT=0 |
| 8 | `set_derives_from` (semantic.py:3704) | dichiara i genitori di un fatto derivato | `composer.py:407` — `mem.semantic.set_derives_from(fid, [a.id, b.id])`, **unico** chiamante | 🔴 **NESSUNO**: il nome nudo cercato in tutto il repo (`*.py`, `*.md`) compare solo in `CHANGELOG.md`, `composer.py` e nella propria definizione | **CHANGELOG:1320** — «`semantic.set_derives_from` declares …» | **NON MISURATO** — ed è il caso che il mandato cerca: una funzione **citata in un claim del CHANGELOG** e senza un solo test che la nomini | `grep -rn set_derives_from --include=*.py --include=*.md .` → 3 righe, nessuna in `tests/` |
| 9 | `direct_predecessors` (semantic.py:6098) | i predecessori diretti di un fatto | `cli.py:3623` · `client.py:3924` — **letto**: non è `history`, è la **purga** («a partial purge would leave sensitive rows resurrectable via as_of»), chiusura all'indietro di tutte le generazioni | nessun test la **nomina**; la esercita **indirettamente** `tests/test_la_storia_si_troncava_in_silenzio.py` via `history()` | `docs/AUDIT-LEDGER.md:386` (M8-1): «FIXATO: rewind al capostipite via `direct_predecessors` … **4 test**» | **FUNZIONA COME PROMESSO**, per via indiretta — e il «4 test» del documento **combacia**: quel file dà esattamente `4 passed` | `pytest -q tests/test_la_storia_si_troncava_in_silenzio.py` → `4 passed, 22 warnings in 63.17s` EXIT=0 · `test_temporal_context.py` → `6 passed in 10.16s` EXIT=0 |
| 10 | `get_supersession_chain` (semantic.py) | la catena di supersessione di un fatto | `client.py:3913` (dentro il walk della storia) · `corpus_health_metrics.py:137` — cercati col nome QUALIFICATO `.nome(`, perche' il nome nudo di queste sei pesca ogni dizionario | `tests/test_fact_supersede.py` | riga 179 (lineage) | **FUNZIONA COME PROMESSO**, limitato a ciò che il test asserisce | `pytest -q tests/test_fact_supersede.py` → `18 passed, 1 warning in 11.23s` EXIT=0 |
| 11 | `count_superseded` (semantic.py) | quanti fatti sono stati ritirati | `cli.py:311` (la riga di stato) · `client.py:3210` · `client.py:3595` | `tests/test_fact_supersede.py` | riga 521 («A fact disappears in TWO ways») | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione della riga 10 |
| 12 | `delete_with_undo` (semantic.py) | cancella lasciando l'operazione annullabile | `cli.py:3578` · `cli.py:3635` · `mcp_server.py:14763` — due porte su tre | `tests/test_undo_log.py` | riga 228 («restore refuses a **superseded** fact») | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_undo_log.py` → `15 passed, 1 warning in 11.61s` EXIT=0 |
| 13 | `list_undoable_ops` (semantic.py) | elenca le operazioni annullabili | `cli.py:3694` · `cli.py:3732` · `mcp_server.py:14855` | `tests/test_undo_log.py` | riga 228 | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione della riga 12 |
| 14 | `undo_destructive_op` (semantic.py) | annulla un'operazione distruttiva | `cli.py:3702` · `client.py:4060` · `gateway.py:1427` — ⚠️ **quattro** superfici con MCP: CLI, SDK, gateway HTTP e porta MCP | `tests/test_undo_log.py` | riga 228 | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione della riga 12 |
| 15 | `search_facts` (semantic.py) | ricerca per parola sui fatti | `cli.py:3358` · `client.py:1789` e `:1793` (due conteggi) | `tests/test_quanti_fatti_ho.py` | riga 466 (search) | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_quanti_fatti_ho.py` → `6 passed, 1 warning in 9.29s` EXIT=0 |

| 16 | `quarantine_fact` (semantic.py) | mette un fatto in quarantena | `client.py:2540` · `composer.py:397` | `tests/test_triage_corpus.py` · `tests/test_l_esclusione_serviva_un_fatto_quarantinato.py` | riga 521: «A fact disappears in TWO ways — retired (superseded) or **quarantined**» | **FUNZIONA COME PROMESSO**, limitato a ciò che il test asserisce | `pytest -q tests/test_triage_corpus.py` → `6 passed, 1 warning in 9.45s` EXIT=0 |
| 17 | `restore_fact` (semantic.py) | riabilita un fatto quarantinato | `client.py:2566` · `client.py:3776` | `tests/test_timone_non_resuscita_i_cancellati.py` | riga 228: «a *guarded* human override, not a back door: restore refuses a **superseded** fact» | **FUNZIONA COME PROMESSO** — il nome del test presidia proprio il claim («non resuscita i cancellati») | `pytest -q tests/test_timone_non_resuscita_i_cancellati.py` → `4 passed, 1 warning in 11.54s` EXIT=0 |
| 18 | `mark_orphaned` (semantic.py) | marca un fatto come orfano (L2 reconciler) | `cli.py:4292` — `sm.mark_orphaned(fid, reason="cli facts anti-confab-apply")` · `mcp_server.py` | `tests/test_cli_facts.py` | nessun claim README diretto; lo status `orphaned` è in `_VALID_STATUSES` (semantic.py:573) | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_cli_facts.py` → `15 passed, 1 warning in 14.0s` EXIT=0 |

| 19 | `get` (semantic.py) | legge un fatto per id | **26 chiamate qualificate** in `verimem/` — `active_probe.py:49` e `:66`, e altre 24: è la lettura di base | `tests/test_quanti_fatti_ho.py` · `tests/test_entity_supersede_leak.py` | riga 179 — è la funzione che rende vero «the old row stays»: `get(id)` risolve anche un id ritirato, `get(id, live_only=True)` no | **FUNZIONA COME PROMESSO** — è la riga 3 vista dal lato del lettore | `pytest -q tests/test_entity_supersede_leak.py` → `4 passed in 7.40s` EXIT=0 · `test_quanti_fatti_ho.py` → `6 passed in 9.29s` EXIT=0 |
| 20 | `list_facts` (semantic.py) | elenca i fatti con filtri | **34 chiamate qualificate**, il numero più alto del file — `client.py:3550`, `client.py:3962` e altre 32 | `tests/test_quanti_fatti_ho.py` · `tests/test_l_esclusione_serviva_un_fatto_quarantinato.py` | riga 521 (i due modi in cui un fatto sparisce dalla vista) | **FUNZIONA COME PROMESSO**, limitato a ciò che i test asseriscono | `pytest -q tests/test_quanti_fatti_ho.py` → `6 passed, 1 warning in 9.29s` EXIT=0 |
| 21 | `count` (semantic.py) | quanti fatti ci sono | 12 chiamate qualificate — `cli.py:251` (la riga di stato del prodotto), `client.py:1077` | `tests/test_quanti_fatti_ho.py` | il nome del test è il claim: «quanti fatti ho» | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione della riga 20 |
| 22 | `all` (semantic.py) | tutti i fatti | 14 chiamate qualificate — `anti_confab_gate.py:1386` (il gate legge il corpus), `cli.py:3554` | `tests/test_quanti_fatti_ho.py` · `tests/test_triage_corpus.py` | nessun claim README diretto | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_triage_corpus.py` → `6 passed, 1 warning in 9.45s` EXIT=0 |
| 23 | `delete` (semantic.py) | cancella un fatto | 5 chiamate qualificate — `cli.py:3582`, `client.py:3909` | `tests/test_cli_facts.py` · `tests/test_timone_non_resuscita_i_cancellati.py` | riga 521 · riga 228 | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_cli_facts.py` → `15 passed, 1 warning in 14.0s` EXIT=0 |
| 24 | `clear` (semantic.py) | svuota lo store | ⚠️ **1 sola** chiamata qualificata in tutto `verimem/`: `agent.py:103` | `tests/test_audit_mutations.py` · `tests/test_pentest_validation.py` | nessun claim README | **FUNZIONA COME PROMESSO**, limitato — e l'unico chiamante è stato **aperto**: vedi «il caso più distruttivo» sotto la tabella | `pytest -q tests/test_audit_mutations.py` → `27 passed, 1 warning in 15.15s` EXIT=0 |

## Contatore

**54 / 155 funzioni mappate, tutte con un comando eseguito nella casella prova
tranne la riga 8, che è NON MISURATO per assenza di test — e lo dice.**
Le caselle «chiamata da» delle righe 10-15 sono state lette col nome
QUALIFICATO (`.nome(`): il nome nudo, giusto per i callback, su nomi come
`get`/`count`/`delete` pesca ogni dizionario e dava 1.065 file candidati. Le altre 148 sono nell'inventario e non sono ancora state toccate: non
hanno una riga qui perché una riga vuota si legge come lavoro fatto.

## ⚠️ «MAI CHIAMATA» — la trappola che ho quasi calpestato alla riga 7

Il mandato dice che il verdetto MAI CHIAMATA porta a **proporre la rimozione**.
Alla riga 7 ci sono arrivato vicino: `grep -rn "audit_head_at(" verimem/` non
dà **nessun** chiamante, e la conclusione ovvia sarebbe «codice morto».

È falsa. La funzione è viva e usata in tre punti, ma passata come **callback**:

```python
# cli.py:5778 · cli.py:5907 · client.py:2731
head_at=sm.audit_head_at        # il riferimento, senza le parentesi
```

Il grep con la parentesi cerca la CHIAMATA; un riferimento passato a una
funzione non ha parentesi e non compare. **Chi mappa cercando `nome(`
proporrà di rimuovere codice vivo**, e su 2.973 funzioni succederà più di una
volta.

⇒ Regola per tutte le righe di questa mappa: prima di scrivere MAI CHIAMATA si
cerca il **nome nudo** in tutto il repo, non `nome(`, e si guarda anche
`getattr`, i dizionari di dispatch e le stringhe. Se dopo questo non c'è nulla,
allora è un candidato — e resta comunque da eseguire qualcosa che lo dimostri.

### E ho sbagliato altre DUE volte prima di arrivare a zero

Il verdetto MAI CHIAMATA porta a **proporre la rimozione**, quindi un falso
«morto» qui costa codice vivo cancellato. Ci sono arrivato vicino tre volte, con
tre righelli diversi, e ogni volta il numero sbagliato era **a mio favore**
(più codice morto = mappa più interessante):

| righello | cosa dava | il vero |
|---|---|---|
| `grep "nome("` — cerca la **chiamata** | `audit_head_at` orfana | viva, passata come **callback** senza parentesi |
| nome nudo, ma **escludendo il file stesso** | **91 orfane su 155** | quasi tutte helper `_private` chiamati **dentro** `semantic.py`: «nessuno la usa da fuori» ≠ «nessuno la usa» |
| nome nudo dentro e fuori, ma solo in `verimem/` e `tests/` | 2 orfane | entrambe chiamate da **`benchmark/eval_retrieval_with_gt.py`** — cercavo in due directory su N |

**Esito: zero MAI CHIAMATA su 155.** Non perché il codice sia perfetto, ma
perché ogni volta che il righello diceva «morto» il codice era vivo altrove.

📌 `tests/test_rerank_breaker.py:485` fa `assert "_fusion_breaker_tripped_now()" in src`
— un test che presidia la **presenza testuale** della chiamata nel sorgente,
cioè esattamente un antidoto alla rimozione per errore. Vale la pena saperlo
prima di proporre rimozioni altrove.

📌 E una cosa che il grep nudo ha mostrato e la parentesi avrebbe nascosto:
`audit_head_at` esiste **due volte**, in `semantic.py:6573` (catena dei fatti) e
in `memory.py:2645` (catena degli episodi, «the episodic chain head»). Non è un
duplicato: sono due catene diverse con lo stesso nome. `memory.py` è nella mia
lista e la riga andrà lì, non qui.

## Il reperto della riga 3, e la sua correzione

**Primo sospetto, e ERA SBAGLIATO**: avevo scritto che il claim README:179
(«never a silent overwrite — the old row stays for lineage») poteva non essere
presidiato, perché il primo test che avevo trovato (`test_audit_mutations`)
prova l'audit della mutazione e non la sopravvivenza della riga. Cercato meglio:
il presidio **c'è**, ed è esplicito —

```python
# tests/test_entity_supersede_leak.py::test_get_live_only_excludes_superseded
assert sm.get("old01") is not None, "plain get must still resolve any id"
assert sm.get("old01", live_only=True) is None, "live_only get must hide a superseded fact"
```
`pytest -q tests/test_entity_supersede_leak.py` → `4 passed in 7.40s` EXIT=0.

**Ma cercandolo ho trovato una cosa più fine, e questa resta.** Quel test
supersede così:

```python
def _supersede(sm, old_id, new_id):
    with sm._connect() as conn:
        conn.execute("UPDATE facts SET superseded_by = ? WHERE id = ?", (new_id, old_id))
```

cioè **in SQL diretto, senza chiamare `semantic.supersede()`**. Presidia
l'invariante dello STORE (una riga marcata resta leggibile), non il
comportamento della FUNZIONE che il README nomina. Se un giorno
`semantic.supersede()` cancellasse la riga invece di marcarla, questo test
resterebbe verde.

⇒ Il claim è coperto **sul dato**, non **sulla funzione**. Non è un difetto e
non apro un ticket: è la distinzione che questa mappa serve a rendere visibile,
e la scrivo qui perché il verdetto «FUNZIONA COME PROMESSO» della riga 3 non
venga letto come «`supersede()` è presidiata».

📌 Metodo, per le prossime 148 righe: il primo test che nomina una funzione non
è necessariamente il test che presidia il suo claim, e un test che presidia il
claim non è necessariamente un test di quella funzione. Vanno guardate e dette
come due cose diverse.


## Il caso più distruttivo del file, e il meglio presidiato

`clear` ha **un solo** chiamante, e aprirlo porta alla catena completa dello
svuotamento — il caso limite dell'invariante di questo ruolo, «nulla scritto si
perde»:

```
cli.py:2589  verimem reset  →  agent.py:99 VerimemAgent.reset()  →
                                memory.clear · skills.clear · semantic.clear
                                (principal="system:agent-reset")
```

Il comando della CLI, **letto per intero**:

```python
@app.command()
def reset(yes: bool = typer.Option(False, "--yes")):
    """Wipe all episodes, skills, semantic facts."""
    if not yes:
        confirm = typer.confirm("Wipe ALL memory and skills?", default=False)
        if not confirm:
            raise typer.Abort()
    VerimemAgent.build().reset()
```

**Tre presidi, non uno:**
1. la guardia è **doppia** — o il flag `--yes`, o una conferma interattiva con
   `default=False` (il default nega, non conferma);
2. lo svuotamento dei fatti finisce nel **registro delle mutazioni**:
   `tests/test_audit_mutations.py:128` asserisce `r["action"] == "reset"`;
3. e quello degli episodi pure: `tests/test_audit_mutations_episodic.py:92`.

⇒ **FUNZIONA COME PROMESSO.** L'invariante regge nel senso giusto: si perde solo
su richiesta esplicita, e con una traccia che resta. Lo scrivo perché una mappa
che segnala solo i rossi mente per omissione: qui il punto più pericoloso del
file è anche quello con più guardie, e chi legge deve saperlo prima di
proporre di irrigidirlo.

Prova: `pytest -q tests/test_audit_mutations.py` → `27 passed, 1 warning in
15.15s` EXIT=0 · `tests/test_cli_facts.py` → `15 passed in 14.0s` EXIT=0.
⚠️ Non ho eseguito `verimem reset`: è distruttivo e lo store di casa non è un
banco. La riga è sostenuta dalla lettura del codice e dai test dell'audit, e
questo limite è dichiarato.


## Le `_private`: 114, mappate a BLOCCHI — e perché

Le 114 funzioni private di questo file non hanno una riga ciascuna, e il motivo
va detto invece di lasciarlo dedurre: sono **helper**, non superficie. Nessuna è
dietro un claim del README, nessuna è chiamata da fuori `verimem/`, e una riga
per ciascuna con la stessa prova ripetuta 114 volte darebbe l'aspetto di 114
verifiche dove ce n'è una. **Il blocco è l'unità onesta**: un test, l'elenco di
ciò che copre, una prova.

**Limite dichiarato**: il verdetto vale **per il blocco** — quel test esercita
quel gruppo. Le singole non sono state aperte una per una, e dove servirà
(perché una diventa sospetta) la riga si scriverà da sola.

| blocco (test) | `_private` coperte | prova |
|---|---|---|
| `test_rerank_breaker.py` | **9** — `_fusion_breaker_record`, `_fusion_breaker_tripped_now`, `_rerank_breaker_cold_overrun`, `_rerank_breaker_cooldown_s`, `_rerank_breaker_overruns_in_window`, `_rerank_breaker_record`, `_rerank_breaker_reset`, `_rerank_breaker_tripped`, `_rerank_breaker_window_s` | `17 passed, 1 warning in 35.92s` EXIT=0 |
| `test_eval_records_read_path_regime.py` | 4 — `_rerank_breaker_n`, `_rerank_breaker_overrun`, `_rerank_inflight_acquire`, `_rerank_inflight_release` | `17 passed in 7.90s` EXIT=0 |
| `test_rerank_auto_default.py` | 3 — `_query_word_count`, `_rerank_auto_max_words`, `_rerank_mode` | `10 passed, 2 warnings in 11.34s` EXIT=0 |
| `test_read_path_never_cold_loads.py` | 3 — `_fusion_breaker_n`, `_fusion_breaker_tripped`, `_fusion_breaker_window` | `7 passed, 1 warning in 14.10s` EXIT=0 |
| `test_topic_penalty_wire.py` | 2 — `_apply_topic_penalty_to_sims`, `_topic_penalty_strength` | `5 passed in 8.04s` EXIT=0 |
| `test_crash_injection_g3.py` | 2 — `_journal_path_for`, `_replay_pending_facts` | `3 passed in 11.18s` EXIT=0 |

**23 `_private` coperte da sei esecuzioni.** Verdetto per tutti i blocchi:
**FUNZIONA COME PROMESSO**, limitato a ciò che quei test asseriscono.

### ⚠️ Un dato che serve a chi cura T38

`test_rerank_breaker.py` è il file che stamattina dava **rosso in CI su
windows** (`test_observing_the_breaker_does_not_rearm_it`, 1 failed su 12.821).
Qui, in locale, sulla stessa base `7b9e8ca1`: **17 passed, EXIT=0**. Il rosso
non è del codice mappato in queste nove righe — è dell'ambiente o del tempo, che
è esattamente l'ipotesi su cui T38 sta lavorando (orologio finto al posto di
`sleep(0.06)` su un cooldown di 0.05). Lo scrivo perché un verde locale non è un
verde in CI, e la differenza qui è il reperto.

### Le 48 che nessun test nomina

Restano **48 `_private` che nessun test nomina**. Non sono codice morto — la
lezione dei tre righelli vale ancora, e i chiamanti **interni** sono già contati
nell'inventario. Sono **NON MISURATO**, e l'elenco sta in
`scratchpad/raccolta_semantic.md`: fra queste `_migrate_v0_to_v1`,
`_migrate_v1_to_v2` (le migrazioni di schema, che nel mio ruolo pesano più delle
altre) e `_rango_di_fiducia`, che è la funzione dietro `_STATUS_RANK` — cioè
dietro la domanda di Galileo sul terzo stato.


## Le migrazioni di schema — il pezzo del mio ruolo, e sta in piedi

`_migrate_v0_to_v1` (1089) e `_migrate_v1_to_v2` (1097) erano nell'elenco delle
48 «che nessun test nomina». Non è codice morto e **non è nemmeno non misurato**:
sono registrate come **callback**, la stessa forma della riga 7 —

```python
# semantic.py:2648-2653
from .migrations import ensure_schema_version
ensure_schema_version(
    …
    (1, _migrate_v0_to_v1),
    (2, _migrate_v1_to_v2),
```

e la porta `ensure_schema_version` ha **quattro** file di test dedicati, che ho
eseguito:

| test | esito |
|---|---|
| `test_migrations.py` | `12 passed in 8.46s` EXIT=0 |
| `test_due_processi_non_rieseguono_la_migrazione.py` | `5 passed in 9.72s` EXIT=0 |
| `test_la_migrazione_non_committa_il_lavoro_altrui.py` | `4 passed in 9.57s` EXIT=0 |
| `test_migration_v14_upgrade_path.py` | `5 passed in 9.32s` EXIT=0 |

E il percorso vero — uno store a schema **vecchio** aperto da un binario nuovo —
è costruito davvero: `test_continuity.py:534` crea la tabella `_schema_version`
e la stampa a 14, «exactly the live corpus»; `test_dg_cabling.py:199` la porta a
2 per gli episodi.

⇒ **FUNZIONA COME PROMESSO** per entrambe. I nomi dei tre test dicono da soli
quali sono i due modi in cui una migrazione fa danno — due processi che la
rieseguono, e una migrazione che committa il lavoro di un altro — e sono presi
tutti e due.

📌 **Terza volta oggi che sospetto un buco e trovo il presidio** (dopo
«the old row stays» e i «4 test» dell'AUDIT-LEDGER). Lo annoto come dato sulla
mappa, non su di me: in questo file **la copertura è migliore di quanto sembri
da un grep**, e il metodo che la fa sembrare peggiore è sempre lo stesso — il
nome cercato con la parentesi, o cercato dove la funzione non è registrata ma
passata.


## 🔴 `_rango_di_fiducia` (599) — due politiche opposte per lo stato ignoto

La funzione che Galileo deve guardare prima di dare un rango a `review`. Non è
codice morto e non è senza chiamanti: è usata a `semantic.py:6064` e `:6080`, ed
è **importata da un altro modulo** (`contradiction.py:536`,
`from .semantic import _rango_di_fiducia`) — una privata che attraversa il
confine del file.

**Il suo docstring porta già i numeri, misurati sullo store vero il 2026-08-07:**

> la tabella conosce **7** stati, nello store ce ne sono **12**, e i fatti vivi
> con uno stato che la tabella non conosce sono **2540 su 6982** — il 36%, di
> cui `user_manual` da solo 2493. […] Contato sulle coppie non risolte con
> entrambi i fatti vivi: **257** in cui il perdente sarebbe il lato a stato
> ignoto (227 battuti da `model_claim`, 30 da `provisional`).
> 🔑 «`.get(..., 0)` traduce "non lo so" in "vale poco". Sono cose diverse, e
> solo la seconda autorizza un ritiro.»

Per questo torna `None` e non `0`, e chi la chiama **salta la decisione**:

```python
# semantic.py:6061-6067
# RANGO IGNOTO = NON DECIDO (vedi `_rango_di_fiducia`). Se non conosco
# il rango di CHI VINCE non so nemmeno che sia piu' forte …
new_rank = _rango_di_fiducia(new_fact.status)
if new_rank is None:
    result["skipped"] = [oid for oid in contradicting_ids if oid]
    return result
```

### Ma l'altra superficie decide lo stesso

```
semantic.py          _rango_di_fiducia(...)         →  None = NON DECIDO
anti_confab_gate.py  _STATUS_RANK.get(..., 2)  ×4   →  ignoto = model_claim
                     (righe 746, 791, 2257, 2406)
anti_confab_gate.py  usa _rango_di_fiducia:  0 volte
```

⇒ **La stessa domanda — «quanto vale uno stato che non conosco?» — ha due
risposte opposte in due file.** Dove la cura è stata fatta, «non lo so» sospende
il ritiro; dove non è stata fatta, «non lo so» vale `model_claim`, cioè un fatto
pulito, e la supersessione procede.

Non apro un ticket e non curo: **è la mappa che lo dice, ed è il suo mestiere.**
Il verdetto della riga è **FUNZIONA COME PROMESSO** per `_rango_di_fiducia` —
fa esattamente ciò che il docstring dichiara — e il reperto sta nel fatto che la
sua lezione non ha attraversato il confine del file.

📌 **Per il design del terzo stato**: aggiungere `review` senza toccare quei
quattro `.get(..., 2)` significa che, in quei punti, uno stato che la tabella non
conoscesse varrebbe `model_claim`. È la stessa cosa che avevo scritto nella
risposta di dati del par. 5, ma ora ha dietro i 2540 fatti del docstring, che
allora non avevo.

| # | funzione | chiamata da | test | verdetto | prova |
|---|---|---|---|---|---|
| 50 | `_rango_di_fiducia` (599) | `semantic.py:6064` e `:6080`; **importata** da `contradiction.py:536` | nessuno la nomina; la esercita `tests/test_auto_supersede_on_contradiction_scan68.py` per via del chiamante | **FUNZIONA COME PROMESSO** — vedi il reperto sopra | `pytest -q tests/test_auto_supersede_on_contradiction_scan68.py` → `3 passed, 1 warning in 9.0s` EXIT=0 |
| 51 | `_validate_min_status` (630) | `semantic.py:4069` (recall) e `:5254` (recall_hybrid) — **due** vie di lettura | `tests/test_fusion_provenance_filter_r3.py` · `tests/test_i_canali_di_scrittura_sono_allineati.py` (passano `min_status`, cioè il parametro che questa valida) | **FUNZIONA COME PROMESSO**, limitato | `2 passed, 2 warnings in 9.x` EXIT=0 · `3 passed in 8.34s` EXIT=0 |
| 52 | `_row_passes_status_filter` (639) | `semantic.py:4492`, dentro il filtro di riga | gli stessi due: sono le celle che esercitano il filtro per stato | **FUNZIONA COME PROMESSO**, limitato | stessa esecuzione della riga 51 |
| 53 | `_fact_from_dict` (257) | `semantic.py:402`, nel replay del journal | `tests/test_crash_injection_g3.py` (per via del replay) | **FUNZIONA COME PROMESSO**, limitato | `3 passed in 11.18s` EXIT=0 |
| 54 | `_journal_append` (238) | `semantic.py:472` e `:515` — la scrittura differita | `tests/test_crash_injection_g3.py` · `tests/test_deferred_write_journal.py` | **FUNZIONA COME PROMESSO**, limitato | `3 passed in 11.18s` EXIT=0 |
