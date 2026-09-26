# T79 — la scomposizione della perdita sta in due script che divergono, e il prodotto la calcola già

*Ruolo Dati, 13 settembre 2026. Tutti i numeri qui sotto sono stati eseguiti
sul corpus di casa in sola lettura; i comandi sono scritti accanto a ciascuno.*

---

## 1. Il sintomo: lo stesso corpus, due numeri per la stessa cosa

La sera del 12 settembre la stessa grandezza — «la potatura voluta» — è stata
letta **8,1%** da uno script e **9,2%** dall'altro, a venti minuti di distanza e
sullo stesso database. Nessuno dei due dichiara quali voci mette dentro.

```
scripts/di_cosa_e_fatta_la_perdita.py     autohook-snapshot   1463   8,1%
scripts/le_tre_misure_del_contratto.py    potatura VOLUTA     1665   9,2%
```

Differenza: **202**, cioè la deduplicazione del testo identico, che il secondo
script somma alla potatura e il primo tiene separata. La stessa quantità esce
poi dalla colonna del **curabile**, che passa da 5,2% a 4,0%. Un movimento
solo, due numeri che si muovono, e nessuna riga che lo dica a chi legge.

## 2. La causa non è «due script»: è che il prodotto lo calcola già

`verimem facts retirement-log --breakdown` **stampa la scomposizione**, per
motivo e per giorno, con la concentrazione. Eseguito il 13 settembre:

```
2414 retired total
    1463  autohook-snapshot daily collapse (kept the day's last snapshot; …)
     530  same-source evolution
     202  exact-text dedup (corpus truth scan 2026-07-02; byte-identical …)
     196  heal_contradictions: numeric_clash …
       6  heal_contradictions: boolean_clash …
       …
— by day —
    1665  2026-07-02
```

Due script riscrivono a mano una query che esiste, e divergono nel farlo. È la
classe «una copia invece della superficie unica», con l'aggravante che la
superficie buona **è già quella del prodotto**: un utente che volesse la stessa
risposta la otterrebbe meglio di noi.

## 3. Ciò che nessuna delle tre superfici dice, e cambia la lettura

⚠️ **Due delle quattro voci non sono un tasso: sono un evento.** Misurato:

| voce | quanti | in quanto tempo |
|---|---|---|
| autohook-snapshot | 1463 | **35,9 secondi** (2 luglio, 23:37:14 → 23:37:50) |
| exact-text dedup | 202 | **1 giorno** (2 luglio) |
| same-source evolution | 530 | 36 giorni (24 luglio → 9 settembre) |
| heal_contradictions | 202 | 32 giorni (20 giugno → 10 settembre) |

E i 1463 sono fatti **scritti fra il 25 maggio e il 1° giugno**: la finestra si
è chiusa tre mesi e mezzo fa, e per questo il numero è identico a tre giorni di
distanza — non è fermo per caso, non può crescere.

⇒ **1665 dei 3828 perduti — il 43,5% — vengono da 36 secondi del 2 luglio**, su
materiale di maggio. La misura che leggiamo come «un quarto della memoria non
risponde» contiene quasi metà di una potatura una tantum, e il suo stesso nome
lo diceva: *«autohook-snapshot daily collapse — kept the day's last snapshot»*.

🔑 La riga per giorno del prodotto (`1665 2026-07-02`) dice questo in una riga
sola, e nessuno dei due script la legge.

## 4. Che cosa chiude questo ticket

1. **Una superficie sola**: gli script prendono la scomposizione dal prodotto
   (`retirement_log.retirement_breakdown`, quella che alimenta `--breakdown`)
   invece di riscrivere la query. Se manca un taglio, si aggiunge **lì**.
2. **Ogni voce dichiara se è un tasso o un evento**: quanti giorni distinti la
   compongono e la quota del giorno più denso. Il dato c'è già nel breakdown
   (`by_day`, `concentration`): va portato accanto alla percentuale, non in
   fondo.
3. **Il denominatore dichiarato accanto al numero**: «8,1% di che cosa» oggi si
   ricava leggendo il sorgente.

## 5. Il controllo che dice se il ticket è chiuso

Dopo la cura, i due script e il prodotto, interrogati **nella stessa
esecuzione**, devono dare per ogni voce lo **stesso numero**; e una voce
composta da un giorno solo deve risultare marcata come evento in tutte e tre le
uscite. Se una sola delle tre dice ancora 8,1 dove le altre dicono 9,2, la cura
non è avvenuta: è stata spostata.

## 6. Il bersaglio: decisione PRESA, non aperta

**Deciso dal ruolo di controllo il 13 settembre 2026, col mandato**: il
bersaglio «≤2%» si applica ai **persi senza ragione**, non a tutti i perduti. La
grandezza da riportare è quindi:

| | oggi | |
|---|---|---|
| **perdita in corso, curabile** | **4,0%** | 530 evoluzioni della stessa fonte + 202 riparazioni di contraddizione |
| fermati dal giudice, per regola | 7,8% | 1414: è la promessa del prodotto, non un difetto |
| l'evento del 2 luglio | 9,2% | 1463 potature + 202 duplicati esatti, in 36 secondi, su fatti di maggio |

⇒ Il bersaglio riguarda la prima riga: **4,0% da portare a ≤2%**, ed è una
misura che si può muovere curando ciò che la produce. Le altre due non vanno
spinte verso il basso: la seconda scenderebbe solo servendo fatti che il gate
ha fermato, la terza è chiusa da luglio e non può muoversi.

⚠️ **«Il 21% è stabile» era vero e ingannava.** Vero perché il numero non si
muoveva; ingannava perché due terzi di quel numero non descrivevano niente di
ciò che succede oggi. È la forma «un numero vero che inganna» già catalogata su
questo prodotto: il numeratore senza il denominatore, e qui anche senza la
finestra temporale.

## 7. Che cosa questo ticket NON fa

Non tocca gli script: i due che divergono non sono in `main` e vivono su rami
aperti. La cura qui è **togliere la ragione di scriverli** — la scomposizione
completa la dà il prodotto, con la forma e il denominatore — e chi porta quei
rami dentro li fa chiamare invece di ricalcolare. Un cricchetto che vieti il
ricalcolo si scriverà quando ci sarà un ricalcolo da vietare in `main`: oggi
sorveglierebbe il nulla.
