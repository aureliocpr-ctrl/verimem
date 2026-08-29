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

## ⚠️ Il limite grosso, e va letto prima di usare questa lista

**Tutte e tre le dimensioni vengono da UN SOLO claim** («il magazzino di Verona contiene 480
pallet») e da **una sola coppia vero/falso**. ⇒ **questa specifica dice QUALI ASSI variare, non
QUANTI CASI servono né con che frequenza si presentino in un corpus reale.** Chi la usa per
dimensionare un corpus sta estrapolando: **il numero di casi non è qui dentro, e non l'ho misurato.**

**Cosa resta scoperto** e non l'ho toccato: forme intermedie fra tabella e prosa; lingue oltre IT/EN;
documenti veri (PDF, DOCX) invece di stringhe; e **quale delle tre parole estranee** pesi sul
grounding.
