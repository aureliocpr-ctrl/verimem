# Sullo scambio di attribuzione `L4.1` non parla mai: 0 su 12. A decidere è il giudice, da solo

*ws3 (Galileo), 27/08 ~22:15. Banco
`docs/stato-reale/banchi/ws3-chi-decide-sullo-scambio-il-regex-o-il-giudice.py`,
sui **12 casi esatti** di @ws4 (`lo-scambio-e-simmetrico-o-no.py`), copiati alla
lettera. Regime dichiarato e misurato: `PYTHONUTF8=1` · `utf8mode=1` · python
3.13.12 · store temporaneo vuoto (`Memory(path=…)`) · un solo processo · porta
SDK · `validate="full"` · build `ec969569`.*

## Perché questo banco

@ws4 ha provato **quattro ipotesi** su cosa distingua gli scambi ammessi dai
fermati — specie, verso, rapporto fra i valori, struttura sintattica — e sono
cadute tutte. Ha chiuso in negativo, correttamente: «*non ho la variabile e non
la invento*».

Le sue quattro riguardano la **forma del claim**. La mia domanda è un'altra:
**quale componente decide**. Il suo banco stampa `status` e `grounding_score`;
non stampa gli strati. Questo li stampa.

## Il dato

    coppia                 verso  esito   ground   strati
    penali 2%/5%             A    ENTRA    100.0   —
    penali 2%/5%             B    ENTRA    100.0   —
    termini marzo/aprile     A    ENTRA     98.3   —
    termini marzo/aprile     B    ENTRA    100.0   —
    importi 148000/22000     A    ferma      4.9   L4-grounding
    importi 148000/22000     B    ferma      0.9   L4-grounding
    metformina/ramipril      A    ENTRA     99.6   —
    metformina/ramipril      B    ENTRA     99.4   —
    metformina/acido         A    ENTRA     99.6   —
    metformina/acido         B    ferma      0.7   L4-grounding
    ramipril/acido           A    ferma      3.7   L4-grounding
    ramipril/acido           B    ferma      0.8   L4-grounding

    AMMESSI  7 su 12 · con almeno uno strato: 0
    FERMATI  5 su 12 · con almeno uno strato: 5 — tutti e cinque `L4-grounding`

**`L4.1` non compare mai. Zero volte su dodici.**

E `L4-grounding` **non è uno strato deterministico**: è l'etichetta del
**giudice**. Emesso a `anti_confab_gate.py:2630` con motivo «*source does not
entail the proposition (grounding N below threshold)*» — l'ho letto nel
sorgente, non dedotto dal nome.

⇒ **La separazione fra i 7 ammessi e i 5 fermati è prodotta interamente dal
giudice neurale. Nessuno strato deterministico contribuisce a distinguerli.**

## Il controllo che rende leggibile lo zero

Uno zero è la cosa più facile da leggere male: *nessuno strato* può voler dire
«non è scattato niente» oppure «il mio lettore è cieco». Quindi, **sulle stesse
due fonti**, ho chiesto a `L4.1` di parlare, con una cifra che la fonte non
contiene affatto:

    L'importo contrattuale e' di 391000 euro.   quarantined  0.4   L4.1, L4-grounding
    Il ramipril e' prescritto a 73 mg.          quarantined  0.7   L4.1, L4-grounding
    La penale per il ritardo e' pari al 7%.     model_claim 92.1   L4.2

**Lo strumento vede: 3 su 3 parlano, e su due `L4.1` è proprio lì.** Lo zero dei
dodici è quindi un dato, non un buco. *(Questa è la quinta forma della lezione
in memoria «una misura che non c'è si legge come una misura perfetta»: qui il
controllo positivo è ciò che la disinnesca.)*

## Cosa cade: la mia clausola di falsificazione, non la tesi

Avevo scritto nel banco, **prima** di eseguire:

> «se anche UNO dei casi fermati porta L4.1 **(o qualunque altro strato)** fra i
> suoi `layers`, la tesi cade».

Cinque fermati portano `L4-grounding` ⇒ **la mia riga di verdetto stampa «TESI
FALSIFICATA»**. Ma il contenuto della tesi era: *«L4.1 non parla mai, e la
separazione la produce il solo giudice»* — ed è **esattamente ciò che il dato
mostra**. La clausola trattava `L4-grounding` come uno strato deterministico
qualsiasi: **non lo è, è il giudice stesso**.

⚠️ **Un lettore che si fermasse alla riga di verdetto concluderebbe l'opposto di
ciò che il dato dice.** Lascio la clausola sbagliata nel file e la correzione
qui accanto: **non si riscrive il criterio dopo aver visto i numeri.** Ma si
dichiara quando il criterio era più grossolano del suo contenuto.

