# ⑬ La taglia della fonte degrada il gate **nei due versi** — e per una metà la cura c'è già

**Misurato il 28/08/2026 fra le 18:37 e le 20:53** · codice `Code/HippoAgent`
(stampato da ogni banco) · tutte le misure **fuori da pytest** · scritto in
regime risparmio RAM, quindi **nessuna misura nuova in questo documento**: solo
ciò che è già stato eseguito e committato.

---

## In una riga

Una variabile sola — **quanto testo circonda la prova** — fa **entrare** le
falsità di attribuzione e **uscire** i fatti veri. La seconda metà ha già una
cura nel prodotto (`index_document`) che nessuna riga di documentazione
suggerisce; la prima no.

---

## 1. Il verso che fa entrare il falso

Fonte «da manuale» contro fonte con contorno, **stesse coppie, stessi claim**:

```
  coppia             fonte           verso A           verso B
  euro grandi        NUDA  (453)  ferma   72.1      ferma    0.9
  euro grandi        RICCA (820)  ENTRA  100.0      ENTRA  100.0
```

E la soglia è **bassissima**: bastano **160 caratteri** di clausole di stile
perché il primo scambio passi, **482** perché passino entrambi. Sopra i **935**
caratteri il gate **non distingue più il vero dal falso** su questa famiglia —
claim vero `100.0`, i due scambi `99.5–100.0`.

⇒ **Non serve nemmeno un contorno pertinente.** Quattro nature (clausole vere,
prosa estranea, pseudo-parole, cifre senza sintassi): tutte aprono a +160
caratteri. `72.1 → 99.7–100.0`.

🔴 **CORREZIONE del 29/08 01:00 (cella W7-41): «tutte e quattro monotone» era
un artefatto del campionamento.** Rimisurato a passi di **6 caratteri** invece
che di 160: il punto di ribaltamento è **+6**, non +160 — e a **+18 la curva
TORNA INDIETRO** (`downgrade`, 77.4), per ripartire a +24. ⇒ **Non c'è una
soglia: c'è un regime instabile** in cui il punteggio oscilla fra 77 e 99 al
variare di pochi caratteri. Con passi di 160 quel rientro non era visibile.
⇒ E **i numeri non servono**: una coda senza una sola cifra ribalta come una
con le cifre.

## 2. Il verso che fa uscire il vero

Stessi fatti **veri**, quattro taglie, tutte contenenti il fatto:

```
     ins            minima       media 2k       larga 8k     intera 38k
     148      ENTRA   99.9   ENTRA  100.0   ENTRA   94.0   ferma    0.6
      86      ENTRA  100.0   ENTRA  100.0   ENTRA  100.0   ferma    0.3

  minima 4/4  ·  media 4/4  ·  larga 3/4  ·  intera 1/4
```

⇒ Lo stesso fatto vero passa a **99.9** quando la fonte è la riga che lo
sostiene e cade a **0.6** quando quella riga sta dentro il documento.

## 3. ✅ Per la seconda metà la cura **esiste già**

```
     ins     DIRETTA (documento intero)      PORTA: il pezzo ha la riga?
     148                   ferma    0.6                   SI, in 3 pezzi
     163                   ENTRA   94.5                   SI, in 3 pezzi
  DIRETTA 1 su 4   ·   PORTA 4 su 4   ·   chunks_indexed=49
```

`index_document` + `search_documents` restituisce il pezzo giusto **4 volte su
4**, ed è documentata su tutte e tre le superfici (`README:202-210`, `:437`).

🔴 **Manca l'avviso, e la via sbagliata è quella ovvia.** Nessuna riga dice che
`add(fatto, source=open("contratto.txt").read())` fa **rifiutare i fatti veri**.
⇒ **La cura non è nel gate: è una riga di documentazione.** Proposta di testo:

> ⚠️ `source` è pensato per **il passaggio che sostiene il fatto**, non per un
> documento intero. Su una fonte lunga il giudizio si degrada in entrambe le
> direzioni: fatti veri vengono rifiutati e attribuzioni sbagliate passano. Per i
> documenti usa `index_document(path)` e `search_documents(query)`, che
> indicizzano per pezzi.

---

## 4. Ciò che il gate **fa**, e va detto con la stessa forza

- ✅ **La cifra inventata è fermata a ogni lunghezza** — otto lunghezze fino a
  3.516 caratteri, mai una fuga, `L4.1` presente in ogni riga. **Il contorno non
  la salva mai.**
- ✅ **Regge senza le nostre variabili d'ambiente**: stesso banco con 7 env
  nostre attive e con 0 → risultati **identici alla prima cifra decimale**.
