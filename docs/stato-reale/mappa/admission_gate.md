# `verimem/admission_gate.py` — 339 righe, 6 funzioni

**Il cancello del corpus CURATO**: decide se un fatto entra fra quelli che il recall serve,
o finisce altrove. Sei funzioni, tutte pubbliche. Mappato su `7b9e8ca1`.

---

## 1. 🔑 «Scritto» non vuol dire «servibile» — e questo file è il perché

`telemetry_route_prefixes` (39): *«Topic prefixes that **ROUTE** a write to the telemetry
table»*. ⇒ Una scrittura può **riuscire** e finire **fuori dal corpus curato**, in una
tabella di telemetria che il recall non serve.

⚠️ È esattamente la distinzione che sui nostri appunti costa di più — *«`superseded_by IS
NULL` ≠ vivo»*, e il **21% di perdita** fra fatti scritti e fatti serviti. Qui c'è una delle
cause, ed è **una scelta di progetto, non un difetto**: certi topic sono telemetria per
definizione.

📌 E il prodotto lo **dice**: `warn_first_route_once` (127) — *«Tell the operator, **once per
process**, that a write was ROUTED»*. Una volta per processo, non a ogni scrittura: abbastanza
per accorgersene, non tanto da diventare rumore che si impara a ignorare.

---

## 2. Il cancello è ACCESO di default, e la data è nel codice

`gate_enabled` (89): *«The admission gate is **ON by default since 0.7.0**»*. Un default
dichiarato con la versione da cui vale — chi legge sa **da quando** il comportamento è
questo, che è la differenza fra una nota e una riga utile.

---

## 3. Le altre tre

| funzione | mestiere |
|---|---|
| `normalize_proposition` (221) | *«Stable key for exact-duplicate detection (whitespace + case)»* |
| `classify_admission` (226) | classifica un candidato per il corpus curato |
| `audit_corpus` (289) | **READ-ONLY**: passa il gate su una `semantic.db` viva e riporta |

📌 `audit_corpus` è dichiarata read-only **nel docstring**: è lo strumento con cui si
misura il corpus senza cambiarlo — e nella nostra pratica *«lo store principale MAI in
scrittura per le misure»* è una regola che qui ha un supporto nel codice.

---

## 4. Quello che questa mappa NON dice — dichiarato

- **Non so quanti fatti del corpus reale siano stati instradati a telemetria**:
  `telemetry_route_prefixes` dice *quali* prefissi, non *quanti* fatti. È una query, e non
  l'ho fatta perché tocca lo store principale.
- **`classify_admission` non l'ho letta dentro**: so cosa promette il nome, non quali classi
  produce né con che criterio.
- **Non ho verificato** se il warning «once per process» sia effettivamente emesso sulle
  porte che usiamo (MCP, CLI, SDK): un avviso una-volta-per-processo su un processo di breve
  vita può non essere mai letto da nessuno.

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`. Il 21% di perdita è una misura del team, attribuita.*

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


### `verimem/admission_gate.py` — 7 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/admission_gate.py:39` `telemetry_route_prefixes` | funzione: Topic prefixes that ROUTE a write to the telemetry table — EMPTY | `verimem/admission_gate.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/admission_gate.py:89` `gate_enabled` | funzione: The admission gate is ON by default since 0.7.0. | `verimem/memory.py`; `verimem/semantic.py` | `tests/test_admission_gate_default_on.py`; `tests/test_admission_gate_wire.py` | NON MISURATO |
| 3 | `verimem/admission_gate.py:127` `warn_first_route_once` | funzione: Tell the operator, once per process, that a write was ROUTED. | `verimem/memory.py`; `verimem/semantic.py` | `tests/test_admission_gate_default_on.py` | NON MISURATO |
| 4 | `verimem/admission_gate.py:215` `AdmissionVerdict` | classe | `verimem/admission_gate.py` | **nessuno** | NON MISURATO |
| 5 | `verimem/admission_gate.py:221` `normalize_proposition` | funzione: Stable key for exact-duplicate detection (whitespace + case folded). | `verimem/admission_gate.py` | `tests/test_admission_gate.py` | NON MISURATO |
| 6 | `verimem/admission_gate.py:226` `classify_admission` | funzione: Classify a candidate fact for admission to the CURATED corpus. | `verimem/admission_cleanup.py`; `verimem/admission_gate.py` (+1) | `tests/security/test_gate_redteam_20260721.py`; `tests/test_admission_gate.py` (+3) | NON MISURATO |
| 7 | `verimem/admission_gate.py:289` `audit_corpus` | funzione: READ-ONLY: run the gate over a live semantic.db, return the breakdown. | **nessuno** | `tests/test_admission_gate.py`; `tests/test_epistemic_health_score.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





