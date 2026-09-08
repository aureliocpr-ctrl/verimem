# `verimem/facts_conflict.py` — 563 righe, 11 funzioni

**Il giro dedicato che avevo dichiarato di non aver fatto.** È il file più grande del lotto
3, e nella prima passata l'avevo trattato come un tool qualunque. *«Contradiction detection
over the semantic-memory facts table.»* Su `7b9e8ca1`.

---

## 1. TRE rilevatori di conflitto, non uno

| funzione | riga | cosa trova |
|---|---|---|
| `find_conflicting_pairs` | 202 | coppie (positivo, negativo) — la **negazione** |
| `find_numeric_conflicts` | 326 | **valori diversi** per la stessa unità |
| `find_lexical_conflicts` | 469 | scansione retroattiva di tutto ciò che il write-gate lessicale fermerebbe **oggi** |

📌 `find_lexical_conflicts` è **retroattiva** per progetto: passa sul corpus già scritto col
gate di adesso. È la risposta a *«il gate è migliorato: cosa sarebbe stato fermato?»* — una
domanda che quasi nessun prodotto si fa sul proprio passato.

---

## 2. ⚠️ Il sospetto che avevo, e perché era SBAGLIATO

Il tool MCP `hippo_facts_find_conflicting` chiama **due** delle tre:

    mcp_server.py:11906   pairs = find_conflicting_pairs(…)
    mcp_server.py:11918   _lex  = find_lexical_conflicts(…)

E `find_numeric_conflicts` non compare in `mcp_server`, né in `cli.py`: le sue due
occorrenze fuori dal file sono **docstring** (`corroboration.py:9`, `quantity_match.py:11`).
Sembrava **un rilevatore su tre non raggiungibile dall'utente**.

**Il secondo righello — dentro il proprio file — l'ha smentito**, e il docstring lo diceva:

    facts_conflict.py:478   «numeric-quantity changes (DELEGATES TO find_numeric_conflicts)»
    facts_conflict.py:496   for p in find_numeric_conflicts(…)

⇒ **La catena è: tool MCP → `find_lexical_conflicts` → `find_numeric_conflicts`.** Tutti e
tre i rilevatori sono raggiungibili; uno lo è **per delega**. Il file è sano.

🔑 **La lezione, per chi mappa**: un conteggio dei chiamanti che guarda solo *fuori* dal
modulo dichiara irraggiungibile ciò che è chiamato **per delega interna**. È lo stesso
errore che stasera mi ha prodotto 20 falsi positivi su 21 — qui l'avrebbe fatto **su una
capacità di prodotto**, non su un helper.

---

## 3. La copertura: cinque file di test

    test_facts_conflict.py · test_facts_conflict_lexical.py · test_facts_conflict_numeric.py
    test_gate_semantic_conflict_wire.py · test_mcp_facts_conflict.py

⇒ i tre rilevatori, il collegamento al gate **e** la porta MCP hanno ciascuno il proprio
file. Fra i 97 file che ho mappato, **è quello con la copertura nominale più articolata**.

📌 `has_negation` (99) è pubblica e dichiara la sua regola: *«True iff `text` contains an ODD
number of syntactic negations»* — **dispari**, non «almeno una». La doppia negazione torna
affermazione, ed è scritto nella firma invece che scoperto da chi legge il codice.

---

## 4. Quello che questa mappa NON dice

- **Non ho eseguito nessuno dei tre rilevatori**: la prova qui è la catena delle chiamate e
  la presenza dei test, non un giro vero su dati.
- **Non ho verificato che i 5 file di test coprano i casi che contano** (solo che esistano e
  nominino le funzioni).
- `_pairs` (523), `_overlap_coefficient` (187), `_content_tokens` (177): lette di nome.

---

*ws5 (Tara), 08/09. Il giro dedicato che mancava, e si chiude in positivo.*
