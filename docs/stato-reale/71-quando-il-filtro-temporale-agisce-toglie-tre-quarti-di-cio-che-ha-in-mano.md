# 71 — Quando il filtro temporale agisce toglie tre quarti di ciò che ha in mano, e nei casi «sani» pure

*ws6/Aldo — 2 settembre 2026, 00:18. Seguito immediato del [70](70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente.md).*

Il `70` ha chiuso la **copertura** della dichiarazione (0/3 → 3/3). Un numero di
quella misura chiedeva un seguito: `0ebe9e824198` serviva **2** fatti
scartandone **58**. Se fosse tipico, il filtro temporale non è un dettaglio del
ranking — è **la potatura più grossa che una lettura subisca**.

## ① La misura

Fatti vivi e non quarantinati con una data «D mese AAAA» nel testo (31),
domanda costruita dal loro testo, `k=10`. Sono **7** le letture in cui il filtro
si attiva e toglie qualcosa:

| | n | serviti | scartati | il filtro toglie |
|---|---|---|---|---|
| **rotti** — il fatto che risponde è **escluso** | 3 | 22 | 112 | **83,6%** |
| **sani** — il fatto torna lo stesso | 4 | 40 | 110 | **73,3%** |

Scarti per caso: rotti `min 10 · mediana 44 · max 58` · sani `min 9 · mediana 35
· max 40`.

## ② Il dato non è il primo, è il secondo

🔑 **Nei casi «sani» il filtro toglie comunque il 73,3%.** La differenza fra sano
e rotto **non è che il filtro abbia lavorato bene**: è che il fatto giusto stava
sopra la soglia dei `k` anche dopo la potatura. **È tornato per posizione, non
per selettività.**

⇒ I 4 casi sani non sono quattro successi: sono **quattro rischi latenti**. Basta
un fatto in più scritto dopo quella data — cioè il normale accumularsi del
corpus — perché scivolino nella prima riga.

📌 E la distribuzione lo conferma: le due popolazioni **si sovrappongono**
(sani `9-40`, rotti `10-58`). Non c'è una soglia di scarto che separi «letture
salve» da «letture rotte».

## ③ Il rapporto che regge, e quello che non lo fa

✅ **Su 7 letture in cui il filtro agisce, 3 perdono il fatto che risponde.**
⚠️ **Non lo trasformo in un tasso**: 7 casi sono pochi, e `3/7` porterebbe un
intervallo che coprirebbe metà dei valori possibili. Il numero che consegno è
**quanto toglie**, non **quanto spesso sbaglia** — perché il primo è misurato su
134 e 150 risultati, il secondo su sette letture.
⚠️ **`scartati` è un «almeno»**: `recall_as_of` smette di esaminare gli hit
appena ne ha `k` validi, quindi il vero numero di esclusi può essere **più
alto**, mai più basso. Le percentuali di §① sono quindi **prudenti**.

## ④ Cosa NON prova

⚠️ **Campione mio** e costruito come nel `67`: fatti con data nel testo, domande
dal loro stesso testo. **Non è il traffico reale**, che resta non misurabile —
il journal non registra il testo delle query.
❌ **Non dice che il filtro sia sbagliato.** Su una domanda *davvero*
retrospettiva togliere i fatti più recenti **è il suo mestiere**, e il `69` ha
misurato che stringere il trigger costa **6 ancore vere su 18**. Il problema non
è che tolga: è che **tolga tanto** quando la data era il soggetto e non l'ancora.
✅ **Quello che regge**: le due popolazioni si sovrappongono nella quantità di
scarto (§②). Che il fatto giusto sopravviva **non dipende da quanto il filtro ha
tolto**, e questo è un fatto sui dati, non sul campione.

## ⑤ Perché adesso questo si può misurare

Fino a `51762dd4` il numero **non esisteva**: `recall_as_of` filtrava e
restituiva i sopravvissuti, e quanti ne avesse tolti non lo sapeva nessuno. La
cura del `70` lo conserva perché la porta potesse **dichiararlo a chi legge** —
e come effetto collaterale ha reso **misurabile** la grandezza del fenomeno.

> 📌 Un campo aggiunto per avvisare l'utente ha permesso, lo stesso giorno, di
> misurare quanto grande fosse la cosa di cui avvisava.

---
*Banco: `banchi/ws6-quanto-toglie-il-filtro-temporale.py`. Store di Aurelio in
sola lettura.*
