# `verimem/encode_service.py` — 974 righe, 37 funzioni

**Il daemon condiviso: un processo per macchina che tiene i modelli caldi per tutti.**
Il nome dice «encode» e ne serve **tre**. Mappato su `7b9e8ca1`. 17 pubbliche, 20 private.

---

## 1. 🔑 Il nome mente per difetto: il daemon serve TRE modelli

    _default_encode_fn (147)   l'embedder
    _default_rerank_fn (163)   «Punteggi del cross-encoder, calcolati QUI — nel daemon, una volta …»
    _default_gate_fn   (184)   «Punteggi del GIUDICE DEL MOAT, calcolati qui — nel daemon, una volta …»

⇒ **Il daemon è anche il giudice.** È la ragione per cui tutta la giornata è girata intorno
a lui: senza daemon, il server MCP delegate-only non ha *nessuna* delle tre vie, e con lui le
ha tutte e tre a costo di un round-trip.

📌 Il file si chiama `encode_service` e la classe fa da encoder, reranker e giudice: chi
cerca «dove vive il moat» non lo cerca qui. **È il tipo di nome che costa mezz'ora a chi
arriva.**

---

## 2. Le difese: quasi tutto il file protegge il daemon dai propri modi di morire

| modo di fallire | chi lo previene | come |
|---|---|---|
| **due daemon insieme** | `acquire_daemon_lock` (722) | claim **atomico**, uno per macchina |
| **lock di un altro rimosso per errore** | `release_daemon_lock` (769) | *«iff THIS process owns it — never someone else's»* |
| **zombie**: vivo ma non serve | `_owner_is_zombie` (682) | *«True se il proprietario del lock è vivo ma non sta SERVENDO»* |
| **pid riciclato / stato ignoto** | `_pid_alive` (586) | *«Unknown/odd states err on 'alive'»* — sbaglia verso il conservativo |
| **pid check che uccide** | `_pid_alive_windows` (612) | *«never sends a console control»* — su Windows un controllo può terminare il processo |
| **daemon del modello sbagliato** | `daemon_usable` (840) | raggiungibile **E** annuncia `CONFIG.embedding_model` |
| **annuncio perso** | `_republish_discovery_if_unclaimed` (383) | si ri-annuncia se nessuno annuncia |
| **daemon superfluo** | `_mark_superfluous` (453) | *«Record the **transition**, not just the state»* |
| **attesa infinita** | `_should_idle_exit` (485) + `_effective_idle_timeout` (462) | esce da sé, e il timeout dipende **da chi è annunciato** |

🔑 **`daemon_usable` contro `is_reachable` (825) è la distinzione che conta**, ed è già
citata in `preload.py`: *«a stale wrong-model daemon is unusable to encode(), so trusting
mere reachability would skip the local warm and leave every encode cold-loading ~20 s»*.
Un daemon che risponde non è un daemon che serve.

📌 Il caso zombie **ha un nome nel codice** — ed è già costato: sui nostri appunti c'è
*«un daemon vivo che non serviva teneva spenta la semantica su tutta la macchina»* (25/07).
Qui la lezione è diventata una funzione.

---

## 3. Il costo del round-trip, misurato oggi

Il daemon non è gratis: nei miei tre bracci di stasera **A − B = 7,5 s** è il tratto che
passa da lui su una prima chiamata. E @ws1 ha misurato lo stesso tratto in condizioni di
carico dell'agenzia: **26,5 s contro 2,2 s in processo (≈11×)**, con l'avvertenza — sua —
che quel numero misura *«tutto quello che passa dal daemon»*, encoding compreso, non «il
giudice».

⚠️ **Nessuno dei due numeri va letto come "il daemon rallenta"**: sono misure sotto otto
agenti sulla stessa macchina. Il file stesso non promette latenze.

---

## 4. Il protocollo, in due funzioni

`recv_msg` (115) / `send_msg` (129): JSON **con prefisso di lunghezza**, `None` su EOF
pulito. `read_discovery` (134) legge il file di annuncio *«or None if absent/unparsable»* —
**mai un'eccezione al chiamante** per un file assente: il degrado è la norma qui.

