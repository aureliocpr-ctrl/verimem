# Il rilevatore dichiara in conflitto il 99% delle coppie possibili di un topic

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, quarantena.*

Questo chiude la serie iniziata col documento 42. Là avevo misurato **quante**
sono le contraddizioni registrate (93.263 irrisolte, il 99,6%) e che il 93,7%
mette a confronto fatti che parlano d'altro. Nel 43 avevo spiegato le poche ad
alto jaccard: sono log a istanti diversi, e valgono il 3%. Restava la domanda
grossa: **da dove vengono le altre novantamila?**

Vengono da tre cartelle.

## Il rilevatore non guarda mai fuori dal topic

Il primo dato è netto e spiega qualcosa che avevo visto senza capirlo:

    coppie fra topic DIVERSI: 0 = 0,0%

**Zero.** Ogni singola contraddizione registrata mette a confronto due fatti
dello **stesso topic**. Nel documento 41 avevo notato che le supersessioni
erano «stesso topic 100%» in entrambi i periodi misurati e l'avevo trovato
curioso: non era una proprietà delle supersessioni, è che **il rilevatore non
confronta mai due topic diversi**.

## Tre topic fanno il 72,6%

| topic | righe | quota | cumulato |
|---|---|---|---|
| `research/memoria-appresa` | 39.322 | 42,2% | 42,2% |
| `project/orin` | 16.865 | 18,1% | 60,2% |
| *(topic vuoto)* | 11.529 | 12,4% | **72,6%** |
| `project/syn/goal-tree-2026-06` | 3.415 | 3,7% | 76,3% |
| `dialog/doc2-dominic-2026-05-14` | 3.210 | 3,4% | 79,7% |
| `handoff/per-ws3-dogfooding` | 2.160 | 2,3% | 82,0% |

Sei topic fanno l'82%. Non è un fenomeno diffuso nel corpus: è concentrato.

## La clique: quasi tutte le coppie possibili

Qui il numero che conta. In `research/memoria-appresa` ci sono **250 fatti**.
Due fatti alla volta, le coppie possibili sono **31.125**. Le coppie distinte
dichiarate in contraddizione sono **30.974**.

| topic | fatti | coppie possibili | dichiarate | quota |
|---|---|---|---|---|
| `research/memoria-appresa` | 250 | 31.125 | 30.974 | **99,5%** |
| `project/orin` | 160 | 12.720 | 12.477 | **98,1%** |
| *(topic vuoto)* | 136 | 9.180 | 9.043 | **98,5%** |

**Non è un caso isolato: in tutti e tre i topic principali il rilevatore
dichiara in conflitto fra il 98% e il 99,5% di tutte le coppie possibili.**

Un rilevatore che segnala quasi ogni coppia non sta rilevando: **sta
enumerando**. Il valore informativo di «questi due fatti sono in contraddizione»
è, dentro questi topic, indistinguibile da «questi due fatti esistono
entrambi».

*(I fatti sono contati senza escludere i superati, quindi il denominatore è
un'approssimazione per eccesso: la quota reale è ancora più alta, non più
bassa.)*

## Perché proprio lì

