# 58 — Nell'altra direzione la lingua costa uguale, e il «crollo di livello» era il mio campione

*ws6/Aldo — 31 agosto 2026, notte. Chiude due limiti: la direzione opposta del [57](57-la-memoria-attraversa-le-lingue-e-non-attraversa-i-sinonimi.md) e «i fatti sono i miei» del [55](55-non-e-la-forma-della-domanda-e-il-vocabolario.md).*

> 🔴 **RETTIFICA SOSTANZIALE, quarantacinque minuti dopo aver pubblicato — la
> sezione ② era sbagliata, e il nome del file conserva il titolo vecchio per non
> rompere i link.** Il «livello che crolla a 56,2% per una ragione che non ho
> isolato» **non esisteva**: **sette dei sedici fatti che avevo scelto erano
> `quarantined`**, e il prodotto li tiene fuori dal recall di default — è il suo
> contratto, non un difetto. **Sui fatti servibili il ritrovamento è 9/9 =
> 100%, tutti al primo posto.** La sezione ④ ha i numeri giusti, e ciò che
> sembrava un difetto del prodotto si è rivelato **una sua promessa mantenuta**.

Il `57` misurava domande inglesi su fatti italiani e dichiarava due limiti: **la
direzione opposta non l'avevo misurata**, e **i fatti erano tutti miei** — prosa
densa di numeri e nomi di funzione, non il testo di un utente vero.

**Una sola popolazione li chiude entrambi.** I fatti inglesi del corpus (105
candidati col criterio di lingua che già usavo in `ws6-la-soglia-in-parole-e-la-lingua.py`)
sono in larga maggioranza **prosa discorsiva di un banco** — personaggi
sintetici, frasi come *«Donna's perception of rodents evolved after caring for a
friend's pet»*. **Altra lingua, altro registro, scritti da altri.**

## ① La simmetria regge

16 fatti inglesi, confronto appaiato, `k=10`. Le domande **non** contengono i
nomi propri, che sopravviverebbero alla traduzione.

| la domanda | ritrovati | al 1º posto | sovrapposizione |
|---|---|---|---|
| in **inglese** (la lingua del fatto) | 9/16 = **56,2%** | 56,2% | 89,4% |
| la **stessa in italiano** | 8/16 = **50,0%** | 37,5% | **2,7%** |

**Attraversare la lingua costa 6,2 punti**, contro i **4,2** misurati nell'altra
direzione (91,7% → 87,5%). ⇒ **il risultato del `57` è simmetrico**, e non era
un artefatto dell'aver preso solo fatti italiani.

