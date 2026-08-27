# ⑪ La quantità vaga non viene confrontata con niente

*ws4 Paragone, misurato il 27/08 fra le 18:30 e le 19:10. Tutte le celle fuori da
pytest, store nuovo per ogni misura, `validate="full"`, CE locale, mai col
giudice llm.*

**In una riga:** i layer numerici del gate confrontano **cifre**. Una
quantificazione vaga — «gran parte», «quasi tutti», «pochi» — non ne ha, quindi
non viene confrontata con nulla; e il giudice semantico la trova sostenuta
perché la fonte parla dello stesso fatto.

---

## 1. Il caso peggiore, e non è quello che esagera

La fonte dà sempre una quantità **esatta**; il claim ne afferma una **vaga**.

| direzione | claim | contro | esito |
|---|---|---|---|
| esagera | «gran parte dei pezzi» | 3 su 40 | passa **99.0** |
| esagera | «la maggioranza» | 2 su 55 | passa **93.0** |
| esagera | «quasi tutti» | 4 su 28 | passa **99.8** |
| esagera | «guasti frequenti» | 1 su 120 | TRATT 0.8 |
| **minimizza** | «**pochi** pazienti» | **30 su 40** | passa **98.1** |
| **minimizza** | «qualche pezzo» | 35 su 40 | passa **85.6** |
| **minimizza** | «una minoranza» | 48 su 55 | passa **99.7** |
| **minimizza** | «guasti sporadici» | 90 su 120 | passa **96.1** |

```
    esagerando   3 falsità su 4 ammesse
    minimizzando 4 su 4          ← tutte, e tutte con ZERO layer
    VERI di controllo            8 su 8 ammessi
```

**Esagerare produce un allarme falso, che qualcuno controlla. Minimizzare
produce un silenzio, che nessuno controlla** — ed è la forma in cui un LLM
riassume un documento.

📌 «sporadici» passa nel verso minimizzante mentre «frequenti» era stato fermato
in quello opposto, sulla stessa struttura di fonte: **non è la parola, è la
direzione.**

## 2. Non è un difetto italiano

| caso | italiano | inglese |
|---|---|---|
| reazioni | passa 98.1 | passa 90.5 |
| ritardi | passa 99.7 | passa 87.7 |
| collaudo | passa 98.7 | passa 84.6 |

**3/3 in entrambe.** È il **primo difetto simmetrico** misurato su questo gate:
tutti gli altri del 26/08 davano l'inglese più robusto (contorno in prosa EN
25.2 contro IT 98.4; contraddizioni implicite EN 0/10 contro IT 3/10). I
punteggi inglesi sono più bassi — il giudice è più prudente — **ma non
abbastanza per fermarne una**.

⇒ Non è una lista monolingue da curare: è una lacuna del modello, da dichiarare
come limite in entrambe le lingue.

## 3. E non è teorico: passa dalla porta ufficiale dei documenti

`promote_chunk_to_fact` è la via per cui un chunk recuperato diventa un fatto, e
il suo docstring dice: «*the caller may pass a **distilled claim** (one clean
sentence) instead of the raw chunk text*». Cioè un LLM legge il chunk e ne scrive
una frase — esattamente questo caso, e la funzione principale del modulo.

Il modulo è **cablato bene**: passa il chunk come `source` e chiede
`ground_write=True`, e il moat gira davvero. Verdetto letto **nello store**:

```
chunk: «…il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40…»

  VERO      «3 su 40»       model_claim    99.9
  VAGO      «gran parte»    model_claim    99.6     ← tre decimi dal vero
  MINIMIZZA «qualche»       model_claim    99.7
  CONTRADD. «non ha»        quarantined     0.8     ✅ fermata
```

Il fatto vago viene salvato con `file:verbale-b12.md:0-146` in `verified_by`. Il
commento del modulo aveva già nominato il rischio — «*il fatto esce con l'aria di
essere verificato DAL DOCUMENTO mentre il documento può dire il contrario: la
provenienza diventa una decorazione*» — **qui la decorazione è misurata su una
quantità.**

## 4. Perché il nostro corpus non può dirci quanto pesa

```
fatti degli ultimi 30 giorni ................. 7974
con un quantificatore vago ................... 14
di cui senza nessuna cifra ................... 1

e la ragione:
fatti che contengono almeno una CIFRA ........ 6595  (82,7%)
via MCP (scritti dagli agenti) ............... 114 su 145  (78,6%)
```

**Noi non scriviamo «gran parte»: scriviamo «3 su 40»**, perché `O3` lo impone. È
un difetto di **riassunto** misurato su un corpus di **misure** — e non esiste
alcuna provenienza `ingest`/`document` nel corpus (verificato: `writer_principal`
dà solo `cli:local` e `mcp:unbound`).

⇒ ⛔ **«1 su 7974» non è un tasso di prodotto.** L'unico uso onesto di quel numero
è: *sul corpus degli sviluppatori il difetto non compare, e il motivo è che gli
sviluppatori scrivono cifre.*

## 5. Cosa regge, e va detto con la stessa forza

* La **contraddizione esplicita** è fermata anche dalla porta documenti (0.8).
* Il claim con le **cifre esatte** resta ammesso: 8/8 nel banco, 4/4 dalla porta.
* I numeri in **lettere** («sette») e le **frazioni** («un quinto») *non*
  sfuggono: lì `L4-grounding` raccoglie quello che `L4.1` non prende — quindi la
  segnalazione di ws3 «se `L4.1` cade nessun altro raccoglie» **non regge**, e la
  ridondanza esiste.

## 6. Il presidio

`tests/test_la_quantita_vaga_elude_i_layer_numerici.py` — **14 passed, 10 xfail
strict**, `--runxfail` verificato. Tiene dentro **quattro** controlli positivi
diversi, perché senza di essi gli xfail misurerebbero un gate spento invece della
vaghezza:

* le cifre esatte restano ammesse (IT ed EN);
* le cifre **sbagliate** sono fermate;
* dalla porta documenti la **contraddizione** è fermata;
* senza `claim` il punteggio resta azzerato — ed è **giusto** così, perché
  lì sarebbe tautologico (`X implica X`, ~100 per costruzione).
