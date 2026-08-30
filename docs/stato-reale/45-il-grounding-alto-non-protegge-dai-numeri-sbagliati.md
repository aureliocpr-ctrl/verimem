# Il grounding alto non protegge dai numeri sbagliati: L4.1 è l'unico che li vede

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, quarantena.*

Ultima area del mio perimetro che non avevo guardato stanotte: **chi mette i
fatti in quarantena, e se ha ragione**.

## Prima la memoria, e la memoria era vecchia

La nostra regola dice di cercare in memoria prima di misurare. L'ho fatto, e
sono usciti due fatti citati nell'indice: `78b1aecf3ff4` e `e00618a933da`, che
l'indice riassume così — *«il gate decide con le parole: L1 precisione ~40%,
1728/1855 quarantinati da sole keyword»*.

Ho letto il fatto invece della sintesi. Dice:

> *«Su un campione casuale di **11** warning L1 del corpus vivo, 4 sono corretti
> e 7 sono falsi positivi.»*

**Il «~40%» che citiamo come dato consolidato poggia su undici osservazioni**, e
il fatto ha `grounding_span = None`: nessuna source registrata. Non è sbagliato
— è fragile, e nessuno lo dice quando lo cita.

E soprattutto è **datato**. Ecco la quarantena oggi, alle **22:29:08 del 30/08**:

    fatti 16.467   quarantined 2.614 = 15,9%

| chi ha fermato | n | quota | grounding medio | di cui ≥90 |
|---|---|---|---|---|
| *(nullo)* | 1.909 | 73,0% | 17,2 | 15 |
| `moat` | 476 | 18,2% | **6,3** | 0 |
| `L4.1` | 118 | 4,5% | **96,8** | **109** |
| `gate` | 55 | 2,1% | **98,8** | **54** |
| `L4-review` | 37 | 1,4% | 60,0 | 0 |
| `L3-coexistence` | 15 | 0,6% | 89,8 | 11 |
| **`L1`** | **2** | **0,1%** | 99,9 | 2 |
| `store-screen` | 1 | 0,0% | 100,0 | 1 |

**`L1` oggi ferma due fatti su 2.614.** Il regime che la nostra memoria descrive
— quello in cui le keyword quarantinavano quasi tutto — **è finito**: al suo
posto lavorano il `moat` e i layer `L4.x`. La lezione non era falsa: era di
un'altra era, e va letta come storia.

## Il 73% senza autore è quasi tutto passato, ma non del tutto

Il dato che salta all'occhio è che tre quarti dei quarantinati non dicono chi li
ha fermati. La datazione spiega quasi tutto:

| mese | senza `quarantined_by` | con |
|---|---|---|
| 2026-05 | 1.579 | 0 |
| 2026-06 | 47 | 0 |
| 2026-07 | 76 | 0 |
| **2026-08** | **207** | **705** |

**Il campo è nato ad agosto**: prima non esisteva, e i 1.702 casi muti di
maggio-luglio sono un'eredità, non un difetto attivo.

Ma **207 quarantinati di agosto — il 22,7% del mese — restano senza autore anche
ora che il campo c'è**. Un fatto su cinque viene messo da parte senza che si
sappia quale controllo l'abbia deciso. È la stessa forma del difetto che questa
serie ha trovato nella telemetria (documento 38): **il prodotto sa e non lo
scrive**.

## Il caso interessante: fermati con la fondatezza al 99

La riga che merita di essere letta è quella di `L4.1`: **118 fatti fermati, con
un grounding medio di 96,8**, e **109 di essi sopra 90.** Più `gate`, altri 55
con media 98,8.

**Centosettantatré fatti sono stati messi in quarantena mentre il giudice di
fondatezza li dichiarava sostenuti dalla loro source al 90-99%.**

Questo si può leggere in due modi opposti: o i layer lessicali sono troppo
severi e stanno buttando via roba buona, o vedono qualcosa che il giudice non
vede. Non si decide a tavolino: si leggono i casi. Ne ho presi quattro, con
claim e source affiancati.

