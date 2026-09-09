# `verimem/local_grounding.py` — 970 righe, 33 funzioni

**Il file del giudice**: qui si decide *se* un fatto viene giudicato, *chi* lo giudica e
*quanto costa* chiederlo. Mappato su `7b9e8ca1`. 18 funzioni pubbliche, 15 private.

---

## 1. Le QUATTRO vie al giudizio — e la quarta è arrivata dopo

Il gate chiede «c'è un giudice?» con **tre criteri**; il docstring di
`daemon_del_giudice_annunciato` (riga 561) racconta che ne mancava uno:

| via | chi la rappresenta | costa |
|---|---|---|
| 1. llm iniettato | il chiamante lo passa | — |
| 2. backend `local` | `local_ce_available` (riga 600) | un `os.path` |
| 3. modello CE su disco | `_holds_a_model` + `holds_the_weights` (55, 68) | un `os.path` |
| 4. **daemon annunciato** | `daemon_del_giudice_annunciato` (561) | una lettura di file |

> Misurato il 2026-08-30 (nel docstring, non da me):
> `_have_judge` **False** mentre `try_local_score` nello stesso processo otteneva **0.5561**
> dal daemon — cioè il gate diceva «nessun giudice» e uno c'era.

🔑 **La cura non è stata togliere il predicato ma aggiungergli la via mancante**, e la
ragione è un numero: tentare il giudizio senza alcun giudice costa **15.453 ms**, mentre col
predicato la scrittura ne costa **351**. Un predicato che protegge quindici secondi si tiene.

📌 **Vincolo che ogni via deve rispettare**: essere *economica*. Nessuna apre connessioni,
nessuna carica modelli. È il vincolo che il percorso della richiesta **viola** — vedi §3.

---

## 2. `judge_state()` (riga 515) — una parola per tutte le superfici

    ready · failed · delegated · absent · warming

L'ultima riga della funzione è:

    return "warming" if _delegate_only() else "ready"

⚠️ **In delegate-only lo stato è `warming` per costruzione**, anche quando nessuno sta
scaldando e nessuno scalderà mai (il server delegate-only **non carica** in processo per
progetto). ⇒ una ricevuta può dire «il giudice sta caricando» dove la verità è «qui non
caricherà mai, e senza daemon non arriverà nessun verdetto». **Questo è T26b, già assegnato
a @ws4** — lo mappo, non lo curo.

---

## 3. 🔴 Il percorso della richiesta paga 35,4 s che nessuna delle quattro vie prevede

Misurato da me stasera su questo albero, tre bracci a una variabile per volta:

    A  daemon ✔  tokenizzatore ✔   42.89 s   (98.62383270263672, None)
    B  daemon ✘  tokenizzatore ✔   35.37 s   None
    C  daemon ✘  tokenizzatore ✘    0.00 s   None
    ⇒ daemon 7,5 s · tokenizzatore 35,4 s

**La catena, riga per riga:**

    try_local_score (890) ──► judge.coppia(source, fact)        (375)
                                └─► _entro_la_finestra(span)    (389)
                                      └─► _tokenizzatore()      (427)
                                            └─► from_pretrained  ~35 s

E il perché sta nel docstring di `_entro_la_finestra`: *«Riduce lo span finché entra nella
finestra del CE, **contando TOKEN**»*. Contare token richiede il tokenizer; il tokenizer
richiede `from_pretrained`; quello costa 35 s la prima volta — **sul thread della
richiesta**, e **prima** di chiedere al daemon, perché `coppia()` è valutata come
**argomento** di `_gate_via_daemon`.

⚠️ **Il docstring di `coppia` dice l'opposto**: *«La selezione dello span è puro testo e
**costa poco**, quindi resta di qua in entrambi i casi»*. Puro testo lo è; costa poco **no**.
⇒ La promessa di `delegate-only` — *«NEVER cold-load the model here»* — vale per il
**modello** e non per il **tokenizer**, e nessuno l'aveva scritto.

**È T40, mio, cura nella finestra di domani.** La direzione: in delegate-only mandare al
daemon lo span **senza** troncarlo col tokenizer locale, lasciando il conteggio a chi il
modello ce l'ha già.

---

