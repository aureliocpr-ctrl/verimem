# `verimem/_hang_watchdog.py` — 232 righe, 4 funzioni

**Non previene gli hang: li rende DIAGNOSABILI.** *«Hang watchdog — make intermittent
multi-minute MCP hangs DIAGNOSABLE.»* Mappato su `7b9e8ca1`. 2 pubbliche, 2 private.

---

## 1. Il mestiere: un dump degli stack quando una chiamata sfonda il budget

`hang_trace` (148) avvolge una tool call: se dura più di `budget_s`, scrive un dump.
`avvia_il_sorvegliante` (103) accende **il sorvegliante UNICO** all'avvio del server;
`_cicla_e_sorveglia` (82) guarda il file corrente e **disarma il timer** quando la chiamata
rientra.

🔑 **La scelta di progetto è dichiarata nel nome del modulo**: davanti a un hang
intermittente di minuti, il prodotto **non prova a impedirlo** — prova a lasciare una
traccia leggibile. È la stessa filosofia di `EncodeDelegateUnavailable` in `embedding`:
meglio un fallimento che si spiega di un fallimento che si nasconde.

📌 Ed è lo strumento che ha **prodotto la diagnosi di T1b**: i due `create_module` fermi in
parallelo — uno nel thread di preload, uno nel thread che serviva — vengono da un dump di
questo watchdog (06/09). Senza, T1b sarebbe ancora «ogni tanto non risponde».

---

## 2. `_pota_i_vecchi` (134) — la difesa che ha già un test col nome giusto

> *«Tiene i `_MAX_FILES` trace più recenti. Best-effort come tutto…»*

Un diagnostico che scrive file a ogni hang è un diagnostico che riempie il disco. La cura è
qui, e il presidio si chiama `tests/test_il_watchdog_non_si_mangia_il_disco.py` — **6 passed
sul perimetro di stasera**.

⚠️ Nota per chi legge oggi: la mia scratchpad è **19,0 GB** perché nessuno ha potato le
*home* dei banchi. Questo modulo pota le proprie tracce; il resto del nostro lavoro no.

---

## 3. Il vincolo che questo file rispetta: non avviare thread nella richiesta

Il presidio `tests/test_il_watchdog_non_avvia_thread_nella_richiesta.py` (**3 passed**)
tiene fermo il punto: il sorvegliante è **uno**, acceso all'avvio, e la richiesta non ne
crea altri. È la stessa classe di difetto di T1b — *un thread avviato al momento sbagliato* —
presidiata prima che accada.

---

## 4. Le 4 funzioni

**Pubbliche (2)**: `avvia_il_sorvegliante` · `hang_trace`.
**Private (2)**: `_cicla_e_sorveglia` · `_pota_i_vecchi`.

---

## 5. Quello che questa mappa NON dice — dichiarato

- **Non ho fatto scattare il watchdog.** So cosa dichiara e quali presidi lo coprono; non ho
  provocato un hang per vedere il dump. Vale l'avvertenza di sempre: *una difesa che non si
  accende è indistinguibile da una che non serve mai* — qui però **una prova storica c'è**,
  ed è il dump di T1b del 06/09.
- **`HIPPO_HANG_TRACE_S=0`** compare in tutti i miei comandi di banco (spegne il
  watchdog): **non ho verificato** cosa cambia con il watchdog acceso durante i test, e in
  linea di principio potrebbe mascherare o rivelare qualcosa.
- **`_MAX_FILES` non l'ho letto**: so che esiste una potatura, non a quale soglia.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I conteggi dei presidi (6 e 3 passed) sono miei,
eseguiti stasera sul perimetro `preload|_scalda`.*

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


### `verimem/_hang_watchdog.py` — 4 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/_hang_watchdog.py:82` `_cicla_e_sorveglia` | funzione: Guarda il file corrente, se c'e', e disarma il timer quando sfonda. | `verimem/_hang_watchdog.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/_hang_watchdog.py:103` `avvia_il_sorvegliante` | funzione: Avvia il sorvegliante UNICO. Va chiamata all'avvio del server. | `verimem/mcp_server.py` | `tests/test_il_watchdog_non_si_mangia_il_disco.py` | NON MISURATO |
| 3 | `verimem/_hang_watchdog.py:134` `_pota_i_vecchi` | funzione: Tiene i ``_MAX_FILES`` trace più recenti. Best-effort come tutto il | `verimem/_hang_watchdog.py` | `tests/test_il_watchdog_non_si_mangia_il_disco.py` | NON MISURATO |
| 4 | `verimem/_hang_watchdog.py:148` `hang_trace` | funzione: Wrap a tool call. If it runs longer than ``budget_s`` seconds, append a | `verimem/mcp_server.py` | `tests/test_hang_watchdog.py`; `tests/test_il_watchdog_non_avvia_thread_nella_richiesta.py` (+1) | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





