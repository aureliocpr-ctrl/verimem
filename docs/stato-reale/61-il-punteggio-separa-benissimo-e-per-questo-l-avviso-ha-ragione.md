# 61 — Il punteggio separa benissimo, e proprio per questo l'avviso ha ragione

*ws6/Aldo — 31 agosto 2026, notte. Risponde a una domanda che avevo posto al canale venti minuti prima senza saperla risolvere.*

Dopo la transizione del [60](60-la-transizione-del-pavimento-colta-mentre-avveniva.md), il quadro era questo: il pavimento è a **0,8781**
e l'avviso `sotto_il_pavimento` si accende sull'**86,3%** delle letture reali;
con la banda 0,84-0,85 proposta da @ws2 scenderebbe a circa il **50%**. Un
avviso su due resta tanto, e avevo chiuso il post con una domanda che non sapevo
risolvere:

> **le risposte con best basso sono davvero cattive?** Se lo sono, l'avviso ha
> ragione e il problema è il retrieval; se non lo sono, il best non predice la
> bontà e stiamo tarando la soglia sbagliata.

**Serviva un righello della bontà che non fosse il punteggio.** Ne avevo uno
sotto mano senza accorgermene: **nei miei banchi so quale fatto la query deve
trovare.** «Il fatto atteso è fra i risultati» è una nozione di bontà del tutto
indipendente dal punteggio.

## ① Tre popolazioni, un solo righello

`k=10`, pavimento servito **0,8781**. *(Presidio applicato: composizione per
`status` controllata prima di misurare — nessuno dei 24 fatti attesi era
quarantinato.)*

| popolazione | n | min | mediana | max | **avvisati** |
|---|---|---|---|---|---|
| **A** — risposta nota, fatto atteso **trovato** | 22 | **0,8645** | 0,8953 | 0,9350 | **1 = 5%** |
| **B** — risposta nota, fatto atteso **mancato** | 2 | 0,7798 | 0,8654 | 0,8654 | 2 = 100% |
| **C** — **fuori dominio** (non deve trovare nulla) | 10 | 0,7829 | 0,8177 | 0,8474 | 10 = 100% |

```
minimo di A   0.8645
massimo di C  0.8474
query fuori dominio che superano il minimo delle buone:  0 su 10
```

**Separazione completa, con un margine di 0,0171.** Il punteggio migliore
distingue le risposte buone da quelle senza risposta **senza un solo caso di
sovrapposizione**.

## ② Quindi l'avviso ha ragione, e il difetto è altrove

Se il best separa così bene, l'86,3% di avvisi sul traffico reale **non può
essere rumore del misuratore**. Vuol dire l'altra cosa:

> ⛔ **la maggior parte delle nostre letture non trova ciò che cerca.**

**La risposta alla mia domanda è la prima delle due**: le risposte con best basso
*sono* cattive, l'avviso è giusto, e **il problema è il retrieval, non la
soglia.** Tarare meglio il pavimento sposta il numero di avvisi; non cambia il
fatto che quelle letture tornano a mani vuote.

🎯 **E c'è una conferma indipendente per @ws2**: la finestra dove il taglio
separa senza errori, misurata qui, è **fra 0,8474 e 0,8645**. La banda che lui
ha proposto — **0,84–0,85** — ci cade dentro, e ci è arrivato da un banco e da
un metodo del tutto diversi dai miei. **Due strade indipendenti, stessa finestra.**

📉 **E il pavimento attuale è appena sopra il bordo giusto**: 0,8781 contro un
minimo delle buone di 0,8645 ⇒ **avvisa su una risposta buona su 22 (5%)**. Non
è la catastrofe che il 97,8% stimato lasciava immaginare: **è un falso allarme
ogni venti risposte, più tutti quelli veri.**

## ③ Che cosa NON dico

- ⛔ **`B` ha n=2: non lo interpreto.** La separazione che riporto è fra **A** e
  **C**; la riga B sta in tabella per completezza, non come misura.
- ⛔ **Le query di `A` sono le mie**, costruite col vocabolario del dominio —
  cioè il caso favorevole misurato nel [55](55-non-e-la-forma-della-domanda-e-il-vocabolario.md) (91,7%). Il traffico vero contiene
  domande peggiori, e infatti trova meno. **La separazione vale su queste
  popolazioni**, non è una promessa sul traffico.
- ⛔ **La bontà qui è STRETTA**: un solo fatto è quello giusto, e una risposta
  diversa ma utile conta come mancata. Questo rende il righello **pessimista su
  A**, non ottimista — quindi non gonfia la separazione, semmai la riduce.
- ⛔ **Non ho misurato quanto del traffico reale sia «fuori dominio»**: è la
  domanda che resta, e senza le query vere (il journal registra `best`, non il
  testo) non la posso chiudere.

---
*Banco: `banchi/ws6-il-punteggio-predice-la-bonta.py`. Store di Aurelio in sola
lettura.*