## 4. Il degrado, dove è scritto bene

`_gate_via_daemon` (816): *«Punteggi del giudice del moat dal daemon condiviso, **o None per
degradare**»*. `warm_local_judge_async` (872): warm fuori dal thread di richiesta, **una
volta per processo**, e *«load failure is cached»* — un fallimento non viene ritentato a ogni
chiamata. Entrambe fanno ciò che dicono.

📌 `make_finetuned_scorer` (181) tiene l'import di `torch`/`transformers` **sotto
`lock_import()` e solo l'import**: il caricamento dei pesi (19,1 s) resta fuori. È la regola
di `_import_lock`, e qui è rispettata.

---

## 5. Le 33 funzioni

**Pubbliche (18)**: `holds_the_weights` · `annuncia_download_del_giudice` ·
`make_finetuned_scorer` · `get_local_judge` · `set_local_judge` · `reset_local_judge` ·
`get_local_threshold` · `judge_state` · `daemon_del_giudice_annunciato` ·
`local_ce_available` · `ensure_gate_model` · `warm_local_judge_async` · `try_local_score` ·
e sulla classe: `scorer` · `config` · `threshold` · `focus_budget` · `coppia` ·
`normalizza` · `score`.

**Private (15)**: `_holds_a_model` · `_resolve_model_dir` · `_download_disattivato` ·
`_download_and_extract_tar` · `_safe_tar_extract` · `_esito_dell_installazione` ·
`_delegate_only` · `_gate_via_daemon` · `__init__` · `_ensure_scorer` ·
`_entro_la_finestra` · `_tokenizzatore` · `_warm`.

📌 `_safe_tar_extract` (707) rifiuta i membri che uscirebbero dalla destinazione: è la
difesa contro il tar-slip sul download del modello da 746 MB. **Non l'ho esercitata** —
esiste un test? Giro 2.

---

## 6. Quello che questa mappa NON dice — dichiarato

- ~~Non ho verificato che `_safe_tar_extract` sia coperta da un test~~ → **VERIFICATO, e
  chiude in positivo**: `tests/test_gate_model_tarslip.py`. La difesa contro il tar-slip sul
  download da 746 MB **è presidiata**, e il presidio si chiama col nome dell'attacco.
