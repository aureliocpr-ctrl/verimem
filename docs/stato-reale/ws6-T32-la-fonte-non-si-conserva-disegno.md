# T32 — la fonte non si conserva, e i fatti con fonte mai giudicati non sono rigiudicabili

**ws6 Dati, 2026-09-08.** Disegno, non cura. Tutti i numeri sotto sono misurati
sul corpus vivo di casa in `mode=ro` oggi; le query stanno in
`scratchpad/t32_*.py` e sono riportate qui in modo che chiunque le rifaccia.

## Il difetto, in una frase

Per un fatto scritto **con una fonte** ma **mai giudicato**, il testo di quella
fonte non esiste più da nessuna parte: `facts` non ha una colonna che lo
conservi, `source_signature` è un'impronta irreversibile (o, per i più vecchi,
un'etichetta), e `audit_mutations` non ne porta traccia. `rejudge` non ha su
cosa lavorare — e questo va detto **nella ricevuta del comando**, non scoperto
da chi lo lancia.

## I numeri, misurati oggi

```
i mai giudicati CON fonte          : 100
   di cui con impronta sha256:     :  74
   di cui con una ETICHETTA        :  26
finestra dei mai giudicati         : 2026-05-10 → 2026-09-08
```

⚠️ **CONTROLLO POSITIVO**, senza il quale i 26 non direbbero niente: la stessa
query sui **giudicati** dà `10205` con fonte, **di cui `10205` con `sha256:`** —
cioè il 100%. La distinzione fra impronta ed etichetta è quindi reale e la query
la vede; i 26 con etichetta non sono un artefatto del filtro.

**Il testo non è recuperabile**, e non è una lettura del codice — è eseguito:

```
colonne di `facts` che riguardano fonte/giudizio:
   source_episodes · verified_by · source_signature ·
   last_verified_at · grounding_score · grounding_span
audit_mutations con 'source' dentro `detail`: 0   (su 1233 righe)
campione di 5 mai giudicati: audit_mutations = 0 per tutti e cinque,
   source_signature = «cycle103-rebrand-2026-05-1…»
```

Nessuna di quelle colonne è il testo della fonte. `grounding_span` è
**l'estratto che il giudice ha usato**, quindi esiste solo dove il giudizio è
avvenuto: per definizione è vuoto proprio nella popolazione che avrebbe bisogno
di essere rigiudicata.

## La finestra include oggi

`2026-05-10 → 2026-09-08`: **non è debito storico**, la popolazione continua a
crescere. Il conteggio dei mai giudicati con fonte è passato da **92**
(mia misura di stamattina, fatto `d2f11bf2c390`) a **100** (adesso), e il post
START ne citava 96.

## Come si lega a T30 (ws4) e T29 (ws2)

**T30** è definito come «1.611 fatti GIUDICATI hanno `source_signature` ma
`grounding_span` vuoto». Applicando quella definizione alla lettera — firma di
fonte **e** span vuoto, senza condizionare sul giudizio — oggi misuro:

```
[def. T30 alla lettera] con firma di fonte e span vuoto: 1711
                        finestra: 2026-05-10 → 2026-09-08
[solo i GIUDICATI con span vuoto]                      : 2786
                        finestra: 2026-07-28 → 2026-09-04
```

Il fatto di ws4 (`9795b28d8336`) dà `n=1611` e la finestra `2026-08-04 →
2026-08-12`. **Non lo smentisco**: quel fatto è `unverified` (nessun
`grounding_score`), e soprattutto una popolazione contata con `AND
grounding_score IS NOT NULL` e una contata senza sono due cose diverse. Le
riporto entrambe con la condizione esplicita perché il confronto sia possibile;
la finestra molto diversa (8 giorni contro 4 mesi) è la cosa da chiarire per
prima fra noi due, prima che uno dei due numeri finisca in un documento
pubblico.

**T29** chiede quanti dei fatti con fonte mai giudicati hanno il TESTO da
rigiudicare e quanti solo l'etichetta. Questa è la risposta misurata: **26 hanno
un'etichetta, 74 un'impronta, e nessuno dei due è il testo.** L'impronta serve a
riconoscere che due fatti vengono dalla stessa fonte, non a ricostruirla: 74 non
è «74 rigiudicabili», è «74 riconoscibili».

## Cosa costa a chi usa il prodotto

Un utente scrive un fatto passando la fonte perché è ciò che separa un claim da
un fatto verificato. Se il giudizio non parte in quel momento — daemon fermo,
processo che esce, delega non disponibile — quel fatto resta `model_claim` e la
fonte **è persa**: non esiste comando che possa rimediare dopo. La promessa
«passa una fonte e il fatto viene verificato» diventa «passa una fonte e spera
che il giudice sia su in quell'istante».

## Tre vie, con la predizione che le falsifica

**(A) Conservare il testo della fonte alla scrittura.** Una colonna
`source_text` (o una tabella `sources` indicizzata per `source_signature`, che
non duplica il testo quando la stessa fonte serve N fatti).
*Predizione:* dopo la cura, un fatto scritto con fonte e giudice fermo è
rigiudicabile e `rejudge` lo porta a `grounding_score` non nullo.
*Come muore:* se dopo la cura `rejudge` continua a non avere il testo, il difetto
non era la conservazione ma il percorso di scrittura.
*Costo da misurare prima:* quanto pesa il testo delle fonti sul disco — va
misurato, non stimato, ed è il motivo per cui questa via non parte oggi.

**(B) Non accettare una scrittura con fonte se non può essere giudicata.**
Rifiutare, o marcarla in modo che l'utente sappia subito che quella fonte non
verrà mai usata.
*Predizione:* zero fatti nuovi nella popolazione dei «mai giudicati con fonte».
*Controindicazione, e non è piccola:* rifiutare una scrittura perché un daemon è
fermo perde il fatto invece della fonte. Va contro «nulla scritto si perde».

**(C) Dirlo, e basta.** Nessun cambio di schema: la ricevuta di `remember`/`save`
dichiara «fonte ricevuta ma NON giudicata, e non conservata: questo fatto non
sarà rigiudicabile», e `rejudge` dice quanti dei candidati non hanno il testo.
*Predizione:* il numero non cala, ma nessuno scopre più il buco a valle.
*È la via più debole sul difetto e la più forte sull'onestà*, ed è quella che
si può fare senza toccare lo store.

## Cosa propongo

**(C) subito e (A) come disegno da approvare.** (C) è dentro l'invariante del
mio ruolo — «nulla scaduto si serve senza dirlo», qui declinato come «nulla di
non giudicato si serve come se lo fosse» — non tocca lo schema e si presidia con
un test. (A) è la cura vera ma cambia lo store: prima serve la misura del costo
su disco, e quella la faccio solo su mandato perché è un banco pesante.

**(B) la sconsiglio**: perde il fatto per salvare la fonte, che è il verso
sbagliato per questo prodotto.

## Cosa serve da chi decide

1. (C) parte adesso sul ramo? È una riga di ricevuta più un presidio.
2. La misura del costo su disco di (A) — la faccio io o è di ws4 (dati)?
3. Il numero pubblico di T30: prima di scriverlo da qualche parte, ws4 e io
   dobbiamo allineare la CONDIZIONE, non il totale. Due query diverse sullo
   stesso corpus danno 1711 e 2786, ed entrambe sono «giuste» per la loro
   definizione.
