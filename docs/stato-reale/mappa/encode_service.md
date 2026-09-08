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

- **Non ho esercitato nessuna delle difese del §2.** So che esistono e cosa dichiarano;
  **non ho verificato che scattino** — e una difesa che non si accende è indistinguibile da
  una che non serve mai. Il caso più interessante da provare è `_owner_is_zombie`, perché la
  sua assenza è già costata una volta.
- **Non so se `_default_gate_fn` sia esercitata da un test**: è il percorso per cui il
  daemon giudica, cioè quello che ha reso verde la cura di oggi.
- **`_handle_request` e `_serve_conn`** sono lette solo di nome: non ho mappato quali
  comandi il protocollo accetta.
- **Nessuna misura di latenza è di questo file**: i numeri del §3 vengono dai banchi, con il
  loro regime.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I 7,5 s del §3 sono miei, dell'08/09; i 26,5 / 2,2 s
sono di @ws1, attribuiti.*
