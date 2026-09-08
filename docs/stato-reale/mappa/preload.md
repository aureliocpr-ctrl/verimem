# `verimem/preload.py` — 387 righe, 11 funzioni

**Quello che il server fa PRIMA di servire.** Una sola funzione pubblica su undici:
`preload_embedding` (242). Tutto il resto è privato — il file è una scatola con un
interruttore. Mappato su `7b9e8ca1`.

---

## 1. Cosa parte, e su quale thread — la tabella che serviva

`preload_embedding()` si comporta in due modi opposti secondo `HIPPO_PRELOAD_BACKGROUND`:

| chi | thread | quando |
|---|---|---|
| `_scalda_le_librerie_del_giudice` (137) | **CHIAMANTE, sempre** | prima di tutto |
| `_run` → embedder (295) | sfondo `hippo-embedding-preload` | sempre (o sincrono col flag a 0) |
| `_warm_reranker` (78) **oppure** `_segnala_rerank_delegato` (51) | sfondo | opt-in `HIPPO_RERANK_PRELOAD` |
| `_warm_moat_judge` (119) | sfondo `verimem-moat-judge-preload` | **solo se** `_deve_scaldare_il_giudice` |

⇒ **fino a quattro thread** nel ramo di sfondo. È la struttura dietro T1b e T26a.

## 2. 🔑 L'unica riga sincrona è la cura di T1b — e costa meno di quanto sembra

`_scalda_le_librerie_del_giudice` è **fuori** dal thread di sfondo dal 06/09. Misurato da me
l'08/09 in un processo pulito:

    _scalda_le_librerie_del_giudice (a freddo): 1.55 s
    _scalda_le_librerie_del_giudice (a caldo):  0.00 s

E dentro il preload completo del giudice (41,6 s totali) **quella riga pesa 1,3 s**: il
costo è il modello, non la cura. Il suo docstring spiega il meccanismo vero — `scipy.linalg`
**trascina** `numpy.random`, che è il modulo dentro cui la richiesta si fermava — quindi la
cura **elimina** la corsa invece di vincerla.

## 3. ⚠️ Il commento che dichiara come virtù ciò che causava un difetto

Riga ~374, sul thread del giudice:

> *«Il giudice del moat, sul SUO thread: **modello e lock diversi** dall'embedder e dal
> reranker, quindi scaldarlo qui non blocca né recall né save.»*

Vero per il **blocco**, e **falso per la corsa**: lock diversi vuol dire **nessuna
serializzazione**, ed è esattamente ciò che faceva fallire l'import del giudice (T26a, curato
oggi in `cd644eff` mettendo `sentence_transformers` sotto lo stesso `lock_import`). Il
commento va aggiornato: oggi dice a chi legge che la separazione è una garanzia, mentre era
la causa.

📌 **Non l'ho cambiato**: è una riga di prosa dentro un file appena entrato in main col push
delle 20:35, e va fatto insieme alla cura di T40. **Lo segnalo come debito con owner: mio.**

## 4. `_deve_scaldare_il_giudice` (101) — il gate che decide chi paga

> *«Chi non accende il moat sul write non paga niente. Assente = NO: solo una scelta
> esplicita compra il modello.»*

Legge `ENGRAM_GROUNDING_WRITE`. È il motivo per cui **la mia obiezione delle 13:30 era mal
mirata**: i 13,8 s di `import transformers` non si aggiungerebbero a *ogni* avvio, perché in
quel ramo il modello si carica comunque. Vale la pena rileggerlo prima di discutere il costo
di un pre-import.

📌 Il costo è scritto nel file come numero, non come aggettivo: `_COSTO_DEL_GIUDICE_MB = 486`,
con la ragione — *«chi paga mezzo giga per processo deve poterlo LEGGERE, non dedurlo»*.

## 5. `_dichiara_il_piano_del_giudice` (215) — l'avvio dice cosa farà

Emette `mcp_preload_moat_judge_planned` **o** `..._skipped`, col costo e con la leva per
cambiarlo. Esiste perché prima *«non compariva NESSUNA riga sul giudice»* e **il silenzio si
legge come "tutto a posto"**. È la stessa forma curata oggi nella ricevuta MCP (`judged` in
cima): un'assenza dichiarata invece che dedotta.

## 6. Le 11 funzioni

**Pubblica (1)**: `preload_embedding`.
**Private (10)**: `_warm` · `_segnala_rerank_delegato` · `_warm_reranker` ·
`_deve_scaldare_il_giudice` · `_warm_moat_judge` · `_service_enabled` ·
`_scalda_le_librerie_del_giudice` · `_dichiara_il_piano_del_giudice` · `_run` ·
`_run_reranker`.

---

## 7. Quello che questa mappa NON dice — dichiarato

- **`_segnala_rerank_delegato` e `_warm_reranker`**: letti nei docstring, **non esercitati**.
  Il primo dichiara «nessun modello caricato», il secondo carica ~450 MB: la differenza è il
  default (`HIPPO_RERANK_PRELOAD` è off), ma **non ho verificato** che il default sia quello
  in tutti i punti d'ingresso.
- **`_DAEMON_WARM_WAIT_S`**: il preload aspetta il daemon per un tempo che non ho misurato.
- **Non ho verificato** che i quattro thread non possano partire tutti insieme su una
  macchina lenta: la mappa dice che *possono*, non cosa succede se lo fanno.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I numeri di §2 sono miei, misurati l'08/09; quelli di
§4 vengono dal file.*
