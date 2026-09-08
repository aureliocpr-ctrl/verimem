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

**24 / 155 funzioni mappate, tutte con un comando eseguito nella casella prova
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
