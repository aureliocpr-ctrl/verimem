# ⑨ — Una `search` con le impostazioni di default paga 32 cold-load del cross-encoder

> **ws2 «Vega» · 09/08 ore 22:50–23:50 · misurato su `603c564c` (09/08 22:13) in worktree
> separato, `git status` vuoto · store isolato per ogni esecuzione**
> L'SHA da solo scadrebbe — main si è mosso tre volte mentre scrivevo. Vale anche su
> `ce690551`: `git diff 603c564c ce690551 -- verimem/client.py verimem/semantic.py` → **0 righe**.
> *Non «l'ho misurato lì», ma «lì e in tutto ciò che non ha toccato questi due file».*
> Nato da due test rossi in `tests/test_rerank_auto_default.py`, uno dei quali l'avevo scritto
> io. Chiuso dopo **10 esecuzioni e 7 ipotesi**, di cui una era vera e l'avevo scartata per un
> errore mio.

---

## Il difetto, in due righe

```
m.search(Q, k=3)                      →  load = 32
m.search(Q, k=3, min_relevance=0)     →  load =  0
```

Senza un `min_relevance` esplicito, `Memory.search` calibra il pavimento di rilevanza
(`client.py:976`, e la funzione è a `client.py:2189`) e **il calibratore carica il
cross-encoder 32 volte**. Non è un'inferenza: il docstring di `_auto_relevance_floor` lo scrive
da sé, a `client.py:2200` —

> *«La stima fa ~32 recall di sonde giudicati dal cross-encoder»*

📌 E non è un solo chiamante: `_auto_relevance_floor()` compare a **976, 1134 e 1554**. Ho
misurato la porta `search`; le altre due non le ho misurate.

## Perché il gate AUTO non lo ferma

Il gate esiste esattamente per questo — salta il CE quando non serve, «*skip BEFORE any
load/slot/breaker touch*», per non pagare i **43,6 s** di cold-load. E sulla query dell'utente
funziona:

```
VAL mode='auto'  words=18  max=10        ← la condizione è VERA, il gate scatta
```

Ma le 32 sonde **non sono la query dell'utente**: sono frammenti dei fatti nello store,
generati per calibrare.

```
STAGE2 query='Amazon Paris. river. Tower for work'       parole=6
STAGE2 query='Marie won The Paris. other than'           parole=6
STAGE2 query='Amazon River vit wrought-iron Nobel Pari'  parole=6
```

**Sei parole: sotto la soglia di dieci.** Ognuna passa il gate legittimamente, ognuna carica.

🔑 **Il gate protegge la query dell'utente e non le 32 che il prodotto si fa da solo.** Non è
rotto e non è inerte: è che nessuno ha guardato il costo del calibratore attraverso di lui.

## Cosa NON è

* ❌ un test da aggiustare — il test dichiara «query lunga in auto → il CE non deve essere
  caricato», e il CE viene caricato. Ha ragione.
* ❌ una regressione del gate — le tre funzioni che lo decidono (`_rerank_mode`,
  `_rerank_auto_max_words`, `_query_word_count`) hanno `diff` **vuoto** fra il commit dove i
  test passavano (27/07) e oggi.
* ❌ un motivo per spegnere il pavimento — ws5 ha misurato che serve, e le sue misure reggono.
  **Il costo semplicemente non era noto. Adesso ha un numero.**

## Le sette ipotesi, e perché tenerle scritte

| # | ipotesi | esito |
|---|---|---|
| ① | l'import di `rerank_candidates` finito sopra il gate | identico nei due alberi |
| ② | la giuntura col daemon del CE (`93cfdf28`) | caduta — **mio errore di disegno** |
| ③ | le `mem.add()` del setup | `load=0` prima della search |
| ④ | il gate rotto | `diff` vuoto sulle tre funzioni |
| ⑤ | `search` non passa più dal gate | stessi chiamanti di `_rerank_stage2` |
| ⑥ | il gate valuta falso | valuta **vero** (18 > 10) |
| ⑦ | **il calibratore del pavimento** | **VERA — e l'avevo scartata** |

**La ⑦ è la lezione.** L'avevo testata con `ENGRAM_MIN_RELEVANCE=off` nell'ambiente e avevo
scritto sul canale «caduta, A/B a un fattore». Ma il default sta nella **firma del metodo**
(`min_relevance="auto"`), che nessuna variabile d'ambiente tocca: il mio A/B aveva **il fattore
sbagliato**, e per venti minuti ho lasciato in giro una conclusione falsa.

Due delle sette sono cadute per errori miei di disegno — la ② (ho copiato un file di test su un
albero vecchio *senza la cura in `semantic.py` che lo accompagna*, quindi falliva per il codice
mancante) e la ⑦. Le altre cinque erano ragionevoli e sbagliate.

🔑 **Un «A/B a un fattore» è forte solo quanto la certezza di quale sia il fattore.** Cambiare
la variabile d'ambiente sbagliata dà un A/B perfettamente eseguito su nulla — e sembra una
falsificazione, che è peggio di non averla fatta.

## Il metodo che ha funzionato, quando le ipotesi non funzionavano

Tre sonde, ognuna inserita e **rimossa** subito (`git status` verificato pulito dopo ognuna):

1. **contatore prima/dopo** — `load=0` dopo il setup, `load=32` dopo la search: esclude il setup
   senza bisogno di capire il codice.
2. **stack trace dentro il monkeypatch** — dice *da dove* arrivano, non *perché*: `semantic.py:4547`
   dentro un thread, e poi `semantic.py:4255:recall`.
3. **stampa della query** a ogni chiamata — ed è quella che ha risolto, perché ha mostrato che le
   query **non erano quella che avevo dato io**.

📌 Le prime due dicevano *dove*; la terza ha detto *che cosa*. Cercavo la causa nel percorso, ed
era nell'**input**.

---

**Per chi raccoglie**: ws4 (fronte velocità) può vederlo dalla telemetria — 32 recall di sonda
per una `search` sono un segnale forte. ws5 (fronte astensione) ha il pavimento nel proprio
perimetro, e questo ne è il prezzo.

**Caveat**: una macchina, Windows, Python 3.13, un corpus di 3 fatti. Il «32» viene dal docstring
*e* dalla misura, ma non ho verificato se scali col corpus. E non ho misurato il **tempo** delle
32 sonde: che siano 32 cold-load è misurato, che costino 43,6 s l'uno è il numero del commento
del gate, non mio.
