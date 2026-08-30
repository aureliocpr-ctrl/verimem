# 53 — Il pavimento si ripara da solo fra 105 fatti, e quel giorno taglia il 98% del traffico

*ws6/Aldo — 31 agosto 2026, notte. Seguito diretto del [48](48-ventitre-minuti-senza-daemon-hanno-spento-una-promessa-del-readme.md).*

Il documento `48` chiude con un fatto: `semantic.db.floor.json` contiene
`{"floor": 0.0, "n_facts": 13795}`, scritto alle 20:32 dentro la finestra senza
daemon, e **quattro ore dopo — daemon warm, 16654 vettori riallineati, zero
fatti non giudicati nell'ultima ora — è ancora lì**. Lì avevo scritto che
sarebbe rimasto «finché non entrano ~600 fatti».

**Quel numero era una stima, e stimare quando puoi contare è un errore.** Ho
contato. Il risultato non è un dettaglio: cambia la natura del reperto da
«difetto che aspetta una decisione» a **«guasto con una scadenza vicina, che si
rompe dall'altra parte»**.

## ① Il margine è di 105 fatti vivi, non di 600

`client.py` decide se fidarsi del valore salvato così:

```python
n = int(self.semantic.count())
...
if abs(n - n_salvato) <= max(1, n_salvato) * self._FLOOR_DRIFT:
    self._floor_cache = (now, salvato)
    return salvato
```

`_FLOOR_DRIFT = 0.05` ⇒ tolleranza `13795 × 0,05 = 689,8`. La stima da «~600»
veniva da qui. Ma quel `n` non è il numero di fatti nello store: è ciò che
`count()` restituisce, e il suo contratto lo dichiara —

> «Live facts only (superseded excluded), matching `search`'s default view.»

**I due conteggi divergono di 2284**, e con quello sbagliato il verdetto si
ribalta:

| conteggio | valore | scarto da 13795 | esito |
|---|---|---|---|
| `facts` TOTALI | 16664 | +2869 | avrebbe **già** ricalcolato |
| `facts` VIVI ← *quello vero* | 14380 | **+585** | usa il salvato, **margine 105** |

Il file non è stato riscritto in quattro ore: è la conferma indipendente che il
conteggio in uso è quello dei vivi. **Restano 105 fatti vivi netti.** Ne ho
scritti 79 io in una notte.

⚠️ La soglia è simmetrica (`abs`): ricalcola sopra 14484 **o sotto 13105**. Una
tornata di ritiri ci arriva dall'altro lato.

## ② Il valore che uscirà è 0,8797 — e non dipende dal daemon

Nel `48` avevo ottenuto **0,8881** cancellando il file su copia, ieri sera,
**mentre il daemon era spento**. Un valore misurato durante il guasto non dice
cosa succederà a guasto finito, quindi ho rifatto la misura adesso, daemon
caldo, su una copia dello store in tempdir:

```
fatti vivi sulla copia: 14389
PAVIMENTO RICALCOLATO ORA (daemon caldo) = 0.8797
```

**0,8797 contro 0,8881: la differenza è il rumore delle sonde, non il daemon.**
La stima è stabile, e questo toglie l'unica scappatoia che restava — «col daemon
caldo verrà un valore diverso». Non verrà.

## ③ Quel pavimento taglierebbe il 97,8% del traffico vero

Qui ho sbagliato una volta, e vale la pena dire come: l'errore è il modo normale
di ingannarsi su questa misura.

**Primo tentativo, sbagliato**: 40 query «dentro dominio» costruite copiando
frasi intere del corpus. Risultato: mediana 0,947, solo il 15% sotto il
pavimento ⇒ *«separa benissimo, l'allarme non esiste»*. **Ma quelle non sono
query, sono documenti**: chiedere a una memoria un testo che contiene già sé
stesso è il caso più facile che esista, e il banco misurava la propria facilità.

**La popolazione vera esiste e non me la devo inventare**: il prodotto registra
`best` a ogni recall. Journal **ruotato**, quindi `events.jsonl` **e**
`events.jsonl.1` — **39.008 righe lette**, 3893 eventi `flow.recall`:

```
per kind (totale / con best):
   search        3355 /  3355
   explain        529 /     0      <- explain non porta best, non e' uno zero
   correct          6 /     0
   answer           3 /     0
```

Escluse le mie recall di stanotte restano **3155 recall reali con un punteggio**,
di cui **268 (8,5%) con `best = 0`** — il regime degradato, dove il punteggio è
zero per costruzione. Tolte anche quelle, la popolazione onesta è **n = 2887**:

```
distribuzione dei best > 0:  min=0.017 p05=0.555 mediana=0.850 p95=0.863 max=1.000
```

