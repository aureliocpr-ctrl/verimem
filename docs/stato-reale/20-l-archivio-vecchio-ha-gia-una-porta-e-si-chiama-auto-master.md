# 20 — L'archivio vecchio ha già una porta, e si chiama auto-MASTER

**ws6 · 30/08 ore 14:22** · corpus servibile **12.247** fatti, `mode=ro`, sole SELECT.

I documenti [17](17-la-ricerca-ordina-per-data-non-per-pertinenza.md) e
[19](19-la-cura-del-ranking-peggiora-il-caso-reale.md) dicono cosa **non** funziona, e 19 si chiude
con un problema aperto: cercando per argomento, **18 fatti vecchi su 20 non entrano nemmeno fra i
candidati** di `hippo_facts_search`. Nessun ordinamento può ripescare ciò che non è in lista.

**Questo documento dice che una via d'accesso esiste già, chi la serve, e quanto copre.**

---

## La scoperta, ed è arrivata usando il prodotto

Interrogando `hippo_facts_recall` con **le parole del topic** (`omnex project`) su un fatto del
**10 maggio**:

· ❌ **il fatto specifico non esce** fra i primi cinque;
· ✅ **tutti e cinque i risultati sono su OMNEX** — dove `search` non agganciava niente;
· 🔑 **il primo risultato è un `AUTO-CLUSTER-MASTER`** (`4a88b9bd0a90`, topic
  `project/omnex/auto-MASTER`) che **organizza 80 sotto-fatti** sotto quel prefisso ed elenca i loro
  id in `verified_by`.

⇒ **Il consolidamento costruisce punti d'ingresso per prefisso di topic, e `recall` li serve per
primi.** Chi cerca un argomento vecchio non trova il fatto: **trova la porta del suo cluster**.

## Quanto copre — coi numeri

```
   auto-MASTER esistenti: 114        (su 114 prefissi distinti)
   creati: 52 il 2026-06-20, poi a gocce · 9 il 28/08 · 6 il 29/08 · 6 OGGI

   copertura              coperti / totale        %
     fatti più VECCHI       1.253 / 2.000       62,6
     fatti più RECENTI      1.614 / 2.000       80,7
     TUTTO il servibile    10.863 / 12.247      88,7
```

· **Il meccanismo è vivo**, non un residuo: sei auto-MASTER creati oggi.
· **Copre l'88,7% del corpus.**
· 🔴 **Ma il gap è proprio dove serve**: **37,4% dei fatti più vecchi è scoperto**, contro il 19,3%
  dei più recenti. **Chi ha più bisogno di una porta ce l'ha meno.**

## 🪞 Il difetto del mio misuratore, trovato e corretto

La prima misura diceva **63,6 / 81,2 / 89,0**. Contavo un fatto come coperto con
`topic.startswith(prefisso)`, che fa risultare `project/omnexXYZ` coperto dall'auto-MASTER di
`project/omnex`. Col criterio stretto (`topic == prefisso` **oppure**
`topic.startswith(prefisso + "/")`) i numeri scendono a **62,6 / 80,7 / 88,7**.

**Sovrastima: 38 fatti su 12.247, lo 0,3%.** Il verdetto non cambia — ma il controllo andava fatto
**prima** di pubblicare, non dopo, e la prova che il criterio serve è che togliendolo il numero si
muove.

## Cosa farne, in pratica

· **Per cercare nell'archivio vecchio: `hippo_facts_recall`, e cercare l'ARGOMENTO, non la frase.**
  Quello che torna è il punto d'ingresso del cluster, da cui si arriva ai sotto-fatti.
· **`hippo_facts_search` non serve a questo**: gli auto-MASTER sono testo come tutto il resto, e la
  LIKE non li privilegia.
· **Il gap è azionabile**: far girare il consolidamento sui prefissi vecchi scoperti alzerebbe il
  62,6% senza toccare una riga del percorso di lettura — che è la cura che il documento 19 ha
  scartato.

## Limiti

· **La prova qualitativa è n=1** (una query, un fatto target). Dice che il meccanismo *esiste ed è
  servito*, non con quale frequenza salva la ricerca.
· **`recall` gira degradato** in tutte le mie letture di oggi (`rerank: timeout_cold`) ⇒ quello che
  restituisce è un **pavimento**, non il suo meglio.
· **La copertura è per prefisso di topic, non per contenuto**: un fatto può stare sotto un prefisso
  con auto-MASTER ed essere comunque irrilevante per quel cluster. Non l'ho verificato.
· **L'istante è parte del dato**: 30/08 ore 14:22, corpus servibile 12.247.
