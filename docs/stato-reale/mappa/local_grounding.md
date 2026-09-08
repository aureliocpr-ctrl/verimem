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