| soglia | che cos'è | taglia |
|---|---|---|
| **0,0000** | il valore degenere di **oggi** | **0/2887 = 0,0%** |
| 0,8500 | la mediana del traffico stesso | 1547/2887 = 53,6% |
| 0,8680 | max dentro-dominio misurato da @ws2 | 2770/2887 = 95,9% |
| **0,8797** | **il ricalcolo di adesso, daemon caldo** | **2823/2887 = 97,8%** |
| 0,8881 | il ricalcolo di ieri sera | 2842/2887 = 98,4% |

**Il sistema è oggi a un estremo — non filtra niente — e fra 105 fatti salta
all'altro, dove non passa quasi niente.** In mezzo non c'è nessun valore che la
stima automatica possa produrre: `estimate_relevance_floor` restituisce
direttamente ~0,88.

✅ **E questo conferma @ws2 sulla popolazione vera**: la banda che aveva misurato
(0,840–0,868) è esattamente dove sta il traffico reale (mediana 0,850, p95
0,863), ma ora su n=2887 invece che su un campione.

## ④ La diagnosi, in due numeri affiancati

`estimate_relevance_floor` prende il **95° percentile del punteggio massimo su
sonde SCRAMBLATE** — testo mescolato, che per costruzione non ha argomento. La
tesi del `48` era che quel testo punteggia *più in alto* delle domande vere.
Adesso i due numeri stanno uno accanto all'altro:

| | p95 |
|---|---|
| sonde scramblate (il righello) | **0,8797** |
| traffico reale (ciò che deve passare) | **0,863** |

**Il righello si taglia sopra la testa di ciò che deve misurare.** Non è un
problema di taratura fine: la stima colloca il pavimento oltre il 95° percentile
del traffico legittimo.

## ⑤ Che cosa NON dico

- **Non dico che il gateway rifiuterà il 97,8% delle risposte.** Dico che il
  97,8% dei punteggi reali starebbe sotto quel pavimento. Che cosa la porta
  faccia poi con «sotto il pavimento» — filtro, avviso, nulla — è un'altra
  domanda, e sul MCP l'avviso **non è mai stato collegato** (`48`, chiuso da
  @ws3).
- **Non ho toccato nulla.** Nessun `rm`, nessuna scrittura: la copia in tempdir è
  l'unica cosa che ho modificato, e il `floor.json` vero è invariato prima e dopo
  ogni misura (mtime 20:32, controllato tre volte).
- **La popolazione ha una parzialità dichiarata**: `best` esiste solo per
  `kind=search` (3355 su 3893). Gli `explain` non lo portano, e contarli zero
  sarebbe l'errore che ho già fatto una volta su questo stesso journal.
- **`best` è il punteggio del primo risultato**, non la prova che quel risultato
  fosse giusto. Misura ciò che il pavimento vede, non la qualità della risposta.

## ⑥ Che cosa cambia per chi decide

Il `48` lasciava la scelta fra «cancellare il file» e «lasciarlo». **Adesso
lasciarlo non è più un'opzione stabile: è cancellarlo in differita, fra 105
fatti, senza che nessuno lo decida.** Le opzioni vere sono due, e nessuna è il
`rm`:

1. **Fissare il pavimento a mano**, a un valore scelto sul traffico — 0,85
   taglia già il 53,6%, quindi nemmeno quello è ovvio. Decisione di prodotto.
2. **Cambiare il righello**: finché la stima usa sonde scramblate, ogni
   ricalcolo rimetterà ~0,88. Il `rm` non cura la causa, la riarma.

📌 **La misura ha una scadenza, e l'ho vista scadere mentre scrivevo.** Ho
rieseguito lo stesso banco venti minuti dopo il primo:

```
01:15   facts VIVI = 14380   margine residuo = 105
01:35   facts VIVI = 14390   margine residuo =  95
```

**Dieci fatti vivi in venti minuti.** A quel ritmo il margine si chiude in circa
tre ore — ma il ritmo è quello di **una notte con otto istanze che scrivono**, e
non va esteso al regime normale senza misurarlo. Il punto non è il tasso: è che
**il 105 era già falso venti minuti dopo averlo scritto.** Il margine si legge
rifacendo il conto (`banchi/ws6-margine-del-pavimento.py`), mai ricopiando il
numero da qui.

---
*Banchi: `banchi/ws6-margine-del-pavimento.py`, `banchi/ws6-best-reali-dal-journal.py`,
`banchi/ws6-ricalcolo-pavimento-daemon-caldo.py`. Store di Aurelio in sola
lettura; ogni ricalcolo su copia in tempdir con `HIPPO_DATA_DIR` isolato.*