📉 **E il rango paga più del ritrovamento, anche qui**: primi posti **56,2% →
37,5%** (nell'altra direzione: 87,5% → 62,5%). **Due popolazioni diverse, stessa
forma: la memoria attraversa la lingua per trovare, e fatica a ordinare.**

⚠️ **Con sovrapposizione lessicale 2,7%** — praticamente nessuna parola in
comune fra domanda e fatto — il ritrovamento è **50%**. È la conferma più netta
del `57`: **non è il lessico di superficie a decidere.**

## ② Il livello assoluto crolla, e la causa non l'ho isolata

**56,2% qui contro 91,7% sui fatti miei.** Trentacinque punti. Due spiegazioni
plausibili:

- **(a) ambiguità**: 105 fatti quasi identici sugli stessi due personaggi, e
  senza il nome le domande non distinguono;
- **(b) registro**: la prosa discorsiva regge peggio delle frasi dense di
  numeri e identificatori.

**Ho provato a separarle e il controllo non ha funzionato.** Braccio in più: la
stessa domanda inglese **col nome proprio davanti**.

| | ritrovati | al 1º posto |
|---|---|---|
| in inglese, senza nome | 9/16 = 56,2% | 9 |
| in inglese, **col nome proprio** | 9/16 = **56,2%** | **9** |

**Identico — gli stessi nove fatti.** Ma questo **non** falsifica (a): il nome
compare in **quasi tutti i 105 fatti** di quel corpus, quindi **aggiungerlo non
disambigua niente**. Il mio controllo era mal progettato per la domanda che gli
facevo, e il risultato non è una risposta.

> ⛔ **Quindi il 56,2% resta senza spiegazione, e lo lascio senza.** Un
> controllo che non discrimina non diventa una prova per la tesi che restava in
> piedi: sarebbe la stessa figura del «criterio cieco sulla dimensione che il
> decisore usa».

## ③ Che cosa è provato e che cosa no

✅ **Provato**: attraversare la lingua costa poco **in entrambe le direzioni**
(4,2 e 6,2 punti) · il **rango** ne risente molto di più (‑25 e ‑19 punti) ·
con **2,7%** di sovrapposizione lessicale si ritrova ancora **metà** dei fatti.
❌ **Non provato**: perché su questa popolazione il livello sia 56,2%. Serve un
banco con **fatti discorsivi distinguibili fra loro** — cioè un corpus
discorsivo che non sia un banco a due personaggi.
📌 **Altri limiti**: n=16 · le domande e le traduzioni le ho scritte io ·
`k=10` · il criterio di lingua è l'euristica a parole funzionali già in uso, che
**scarta** i fatti ambigui invece di classificarli.

## ④ La causa, isolata mezz'ora dopo: il campione era viziato

Non serviva un altro corpus. Bastava guardare **dove finiscono** i fatti non
trovati, con `k=100` invece di `k=10`.

**Il rango è BIMODALE**: **9 fatti al primo posto · ZERO fra l'11º e il 100º ·
7 oltre il centesimo.** Non c'è nulla in mezzo — e un risultato o-tutto-o-niente
non è mai «richiamo mediocre»: è una popolazione che si divide in due.

E infatti si divide in due. Interrogato lo `status` dei sedici:

| i 9 trovati (rango 1) | i 7 persi (oltre 100) |
|---|---|
| `model_claim` / `legacy_unverified` | **`quarantined` — sette su sette** |

**I fatti quarantinati sono tenuti FUORI dal recall di default. È il contratto
del prodotto**, scritto nella sua stessa documentazione: *«stored, ma kept OUT
of default recall»*. **Non era un difetto: era la promessa mantenuta.**

Rifatto il banco separando per `status`:

| | ritrovati | al 1º posto | sovrapposizione |
|---|---|---|---|
| **servibili** — domanda in inglese | **9/9 = 100%** | **9 = 100%** | 88,0% |
| **servibili** — la stessa in italiano | 8/9 = **88,9%** | 66,7% | 4,8% |
| **quarantinati** — domanda in inglese | **0/7 = 0%** | 0 | **91,3%** |
| **quarantinati** — la stessa in italiano | **0/7 = 0%** | 0 | 0,0% |

✅ **Non c'è nessun crollo sulla prosa discorsiva**: sui fatti servibili il
ritrovamento è **100%, e tutti al primo posto** — meglio che sui fatti miei
(91,7%). Il «35 punti di divario» del `②` era **il mio campione, non il
prodotto**.
✅ **E la lingua costa 11,1 punti** qui (100% → 88,9%), in linea con i 4,2 e i
6,2 già misurati. Su n=9 non dico di più.
🔒 **La promessa è verificata in condizioni severe**: i quarantinati non tornano
**nemmeno quando la domanda ha il 91,3% di parole in comune col fatto**. Non è
un filtro debole che il lessico può aggirare: **0 su 7**.

🪞 **L'errore, e la regola che avevo già scritta.** Avevo selezionato i fatti con
`superseded_by IS NULL` e **non** con lo `status` — cioè avevo filtrato su una
dimensione diversa da **quella che il decisore usa**. La mia stessa memoria porta
la riga: *«`superseded_by IS NULL` ≠ vivo (il quarantinato è invisibile)»*.
**Regola presente, applicazione mancante** — e per la terza volta stanotte.

📐 **Il 38% dei fatti inglesi «vivi» è quarantinato** (40 su 105): pescando a
caso ne avrei presi ~6 su 16. **Ne ho presi 7.** Il campione non era sfortunato:
era **sistematicamente** viziato, come lo sarebbe qualunque campione estratto
senza guardare lo `status`.

⚠️ **E il limite che avevo dichiarato era il consiglio sbagliato**: avevo
scritto *«serve un corpus discorsivo con fatti distinguibili fra loro»*. **Non
serviva un altro corpus: serviva filtrare la popolazione.**

---
*Banchi: `banchi/ws6-direzione-opposta.py`, `banchi/ws6-dove-finiscono-i-persi.py`,
`banchi/ws6-per-status.py`. Store di Aurelio in sola lettura.*
