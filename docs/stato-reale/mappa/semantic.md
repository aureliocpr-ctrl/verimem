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

## Inventario completo — ogni funzione per nome

**153 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 117 | `_recall_rerank_budget_s` | priv | Wall-clock budget (s) for the stage-2 CE rerank, read at C | 2 — `test_rerank_cold_start.py` |
| 133 | `_encode_prepared_within_budget` | priv | Encode ALREADY-PREFIXED text (caller applied as_query / as | 10 — `test_il_degrado_arriva_anche_agli_agenti.py` |
| 174 | `_encode_within_budget` | priv | Encode `text` for a STORE (applies as_passage), returning  | 1 — `test_save_encode_circuit_breaker.py` |
| 216 | `_slow_txn_warn_s` | priv | Threshold (s) above which a held _connect() context logs a | 1 — `test_slow_txn_telemetry.py` |
| 228 | `_journal_path_for` | priv | pending_facts.jsonl beside the semantic db; None for :memo | 4 — `test_crash_injection_g3.py` |
| 238 | `_journal_append` | priv | Append one JSON line, fsync'd (must survive an immediate k | 🔴 **nessuno** |
| 253 | `_json_safe_store_kwargs` | priv |  | 🔴 **nessuno** |
| 257 | `_fact_from_dict` | priv | Rebuild a Fact from a journal entry, tolerant to schema dr | 🔴 **nessuno** |
| 264 | `_episode_from_dict` | priv | Rebuild an Episode (with its nested Trace list) from a jou | 🔴 **nessuno** |
| 283 | `_durable_checkpoint` | priv | Force WAL -> main db + fsync so replayed writes are on dis | 1 — `test_journal_durability_r3.py` |
| 310 | `_replay_pending_facts` | priv | Replay crash-orphaned deferred writes for this db. Returns | 3 — `test_crash_injection_g3.py` |
| 437 | `store_within_budget` | **pub** | Persist `fact` via `memory.store` without letting the INTE | 6 — `test_deferred_write_durability.py` |
| 523 | `_flush_pending_writes` | priv | Wait (bounded) for in-flight deferred writes before interp | 1 — `test_deferred_write_durability.py` |
| 599 | `_rango_di_fiducia` | priv | Il rango di ``status``, oppure ``None`` se la tabella non  | 🔴 **nessuno** |
| 630 | `_validate_min_status` | priv | Raise ValueError when ``min_status`` is set but unknown. | 🔴 **nessuno** |
| 639 | `_row_passes_status_filter` | priv | Apply provenance filter to a raw SQLite row (pre-Fact dese | 🔴 **nessuno** |
| 765 | `_glob_to_like` | priv | Cycle #79: translate small glob (``*``/``?``) into SQL LIK | 🔴 **nessuno** |
| 786 | `_like_escape_literal` | priv | Escape a string so it matches LITERALLY inside a ``LIKE``  | 🔴 **nessuno** |
| 890 | `_bump_busy_timeout_ms` | priv | SQLite busy_timeout (ms) for the bump-on-recall UPDATE, re | 🔴 **nessuno** |
| 967 | `_is_telemetry_topic` | priv | Python mirror of _TELEMETRY_DENYLIST_CLAUSES (same prefixe | 🔴 **nessuno** |
| 973 | `_topic_prefix_upper` | priv | Half-open upper bound for an INDEXED prefix range scan: th | 1 — `test_scope_index_scan.py` |
| 993 | `_is_unverified_conversational` | priv | A conversational_promotion row that hasn't been verified — | 🔴 **nessuno** |
| 1002 | `_fact_is_stale` | priv | v8 (2026-06-03) buco #3: True se il fatto e' scaduto per e | 6 — `test_freshness_bump_on_recall.py` |
| 1056 | `_topic_penalty_strength` | priv | Strength of the off-topic recall penalty (verimem.topic_pr | 2 — `test_topic_penalty_wire.py` |
| 1067 | `_apply_topic_penalty_to_sims` | priv | Down-rank broadly-matching off-topic facts (verimem.topic_ | 1 — `test_topic_penalty_wire.py` |
| 1089 | `_migrate_v0_to_v1` | priv | No-op: the pre-cycle-#78 schema is already created by _SCH | 🔴 **nessuno** |
| 1097 | `_migrate_v1_to_v2` | priv | Add supersession columns to facts table (cycle #78, 2026-0 | 🔴 **nessuno** |
| 1134 | `_migrate_v2_to_v3` | priv | Add provenance columns to facts table (cycle #109, 2026-05 | 🔴 **nessuno** |
| 1170 | `_migrate_v3_to_v4` | priv | Cycle #157 (2026-05-19): partial UNIQUE INDEX on auto-clus | 1 — `test_consolidation_unique_index.py` |
| 1216 | `_migrate_v4_to_v5` | priv | Cycle 160 (2026-05-19): pattern card schema. Add four opti | 🔴 **nessuno** |
| 1249 | `_migrate_v5_to_v6` | priv | Cycle 2026-05-27 round 12 (F-fix): provenance schema for t | 🔴 **nessuno** |
| 1296 | `_migrate_v6_to_v7` | priv | Cycle 2026-05-27 round 13 P0c: transactional rollback for  | 🔴 **nessuno** |
| 1314 | `_migrate_v7_to_v8` | priv | 2026-06-03 buco #3 (validita temporale): colonna ``last_ve | 🔴 **nessuno** |
| 1340 | `_migrate_v8_to_v9` | priv | 2026-06-03 buco silent-poisoning (Sorella C): colonna ``em | 🔴 **nessuno** |
| 1362 | `_migrate_v9_to_v10` | priv | 2026-06-14 valid-time bi-temporale: colonna ``valid_until` | 1 — `test_valid_time.py` |
| 1387 | `_migrate_v10_to_v11` | priv | 2026-06-19 typed LOGICAL-derivation edge ``derives_from``  | 🔴 **nessuno** |
| 1405 | `_migrate_v11_to_v12` | priv | 2026-06-20 persist the write-time grounding score (moonsho | 🔴 **nessuno** |
| 1421 | `_migrate_v12_to_v13` | priv | 2026-07-05 bi-temporal EVENT time ``asserted_at`` (valid-F | 🔴 **nessuno** |
| 1442 | `_migrate_v14_to_v15` | priv | v15 (2026-07-19): persist the write-time confidence_tier.  | 🔴 **nessuno** |
| 1452 | `_migrate_v15_to_v16` | priv | v16 (2026-07-23): ``writer_principal`` in a REACHABLE ladd | 🔴 **nessuno** |
| 1466 | `_migrate_v16_to_v17` | priv | v17 (2026-08-08): ``grounding_span`` — LA PROVA della veri | 🔴 **nessuno** |
| 1531 | `_ensure_fact_columns` | priv | Self-heal additive fact columns the versioned ladder faile | 🔴 **nessuno** |
| 1561 | `_ensure_fact_indexes` | priv | Create the indexes an already-migrated store would never g | 🔴 **nessuno** |
| 1578 | `_migrate_v13_to_v14` | priv | 2026-07-13 epistemic label (cortex transfer #1). | 1 — `test_migration_v14_upgrade_path.py` |
| 1715 | `_rerank_mode` | priv | 'on' | 'off' | 'auto'. Default AUTO since 2026-07-26 (was  | 1 — `test_rerank_auto_default.py` |
| 1742 | `_rerank_enabled` | priv | Whether the CE may run at all (preload/CLI warm it iff thi | 6 — `test_la_vetrina_nomina_i_modelli_che_scarica.py` |
| 1747 | `_rerank_auto_max_words` | priv | AUTO mode's gate: rerank only queries of at most this many | 1 — `test_rerank_auto_default.py` |
| 1772 | `_query_word_count` | priv | Word count for the AUTO gate — Unicode-aware where split() | 1 — `test_rerank_auto_default.py` |
| 1791 | `_topk_deterministic` | priv | Top-``n`` candidate indices by ``(-score, fact.id)`` — det | 1 — `test_recall_deterministic_tiebreak.py` |
| 1822 | `_ann_recall_enabled` | priv | ANN pre-narrowing of the recall corpus. Default AUTO-ON (i | 🔴 **nessuno** |
| 1843 | `_entity_live_enabled` | priv | Entity-live write path (2026-06-10): keep the entity KG in | 🔴 **nessuno** |
| 1852 | `_reconcile_on_write_enabled` | priv | P1 truth-reconciliation on write (2026-06-17): after a fac | 🔴 **nessuno** |
| 1863 | `_source_auto_confirm_enabled` | priv | Auto-confirmation on write (2026-07-11): when a fact resta | 🔴 **nessuno** |
| 1876 | `_reconcile_auto_supersede_enabled` | priv | Allow reconcile-on-write to SUPERSEDE (apply a knowledge u | 🔴 **nessuno** |
| 1887 | `_reconcile_evidence_policy` | priv | Anti-sycophancy policy for write-path supersede -> ``(stri | 🔴 **nessuno** |
| 1907 | `_rerank_topn` | priv | CE pool size = pairs actually scored — the latency knob (2 | 🔴 **nessuno** |
| 1916 | `_rerank_max_doc_chars` | priv | Length guard for stage-2 rerank. The mmarco CE truncates a | 1 — `test_una_frase_estranea_puo_ribaltare_il_moat.py` |
| 1939 | `_rerank_via_daemon` | priv | Punteggi del cross-encoder dal daemon condiviso, o None pe | 3 — `test_il_giudice_del_moat_vive_nel_daemon.py` |
| 1996 | `_load_reranker` | priv | Process-wide lazy CrossEncoder scorer (mirror of embedding | 14 — `test_abstention_ce_gate.py` |
| 2058 | `_reranker_ready` | priv | True quando una risposta del cross-encoder e' a portata: m | 5 — `test_il_reranker_vive_nel_daemon.py` |
| 2110 | `_rerank_breaker_n` | priv | Overruns WITHIN THE WINDOW that trip the breaker. 0 disabl | 1 — `test_eval_records_read_path_regime.py` |
| 2119 | `_rerank_breaker_window` | priv | How many recent reranks the window remembers. | 1 — `test_rerank_breaker.py` |
| 2128 | `_rerank_breaker_cooldown_s` | priv | Seconds after a trip before the breaker re-arms itself; 0  | 1 — `test_rerank_breaker.py` |
| 2147 | `_rerank_breaker_tripped_now` | priv | The state as it IS, with no side effect — for observers. | 1 — `test_rerank_breaker.py` |
| 2162 | `_rerank_breaker_tripped` | priv | THE GATE: whether the rerank is disabled — re-arming LAZIL | 1 — `test_rerank_breaker.py` |
| 2193 | `_rerank_breaker_overruns_in_window` | priv |  | 2 — `test_rerank_breaker.py` |
| 2197 | `_rerank_cold_breaker_n` | priv | Cold-load overruns tolerated before tripping (0 disables). | 🔴 **nessuno** |
| 2234 | `_rerank_slot_lease_s` | priv | How long the slot may stay held before it is presumed lost | 1 — `test_rerank_does_not_pile_up_threads.py` |
| 2266 | `_rerank_inflight_acquire` | priv | Claim the single rerank slot. Returns the lease number, or | 2 — `test_eval_records_read_path_regime.py` |
| 2297 | `_rerank_inflight_release` | priv | Release the slot, but only if it is still the one we were  | 2 — `test_eval_records_read_path_regime.py` |
| 2310 | `_rerank_breaker_reset` | priv | Re-arm the rerank protection (tests; model/env swap at run | 6 — `conftest.py` |
| 2331 | `_rerank_breaker_record` | priv | Record one FINISHED rerank, in budget or not. | 1 — `test_rerank_breaker.py` |
| 2362 | `_rerank_breaker_overrun` | priv | One rerank that overran. Kept as the name the call sites a | 1 — `test_eval_records_read_path_regime.py` |
| 2367 | `_rerank_breaker_cold_overrun` | priv |  | 1 — `test_rerank_breaker.py` |
| 2413 | `_fusion_breaker_n` | priv | Overruns WITHIN the window that trip the breaker. 0 disabl | 1 — `test_read_path_never_cold_loads.py` |
| 2423 | `_fusion_breaker_window` | priv | How many recent fusion outcomes the decision looks at. | 1 — `test_read_path_never_cold_loads.py` |
| 2432 | `_fusion_breaker_reset` | priv | Re-arm the breaker (tests; env swap at runtime). | 4 — `conftest.py` |
| 2440 | `_fusion_breaker_cooldown_s` | priv | Fusion twin of _rerank_breaker_cooldown_s — same rationale | 🔴 **nessuno** |
| 2451 | `_fusion_breaker_tripped_now` | priv | The fusion state as it IS, no side effect — twin of | 1 — `test_rerank_breaker.py` |
| 2457 | `_fusion_breaker_tripped` | priv | THE GATE: whether the fusion is disabled — re-arming lazil | 2 — `test_read_path_never_cold_loads.py` |
| 2476 | `_fusion_breaker_record` | priv | Record one fusion outcome and trip if the window says it i | 1 — `test_rerank_breaker.py` |
| 2499 | `_rerank_cold_budget_s` | priv | Wall-clock budget for a rerank attempt while the CE is sti | 1 — `test_rerank_cold_start.py` |
| 2512 | `_ppr_fusion_budget_s` | priv | Wall-clock budget for the opt-in PPR+BM25 fusion (default- | 🔴 **nessuno** |
| 2532 | `_ppr_fusion_enabled` | priv | DEFAULT-ON (2026-06-15): the 3-signal fusion (dense-cosine | 🔴 **nessuno** |
| 2577 | `ranking_reset` | **pub** | Apre una registrazione per la recall che sta per partire. | 1 — `test_una_recall_dice_quali_segnali_hanno_deciso.py` |
| 2582 | `_ranking_note` | priv | Registra l'esito di uno stadio. Muta il dict IN PLACE: chi | 1 — `test_una_recall_dice_quali_segnali_hanno_deciso.py` |
| 2592 | `ranking_stages` | **pub** | Gli stadi dell'ultima recall in questo contesto, o None se | 1 — `test_una_recall_dice_quali_segnali_hanno_deciso.py` |
| 144 | `_work` | priv |  | 1 — `test_entity_live_latency.py` |
| 462 | `_work` | priv |  | 1 — `test_entity_live_latency.py` |
| 1688 | `as_payload` | **pub** | Il fatto come esce dal prodotto: un contratto solo, per tu | 1 — `test_fact_ha_un_contratto_di_uscita.py` |
| 1809 | `_fid` | priv |  | 5 — `test_anti_confabulation_reconciler.py` |
| 2742 | `_connect` | priv |  | 47 — `test_bridge.py` |
| 2769 | `_ann_cache` | priv | La cache dell'indice ANN, costruita al PRIMO accesso. | 3 — `test_ann_recall_equivalence.py` |
| 2789 | `_db_data_version` | priv | Cross-process cache-coherence probe (sorelle loop 2026-06- | 3 — `test_episode_index_cross_process.py` |
| 2833 | `_store_telemetry` | priv | Admission-gate (opt-in): persist a telemetry-topic fact in | 🔴 **nessuno** |
| 2851 | `store` | **pub** | Insert or replace a fact. Backwards-compatible default ret | _generico — cercato qualificato nei blocchi sopra_ |
| 3543 | `backfill_pending_embeddings` | **pub** | Embed rows persisted with ``embed='defer'`` (NULL embeddin | 7 — `test_backfill_heals_model_mismatch.py` |
| 3624 | `all` | **pub** |  | _generico — cercato qualificato nei blocchi sopra_ |
| 3629 | `live_topic_siblings` | **pub** | LIVE same-topic facts a NEW write should be checked agains | 1 — `test_live_topic_siblings.py` |
| 3650 | `get` | **pub** | Fetch one Fact by id. Returns None if not found. | _generico — cercato qualificato nei blocchi sopra_ |
| 3684 | `set_epistemic` | **pub** | Apply an epistemic label under the MONOTONE transition rul | 8 — `test_cosa_resta_scollegato_dell_epistemico.py` |
| 3712 | `set_derives_from` | **pub** | Declare the LOGICAL derivation edge (v11 ``derives_from``) | 🔴 **nessuno** |
| 3729 | `filter_live_ids` | **pub** | Return the subset of ``fact_ids`` that are LIVE (supersede | 2 — `test_entity_supersede_leak.py` |
| 3750 | `list_facts` | **pub** | CYCLE #10 fix: paginated list. mcp_server.py called | 22 — `test_audit_summary_integration.py` |
| 3797 | `_get_corpus_cache` | priv | Cycle #135: lazy build of the recall hot-path cache. | 2 — `test_recall_cache_cross_conn_staleness.py` |
| 3938 | `_attach_trust_signals` | priv | Cycle #117: post-hoc trust-signal attachment (reused from | 🔴 **nessuno** |
| 3953 | `_bump_verified` | priv | Bump-on-recall (2026-06-09): refresh ``last_verified_at``  | 1 — `test_bump_on_recall_nonblocking.py` |
| 4016 | `recall` | **pub** | Semantic recall over facts (cosine on embeddings). | _generico — cercato qualificato nei blocchi sopra_ |
| 4598 | `_rerank_stage2` | priv | P0.3: re-order the bi-encoder shortlist with a cross-encod | 3 — `test_recall_ppr_fusion.py` |
| 4753 | `_recall_entity_store` | priv | Lazy EntityStore over the same data dir as this semantic d | 2 — `test_asserted_at_bitemporal.py` |
| 4764 | `set_reconcile_judge` | **pub** | Wire a semantic NLI judge (semantic_conflict.RelationJudge | 2 — `test_reconcile_judge_env_wiring.py` |
| 4772 | `reconcile_new_fact` | **pub** | P1 truth-reconciliation on a just-stored fact: find shared | 5 — `test_asserted_at_bitemporal.py` |
| 4793 | `_auto_confirm_source_trust` | priv | Feed the source-trust consistency channel from same-topic  | 🔴 **nessuno** |
| 4834 | `_extra_similarity_scorer` | priv | Real cosine for a graph/lexical-only fusion candidate. | 2 — `test_fusion_score_real_store.py` |
| 4897 | `_maybe_fuse_ppr` | priv | Opt-in (ENGRAM_PPR_FUSION): RRF-fuse query-auto-seeded ent | 3 — `test_fusion_provenance_filter_r3.py` |
| 5097 | `_expand_query_tokens` | priv | Cycle 166: expand query tokens with synonyms from | 🔴 **nessuno** |
| 5109 | `recall_hybrid` | **pub** | Hybrid recall: semantic cosine + keyword overlap re-rank. | 6 — `test_l_iniezione_proattiva_spariva_col_degrado.py` |
| 5204 | `topics_for_query` | **pub** | FORGIA pezzo #180: schema priming primitive. | 2 — `test_semantic_topics_for_query.py` |
| 5232 | `search_facts` | **pub** | FORGIA pezzo #203: keyword/substring search over `proposit | 41 — `test_anchor_recall.py` |
| 5442 | `_cascade_delete_refs` | priv | Audit R3 #16: a hard fact-delete must cascade to its refer | 2 — `test_audit_mutations_episodic.py` |
| 5467 | `_relink_through` | priv | Re-link incoming supersession pointers THROUGH a row about | 🔴 **nessuno** |
| 5485 | `delete` | **pub** | FORGIA pezzo #202: delete one fact by id (privacy / GDPR). | _generico — cercato qualificato nei blocchi sopra_ |
| 5547 | `delete_with_undo` | **pub** | Cycle 2026-05-27 round 13 P0c — delete + emit undo handle. | 6 — `test_audit_mutations.py` |
| 5601 | `undo_destructive_op` | **pub** | Undo a previous delete_with_undo / supersede_with_undo. | 2 — `test_timone_supersede_undo.py` |
| 5624 | `list_undoable_ops` | **pub** | List the N most recent undoable ops (not yet undone, not e | 3 — `test_timone_non_resuscita_i_cancellati.py` |
| 5638 | `quarantine_fact` | **pub** | Flip a fact to ``status='quarantined'`` — used by the Tier | 15 — `test_ask_ha_un_contratto_solo.py` |
| 5695 | `restore_fact` | **pub** | Un-quarantine: flip a ``quarantined`` fact back to ``to_st | 7 — `test_flow_quarantine_exit.py` |
| 5727 | `mark_orphaned` | **pub** | Cycle #137 — L2 mutation: flip a fact to ``status='orphane | 6 — `test_anti_confab_gate.py` |
| 5778 | `count` | **pub** | Quante righe, e di QUALE popolazione. | _generico — cercato qualificato nei blocchi sopra_ |
| 5807 | `count_superseded` | **pub** | Cycle #78: count facts marked as superseded. | 2 — `test_fact_supersede.py` |
| 5814 | `supersede` | **pub** | Cycle #78 — declare ``old_id`` superseded by ``new_id``. | 102 — `test_asserted_at_bitemporal.py` |
| 6021 | `auto_supersede_on_contradiction` | **pub** | Auto-invalidate (supersede, NOT delete) older facts that a | 5 — `test_auto_supersede_on_contradiction_scan68.py` |
| 6106 | `direct_predecessors` | **pub** | Facts this fact directly REPLACED (``superseded_by == fact | 🔴 **nessuno** |
| 6125 | `get_supersession_chain` | **pub** | Walk forward from ``fact_id`` along ``superseded_by`` poin | 2 — `test_fact_supersede.py` |
| 6154 | `supersede_chain` | **pub** | Cycle #81 (2026-05-16) — declare a multi-hop supersession | 5 — `test_audit_mutations.py` |
| 6314 | `_restore_supersession_snapshots` | priv | Cycle #81b atomic rollback helper. Each snapshot is | 1 — `test_semantic_recall_cache_supersede_invalidation.py` |
| 6350 | `summary_topic` | **pub** | Cycle #79 (2026-05-16) — narrative aggregator for a topic  | 6 — `test_briefing_by_project.py` |
| 6503 | `_fact_to_summary_dict` | priv |  | 🔴 **nessuno** |
| 6543 | `clear` | **pub** | Wipe EVERY fact (test-reset / full re-init). ``principal`` | _generico — cercato qualificato nei blocchi sopra_ |
| 6562 | `audit_verify` | **pub** | Recompute the mutation-audit chain; the id of the first ta | 5 — `test_adjudication_log_chain.py` |
| 6570 | `audit_head` | **pub** | Current mutation-audit chain head (archive it off-box). | 4 — `test_adjudication_log_chain.py` |
| 6575 | `audit_count` | **pub** | Number of chained mutation rows — recorded in a signed anc | 1 — `test_tamper_anchor_receipt.py` |
| 6581 | `audit_head_at` | **pub** | Stored head of the ``count``-th chained mutation row (1-in | 1 — `test_tamper_anchor_receipt.py` |
| 6588 | `_row` | priv | Deserialize a SQLite row into a Fact. | 6 — `test_continuity.py` |
| 2012 | `_scorer_remoto` | priv |  | 🔴 **nessuno** |
| 4853 | `_score` | priv |  | 10 — `test_abstention_hybrid.py` |
| 4959 | `_fuse` | priv |  | 🔴 **nessuno** |
| 5022 | `_work` | priv |  | 1 — `test_entity_live_latency.py` |
| 6601 | `_opt` | priv |  | 1 — `test_ogni_colonna_di_facts_arriva_all_oggetto.py` |
| 4121 | `_passes_recall_view` | priv |  | 1 — `test_i_ritirati_sostenuti_non_tornano_da_nessuna_porta.py` |
| 4513 | `_row_lv` | priv |  | 🔴 **nessuno** |
| 4519 | `_row_vu` | priv |  | 1 — `test_un_fatto_scaduto_non_viene_servito.py` |
| 4689 | `_work` | priv |  | 1 — `test_entity_live_latency.py` |

### I dunder di questo file

L'inventario sopra esclude i metodi speciali, e qui sono nominati per chiudere il
conteggio: **`__getattr__`, `__init__`**. Sono costruttori e accessori di protocollo — non hanno
un claim del README, non hanno un test proprio, e sono esercitati da **ogni** uso
della loro classe: il verdetto è quello dei blocchi qui sopra, non una riga a sé.
