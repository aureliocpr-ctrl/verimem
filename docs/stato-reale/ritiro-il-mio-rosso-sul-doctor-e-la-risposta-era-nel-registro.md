# Ritiro il mio rosso sul `doctor`: è curato. E la risposta era nel registro da ore, mentre io la chiedevo sul canale

*ws3 (Galileo), 28/08 ~18:45. Banco
`docs/stato-reale/banchi/ws3-doctor-dice-il-vero-sui-pesi-o-solo-sui-metadati.py`.
Regime: processo separato per cella, eseguibile `python -m verimem.cli doctor`,
`HIPPO_DATA_DIR` in cartella temporanea (**lo store di Aurelio non è toccato**),
unica variabile `ENGRAM_LOCAL_GATE_MODEL`, **nessun `warmup`, nessun download**,
albero `f59a1f03`.*

## Il rosso che ho portato in giro per undici giorni

Il 17/08 avevo misurato che `verimem doctor` diceva «*local CE gate model
installed — the grounding moat is ON*» con `EXIT=0` su una cartella che
conteneva **il solo `config.json`** — cioè ciò che un'estrazione interrotta
lascia — mentre un `verimem save` reale sulla stessa macchina tornava
`judged=False`, `grounding_score=None`, e **ammetteva un claim smentito dalla
propria fonte**.

**L'ho citato ogni giorno da allora senza rimisurarlo.** Ieri sera l'ho scritto
tre volte sul canale come «il rosso che regge».

## La misura di oggi

    cella            exit   ON?    OFF?   riga del prodotto
    A vuota            2    False  True
    B solo config      2    False  True   the moat does NOT run (moat OFF)
    C reale coi pesi   0    True   False  the grounding moat is ON

**Controllo**: le celle devono differire, altrimenti la variabile non arriva al
prodotto e non c'è verdetto. Firme distinte: **2**.

⇒ **Il rosso è curato e lo ritiro.** La cura è `7b72a9ea` — «*gate model: mezzo
modello sul disco contava come modello installato*» — e `holds_the_weights()`
(`local_grounding.py:68`) fa una `stat` su due nomi invece di fidarsi del solo
`config.json`. **Il commento del codice cita la mia misura del 17/08 come causa
della cura.**

## E il messaggio che esce è migliore di quanto chiedessi

Non dice solo «OFF». Sulla cella B, testualmente:

    ✗ moat-judge  NO working grounding judge:
    <dir> has the model metadata but none of its weights
    (model.safetensors / pytorch_model.bin) — the load fails at the first
    judged write and no llm provider detected, so the moat does NOT run
    (moat OFF) — writes that CARRY A SOURCE are admitted with an L4-skipped
    advisory; … and with nothing judging them, a later write on the same
    source retracts the earlier one, so an unchecked claim can end up the
    only fact left
        fix: delete <dir> and run `verimem warmup` — running it on the
    half-extracted dir reports success without downloading anything

🔑 **Il prodotto nomina da solo la supersessione same-source** — il difetto che
avevo documentato il 26/08 e che @ws4 ha riprodotto ieri. E dà il rimedio
esatto, **incluso l'avvertimento che rilanciare `warmup` sulla cartella
mutilata riporta successo senza scaricare niente**, che è precisamente la
trappola in cui ero caduto io.

## La parte che conta di più: **la risposta era già nel registro**

La riga **W7-18** dice, da ore: «🟢 **no — curato dopo il 17/08**», autrice
**@ws7 (rimisura del claim di ws3)**.

**Ha risposto. Non sul canale — nel registro**, cioè nel file che cito di
continuo. E io ho scritto **tre volte** «*nessuna ha ancora risposto se il loro
rosso fosse un altro*», l'ultima volta ieri sera nella mia riga di chiusura.

> 🔑 **La lezione che avevo già in memoria, dal 21/08, e che ho violato oggi:
> *prima di un ragionamento, CERCA IL DOCUMENTO*.** Chiedere sul canale è più
> facile che leggere il file, e produce l'illusione che nessuno abbia risposto.
> **Il costo non è il rumore: è che ho tenuto vivo un rosso curato**, e ieri
> l'ho consegnato a @lead-audit per il punto ad Aurelio.

## Cosa aggiunge la mia misura, e non è zero

@ws7 aveva dichiarato un limite, esplicitamente:

> ⚠️ «*non ho eseguito quel ramo — servirebbe mutilare la cartella del modello,
> che è **condivisa fra otto istanze**. Ho verificato che i due predicati sono
> distinti e il ramo raggiungibile, **non che il messaggio esca**.*»

**Quel limite è pagato: il messaggio esce.** E la cartella condivisa non è
stata toccata, perché non serve mutilarla — basta
**`ENGRAM_LOCAL_GATE_MODEL`** (`local_grounding.py:35`), che `_resolve_model_dir`
onora prima di ogni default. 📌 **È una tecnica che serve alle altre sette**:
qualunque cella su «modello assente / mutilato» si misura così, in un processo
suo, senza rischiare i 2,3 GB condivisi.

🔑 E vale come istanza della regola di casa: **un limite dichiarato è un debito,
non un'assicurazione.** Il suo era del tipo che poteva ribaltare il verdetto —
un ramo raggiungibile ma muto avrebbe lasciato il rosso vivo — quindi andava
pagato, non archiviato. **Due misure indipendenti, due livelli diversi
(predicati raggiungibili · messaggio alla porta), e la cella ora è chiusa da
entrambi i lati.**

## Bilancio onesto: **i miei due rossi sul moat sono morti tutti e due**

| | cosa dicevo | oggi |
|---|---|---|
| sul **pacchetto** | «il moat non giudica sul pubblicato» | **non regge**: il prodotto lo dichiara **tre volte** nel README **e** a runtime sulla ricevuta ⇒ passo d'installazione dichiarato, non promessa non mantenuta |
| su **`doctor`** | «dice ON con i soli metadati» | **curato**, misurato oggi alla porta |

⇒ **Nel punto ad Aurelio non deve restare né l'uno né l'altro.** Ieri sera ho
consegnato il secondo come «il rosso che regge»: **era falso, e lo correggo
prima che entri in un documento che va fuori.**

## Limiti, dichiarati

⚠️ **Una macchina sola**, la mia, albero `f59a1f03`. Non ho verificato il
comportamento sulla versione **pubblicata su PyPI**: là la cura potrebbe non
esserci ancora, ed è una cella diversa (la 11).
⚠️ Le celle **A** e **B** hanno la **stessa firma** `(ON=False, OFF=True)`: il
mio banco distingue «assente» da «mutilato» solo guardando il **testo**, non
l'esito booleano. Il testo differisce (B nomina i pesi e dà il rimedio), ma
**il mio criterio automatico non lo cattura** — chi lo riusa lo sappia.
⚠️ **Non ho eseguito una scrittura reale** in regime B per confermare che
`judged=False`: ho misurato ciò che `doctor` **dice**, che è esattamente il mio
perimetro e il mio claim originale, **non** ciò che il gate fa. Quella metà era
già misurata il 17/08 e non l'ho rifatta oggi.
