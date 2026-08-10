# ⑨ — Una `search` con le impostazioni di default paga 32 cold-load del cross-encoder

> **Artefatto**: misurato su `603c564c`; vale anche su `ce690551` —
> `git diff 603c564c ce690551 -- verimem/client.py verimem/semantic.py` → **0 righe**.
> Non «misurato su un commit», ma «su quel commit e su tutto ciò che non tocca questi due file».
> Store isolato per ogni esecuzione, `git status` vuoto, worktree separato.

---

## Il difetto

```
m.search(Q, k=3)                      →  load = 32
m.search(Q, k=3, min_relevance=0)     →  load =  0
```

Senza un `min_relevance` esplicito, `Memory.search` calibra il pavimento di rilevanza
(`client.py:976`; la funzione è a `client.py:2189`) e il calibratore carica il cross-encoder
32 volte. Il docstring di `_auto_relevance_floor` lo dichiara, a `client.py:2200`:

> *«La stima fa ~32 recall di sonde giudicati dal cross-encoder»*

`_auto_relevance_floor()` ha tre chiamanti — `976`, `1134`, `1554`. La misura riguarda la porta
`search`; gli altri due non sono stati misurati.

Il numero 32 non viene solo dal docstring: è il default nella firma della funzione che genera le
sonde, `relevance_floor.py:139` — `scrambled_probes(sm, *, n: int = 32, seed: int = 0)`. Il modulo
`relevance_floor.py` è presente anche nel wheel 0.7.0 pubblicato.

## Quante volte si paga: la doppia cache ridimensiona il titolo

Il costo **non è a ogni `search`**. `_auto_relevance_floor` è protetta da due cache:

```
client.py:2113   _FLOOR_CACHE_TTL_S = 300.0     cache in memoria, 5 minuti
client.py:2118   _FLOOR_DRIFT       = 0.05      il valore su file è riusato finché
client.py:2238   abs(n - n_salvato) <= max(1, n_salvato) * _FLOOR_DRIFT
```

Le 32 sonde si pagano quando **entrambe** mancano: primo calcolo su uno store nuovo, cache in
memoria scaduta, oppure conteggio dei fatti spostato oltre il 5% rispetto al valore salvato.
La misura riportata sopra è stata eseguita su store isolato e nuovo: è quindi il **caso peggiore**,
non il regime.

Il costo però non è nemmeno «una volta sola». Con `_FLOOR_DRIFT = 0.05` la soglia è
**proporzionale**: su uno store di 250 fatti bastano circa 13 scritture per invalidare il file e
ripagare le 32 sonde. Su uno store in scrittura continua il costo ricorre a ogni +5% di fatti.

## Perché il gate AUTO non le ferma

Il gate salta il cross-encoder quando non serve, «*skip BEFORE any load/slot/breaker touch*», per
non pagare i 43,6 s di cold-load. Sulla query dell'utente la condizione è vera e il gate scatta:

```
VAL mode='auto'  words=18  max=10
```

Le 32 sonde non sono la query dell'utente: sono frammenti dei fatti nello store, generati per
calibrare.

```
STAGE2 query='Amazon Paris. river. Tower for work'       parole=6
STAGE2 query='Marie won The Paris. other than'           parole=6
STAGE2 query='Amazon River vit wrought-iron Nobel Pari'  parole=6
```

Sei parole, sotto la soglia di dieci: ognuna passa il gate legittimamente e ognuna carica.

**Il gate protegge la query dell'utente, non le 32 che il prodotto genera per sé.** Non è rotto e
non è inerte: il costo del calibratore non era mai stato osservato attraverso di lui.

## Cosa non è

* **Non è un test da aggiustare.** Il test dichiara «query lunga in auto → il cross-encoder non
  deve essere caricato», e il cross-encoder viene caricato.
* **Non è una regressione del gate.** Le tre funzioni che lo decidono — `_rerank_mode`,
  `_rerank_auto_max_words`, `_query_word_count` — hanno `diff` vuoto fra il commit del 27/07, dove
  i test passavano, e oggi.
* **Non è un motivo per spegnere il pavimento**, che è misurato e serve. Il costo non era noto e
  ora ha un numero.

## Le ipotesi scartate

| # | ipotesi | esito |
|---|---|---|
| ① | l'import di `rerank_candidates` finito sopra il gate | identico nei due alberi |
| ② | la giuntura col daemon del cross-encoder (`93cfdf28`) | caduta per errore di disegno del banco |
| ③ | le `mem.add()` del setup | `load=0` prima della search |
| ④ | il gate rotto | `diff` vuoto sulle tre funzioni |
| ⑤ | `search` non passa più dal gate | stessi chiamanti di `_rerank_stage2` |
| ⑥ | il gate valuta falso | valuta vero (18 > 10) |
| ⑦ | **il calibratore del pavimento** | **confermata** |

L'ipotesi ⑦ era stata scartata una prima volta usando `ENGRAM_MIN_RELEVANCE=off`: il default sta
nella firma del metodo (`min_relevance="auto"`) e nessuna variabile d'ambiente lo tocca.
L'esperimento aveva quindi il fattore sbagliato.

**Un A/B a un fattore vale quanto la certezza su quale sia il fattore.** Cambiare la variabile
d'ambiente sbagliata produce un esperimento formalmente corretto su nulla, e ha l'aspetto di una
falsificazione riuscita.

L'ipotesi ② è caduta per la stessa ragione: il file di test era stato copiato su un albero più
vecchio senza la cura in `semantic.py` che lo accompagna, quindi falliva per il codice mancante e
non per la causa in esame.

## Il metodo che ha isolato la causa

Tre sonde, ognuna inserita e rimossa subito, con `git status` verificato pulito dopo ognuna:

1. **contatore prima/dopo** — `load=0` dopo il setup, `load=32` dopo la search: esclude il setup
   senza richiedere la lettura del codice.
2. **stack trace nel monkeypatch** — indica la provenienza: `semantic.py:4547` dentro un thread,
   poi `semantic.py:4255:recall`.
3. **stampa della query a ogni chiamata** — mostra che le query non sono quella passata in
   ingresso. È la sonda che ha risolto.

Le prime due dicono *dove*; la terza dice *che cosa*. La causa era nell'input, non nel percorso.

---

**Rilevanza per altri fronti**: il fronte velocità può osservarlo dalla telemetria — 32 recall di
sonda per una `search` sono un segnale forte; il fronte astensione ha il pavimento nel proprio
perimetro e questo ne è il prezzo.

**Caveat**: una macchina, Windows, Python 3.13, un corpus di 3 fatti. Il valore 32 viene dal
docstring e dalla misura, ma non è verificato se scali col corpus. Il tempo delle 32 sonde non è
stato misurato: che siano 32 cold-load è misurato; il costo di 43,6 s l'uno è il numero riportato
nel commento del gate.
