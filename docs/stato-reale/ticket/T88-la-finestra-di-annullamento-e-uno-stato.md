# T88 — la finestra di annullamento è uno stato, non un tempo

*Ruolo Dati con il ruolo di prodotto, 13 settembre 2026. Il costo è misurato,
non stimato: sta nella sezione 1.*

---

## 1. Il numero, e come è stato misurato

Il 10 settembre i ritiri per «evoluzione della stessa fonte» riparabili — cioè
quelli con una maniglia di annullamento ancora valida — erano **62**. Il 13
settembre, prima di toccare niente, ne restava **1**. Due righelli indipendenti,
la porta e una query diretta, hanno dato la stessa risposta:

```
ritiri same-source evolution         : 530
di cui con maniglia ANCORA VALIDA    :   1      (erano 62 il 10/09)
maniglie valide totali (ogni motivo) :   6      (erano 90 il 10/09)
voci nel registro                    : 106      (erano 106: NON è cresciuto)
```

⇒ **Sessantuno fatti veri sono usciti dalla finestra in tre giorni**, senza che
nessuno li leggesse, li giudicasse o decidesse di lasciarli andare. Il registro
non è cresciuto di una riga: non è successo nulla, è solo passato il tempo.

## 2. Che cosa fa oggi il prodotto

Ogni ritiro automatico prende uno scatto del fatto prima di toccarlo e ne
registra la maniglia, con una scadenza fissa di **168 ore**. Passate quelle, la
maniglia risponde `expired` e il fatto resta nel corpus per la genealogia ma
non torna più nella lettura di default.

La scelta è difendibile per un'operazione che l'utente ha *chiesto*: chi
cancella qualcosa sa di averlo fatto, e sette giorni sono un ripensamento
ragionevole. **Ma un ritiro automatico non è stato chiesto da nessuno.** Chi
scrive un fatto non sa che ne ha ritirato un altro — a meno che la porta glielo
dica, e fino a ieri due porte su tre non lo dicevano.

⇒ Il tempo di ripensamento comincia a scorrere da un evento che l'interessato
non ha visto. Quando scade, la scelta reversibile è diventata una perdita, e
nessuno se n'è accorto: **è la definizione di silenziosa**.

## 3. La proposta

**La finestra è uno STATO, non un tempo.**

1. La maniglia di un ritiro **automatico** resta valida finché quel ritiro non è
   stato **riletto** — cioè finché qualcuno non lo ha visto in un registro, in
   una ricevuta o in una risposta e non ha deciso. Da quel momento il tempo può
   anche scorrere: la scelta è stata fatta.
2. Il TTL diventa al massimo **una scelta dell'utente**, con default **nessuna
   scadenza**. Chi ha vincoli di spazio o di riservatezza lo accorcia sapendo
   cosa sta scambiando.
3. Il costo è **una riga di registro per ritiro**: al 13 settembre il registro
   intero è 106 righe su 2413 ritiri, perché le altre sono già state potate dal
   tempo. Non è lo spazio il problema che la scadenza risolveva.

⚠️ **Che cosa NON propone questo ticket**: non propone di ritirare di meno. La
direzione è già decisa (T56: si versiona, il vecchio resta e si raggiunge), e
questo ticket riguarda solo per quanto tempo la strada del ritorno resta aperta.

## 4. La domanda aperta, che è di prodotto

Che cosa conta come «riletto»? Tre risposte possibili, e non sono equivalenti:

| | quando la maniglia smette di essere protetta |
|---|---|
| **(a) visto in una lettura** | il fatto ritirato è comparso in una risposta con `--include-superseded` o `--as-of` |
| **(b) visto in un registro** | qualcuno ha aperto `facts retirement-log` e quella riga era nella pagina |
| **(c) deciso** | qualcuno ha annullato il ritiro o lo ha marcato come accettato |

⚠️ La (b) è la più facile da implementare e la più debole: aprire un elenco non
è leggerlo. La (c) è la più forte e chiede una superficie che oggi non esiste —
un modo di dire «questo ritiro va bene». La (a) sta in mezzo e ha un difetto
dichiarato: un fatto che nessuno cerca non viene mai riletto, quindi la sua
maniglia non scade **mai**, che è esattamente ciò che il ticket vuole — e va
detto che è una scelta, non un effetto collaterale.

**Lo decide il ruolo di prodotto.** Qui ci sono i numeri e le tre forme.

## 5. Il controllo che dirà se è stato chiuso

Un ritiro automatico di oggi deve avere una maniglia valida **fra un mese**, se
nessuno l'ha riletto. Si misura con una query sola, e il giorno in cui quel
numero torna a scendere da solo il difetto è tornato.
