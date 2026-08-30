# Il presidio consiglia una cura che ritirerebbe mille fatti per contraddizioni che non lo sono

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, quarantena.*

`verimem doctor` chiude il suo referto con una riga di avvertimento e un
consiglio:

> `! trust-rank-coverage  2541 of 14049 live facts carry a status with no trust
> rank (user_manual 2494, bootstrap_rule 24, bootstrap_lesson 14, diary 3) —
> they are NEVER auto-retired in a contradiction, so those clashes pile up
> unresolved instead of being decided wrongly`
>
> `fix: normalise those statuses, or add them to _STATUS_RANK
> (verimem/semantic.py)`

Prima di misurare ho fatto la cosa che la nostra regola impone e che rispetto
poco: ho cercato in memoria. È uscito il fatto `62c2a8610c99` — **otto criteri
su otto caduti** nel tentativo di separare un catalogo da un conflitto, e la
conclusione che le **contraddizioni registrate sono circa il 95% rumore**.

Se quel fatto è ancora vero, il consiglio del referto è pericoloso: normalizzare
gli status significa rendere quei fatti **ritirabili automaticamente** in
contraddizioni che per la stragrande maggioranza non sono contraddizioni.

Questo pezzo verifica se lo sia.

## Quante sono, e quante sono irrisolte

Alle **21:55:39 del 30/08**, sullo store in sola lettura:

    contraddizioni registrate: 93.622   irrisolte: 93.263 (99,6%)

    per kind (solo irrisolte):
       numeric_clash    74.071
       boolean_clash    19.192

**Il 99,6% non è mai stato risolto.** Non esistono altri tipi: tutto è uno
scontro fra numeri o fra booleani.

## Sono contraddizioni?

Il campione, letto a occhio, risponde da solo:

    A: GOAL syn 2026-06-20 ESECUZIONE (post-audit): chiusi 4 gap HIGH dell'audit-360…
    B: GOAL syn 2026-06-20 ciclo workflow-audit: lanciato workflow audit-360 (6 agenti opus, 66…
       kind=numeric_clash sim=0.9418

Due voci di diario dello stesso giorno. Una dice «4 gap», l'altra «6 agenti».
**Non si contraddicono: parlano di cose diverse che contengono numeri.**

Per non fermarmi a sei esempi ho campionato **4.000 coppie irrisolte** e ho
applicato il righello che ho già usato nel documento 41 — la similarità di
Jaccard fra le due proposizioni:

| kind | coppie | jaccard < 0,15 («parlano d'altro») | mediana |
|---|---|---|---|
| `numeric_clash` | 3.193 | **2.993 = 93,7%** | **0,039** |
| `boolean_clash` | 807 | **800 = 99,1%** | **0,031** |

**Mediana 0,039**: due fatti dichiarati in contraddizione condividono circa il
**quattro per cento** delle parole. Il ~95% della nostra memoria è confermato,
con un righello diverso da quello di allora.

*(Il Jaccard è un proxy dichiarato: due frasi possono contraddirsi usando parole
diverse. Ma con una mediana di 0,039 e un campione che mostra voci di diario di
argomenti scollegati, la lettura regge.)*

## Perché sbaglia: un criterio che il prodotto sa già applicare altrove

Il `numeric_clash` scatta quando due fatti contengono numeri che non coincidono.
Non verifica che quei numeri si riferiscano **alla stessa grandezza**.

È lo stesso errore che il gate di scrittura **sa già evitare**. Stasera, mentre
salvavo i fatti di un altro documento, il layer `L4.2` mi ha respinto un claim
con questa motivazione:

> *«il claim riusa un numero della fonte riferendolo a un'altra grandezza: 278
> qui è "vettori", nella fonte "do"»*

**Il prodotto possiede già il criterio che eliminerebbe la maggior parte di
questi 93.263 falsi allarmi.** Lo applica in scrittura, dove serve a proteggere
il corpus, e non lo applica nel rilevatore di contraddizioni, dove servirebbe a
non inquinarlo.

## Cosa succederebbe seguendo il consiglio

Il perimetro del fix, contato:

    irrisolte con almeno un fatto senza trust rank:  66.293
    irrisolte con entrambi senza trust rank:         65.882

Sessantaseimila coppie sono un numero che spaventa e che va subito ridotto a
quello vero: **un fatto compare in molte coppie**. I fatti **distinti**:

    fatti DISTINTI senza trust rank in contraddizioni irrisolte:   998
    fatti vivi 14.176, di cui senza trust rank                   2.535
    => il 39,4% dei fatti oggi protetti è già in almeno un clash

**Normalizzare gli status renderebbe ritirabili automaticamente fino a 998
fatti** — il 39,4% di quelli che oggi il mancato trust rank protegge — sulla
base di scontri che nel 93,7-99,1% dei casi non sono contraddizioni.

E il fenomeno non è confinato a quella minoranza: **3.312 fatti distinti, il
23,4% del corpus vivo**, sono coinvolti in almeno una contraddizione irrisolta.

## In difesa del referto

Va detto per intero, perché il doctor non è cieco: la sua stessa riga contiene
**«instead of being decided wrongly»**. Riconosce, nella frase in cui segnala il
problema, che l'alternativa sarebbe decidere male.

Il difetto non è la diagnosi: è **l'ordine delle parole e il fix**. La riga
apre con `!` (avviso), descrive l'accumulo come il male, e chiude con
un'istruzione operativa — *normalise those statuses* — che è l'unica cosa che un
lettore di fretta porta a casa. **Quella che oggi è una protezione viene
presentata come un debito.**

## Per chi riprende

- **Non applicare il fix suggerito** finché il rilevatore non lega numero e
  grandezza. Il numero da guardare non è 2.541 (i fatti senza rank) ma **998**
  (quelli già in un clash).
- Il righello è
  `docs/stato-reale/banchi/ws6-il-consiglio-del-presidio.py` (sola lettura).
- **La cura sensata è a monte**: portare nel rilevatore di contraddizioni il
  criterio di `L4.2`. Non l'ho fatto — è codice del gate, e il gate non si tocca
  senza mandato.
- **Quello che non ho misurato**: quante delle 4,3% di coppie `numeric_clash`
  con jaccard ≥ 0,50 siano contraddizioni **vere**. Sono ~137 nel campione: se
  lo fossero tutte, sarebbero il segnale reale sepolto sotto il rumore, e
  varrebbe la pena tirarle fuori.

---

**Verifica**: `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`.
Istante 21:55:39 del 30/08; il corpus cresce mentre si misura. Campione di
4.000 coppie prese in ordine di `id`.
