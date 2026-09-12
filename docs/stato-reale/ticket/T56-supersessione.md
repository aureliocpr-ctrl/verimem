# T56 — la supersessione della stessa fonte cancella fatti complementari

*Ticket con owner dal 12 settembre 2026 (ruolo Dati). Scritto dopo il ritiro di
una cura sbagliata, perché chi lo riprende non ricominci da dove si è
ricominciato due volte.*

---

## 1. Il difetto, misurato due volte con due righelli diversi

| quando | righello | esito |
|---|---|---|
| 31 agosto | campione letto a mano dei ritiri per «evoluzione della stessa fonte» | **30 letti, 30 sbagliati, zero eccezioni** |
| 9 settembre | tutte le coppie (ritirato → sostituto) del corpus di casa | **425 su 529 (80%)**: il sostituto non porta i numeri del ritirato |

Le forme ricorrenti, dal corpus:

- «la latenza riporta **mediana** 33.0s» ritirata da «la latenza riporta **min** 16.3s» — stessa esecuzione;
- «le righe **retired** sono 1796» ritirata da «le righe **never_judged** sono 64» — stessa passata;
- «nel caso **ZH** lo slice a 3 produce SPAIATO **true**» ritirata da «nel caso **IT** … **false**» — i due bracci dello stesso confronto.

**Nessuno di questi fatti nega quello che ha cancellato.**

## 2. Dove scatta, esattamente

`anti_confab_gate.py` — la supersessione della stessa fonte parte **solo**
quando il layer lessicale L3 dà `verdict == "contradicted"`. Due numeri diversi
vicini alle stesse parole SONO una contraddizione lessicale; che siano il
minimo e la mediana della stessa riga, quel layer non lo distingue.

La classificazione passa poi da `supersession_policy.classify_write_relation`,
conservativa per progetto («any ambiguity → conflict») ma con un ripiego su
`created_at` quando manca `asserted_at` — **che nessuna porta valorizza** (0
fatti su 15.978, misurato il 30 agosto). Il momento di scrittura del candidato è
sempre *adesso*, quindi l'ordine non è ambiguo-e-risolto-in-conflitto: è
**inventato**, e il verdetto è `evolution` per costruzione.

⛔ Il docstring di quella funzione **vieta** la cura ovvia: togliere il ripiego
manderebbe quasi ogni coppia a `conflict`, e a pagarlo sarebbero i fatti veri
(«whoever touches it must measure BOTH populations»).

## 3. I DIECI criteri caduti

Otto il 5 agosto, nel distinguere un catalogo da una contraddizione — e la tesi
che ne uscì diceva già: *l'informazione non è nelle due frasi*.

Più due, il 10 settembre, entrambi falsificati da test che esistevano prima:

**9. L'impronta della fonte** — «un'evidenza non si contraddice da sola»:
stessa impronta ⇒ due letture complementari ⇒ coesistono.
🔴 **FALSIFICATO** da `test_tre_consegne_in_tre_date_restano_tre.py`:

```python
fonte = "Listino: il contratto con Rossi vale 100 euro, poi aggiornato a 120 euro."
mem.add("Il contratto con Rossi vale 100 euro.", source=fonte)
mem.add("Il contratto con Rossi vale 120 euro.", source=fonte)
```

Una fonte **può contenere una successione temporale**: quei due fatti sono
versioni, e l'impronta è la stessa del caso complementare.

**10. La citazione dell'id come discriminante** (escludere dalla coesistenza
chi nomina il fatto che corregge).
🔴 **FALSIFICATO** da `test_reference_not_evolution.py`: rimette sulla rotta
deterministica una guardia che il review del 25 luglio aveva escluso di
proposito — e il codice lo diceva tre righe sopra il punto toccato: *«NO
reference guard on THIS path, deliberately»*.

## 4. Quanto costa sbagliare qui

```
= 11 failed, 12841 passed, 44 skipped, 40 deselected, 131 xfailed in 1763.63s =

test_due_guardie_si_coprono_e_nessuno_lo_sa.py     (1)
test_il_routing_temporale_era_spento_di_default.py (4)
test_la_storia_di_un_fatto_era_scheletrica.py      (1)
test_reference_not_evolution.py                    (1)
test_tre_consegne_in_tre_date_restano_tre.py       (2)
test_una_data_che_si_sposta_non_e_un_registro.py   (2)
```

⚠️ **E in locale quel file era VERDE** (`5 passed in 84.96s`, anche con ordine
casuale): la coesistenza scattava pure lì, ma una **seconda rotta** ritirava lo
stesso e il caso passava. Chi riprova questa strada **esegua col comando della
CI** — suite intera, ordine casuale — non col file singolo.

## 5. Quanto vale la posta, e la finestra che si chiude

