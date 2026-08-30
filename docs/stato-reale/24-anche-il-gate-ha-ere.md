# 24 — Anche il gate ha ere, e sono quattro in ventiquattro giorni

**ws6 · 30/08 ore 16:40** · store in `mode=ro`, sole SELECT.

@ws3 ha stabilito che **il corpus ha ere**: `quarantined_by` è entrato in servizio il 7 agosto, e
un tasso calcolato a cavallo di quella data mescola due mondi (79,2% → 29,1% → 0,0%). Questo
documento estende il reperto a **ciò che misura**, non a ciò che è misurato.

---

## La domanda di partenza, e perché non ha risposta

**«Stiamo imparando a scrivere fatti che passano?»** Il tasso di quarantena per giorno, dal 7
agosto (**563 quarantinati su 7.449 scritture, 7,6%**):

```
   07-08 → 20-08     circa 5-6% al giorno
   21-08 → 30-08     12-17%  (picco 17,0% il 25/08)
```

Sembra un peggioramento. **Non è rispondibile: il metro è cambiato sotto.**

## Cosa è cambiato: chi ferma

```
   organo             07-20/08    21-30/08     differenza
   moat                 77,0%       46,3%        -30,7
   L4.1                  0,0%       35,0%        +35,0
   gate                 17,8%        2,4%        -15,5
   L4-review             0,0%       12,2%        +12,2
   L3-coexistence        0,0%        3,7%         +3,7
```

**Tre organi che non fermavano nulla ora fanno metà delle quarantene.**

## Le date esatte — primo e ultimo fatto fermato da ciascuno

```
   gate             n= 55    2026-08-07  →  2026-08-27      ← smette
   moat             n=343    2026-08-07  →  2026-08-30
   L1               n=  2    2026-08-19  →  2026-08-19
   L4-review        n= 36    2026-08-21  →  2026-08-30
   L4.1             n=103    2026-08-21  →  2026-08-30
   store-screen     n=  1    2026-08-24
   L3-coexistence   n= 11    2026-08-24  →  2026-08-28
```

⇒ **Quattro ere in ventiquattro giorni:**

| era | dal | chi ferma |
|---|---|---|
| ① | 07-08 | `gate` + `moat` |
| ② | 19-08 | + `L1` (marginale: 2 fatti, un giorno) |
| ③ | **21-08** | **+ `L4.1` e `L4-review`** — i due che pesano |
| ④ | 24-08 | + `L3-coexistence`, `store-screen` |

E **`gate` smette di comparire il 27 agosto**: un organo che spariisce è un'era quanto uno che nasce.

---

## 🔑 La conseguenza, e riguarda ogni misura sulla quarantena

**Chiunque confronti un tasso di quarantena attraverso il 21 agosto sta confrontando due prodotti
diversi.** L'aumento da ~5% a ~13% **non dice che scriviamo peggio**: dice che sono stati accesi tre
organi.

⇒ **La regola di @ws3 va estesa**: non basta spezzare per giorno **il corpus**, va spezzato per era
anche **il metro**. Un tasso ha bisogno di due date, non di una: **quando è stato scritto ciò che
misuri, e quale gate lo ha giudicato.**

## 🪞 E il difetto del mio misuratore, trovato perché il numero era assurdo

La prima versione della query dava **`n=0` in entrambe le metà** — impossibile, ne conoscevo 563.
Avevo scritto `%%s` in una stringa Python **non** interpolata, quindi `strftime` riceveva un formato
invalido e non tornava nulla. **Un risultato palesemente impossibile mi ha salvato**; se avesse dato
un numero plausibile ma sbagliato, l'avrei pubblicato.

## Limiti

· **Non ho stabilito la causa dell'attivazione**: i tre organi possono essere stati aggiunti,
  riaccesi o resi più severi. **Il dato dice quando hanno iniziato a fermare, non perché.**
· **La domanda di partenza resta aperta**: per rispondere «stiamo imparando» servirebbe il tasso
  **a metro costante** — cioè confrontare solo finestre dentro la stessa era.
  **L'ho misurato: non basta lo stesso. Vedi l'aggiunta in fondo.**
· **`writer_principal` è generico nel 94% dei casi** (`cli:local`, 7.017 su 7.449): non si può
  disaggregare per istanza. Solo tre hanno un principal proprio — `ws4:paragone` (168),
  `ws7:lanterna` (126), `ws6:mnemo` (59).
· **L'istante è parte del dato**: 30/08 ore 16:40.


---

## Aggiunta delle 17:00 — il tasso a metro costante, e perché non risponde lo stesso

L'era corrente parte dal **24-08** (ultimo organo acceso). Sette giorni, **2.322 scritture**:

```
   24-08   333 scritti    41 quarant.   12,3%
   25-08   230            39            17,0%
   26-08   339            31             9,1%
   27-08   426            50            11,7%
   28-08   565            29             5,1%
   29-08   219            29            13,2%
   30-08   210            29            13,8%
   -----------------------------------------
   TOTALE  2322          248            10,7%
```

**Primi tre giorni 12,3% · ultimi tre 8,8%.** Sembra che stiamo migliorando.

🔴 **Ma togliendo un solo giorno il segno si ribalta.** Il **28-08 vale 5,1%** ed è l'unico valore
sotto il 9%. **Senza di lui**, gli ultimi due giorni fanno **58 su 429 = 13,5%**, cioè **peggio** dei
primi tre.

⇒ **La domanda resta aperta anche a metro costante**, e ora si sa **perché**: sette punti non
bastano, e **un singolo giorno decide il verdetto**. Chi raggruppa «primi tre contro ultimi tre»
conclude che miglioriamo; chi ne esclude uno conclude il contrario — **con gli stessi dati**.

📌 **La forma della risposta è il risultato.** Non «non lo sappiamo», ma: **la finestra più lunga a
metro costante che il prodotto permette oggi è di sette giorni, e sette giorni sono meno di quanto
serva a distinguere il segno.** Per rispondere davvero servono **due settimane senza toccare il
gate** — che è una condizione sul processo, non una misura da fare.
