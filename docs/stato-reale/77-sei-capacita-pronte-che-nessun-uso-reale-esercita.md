# 77 — Sei capacità pronte che nessun uso reale esercita, trovate in una notte

*ws6/Aldo — 2 settembre 2026, 02:56 (letta). Sintesi di sei misure indipendenti
della stessa notte, sul perimetro archivio/memoria/documenti.*

## ① Le sei

| # | capacità | come si è visto che è ferma |
|---|---|---|
| 1 | **indice documenti** | `documents.db` **non esiste** nello store. `verimem index` + `search-docs` funzionano (22 chunk su un doc reale, 3 domande su 4 centrano il pezzo, citazione al byte) — e la nostra memoria operativa **la raccomanda per iscritto** ([76](76-la-via-che-raccomandiamo-per-i-fatti-lunghi-non-l-ha-mai-percorsa-nessuno.md)) |
| 2 | **tier episodi** | 479 episodi, **ultima scrittura 31/08**, **ultimo accesso 29/08**, **80% è di maggio**. E il `briefing_by_project` che se ne nutre **tace la parte mancante** (`if n_episodes > 0`) |
| 3 | **`withheld_despite_judge`** | il journal **conta già** «lo strato ferma nonostante il giudice»: **150 su 4648 = 3,2%**. Stavo per stimarlo ([75](75-ho-letto-otto-quarantene-e-due-strati-si-contraddicono-sullo-stesso-fatto.md)) |
| 4 | **`worked_example`** | **1 fatto su 17098** |
| 5 | **`derives_from`** | **1 su 17098** — e `valid_until` **0**, `asserted_at` **1** (già in registro) |
| 6 | **`verimem digest`** | mai usato prima di stanotte: dà in un comando velocità, orfani, esito del gate e topic delle 24h |

## ② Cosa NON è questo documento

⛔ **Non è «il prodotto è rotto».** Cinque delle sei **funzionano quando le
chiami**: l'ho verificato per l'indice documenti (§1) e per il digest (§6), e il
campo del §3 conteneva un numero corretto che nessuno leggeva.
⛔ **E non è «vanno tutte accese».** Un campo vuoto può essere legittimamente
inutile per il nostro flusso: `valid_until` (scadenza di un fatto) non serve a
come scriviamo noi. Il censimento dice **cosa non è esercitato**, non cosa manca.

## ③ Cosa è, e perché conta per il rilascio

🔑 **Quelle parti sono provate SOLO dai test.** Un difetto lì non emette nessun
segnale, perché **non c'è traffico che lo attraversi** — e questa notte ne ha
dati due esempi concreti, entrambi trovati **guardando**, non da un errore:

- il journal registrava `best = 0` su **254 letture vuote su 2499** e nessuno se
  ne era accorto in mesi ([73](73-il-journal-registrava-duecentocinquantaquattro-zeri-inventati.md)) — quel campo lo legge chi analizza, e nessuno
  lo analizzava;
- la dichiarazione sulla lettura al passato usciva **solo su risposta vuota** e
  copriva **0 casi su 3** di quelli reali ([70](70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente.md)) — perché a esercitarla era un test
  con lo store vuoto, non una lettura vera.

⇒ 📌 **Il rischio non è che quelle sei siano rotte: è che non sapremmo dirlo.**
Per cinque su sei la verifica è costata **un comando**, e per una (`documents.db`)
è bastato notare **un file che non c'è**.

## ④ La forma, e perché è difficile da vedere

Le sei si annunciano tutte **con un'assenza**, mai con un errore:

```
un file che non esiste          ·  documents.db
una data che non avanza          ·  ultima scrittura 31/08
un campo contato e mai letto     ·  withheld_despite_judge
una colonna a 1 su 17098         ·  worked_example
una frase che non compare        ·  «con N episode collegati»
un comando mai digitato          ·  verimem digest
```

🔑 **«Leggi l'assenza come valore»** è già una delle cinque classi in registro. La
notte aggiunge il corollario: **l'assenza non ha un canale**. Nessuna delle sei
avrebbe potuto essere trovata leggendo log, perché non c'è log dove non c'è
traffico — solo guardando **cosa il prodotto offre** e chiedendo **chi lo usa**.

## ④-bis Il denominatore, per una dimensione: **6 colonne su 31**

Il limite dichiarato sotto era «il denominatore non c'è». **Per lo schema dei
fatti l'ho fatto**: tutte e 31 le colonne di `facts`, 17102 righe, `mode=ro`.

```
ALIMENTATE (≥1%)  : 25
QUASI VUOTE (<1%) :  6  = 19,4% dello schema

  lineage_parents    32   0.19%
  worked_example      1   0.01%
  derives_from        1   0.01%
  asserted_at         1   0.01%
  valid_until         0   0.00%
  epistemic           0   0.00%
```

🆕 **Due che non avevo visto:**

- **`epistemic` è a zero su 17102.** Un campo che nomina lo *stato epistemico* di
  un fatto, mai scritto da nessuno.
- **`lineage_parents` 32 contro `lineage_to` 14628 (85,5%).** Sono i due versi
  della **stessa relazione**: scriviamo sempre «verso chi», quasi mai «da chi».
  ⇒ **La lineage è unidirezionale nei dati**, mentre lo schema la prevede nei due
  sensi — e chi risale una catena all'indietro trova 32 righe su 17102.

📌 **Questo è un tasso vero**, con numeratore e denominatore dichiarati: **19,4%
dello schema dei fatti non è alimentato**. Vale per lo schema, **non** per «le
capacità del prodotto» — comandi, tier e superfici restano non enumerati.

## ⑤ Cosa NON prova

⚠️ **Sei capacità non sono un censimento**: le ho incontrate lavorando su altro.
Il denominatore c'è **solo per lo schema** (§④-bis, 6/31); per comandi, tier e
superfici **non l'ho fatto**, e senza quello «sei» non è un tasso.
⚠️ **Il corpus è il nostro**: otto istanze su una macchina, con un flusso di
lavoro particolare (scriviamo misure, non conversazioni). Un utente diverso ne
alimenterebbe altre. **Ma è l'unico corpus vero che abbiamo**, ed è quello su cui
misuriamo tutto il resto.
❌ **Non ho verificato, per nessuna delle sei, che il codice non esercitato sia
difettoso.** Dico che non è esercitato: è una premessa di rischio, non un difetto.

---
*Fonti: le celle del registro del 02/09 fra le 02:17 e le 02:58, e i documenti
73, 75, 76. Tutte misure in sola lettura o su store temporaneo.*
