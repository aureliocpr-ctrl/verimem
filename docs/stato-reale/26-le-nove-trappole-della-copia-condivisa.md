# 26 — Le nove trappole della copia condivisa

**ws6 · 30/08** · nessuna è ipotizzata: **le ho pagate tutte oggi, in prima persona**, e sei di esse
mi hanno fatto credere una cosa falsa per almeno qualche minuto.

Otto istanze condividono **un albero git, un indice, un pre-commit e uno store**. Le trappole che
seguono non sono difetti del prodotto: sono **il prezzo della copia condivisa**, e chi arriva le
paga tutte da capo se nessuno le scrive.

---

## 🔴 La famiglia che costa di più: i controlli indiretti che dicono di NO quando è SÌ

**Tre falsi negativi in un giorno, tutti su un proxy invece che sulla cosa:**

**①** **`origin/main` locale è STALE.** `git merge-base --is-ancestor <sha> origin/main` **nega un
commit che è su origin**, perché il ref locale non è aggiornato. ⇒ **`git fetch` prima**, sempre.

**②** **Dopo un `pull --rebase` il tuo SHA non è più il tuo.** Il rebase riscrive il commit con un
altro identificatore: `merge-base` sul vecchio SHA dà **EXIT=1 su lavoro che è arrivato**.

**③** **`grep` è case-sensitive.** Verificando un documento appena pushato con
`grep -c "nessuno dei tre..."` ho ottenuto **0**: nel file la frase comincia con la **maiuscola**.
Sembrava un push fallito. ⇒ **`grep -i`**, e meglio contare una stringa che non dipende dalla
formattazione.

🔑 **La regola che ne segue: quando un controllo indiretto dice di no, sospetta il controllo prima
della cosa.** E verifica **il contenuto**, non l'identificatore:

```bash
git show origin/main:<file> | grep -c -i "<una frase del file>"
```

---

## Git — e una che è a metà

**④** **L'INDICE è condiviso.** Al tuo commit possono esserci **file di altre istanze già staged**:
committare senza pathspec porta su origin **il loro lavoro in corso**. ⇒ **sempre
`git commit -F msg -- <solo il mio path>`**.
*(Il 30/08 un mio file in `tests/` ha fatto rifiutare un commit di ws8, e una sua cella è finita su
origin dentro un commit altrui.)*

**⑤** **`git commit -- <path>` funziona SOLO su file già tracked.** Su un file nuovo dà «pathspec did
not match» — **l'errore viene stampato**, ma se hai `| tail` nella catena **l'exit code è mascherato
e i comandi dopo `&&` proseguono** come se fosse andata bene. ⇒ `git add` prima; e **cattura l'exit
subito**: `cmd >out 2>&1; RC=$?`, **mai riusare `${PIPESTATUS[0]}` più avanti** (dopo un `echo` si
riferisce all'`echo`).

---

## Il pre-commit

**⑥** **Guarda anche gli UNTRACKED.** Un file di lavoro non pronto in `tests/` **blocca i commit di
tutte**, comprese le istanze che non l'hanno mai visto. ⇒ **i file non verdi stanno fuori
dall'albero** finché `ruff` non passa.
🔑 **Il TDD chiede un test ROSSO, non un file SPORCO**: il rosso sta nell'**esito**, non nel lint —
un test RED passa benissimo `ruff`.

**⑦** **Cambia sotto i piedi, e linta `verimem tests scripts` ma NON `docs/`.** Alle 14:28 bloccava
per due errori non miei, alle 14:32 era pulito; alle 18:14 di nuovo, sbloccato in dieci minuti.
⇒ **se blocca su path che non hai toccato, è di un'altra istanza: non toccarlo, segnalalo e
riprova.** *(Verificato che `docs/` non è lintato: un banco già in main ha 8 errori ruff ed era
passato «lint clean».)*

---

## Le porte del prodotto

**⑧** **Le due porte di lettura non usano lo stesso nome per il limite**: `hippo_facts_search` vuole
`limit`, **`hippo_facts_recall` vuole `k`** — e con `limit` il parametro è **ignorato in silenzio**
(tornano 5 risultati, il default). `hippo_remember` vuole **`proposition`**, non `content`: con
`content` risponde «Input validation error», e si finisce per misurare su uno store vuoto credendolo
pieno.

**⑨** **Il gate non traduce.** La `--source` va in **prosa** (quella tabellare fa quarantinare) e i
numeri vanno scritti **in cifre come nel claim**: «settanta» nella fonte e `70` nel claim **non si
agganciano**.

---

## 🪞 Cosa dice il conto — e cosa è successo a me

**5 silenziose** (①, ②, ④, ⑧, e il `%s`/`%%s` qui sotto) · **3 rumorose** (⑥, ⑦, ⑨: fanno male ma lo
dicono, e la causa si trova subito) · **1 a metà** (⑤).

*(Annunciandole sul canale avevo scritto «sette su nove sono silenziose». **Non l'avevo contata.**
Sono cinque — e una sintesi è un numero come gli altri.)*

⚠️ **Bonus Python**: in una stringa **non interpolata** scrivi `%s`, non `%%s`. `strftime('%%s', …)`
riceve un formato invalido e torna **zero righe**: mi ha dato `n=0` su una query che doveva darne
**563**, e **mi ha salvato solo che il numero fosse palesemente impossibile**.

### Le due volte in cui ci sono ricascato dopo averle scritte

· **Un'ora dopo** aver scritto la trappola su `PIPESTATUS`, l'ho riusata dopo un `echo`: **l'avviso
  che stavo mandando al canale non è partito**, e io credevo di averlo mandato.
· **Dieci minuti dopo** aver pubblicato il documento sui numeri in lettere, **il gate mi ha
  quarantinato tre fatti su quattro** esattamente per quel motivo.

🔑 **Scrivere una lezione non la applica.** Ed è la ragione per cui questo file sta qui e non solo
nella memoria di una sessione: **quello che non è nel registro, il turno dopo non esiste.**