`_spawn_detached` (864): processo **staccato e senza finestra** — *«no console flash»*.
Dettaglio da desktop, non da server, e dice chi è l'utente vero di questo prodotto.

---

## 5. Le 37 funzioni

**Pubbliche (17)**: `recv_msg` · `send_msg` · `read_discovery` · `acquire_daemon_lock` ·
`release_daemon_lock` · `ping_healthy` · `is_reachable` · `daemon_usable` · `ensure_running`
· `main` · e sulla classe `port` · `start` · `serve_forever` · `stop`.
**Private (20)**: `_idle_timeout_s` · `_recvall` · `_default_encode_fn` ·
`_default_rerank_fn` · `_default_gate_fn` · `_pid_alive` · `_pid_alive_windows` ·
`_read_lock_owner` · `_owner_is_zombie` · `_ping` · `_spawn_detached` · `__init__` ·
`_touch` · `_idle_for` · `_to_list` · `_handle_request` · `_serve_conn` ·
`_write_discovery` · `_republish_discovery_if_unclaimed` · `_mark_superfluous` ·
`_effective_idle_timeout` · `_should_idle_exit` · `_clear_discovery`.

---

## 6. Quello che questa mappa NON dice — dichiarato

- ~~**Non ho esercitato nessuna delle difese del §2.**~~ ✅ **CHIUSO il 10/09**, e non da
  un banco: dall'incidente vero. La notte del 09-10/09 il daemon è stato rimpiazzato da uno
  con un **altro modello** (`e5-base`/768 → `MiniLM`/384) e le difese sono state osservate
  **mentre lavoravano**:

      is_reachable()   = True     il daemon rispondeva
      daemon_usable()  = False    e RIFIUTAVA, perché il modello non era quello di CONFIG
      lock owner       = 34992    il daemon sbagliato teneva il lock del singleton
      eta del lock     = 3844 s   (grazia 600 s)
      _owner_is_zombie = True     ⇒ il lock era RUBABILE

  ⇒ **`_owner_is_zombie` SI ACCENDE**, ed è model-aware perché passa da `daemon_usable`.
  La mia prima ipotesi — «il lock è model-blind, un daemon col modello sbagliato non si
  sostituisce più» — era **falsa**, falsificata prima di pubblicarla. Il sostituto è nato in
  **42 s** con una sola chiamata a `ensure_running()`, senza uccidere niente.

- 🔴 **E LA DIFESA CHE MANCA, trovata nello stesso incidente**: `DISCOVERY_PATH` (41),
  `_SPAWN_LOCK_PATH` (573) e `DAEMON_LOCK_PATH` (583) stanno tutti in **`Path.home()`**, mai
  nella data dir. ⇒ **un processo che isola `ENGRAM_DATA_DIR` NON isola il daemon**: legge
  la discovery globale, non riconosce il modello, ne spawna uno col **proprio** e lo
  registra per tutti. Il 09/09 l'ha fatto un banco isolato di un'altra istanza
  (`ENGRAM_DATA_DIR = …\Temp\ws2-t49-…`, `ENGRAM_EMBEDDING_MODEL = …MiniLM…`, letto dal suo
  `environ`), e il ripristino manuale è durato **12 minuti**. Costo: 15 fatti entrati nello
  store di produzione senza vettore. Rimedio immediato `ENGRAM_ENCODE_SERVICE=0` nei banchi
  con un modello diverso; la cura strutturale (discovery e lock **dentro** la data dir) è
  una decisione di progetto, **aperta**.
- **Non so se `_default_gate_fn` sia esercitata da un test**: è il percorso per cui il
  daemon giudica, cioè quello che ha reso verde la cura di oggi.
- **`_handle_request` e `_serve_conn`** sono lette solo di nome: non ho mappato quali
  comandi il protocollo accetta.
- **Nessuna misura di latenza è di questo file**: i numeri del §3 vengono dai banchi, con il
  loro regime.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I 7,5 s del §3 sono miei, dell'08/09; i 26,5 / 2,2 s
sono di @ws1, attribuiti.*

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


