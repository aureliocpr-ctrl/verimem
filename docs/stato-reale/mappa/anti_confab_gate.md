# `verimem/anti_confab_gate.py` — 3.380 righe, 42 funzioni

**Il file più grande della superficie che presidio, e quello dietro la frase di copertina.**
Mappato sul commit `7b9e8ca1` (origin/main). Ogni numero qui sotto viene da un comando
eseguito su quell'albero; dove il numero è di qualcun altro, è attribuito.

---

## 1. Cosa promette il README, e cosa risponde il codice

Il README vende questo file come *«stops what the source does not support»*. La domanda
che ne nasce è: **chi ferma cosa?** Il codice risponde con **tre famiglie di layer**, non
una:

| famiglia | quanti | cosa guarda | come decide |
|---|---|---|---|
| **L1.x** | 14 sigle (`L1`, `L1.5`, `L1.7`…`L1.21`) | **le parole del claim** | pattern lessicali/semantici — **non guarda la fonte** |
| **L3.x** | 6 sigle (`L3`, `L3-semantic`, `L3-supersession`, `L3-coexistence`, + 2 `-observe`) | **il claim contro i fatti già in memoria** | contraddizione / supersessione |
| **L4.x** | 8 sigle (`L4-grounding`, `L4-negazione`, `L4-relazione`, `L4-review`, `L4-skipped`, `L4.1`, `L4.1-ambiguo`, `L4.2`) | **il claim contro la SUA fonte** | il giudice CE (il «moat») |

🔑 **Solo L4 fa ciò che la frase di copertina descrive.** L1 ferma un claim **senza aver
mai letto la fonte**: giudica come è scritto, non se è sostenuto. Questa non è una critica
al design — L1 esiste per intercettare l'auto-affermazione di un agente, che è la
confabulazione tipica — ma **la frase del README descrive L4 e il lavoro lo fa in
maggioranza L1**.

> Misurato da @ws4 (non riverificato qui): **il 90,2% della quarantena del corpus viene
> dallo screen lessicale e non dal moat — 1728 su 1915.**

---

## 2. ⚠️ `L2` NON ESISTE in questa scala — e il nome è occupato altrove

    grep -rn '"L2' verimem/ --include=*.py
      verimem/anti_confabulation.py:485   f"L2 reconciler: {total} orphan facts found"
      verimem/cli.py:4227                 """L2 reconciler scan: ...
      verimem/mcp_server.py:14422         reason=f"L2 reconciler {cat}: ..."

**Nessuna ricevuta porterà mai `layer: "L2"`.** La numerazione L1→L4 sembra una scala
continua e non lo è: il gradino 2 vive in **un altro modulo** (`anti_confabulation.py` —
nome quasi identico a questo file) e significa **un'altra cosa** (una scansione del corpus
a posteriori, non un layer di scrittura).

⇒ Chi legge `L1.19` e `L3-semantic` in una ricevuta e cerca «cos'è L2» non trova un layer:
trova un reconciler. **Due file omonimi e una scala con un buco al centro** sono due
inciampi per chi legge, e non costano niente da documentare.

---

## 3. I 14 detector di L1 — riga per riga, cosa fermano

Tutti nella stessa funzione (righe 1477-1690), tutti sulla **forma del claim**:

| layer | riga | ferma un claim che dice… |
|---|---|---|
| `L1.8` | 1477 | parola-spia generica (struttura Warning con `advice`) |
| `L1.9` | 1492 | **prestazione** senza bench (`lacks bench evidence`) |
| `L1.10` | 1509 | «funziona / confermato» |
| `L1.11` | 1524 | «production-ready / stabile» |
| `L1.12` | 1540 | «sicuro / hardened» |
| `L1.13` | 1557 | «completato» |
| `L1.14` | 1573 | «documentato» |
| `L1.15` | 1588 | «testato / verificato» |
| `L1.16` | 1603 | «approvato» |
| `L1.17` | 1619 | «monitorato / osservato» |
| `L1.18` | 1635 | «automatizzato / schedulato» |
| `L1.19` | 1653 | **numero assoluto** senza fonte di misura (`lacks measurement`) |
| `L1.20` | ~1690 | auto-affermazione **semantica multilingue** (chiude il buco «8 lingue su 10» delle famiglie EN/IT) |
| `L1.21` | 1677 | (da mappare nel giro 2) |

📌 **La forma di dodici di questi è la stessa** — «cycle 2026-05-27 round 1..11»: sono
nati in un pomeriggio come famiglia di parole chiave. `L1.20` è l'unico semantico, ed è
nato perché la famiglia lessicale **non copriva 8 lingue su 10**.

---

## 4. I quattro `L4-skipped`, cioè i quattro modi di NON giudicare

Righe 1907, 1944, 1954, 1963 — e le loro `reason` sono diverse di proposito:

    1907  source provided but the grounding judge was still …   (warming)
    1944  source provided but the grounding judge failed to …   (failed, in processo)
    1954  source provided but the grounding judge failed to load - …
    1963  source provided but no grounding judge is available - …

⇒ **Quattro stati distinti**, perché mandano chi legge a fare cose diverse. È l'unico punto
del file dove l'assenza di un verdetto viene raccontata invece che taciuta — e nella
ricevuta della porta MCP quella distinzione arriva (vedi `mcp_server` nel giro 2).

---

## 5. Le 42 funzioni — dove sono e cosa presidiano

Il conteggio della superficie combacia col mandato: **3.380 righe, 42 funzioni**
(`ast`, non grep). Il dettaglio funzione-per-funzione è il **giro 2** di questo file:
qui è mappata la struttura che serve a leggere una ricevuta.

---

## 6. Quello che questa mappa NON dice ancora — dichiarato

- **`L1.21` e `L1.5`/`L1.7`**: le sigle esistono, la riga `L1|L1.5|L1.7|L3` a 356 le
  raggruppa, ma **non ho ancora letto cosa fermano**. Giro 2.
- **La precisione di ciascun detector**: non misurata qui. Il team ha un numero
  complessivo per L1 (~40%, @ws1/@ws4) ma **non per singolo layer**, e senza quello non si
  sa quale dei 14 produce i falsi positivi.
- **Se ogni layer emesso sia raggiungibile**: nessuna prova che tutti e 28 possano
  accendersi davvero su un input reale. Un layer irraggiungibile sarebbe indistinguibile
  da uno che non scatta mai.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I comandi che producono ogni tabella sono nel testo.*
