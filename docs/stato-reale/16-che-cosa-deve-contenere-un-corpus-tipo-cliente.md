# Che cosa deve contenere un corpus di validazione «tipo cliente»

**Autore**: ws6/Aldo · **Data**: 2026-08-29, sera · **Stato**: specifica degli **assi**, non del
numero di casi.

## Perché esiste questo documento

@ws3 ha misurato (`13e98fcb`, sola lettura, istante 01:23) che **il corpus su cui validiamo non
somiglia al cliente**: sui **6009** span con `grounding_span` non vuoto, il **51,9%** ha più del 40%
di righe **a colonne**, il **71,4%** ne ha almeno una, e la prosa con numerazione di sezione è
**0,07% (4 span)** — quei quattro, letti uno per uno, sono **nostri output di banco**. Ablazione su
prosa sintetica: **0%**. È il gemello, dal lato della **fonte**, del **70% contro 0,6%** che @ws1 ha
misurato dal lato del **claim**.
⇒ Servono **due** corpora: il nostro (output di strumenti) e uno **tipo cliente**. **Oggi ce n'è uno
solo, e non è quello giusto.**

**Questo documento non costruisce il corpus.** Dice **quali assi devono variare**, e lo dice con
**numeri misurati**, non con un'idea di come dovrebbe essere un documento reale. Chi lo costruirà
senza questa lista lo farà **a caso**.

---

## ① Tabellare contro prosa — cambia **CHI avvisa**

Stesso claim, stessa cifra, stessa verità; cambia **solo** la forma della fonte:

| forma | claim **VERO** | claim **FALSO** |
|---|---|---|
| tabellare (`sede  Verona` / `pallet  480`) | 99,8 · 🔴 **`L4.2`** | 0,4 · `L4.1`+`L4-grounding` |
| prosa (verbale con formule di rito) | 98,3 · ✅ nessun layer | 0,6 · `L4.1`+`L4-grounding` |

⇒ **La protezione NON cambia** — il falso è preso in entrambe con gli stessi layer. **Cambia il
rumore**: `L4.2` avvisa **solo** sulla tabellare. **Verificato anche in inglese**, con esito identico
(99,9 / 98,0): **è la forma, non la lingua.**
**Rifallo con**: `for forma in tabellare prosa; do for lingua in it en; do HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-la-forma-della-fonte-decide-il-rumore.py $forma $lingua; done; done`
**Non misurato**: forme intermedie (elenchi puntati, tabelle markdown, PDF con intestazioni).

## ② Ordine etichetta/numero **dentro** la tabellare — è **la variabile vera**

Quattro varianti, una cosa per volta:

| variante | layer |
|---|---|
| tabellare completa | 🔴 `L4.2` |
| stessa tabella **senza il secondo numero** | 🔴 `L4.2` — *quindi non è la compresenza di numeri* |
| stessa tabella con **`480  pallet`** invece di `pallet  480` | ✅ nessuno — *quindi non è la tabella* |
| prosa con **due** numeri | ✅ nessuno |

⇒ **Resta una sola variabile: l'ordine.** Etichetta **prima** del numero → `L4.2` parla; etichetta
**dopo** → tace. **Conferma a variabile singola** il reperto di @ws4 («*L4.2 legge la grandezza a
destra del numero*»).
🔑 **Un corpus tipo cliente deve contenere ENTRAMBI gli ordini**, altrimenti misura un solo lato.
**Rifallo con**: `for v in a b c d; do HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-cosa-della-tabella-attiva-L4-2.py $v; done`
**Non misurato**: il **codice** di `L4.2` — ho misurato ingresso e uscita, il meccanismo lo dichiara @ws4.

## ③ Asciutto contro contestualizzato — cambia il **GROUNDING**

| fonte | caratteri | grounding |
|---|---:|---:|
| secca, zero parole estranee | 43 | 98,9 |
| corta **con** parole estranee («verbale», «attesta», «censiti») | 71 | **96,9** |
| lunga **senza** parole estranee (il claim ripetuto) | 175 | **99,9** |
| prosa piena | 140 | 98,3 |

⇒ **Non è la lunghezza** — anzi è rovesciata: la fonte **più lunga** ha il punteggio **più alto**.
**Sono le parole estranee.** ⇒ **il grounding premia la fonte che RIPETE il claim e penalizza quella
che lo CONTESTUALIZZA** — cioè penalizza il documento reale, che le formule di rito **ce le ha per
forza**.
🔴 **E QUI IL VERSO CHE IO NON HO MISURATO, ed è il più grave** — documento **⑬**
(`13-la-taglia-della-fonte-degrada-il-gate-nei-due-versi.md`): le **stesse** clausole di stile, su un
claim **FALSO**, lo fanno **ENTRARE a 100,0** dove la fonte nuda lo fermava a **72,1**, e bastano
**160 caratteri**. ⇒ **il contorno estraneo agisce nei due versi**, e sul falso è un difetto vero.
⚖️ Sul claim **vero** restano 1,5–2 punti su una soglia di **40**: **innocui, nessun verdetto
cambia**. **Ma «non è un difetto» vale solo per quella metà**: l'avevo scritto come conclusione
generale ed era falso.
📌 **Un dato che il ⑬ non ha**: la variante **«lunga SENZA parole estranee»** (il claim ripetuto, 175
caratteri) prende **99,9**, il massimo ⇒ **non è la TAGLIA a degradare, è il testo ESTRANEO** — e la
soglia dei 160 caratteri è una soglia **sul rumore**, non sulla dimensione. **Conta solo se
qualcuno usa il grounding come metrica di qualità della fonte**, che è un uso diverso da quello per
cui esiste.
📌 Utile a chi misura: **il giudice è deterministico** su questa cella — 98,3 **tre volte su tre**.
**Rifallo con**: `for v in secca corta_extra lunga_pulita prosa_piena; do HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-il-grounding-e-il-vocabolario-estraneo.py $v; done`

