# T56 — una politica di conservazione sola sulle tre porte

*Pagina di design dal ruolo Dati, 12 settembre 2026. Nessun codice: il
problema con i numeri, tre alternative con quello che ciascuna rompe, la
decisione proposta, la misura che direbbe che ha funzionato.*

---

## 1. Il difetto

**La stessa scrittura conserva o cancella a seconda della porta da cui entra,
e nessuna delle porte lo dichiara.**

Misurato il 10 settembre sul corpus di casa, contando quanti fatti portano
l'impronta della fonte, per scrittore:

```
  riga di comando        9716 / 10964
  libreria                217 /   269
  server di strumenti       0 /   151     <- non la scrive MAI
```

La politica che decide se una scrittura nuova **ritira** quella vecchia si
accende su quell'impronta: dove l'impronta non c'è, il confronto non trova
«stessa fonte» e il ritiro non avviene. Misurato dalla porta, con due
scritture identiche fatte nei due modi:

- dal server di strumenti: i due fatti restano **entrambi vivi**;
- dalla riga di comando e dalla libreria: il secondo **ritira** il primo (dei
  ritiri per evoluzione della stessa fonte, 468 su 529 vengono dalla riga di
  comando e 61 dalla libreria; **zero** dal server di strumenti).

⇒ Chi usa il prodotto dentro un assistente e chi lo usa da terminale hanno
**due prodotti diversi**, con due politiche di conservazione diverse, e la
differenza non è scritta in nessuna ricevuta né in nessuna pagina.

## 2. Che cosa NON si decide qui

1. **Quando due fatti sono versioni e quando sono letture complementari.** È
   il criterio, ed è un ticket aperto con dieci criteri caduti alle spalle.
   Qui si decide **dove** la politica si applica, non **come** decide.
2. **La finestra dell'annullamento** (ticket a sé).
3. **Il tetto della scansione** (ticket a sé, già in coda).

## 3. Le tre alternative, con quello che ciascuna rompe

### A — ogni porta calcola l'impronta

La porta che oggi non la scrive comincia a scriverla.

- **Ripara**: le tre porte vedono la stessa cosa.
- **Rompe**: da quel giorno quella porta **comincia a ritirare** fatti che
  prima conservava. Per chi la usa è un cambiamento di comportamento
  silenzioso, e arriva sotto forma di fatti che spariscono.
- **Costo**: basso in righe, alto in conseguenze.

### B — l'impronta si calcola nello strato comune di scrittura

Un punto solo, attraversato da tutte e tre le porte, invece di tre punti che
devono ricordarsene.

- **Ripara**: nessuna porta può dimenticarla, e una porta nuova nasce già
  allineata. È la forma che il prodotto usa già per il filtro degli stati
  nascosti, dopo che la stessa classe era costata una cura ripetuta in un
  chiamante su trentotto.
- **Rompe**: niente di per sé — ma produce lo **stesso** effetto di A sul
  comportamento, perché l'impronta comincia a esserci anche dove non c'era.
- **Costo**: trovare il punto comune e provarlo dalle tre porte.

### C — la politica si dichiara nella ricevuta, senza unificarla

Ogni porta scrive nella propria risposta quale politica ha applicato.

- **Ripara**: niente. Ma rende **visibile** una differenza che oggi è muta, e
  chi integra può decidere.
- **Rompe**: niente.
- **Costo**: minimo.

## 4. La proposta: B **verso il comportamento che conserva**, più C

🔑 **L'ordine conta più della scelta.** Unificare adesso verso il
comportamento della riga di comando significa **estendere alla terza porta un
difetto da cui oggi è immune**: il criterio che decide i ritiri è quello con
dieci criteri caduti, e i ritiri che produce sono per la maggior parte
sbagliati (su un campione letto a mano, trenta su trenta; su tutte le coppie,
l'ottanta per cento perde numeri che il successore non porta).

⇒ **Si unifica verso il comportamento che non perde, non verso quello che
cancella.** In concreto:

1. **C subito** — le tre porte dichiarano la politica applicata nella
   ricevuta. Costa poco, non cambia nessun esito, e toglie il silenzio.
2. **B quando il criterio è deciso** — il calcolo dell'impronta si sposta nel
   punto comune, e da lì tutte e tre le porte applicano **lo stesso** criterio,
   quello nuovo.
3. **A mai da sola**: allinea le porte al comportamento peggiore.

**Se la decisione collegiale fosse di unificare prima del criterio**, allora
la conservazione va scelta come default sulle tre porte (nessun ritiro
automatico) e il ritiro resta un'azione esplicita: è la stessa asimmetria che
il prodotto dichiara altrove — perdere un fatto vero è irreversibile, tenerne
due no.

## 4-bis. Il RED che lo prova — e sono DUE, perché le domande sono due

La prima stesura di questa pagina diceva «si unifica verso il comportamento
che conserva» **senza il test che lo prova**: una pagina di design che propone
una direzione e non scrive come si falsifica è prosa. I due RED sono separati
perché rispondono a due domande diverse, e una delle due non è tecnica.

### RED-1 — l'unificazione (tecnico, indipendente dal criterio)

> La stessa coppia di scritture, ripetuta dalle tre porte su tre store
> isolati, lascia **lo stesso numero di fatti vivi**.

```
la coppia: due letture della stessa evidenza, scritte con la stessa fonte
atteso  : n(riga di comando) == n(libreria) == n(server di strumenti)
oggi    : 1 == 1 != 2          ROSSO
```

Non dice **quale** debba essere il numero: dice che non possono essere due
numeri diversi. Resta rosso qualunque criterio si scelga, e diventa verde solo
quando le tre porte decidono allo stesso modo. **È il RED dell'unificazione.**

### RED-2 — la direzione (decisione, non misura)

> Quel numero comune è **2**: le due letture della stessa evidenza restano
> entrambe.

```
atteso  : n == 2 su tutte e tre
oggi    : 2 dal server di strumenti, 1 dalle altre due
```

⚠️ **Questo secondo RED non lo decide chi scrive il codice.** Sceglie fra
conservare e ritirare, cioè sceglie il criterio — e il criterio ha dieci
tentativi caduti alle spalle. Va scritto **dopo** la decisione collegiale, e
la pagina propone `2` per l'asimmetria già dichiarata dal prodotto: perdere un
fatto vero è irreversibile, tenerne due no.

⇒ **RED-1 si può scrivere oggi. RED-2 no**, e dire perché fa parte del
design.

## 5. La misura che direbbe che ha funzionato

| grandezza | oggi | dopo |
|---|---|---|
| fatti con l'impronta della fonte, per scrittore | 0 su 151 da una porta | la stessa quota dalle tre |
| la stessa coppia di scritture dalle tre porte | due esiti diversi | **un esito solo** |
| ricevute che dichiarano la politica applicata | nessuna | tutte e tre |

E il controllo che può smentire la cura, da scrivere **prima** di applicarla:
**se una porta deve legittimamente comportarsi in modo diverso** — per esempio
un ingresso di sola lettura o un canale di importazione — quella porta deve
restare diversa **e dirlo**. Una misura che pretende tre comportamenti
identici senza chiedersi se debbano esserlo è un righello che impone, non che
misura.

## 6. Il rischio dichiarato

La cura tocca il percorso di scrittura, che è il punto in cui il prodotto
decide che cosa dell'utente sopravvive. Un errore qui non si vede in un test
verde: si vede sei mesi dopo, in un fatto che manca. Per questo la pagina
propone di muovere **per primo** ciò che non cambia nessun esito (la
dichiarazione nella ricevuta) e di rimandare il resto a quando il criterio è
deciso.
