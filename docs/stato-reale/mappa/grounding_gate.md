# `verimem/grounding_gate.py` — 671 righe, 22 funzioni

**Il modulo che decide se una fonte sostiene un fatto, e con quale soglia.** È il livello
sotto `anti_confab_gate`: qui non ci sono layer, c'è il punteggio e il taglio. Mappato su
`7b9e8ca1`. 11 funzioni pubbliche, 11 private.

---

## 1. 🔴 IL REPERTO: **lo span viene troncato DUE VOLTE, e solo il secondo costa**

Questo è il pezzo che spiega T40 e ne rende la cura precisa.

| dove | funzione | unità | costo |
|---|---|---|---|
| `grounding_gate.py:364` | `select_relevant_span` | **caratteri** (`up to budget chars`) | **zero** — *«Pure + deterministic — no embeddings»* |
| `local_grounding.py:389` | `_entro_la_finestra` | **token** | **35,4 s** — serve il tokenizer (misurato stasera) |

Il primo taglio è già fatto, è gratis, ed è quello che porta il beneficio dichiarato nel
docstring:

> *clean-admission ~0.70 → 0.80 a budget di caratteri FISSO, noise-rejection invariata
> ~100%* (`benchmark/halumem_gate_source_ab.py`)

Il secondo taglio ri-riduce lo **stesso** span contando token, e per contarli carica un
tokenizer da 35 secondi **sul thread della richiesta**.

⇒ **La cura di T40 diventa piccola e a basso rischio**: in delegate-only lo span è già
dentro un budget di caratteri e va **mandato al daemon così com'è** — il conteggio dei token
lo fa chi il modello ce l'ha già in memoria. Non serve inventare un troncamento nuovo:
serve **non fare il secondo**.

---

## 2. Le soglie: tre risolutori, non uno

    _resolve_threshold          (161)  generico
    _resolve_write_threshold    (173)  «Calibrated LOWER» per il percorso di SCRITTURA
    resolve_write_threshold_for (510)  la soglia CONSISTENTE col giudice che ha prodotto il punteggio

🔑 Il terzo esiste perché **il taglio dipende da chi ha giudicato**: un punteggio del CE
locale e uno di un llm non stanno sulla stessa scala, e applicare la soglia sbagliata è il
modo silenzioso di ammettere o rifiutare per errore. `_resolve_write_threshold` dichiara che
il taglio in scrittura è **più basso** di quello in lettura — una scelta, non un caso.

📌 Su questo albero c'è anche il presidio della banda di mezzo: `_ce_band_enforced` (570),
**acceso di default dal 2026-07-19**, con `_ce_band_tau_hi` (565).

---

## 3. Il giudice: `_e_un_giudice_vero` (194)

> *«C'è un llm che sa davvero giudicare, o solo il segnaposto?»*

È il predicato che impedisce di chiamare `llm.complete()` su un oggetto finto. `_resolve_backend`
(245) sceglie fra `claude` (default, llm iniettato) e `local`; `fact_grounding_score_ex`
(439) torna **anche QUALE giudice ha prodotto il punteggio** — ed è la funzione che rende
possibile la soglia coerente del §2.

---

## 4. `confidence_tier` (586) — il campo che dice di non essere una verità

> *«The judge's CONFIDENCE level for a gate score — **NOT a truth claim**»*

📌 È il tipo di onestà che manca altrove nel prodotto: il nome del campo potrebbe far
credere a una probabilità di verità, e il docstring lo nega esplicitamente. **Chi scrive
ricevute copi questa riga.**

---

## 5. L'astensione, e perché ha un classificatore

    _is_abstention   (113)
    _abstention_kind (127)  «Classify a reply for the short-circuit decision (F4, kimi audit…)»

Una risposta che si astiene non va giudicata come una risposta sbagliata: `gate_answer`
(290) la fa uscire prima. ⇒ **l'astensione è un esito, non un fallimento** — coerente con
la riga del README sulle *«honest read-path abstentions»*.

---

## 6. Le 22 funzioni

**Pubbliche (11)**: `grounding_score` · `is_grounded` · `gate_answer` · `optimal_threshold`
· `select_relevant_span` · `fact_grounding_score` · `fact_grounding_score_ex` ·
`resolve_write_threshold_for` · `confidence_tier` · `should_store_fact` ·
`fact_grounding_span`.

**Private (11)**: `_is_abstention` · `_abstention_kind` · `_resolve_threshold` ·
`_resolve_write_threshold` · `_resolve_judge` · `_e_un_giudice_vero` · `_resolve_backend` ·
`_span_tokens` · `_overlap` · `_ce_band_tau_hi` · `_ce_band_enforced`.

📌 `should_store_fact` (614) e `fact_grounding_span` (648) sono le due porte che il resto
del prodotto chiama: la prima decide, la seconda **conserva la prova** (`{"score", "span"}`).
⚠️ E il team ha misurato **2.786 fatti giudicati senza span conservato** — cioè la seconda
non è sempre stata chiamata dove la prima decideva. Reperto mio del 07/09, **non curato da
nessuno**.

---

## 7. Quello che questa mappa NON dice — dichiarato

- **`optimal_threshold` (Youden's J) non è esercitata qui**: non so se sia usata a runtime
  o solo negli esperimenti.
- **Non ho misurato** se `select_relevant_span` e `_entro_la_finestra` producano lo stesso
  span su input reali: l'ipotesi che il secondo sia ridondante in delegate-only **va provata
  con un A/B** prima della cura di T40, non dopo.
- `_span_tokens` e `_overlap` sono lette solo di nome.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. §1 usa i tre bracci misurati da me stasera; il numero
del §2 e il beneficio dello span vengono dal docstring e sono attribuiti lì.*
