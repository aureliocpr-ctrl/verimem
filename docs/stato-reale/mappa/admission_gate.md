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

*Mappato da ws5 (Tara) su `7b9e8ca1`. Il 21% di perdita è una misura del team, attribuita.*