---

## ④ Il TIPO di falsità — **cifra inventata contro quantità vaga**

**Aggiunto il 29/08 dopo aver letto `l4-1-guarda-in-una-direzione-sola.md`** (@ws3, 27/08), che legge
il codice: `anti_confab_gate.py:2455` fa `_assenti = valori_non_nella_fonte(proposition, source)` —
prende i valori **del claim** e restituisce quelli che **non compaiono nella fonte**.

⇒ **Questo spiega il dato degli assi ① e ②**: il claim falso di quei banchi dice «**999** pallet» e la
fonte dice «480» — **999 non c'è in NESSUNA delle quattro forme**. ⇒ **`L4.1` è insensibile alla forma
per costruzione**, e «la protezione non dipende dalla forma della fonte» **regge, con il meccanismo
accanto invece che come sola misura**.

🔴 **Ma ridimensiona la popolazione di controllo di questo documento.** Una **cifra inventata** è il
caso **facile** per `L4.1`: un valore assente dalla fonte, che è esattamente ciò che quella funzione
cerca. I numeri di @ws4 citati in quel documento mostrano l'altro tipo di falsità:
```
  «pochi pazienti»    contro  30 su 40    passa a 98.1   layer: []
  «una minoranza»     contro  48 su 55    passa a 99.7   layer: []
  «guasti sporadici»  contro  90 su 120   passa a 96.1   layer: []
```
⇒ **una falsità VAGA non contiene un valore assente, quindi `L4.1` non ha nulla da trovare e il claim
passa.**

🔑 **Per il corpus**: le due popolazioni non bastano se la seconda contiene **un solo tipo di
falsità**. Un corpus tipo cliente deve avere **entrambi**: ① il falso **per cifra** (facile) e ② il
falso **per vaghezza** (che oggi passa). **Senza il secondo si misura solo la metà che il prodotto
prende bene.**
⚠️ **Non l'ho misurato io**, e la fonte primaria non è quella che avevo citato.

🔴 **CORREZIONE (29/08, 20:16) — questo asse NON è una lacuna da colmare: è un documento già
scritto.** `docs/stato-reale/11-la-quantita-vaga-non-viene-confrontata.md` (@ws4, 27/08 18:30–19:10,
`validate="full"`, CE locale, store nuovo per cella) lo copre **per intero**, con **otto casi in due
direzioni** e **la popolazione di controllo**:
```
  esagera    «gran parte dei pezzi»  contro  3 su 40    passa 99.0
             «quasi tutti»           contro  4 su 28    passa 99.8
             «guasti frequenti»      contro  1 su 120   TRATT 0.8
  minimizza  «pochi pazienti»        contro 30 su 40    passa 98.1
             «una minoranza»         contro 48 su 55    passa 99.7

  esagerando    3 falsità su 4 ammesse
  minimizzando  4 su 4  ← TUTTE, e tutte con ZERO layer
  VERI di controllo     8 su 8 ammessi
```
🔑 **E porta un dato che io non avevo e che è il più forte: il caso peggiore NON è quello che
esagera.** Minimizzare passa **4 su 4**, esagerare **3 su 4** — controintuitivo, e nessuno lo
indovinerebbe costruendo un corpus a mano.
⇒ **Per il corpus resta vero che servono entrambi i tipi di falsità**, ma la misura **non va rifatta**:
**va presa dal ⑪**, e un corpus tipo cliente deve contenere **le due DIREZIONI della vaghezza**, non
solo «una falsità vaga».
⚖️ **Errore mio, dichiarato**: avevo citato questi numeri **via `l4-1-guarda-in-una-direzione-sola`**,
cioè **di seconda mano**, mentre la fonte primaria esisteva ed è più ricca. **È la quarta volta in una
sera che un documento già scritto copriva ciò che stavo per aggiungere**, e l'ho trovato — di nuovo —
**elencando i titoli, non cercando parole mie**.

## ⚠️ Il limite grosso, e va letto prima di usare questa lista

**Tutte e tre le dimensioni vengono da UN SOLO claim** («il magazzino di Verona contiene 480
pallet») e da **una sola coppia vero/falso**. ⇒ **questa specifica dice QUALI ASSI variare, non
QUANTI CASI servono né con che frequenza si presentino in un corpus reale.** Chi la usa per
dimensionare un corpus sta estrapolando: **il numero di casi non è qui dentro, e non l'ho misurato.**

**Cosa resta scoperto** e non l'ho toccato: forme intermedie fra tabella e prosa; lingue oltre IT/EN;
documenti veri (PDF, DOCX) invece di stringhe; e **quale delle tre parole estranee** pesi sul
grounding.
