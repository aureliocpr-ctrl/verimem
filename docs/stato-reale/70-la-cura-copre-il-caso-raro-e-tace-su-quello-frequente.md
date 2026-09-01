# 70 — Case-study n.1: la cura del filone copre il caso raro e tace su quello frequente — 0 su 3

*ws6/Aldo — 2 settembre 2026, 00:02. Chiude il filone «le letture non trovano»
([61](61-il-punteggio-separa-benissimo-e-per-questo-l-avviso-ha-ragione.md) → [67](67-la-data-nella-domanda-spegne-la-risposta.md) → [69](69-la-cura-che-avevo-proposto-costa-sei-ancore-vere-su-diciotto.md)) con la misura della cura, non con il suo racconto.*

## ① L'arco del filone, in quattro righe verificabili

| doc | cosa ha stabilito | come |
|---|---|---|
| `61` | il punteggio **separa** (min trovate `0,8645` · max fuori dominio `0,8474`, **0/10** sopra il minimo) ⇒ l'86% di avvisi **non è rumore**: il difetto è il **retrieval** | banco |
| `67` | una **data nella domanda** attiva il time travel e spegne la risposta: **3/16 retrospettivi**, tutti e tre dal **rango 1**; contemporanei **0/15** | A/B stessa esecuzione |
| `69` | ⛔ **la cura che avevo proposto io** (stringere il trigger) costa **6 ancore vere su 18** — ritirata | banco con controesempi cercati apposta |
| **`70`** | **la cura che è entrata copre 0 dei 3 casi misurati** | questo documento |

## ② La misura che il case-study richiedeva

`letto_al_passato` (`5f84f8a5` + la correzione del fuso `6d79f676`) fa dire alla
porta *«ho letto la domanda come "cosa risultava AL …" e a quell'istante non
c'era nulla»*. Buona cura, e nel `67` §⑥-bis l'ho verificata funzionante sul
corpus vero.

**Ma la sua condizione è `not out`** — esce **solo su risposta completamente
vuota**. Ed ecco cosa succede sui tre casi che il `67` ha misurato come spenti:

```
758425daf047   n=10   fatto giusto PERSO   dichiarazione NESSUNA
0ebe9e824198   n= 2   fatto giusto PERSO   dichiarazione NESSUNA
3e74902dc247   n=10   fatto giusto PERSO   dichiarazione NESSUNA
```

> 🔴 **0 su 3.** Nei casi reali la risposta **non è vuota**: il filtro temporale
> toglie il fatto giusto e ne lascia altri. `out` è pieno, la condizione è falsa,
> la porta tace.

E il banco sull'intera popolazione conferma che non è un caso dei tre:

```
RETROSPETTIVI (dove il difetto accade)  n=16
  risposte VUOTE                        :  0
  risposte servite                      : 16
CONTEMPORANEI (controllo)               n=15
  risposte VUOTE                        :  0
```

⇒ **Nel campione non esiste una sola risposta vuota**, quindi la dichiarazione
non ha mai occasione di uscire. ✅ **Zero rumore** (mai emessa dove non serve),
**zero copertura** dove serve.

## ③ Perché questo è peggio del vuoto

Il vuoto è **onesto**: «non ho trovato niente». Una risposta con dieci fatti da
cui il filtro ha tolto proprio quello giusto è **una risposta plausibile e
sbagliata**, e chi legge non ha nessun segnale.

📌 Il caso `0ebe9e824198` è il più chiaro: **due** risultati, il fatto che
risponde escluso, nessun avviso. Non è «la memoria non lo sa»: è «la memoria lo
sa, e la data nella tua domanda glielo ha fatto scartare».

## ④ La cura che manca ha già il suo precedente nel codice

La condizione giusta non è «`out` è vuoto» ma **«il filtro temporale ha scartato
qualcosa»** — e quel numero oggi **si perde dentro `recall_as_of`**, che filtra e
restituisce solo i sopravvissuti.

🔑 **È esattamente il problema che il pezzo (i) ha già risolto per il pavimento**,
e il suo commento lo dice:

> *«⚠️ IL PRIMA DEL TAGLIO SI CONSERVA … senza questi due valori l'avviso a valle
> non può dire né QUANTI ne ha tagliati né quanto valeva il migliore — `out` è
> stato riassegnato e il prima è perso.»*

⇒ **La stessa forma, sull'altro filtro**: `recall_as_of` conservi quanti ne ha
scartati, e la dichiarazione esca quando quel numero è `> 0`, non quando `out` è
vuoto. **Il vuoto è un caso particolare di quello.**

## ⑤ Cosa NON prova

❌ **Non ho implementato la cura di §④**: la propongo con il suo precedente, non
l'ho scritta né misurata.
⚠️ **`0/3` e `0/16` sono su un campione mio** — fatti vivi il cui testo contiene
una data in forma «D mese AAAA», con la domanda costruita dal loro stesso testo.
**Non è il traffico reale**, che resta non misurabile: il journal non registra
il testo delle query (`67` §⑦).
✅ **Quello che regge**: la condizione `not out` è nel codice, esplicita, e i tre
casi misurati hanno `out` **pieno**. La copertura zero su quella popolazione non
è un'inferenza, è una lettura.
✅ **E la cura non è sbagliata**: fa quello che dichiara di fare, con **zero
rumore** misurato. È **parziale**, e il caso che copre non è quello frequente.

## ⑥ Cosa vale, per il prodotto

Il filone in quattro documenti ha prodotto **tre cambiamenti in `main`** —
`letto_al_passato`, la correzione del fuso, la guardia del pavimento — e **due
raccomandazioni ritirate dopo averle misurate**, una delle quali era mia.

> 🔑 **Il valore non è nei tre commit: è che nessuno dei due ritiri sarebbe
> avvenuto senza un banco.** «Stringere il trigger» sembrava ovvio e costava 6
> ancore vere su 18; «la porta adesso lo dichiara» sembrava chiuso e copre 0 casi
> su 3. Entrambe le volte l'evidenza era a due comandi di distanza.

---
*Banco: `banchi/ws6-quante-letture-mute-parlano-ora.py`. Store di Aurelio in
sola lettura.*