### `verimem/encode_service.py` — 38 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/encode_service.py:44` `_idle_timeout_s` | funzione: Seconds of inactivity before the daemon self-exits. | `verimem/encode_service.py` | `tests/test_encode_service_idle.py`; `tests/test_superfluous_daemon_steps_aside.py` | NON MISURATO |
| 2 | `verimem/encode_service.py:105` `_recvall` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 3 | `verimem/encode_service.py:115` `recv_msg` | funzione: Read one length-prefixed JSON message. None on clean EOF. | `verimem/embedding.py`; `verimem/encode_service.py` (+2) | `tests/security/test_encode_service_auth.py`; `tests/test_daemon_health_probe.py` (+4) | NON MISURATO |
| 4 | `verimem/encode_service.py:129` `send_msg` | funzione | `verimem/embedding.py`; `verimem/encode_service.py` (+2) | `tests/security/test_encode_service_auth.py`; `tests/test_daemon_health_probe.py` (+4) | NON MISURATO |
| 5 | `verimem/encode_service.py:134` `read_discovery` | funzione: Return the running service's discovery info, or None if absent/unparseable. | `verimem/doctor.py`; `verimem/embedding.py` (+4) | `tests/security/test_encode_service_auth.py`; `tests/test_il_reranker_vive_nel_daemon.py` | NON MISURATO |
| 6 | `verimem/encode_service.py:147` `_default_encode_fn` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 7 | `verimem/encode_service.py:163` `_default_rerank_fn` | funzione: Punteggi del cross-encoder, calcolati QUI — nel daemon, una volta sola. | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 8 | `verimem/encode_service.py:184` `_default_gate_fn` | funzione: Punteggi del GIUDICE DEL MOAT, calcolati qui — nel daemon, una volta sola. | `verimem/encode_service.py` | `tests/test_il_giudice_del_moat_vive_nel_daemon.py` | NON MISURATO |
| 9 | `verimem/encode_service.py:213` `EncodeServer` | classe: Threaded localhost encode server. ``encode_fn`` is injectable for tests. | `verimem/encode_service.py` | `tests/security/test_encode_service_auth.py`; `tests/test_daemon_health_probe.py` (+7) | NON MISURATO |
| 10 | `verimem/encode_service.py:216` `EncodeServer.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 11 | `verimem/encode_service.py:269` `EncodeServer.port` | funzione | `verimem/cli.py`; `verimem/encode_service.py` (+1) | `tests/security/test_ssrf.py`; `tests/security/test_ssrf_rebind_real_socket.py` (+5) | NON MISURATO |
| 12 | `verimem/encode_service.py:272` `EncodeServer._touch` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 13 | `verimem/encode_service.py:276` `EncodeServer._idle_for` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 14 | `verimem/encode_service.py:280` `EncodeServer._to_list` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 15 | `verimem/encode_service.py:283` `EncodeServer._handle_request` | funzione | `verimem/encode_service.py` | `tests/test_embedding_model_versioning.py` | NON MISURATO |
| 16 | `verimem/encode_service.py:331` `EncodeServer._serve_conn` | funzione | `verimem/encode_service.py` | `tests/test_daemon_republishes_its_discovery.py` | NON MISURATO |
| 17 | `verimem/encode_service.py:354` `EncodeServer._write_discovery` | funzione | `verimem/encode_service.py` | `tests/test_daemon_republishes_its_discovery.py` | NON MISURATO |
| 18 | `verimem/encode_service.py:383` `EncodeServer._republish_discovery_if_unclaimed` | funzione: Re-announce this daemon if nothing currently announces it. | `verimem/encode_service.py` | `tests/test_daemon_health_probe.py`; `tests/test_daemon_republishes_its_discovery.py` (+1) | NON MISURATO |
| 19 | `verimem/encode_service.py:453` `EncodeServer._mark_superfluous` | funzione: Record the transition, not just the state — when the step-aside | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 20 | `verimem/encode_service.py:462` `EncodeServer._effective_idle_timeout` | funzione: Seconds of silence before self-exiting, given who is announced. | `verimem/encode_service.py` | `tests/test_superfluous_daemon_steps_aside.py` | NON MISURATO |
| 21 | `verimem/encode_service.py:485` `EncodeServer._should_idle_exit` | funzione: Whether to stop waiting for requests that are not coming. | `verimem/encode_service.py` | `tests/test_superfluous_daemon_steps_aside.py` | NON MISURATO |
| 22 | `verimem/encode_service.py:512` `EncodeServer._clear_discovery` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 23 | `verimem/encode_service.py:523` `EncodeServer.start` | funzione | `verimem/_hang_watchdog.py`; `verimem/ann_cache.py` (+36) | `tests/security/test_encode_service_auth.py`; `tests/security/test_pentest_validation.py` (+39) | NON MISURATO |
| 24 | `verimem/encode_service.py:531` `EncodeServer.serve_forever` | funzione | `verimem/encode_service.py` | `tests/security/test_encode_service_auth.py`; `tests/security/test_ssrf_rebind_real_socket.py` (+5) | NON MISURATO |
| 25 | `verimem/encode_service.py:561` `EncodeServer.stop` | funzione | `verimem/decision_chain.py`; `verimem/encode_service.py` (+1) | `tests/security/test_encode_service_auth.py`; `tests/swarm/test_cli.py` (+10) | NON MISURATO |
| 26 | `verimem/encode_service.py:586` `_pid_alive` | funzione: Best-effort liveness. Unknown/odd states err on 'alive' — a false | `verimem/encode_service.py`; `verimem/interactive_judge.py` | `tests/test_ram_footprint.py` | NON MISURATO |
| 27 | `verimem/encode_service.py:612` `_pid_alive_windows` | funzione: Windows liveness via the Win32 API — never sends a console control event | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 28 | `verimem/encode_service.py:636` `_read_lock_owner` | funzione | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 29 | `verimem/encode_service.py:682` `_owner_is_zombie` | funzione: True se il proprietario del lock e' vivo ma non sta SERVENDO. | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 30 | `verimem/encode_service.py:722` `acquire_daemon_lock` | funzione: Atomically claim the one-daemon-per-machine lock. | `verimem/encode_service.py` | `tests/test_daemon_zombie_does_not_block.py`; `tests/test_ram_footprint.py` | NON MISURATO |
| 31 | `verimem/encode_service.py:769` `release_daemon_lock` | funzione: Remove the lock iff THIS process owns it (never someone else's). | `verimem/encode_service.py` | `tests/test_ram_footprint.py` | NON MISURATO |
| 32 | `verimem/encode_service.py:779` `_ping` | funzione: One verified ping round-trip, or None. | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 33 | `verimem/encode_service.py:817` `ping_healthy` | funzione: True iff a daemon ANSWERS a verified ping within the timeout. | `verimem/encode_service.py` | `tests/test_daemon_health_probe.py` | NON MISURATO |
| 34 | `verimem/encode_service.py:825` `is_reachable` | funzione: True if a daemon is listening per the discovery file (or given info). | `verimem/encode_service.py`; `verimem/mcp_server.py` | `tests/test_daemon_health_probe.py` | NON MISURATO |
| 35 | `verimem/encode_service.py:840` `daemon_usable` | funzione: True iff a daemon is reachable AND advertises ``CONFIG.embedding_model``. | `verimem/doctor.py`; `verimem/embedding.py` (+6) | `tests/test_cold_start_warmup.py`; `tests/test_daemon_health_probe.py` (+1) | NON MISURATO |
| 36 | `verimem/encode_service.py:864` `_spawn_detached` | funzione: Spawn the daemon in a DETACHED, windowless process (no console flash). | `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 37 | `verimem/encode_service.py:882` `ensure_running` | funzione: Ensure the shared encode daemon is up; spawn it (windowless) if not. | `verimem/cli.py`; `verimem/memory.py` (+2) | `tests/test_discovery_not_deleted_for_live_daemon.py`; `tests/test_encode_service.py` | NON MISURATO |
| 38 | `verimem/encode_service.py:952` `main` | funzione | `verimem/auto_dream_worker.py`; `verimem/cli.py` (+9) | `tests/perf/bench.py`; `tests/perf/bench_briefing_v3_robustness.py` (+25) | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





