# T78 — la ricevuta di scrittura dice le stesse cose con nomi diversi, e nessuno la confronta

*Ticket, 12/09/2026. Sweep di **lettura**: il limite del righello è dichiarato in §4 e
la misura che chiude la domanda **non è stata eseguita**.*

---

## 1. Il presidio esiste, e guarda un'altra superficie

Un banco del repo pinna che le porte «dicano le stesse cose con gli stessi nomi», e il
suo docstring racconta perché fu scritto, il 05/08: una lettura chiamava un campo
`text` e un'altra lo chiamava `proposition` — **due nomi per la stessa cosa**, e a chi
li confrontava è quasi costato un referto sbagliato.

⚠️ Quel banco confronta la superficie del **governo** (il registro dei ritiri).
**La ricevuta di SCRITTURA non è confrontata da nessuno** — ed è la superficie su cui,
in un solo pomeriggio, abbiamo trovato **tre** divergenze.

## 2. Le tre divergenze, in ordine di scoperta

| che cosa | libreria | porta esposta all'agente | esito |
|---|---|---|---|
| chi ha fermato la scrittura | il layer vero | il layer vero | ✅ era la riga di comando a divergere (ticket precedente) |
| gli avvisi del gate | `warnings` | `anti_confab_warnings` | 🔴 **aperto: stesso contenuto, due nomi** |
| il giudizio è avvenuto / è stato rimandato | — | `judged`, `deferred` | 🟡 aperto: vivono su una porta sola |
| chi ha giudicato | c'era | **mancava** | ✅ curato lo stesso giorno, un'ora dopo essere nato |

🔑 **L'ultima riga è la più istruttiva**: quel campo era stato aggiunto **due ore
prima** su una porta sola. Non è debito ereditato — **stava nascendo** mentre
scrivevamo la regola che lo vieta. Chi l'ha curato ha messo nel codice la frase che
questo ticket esiste per difendere: *«un campo che esiste da una parte e non
dall'altra si legge come un'ASSENZA — la differenza va DECISA, non EREDITATA»*.

## 3. Perché il caso dei due nomi conta più di quanto sembri

La lezione di questo pomeriggio, pagata da otto persone, è stata: *«non fidarti
dell'etichetta generica: leggi il layer dentro gli avvisi»*.

⇒ **Ma il nome del campo degli avvisi dipende dalla porta da cui sei entrato.** Chi
impara la lezione su una porta e la applica sull'altra **non trova il campo**, e un
campo che non c'è **si legge come un'assenza**: è esattamente la trappola da cui
veniamo, un piano più su.

📌 **Non tutte le differenze sono difetti**, e il ticket non chiede di uniformare
tutto: la porta esposta rimanda anche il testo del claim, il topic e chi lo vouchsa —
cose che un programma che ha chiamato la libreria **ha già in mano**. La richiesta è
un'altra: **che la differenza sia decisa e scritta, non ereditata e dedotta.**

## 4. ⚠️ Il limite del righello di questo ticket, dichiarato prima delle conclusioni

Le chiavi sono state contate **come letterali nel sorgente** dei due costruttori.
**Un conteggio così non vede le chiavi aggiunte per assegnazione** dopo la creazione
del dizionario — e infatti una l'avevo data per mancante e c'era su entrambe.

> *Il righello descrive la forma del codice, non l'oggetto che esce.* È la stessa
> forma che oggi ci ha ingannati più volte, e qui riguarda chi scrive il ticket.

⇒ **La misura che chiude la domanda è un'esecuzione**: la stessa scrittura dalle porte,
e si confrontano **le chiavi del dizionario restituito**, non il sorgente.

## 5. La cura

1. **Estendere il presidio di parità alla ricevuta di scrittura**, con la forma che il
   banco del governo ha già.
2. **Dichiarare nel banco le differenze volute**, una per una e con la ragione: così
   le altre cadono da sole. Un elenco di eccezioni scritto è un contratto; un elenco
   dedotto è un'opinione.
3. **Decidere il caso dei due nomi.** Non lo decide questo ticket: rinominare una
   chiave pubblica ha un costo per chi già la legge, e la scelta fra «un nome solo» e
   «due nomi con un alias dichiarato» è di chi possiede le porte.

## 6. Il RED — specificato, NON eseguito

> **La stessa scrittura, fatta dalle porte, restituisce ricevute le cui chiavi
> coincidono, tranne quelle dichiarate diverse nell'elenco del banco.**

    ARRANGIA   un claim con una fonte che lo sostiene solo in parte, cosi' che il gate
               abbia qualcosa da dire (una ricevuta con avvisi e' piu' informativa di
               una pulita)
    AGISCI     scrivilo dalle porte, su store isolati
    PRETENDI   insieme_chiavi(A) - insieme_chiavi(B) == differenze_dichiarate
               e viceversa                              <- oggi CADE su almeno un nome

**Controllo positivo, nello stesso braccio**: una chiave presente su entrambe (per
esempio l'identificatore del fatto) deve comparire **in nessuna delle due differenze**.
Senza, un banco che confrontasse insiemi vuoti passerebbe.

🚧 **Chi lo esegue lo veda rosso prima che entri in `tests/`.** Un banco non provato
che nasce verde è il modo in cui i presidi muoiono.

## 7. Quello che questo ticket NON dice

- **Non dice quale nome sia quello giusto**: dice che devono essere uno, o due
  dichiarati.
- **Non ha misurato le ricevute vere**: §4.
- **Non tocca la terza porta** (la riga di comando), che non restituisce un dizionario
  ma stampa: lì la domanda è diversa — *che cosa di tutto questo un utente vede* — e
  merita un ticket suo invece di essere infilata qui.