I dodici fatti più conflittuali hanno tutti **458-459 clash** ciascuno — numeri
quasi identici, che è la firma di una clique dove ognuno confligge con ognuno.
Sono questi:

    ESPERIMENTO C plasticita Hebbian (Miconi 1804.02464) DIMOSTRATO: rete plastica W…
    KEPLER orbite 2-invarianti 2026-06-28 (SIGNIFICATIVO): HNN (plasticita'+invarian…
    GROKKING (a+b) mod 97, MLP 256, weight_decay 1.0, 2026-06-28: RISULTATO FORTE e…
    SCALA ondata-2 (workflow wf_e98e9a99, 2026-06-27): 18 estensioni per superare la…

Appunti di ricerca: **lunghi, densi di numeri, tutti diversi fra loro**. Ognuno
contiene misure, date, dimensioni, identificatori. Confrontati a coppie da un
criterio che segnala «due numeri che non coincidono», producono un conflitto
ogni volta.

Il documento 42 ha mostrato che il criterio non lega il numero alla grandezza.
Questo mostra **dove quel difetto esplode**: in un topic che raccoglie molti
fatti lunghi, il costo è quadratico.

## E il registro è duplicato per un quinto

Contando le coppie **non ordinate** invece delle righe:

    righe irrisolte              : 93.263
    coppie non ordinate distinte : 74.646
    => 18.617 righe in eccesso (20%)

**Un quinto del registro delle contraddizioni è la stessa coppia registrata più
di una volta.** Nel topic principale il rapporto è 1,27 righe per coppia
distinta. Non cambia le conclusioni — le proporzioni misurate nel 42 e nel 43
reggono — ma chiunque citi «93.263 contraddizioni» sta citando un numero
gonfiato del 25%.

**Il registro però non si gonfia da solo.** Avevo lasciato come limite la
domanda se il rilevatore ripassasse periodicamente sullo stesso materiale,
registrandolo di nuovo; anche questa si chiude con una query, e la risposta è
no: delle 18.617 coppie duplicate, **solo 49 (lo 0,3%) sono state rilevate in
giorni diversi**. La duplicazione avviene dentro la stessa giornata — più
scritture ravvicinate che rifanno lo stesso confronto — non nel tempo.

## E non sta peggiorando: è un accumulo storico

Un'ultima cosa che cambia l'urgenza, e che va detta perché ridimensiona il
pezzo. Le contraddizioni irrisolte per giorno di rilevamento, negli ultimi dieci
giorni:

    14/08     1     24/08   193
    15/08   119     27/08  1477
    18/08     3     28/08  2990
    20/08    54     29/08   141
    23/08    29     30/08   136

Circa **5.100 righe su 93.263**. Tutto il resto è **antecedente al 14 agosto**,
coerente con il fatto che il topic dominante raccoglie appunti di ricerca di
giugno.

**Non è un problema in crescita: è un deposito.** Il criterio difettoso è ancora
attivo — le 136 righe di oggi lo dimostrano — ma il volume che spaventa è
storico, e questo cambia la priorità: prima si sistema il criterio, poi si
decide cosa fare del deposito, senza fretta.

## Il legame che nessuno aveva fatto

`verimem doctor` ha un controllo separato, il **topic-crowding**: avverte che i
fatti scritti su un topic già usato sopravvivono 1204 su 1724, contro 1020 su
1125 per i topic usati una sola volta. E la nostra regola «**un topic per
misura**» nasce da lì.

Questo documento mostra **un secondo effetto dello stesso affollamento**, che
non era stato collegato: un topic con 250 fatti lunghi non produce solo più
supersessioni — produce **30.974 falsi conflitti**, perché il rilevatore lavora
a coppie dentro il topic e il numero di coppie cresce col quadrato.

«Un topic per misura» aveva una ragione conosciuta. Ne ha una seconda, ed è
quadratica.

## Per chi riprende

- Il righello è `docs/stato-reale/banchi/ws6-la-clique-di-un-topic.py` (sola
  lettura).
- **La cura resta quella del documento 42** — legare numero e grandezza, come
  `L4.2` fa già in scrittura — ma questo pezzo ne aggiunge una seconda,
  indipendente e più economica: **non confrontare a coppie dentro un topic oltre
  una certa cardinalità**, o almeno non registrare il risultato. Nessuna delle
  due l'ho applicata: è codice del gate.
- **Il numero da citare non è 93.263 ma 74.646**, e la deduplicazione andrebbe
  fatta a monte.
- **Il picco di fine agosto è spiegato, e conferma il meccanismo**: le
  contraddizioni rilevate in quei giorni vengono da **`brainstorming/25-08`**,
  un topic con **81 fatti** che ne ha prodotte **1.413** — il 43,6% delle 3.240
  coppie possibili. Un topic riempito in fretta genera più di mille conflitti
  nel giro di due giorni: è il meccanismo quadratico visto all'opera su
  materiale recente, non solo sul deposito di giugno.
- 🪞 **Un mio inciampo da segnalare a chi rifà i conti**: la tabella per giorno
  qui sopra usa l'**ora locale** (`datetime.fromtimestamp`), mentre le query per
  topic usano **UTC** (`date(detected_at,'unixepoch')`). I due totali non
  coincidono e non sono confrontabili — non è un'anomalia dei dati, è il fuso.
  Nono difetto del misuratore in una sera.
- **Le righe orfane sono trascurabili**: solo **22 su 93.263** hanno un lato che
  non esiste più fra i fatti, quindi tutti i conteggi fatti qui con una `JOIN`
  sono completi e non sottostimati. L'ho verificato perché, se fossero state
  migliaia, ogni numero di questo documento e dei due precedenti sarebbe stato
  una sottostima.

---

**Verifica**: `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`.
Istanti 22:15:36-22:18:01 del 30/08, dichiarati perché il corpus cresce mentre
si misura. Nessuna scrittura.
