# Referto del laboratorio — 27/08 sera, un'ora

*Assemblato da ws3 (Galileo). Mandato di Aurelio: «ognuno un ruolo di
ricercatore, concatenate la memoria, guardate su internet, siate massive. Non
voglio cazzate. Il progetto è il progetto».*

⚠️ **Limite di questo referto, dichiarato in testa**: i risultati di ws3 sono
riportati per intero perché sono miei e li ho misurati. Quelli delle altre sette
sono riportati **dai titoli dei loro messaggi sul canale**, non dai corpi
completi: sono **segnalazioni, non verifiche mie**. Ognuna corregga la propria
riga.

## Il fatto che conta più di ogni singolo numero

In dieci minuti, sul canale, **cinque messaggi su sedici sono ritiri o
ribaltamenti a favore del prodotto**, scritti da chi aveva sollevato l'allarme:

> ws4 — «**cade la mia frase delle 20:43, e cade A FAVORE del prodotto**»
> ws1 — «**il gate aveva ragione e avevo torto io**: la scala non crolla»
> ws7 — «**ribaltata a VERDE la riga 31**: il gate aveva ragione»
> ws8 — «**ridimensiona il mio allarme**: `meta_narrative` spegne solo L1»
> ws4 — «**converge sul tuo ritiro** per altra via»

E ws3, cioè io, ne ho collezionati **cinque in una sera** (sotto).

⇒ **Quando ci siamo messe a falsificarci a vicenda invece che a cercare
conferme, la maggior parte dei rossi si è rivelata NOSTRA, non del prodotto.**
Non è un dettaglio di metodo: è la risposta alla domanda «*stiamo girando in
tondo?*». Giravamo perché **misuravamo male e ci credevamo**.

## Fronte per fronte

### ① Concorrenza — CHIUSO (ws3)

Tre letture successive dello stesso fenomeno, **le prime due mie e sbagliate**:

| | write p50 | conclusione |
|---|---|---|
| test 21/07, 2 processi, 10 s | 23.914 ms | «0,2 ops/s, muro invalicabile» |
| mio run, 1 processo, 10 s, **n=2** | 111 ms | ottimista di **10×** |
| mio run, 90 s, **n=35** | **1.213 ms** | il vero, per processi separati |
| **regime servizio, 2 client** | **258 ms** | **14,3 ops/s, 0 errori** |

**Il «muro» era il cold start**: `write_p99` = `write_max` = 26 s, cioè **un
solo valore alto su 140 operazioni**. E il benchmark che lo produceva è
**dichiarato un anti-pattern nel proprio docstring** — che nessuna di noi aveva
letto.

**La curva 2→20 client**: 13,4 → **18,7 (picco a 5)** → 17,5 → **10,4** ops/s.
Satura **fra 5 e 10**. E la **mediana mente**: a 5 client `read_p50` è 96 ms ma
`read_p99` è **3,4 secondi**; a 20 client venti operazioni superano i 10 s.
**Zero errori in tutte le configurazioni: non si rompe, rallenta.**

⚠️ Otto istanze Claude giravano sulla macchina durante il benchmark: il crollo a
20 è **verosimilmente pessimistico**, e di quanto non lo so.

### ② Il documento lungo — CHIUSO, e non era il problema (ws3)

Quattro regimi (fonte corta · lunga-inizio · lunga-metà · lunga-fondo), tre
casi, tre tipi di claim:

    contraddizione ...... 0/12 sfuggite, in tutti i regimi, posizione irrilevante
    omissione ........... 12/12 ammesse, in tutti i regimi, sempre con zero layer
    veri rifiutati ...... 1/3 sulla fonte CORTA · 0/9 sulle fonti LUNGHE

**La mia predizione era che l'omissione peggiorasse sul lungo: falsa.** Passa
uguale, perché **il pavimento era già a terra**. E il dato inatteso è positivo:
**sul documento lungo il gate sbaglia meno sui veri.**

⇒ **Temevamo che il regime lungo invalidasse metà della matrice. Non la
invalida.** Non ci sono due buchi grossi: **ce n'è uno solo.**

### ③ L'unica falla vera: l'omissione

12 casi su 12 ammessi, in ogni regime, **senza che un solo controllo parli**. E
la causa non è una soglia — è nel codice, in **due punti indipendenti**:

    grounding_gate.select_relevant_span   ordina i pezzi della fonte per
                                          SOVRAPPOSIZIONE DI TOKEN COL CLAIM
    anti_confab_gate  (L4.1)              cerca nella fonte i VALORI DEL CLAIM

> **Il gate è guidato da ciò che il claim DICE, e per questo è cieco a ciò che
> TACE.** Due meccanismi diversi, una sola forma.

E si salda con i risultati delle altre: ws4 ha misurato che «*pochi pazienti*»
contro una fonte che dice «*30 su 40*» entra a **98,1 con zero layer**; ws5 che
il numero **scritto a parole** («trecentoquaranta») per `L4.1` **non è più un
numero**. ⇒ **vaghezza, omissione e numerali a parole sono una classe sola**:
in nessuna il claim porta ciò che il gate sa cercare.

## Il metodo che ha prodotto tutto questo

L'anello di falsificazione — ognuna attacca una sola altra, nessuna sé stessa —
ha prodotto in un'ora più correzioni di intere giornate di lavoro parallelo. Le
regole che si sono guadagnate il posto sul campo:

1. **Apri il file accanto prima del primo run.** La diagnosi del cold start era
   già nel docstring del benchmark; l'ho riscoperta in tre run.
2. **Scrivi la predizione prima di eseguire.** Così la falsificazione è
   leggibile, e metà della mia è caduta.
3. **Dichiara il regime, e misuralo invece di presumerlo.** Io l'ho presunto due
   volte e ho sbagliato due volte.
4. **Mai la mediana senza la coda.** A 5 client la mediana dice «perfetto» e il
   p99 dice «3,4 secondi».
5. **Un limite dichiarato non protegge l'enunciato accanto** — a volte lo
   sospende del tutto.
6. **Consegna il tuo punto debole invece di fartelo trovare.**

## Cosa resta scoperto — e lo lascio scritto, non implicito

- **Documenti da 40 pagine reali**: il mio «lungo» sono 15 paragrafi. Su testi
  molto più lunghi **non dico nulla**.
- **La curva su macchina scarica**: senza otto istanze che consumano CPU, il
  tetto fra 5 e 10 client potrebbe stare più in alto. **Di quanto, ignoto.**
- **Il regime servizio con fonte lunga**: le due misure sono separate, la
  combinazione non è stata provata.
- **Perché il giudice viene caricato su scritture che non giudicano** (~2 s per
  un modello mai usato): il caricamento è lazy, quindi *qualcuno lo chiede*.
  Chi, non si sa.

## Una riga per Aurelio

> Il prodotto ha **una falla vera** — non vede ciò che una fonte tace — e **due
> problemi che credevamo di avere e non abbiamo**: la concorrenza e il documento
> lungo. La differenza fra ieri e stasera non è che abbiamo corretto di più: è
> che **abbiamo smesso di crederci sulla parola**.
