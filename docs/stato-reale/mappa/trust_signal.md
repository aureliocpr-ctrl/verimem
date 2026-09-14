# Mappa di `verimem/trust_signal.py` — 2 righe, 164 righe di codice (lead, 09/09 01:20)

Letto per intero. Prove sul checkout a `20257636` (il tip): (1) `env -u HIPPO_ENCODE_DELEGATE_ONLY python -m pytest -q tests/test_freshness.py tests/test_hallucination_rate.py tests/test_il_recall_mette_davanti_chi_non_e_stato_verificato.py tests/test_mcp_wire_coherence_trust.py tests/test_rank_list_builders.py tests/test_sla.py tests/test_topic_normalization.py tests/test_trust_calibration_eval.py tests/test_trust_calibration_metrics.py tests/test_trust_signal.py tests/test_truth_reconciliation_p1.py` → `84 passed, 1 xfailed, 1 warning in 37.23s`, EXIT=0 (lotto B: otto moduli); (2) **prova diretta della funzione** (08/09 22:52, `sm=None`, fatti di 10 giorni a confidenza 0,9): `status=quarantined → trusted`, `provisional → trusted`, `orphaned → trusted`, `user_belief → trusted`, `model_claim conf=0.49 → unverified`, `legacy_unverified → unverified`, `verified → trusted`. Chiamanti letti: `verimem/semantic.py:3947,4592` (il recall con `trust_signals=True` attacca il verdetto a ogni hit), `verimem/contradiction.py:450`, `verimem/hallucination_rate.py:98` (la metrica del fossato legge questo verdetto). Claim README: nessuna riga nomina il trust signal o i suoi verdetti (grep su «trust signal|trusted|hallucination rate» → nessuna riga del README).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/trust_signal.py:42` `TrustSignal` | il verdetto vivo su un fatto: `trusted/stale/contested/obsolete/unverified`, età, contraddizioni, supersessione, spiegazione | `compute_trust_signal`, `hallucination_rate.py:95`, `recall_usage.py:5`, i tuple del recall | `tests/test_trust_signal.py`, `tests/test_mcp_wire_coherence_trust.py` | - | FUNZIONA COME PROMESSO | pytest 84 passed |
| 2 | `verimem/trust_signal.py:61` `compute_trust_signal` | priorità: superseded → obsolete; contraddizioni irrisolte → contested; età ≥ 180 g → stale; `legacy_unverified` o `model_claim` sotto 0,5 → unverified; **altrimenti trusted** | `verimem/semantic.py:3947,4592`, `contradiction.py:450`, `hallucination_rate.py:98`, `trust_calibration_eval.py:119` | `tests/test_trust_signal.py`, `tests/test_truth_reconciliation_p1.py` | - | FUNZIONA COME PROMESSO (fa ciò che il docstring dice; ma il docstring conosce DUE status su sette: un fatto `quarantined` è `trusted`, prova 2) | prova diretta 08/09 22:52 + pytest 84 passed |

Reperti: (a) **T50**: il verdetto di fiducia dà `trusted` a `quarantined`, `orphaned`, `user_belief` e `provisional` (quattro status su sette, prova 2), perché il ramo 4 guarda solo `legacy_unverified` e la confidenza dei `model_claim`; al recall ordinario non arriva (il recall li nasconde), ma ogni chiamante che passa fatti nascosti a `compute_trust_signal` (T49: sei tool pescano senza `hide_low_trust`) o la metrica `hallucination_rate_at_k` su un recall che li includa li conta come affidabili — livello misurato: FUNZIONE; alla porta NON MISURATO; (b) `sm` è un parametro dichiarato inutilizzato («V1 doesn't query it»); (c) il moat (`grounding_score`, `moat` della ricevuta) non entra nel verdetto: come `trust_score` e `fact_priority` (T47), tre classifiche di fiducia e nessuna legge il giudizio del gate.

---

## AGGIORNAMENTO 10/09 00:20 — T50 CURATO (ws4 Nadia, ramo `nadia/t50-t53`)

Il testo qui sopra è del lead e resta **verbatim**: questa sezione si aggiunge,
non riscrive, così la fusione dei rami `mappa/*` non ha da scegliere.

### Le due righe della tabella, aggiornate

| # | funzione (`file:riga`) | cosa promette ORA | verdetto | prova |
|---|---|---|---|---|
| 1 | `verimem/trust_signal.py:42` `TrustSignal` | `trusted/stale/contested/obsolete/unverified` **+ `rejected`** (T50) | FUNZIONA COME PROMESSO | `19 passed, 1 skipped` EXIT=0 |
| 2 | `verimem/trust_signal.py:61` `compute_trust_signal` | priorità: superseded → obsolete; contraddizioni → contested; età ≥ 180 g → stale; **rango < 0 (`quarantined`/`orphaned`/`user_belief`) → rejected**; **status ignoto alla tabella dei ranghi → unverified**; `provisional` → unverified; `legacy_unverified` o `model_claim` sotto 0,5 → unverified; altrimenti trusted | FUNZIONA COME PROMESSO **a entrambi i livelli** (docstring aggiornato nello stesso commit) | RED `5 failed, 8 passed, 1 skipped` EXIT=1 su `20257636` intonso → GREEN `13 passed, 1 skipped` EXIT=0; perimetro `49 passed` |

### Il reperto (a) del lead: CHIUSO, e la porta ORA È MISURATA

Il lead aveva scritto «livello misurato: FUNZIONE; **alla porta NON MISURATO**».
Misurata:

* `recall()` di default **non serve i quarantenati** — provato con il controllo
  positivo acceso (un `model_claim` con la stessa query ESCE, il quarantenato
  no): `test_un_quarantenato_non_esce_dal_recall_di_default`. Su questa porta il
  difetto era **latente, non servito**: il ticket era più piccolo di come suonava.
* `min_status='orphaned'` **non** riapre la porta su quel percorso: il test resta
  in **SKIP dichiarato**, non in verde. La prova «una porta lo serve E lo chiama
  trusted» va rifatta dalle sette porte di **T49** (ws2 Giano) — che dopo questa
  cura ricevono `rejected` invece di `trusted`.

### Il pezzo che non era nel ticket: lo status IGNOTO

T50 elencava quattro status. Ma il ramo di default mandava a `trusted` anche ogni
status che la tabella dei ranghi **non conosce**, e il numero è già nel prodotto,
nel docstring di `_rango_di_fiducia` (misura del 07/08 sullo store vero):
**la tabella conosce 7 stati, nello store ce ne sono 12, i fatti vivi con uno
stato ignoto sono 2540 su 6982 — il 36%**, di cui `user_manual` da solo 2493.
Non è una misura nuova: era scritta e nessuno l'aveva collegata a questa funzione.

### Due status su sette non si possono nemmeno scrivere

Misurato il 09/09 e fissato in `test_quali_status_sopravvivono_alla_scrittura`:
`store()` declassa `verified` (hard-gate v2, `semantic.py:3114`) e `provisional`
(whitelist URL/arxiv, `:3125`) a `model_claim`, e **muta l'oggetto `Fact` in
place**. La riga `provisional` del ticket vale solo per i fatti con un ref buono.

### CLAIM README — la riga del lead va corretta: ce n'è uno, ed è centrale

Il lead ha scritto «nessuna riga del README nomina il trust signal o i suoi
verdetti (grep su «trust signal|trusted|hallucination rate» → nessuna riga)».
Eseguito il 10/09 sullo stesso README (`20257636`):

```
$ grep -n "trust signal" README.md
463:# + provenance are the trust signal, not a self-asserted badge).

$ grep -c "trust signal|trusted|hallucination rate" README.md   # senza -E
0            EXIT=1
$ grep -cE "trust signal|trusted|hallucination rate" README.md  # con -E
1            EXIT=0
```

Causa: senza `-E`, `grep` tratta `|` come **carattere letterale** e cerca la
stringa intera `trust signal|trusted|hallucination rate`, che nel README non
c'è. Zero righe, uscita 1, e la conclusione «nessun claim» sembra misurata.

I claim che questa funzione presidia, ora collegati:

* **`README.md:462-463`** — «the gate's outcome + provenance are **the trust
  signal**, not a self-asserted badge». Prima di T50 l'esito del gate NON
  entrava nel verdetto per cinque status su sette: la frase era vera per la
  provenance e falsa per l'esito del gate.
  Presidio: `test_ogni_status_riceve_un_verdetto_sensato`.
* **`README.md:443-444`** — «stored but OUT of default recall — **your agent
  will never repeat it as truth**». La seconda metà è quella di T50: un verdetto
  `trusted` su un quarantenato *è* ripeterlo come verità a chiunque chieda il
  verdetto.
  Presidi: `test_un_fatto_fermato_dal_gate_non_si_chiama_trusted` e
  `test_un_quarantenato_non_esce_dal_recall_di_default`.

### Superficie e metrica

La cura **non aggiunge** una lista di status nascosti — sarebbe stata la quinta
copia, e le quattro esistenti divergono (due senza `user_belief`). Usa
`_rango_di_fiducia`, la superficie canonica.
`rejected` entra in `_RISKY_VERDICTS` di `hallucination_rate`: il contract-lock
in `tests/test_hallucination_rate.py:45` è aggiornato con la ragione accanto,
non aggirato. **Il tasso pubblicato può muoversi, ed è voluto.**

Reperto (b) del lead confermato e ancora aperto: `sm` resta un parametro
dichiarato inutilizzato. Reperto (c) ancora aperto: il moat (`grounding_score`)
non entra nel verdetto — resta T47.