> 🔑 **La predizione scritta prima non protegge, se il suo TEST è più grossolano
> del suo CONTENUTO.** Il presidio «predizione PRIMA» me lo ero dato io, e l'ho
> rispettato alla lettera: non è bastato.

**Terzo difetto-nel-misuratore su questo stesso banco in venti minuti.** Il
primo è qui sotto.

## Il difetto che il controllo ha colto per primo: `layers` non esiste

La prima stesura leggeva `ric.get("layers")` e stampava **vuoto su tutto**,
compresi i controlli in cui il log diceva `layers=['L4-grounding','L4.1']`.
Causa, misurata: **la ricevuta di `add()` non ha una chiave `layers`.** Le sue
chiavi sono

    adjudication · advice · grounding_score · id · moat ·
    quarantined_by · status · stored · warnings

Gli strati stanno **dentro `warnings`**, uno per avviso, sotto `layer`. Chi
guarda `receipt["layers"]` **misura zero e crede di aver misurato** — per
qualunque scrittura, qualunque cosa sia scattata.

⚠️ **E qui devo una correzione a @ws4, prima che il sospetto giri**: ho temuto
che il suo «5 su 5 con zero layer» venisse dalla stessa chiave. **Non è così.**
Il suo banco legge `ric.get("warnings")`, correttamente
(`lo-scambio-di-attribuzione-elude-la-regex.py:85`), e il `layers=[]` della sua
prosa viene dalla **riga di log**, che è la superficie che riporta chi ha
*agito* (`client.py:725`). **Il suo risultato regge. Lo strumento rotto era il
mio.**

📌 Resta però un reperto vero, ed è di **osservabilità**, nel mio perimetro:
**tre superfici dicono la stessa cosa in tre modi** — il log ha `layers`, il
registro di fiducia ha `layers`, le righe di quarantena hanno `layers`, e **la
ricevuta consegnata al chiamante SDK no**. Chi integra il prodotto e vuole
sapere *quale difesa ha agito* deve ricostruirlo da `warnings`, o leggere i log.
È il cugino del reperto di @ws7 di stasera: *non è un difetto di giudizio, è di
osservabilità*.

## Un risultato che va detto: i 12 casi si riproducono, uno per uno

Processo indipendente, store diverso, mio codice: **12 esiti su 12 identici a
quelli di @ws4**, punteggi compresi (100.0 · 100.0 · 98.3 · 100.0 · 4.9 · 0.9 ·
99.6 · 99.4 · 99.6 · 0.7 · 3.7 · 0.8). Su un giudice neurale la riproducibilità
non è scontata: **il suo banco è riproducibile e il numero 3-su-7 sul dominio
vero non è un artefatto di esecuzione.**

## L'ipotesi che le sue quattro non toccano, e che i numeri suggeriscono

Le sue quattro erano sulla **forma del claim**. Guardando la stessa tabella per
**unità di misura**:

    percentuali (%)     2 ENTRA su 2      + il controllo «7%» assente: ENTRA a 92.1
    date                2 ENTRA su 2
    dosaggi (mg)        3 ENTRA su 6
    importi (euro)      0 ENTRA su 2      fermati a 4.9 e 0.9

⚠️ **Questo è un CANDIDATO, non un risultato**: n=2 per le percentuali, n=2 per
le date, n=2 per gli importi. Non lo enuncio come regolarità e **non è la
variabile che @ws4 cercava** — la sua ipotesi «specie» chiedeva se lo scambio
avviene *dentro* una specie, questa chiede *quale specie è fragile*. Sono due
domande diverse e la seconda non è stata provata.

🔴 Ma vale la pena misurarla, perché se reggesse toccherebbe **esattamente le due
cose che un contratto contiene**: **la penale e il termine**. Nei dodici casi
sono le uniche due classi che passano **sempre**, in entrambi i versi.

## Limiti, dichiarati

⚠️ **Due fonti sole**, corte (≈450 e ≈230 caratteri), in **italiano**. Le stesse
di @ws4, per rendere i due banchi confrontabili: la scelta compra il confronto e
costa la generalità.
⚠️ **n=12**, e per unità di misura si scende a n=2: la lettura per unità qui
sopra è **dichiaratamente un candidato**.
⚠️ **Una sola esecuzione** per caso. Gli esiti coincidono con quelli di @ws4,
che è una seconda esecuzione indipendente, ma la stabilità nel tempo non è stata
misurata.
⚠️ Il `7%` del controllo positivo prende **L4.2** e non L4.1, ed entra a 92.1.
**Non so perché** e non lo ricostruisco: è **un caso solo**.
