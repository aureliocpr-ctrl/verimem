# 58 — Nell'altra direzione la lingua costa uguale, e il livello crolla per una ragione che non ho isolato

*ws6/Aldo — 31 agosto 2026, notte. Chiude due limiti: la direzione opposta del [57](57-la-memoria-attraversa-le-lingue-e-non-attraversa-i-sinonimi.md) e «i fatti sono i miei» del [55](55-non-e-la-forma-della-domanda-e-il-vocabolario.md).*

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

---
*Banco: `banchi/ws6-direzione-opposta.py`. Store di Aurelio in sola lettura.*
