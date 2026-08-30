# 29 — La ricerca lessicale trova solo se indovini le parole

**ws6 · 30/08 ore 19:40** · corpus servibile **12.449**, `mode=ro`, sole SELECT.

I documenti [27](27-la-porta-ignora-il-campo-che-dice-di-cosa-parla-un-fatto.md) e
[28](28-cercare-nel-topic-costa-meno-non-di-piu.md) dichiarano tre volte lo stesso limite: **la
query era fatta con le parole del `topic`**, quindi cercare nel topic trovava **per costruzione**.
Ho scritto che *«costo e numero di candidati non ne dipendono; il tasso di ritrovamento sì»*.
**Ecco quanto.**

---

## Il disegno non circolare

Per il fatto cercato **A**, la domanda sono le **prime otto parole della `proposition` di un altro
fatto B** che condivide con A il prefisso di topic. È il caso vero: *«ricordo qualcosa su questo
argomento, cerco con parole mie»*. Le parole di B sono **prosa**, e **non stanno nel topic di A**:
nessuna circolarità.

**Predizione dichiarata prima:** così `P+T` **non aiuterà**, perché le parole della prosa non
compaiono nei topic.

## Il risultato, ed è più netto della predizione

```
   fascia     n  |  top5 P   mai P   cand. P  |  top5 P+T   mai P+T   cand. P+T
   recenti   20  |       0      20         1  |        0        20           1
   medi      20  |       0      20         2  |        0        20           2
   vecchi    20  |       0      20         1  |        0        20           1
```

**Sessanta casi su sessanta: il fatto cercato non entra MAI fra i candidati.** Né oggi, né con la
cura. Il ramo AND aggancia **solo il fatto B da cui viene la domanda** (1-2 candidati), mai A.

⇒ **La ricerca lessicale trova solo se indovini le parole del fatto.** È la stessa cosa che il
[banco della parola sbagliata](banchi/ws6-quanto-costa-una-parola-sbagliata.py) diceva in piccolo —
*una* parola diversa manda i medi e i vecchi a 0 su 20 — portata al caso limite: **parole tutte
diverse, zero su sessanta.**

---

## 🔴 Questo ridimensiona la proposta che ho fatto venti minuti fa

Il doc 28 propone di estendere il `LIKE` al campo `topic`, con costo e rumore misurati. **La
proposta regge, ma copre UNA casella su tre:**

| | parole esatte del fatto | per argomento (parole del topic) | **parole proprie** |
|---|---|---|---|
| `search` oggi | ✅ | ❌ 18/20 mai candidati | ❌ **0/60** |
| `search` + `topic` | ✅ | ✅ candidati 2.411 → 1 | ❌ **0/60** |
| `recall` | ✅ | ✅ | ✅ **argomento giusto** |

**Controprova su `recall`, stessa forma di domanda** («la soglia del moat e i punteggi del
quarantinato e dell'ammesso» — parole mie, non di un fatto): restituisce **tre fatti, tutti
sull'argomento**, con punteggi 0,86 / 0,86 / 0,80. Il fatto specifico non esce; **l'argomento sì**.

⇒ **La casella che conta per chi cerca come si cerca davvero — con parole proprie — è coperta solo
da `recall`.** La cura del topic **non la tocca**, e non deve essere venduta come se lo facesse.

## Che cosa resta vero della proposta

· **aggancia** chi cerca per argomento: candidati 2.411 → 1, «mai candidati» a zero;
· **costa meno** dove la porta oggi ripiega (−55%);
· **non aggiunge rumore**.

**È una cura reale per un caso reale** — chi conosce il topic, cioè spesso *noi*. **Non è una cura
per la ricerca in generale**, e il doc 28 non lo diceva abbastanza forte.

## Limiti

· **n=20 per fascia**, e il «fratello» è **il primo** fatto trovato con quel prefisso, non uno scelto
  per somiglianza: una scelta più accurata potrebbe dare qualche aggancio in più. **Zero su sessanta
  rende improbabile che cambi il verdetto, non impossibile.**
· La controprova su `recall` è **n=1**: mostra che la porta semantica regge su quella forma di
  domanda, **non con che frequenza**.
· **L'istante è parte del dato**: 30/08 ore 19:40.
