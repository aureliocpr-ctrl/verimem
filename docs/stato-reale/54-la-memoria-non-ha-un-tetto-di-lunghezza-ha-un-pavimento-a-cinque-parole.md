# 54 — La memoria non ha un tetto di lunghezza: ha un pavimento a cinque parole (e il topic ci sta sotto)

*ws6/Aldo — 31 agosto 2026, notte. Chiude il limite dichiarato nel [51](51-ho-scritto-settanta-fatti-e-ne-ritrovo-il-nove-per-cento.md).*

Il documento `51` finiva con una riga di debito: *«la misura che manca: la
stessa cosa con query costruite dal **contenuto** invece che dal topic»*. Era il
limite più importante che avessi lasciato aperto, perché senza quella misura il
`51` si poteva leggere come *«i miei fatti non si ritrovano»* — e **non è vero.**

## ① I fatti si ritrovano. È il topic che non li ritrova

Stessi 66 fatti vivi, stessa attesa, `k=10`. Cambia solo **come si costruisce la
domanda**:

| | query costruita da… | ritrovati |
|---|---|---|
| **A** | il **topic** in parole | **8/66 = 12,1%** |
| **B** | un **frammento di 7 parole** della frase | **66/66 = 100%** |
| **C** | la **proposizione intera** | 63/66 = 95,5% |

**Zero corse degradate su 198**, quindi il confronto è a regime pieno.

⇒ **Il `51` non aveva trovato una memoria che perde i fatti: aveva trovato una
CHIAVE che non li apre.** Chiedendo il contenuto tornano tutti.

## ② L'ipotesi che mi sono fatto era sbagliata, e il banco l'ha detto

**B (100%) faceva meglio di C (95,5%)**, cioè il frammento batteva la frase
intera. Il caso più facile che perde: sembrava un reperto. **Ipotesi: esiste una
lunghezza di query oltre la quale il recall peggiora** — plausibile, c'è persino
un `rerank: skipped_long_query` nel prodotto.

Ho misurato la curva: stesso fatto, stessa attesa, **solo la lunghezza cambia**
(22 fatti da almeno 20 parole).

| parole nella query | trovati | **al primo posto** | punteggio medio |
|---|---|---|---|
| 3 | **6/22 = 27%** | 2/22 | 0,8409 |
| 5 | 21/22 = 95% | 7/22 | 0,8503 |
| 7 | **22/22 = 100%** | 15/22 | 0,8668 |
| 10 | 22/22 = 100% | 20/22 | 0,8919 |
| 15 | 21/22 = 95% | 20/22 | 0,9248 |
| frase intera | 21/22 = 95% | **21/22 = 95%** | 0,9507 |

**Nessun ginocchio. L'ipotesi è falsificata**: da 7 parole in su il ritrovamento
resta fra 95% e 100%, e **il rango migliora in modo monotono** (2 → 7 → 15 → 20
→ 20 → **21 primi posti su 22**), come il punteggio (0,84 → 0,95).

🪞 **E la differenza B/C che mi aveva incuriosito era rumore.** Su 66 casi, 100%
contro 95,5% sono **tre fatti**; sulla curva, 22/22 contro 21/22 è **un caso
solo**. La mia memoria porta questa lezione scritta — *«una proporzione senza
intervallo invita a spiegare il rumore»* — e stavo per spiegarlo comunque. **Il
banco è servito a fermarmi, non a confermarmi.**

## ③ Il dato vero sta dall'altra parte: sotto le 5 parole si crolla

Quello che la curva mostra davvero non è un tetto, **è un pavimento**:

```
3 parole -> 27%      5 parole -> 95%      7 parole -> 100%
```

**68 punti fra 3 e 5 parole.** Questo *non* è rumore: è un salto che nessun
intervallo di confidenza su 22 casi può assorbire, ed è tutto concentrato in due
parole di differenza.

## ④ E qui si spiega il 12,1% del `51`

I nomi dei topic sono **corti**: `pavimento-persistito`,
`cura-avviso-verificata`, `supersessione-misura` — due, tre, al massimo quattro
parole una volta sciolti i trattini.

⇒ **Interrogare per topic significa interrogare con una query da 2-4 parole,
cioè esattamente sotto il pavimento.** Il 12,1% del braccio A non è un mistero
del corpus né una colpa della supersessione: **è il regime «3 parole», che
misurato in isolamento dà 27%.**

**Le due misure si spiegano a vicenda, e nessuna delle due da sola lo diceva.**

## ⑤ Che cosa se ne fa, chi usa il prodotto

- **Chiedere con una frase, non con un'etichetta.** Sette parole di contenuto
  ritrovano tutto; il nome della categoria no.
- **Le parole in più non fanno danno**: il punteggio e il rango migliorano fino
  alla frase intera. Non c'è nessuna ragione, in questi dati, per accorciare una
  domanda.
- **Un `topic` resta ottimo per FILTRARE** (`count(topic=…)`, `topic_prefix`) e
  pessimo come **testo di ricerca**. Sono due cose diverse, e il `51` mostrava
  solo la seconda.

## ⑥ Limiti dichiarati

- **22 fatti** nella curva (quelli lunghi almeno 20 parole), 66 nel confronto
  A/B/C. Piccolo: sostiene il salto da 68 punti, **non** differenze di pochi
  punti — che infatti ho smesso di interpretare.
- **La riga «30 parole» del banco ha n=3** e non la riporto in tabella: tre casi
  non dicono niente, e tenerla accanto alle altre l'avrebbe fatta sembrare una
  misura.
- **I fatti sono i miei**, scritti stanotte: prosa densa di numeri e nomi
  propri. Su un corpus di testo più discorsivo il pavimento può stare altrove.
- **`k=10`**: «trovato» significa dentro i primi dieci. Con `k=5` i numeri di
  coda scenderebbero.
- **Non ho misurato query riformulate** — parole *diverse* da quelle del fatto,
  che è il caso dell'utente vero. Qui il frammento usa le parole del fatto:
  è un caso favorevole, e lo dichiaro invece di spacciarlo per il caso generale.

---
*Banchi: `banchi/ws6-ritrovabili-dal-contenuto.py`, `banchi/ws6-curva-lunghezza-query.py`.
Store di Aurelio in sola lettura (la recall è una lettura); nessuna scrittura.*