**1. `ws4-soglia-di-sopravvivenza` — grounding 99,99**

    CLAIM : …security ha 19 success con durata media 6.1 min mentre ci ha
            21 cancelled con durata media 23.5 min e 0 success.
    SOURCE: ci cancelled 21 · security cancelled 15 · security success 19
            security success 6.1 min (n=19) · cancelled 3.4 min (n=15)

Il claim afferma **23,5 minuti**. Nella source ci sono **6.1** e **3.4**.
**Quel numero non esiste.** L4.1 ha ragione, e il giudice di fondatezza — che
guarda se il senso è sostenuto — non se n'era accorto.

**2. `a1-costo-ricevuta` — grounding 99,98**

    CLAIM : …i due punteggi sono 0.776 per il quarantinato e 90.59 per l'ammesso.
    SOURCE: score=0.7760113477706909 … score=90.59536743164062

Qui L4.1 ha fermato un **arrotondamento**. È severo. Ma è **esattamente la
regola che ci siamo dati noi**: i numeri vanno scritti come stanno nella source.
Non è un errore del layer: è la nostra severità, applicata.

**3. `approvati-trattenuti-w34-67` — grounding 99,99**

    CLAIM : Nella settimana W34 i quarantinati con grounding sopra 80 sono 67
            e nella W31 sono 17.
    SOURCE: === la crescita degli APPROVATI-ma-trattenuti === W31 17 … W34 67

I numeri **ci sono entrambi**. Ma il claim li chiama «quarantinati con grounding
sopra 80» e la source «approvati-ma-trattenuti». **La grandezza è descritta
diversamente**, ed è difendibile da entrambe le parti: caso ambiguo, lo dichiaro
tale.

**4. `teclast/pacchetto-consegnato`** — non giudicabile: claim e source sono
elenchi di file troncati nella lettura.

## La tesi

Su quattro casi letti, **nessun falso positivo grossolano**. Uno chiaramente
giusto, uno severo ma coerente con le nostre regole, uno ambiguo, uno non
giudicabile.

> **Il grounding e L4.1 non misurano la stessa cosa.** Il grounding chiede: *la
> source sostiene il senso di questa affermazione?* L4.1 chiede: *i numeri sono
> proprio quelli?* **Un fatto può essere perfettamente sensato e avere un numero
> sbagliato**, e in quel caso il primo dice 99,99 e solo il secondo lo ferma.

Con 118 fatti fermati a grounding medio 96,8, **L4.1 sta intercettando errori
numerici dentro claim che sembrano fondati** — cioè esattamente i più
pericolosi, perché nessun'altra difesa li vedrebbe.

L'ho verificato anche su me stesso, stanotte, senza volerlo. L4.1 ha respinto
due miei claim: uno perché conteneva **un'ora che la source non aveva**, l'altro
con la motivazione *«il claim riusa un numero della fonte riferendolo a un'altra
grandezza: 278 qui è "vettori", nella fonte "do"»*. **Aveva ragione entrambe le
volte.** Riscritte le source in modo che numero e grandezza fossero legati,
**28 fatti su 28 sono passati**, con grounding fra 99,37 e 99,98.

## Per chi riprende

- Il righello è `docs/stato-reale/banchi/ws6-la-quarantena-oggi.py` (sola
  lettura, nessun `requalify`). Stampa i casi con claim e source affiancati e
  **non decide**: il giudizio resta a chi legge.
- **Aggiornare la citazione in memoria**: «L1 precisione ~40%» va accompagnato
  da «misurato su 11 casi, maggio 2026, L1 oggi ferma 2 fatti su 2.614».
- **Quello che non ho misurato**: i **207 quarantinati di agosto senza autore**.
  Sapere quale controllo li ha fermati richiede di guardare il percorso di
  scrittura, non lo store — ed è la cosa che renderebbe la quarantena
  interamente leggibile.

---

**Verifica**: `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`.
Istante 22:29:08 del 30/08. Nessuna scrittura, nessun `requalify`.