```
ritiri per evoluzione della stessa fonte : 530   (2,9% del corpus)
di cui con impronta identica             : 258
maniglie di annullamento ancora valide   :  62
non più riparabili                       : 468
finestra dell'annullamento               : 168,0h esatte — sette giorni
```

⇒ **Ogni settimana una fetta esce dalla finestra e diventa definitiva.** Non
cambia la diagnosi: cambia il costo di lasciare il ticket fermo.

## 6. I due RED, e solo uno è di chi scrive il codice

**RED-1 — l'unificazione (tecnico, indipendente dal criterio).**

> La stessa coppia di scritture, ripetuta dalle tre porte su tre store isolati,
> lascia **lo stesso numero di fatti vivi**.

```
atteso : n(riga di comando) == n(libreria) == n(server di strumenti)
oggi   : 1 == 1 != 2      ROSSO
```

Non dice **quale** debba essere il numero: dice che non possono essere due
numeri diversi. Resta rosso qualunque criterio si scelga. **Si scrive subito.**

**RED-2 — la direzione (decisione, non misura).**

> Quel numero comune è **2** (le due letture restano) oppure **1** (una vince).

⚠️ **Non lo decide chi scrive il codice**: sceglie fra conservare e ritirare,
cioè fissa una promessa all'utente. Lo decide il ruolo di prodotto; qui si
scrive come test appena la decisione c'è. Ciò che la decisione ha in mano sono
i numeri della sezione 1 e della 5.

## 6bis. Le tre forme che la risposta può avere — e la domanda va riscritta

La domanda «1 o 2?» ne ammette **tre** di risposte, non due, e **due delle tre
danno lo stesso conteggio di righe vive**. Il RED-1 non le separa: se il RED-2
si scrive sulla stessa grandezza, resta verde anche quando all'utente non
arriva niente di nuovo — è la trappola del §7, misurata il 4 agosto.

| risposta | promessa all'utente | righe vive | la lettura di default rende |
|---|---|---|---|
| **(A) ritirare** | «ti do il valore più recente, e uno solo» | 1 | 1 |
| **(B) conservare** | «ti do tutte le letture della stessa evidenza» | 2 | **2** |
| **(C) versionare** | «le tengo tutte, ti do l'ultima» | 2 | **1** |

⚠️ **(B) e (C) hanno lo stesso numero di righe vive e promesse opposte.** (C) è
la strada che il §7 indica ed è già nel prodotto per i documenti — ma se il
vecchio resta fuori dalla lettura di default, **il numero della perdita scende
senza che l'utente riceva un fatto in più**: cambia il nome della perdita, non
la perdita.

⇒ **Il RED-2 non si scrive sul conteggio delle righe: si scrive su ciò che una
lettura rende.** In concreto, l'asserzione cambia così:

```
(A)  una ricerca sul tema rende 1 risposta,  ed è la più recente
(B)  una ricerca sul tema rende 2 risposte,  ed è dichiarato che sono
     due letture della stessa evidenza (altrimenti l'utente riceve due
     numeri senza sapere quale vale — §6a del piano di ripristino)
(C)  una ricerca sul tema rende 1 risposta (l'ultima) E la precedente è
     raggiungibile da una porta dichiarata, che va nominata nella
     decisione: senza quella porta, (C) è (A) con un altro nome
```

**La domanda per il ruolo di prodotto, riscritta** — nel linguaggio di chi usa
il prodotto, non in quello della tabella:

> Quando l'utente chiede «quanto è la latenza», e la memoria ha registrato
> *mediana 33,0s* e *min 16,3s* dalla **stessa** esecuzione: quante risposte
> deve ricevere, e se sono due, che cosa gli dice quale vale?

Le tre risposte sono (A), (B), (C) qui sopra. I numeri su cui decidere stanno
nelle sezioni 1 e 5. **Appena la risposta c'è, il RED-2 è una giornata**: il
banco delle tre porte esiste già, cambia l'asserzione finale.

## 7. La strada che resta, e non è un criterio

Dieci criteri testuali caduti dicono la stessa cosa: **l'informazione che
servirebbe non è nelle due frasi**. La decisione del 5 agosto lo aveva già
scritto:

> *non cancellare al write è l'unica strada che non chiede l'impossibile.*

Cioè: non cercare **chi** ritirare, ma cambiare **cosa significa ritirato per
la lettura** — e il modello è già nel prodotto, nel tier dei documenti
(`version INTEGER NOT NULL`, cerca l'ultima, tiene tutte).

⚠️ **La trappola del righello, per chi misurerà.** La misura «21% → ≤2%» **non**
si muove versionando, se il vecchio resta comunque fuori dalla lettura di
default: cambiare il nome della perdita da «ritirato» a «versione non ultima»
fa scendere il numero **senza che l'utente riceva un fatto in più**. È l'errore
del 4 agosto, raccontato nel docstring dello script che misura quanti fatti
tornano davvero.