- **Non ho misurato le altre tre vie**: solo la quarta (daemon) e il costo del tokenizer.
- **`_resolve_model_dir` e `_esito_dell_installazione`** sono lette solo di nome.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I tre bracci di §3 sono miei, misurati stasera; i
numeri di §1 vengono dal docstring e sono attribuiti lì.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/local_grounding.py` — 34 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/local_grounding.py:55` `_holds_a_model` | funzione: True only when the dir actually HOLDS a model — its mere existence is not | `verimem/anti_confab_gate.py`; `verimem/local_grounding.py` | `tests/test_una_cartella_vuota_del_giudice_e_un_modello_assente.py`; `tests/test_una_cartella_vuota_non_e_un_giudice.py` | NON MISURATO |
| 2 | `verimem/local_grounding.py:68` `holds_the_weights` | funzione: True quando la cartella tiene anche i PESI, non solo i metadati. | `verimem/anti_confab_gate.py`; `verimem/cli.py` (+2) | `tests/test_una_cartella_vuota_del_giudice_e_un_modello_assente.py`; `tests/test_warmup_non_dice_installato_su_mezzo_modello.py` | NON MISURATO |
| 3 | `verimem/local_grounding.py:94` `_resolve_model_dir` | funzione | `verimem/cli.py`; `verimem/doctor.py` (+1) | `tests/test_lo_span_sta_nella_finestra_del_giudice.py`; `tests/test_ws5_giudice_si_procura_da_solo.py` | NON MISURATO |
| 4 | `verimem/local_grounding.py:122` `annuncia_download_del_giudice` | funzione: Dice all'utente che stiamo scaricando 746 MB, PRIMA di farlo. | `verimem/anti_confab_gate.py`; `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 5 | `verimem/local_grounding.py:163` `_download_disattivato` | funzione: True se l'operatore ha chiesto di non toccare la rete. | `verimem/anti_confab_gate.py`; `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 6 | `verimem/local_grounding.py:181` `make_finetuned_scorer` | funzione: Production scorer over the saved binary-head CE: sigmoid(logit)*100 per | `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 7 | `verimem/local_grounding.py:202` `make_finetuned_scorer.scorer` | funzione | `verimem/cross_encoder_rerank.py`; `verimem/encode_service.py` (+4) | `tests/test_cross_encoder_rerank.py`; `tests/test_flow_warmup_dichiarato.py` (+7) | NON MISURATO |
| 8 | `verimem/local_grounding.py:220` `LocalGroundingJudge` | classe: Scores source ⊢ fact in [0, 100] with the local CE. The source is reduced to | `verimem/local_grounding.py` | `tests/test_flow_warmup_dichiarato.py`; `tests/test_lo_span_sta_nella_finestra_del_giudice.py` (+6) | NON MISURATO |
| 9 | `verimem/local_grounding.py:225` `LocalGroundingJudge.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 10 | `verimem/local_grounding.py:239` `LocalGroundingJudge.config` | funzione: gate_config.json from the model dir ({} when absent/corrupt). | `verimem/local_grounding.py`; `verimem/resource_monitor.py` (+2) | `tests/test_admission_gate_default_on.py`; `tests/test_admission_gate_wire.py` (+13) | NON MISURATO |
| 11 | `verimem/local_grounding.py:250` `LocalGroundingJudge.threshold` | funzione | `verimem/adjudication_log.py`; `verimem/anti_confab_gate.py` (+26) | `tests/perf/bench_briefing_proactive_v2.py`; `tests/perf/bench_briefing_v3_robustness.py` (+4) | NON MISURATO |
| 12 | `verimem/local_grounding.py:255` `LocalGroundingJudge.focus_budget` | funzione | `verimem/grounding_gate.py`; `verimem/interactive_judge.py` (+1) | **nessuno** | NON MISURATO |
| 13 | `verimem/local_grounding.py:261` `LocalGroundingJudge._ensure_scorer` | funzione | `verimem/encode_service.py`; `verimem/local_grounding.py` (+1) | `tests/test_ws5_giudice_si_procura_da_solo.py`; `tests/test_ws5_il_download_del_giudice_lo_dice_all_utente.py` | NON MISURATO |
| 14 | `verimem/local_grounding.py:375` `LocalGroundingJudge.coppia` | funzione: La coppia (span, fatto) che il CE giudica. | `verimem/local_grounding.py` | `tests/test_due_fatti_che_si_contraddicono_non_si_confermano.py`; `tests/test_hippo_reason_non_esplode_sulle_skill.py` (+2) | NON MISURATO |
| 15 | `verimem/local_grounding.py:389` `LocalGroundingJudge._entro_la_finestra` | funzione: Riduce lo span finche' entra nella finestra del CE, contando TOKEN. | `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 16 | `verimem/local_grounding.py:427` `LocalGroundingJudge._tokenizzatore` | funzione: Il tokenizzatore del gate, caricato una volta e riusato. None quando | `verimem/local_grounding.py` | `tests/test_l_import_del_giudice_non_tiene_il_lock.py` | NON MISURATO |
| 17 | `verimem/local_grounding.py:463` `LocalGroundingJudge.normalizza` | funzione: Il punteggio in [0, 100], da qualunque esecutore arrivi. | `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 18 | `verimem/local_grounding.py:467` `LocalGroundingJudge.score` | funzione | `verimem/adjudication_log.py`; `verimem/cli.py` (+39) | `tests/test_abstention_hybrid.py`; `tests/test_adjudication_log.py` (+34) | NON MISURATO |
| 19 | `verimem/local_grounding.py:477` `get_local_judge` | funzione: Process-wide lazy singleton (model loads once). | `verimem/anti_confab_gate.py`; `verimem/client.py` (+4) | `tests/test_flow_warmup_dichiarato.py`; `tests/test_il_giudice_dice_se_sta_scaldando.py` (+2) | NON MISURATO |
| 20 | `verimem/local_grounding.py:498` `set_local_judge` | funzione: Inject a judge (tests) — pass None to clear. | `verimem/local_grounding.py` | `tests/test_local_grounding.py`; `tests/test_moat_ce_delegate_only_nonblocking.py` (+1) | NON MISURATO |
| 21 | `verimem/local_grounding.py:504` `reset_local_judge` | funzione | **nessuno** | `tests/test_flow_warmup_dichiarato.py`; `tests/test_il_gate_dice_se_il_giudice_non_si_carica.py` (+5) | NON MISURATO |
| 22 | `verimem/local_grounding.py:510` `get_local_threshold` | funzione: The fine-tune-calibrated admission threshold, if the model ships one. | `verimem/doctor.py`; `verimem/grounding_gate.py` | `tests/test_local_grounding.py` | NON MISURATO |
| 23 | `verimem/local_grounding.py:515` `judge_state` | funzione: Lo stato del giudice locale in UNA parola, per tutte le superfici. | `verimem/anti_confab_gate.py`; `verimem/cli.py` (+2) | `tests/test_il_doctor_dichiara_ENTRAMBE_le_soglie.py`; `tests/test_il_giudice_dice_se_sta_scaldando.py` (+2) | NON MISURATO |
| 24 | `verimem/local_grounding.py:561` `daemon_del_giudice_annunciato` | funzione: True quando un daemon condiviso si e' ANNUNCIATO: la quarta via al giudizio. | `verimem/anti_confab_gate.py` | `tests/test_il_daemon_e_la_quarta_via_al_giudizio.py` | NON MISURATO |
| 25 | `verimem/local_grounding.py:600` `local_ce_available` | funzione: True when the local CE moat judge can score WITHOUT an injected llm — an | `verimem/anti_confab_gate.py`; `verimem/doctor.py` (+1) | `tests/_real_model.py`; `tests/test_adversarial_guarantees.py` (+10) | NON MISURATO |
| 26 | `verimem/local_grounding.py:675` `_download_and_extract_tar` | funzione: Stream ``url`` to a temp file (verifying sha256), then extract the tar.gz | `verimem/local_grounding.py` | `tests/test_gate_model_fetch_and_doctor.py`; `tests/test_una_cartella_vuota_non_e_un_giudice.py` | NON MISURATO |
| 27 | `verimem/local_grounding.py:707` `_safe_tar_extract` | funzione: Extract *tar* into *dest*, refusing any member that would escape it — | `verimem/local_grounding.py` | `tests/test_gate_model_tarslip.py` | NON MISURATO |
| 28 | `verimem/local_grounding.py:730` `ensure_gate_model` | funzione: Ensure the local gate CE exists at ``model_dir``; download+verify+extract | `verimem/anti_confab_gate.py`; `verimem/cli.py` (+1) | `tests/test_gate_model_fetch_and_doctor.py`; `tests/test_una_cartella_vuota_non_e_un_giudice.py` (+1) | NON MISURATO |
| 29 | `verimem/local_grounding.py:759` `_esito_dell_installazione` | funzione: Se il modello sia utilizzabile dopo il download, e cosa manca se no. | `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 30 | `verimem/local_grounding.py:804` `_delegate_only` | funzione | `verimem/embedding.py`; `verimem/local_grounding.py` (+2) | **nessuno** | NON MISURATO |
| 31 | `verimem/local_grounding.py:816` `_gate_via_daemon` | funzione: Punteggi del giudice del moat dal daemon condiviso, o None per degradare. | `verimem/local_grounding.py` | `tests/test_il_giudice_del_moat_vive_nel_daemon.py` | NON MISURATO |
| 32 | `verimem/local_grounding.py:872` `warm_local_judge_async` | funzione: Warm the CE off the request thread (once per process). Load failure is | `verimem/local_grounding.py` | **nessuno** | NON MISURATO |
| 33 | `verimem/local_grounding.py:881` `warm_local_judge_async._warm` | funzione | `verimem/local_grounding.py`; `verimem/preload.py` | **nessuno** | NON MISURATO |
| 34 | `verimem/local_grounding.py:890` `try_local_score` | funzione: (score, config_threshold) via the local judge, or None when the local model is | `verimem/client.py`; `verimem/conversation_ingest.py` (+1) | `tests/test_answer_grounding_verified.py`; `tests/test_il_giudice_del_moat_vive_nel_daemon.py` (+5) | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





