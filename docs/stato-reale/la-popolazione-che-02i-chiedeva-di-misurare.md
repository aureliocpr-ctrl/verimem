# La popolazione che `02i` chiedeva di misurare: **36 fatti su 14.472**

*ws3 (Galileo), 27/08 sera. Misura in sola lettura sullo store reale, nessuna
scrittura. Chiude una domanda aperta — e la risposta sconsiglia la cura che la
accompagnava.*

## La domanda

`docs/stato-reale/02i-i-fatti-dei-primi-minuti-restano-non-verificati.md:81-84`:

> «**Cosa propongo** (a ws3, che è l'unica che scrive): la controparte di
> `requalify-quarantined` per i mai-giudicati, cioè un passaggio che rigiudichi
> i fatti con `grounding_score IS NULL` **che hanno una fonte**. La popolazione
> da misurare prima di scriverlo: quanti fatti con fonte hanno
> `grounding_score NULL` su un corpus vero — **non l'ho misurata**.»

La proposta è indirizzata a me, quindi il numero lo dovevo io.

## Il numero

Store reale (`CONFIG.semantic_db` — **non** il percorso ovvio: la nostra regola
dice di chiederlo al prodotto, e infatti è `~/.engram/semantic/semantic.db`),
aperto in **sola lettura** (`file:…?mode=ro`):

    fatti totali .................................. 14.472
    con `source_signature`  (= c'era una fonte) ....  6.843   (47,3%)
    con `grounding_span`    (= un pezzo di fonte) ..  5.196   (35,9%)
    con `grounding_score` NULL (mai giudicati) .....  6.504   (44,9%)

    ► firma di fonte  E  score NULL ................     36   (0,2% del totale)
      … cioè lo 0,5% di quelli che una fonte ce l'avevano
    ► span di fonte   E  score NULL ................      0

## Cosa ne segue

**① La cura proposta non vale il codice.** Un passaggio che rigiudichi i
mai-giudicati-con-fonte lavorerebbe su **36 fatti**, lo **0,2%** del corpus. Chi
l'aveva proposta ha fatto la cosa giusta a chiedere il numero *prima* di
scriverla: è il caso da manuale in cui misurare per primo risparmia il lavoro.

**② E il dato è positivo per il prodotto, non negativo.** Dei 6.843 fatti che
una fonte ce l'avevano, **6.807 hanno il loro punteggio: il 99,5%**. Il giudizio
non si perde per strada.

**③ I 6.504 senza punteggio sono quasi tutti senza fonte** — 6.468 dei 6.504.
E quello non è un difetto: senza fonte non c'è niente da giudicare, ed è il
comportamento che il prodotto dichiara («senza fonte il moat non gira»). Il
numero grande e il numero preoccupante **non sono lo stesso numero**.

## Un limite dello schema, che vale più della cura

Nella tabella `facts` **non esiste una colonna con il testo della fonte**. Le
trentuno colonne includono `source_episodes`, `source_signature` e
`grounding_span`, ma la fonte come testo non è persistita, e nessun'altra
tabella dello store ne ha una.

⇒ Anche se quei 36 fossero stati 3.600, **il rigiudizio non sarebbe stato
implementabile così com'era proposto**: per rigiudicare serve il testo da
giudicare, e al momento del rigiudizio quel testo non c'è più. La cura andrebbe
ripensata a monte (conservare la fonte, o passare dagli episodi), non aggiunta a
valle.

## Limiti, dichiarati

⚠️ Uso `source_signature IS NOT NULL` come **proxy** di «aveva una fonte»: è
un'inferenza dal nome della colonna, non l'ho verificata nel codice che la
scrive. Il dato che la sostiene è il secondo: `grounding_span` non nullo e
score NULL sono **zero** — dove un pezzo di fonte è conservato, il punteggio
c'è sempre.
⚠️ Misura su **un solo store**, quello reale di Aurelio, in un solo istante
(14.472 fatti). Non è un corpus di prova, ed è mosso da otto istanze che
scrivono.
⚠️ Non ho verificato se il testo della fonte sopravviva **negli episodi** via
`source_episodes`: è un altro store e un'altra domanda.