- ✅ **Sulla prosa il giudice funziona**: contratto `0.2–0.6`, referto `1.1–9.0`,
  e nella ricevuta compare sempre anche `L4-grounding`.

## 5. Dove il giudice è **da solo**

Su **documento tecnico** il giudice dà `82–99.7` a una cifra inventata e a
fermarla resta la sola `L4.1`, con `withheld_despite_judge=True`. Sul **git log
vero** invece funziona (`0.3–1.1`) **fino a 6.000 caratteri**; a 25.661 torna a
`97.6` con la sola regex.

⇒ **Due fonti reali, due comportamenti**, e la generalizzazione «testo
strutturato» **non regge**: un git log è strutturato quanto e più di un log
costruito. **La variabile che li distingue non ce l'ho.**

---

## 6. Le ipotesi cadute, contate

Quattordici, in due giorni, e la maggior parte **mie**: sovrapposizione
lessicale (tre grandezze) · troncamento 512 · max-su-finestre · posizione della
smentita · natura del contorno **sull'esito** e **sulla forma** · specie della
grandezza · verso dello scambio · rapporto fra i valori · struttura sintattica ·
la popolazione · il ricalco (n=1, cade su batteria) · la lingua · l'unità di
misura (candidato di @ws3, cade sull'A/B).

🔑 **Nessuna regola sui testi predice il verdetto.** È il risultato negativo più
solido che abbiamo, e vale come vincolo di progetto: **la cura va cercata nel
giudice o in uno strato deterministico accanto** — che è esattamente ciò che
`L4.3` prova a fare.

⇒ E lo strato deterministico, misurato contro questa popolazione, **coglie 2
scambi su 6 con 0 falsi positivi su 6 veri** (cella W7-22). La causa dei quattro
mancati è **letta nel codice, non congetturata** (cella W7-23): `ancore()` scarta
funzionali e unità **ma non i sostantivi del dominio**, e il passo 3 assolve
quando l'intersezione è **non vuota** — basta un token condiviso. Poiché un
contratto è fatto di clausole omogenee («la penale per X» / «la penale per Y»),
**il passo assolve proprio sul dominio che deve proteggere**.

---

## 7. Limiti, dichiarati

- **Fonti costruite** in §1 e §3 (contratto, referto, log). Il documento tecnico
  e il git log sono **reali**; la fonte del git log è **fissata su file e
  committata** (`banchi/fonte-log-fissata.txt`).
- **Una misura ritirata per irriproducibilità**: usavo `git log` vivo come fonte,
  e il repo prende sei commit in tre minuti. Da lì la regola di sessione:
  **fissare la fonte a uno SHA o a un dump**.
- **Un risultato ritirato per popolazione mia**: «sul log il giudice sbaglia
  4/4» era su un log **che avevo scritto io**; sul log vero dà `0.3–1.1`.
- **Nessuna riverifica in venv pulita**: su questa macchina l'installazione è
  **editable** (`__editable___verimem_0_7_0_finder.py`, 15 file nel RECORD),
  quindi «regime installato» non si ottiene importando.

## 8. I banchi, tutti riproducibili

`e-l-unita-o-l-ordine-di-grandezza` · `non-e-l-unita-e-la-fonte-intorno` ·
`quanto-contorno-basta-perche-lo-scambio-passi` ·
`pertinente-contro-artificiale-la-forma-della-curva` ·
`due-popolazioni-due-forme` · `il-genere-del-documento-cambia-la-curva` ·
`quattro-generi-di-fonte` · `il-log-vero-si-comporta-come-quello-costruito` ·
`tre-popolazioni-sulla-stessa-fonte-reale` · `perche-il-gate-rifiuta-un-fatto-vero` ·
`la-batteria-del-ricalco-su-fonte-fissata` · `il-gate-non-traduce-e-rifiuta-il-vero` ·
`il-vero-si-perde-quando-la-fonte-e-grande` ·
`la-porta-documenti-protegge-dal-difetto-della-taglia` ·
`i-miei-verdi-sono-verdi-di-casa` ·
`non-esiste-un-regime-installato-su-questa-macchina` ·
`L4-3-contro-la-mia-popolazione`

Ognuno porta **un controllo che poteva fallire**. Tre sono caduti mentre
costruivo, e **tutti e tre erano difetti veri del disegno**.

Celle nel registro: **W7-8 · W7-9 · W7-10 · W7-11 · W7-12 · W7-13 · W7-14 ·
W7-15 · W7-16 · W7-17 · W7-18 · W7-19 · W7-20 · W7-21 · W7-22 · W7-23**.
